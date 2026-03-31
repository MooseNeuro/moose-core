# swc_utils.py ---
#
# Filename: swc_utils.py
# Description: Reduce compartment count in SWC morphology
#
# Author: Subhasis Ray and ClaudeAI (Derived from ShapeShifter by
# Jonathan Reed, Saivardhan Mada, and Avrama Blackwell)
#
# Created: Fri Mar 27 21:59:03 2026 (+0530)
#

# Code:

"""
Reduce compartment count of an SWC morphology by merging electrotonically
short, similar-radius segments along each branch before simulation.

Condensation math from ShapeShifter (Blackwell/Reed/Mada, GMU):
  Hendrickson et al., J Comput Neurosci 2011.
  DC lambda: λ[μm] = sqrt(RM / (4·RA)) · 1000 · sqrt(d[μm])
  Merged compartment preserves total surface area and electrotonic length.
"""


import os
import math
import tempfile

SOMA_TYPE = 1


# ---------------------------------------------------------------------------
# Electrotonic math (adapted from ShapeShifter/shape_shifter.py, GMU)
# ---------------------------------------------------------------------------


def _lambda_factor(RM, RA, CM=0.01, f=0.0):
    """
    λ_factor [μm^½] such that λ[μm] = λ_factor · sqrt(diameter[μm]).
    f=0  → DC lambda (CM not needed).
    f>0  → AC lambda (CM required).
    RM [Ω·m²], RA [Ω·m], CM [F/m²], f [Hz].
    """
    dc = math.sqrt(RM / (4.0 * RA)) * 1000.0
    if f == 0.0:
        return dc
    if CM is None:
        raise ValueError("CM is required for AC lambda (f > 0)")
    w = 2.0 * math.pi * f * RM * CM
    return dc * math.sqrt(2.0 / (1.0 + math.sqrt(1.0 + w * w)))


def _elec_len(length_um, diam_um, lf):
    """L = length / (lf · sqrt(diam)), dimensionless."""
    if length_um <= 0 or diam_um <= 0:
        return 0.0
    return length_um / (lf * math.sqrt(diam_um))


def _merge_geometry(segs_data, surface_tot, Ltot, lf):
    """
    Hendrickson (2011): compute merged compartment geometry.

    segs_data : list of {'dx', 'dy', 'dz'} — per-segment displacement vectors
                relative to each segment's original parent (μm).
    Returns   : (dx, dy, dz, radius_new) all in μm.
                dx/dy/dz is the displacement from the proximal to the new distal.
    """
    new_diam = (surface_tot / (Ltot * math.pi * lf)) ** (2.0 / 3.0)
    new_len = surface_tot / (math.pi * new_diam)

    # Sum of relative vectors telescopes to (last_seg - first_seg_parent)
    sx = sum(s['dx'] for s in segs_data)
    sy = sum(s['dy'] for s in segs_data)
    sz = sum(s['dz'] for s in segs_data)
    mag = math.sqrt(sx * sx + sy * sy + sz * sz)

    if mag > 0:
        dx, dy, dz = sx / mag * new_len, sy / mag * new_len, sz / mag * new_len
    else:
        dx, dy, dz = new_len, 0.0, 0.0  # degenerate: lay along x

    return dx, dy, dz, new_diam / 2.0


# ---------------------------------------------------------------------------
# SWC I/O
# ---------------------------------------------------------------------------


def _read_swc(path):
    """
    Parse an SWC file. Returns (segs_list, by_idx dict).
    Each segment: idx, stype, x, y, z, r, parent_idx, children=[].
    """
    segs, by_idx = [], {}
    with open(path) as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            f = s.split()
            if len(f) < 7:
                continue
            seg = dict(
                idx=int(f[0]),
                stype=int(f[1]),
                x=float(f[2]),
                y=float(f[3]),
                z=float(f[4]),
                r=float(f[5]),
                parent_idx=int(f[6]),
                children=[],
            )
            segs.append(seg)
            by_idx[seg['idx']] = seg
    for seg in segs:
        pi = seg['parent_idx']
        if pi != -1 and pi in by_idx:
            by_idx[pi]['children'].append(seg['idx'])
    return segs, by_idx


def _write_swc(out_segs, path):
    with open(path, 'w') as fh:
        fh.write('# Condensed by moose.swc_utils\n')
        for s in out_segs:
            fh.write(
                f"{s['idx']} {s['stype']} "
                f"{s['x']:.4f} {s['y']:.4f} {s['z']:.4f} "
                f"{s['r']:.4f} {s['parent_idx']}\n"
            )


# ---------------------------------------------------------------------------
# Tree traversal and condensation
# ---------------------------------------------------------------------------


def _collect_chain(start, by_idx):
    """
    Walk the linear chain from start until a branch point, leaf, or
    segment type change. Returns list of segments in order.
    """
    chain = [start]
    cur = start
    while True:
        children = [by_idx[c] for c in cur['children']]
        if len(children) == 1 and children[0]['stype'] == cur['stype']:
            cur = children[0]
            chain.append(cur)
        else:
            break
    return chain


