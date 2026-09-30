# reader.py --- clean-room SBML reader for MOOSE
#
# Reads standard SBML (targeting the curated BioModels corpus) and builds a
# MOOSE chemical model that can be simulated. Reactions whose kinetic law is
# recognized as mass-action / Michaelis-Menten map to native Reac / MMenz;
# everything else (arbitrary rate laws, rate rules, assignment rules) is
# compiled to MOOSE ``Function`` objects that feed the same ODE solver. See
# the package docstring for the overall design.

import os
import re

import libsbml
from moose import _moose

from ..base import ModelLoadError
from . import units
from .common import participants
from .identify import identify
from .mathconv import to_exprtk, UnsupportedMath
from .normalize import normalize
from .report import LoadReport


class SBMLValidationError(Exception):
    pass


class _Context:
    def __init__(self, root, report):
        self.root = root
        self.report = report
        self.compartment = {}       # sid -> CubeMesh
        self.comp_size = {}         # sid -> SBML size value (SBML units)
        self.comp_vol_m3 = {}       # sid -> compartment volume in m^3
        self.species = {}           # sid -> Pool/BufPool
        self.species_info = {}      # sid -> {'comp', 'substance_units', 'boundary', 'constant'}
        self.const_param = {}       # sid -> float (constant global parameters)
        self.variable = {}          # sid -> Pool/BufPool proxy holding a raw scalar value
        self.assign_targets = set() # ids on the LHS of an assignment rule
        self.rate_targets = set()   # ids on the LHS of a rate rule
        self.subst_factor = units.AVOGADRO
        self.unsupported_xcompt = False  # non-native cross-compartment coupling seen


# ----------------------------------------------------------------------
# per-Function input bookkeeping
# ----------------------------------------------------------------------
class _Inputs:
    """Collects the ordered list of MOOSE elements feeding one Function's
    x[] inputs, and hands out the exprtk token for each referenced symbol.

    Feeding a pool's value into a Function is done by connecting the pool's
    'nOut' to the Function's x[i] 'input' -- this looks like a push from a
    SrcFinfo that (per PoolBase.cpp) is otherwise only the reply half of the
    'reac' SharedFinfo pair with a Reac/Enz, but it is the convention
    ReadKkit.cpp's buildSumTotal uses (and the only one Stoich recognizes):
    when the Function and the pool it feeds are both compiled into the same
    Stoich (stoich.reacSystemPath spans both), Stoich's own compile step finds
    this exact 'x'/'nOut' wiring and absorbs the Function into an internal
    FuncTerm it drives directly -- bypassing the Function's own Clock tick
    entirely (confirmed: the live Function's .tick/.value stay at -2/0.0 after
    compile, yet the target pool tracks the correct value every step). A
    y-variable/'requestOut' pull (Table2's own convention) does NOT get this
    treatment and silently never updates the target under a real solver."""

    def __init__(self, ctx):
        self.ctx = ctx
        self.order = []          # list of moose elements (connected via nOut)
        self._index = {}         # id(elem) -> x index

    def _slot(self, elem):
        key = elem.path
        if key not in self._index:
            self._index[key] = len(self.order)
            self.order.append(elem)
        return self._index[key]

    def species_token(self, sid):
        info = self.ctx.species_info[sid]
        k = self._slot(self.ctx.species[sid])
        amount = f'x{k}/{self.ctx.subst_factor!r}'  # substance units
        if info['substance_units']:
            return f'({amount})'
        size = self.ctx.comp_size[info['comp']]
        return f'(({amount})/{size!r})'  # concentration in SBML units

    def variable_token(self, sid):
        k = self._slot(self.ctx.variable[sid])
        return f'x{k}'  # raw scalar (parameter-like), no unit scaling


def _resolver(inputs):
    ctx = inputs.ctx

    def resolve(name):
        if name in ctx.species:
            return inputs.species_token(name)
        if name in ctx.const_param:
            return repr(ctx.const_param[name])
        if name in ctx.compartment:
            return repr(ctx.comp_size[name])
        if name in ctx.variable:
            return inputs.variable_token(name)
        raise UnsupportedMath(f'unresolved symbol {name!r}')

    return resolve


def _make_function(path, expr, inputs):
    fn = _moose.Function(path)
    fn.expr = expr
    for i, elem in enumerate(inputs.order):
        _moose.connect(elem, 'nOut', fn.x[i], 'input')
    return fn


