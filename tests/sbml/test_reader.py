"""Tests for the clean-room SBML reader (moose.io.sbml).

These exercise the general SBML->ODE path end-to-end: load a model, build the
MOOSE object graph, simulate, and check the trajectory. Where libRoadRunner is
installed we compare against it as an independent reference; otherwise we fall
back to analytic / conservation checks that need no external simulator.
"""
import os

import numpy as np
import pytest

import moose
from moose.io.sbml import SBMLHandler

HERE = os.path.dirname(os.path.abspath(__file__))


def _sim(root, species_path, runtime, npts=200):
    el = moose.element(species_path)
    tab = moose.Table2(root + '/_tab_' + el.name)
    moose.connect(tab, 'requestOut', el, 'getConc')
    moose.setClock(tab.tick, runtime / npts)
    moose.reinit()
    moose.start(runtime)
    v = np.array(tab.vector)
    return np.linspace(0, runtime, len(v)), v


def test_massaction_decay_and_conservation():
    """00001-sbml-l3v1: S1 -> S2 with rate k1*S1 (k1=1). S1 must decay as
    exp(-t) and S1+S2 must be conserved."""
    h = SBMLHandler()
    h.read(os.path.join(HERE, '00001-sbml-l3v1.xml'), '/decay')
    assert h.report.fully_supported

    t, s1 = _sim('/decay', '/decay/compartment/S1', 5.0)
    _, s2 = _sim('/decay', '/decay/compartment/S2', 5.0)
    # S1 decays as exp(-k1*t) with k1 = 1: log(S1) is linear with slope -1.
    slope = np.polyfit(t, np.log(s1), 1)[0]
    assert abs(slope - (-1.0)) < 1e-2
    # mass conservation: S1 + S2 constant
    total = s1 + s2
    assert np.allclose(total, total[0], rtol=1e-3)


def test_kholodenko_loads_and_runs():
    """A real MAPK-cascade model must load, build pools, and simulate to a
    finite, non-negative trajectory."""
    h = SBMLHandler()
    h.read(os.path.join(HERE, 'Kholodenko.sbml'), '/mapk')
    pools = moose.wildcardFind('/mapk/##[ISA=PoolBase]')
    assert len(pools) > 0
    _, v = _sim('/mapk', pools[0].path, 100.0)
    assert np.all(np.isfinite(v))
    assert np.all(v >= -1e-9)


def test_report_flags_events_unsupported(tmp_path):
    """Events have no MOOSE equivalent and must be reported, not silently
    dropped."""
    sbml = '''<?xml version="1.0" encoding="UTF-8"?>
<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4">
  <model id="ev">
    <listOfCompartments><compartment id="c" size="1"/></listOfCompartments>
    <listOfSpecies>
      <species id="S" compartment="c" initialConcentration="1"/>
    </listOfSpecies>
    <listOfEvents>
      <event id="e"><trigger><math xmlns="http://www.w3.org/1998/Math/MathML">
        <apply><gt/><csymbol encoding="text"
          definitionURL="http://www.sbml.org/sbml/symbols/time">t</csymbol>
          <cn>5</cn></apply></math></trigger>
        <listOfEventAssignments>
          <eventAssignment variable="S"><math
            xmlns="http://www.w3.org/1998/Math/MathML"><cn>0</cn></math>
          </eventAssignment>
        </listOfEventAssignments>
      </event>
    </listOfEvents>
  </model>
</sbml>'''
    p = tmp_path / 'ev.xml'
    p.write_text(sbml)
    h = SBMLHandler()
    h.read(str(p), '/ev')
    assert any('event' in u.lower() for u in h.report.unsupported)


def test_massaction_maps_to_native():
    """The mass-action decay model must be recognized symbolically and built as
    a native Reac, not the Function fallback."""
    h = SBMLHandler()
    h.read(os.path.join(HERE, '00001-sbml-l3v1.xml'), '/nat')
    assert h.report.reactions_native >= 1
    assert h.report.reactions_function == 0
    assert moose.wildcardFind('/nat/##[ISA=Reac]')