def _split_chain(chain, by_idx, lf, max_len, rad_diff):
    """
    Greedily group chain segments so each group stays within max_len
    electrotonic lengths and rad_diff fractional radius tolerance.
    Returns list of groups (each a list of segment dicts).
    """
    groups, cur_group, Ltot = [], [], 0.0
    for seg in chain:
        pp = by_idx[seg['parent_idx']] if seg['parent_idx'] != -1 else seg
        length = math.sqrt(
            (seg['x'] - pp['x']) ** 2
            + (seg['y'] - pp['y']) ** 2
            + (seg['z'] - pp['z']) ** 2
        )
        L = _elec_len(length, seg['r'] * 2.0, lf)

        can_add = True
        if cur_group:
            ref_r = cur_group[0]['r']
            if ref_r > 0 and abs(ref_r - seg['r']) / ref_r > rad_diff:
                can_add = False
            if Ltot + L >= max_len:
                can_add = False

        if not can_add:
            groups.append(cur_group)
            cur_group, Ltot = [], 0.0

        cur_group.append(seg)
        Ltot += L

    if cur_group:
        groups.append(cur_group)
    return groups


def condense_swc(
    swc_path, RM, RA, CM=0.01, max_len=0.1, f=0.0, rad_diff=0.1, out_path=None
):
    """
    Reduce an SWC morphology by merging electrotonically short,
    similar-radius segments. Returns path to the condensed SWC file.

    Parameters (SI units)
    ---------------------
    RM       : Membrane resistance   [Ω·m²]
    RA       : Axial resistivity     [Ω·m]
    CM       : Membrane capacitance  [F/m²]  (required only when f > 0)
    max_len  : Max electrotonic length per output compartment (default 0.1)
    f        : Frequency [Hz] for AC lambda; 0 = DC lambda (default)
    rad_diff : Max fractional radius difference for merging (default 0.1)
    out_path : Output SWC path; None → temp file
    """
    lf = _lambda_factor(RM, RA, CM, f)
    segs, by_idx = _read_swc(swc_path)
    root = next(s for s in segs if s['parent_idx'] == -1)

    out_segs = []
    _ctr = [0]

    def emit(stype, x, y, z, r, parent_new_idx):
        _ctr[0] += 1
        out_segs.append(
            dict(
                idx=_ctr[0],
                stype=stype,
                x=round(x, 4),
                y=round(y, 4),
                z=round(z, 4),
                r=round(r, 4),
                parent_idx=parent_new_idx,
            )
        )
        return _ctr[0]

    def visit(seg, parent_new_idx, prox_x, prox_y, prox_z):
        """
        Emit seg and descendants.
        Soma segments: unchanged.
        All other types: condense along linear chains using Hendrickson eqs.
        prox_x/y/z: the OUTPUT position of this segment's parent.
        """
        if seg['stype'] == SOMA_TYPE:
            new_idx = emit(
                SOMA_TYPE,
                seg['x'],
                seg['y'],
                seg['z'],
                seg['r'],
                parent_new_idx,
            )
            for cid in seg['children']:
                child = by_idx[cid]
                visit(child, new_idx, seg['x'], seg['y'], seg['z'])
            return

        chain = _collect_chain(seg, by_idx)
        groups = _split_chain(chain, by_idx, lf, max_len, rad_diff)

        cur_idx = parent_new_idx
        cur_x, cur_y, cur_z = prox_x, prox_y, prox_z

        for group in groups:
            segs_data, surface_tot, Ltot = [], 0.0, 0.0
            for node in group:
                pp = (
                    by_idx[node['parent_idx']]
                    if node['parent_idx'] != -1
                    else node
                )
                dx = node['x'] - pp['x']
                dy = node['y'] - pp['y']
                dz = node['z'] - pp['z']
                length = math.sqrt(dx * dx + dy * dy + dz * dz)
                diam = node['r'] * 2.0
                segs_data.append({'dx': dx, 'dy': dy, 'dz': dz})
                surface_tot += math.pi * diam * length
                Ltot += _elec_len(length, diam, lf)

            if Ltot > 0 and surface_tot > 0:
                gdx, gdy, gdz, new_r = _merge_geometry(
                    segs_data, surface_tot, Ltot, lf
                )
            else:
                # Zero-length or zero-radius: pass through last segment as-is
                last = group[-1]
                gdx = last['x'] - cur_x
                gdy = last['y'] - cur_y
                gdz = last['z'] - cur_z
                new_r = last['r']

            cur_x += gdx
            cur_y += gdy
            cur_z += gdz
            cur_idx = emit(
                group[0]['stype'], cur_x, cur_y, cur_z, new_r, cur_idx
            )

        # Recurse on children of the last node in the chain
        for cid in chain[-1]['children']:
            visit(by_idx[cid], cur_idx, cur_x, cur_y, cur_z)

    visit(root, -1, root['x'], root['y'], root['z'])

    if out_path is None:
        out_path = os.path.normpath(
            swc_path.rpartition('.')[0] + '.condensed.swc'
        )

    _write_swc(out_segs, out_path)
    print(f'Saved condensed SWC file at {out_path}')
    return out_path


#
# swc_utils.py ends here