# ----------------------------------------------------------------------
# passes
# ----------------------------------------------------------------------
def _create_compartments(model, ctx):
    for i in range(model.getNumCompartments()):
        comp = model.getCompartment(i)
        sid = comp.getId()
        mesh = _moose.CubeMesh(f'{ctx.root.path}/{sid}')
        mesh.volume = units.volume(comp)
        ctx.compartment[sid] = mesh
        ctx.comp_size[sid] = comp.getSize() if comp.isSetSize() else 1.0
        ctx.comp_vol_m3[sid] = mesh.volume


def _create_species(model, ctx):
    for i in range(model.getNumSpecies()):
        sp = model.getSpecies(i)
        sid = sp.getId()
        comp_sid = sp.getCompartment()
        parent = ctx.compartment[comp_sid]
        boundary = sp.getBoundaryCondition()
        constant = sp.getConstant()
        # BufPool if the value is held/assigned (constant, boundary, or set by
        # an assignment rule); Pool if it is integrated (by reactions or a rate
        # rule). A rate rule wins even over boundaryCondition.
        held = (constant or boundary or sid in ctx.assign_targets)
        cls = _moose.BufPool if held and sid not in ctx.rate_targets else _moose.Pool
        pool = cls(f'{parent.path}/{sid}')
        pool.nInit = units.species_ninit(sp, model.getCompartment(comp_sid), ctx.subst_factor)
        ctx.species[sid] = pool
        ctx.species_info[sid] = {
            'comp': comp_sid,
            'substance_units': sp.getHasOnlySubstanceUnits(),
            'boundary': boundary,
            'constant': constant,
        }


def _create_parameters(model, ctx):
    """Constant parameters fold to literals; a parameter driven by a rule
    becomes a 'variable' proxy pool (Pool if rate-ruled so it integrates,
    BufPool if assignment-ruled so it is overwritten each step). Proxies live
    inside the first compartment so they fall within a solver's scope."""
    host = next(iter(ctx.compartment.values())).path
    for i in range(model.getNumParameters()):
        prm = model.getParameter(i)
        sid = prm.getId()
        value = prm.getValue() if prm.isSetValue() else 0.0
        if sid in ctx.rate_targets:
            proxy = _moose.Pool(f'{host}/{sid}')
            proxy.nInit = value
            ctx.variable[sid] = proxy
        elif sid in ctx.assign_targets:
            proxy = _moose.BufPool(f'{host}/{sid}')
            proxy.nInit = value
            ctx.variable[sid] = proxy
        else:
            ctx.const_param[sid] = value


def _read_diffusion(model, ctx):
    """Read SBML-spatial diffusion coefficients into pool.diffConst.

    In the SBML Level 3 *spatial* package a diffusion constant is a Parameter
    carrying a DiffusionCoefficient that names the species it applies to. We
    copy the (isotropic) value onto the MOOSE pool so it is not lost. NOTE: this
    only takes physical effect once the spatial *geometry* is turned into a
    multi-voxel mesh -- until then every compartment is a single well-mixed
    voxel and diffConst is inert. That geometry mapping is not built yet, so a
    spatial model is reported as simulated well-mixed."""
    plug = model.getPlugin('spatial')
    if plug is None:
        return
    for i in range(model.getNumParameters()):
        p = model.getParameter(i)
        sp = p.getPlugin('spatial')
        if sp is None or not sp.isSetDiffusionCoefficient():
            continue
        dc = sp.getDiffusionCoefficient()
        sid = dc.getVariable()
        pool = ctx.species.get(sid)
        if pool is None:
            continue
        if dc.getType() != libsbml.SPATIAL_DIFFUSIONKIND_ISOTROPIC:
            ctx.report.unsupported_add(
                f'anisotropic/tensor diffusion for {sid!r} reduced to isotropic')
        pool.diffConst = p.getValue() if p.isSetValue() else 0.0
    geom = plug.getGeometry() if plug.isSetGeometry() else None
    if geom is not None and geom.getNumGeometryDefinitions() > 0:
        ctx.report.unsupported_add(
            'SBML-spatial geometry (coordinate systems / domains) is not mapped '
            'to a MOOSE mesh yet; the model is simulated well-mixed and '
            'diffusion constants have no spatial effect')


def _classify_rules(model, ctx):
    for i in range(model.getNumRules()):
        rule = model.getRule(i)
        if rule.isAssignment():
            ctx.assign_targets.add(rule.getVariable())
        elif rule.isRate():
            ctx.rate_targets.add(rule.getVariable())