def test_symbolic_catalyst_extraction():
    """A reaction S -> P with rate k*E*S (E a modifier) must be recognized as
    mass-action with E identified as a catalyst and Kf extracted exactly."""
    import libsbml
    from moose.io.sbml import symbolic

    doc = libsbml.SBMLDocument(3, 1)
    m = doc.createModel()
    c = m.createCompartment()
    c.setId('c'); c.setConstant(True); c.setSize(1.0); c.setSpatialDimensions(3)
    for sid in ('S', 'P', 'E'):
        sp = m.createSpecies()
        sp.setId(sid); sp.setCompartment('c'); sp.setInitialConcentration(1.0)
        sp.setConstant(False); sp.setBoundaryCondition(False)
        sp.setHasOnlySubstanceUnits(False)
    r = m.createReaction()
    r.setId('r'); r.setReversible(False)
    ref = r.createReactant(); ref.setSpecies('S'); ref.setStoichiometry(1); ref.setConstant(True)
    prd = r.createProduct(); prd.setSpecies('P'); prd.setStoichiometry(1); prd.setConstant(True)
    r.createModifier().setSpecies('E')
    kl = r.createKineticLaw()
    kl.setMath(libsbml.parseL3Formula('k * E * S'))
    p = kl.createLocalParameter(); p.setId('k'); p.setValue(0.5)

    res = symbolic.analyze(r, {'c': 1.0})
    assert res is not None and res['kind'] == 'massaction'
    assert res['catalysts'] == {'E'}
    assert abs(res['Kf_val'] - 0.5) < 1e-9
    assert abs(res['Kb_val']) < 1e-12


@pytest.mark.parametrize('fname', ['00001-sbml-l3v1.xml', 'Kholodenko.sbml'])
def test_matches_roadrunner(fname):
    """When libRoadRunner is available, MOOSE trajectories must agree with it
    for these mass-action / Michaelis-Menten models."""
    rr = pytest.importorskip('roadrunner')
    rr.Logger.setLevel(rr.Logger.LOG_FATAL)
    path = os.path.join(HERE, fname)

    import libsbml
    model = libsbml.readSBML(path).getModel()
    sids = [model.getSpecies(i).getId() for i in range(model.getNumSpecies())]
    runtime = 100.0

    r = rr.RoadRunner(path)
    r.timeCourseSelections = ['time'] + ['[%s]' % s for s in sids]
    ref = r.simulate(0, runtime, 201)

    # MOOSE reports concentration in SI mM; RoadRunner in the model's own units.
    # Convert: mM = value * substance_scale / size_scale.
    from moose.io.sbml import units as sbml_units
    ss = sbml_units.substance_scale(model)

    root = '/rr_' + fname.split('.')[0].replace('-', '_')
    SBMLHandler().read(path, root)
    grid = np.linspace(0, runtime, 40)
    for i, sid in enumerate(sids):
        el = [e for e in moose.wildcardFind('%s/##/%s[0]' % (root, sid))
              if 'Pool' in e.className]
        if not el:
            continue
        comp = model.getCompartment(model.getSpecies(sid).getCompartment())
        cfac = ss / sbml_units.size_scale(comp)
        t, v = _sim(root, el[0].path, runtime)
        rvals = np.interp(grid, ref[:, 0], ref[:, i + 1]) * cfac
        mvals = np.interp(grid, t, v)
        denom = max(np.max(np.abs(rvals)), 1e-12)
        assert np.max(np.abs(rvals - mvals)) / denom < 2e-2, sid


