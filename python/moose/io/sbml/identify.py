"""Recognize native MOOSE kinetics in an arbitrary SBML rate law.

Many BioModels write mass-action or Michaelis-Menten kinetics in non-canonical
algebraic forms (expanded polynomials, ``pow`` for stoichiometry, an explicit
compartment factor, reversible ``k1*A*B - k2*C`` collapsed, ...). The primary
recognizer is :func:`symbolic.analyze`, which decomposes the rate law's algebra
regardless of how it was written. Its result is then numerically self-verified
here: an independent evaluator reconstructs the rate at many random points and
checks it against the original law, so a bad extraction falls back to a
Function rather than silently mis-simulating.

Recognizing native forms matters because native Reac/MMenz (a) are faster,
(b) support the stochastic (GSSA) solver, and (c) are the ONLY way to couple
reactions across compartments (via fixXreacs); a Function cannot read a pool in
another compartment's solver.
"""

import math

import libsbml
import numpy as np

from . import symbolic
from .common import participants
from .units import AVOGADRO

_UNARY = {
    libsbml.AST_FUNCTION_EXP: math.exp,
    libsbml.AST_FUNCTION_LN: lambda x: math.log(x) if x > 0 else -1e30,
    libsbml.AST_FUNCTION_ABS: abs,
    libsbml.AST_FUNCTION_SIN: math.sin,
    libsbml.AST_FUNCTION_COS: math.cos,
    libsbml.AST_FUNCTION_TAN: math.tan,
    libsbml.AST_FUNCTION_TANH: math.tanh,
    libsbml.AST_FUNCTION_FLOOR: math.floor,
    libsbml.AST_FUNCTION_CEILING: math.ceil,
}


def _eval(node, values):
    t = node.getType()
    if t == libsbml.AST_INTEGER:
        return float(node.getInteger())
    if t in (libsbml.AST_REAL, libsbml.AST_REAL_E, libsbml.AST_RATIONAL):
        return node.getValue()
    if t == libsbml.AST_NAME:
        return values.get(node.getName(), 1.0)
    if t == libsbml.AST_NAME_AVOGADRO:
        return AVOGADRO
    if t == libsbml.AST_NAME_TIME:
        return values.get('t', 0.0)
    if t == libsbml.AST_CONSTANT_PI:
        return math.pi
    if t == libsbml.AST_CONSTANT_E:
        return math.e
    n = node.getNumChildren()
    c = [_eval(node.getChild(i), values) for i in range(n)]
    if t == libsbml.AST_PLUS:
        return sum(c) if c else 0.0
    if t == libsbml.AST_TIMES:
        r = 1.0
        for x in c:
            r *= x
        return r
    if t == libsbml.AST_MINUS:
        return -c[0] if n == 1 else c[0] - c[1]
    if t == libsbml.AST_DIVIDE:
        return c[0] / c[1]
    if t in (libsbml.AST_POWER, libsbml.AST_FUNCTION_POWER):
        return c[0] ** c[1]
    if t == libsbml.AST_FUNCTION_ROOT:
        return c[-1] ** (1.0 / c[0]) if n == 2 else math.sqrt(c[0])
    if t in _UNARY:
        return _UNARY[t](c[0])
    raise ValueError(f'uneval node type {t}')


def referenced_names(node, out):
    if node.getType() == libsbml.AST_NAME:
        out.add(node.getName())
    for i in range(node.getNumChildren()):
        referenced_names(node.getChild(i), out)


def identify(reac, const_params, comp_sizes, variable_names):
    """Recognize native kinetics in a reaction's rate law.

    Symbolic decomposition (``symbolic.analyze``) recovers the reaction
    structure and constants in the rate law's own value space; the result is
    numerically self-verified (reconstruct the rate and sample-check it against
    the original law) so a bad extraction falls back to the Function path. The
    caller converts the value-space constants to SI MOOSE units.

    Returns a mapping dict (value space) or ``None``:

    * ``{'kind':'massaction', 'Kf_val', 'Kb_val', 'catalysts': set()}``
    * ``{'kind':'mmenz', 'kcat_val', 'Km_val', 'enzyme'}`` -- ``enzyme`` may
      be ``None`` (lumped-Vmax law, no declared modifier); see symbolic.py.
    """
    kl = reac.getKineticLaw()
    if kl is None or kl.getMath() is None:
        return None

    names = set()
    referenced_names(kl.getMath(), names)
    # A rate law referencing a rule-driven (time-varying) symbol is not a
    # constant-coefficient native form; treat it via the Function fallback.
    if names & variable_names:
        return None

    subst = dict(const_params)
    subst.update(comp_sizes)

    mapping = symbolic.analyze(reac, subst)
    if mapping is None:
        return None
    if not _verify(reac, mapping, subst):
        return None
    return mapping


def _verify(reac, mapping, subst, n=24, tol=1e-6):
    """Sample the original rate law and the rate the recognized native form
    reproduces (both in the rate law's value space); accept only if they agree
    everywhere. Unit conversion to SI is the caller's job and is exact given a
    correct structural match, so verifying in value space is sufficient."""
    ast = reac.getKineticLaw().getMath()
    subs, prds, mods = participants(reac)
    species = sorted(set([s for s, _ in subs] + [s for s, _ in prds] + mods))

    base = dict(subst)
    kl = reac.getKineticLaw()
    for i in range(kl.getNumParameters()):
        base[kl.getParameter(i).getId()] = kl.getParameter(i).getValue()

    rng = np.random.default_rng(20240713)
    worst = 0.0
    denom = 1e-30
    for _ in range(n):
        v = dict(base)
        for s in species:
            v[s] = rng.uniform(0.05, 5.0)
        try:
            r_orig = _eval(ast, v)
        except (ValueError, OverflowError, ZeroDivisionError):
            return False
        if not np.isfinite(r_orig):
            return False

        if mapping['kind'] == 'massaction':
            cat = 1.0
            for c in mapping.get('catalysts', set()):
                cat *= v[c]
            fwd = cat
            for s, st in subs:
                fwd *= v[s] ** st
            bwd = cat
            for s, st in prds:
                bwd *= v[s] ** st
            r_recon = mapping['Kf_val'] * fwd - mapping['Kb_val'] * bwd
        elif mapping['kind'] == 'mmenz':
            # enzyme is None for a lumped-Vmax law with no declared modifier
            # (see symbolic._michaelis_menten); its value-space reading is
            # fixed at 1 by construction in that case.
            e = 1.0 if mapping['enzyme'] is None else v[mapping['enzyme']]
            s = v[subs[0][0]]
            r_recon = mapping['kcat_val'] * e * s / (mapping['Km_val'] + s)
        else:
            return False
        worst = max(worst, abs(r_orig - r_recon))
        denom = max(denom, abs(r_orig))
    return worst / denom < tol