def _reac_compartments(reac, ctx):
    """Set of compartment-ids the reaction's substrates and products live in."""
    subs, prds, _ = participants(reac)
    comps = set()
    for sid, _ in list(subs) + list(prds):
        info = ctx.species_info.get(sid)
        if info is not None:
            comps.add(info['comp'])
    return comps


def _reaction_home(reac, ctx):
    """(mesh, compartment-id) the reaction is created in. For a single-
    compartment reaction that is its compartment; for a cross-compartment
    reaction the smallest-volume participating compartment -- the numerically
    stable placement recommended by moose-examples/crossComptSimpleReac. The
    rate constants are set in volume-independent number space (see
    _num_massaction), so this choice does not affect the kinetics."""
    comps = _reac_compartments(reac, ctx)
    if not comps:
        return None, None
    cid = min(comps, key=lambda c: ctx.comp_vol_m3[c])
    return ctx.compartment[cid], cid


def _elem_compartment(elem, ctx):
    """Compartment-id whose mesh contains this MOOSE element, or None."""
    path = elem.path
    for cid, mesh in ctx.compartment.items():
        mp = mesh.path
        if path == mp or path.startswith(mp + '/'):
            return cid
    return None


def _spans_compartments(kind, name, target_comp, inputs, ctx):
    """True (and reported unsupported) if a Function reading ``inputs`` and
    writing ``target_comp`` would have to reach across compartments -- a MOOSE
    Function reads pools by index within one solver's scope, so a foreign read
    is out of bounds and would crash the multi-compartment solver."""
    comps = set(_elem_compartment(e, ctx) for e in inputs.order)
    comps.discard(None)
    if target_comp is not None:
        comps.add(target_comp)
    if len(comps) > 1:
        ctx.report.unsupported_add(
            f'{kind} for {name!r} spans compartments {sorted(comps)}; a MOOSE '
            'Function cannot read pools outside its own solver')
        ctx.unsupported_xcompt = True
        return True
    return False


def _inv(sid, ctx, substance_scale):
    """Factor relating a species' rate-law value to its MOOSE concentration:
    value = inv * conc. (Inverse of the value->conc scale.)"""
    info = ctx.species_info[sid]
    comp = info['comp']
    if info['substance_units']:            # value is an amount
        return ctx.comp_vol_m3[comp] / substance_scale
    size_scale = ctx.comp_vol_m3[comp] / ctx.comp_size[comp]  # m^3 per size unit
    return size_scale / substance_scale


def _si_massaction(result, reac, home_cid, ctx):
    """Convert value-space Kf/Kb to SI (mM-based) constants."""
    ss = ctx.subst_factor / units.AVOGADRO           # substance_scale (mol/unit)
    pref = ss / ctx.comp_vol_m3[home_cid]            # substance_scale / V_home[m^3]
    subs, prds, _ = participants(reac)
    kf = result['Kf_val'] * pref
    kb = result['Kb_val'] * pref
    for sid, st in subs:
        kf *= _inv(sid, ctx, ss) ** st
    for sid, st in prds:
        kb *= _inv(sid, ctx, ss) ** st
    for c in result.get('catalysts', set()):
        kf *= _inv(c, ctx, ss)
        kb *= _inv(c, ctx, ss)
    return kf, kb


def _si_mmenz(result, subs0, home_cid, ctx):
    """Convert value-space kcat/Km to SI (kcat 1/s, Km in mM)."""
    ss = ctx.subst_factor / units.AVOGADRO
    kcat = result['kcat_val'] * _inv(result['enzyme'], ctx, ss) * ss / ctx.comp_vol_m3[home_cid]
    km = result['Km_val'] / _inv(subs0, ctx, ss)
    return kcat, km


