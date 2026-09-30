# writer.py --- clean-room SBML writer for MOOSE
#
"""
Writes a MOOSE reaction-diffusion model (compartments, Pool/BufPool,
Reac, MMenz, Enz, Function-driven rules, diffusion constants) out as
standard SBML.

Unit convention (mirrors units.py exactly, in the inverse direction)
----------------------------------------------------------------------
* substance = mole (SBML default -- no UnitDefinition needed: an absent
  'substance' UnitDefinition means substance_scale()==1 on read).
* volume = a UnitDefinition ('m3') of one cubic metre, set as the model's
  default volumeUnits, so a compartment's size is written verbatim as its
  MOOSE volume (already SI m^3) and size_scale() comes back 1.0 on read.
* every species is hasOnlySubstanceUnits="true": its value in a kinetic
  law or rule is its amount in mole, so initialAmount = nInit/NA exactly
  inverts species_ninit(), and no per-reaction compartment-size factor is
  needed in a kinetic law formula.

Reaction rate constants
----------------------------------------------------------------------
MOOSE's Reac.numKf/numKb (Enz.k1/k2/k3) are volume-independent rate
constants defined on molecule *counts* n = amount*NA (see Reac.cpp /
convertConcToNumRateUsingMesh -- this is true whether or not the reaction
is single- or cross-compartment, and needs no solver to be built). Writing
a kinetic law in terms of species *amount* a (mole) instead of n means
every rate constant of a monomial of total order k (number of reactant
instances feeding that monomial, counting stoichiometry) picks up a factor
NA**(k-1):

    dn/dt = numK * prod(n_i^st_i) = numK * NA**k * prod(a_i^st_i)
    da/dt = dn/dt / NA            = numK * NA**(k-1) * prod(a_i^st_i)

so Kf_val = numKf * NA**(order_sub-1) is exactly the coefficient the SBML
kinetic law (written against amounts) must use, and symmetrically for
Kb_val/order_prd. The same relation, with order=1, leaves an intensive rate
constant (Enz.k3/kcat) unchanged -- so one formula covers both cases.

MMenz.kcat/Km are already in the mixed convention rate = kcat*E*S/(Km+S)
with E, S as *concentrations*; substituting conc = amount/volume gives
rate [mol/s] = kcat * E_a * S_a / (Km*V + S_a), i.e. kcat is unchanged and
Km_val = Km * V (V = the enzyme's own compartment volume, in m^3). For
several distinct substrates, or one substrate wired with stoichiometry > 1,
S is the *product* of every wired substrate value (repeats included) in
both the numerator and denominator with Km unscaled.

Limitations
----------------------------------------------------------------------
* A Function feeding a pool via 'increment'/'setN' is converted to a
  MathML rule by literal token substitution (x0, x1, ... -> the connected
  pool's amount*NA, matching the 'nOut'/x[i] push convention reader.py's
  _Inputs uses -- see its docstring for why that convention, and not a
  'requestOut' pull, is the one Stoich's compiler actually recognizes)
  through libsbml's infix-formula parser; a Function using constructs the
  parser can't express (piecewise/logical operators) is reported
  unsupported and no rule is written.
* A pool that is both a reaction participant *and* Function-driven (a
  partial-ODE assembly, mixing native kinetics with a Function remainder)
  cannot be represented as a single SBML rate law; the reaction side is
  written and the Function contribution is reported unsupported.
* SBML-spatial geometry is not written (nothing to write: the reader does
  not build one either); only diffusion coefficients are round-tripped.
"""

import re

import libsbml
import moose
from moose import _moose
from moose.chemUtil.chemConnectUtil import findCompartment
from moose.fixXreacs import restoreXreacs

from .report import WriteReport
from .units import AVOGADRO

_ID_RE = re.compile(r'[^A-Za-z0-9_]')
_TOKEN_RE = re.compile(r'\bx(\d+)\b')


