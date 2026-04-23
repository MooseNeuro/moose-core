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
SWC morphology utilities for MOOSE:

1. Condense an SWC morphology by merging electrotonically short,
   similar-radius segments along each branch before simulation.
   Condensation math from ShapeShifter (Blackwell/Reed/Mada, GMU):
     Hendrickson et al., J Comput Neurosci 2011.
     DC lambda: λ[μm] = sqrt(RM / (4·RA)) · 1000 · sqrt(d[μm])
     Merged compartment preserves total surface area and electrotonic length.

2. Convert GENESIS .p cell morphology files to SWC format.
   Handles cartesian/polar coordinates (relative or absolute), mixed modes,
   prototype blocks, channel-density columns, and C-style comments.

Usage:
    from moose.swc_utils import condense_swc, p_to_swc
    swc_path = p_to_swc('CA1.p', 'CA1.swc')
    condensed = condense_swc('CA1.swc', RM=1.0, RA=1.0)
"""


import os
import math
import re

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


def _reroot_at_soma(segs, by_idx):
    """
    Re-root the SWC tree at the soma (type-1) segment.

    Returns a new list of segment dicts with contiguous 1-based indices and
    parent indices updated so that the soma is index 1 with parent -1.
    All segment positions are unchanged (absolute coords).
    If there is no type-1 segment or soma is already the root, returns the
    original list unchanged.
    """
    soma = next((s for s in segs if s['stype'] == 1), None)
    if soma is None or soma['parent_idx'] == -1:
        return segs  # Already rooted at soma or no soma

    # Collect path from old root to soma via parent links
    path = []
    cur = soma['idx']
    while cur != -1:
        path.append(cur)
        cur = by_idx[cur]['parent_idx']
    path.reverse()  # [old_root_idx, ..., soma_idx]

    # Reverse parent links along the path so soma becomes root
    for i in range(len(path) - 1):
        anc = by_idx[path[i]]
        desc = by_idx[path[i + 1]]
        anc['parent_idx'] = path[i + 1]   # ancestor now points UP to desc
        anc['children'] = [c for c in anc['children'] if c != path[i + 1]]
        desc['children'].append(path[i])
    soma['parent_idx'] = -1
    soma['children'] = [c for c in soma['children'] if c != soma['idx']]

    # BFS from soma → parent-before-child ordering
    from collections import deque
    order = []
    queue = deque([soma['idx']])
    visited = set()
    while queue:
        idx = queue.popleft()
        if idx in visited:
            continue
        visited.add(idx)
        order.append(by_idx[idx])
        for child_idx in by_idx[idx]['children']:
            queue.append(child_idx)

    # Renumber contiguously: old idx → new idx
    old_to_new = {s['idx']: i + 1 for i, s in enumerate(order)}
    result = []
    for s in order:
        result.append(dict(
            idx=old_to_new[s['idx']],
            stype=s['stype'],
            x=s['x'], y=s['y'], z=s['z'], r=s['r'],
            parent_idx=-1 if s['parent_idx'] == -1 else old_to_new[s['parent_idx']],
        ))
    return result


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



# ---------------------------------------------------------------------------
# SWC type inference (.p file helper)
# ---------------------------------------------------------------------------


def _infer_swc_type(name):
    """Return the SWC structure type integer for a compartment name.

    Mapping is based on common GENESIS naming conventions:
      - soma                          -> 1
      - axon / ax*                    -> 2
      - apical* / prim* / glom*       -> 4  (apical / primary-dendrite tree)
      - s2p / p2g                     -> 4  (pseudo-compts in apical path)
      - everything else               -> 3  (basal / lateral / general dendrite)
    """
    n = re.sub(r'\[.*', '', name).lower()
    if n == 'soma':
        return 1
    if n.startswith('ax'):
        return 2
    if (n.startswith('apical') or n.startswith('prim')
            or n.startswith('glom') or n in ('s2p', 'p2g')):
        return 4
    return 3


# ---------------------------------------------------------------------------
# Comment extraction (.p file helper)
# ---------------------------------------------------------------------------


def _collect_p_comments(path):
    """
    Extract all comment text from a GENESIS .p file, preserving order.

    Returns a list of strings — one entry per logical comment line — with
    the comment delimiters (// or /* */) stripped but all other whitespace
    and content preserved.
    """
    comments = []
    in_block = False

    with open(path) as fh:
        for raw in fh:
            line = raw.rstrip('\n')

            if in_block:
                if '*/' in line:
                    text = line[:line.index('*/')].rstrip()
                    if text:
                        comments.append(text)
                    in_block = False
                else:
                    comments.append(line)
                continue

            # Find positions of // and /* so we can tell which wins.
            # A /* preceded by / (i.e. part of //) is a line comment, not a block opener.
            ll_pos = line.find('//')
            bc_pos = line.find('/*')

            # /* is a real block opener only if it exists and comes before any //
            real_block = (bc_pos != -1) and (ll_pos == -1 or bc_pos < ll_pos)

            if real_block:
                before = line[:bc_pos]
                after  = line[bc_pos + 2:]
                if '//' in before:
                    comments.append(before[before.index('//') + 2:].rstrip())
                if '*/' in after:
                    text = after[:after.index('*/')].rstrip()
                    if text:
                        comments.append(text)
                else:
                    in_block = True
                    if after.strip():
                        comments.append(after.rstrip())
                continue

            if ll_pos != -1:
                comments.append(line[ll_pos + 2:].rstrip())

    return comments


# ---------------------------------------------------------------------------
# Coordinate helpers (.p file helper)
# ---------------------------------------------------------------------------


def _polar_to_cartesian_delta(r, theta_deg, phi_deg):
    """
    GENESIS polar -> Cartesian displacement.

    GENESIS polar convention:
      theta : azimuthal angle from x-axis (degrees, in xy-plane)
      phi   : elevation angle from xy-plane (degrees, 0 = horizontal)

    Returns (dx, dy, dz).
    """
    t = math.radians(theta_deg)
    p = math.radians(phi_deg)
    dx = r * math.cos(p) * math.cos(t)
    dy = r * math.cos(p) * math.sin(t)
    dz = r * math.sin(p)
    return dx, dy, dz


# ---------------------------------------------------------------------------
# GENESIS .p file parser
# ---------------------------------------------------------------------------


def parse_p_file(path):
    """
    Parse a GENESIS .p file and return ``(comps, comments)``.

    comps : list of dicts, each with:
        name        : str    compartment name (e.g. 'soma', 'apical_10')
        parent      : str|None  parent compartment name (None for root)
        x, y, z     : float  absolute coordinates (microns)
        r           : float  radius (microns)
        swc_type    : int    SWC structure type

    comments : list of str
        All comment text from the source file (delimiters stripped).
    """
    comps = []
    by_name = {}

    coord_mode = 'cartesian'
    coord_relative = True
    in_proto = False
    in_block_comment = False
    prev_name = None

    with open(path) as fh:
        lines = fh.readlines()

    for raw in lines:
        line = raw

        if in_block_comment:
            if '*/' in line:
                in_block_comment = False
            continue

        # Strip // line comments first (avoids false // + * == /* matches)
        line = re.sub(r'//.*', '', line)

        if '/*' in line:
            before = line[:line.index('/*')]
            after_marker = line[line.index('/*') + 2:]
            if '*/' in after_marker:
                line = before + after_marker[after_marker.index('*/') + 2:]
            else:
                in_block_comment = True
                line = before
            if not line.strip():
                continue

        line = line.strip()
        if not line:
            continue

        if line.startswith('*'):
            tok = line.split()
            directive = tok[0].lower()

            if not in_proto:
                if directive == '*cartesian':
                    coord_mode = 'cartesian'
                elif directive == '*polar':
                    coord_mode = 'polar'
                elif directive == '*relative':
                    coord_relative = True
                elif directive == '*absolute':
                    coord_relative = False

            if directive == '*start_cell':
                in_proto = len(tok) > 1   # True only when a library path follows
            elif directive == '*makeproto':
                in_proto = False

            continue

        if in_proto:
            continue

        tok = line.split()
        if len(tok) < 6:
            continue

        name = tok[0]
        parent_raw = tok[1]

        if any('{' in tok[i] for i in (2, 3, 4, 5)):
            continue

        try:
            a = float(tok[2])
            b = float(tok[3])
            c = float(tok[4])
            diam = float(tok[5])
        except ValueError:
            continue

        if parent_raw == '.':
            parent_name = prev_name
        elif parent_raw.lower() in ('none',):
            parent_name = None
        else:
            parent_name = parent_raw

        if coord_mode == 'polar':
            a, b, c = _polar_to_cartesian_delta(a, b, c)

        comp = {
            'name': name,
            'parent': parent_name,
            '_dx': a, '_dy': b, '_dz': c,
            'r': diam / 2.0,
            'swc_type': _infer_swc_type(name),
            'x': None, 'y': None, 'z': None,
        }

        if parent_name is None:
            comp['x'] = a
            comp['y'] = b
            comp['z'] = c
        else:
            if parent_name not in by_name:
                raise ValueError(
                    f"Compartment '{name}' references unknown parent "
                    f"'{parent_name}' in {path}"
                )
            p = by_name[parent_name]
            if coord_relative:
                comp['x'] = round(p['x'] + a, 6)
                comp['y'] = round(p['y'] + b, 6)
                comp['z'] = round(p['z'] + c, 6)
            else:
                comp['x'] = a
                comp['y'] = b
                comp['z'] = c

        comps.append(comp)
        by_name[name] = comp
        prev_name = name

    comments = _collect_p_comments(path)
    return comps, comments


# ---------------------------------------------------------------------------
# GENESIS .p -> SWC writer
# ---------------------------------------------------------------------------


def p_to_swc(p_path, swc_path=None, source_url=None):
    """
    Convert a GENESIS .p file to SWC format.

    All comment text from the source .p file is written verbatim into the
    SWC header so that authorship and provenance are retained.

    Parameters
    ----------
    p_path : str
        Path to the input .p file.
    swc_path : str, optional
        Output path.  Defaults to p_path with extension replaced by .swc.
    source_url : str, optional
        Original URL or repository location of the .p file; written into
        the SWC header as a provenance note.

    Returns
    -------
    str
        Absolute path of the written SWC file.
    """
    comps, orig_comments = parse_p_file(p_path)

    # Re-root at soma so SWC convention (soma = root) is satisfied
    by_name = {c['name']: c for c in comps}
    soma_comp = next((c for c in comps if c['swc_type'] == 1), None)
    if soma_comp is not None and soma_comp['parent'] is not None:
        # Walk parent links from soma to root to get reversal path
        path = []
        cur = soma_comp['name']
        while cur is not None:
            path.append(cur)
            cur = by_name[cur]['parent']
        path.reverse()  # [old_root_name, ..., soma_name]
        # Reverse edges along path
        for i in range(len(path) - 1):
            by_name[path[i]]['parent'] = path[i + 1]
        soma_comp['parent'] = None
        # BFS to get parent-before-child ordering
        from collections import deque
        children = {c['name']: [] for c in comps}
        for c in comps:
            if c['parent'] is not None:
                children[c['parent']].append(c['name'])
        order, visited, queue = [], set(), deque([soma_comp['name']])
        while queue:
            name = queue.popleft()
            if name in visited:
                continue
            visited.add(name)
            order.append(by_name[name])
            for ch in children.get(name, []):
                queue.append(ch)
        comps = order

    name_to_id = {comp['name']: idx for idx, comp in enumerate(comps, start=1)}

    if swc_path is None:
        swc_path = os.path.splitext(p_path)[0] + '.swc'

    with open(swc_path, 'w') as fh:
        fh.write(f'# Converted from {os.path.basename(p_path)}'
                 f' by moose.swc_utils.p_to_swc\n')
        if source_url:
            fh.write(f'# Source: {source_url}\n')
        fh.write('#\n')
        fh.write('# ---- Original comments from source .p file ----\n')
        for line in orig_comments:
            fh.write(f'#{line}\n')
        fh.write('# ---- End of original comments ----\n')
        fh.write('#\n')
        fh.write('# n type x y z radius parent\n')

        for idx, comp in enumerate(comps, start=1):
            pname = comp['parent']
            pid = -1 if pname is None else name_to_id.get(pname, -1)
            fh.write(
                f"{idx} {comp['swc_type']} "
                f"{comp['x']:.4f} {comp['y']:.4f} {comp['z']:.4f} "
                f"{comp['r']:.4f} {pid}\n"
            )

    return os.path.abspath(swc_path)


#
# swc_utils.py ends here