def _synthesize_enzyme(ctx, comp_sid):
    """A Michaelis-Menten rate law that lumps a constant, untracked enzyme
    concentration into its Vmax (V*S/(Km+S), no declared modifier -- see
    symbolic._michaelis_menten's docstring for why real curated SBML does
    this) still maps to a native MMenz: invent a BufPool held at the
    concentration that makes kcat*E reconstruct exactly the same Vmax, with
    the enzyme's *value-space* reading fixed at 1 by construction -- so
    _si_mmenz's existing kcat/Km conversion (which only depends on the
    enzyme's compartment and substance_units, never its stored value) needs
    no special-casing. Returns the new species id."""
    n = 0
    sid = '_impliedEnz0'
    while sid in ctx.species_info:
        n += 1
        sid = f'_impliedEnz{n}'
    ctx.species_info[sid] = {
        'comp': comp_sid,
        'substance_units': False,
        'boundary': True,
        'constant': True,
    }
    ss = ctx.subst_factor / units.AVOGADRO
    pool = _moose.BufPool(f'{ctx.compartment[comp_sid].path}/{sid}')
    pool.concInit = 1.0 / _inv(sid, ctx, ss)  # value-space reading == 1
    ctx.species[sid] = pool
    return sid


def _num_massaction(result, reac, ctx):
    """Number-space rate constants (numKf/numKb, units 1/s scaled by molecule
    counts) for a mass-action reaction. Unlike the concentration-space Kf/Kb,
    these do not reference any single compartment volume, so they are correct
    for a cross-compartment reaction whose substrates and products sit in
    different volumes -- and fixXreacs preserves numKf/numKb verbatim when it
    splits the reaction. Derivation: MOOSE flux [molecules/s] must equal the
    SBML extensive rate [substance/s] times subst_factor, giving
    numKf = Kf_val * subst_factor * prod_i f(species_i)^stoich_i, where the
    per-species factor f folds one power of subst_factor back out (and the
    SBML compartment size for concentration species)."""
    sf = ctx.subst_factor
    subs, prds, _ = participants(reac)

    def f(sid):
        info = ctx.species_info[sid]
        if info['substance_units']:          # rate law sees an amount
            return 1.0 / sf
        return 1.0 / (ctx.comp_size[info['comp']] * sf)  # ...sees a concentration

    numkf = result['Kf_val'] * sf
    for sid, st in subs:
        numkf *= f(sid) ** st
    numkb = result['Kb_val'] * sf
    for sid, st in prds:
        numkb *= f(sid) ** st
    # A catalyst enters both monomials once (M -> M + P), unconsumed.
    for c in result.get('catalysts', ()):
        fc = f(c)
        numkf *= fc
        numkb *= fc
    return numkf, numkb


def _wire(mreac, reac, ctx):
    """Connect substrate/product pools to a Reac/MMenz, honoring stoichiometry."""
    subs, prds, _ = participants(reac)
    for field, refs in (('sub', subs), ('prd', prds)):
        for sid, st in refs:
            pool = ctx.species.get(sid)
            if pool is not None:
                for _ in range(int(st)):
                    _moose.connect(mreac, field, pool, 'reac', 'OneToOne')


def _reac_id(reac, index):
    return reac.getIdAttribute() if reac.isSetIdAttribute() else f'reaction_{index}'


def _create_reactions(model, ctx):
    """Recognize mass-action / Michaelis-Menten kinetics numerically and emit
    native Reac / MMenz; everything else goes to the Function fallback."""
    variable_names = set(ctx.variable)
    fallback = []
    for r in range(model.getNumReactions()):
        reac = model.getReaction(r)
        if reac.getFast():
            ctx.report.unsupported_add(f'fast reaction {reac.getId()!r} (no QSS handling)')
        home, home_cid = _reaction_home(reac, ctx)
        xcompt = len(_reac_compartments(reac, ctx)) > 1
        result = None
        if home is not None:
            result = identify(reac, ctx.const_param, ctx.comp_size, variable_names)
        # A cross-compartment reaction has to become a native Reac/MMenz: the
        # Function fallback reads pools by index within one solver's scope and
        # cannot span compartments (it would read out of bounds and crash).
        if xcompt and (result is None or result['kind'] != 'massaction'):
            ctx.report.unsupported_add(
                f'cross-compartment reaction {reac.getId()!r} is not native '
                'mass-action; no Function fallback across compartments')
            ctx.unsupported_xcompt = True
            continue
        if result is None:
            fallback.append(reac)
        elif result['kind'] == 'massaction':
            mr = _moose.Reac(f'{home.path}/{_reac_id(reac, r)}')
            if xcompt:
                # Volume-independent number-space constants; fixXreacs preserves
                # numKf/numKb when it splits the reaction across the junction.
                mr.numKf, mr.numKb = _num_massaction(result, reac, ctx)
            else:
                mr.Kf, mr.Kb = _si_massaction(result, reac, home_cid, ctx)
            _wire(mr, reac, ctx)
            # A catalyst (modifier that enters the rate multiplicatively) is
            # wired as substrate AND product so it drives the rate without
            # being consumed.
            for cat in result.get('catalysts', ()):
                pool = ctx.species.get(cat)
                if pool is not None:
                    _moose.connect(mr, 'sub', pool, 'reac', 'OneToOne')
                    _moose.connect(mr, 'prd', pool, 'reac', 'OneToOne')
            ctx.report.reactions_native += 1
        elif result['kind'] == 'mmenz':
            if result['enzyme'] is None:
                # Lumped-Vmax law, no declared modifier (see
                # symbolic._michaelis_menten) -- still native, with an
                # invented constant-concentration enzyme pool standing in
                # for the untracked one the SBML file folded into Vmax.
                result['enzyme'] = _synthesize_enzyme(ctx, home_cid)
            if result['enzyme'] in ctx.species:
                enzpool = ctx.species[result['enzyme']]
                mm = _moose.MMenz(f'{enzpool.path}/{_reac_id(reac, r)}')
                mm.kcat, mm.Km = _si_mmenz(result, reac.getReactant(0).getSpecies(),
                                           home_cid, ctx)
                _moose.connect(enzpool, 'nOut', mm, 'enzDest')
                _wire(mm, reac, ctx)
                ctx.report.reactions_native += 1
            else:
                fallback.append(reac)
        else:
            fallback.append(reac)
    _build_fallback_functions(fallback, ctx)