class UnsupportedModel(Exception):
    """The model has nothing writable (e.g. no compartments)."""


class _Ids:
    """Hands out unique, SBML-legal SIds, mirroring reader ids where they
    started legal (mostly) so a round trip keeps recognizable names."""

    def __init__(self):
        self._used = set()

    def make(self, name):
        base = _ID_RE.sub('_', str(name)) or 'id'
        if base[0].isdigit():
            base = '_' + base
        sid, n = base, 2
        while sid in self._used:
            sid = f'{base}_{n}'
            n += 1
        self._used.add(sid)
        return sid


class _Model:
    """Bookkeeping shared across the write passes."""

    def __init__(self, sbml_model, report):
        self.sbml = sbml_model
        self.report = report
        self.ids = _Ids()
        self.compartment_id = {}   # moose ChemCompt path -> SBML compartment id
        self.species_id = {}       # moose Pool/BufPool path -> SBML species id


# ----------------------------------------------------------------------
# compartments / species
# ----------------------------------------------------------------------
def _create_compartments(root, mdl):
    compts = _moose.wildcardFind(root.path + '/##[0][ISA=ChemCompt]')
    if not compts:
        raise UnsupportedModel(f'model {root.path!r} has no compartment (ChemCompt)')
    for c in compts:
        c = moose.element(c)
        sid = mdl.ids.make(c.name)
        sc = mdl.sbml.createCompartment()
        sc.setId(sid)
        sc.setName(c.name)
        sc.setSpatialDimensions(3)
        sc.setSize(c.volume)
        sc.setConstant(True)
        mdl.compartment_id[c.path] = sid
        mdl.report.compartments += 1


def _create_species(root, mdl):
    pools = _moose.wildcardFind(root.path + '/##[0][ISA=PoolBase]')
    for p in pools:
        p = moose.element(p)
        comp = findCompartment(p)
        if comp.path not in mdl.compartment_id:
            mdl.report.unsupported_add(
                f'species {p.path!r} has no enclosing compartment; skipped')
            continue
        sid = mdl.ids.make(p.name)
        sp = mdl.sbml.createSpecies()
        sp.setId(sid)
        sp.setName(p.name)
        sp.setCompartment(mdl.compartment_id[comp.path])
        sp.setHasOnlySubstanceUnits(True)
        sp.setInitialAmount(p.nInit / AVOGADRO)
        buffered = bool(p.isA['BufPool'])
        sp.setBoundaryCondition(buffered)
        sp.setConstant(buffered)
        mdl.species_id[p.path] = sid
        mdl.report.species += 1


# ----------------------------------------------------------------------
# diffusion (SBML L3 spatial DiffusionCoefficient)
# ----------------------------------------------------------------------
_SPATIAL_NS = 'http://www.sbml.org/sbml/level3/version1/spatial/version1'


def _any_diffusive(root):
    for p in _moose.wildcardFind(root.path + '/##[0][ISA=PoolBase]'):
        if moose.element(p).diffConst > 0:
            return True
    return False


def _mark_reactions_local(mdl):
    """Every Reaction gets a SpatialReactionPlugin once the spatial package
    is registered on the document, and SBML-spatial requires 'isLocal' be
    set on it; we do not model per-voxel-local vs bulk reactions, so mark
    every reaction local (a valid, harmless default the reader ignores)."""
    for i in range(mdl.sbml.getNumReactions()):
        reaction = mdl.sbml.getReaction(i)
        plug = reaction.getPlugin('spatial')
        if plug is not None:
            plug.setIsLocal(True)