# ----------------------------------------------------------------------
# multi-compartment: cross-compartment transport reactions
# ----------------------------------------------------------------------
def _two_compartment_transport(reversible=False, native=True):
    """Build an in-memory SBML doc: X in compartment A moves to Y in
    compartment B. With native=True the law is mass-action (k*A*X[, -kb*B*Y]);
    with native=False it is a saturating (non-mass-action) law that cannot map
    to a native Reac and so has no cross-compartment Function fallback."""
    import libsbml
    doc = libsbml.SBMLDocument(3, 1)
    m = doc.createModel()
    m.setId('xport')
    for cid, size in (('A', 2.0), ('B', 5.0)):
        c = m.createCompartment()
        c.setId(cid); c.setConstant(True); c.setSize(size); c.setSpatialDimensions(3)
    for sid, comp, conc in (('X', 'A', 3.0), ('Y', 'B', 0.0)):
        s = m.createSpecies()
        s.setId(sid); s.setCompartment(comp); s.setInitialConcentration(conc)
        s.setConstant(False); s.setBoundaryCondition(False)
        s.setHasOnlySubstanceUnits(False)
    r = m.createReaction()
    r.setId('xfer'); r.setReversible(reversible); r.setFast(False)
    ref = r.createReactant(); ref.setSpecies('X'); ref.setStoichiometry(1); ref.setConstant(True)
    prd = r.createProduct(); prd.setSpecies('Y'); prd.setStoichiometry(1); prd.setConstant(True)
    kl = r.createKineticLaw()
    if native:
        law = 'k * A * X' + (' - kb * B * Y' if reversible else '')
    else:
        law = 'k * A * X / (Km + X)'          # saturating -> not mass-action
        p = kl.createLocalParameter(); p.setId('Km'); p.setValue(1.0)
    kl.setMath(libsbml.parseL3Formula(law))
    p = kl.createLocalParameter(); p.setId('k'); p.setValue(0.3)
    if reversible:
        p = kl.createLocalParameter(); p.setId('kb'); p.setValue(0.05)
    return doc


def test_crosscompartment_transport_conserves(tmp_path):
    """Irreversible transport X(A)->Y(B) with law k*A*X must (a) build a native
    cross-compartment Reac split by fixXreacs into local proxy pools, (b) let X
    decay exactly as exp(-k t) [d(amount)/dt = -k*amount], and (c) conserve the
    total molecule count across the two compartments."""
    import libsbml
    p = tmp_path / 'xport.xml'
    libsbml.writeSBMLToFile(_two_compartment_transport(), str(p))

    h = SBMLHandler()
    h.read(str(p), '/xp')
    assert h.report.reactions_native == 1
    assert not h.report.unsupported, h.report.unsupported
    # fixXreacs made a local proxy for the foreign product.
    assert moose.wildcardFind('/xp/##/Y_xfer_#')

    eX = [e for e in moose.wildcardFind('/xp/##/X[0]') if 'Pool' in e.className][0]
    eY = [e for e in moose.wildcardFind('/xp/##/Y[0]')
          if 'Pool' in e.className and '_xfer_' not in e.name][0]
    n0 = eX.nInit + eY.nInit
    # The cross-compartment proxy exchange is operator-split at the solver tick,
    # so accuracy needs a fine dt (see reader docstring).
    for tck in range(20):
        moose.setClock(tck, 0.002)
    tab = moose.Table2('/xp/_tabX')
    moose.connect(tab, 'requestOut', eX, 'getConc')
    moose.setClock(tab.tick, 0.05)
    moose.reinit()
    moose.start(5.0)
    v = np.array(tab.vector)
    t = np.linspace(0, 5.0, len(v))
    slope = np.polyfit(t, np.log(v / v[0]), 1)[0]
    assert abs(slope - (-0.3)) < 1e-2, slope           # exp(-k t) decay
    assert abs((eX.n + eY.n) - n0) / n0 < 1e-2, (eX.n + eY.n, n0)  # conserved


def test_noncnative_crosscompartment_rejected(tmp_path):
    """A cross-compartment reaction with a non-mass-action law cannot become a
    native Reac and must not silently become a (compartment-crossing) Function:
    it is reported unsupported and no solver is built."""
    import libsbml
    p = tmp_path / 'xport_nonnative.xml'
    libsbml.writeSBMLToFile(_two_compartment_transport(native=False), str(p))

    h = SBMLHandler()
    h.read(str(p), '/xpn')
    assert any('cross-compartment' in u for u in h.report.unsupported), h.report.unsupported
    assert not moose.wildcardFind('/xpn/##[ISA=Stoich]')  # solver refused