def _build_fallback_functions(reactions, ctx):
    """General-ODE assembly for reactions with non-native rate laws: per
    reacting species build one Function giving dn/dt = subst_factor *
    Sum_j netstoich_ij * KL_j."""
    contrib = {}  # sid -> list of (netstoich, reaction)
    for reac in reactions:
        subs, prds, _ = participants(reac)
        net = {}
        for sid, st in subs:
            net[sid] = net.get(sid, 0.0) - st
        for sid, st in prds:
            net[sid] = net.get(sid, 0.0) + st
        for sid, ns in net.items():
            if ns == 0.0:
                continue
            info = ctx.species_info.get(sid)
            if info is None or info['boundary'] or info['constant']:
                continue  # not altered by reactions
            contrib.setdefault(sid, []).append((ns, reac))

    for sid, terms in contrib.items():
        inputs = _Inputs(ctx)
        resolve = _resolver(inputs)
        try:
            pieces = []
            for ns, reac in terms:
                kl = reac.getKineticLaw()
                if kl is None or kl.getMath() is None:
                    raise UnsupportedMath(f'reaction {reac.getId()!r} has no kinetic law')
                pieces.append(f'{ns!r}*({to_exprtk(kl.getMath(), resolve)})')
        except UnsupportedMath as e:
            ctx.report.unsupported_add(
                f'species {sid!r} derivative not built: {e}')
            continue
        if _spans_compartments('derivative', sid, ctx.species_info[sid]['comp'],
                               inputs, ctx):
            continue
        expr = f'{ctx.subst_factor!r}*({" + ".join(pieces)})'
        pool = ctx.species[sid]
        fn = _make_function(f'{pool.path}/dot', expr, inputs)
        _moose.connect(fn, 'valueOut', pool, 'increment')
        ctx.report.reactions_function += 1


def _create_rules(model, ctx):
    for r in range(model.getNumRules()):
        rule = model.getRule(r)
        if rule.isAlgebraic():
            ctx.report.unsupported_add('algebraic rule (no DAE solver in MOOSE)')
            continue
        var = rule.getVariable()
        math = rule.getMath()
        if math is None:
            continue
        inputs = _Inputs(ctx)
        try:
            body = to_exprtk(math, _resolver(inputs))
        except UnsupportedMath as e:
            ctx.report.unsupported_add(f'rule for {var!r}: {e}')
            continue

        target, scale, _is_species = _rule_target(var, ctx)
        if target is None:
            ctx.report.unsupported_add(f'rule target {var!r} not found')
            continue
        if _spans_compartments('rule', var, _elem_compartment(target, ctx),
                               inputs, ctx):
            continue

        if rule.isAssignment():
            expr = body if scale == 1.0 else f'{scale!r}*({body})'
            fn = _make_function(f'{target.path}/assign', expr, inputs)
            _moose.connect(fn, 'valueOut', target, 'setN')
            ctx.report.assignment_rules += 1
        elif rule.isRate():
            expr = body if scale == 1.0 else f'{scale!r}*({body})'
            fn = _make_function(f'{target.path}/rate', expr, inputs)
            _moose.connect(fn, 'valueOut', target, 'increment')
            ctx.report.rate_rules += 1