def _write_diffusion(root, mdl):
    pools = _moose.wildcardFind(root.path + '/##[0][ISA=PoolBase]')
    for p in pools:
        p = moose.element(p)
        if p.diffConst <= 0 or p.path not in mdl.species_id:
            continue
        sid = mdl.species_id[p.path]
        prm = mdl.sbml.createParameter()
        prm.setId(mdl.ids.make(sid + '_diffConst'))
        prm.setValue(p.diffConst)
        prm.setConstant(True)
        plug = prm.getPlugin('spatial')
        if plug is None:
            mdl.report.warnings.append(
                'spatial package unavailable in this libsbml build; '
                f'diffConst for {p.path!r} not written')
            continue
        dc = plug.createDiffusionCoefficient()
        dc.setVariable(sid)
        dc.setType(libsbml.SPATIAL_DIFFUSIONKIND_ISOTROPIC)
        mdl.report.diffusing_species += 1


# ----------------------------------------------------------------------
# kinetics helpers
# ----------------------------------------------------------------------
def _counts(neighbors):
    """(ordered distinct elements, stoichiometry) for a neighbor list that
    may repeat an element once per unit of stoichiometry (see reader._wire)."""
    order, count = [], {}
    for n in neighbors:
        n = moose.element(n)
        if n.path not in count:
            order.append(n)
            count[n.path] = 0
        count[n.path] += 1
    return order, count


def _monomial(order, count, sid_of):
    if not order:
        return None
    parts = []
    for elem in order:
        st = count[elem.path]
        sid = sid_of[elem.path]
        parts.append(sid if st == 1 else f'{sid}^{st}')
    return '*'.join(parts)


def _species_reference(reaction, order, count, sid_of, kind):
    for elem in order:
        ref = reaction.createReactant() if kind == 'sub' else reaction.createProduct()
        ref.setSpecies(sid_of[elem.path])
        ref.setStoichiometry(count[elem.path])
        ref.setConstant(True)


def _set_kinetic_law(reaction, formula, params, mdl):
    kl = reaction.createKineticLaw()
    math = libsbml.parseL3Formula(formula)
    if math is None:
        mdl.report.unsupported_add(
            f'reaction {reaction.getId()!r}: could not parse generated formula {formula!r}')
        return False
    kl.setMath(math)
    for pid, value in params:
        lp = kl.createLocalParameter()
        lp.setId(pid)
        lp.setValue(value)
    return True


# ----------------------------------------------------------------------
# Reac -> mass-action SBML reaction
# ----------------------------------------------------------------------
def _create_reactions(root, mdl):
    for r in _moose.wildcardFind(root.path + '/##[0][ISA=Reac]'):
        r = moose.element(r)
        sub_order, sub_count = _counts(r.neighbors['sub'])
        prd_order, prd_count = _counts(r.neighbors['prd'])
        if not sub_order and not prd_order:
            mdl.report.unsupported_add(
                f'reaction {r.path!r} has neither substrate nor product; skipped')
            continue
        for elem in sub_order + prd_order:
            if elem.path not in mdl.species_id:
                mdl.report.unsupported_add(
                    f'reaction {r.path!r} references unwritten species {elem.path!r}; skipped')
                break
        else:
            _emit_reac(r, sub_order, sub_count, prd_order, prd_count, mdl)


def _emit_reac(r, sub_order, sub_count, prd_order, prd_count, mdl):
    order_sub = sum(sub_count.values())
    order_prd = sum(prd_count.values())
    reaction = mdl.sbml.createReaction()
    rid = mdl.ids.make(r.name)
    reaction.setId(rid)
    reaction.setName(r.name)
    reaction.setFast(False)

    _species_reference(reaction, sub_order, sub_count, mdl.species_id, 'sub')
    _species_reference(reaction, prd_order, prd_count, mdl.species_id, 'prd')

    fwd = _monomial(sub_order, sub_count, mdl.species_id)
    bwd = _monomial(prd_order, prd_count, mdl.species_id) if prd_order else None

    params = [('kf', r.numKf * AVOGADRO ** (order_sub - 1))]
    formula = 'kf' if fwd is None else f'kf*{fwd}'
    reversible = bool(bwd) and r.Kb != 0.0
    if bwd is not None and reversible:
        params.append(('kb', r.numKb * AVOGADRO ** (order_prd - 1)))
        formula = f'({formula}) - (kb*{bwd})'
    reaction.setReversible(reversible)

    if _set_kinetic_law(reaction, formula, params, mdl):
        mdl.report.reactions += 1