def test_gorlich_multicompartment_native():
    """A real two-compartment model (Gorlich2003 RanGTP gradient): every
    reaction -- including the two nucleus<->cytoplasm transport reactions --
    maps to a native Reac, the model builds a per-compartment solver, and it
    simulates to a finite, non-negative trajectory."""
    path = os.path.join(HERE, 'Gorlich2003_RanGTP.xml')
    if not os.path.isfile(path):
        pytest.skip('Gorlich2003 fixture not present')
    h = SBMLHandler()
    h.read(path, '/ran')
    assert h.report.reactions_native == 9
    assert h.report.reactions_function == 0
    assert not h.report.unsupported, h.report.unsupported
    assert len(moose.wildcardFind('/ran/##[ISA=ChemCompt]')) == 2
    assert len(moose.wildcardFind('/ran/##[ISA=Stoich]')) == 2
    assert moose.wildcardFind('/ran/##/#_xfer_#')      # transport proxies exist

    el = [e for e in moose.wildcardFind('/ran/##/RanGTP_cy[0]')
          if 'Pool' in e.className and '_xfer_' not in e.name][0]
    for tck in range(20):
        moose.setClock(tck, 0.01)
    t, v = _sim('/ran', el.path, 100.0)
    assert np.all(np.isfinite(v))
    assert np.all(v >= -1e-9)
    assert v[-1] > 0                                    # transport filled it


def test_doqcs_multicompartment_sbml():
    """A DOQCS model exported to SBML (cAMP pathway, membrane+cytosol) -- a
    multi-compartment model MOOSE itself can also read as GENESIS kkit -- must
    load with every reaction native across both compartments and simulate to a
    finite, non-negative trajectory."""
    path = os.path.join(HERE, 'DOQCS_acc25_cAMP.xml')
    if not os.path.isfile(path):
        pytest.skip('DOQCS fixture not present')
    h = SBMLHandler()
    h.read(path, '/camp')
    assert h.report.reactions_function == 0
    assert h.report.reactions_native >= 20
    assert not h.report.unsupported, h.report.unsupported
    assert len(moose.wildcardFind('/camp/##[ISA=Stoich]')) >= 2

    pools = [e for e in moose.wildcardFind('/camp/##[ISA=PoolBase]')
             if '_xfer_' not in e.name]
    for tck in range(20):
        moose.setClock(tck, 0.005)
    t, v = _sim('/camp', pools[0].path, 20.0)
    assert np.all(np.isfinite(v))
    assert np.all(v >= -1e-6)


def test_spatial_diffusion_coefficient_read():
    """A diffusion constant declared with the SBML Level 3 spatial package
    (a Parameter carrying a DiffusionCoefficient) is copied onto the species'
    pool.diffConst."""
    import libsbml
    ns = libsbml.SBMLNamespaces(3, 1, 'spatial', 1)
    doc = libsbml.SBMLDocument(ns)
    doc.setPackageRequired('spatial', True)
    m = doc.createModel()
    c = m.createCompartment()
    c.setId('cyt'); c.setConstant(True); c.setSize(1.0); c.setSpatialDimensions(3)
    s = m.createSpecies()
    s.setId('S'); s.setCompartment('cyt'); s.setInitialConcentration(1.0)
    s.setConstant(False); s.setBoundaryCondition(False)
    s.setHasOnlySubstanceUnits(False)
    p = m.createParameter()
    p.setId('S_diff'); p.setValue(2.5e-12); p.setConstant(True)
    dc = p.getPlugin('spatial').createDiffusionCoefficient()
    dc.setVariable('S'); dc.setType(libsbml.SPATIAL_DIFFUSIONKIND_ISOTROPIC)

    import tempfile
    fn = tempfile.mktemp(suffix='.xml')
    libsbml.writeSBMLToFile(doc, fn)
    h = SBMLHandler()
    h.read(fn, '/spdiff')
    pool = [e for e in moose.wildcardFind('/spdiff/##/S[0]')
            if 'Pool' in e.className][0]
    assert abs(pool.diffConst - 2.5e-12) < 1e-20, pool.diffConst