def _rule_target(var, ctx):
    """Resolve a rule variable to (moose element, n-scale factor, is_species).
    The scale converts an SBML value/derivative into MOOSE number units."""
    if var in ctx.species:
        info = ctx.species_info[var]
        scale = ctx.subst_factor
        if not info['substance_units']:
            scale = ctx.subst_factor * ctx.comp_size[info['comp']]
        return ctx.species[var], scale, True
    if var in ctx.variable:
        return ctx.variable[var], 1.0, False
    return None, 1.0, False


def _detect_unsupported(model, ctx):
    if model.getNumEvents() > 0:
        ctx.report.unsupported_add(
            f'{model.getNumEvents()} event(s): MOOSE has no discrete-event support')


def _position_compartments(compts):
    """Chain compartments along x so successive CubeMeshes abut (shifting both
    x0 and x1 preserves each width, hence each volume). Adjacent meshes are
    what buildMeshJunctions needs to couple diffusion. Mirrors
    moose.chemUtil.add_Delete_ChemicalSolver.positionCompt."""
    for i in range(len(compts) - 1):
        compts[i + 1].x1 += compts[i].x1
        compts[i + 1].x0 += compts[i].x1


def _setup_solver(ctx, solver):
    """Add one Ksolve(+Dsolve)+Stoich per compartment. For multi-compartment
    models the cross-compartment reactions are first split by fixXreacs into
    per-compartment halves that talk to local proxy pools; the two solvers then
    exchange those proxies (Ksolve<->Ksolve), and a Dsolve mesh junction couples
    any diffusing pools. See moose-examples/crossComptSimpleReac and
    moose.chemUtil setCompartmentSolver."""
    if solver == 'ee':
        return
    compts = list(ctx.compartment.values())
    multi = len(compts) > 1
    if multi:
        # A non-native cross-compartment coupling would leave a hole in the ODEs
        # (no Function can cross compartments), so refuse to build a solver that
        # would silently simulate the wrong system.
        if ctx.unsupported_xcompt:
            ctx.report.unsupported_add(
                'solver not built: model has cross-compartment coupling that '
                'is not native mass-action')
            return
        from moose.fixXreacs import fixXreacs
        compts = sorted(compts, key=lambda c: c.volume)  # smallest first
        _position_compartments(compts)
        fixXreacs(ctx.root.path)

    for comp in compts:
        if solver == 'gssa':
            ksolve = _moose.Gsolve(f'{comp.path}/ksolve')
            # GSSA is event-driven: a Function's contribution (rate/assignment
            # rule, or the non-native fallback ODE) has no reaction event of
            # its own to trigger a re-check, so it would go stale between
            # unrelated events unless polled on a clock (see
            # moose-examples/snippets/funcInputToPools.py). Skip the cost when
            # this compartment has no Function to poll.
            if _moose.wildcardFind(comp.path + '/##[ISA=Function]'):
                ksolve.useClockedUpdate = True
        else:
            ksolve = _moose.Ksolve(f'{comp.path}/ksolve')
            # Many BioModels are stiff; LSODA (like RoadRunner's CVODE) handles
            # them where the default explicit RKF45 diverges. Only for a single
            # compartment though: LSODA does not integrate the cross-compartment
            # proxy exchange that couples a multi-compartment model.
            if not multi:
                try:
                    ksolve.method = 'lsoda'
                except Exception:
                    pass
        dsolve = _moose.Dsolve(f'{comp.path}/dsolve') if multi else None
        stoich = _moose.Stoich(f'{comp.path}/stoich')
        stoich.ksolve = ksolve
        if dsolve is not None:
            stoich.dsolve = dsolve
        stoich.compartment = comp
        stoich.reacSystemPath = comp.path + '/##'  # last: this triggers the build
        # NOTE: a Function wired x[i]<-nOut-<pool and valueOut->pool's
        # increment/setN (see _make_function) needs no useClock of its own:
        # Stoich's compile step above recognizes that exact wiring within its
        # path and absorbs the Function into an internal FuncTerm it drives
        # directly, independent of the Function's own (now -2/unscheduled)
        # Clock tick. Confirmed by direct test against ReadKkit.cpp's
        # buildSumTotal, which uses the identical wiring with no useClock.

    if multi:
        # Couple diffusion across each adjacent (volume-sorted) mesh pair. Pure
        # reaction transport already works through the Ksolve proxy exchange, so
        # a junction that finds no shared voxels is harmless -- guard it anyway.
        dsolves = [_moose.element(c.path + '/dsolve') for c in compts]
        for i in range(len(dsolves) - 1):
            try:
                dsolves[i + 1].buildMeshJunctions(dsolves[i])
            except Exception as e:
                ctx.report.warnings.append(
                    f'mesh junction {compts[i].name}<->{compts[i + 1].name} failed: {e}')