# ----------------------------------------------------------------------
# MMenz -> Michaelis-Menten SBML reaction
# ----------------------------------------------------------------------
def _create_mmenz(root, mdl):
    for e in _moose.wildcardFind(root.path + '/##[0][ISA=MMenz]'):
        e = moose.element(e)
        enz = e.neighbors['enzDest']
        sub_order, sub_count = _counts(e.neighbors['sub'])
        prd_order, prd_count = _counts(e.neighbors['prd'])
        if not enz or not sub_order or not prd_order:
            mdl.report.unsupported_add(
                f'MMenz {e.path!r} missing enzyme/substrate/product; skipped')
            continue
        enz = moose.element(enz[0])
        missing = [x for x in [enz] + sub_order + prd_order
                   if x.path not in mdl.species_id]
        if missing:
            mdl.report.unsupported_add(
                f'MMenz {e.path!r} references unwritten species; skipped')
            continue
        _emit_mmenz(e, enz, sub_order, sub_count, prd_order, prd_count, mdl)


def _emit_mmenz(e, enz, sub_order, sub_count, prd_order, prd_count, mdl):
    reaction = mdl.sbml.createReaction()
    rid = mdl.ids.make(e.name)
    reaction.setId(rid)
    reaction.setName(e.name)
    reaction.setFast(False)
    reaction.setReversible(False)

    _species_reference(reaction, sub_order, sub_count, mdl.species_id, 'sub')
    _species_reference(reaction, prd_order, prd_count, mdl.species_id, 'prd')
    mref = reaction.createModifier()
    mref.setSpecies(mdl.species_id[enz.path])

    s_term = _monomial(sub_order, sub_count, mdl.species_id)
    enz_sid = mdl.species_id[enz.path]
    formula = f'kcat*{enz_sid}*{s_term}/(Km + {s_term})'
    params = [('kcat', e.kcat), ('Km', e.Km * enz.volume)]

    if _set_kinetic_law(reaction, formula, params, mdl):
        mdl.report.enz_reactions += 1


# ----------------------------------------------------------------------
# Enz -> explicit two-step complex-forming enzyme
# ----------------------------------------------------------------------
def _create_enz(root, mdl):
    for e in _moose.wildcardFind(root.path + '/##[0][ISA=Enz]'):
        e = moose.element(e)
        enz = e.neighbors['enzDest']
        cplx = e.neighbors['cplx']
        sub_order, sub_count = _counts(e.neighbors['sub'])
        prd_order, prd_count = _counts(e.neighbors['prd'])
        if not enz or not cplx or not sub_order or not prd_order:
            mdl.report.unsupported_add(
                f'Enz {e.path!r} missing enzyme/complex/substrate/product; skipped')
            continue
        enz = moose.element(enz[0])
        cplx = moose.element(cplx[0])
        missing = [x for x in [enz, cplx] + sub_order + prd_order
                   if x.path not in mdl.species_id]
        if missing:
            mdl.report.unsupported_add(
                f'Enz {e.path!r} references unwritten species; skipped')
            continue
        _emit_enz(e, enz, cplx, sub_order, sub_count, prd_order, prd_count, mdl)