# ----------------------------------------------------------------------
# public entry point
# ----------------------------------------------------------------------
_NAME_RE = re.compile(r'[^A-Za-z0-9_]+')


def _default_model_name(model, filepath):
    """A moose-legal name for ``model``, for the default loadpath: its SBML
    id if set (already SId-constrained -- letters/digits/underscore, not
    starting with a digit -- so safe to use as-is), else its human-readable
    name (sanitized), else the source filename's basename (sanitized)."""
    name = model.getId() if model.isSetId() else ''
    if name:
        return name
    name = model.getName() if model.isSetName() else ''
    if not name:
        name = os.path.splitext(os.path.basename(filepath))[0]
    name = _NAME_RE.sub('_', name).strip('_')
    if not name:
        name = 'model'
    if name[0].isdigit():
        name = '_' + name
    return name


def read(filepath, loadpath=None, solver='gsl', validate=True):
    """Load ``filepath`` (an SBML document) into a new MOOSE subtree rooted
    at ``loadpath``.

    ``loadpath`` defaults to ``/library/{model_name}``, where ``model_name``
    is taken from the SBML model's ``id`` (or, failing that, its ``name``,
    or the source filename) -- see :func:`_default_model_name`.

    ``solver`` selects the chemical solver built over the result: ``'gsl'``
    (default) for deterministic ODE integration via Ksolve, ``'gssa'`` for
    the stochastic Gillespie solver via Gsolve, or ``'ee'`` to skip solver
    setup entirely (the caller is responsible for scheduling). ``validate``
    controls whether libsbml errors on the document abort the load
    (:class:`SBMLValidationError`) or are ignored.

    Returns ``(element, report)``: the loaded root element, and a
    :class:`~.report.LoadReport` recording what could not be represented
    faithfully -- see the package docstring for the overall design and its
    hard limits.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f'No such file: {filepath}')
    doc = libsbml.readSBML(filepath)
    if doc is None:
        raise ModelLoadError('Empty SBML doc', filepath, loadpath)
    if validate and doc.getNumErrors(libsbml.LIBSBML_SEV_ERROR) > 0:
        errs = [doc.getError(i).getMessage()
                for i in range(doc.getNumErrors())
                if doc.getError(i).getSeverity() >= libsbml.LIBSBML_SEV_ERROR]
        raise SBMLValidationError('\n'.join(errs))

    if loadpath is None:
        peek = doc.getModel()
        if peek is None:
            raise ModelLoadError('Invalid SBML: no model element', filepath, loadpath)
        loadpath = f'/library/{_default_model_name(peek, filepath)}'
        if not _moose.exists('/library'):
            _moose.Neutral('/library')

    report = LoadReport(filepath=filepath, loadpath=loadpath)
    report.normalized, skipped = normalize(doc)
    report.warnings += skipped

    model = doc.getModel()
    if model is None:
        raise ModelLoadError('Invalid SBML: no model element', filepath, loadpath)
    if model.getNumCompartments() == 0:
        raise ModelLoadError('Model has no compartments', filepath, loadpath)

    root = _moose.Neutral(loadpath)
    ctx = _Context(root, report)
    # SI: n = (SBML amount) * NA * substance_scale, volumes in m^3 (units.py).
    ctx.subst_factor = units.AVOGADRO * units.substance_scale(model)

    _classify_rules(model, ctx)
    _create_compartments(model, ctx)
    _create_species(model, ctx)
    _create_parameters(model, ctx)
    _read_diffusion(model, ctx)
    _create_reactions(model, ctx)
    _create_rules(model, ctx)
    _detect_unsupported(model, ctx)
    _setup_solver(ctx, solver)

    element = _moose.element(loadpath)
    print(f"Loaded SBML model '{filepath}' into '{element.path}'")
    return element, report