def _emit_enz(e, enz, cplx, sub_order, sub_count, prd_order, prd_count, mdl):
    sid_of = mdl.species_id
    order_sub = 1 + sum(sub_count.values())  # enzyme + substrates

    # Step 1: E + S <-> cplx (reversible, k1/k2, both '# units' rate consts)
    formation = mdl.sbml.createReaction()
    formation.setId(mdl.ids.make(e.name + '_formation'))
    formation.setName(e.name + ' complex formation')
    formation.setFast(False)
    formation.setReversible(e.k2 != 0.0)

    enz_ref = formation.createReactant()
    enz_ref.setSpecies(sid_of[enz.path])
    enz_ref.setStoichiometry(1)
    enz_ref.setConstant(True)
    _species_reference(formation, sub_order, sub_count, sid_of, 'sub')
    cplx_ref = formation.createProduct()
    cplx_ref.setSpecies(sid_of[cplx.path])
    cplx_ref.setStoichiometry(1)
    cplx_ref.setConstant(True)

    s_term = _monomial(sub_order, sub_count, sid_of)
    fwd = f'k1*{sid_of[enz.path]}*{s_term}'
    formula = fwd
    params = [('k1', e.k1 * AVOGADRO ** (order_sub - 1))]
    if formation.getReversible():
        formula = f'({fwd}) - (k2*{sid_of[cplx.path]})'
        params.append(('k2', e.k2))
    ok1 = _set_kinetic_law(formation, formula, params, mdl)

    # Step 2: cplx -> E + P (irreversible, k3 aka kcat, intensive)
    catalysis = mdl.sbml.createReaction()
    catalysis.setId(mdl.ids.make(e.name + '_product_formation'))
    catalysis.setName(e.name + ' product formation')
    catalysis.setFast(False)
    catalysis.setReversible(False)

    csub_ref = catalysis.createReactant()
    csub_ref.setSpecies(sid_of[cplx.path])
    csub_ref.setStoichiometry(1)
    csub_ref.setConstant(True)
    enz_prd_ref = catalysis.createProduct()
    enz_prd_ref.setSpecies(sid_of[enz.path])
    enz_prd_ref.setStoichiometry(1)
    enz_prd_ref.setConstant(True)
    _species_reference(catalysis, prd_order, prd_count, sid_of, 'prd')

    ok2 = _set_kinetic_law(catalysis, f'k3*{sid_of[cplx.path]}',
                            [('k3', e.k3)], mdl)

    mdl.report.enz_reactions += int(ok1) + int(ok2)


# ----------------------------------------------------------------------
# Function-driven pools -> assignment / rate rules
# ----------------------------------------------------------------------
def _function_inputs(fn):
    """The elements feeding fn's x0, x1, ... variables, in x-index order --
    each x[i] is fed by exactly one 'nOut'->'input' connection (see
    reader.py's _Inputs / _make_function)."""
    inputs = []
    for i in range(fn.numVars):
        neigh = moose.element(fn.x[i]).neighbors['input']
        inputs.append(moose.element(neigh[0]) if neigh else None)
    return inputs


def _function_formula(fn, mdl):
    """Substitute x0,x1,... in fn.expr with the connected pool's amount*NA
    (matching the 'nOut' push convention -- see module docstring), returning
    a formula string, or None if some input is unwritten or unresolved."""
    inputs = _function_inputs(fn)
    expr = fn.expr

    def sub(m):
        i = int(m.group(1))
        if i >= len(inputs) or inputs[i] is None:
            raise UnsupportedModel(f'Function {fn.path!r}: x{i} has no connected input')
        elem = inputs[i]
        if elem.path not in mdl.species_id:
            raise UnsupportedModel(
                f'Function {fn.path!r}: input {elem.path!r} is not a written species')
        return f'({mdl.species_id[elem.path]}*{AVOGADRO!r})'

    try:
        return _TOKEN_RE.sub(sub, expr)
    except UnsupportedModel as exc:
        mdl.report.unsupported_add(str(exc))
        return None


def _create_rules(root, mdl):
    for p in _moose.wildcardFind(root.path + '/##[0][ISA=PoolBase]'):
        p = moose.element(p)
        if p.path not in mdl.species_id:
            continue
        rate_fns = [moose.element(f) for f in p.neighbors['increment']
                    if moose.element(f).isA['Function']]
        assign_fns = [moose.element(f) for f in p.neighbors['setN']
                      if moose.element(f).isA['Function']]
        has_reac = bool(p.neighbors['reac'])
        if not rate_fns and not assign_fns:
            continue
        if has_reac:
            mdl.report.unsupported_add(
                f'pool {p.path!r} is both a reaction participant and Function-driven; '
                'the Function contribution was not written')
            continue
        if rate_fns and assign_fns:
            mdl.report.unsupported_add(
                f'pool {p.path!r} has both a rate- and assignment-driving Function; '
                'only the rate rule was written')
            assign_fns = []

        sid = mdl.species_id[p.path]
        species = mdl.sbml.getSpecies(sid)
        if rate_fns:
            formula = _function_formula(rate_fns[0], mdl)
            if formula is None:
                continue
            formula = f'({formula})/{AVOGADRO!r}'  # d(amount)/dt from dn/dt
            rule = mdl.sbml.createRateRule()
            rule.setVariable(sid)
            math = libsbml.parseL3Formula(formula)
            if math is None:
                mdl.report.unsupported_add(
                    f'rate rule for {p.path!r}: could not parse formula {formula!r}')
                continue
            rule.setMath(math)
            species.setBoundaryCondition(True)
            species.setConstant(False)
            mdl.report.rate_rules += 1
        elif assign_fns:
            formula = _function_formula(assign_fns[0], mdl)
            if formula is None:
                continue
            formula = f'({formula})/{AVOGADRO!r}'  # n -> amount
            rule = mdl.sbml.createAssignmentRule()
            rule.setVariable(sid)
            math = libsbml.parseL3Formula(formula)
            if math is None:
                mdl.report.unsupported_add(
                    f'assignment rule for {p.path!r}: could not parse formula {formula!r}')
                continue
            rule.setMath(math)
            species.setBoundaryCondition(True)
            species.setConstant(False)
            mdl.report.assignment_rules += 1


# ----------------------------------------------------------------------
# public entry point
# ----------------------------------------------------------------------
def write(modelpath, filepath, report=None):
    if not _moose.exists(modelpath):
        raise UnsupportedModel(f'no such moose element: {modelpath!r}')
    restoreXreacs(modelpath)  # undo any fixXreacs proxy split before mapping
    root = moose.element(modelpath)

    if report is None:
        report = WriteReport(modelpath=modelpath, filepath=filepath)

    diffusive = _any_diffusive(root)
    xmlns = libsbml.SBMLNamespaces(3, 1)
    if diffusive:
        # Must be registered before the document is constructed (mirrors
        # writeSBML.py's 'groups' package registration): a namespace added
        # after construction does not instantiate the package's plugins.
        xmlns.addNamespace(_SPATIAL_NS, 'spatial')
    doc = libsbml.SBMLDocument(xmlns)
    if diffusive:
        # The spatial package spec mandates required="true" (it changes the
        # model's meaning), unlike most L3 packages.
        doc.setPackageRequired('spatial', True)
    model = doc.createModel()
    model.setId(_ID_RE.sub('_', root.name) or 'model')
    model.setTimeUnits('second')
    model.setExtentUnits('mole')
    model.setSubstanceUnits('mole')

    ud = model.createUnitDefinition()
    ud.setId('m3')
    u = ud.createUnit()
    u.setKind(libsbml.UNIT_KIND_METRE)
    u.setExponent(3)
    u.setScale(0)
    u.setMultiplier(1)
    model.setVolumeUnits('m3')

    mdl = _Model(model, report)
    _create_compartments(root, mdl)
    _create_species(root, mdl)
    if diffusive:
        _write_diffusion(root, mdl)
    _create_reactions(root, mdl)
    _create_mmenz(root, mdl)
    _create_enz(root, mdl)
    _create_rules(root, mdl)
    if diffusive:
        _mark_reactions_local(mdl)

    if libsbml.writeSBMLToFile(doc, filepath) != 1:
        raise UnsupportedModel(f'libsbml failed to write {filepath!r}')
    return report
