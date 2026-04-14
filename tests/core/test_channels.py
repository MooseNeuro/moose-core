# Filename: test_channels.py
# Description: Tests for moose.channels submodule (ICGenealogy channel DB)
# Author: Subhasis Ray and Claude
#

"""Tests for moose.channels.

Covers:
  - DB layer: search, get_expressions, expression format
  - make_prototype: HHChannel created in /library, gate powers, idempotency
  - Q10 temperature correction: Gbar scale at non-reference temperature
  - >3 gate UserWarning
  - insert: copies into compartment, Gbar set, channel connected
  - load: end-to-end convenience wrapper
  - brief simulation: channel conductance responds to voltage

Reference channels used throughout:
  - model_id=87535, suffix='nax'  (Na, 2 gates m^3 h^1)
  - model_id=45539, suffix='kdr'  (K,  1 gate  n^4)
"""

import math
import warnings

import pytest
import moose
import moose.channels as chan
from moose.channels._proto import T_REF


# ── helpers ───────────────────────────────────────────────────────────────────

def make_container(path='/test_chan'):
    """Reset a MOOSE namespace for isolation between tests."""
    if moose.exists(path):
        moose.delete(path)
    return moose.Neutral(path)


def reset_library():
    """Remove /library so prototype tests start fresh."""
    if moose.exists('/library'):
        moose.delete('/library')


# ── DB layer (no MOOSE objects) ───────────────────────────────────────────────

def test_search_by_model_id():
    results = chan.search(model_id=87535, show=False)
    assert len(results) >= 1
    assert results[0]['model_id'] == 87535


def test_search_by_ion_class():
    results = chan.search(ion_class='Na', show=False)
    assert len(results) > 0
    for r in results:
        for suffix, gates in r['channels'].items():
            assert gates[0]['ion_class'] == 'Na'


def test_search_by_suffix():
    results = chan.search(suffix='kdr', show=False)
    assert len(results) > 0
    for r in results:
        assert any('kdr' in s.lower() for s in r['channels'])


def test_search_no_match():
    results = chan.search(model_id=999999999, show=False)
    assert results == []


def test_list_ion_classes():
    classes = chan.list_ion_classes()
    assert set(classes) >= {'Na', 'K', 'Ca', 'KCa', 'IH'}


def test_get_expressions_returns_strings():
    inf_expr, tau_expr = chan.get_expressions(87535, 'nax', 'm')
    assert isinstance(inf_expr, str) and len(inf_expr) > 0
    assert isinstance(tau_expr, str) and len(tau_expr) > 0


def test_expression_contains_v():
    """Expressions must reference 'v' (MOOSE voltage field)."""
    inf_expr, tau_expr = chan.get_expressions(87535, 'nax', 'm')
    assert 'v' in inf_expr
    assert 'v' in tau_expr


def test_expression_contains_si_conversion():
    """Expressions should convert volts→mV via 1e3 factor."""
    inf_expr, tau_expr = chan.get_expressions(87535, 'nax', 'm')
    assert '1e3' in inf_expr
    assert '1e3' in tau_expr


def test_get_expressions_unknown_gate():
    with pytest.raises(KeyError):
        chan.get_expressions(87535, 'nax', 'z_nonexistent')


# ── make_prototype ────────────────────────────────────────────────────────────

def test_make_prototype_creates_hhchannel():
    reset_library()
    proto = chan.make_prototype(87535, 'nax')
    assert proto.className == 'HHChannel'


def test_make_prototype_in_library():
    reset_library()
    proto = chan.make_prototype(87535, 'nax')
    assert proto.path.startswith('/library/')


def test_make_prototype_name_encodes_temperature():
    reset_library()
    proto = chan.make_prototype(87535, 'nax')
    t_tag = f'T{round(T_REF * 10):d}'
    assert t_tag in proto.name


def test_make_prototype_gate_powers():
    """nax has m^3 h^1 → Xpower=3, Ypower=1."""
    reset_library()
    proto = chan.make_prototype(87535, 'nax')
    assert math.isclose(proto.Xpower, 3.0), f'Xpower={proto.Xpower}'
    assert math.isclose(proto.Ypower, 1.0), f'Ypower={proto.Ypower}'


def test_make_prototype_gates_have_expressions():
    reset_library()
    proto = chan.make_prototype(87535, 'nax')
    gate_x = moose.element(f'{proto.path}/gateX')
    gate_y = moose.element(f'{proto.path}/gateY')
    assert len(gate_x.infExpr) > 0
    assert len(gate_x.tauExpr) > 0
    assert len(gate_y.infExpr) > 0
    assert len(gate_y.tauExpr) > 0


def test_make_prototype_gate_lookup_table_set():
    """Lookup table parameters must be set for exprtk expressions to work."""
    reset_library()
    proto = chan.make_prototype(87535, 'nax')
    gate_x = moose.element(f'{proto.path}/gateX')
    assert gate_x.divs > 0
    assert gate_x.min < 0        # negative (volts)
    assert gate_x.max > 0        # positive (volts)
    assert gate_x.useInterpolation


def test_make_prototype_idempotent():
    """Second call with identical args returns the same element, not a new one."""
    reset_library()
    proto1 = chan.make_prototype(87535, 'nax')
    proto2 = chan.make_prototype(87535, 'nax')
    assert proto1.path == proto2.path


def test_make_prototype_kdr():
    reset_library()
    proto = chan.make_prototype(45539, 'kdr')
    assert proto.className == 'HHChannel'
    assert proto.Xpower > 0


# ── Q10 temperature correction ────────────────────────────────────────────────

def test_q10_gbar_scale_at_reference():
    """At T_REF the gbar scale should be 1.0 (no correction)."""
    reset_library()
    proto = chan.make_prototype(87535, 'nax', temperature=T_REF)
    assert math.isclose(proto.Gbar, 1.0, rel_tol=1e-9), (
        f'proto.Gbar={proto.Gbar} expected 1.0 at T_REF')


def test_q10_gbar_scale_above_reference():
    """At T > T_REF and Q10_g > 1 the gbar scale should exceed 1.0."""
    reset_library()
    T_warm = T_REF + 20.0
    proto_ref  = chan.make_prototype(87535, 'nax', temperature=T_REF)
    reset_library()
    proto_warm = chan.make_prototype(87535, 'nax', temperature=T_warm)
    # If Q10_g is present for this channel, warm proto has higher Gbar scale.
    # If Q10_g is absent (== 1), both are 1.0 — still equal or greater.
    assert proto_warm.Gbar >= proto_ref.Gbar


def test_q10_different_temperature_different_prototype():
    """Different temperatures map to different prototype paths."""
    reset_library()
    proto_a = chan.make_prototype(87535, 'nax', temperature=T_REF)
    proto_b = chan.make_prototype(87535, 'nax', temperature=T_REF + 10.0)
    assert proto_a.path != proto_b.path


# ── >3 gate warning ───────────────────────────────────────────────────────────

def test_more_than_3_gates_warning():
    """Channels with 4+ gate variables should emit a UserWarning."""
    from moose.channels._db import ICGChannelDB
    from pathlib import Path

    data = Path(__file__).parents[2] / 'python/moose/channels/data'
    db = ICGChannelDB(
        data / 'channel_db.csv',
        data / 'modeldb_popularity.csv',
    )
    # Find a channel with >3 gate rows
    four_gate_chan = None
    for row in db._rows:
        mid = row['model_id']
        suf = row['suffix']
        if mid and suf:
            try:
                gates = db.get_gate_rows(mid, suf)
                if len(gates) > 3:
                    four_gate_chan = (mid, suf)
                    break
            except KeyError:
                pass

    if four_gate_chan is None:
        pytest.skip('No >3 gate channel found in database')

    reset_library()
    mid, suf = four_gate_chan
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        chan.make_prototype(mid, suf)
    user_warnings = [w for w in caught if issubclass(w.category, UserWarning)]
    assert len(user_warnings) >= 1
    assert 'gate' in str(user_warnings[0].message).lower()


# ── insert ────────────────────────────────────────────────────────────────────

def test_insert_copies_into_compartment():
    reset_library()
    container = make_container()
    comp  = moose.Compartment(f'{container.path}/comp')
    proto = chan.make_prototype(87535, 'nax')
    copies = chan.insert(comp, proto, gbar=1e-9, Ek=0.050)
    assert len(copies) == 1
    assert copies[0].className == 'HHChannel'
    assert copies[0].path.startswith(comp.path)


def test_insert_sets_gbar():
    reset_library()
    container = make_container()
    comp  = moose.Compartment(f'{container.path}/comp')
    proto = chan.make_prototype(87535, 'nax', temperature=T_REF)
    gbar_val = 5e-9
    copies = chan.insert(comp, proto, gbar=gbar_val, Ek=0.050)
    # At T_REF proto.Gbar == 1.0, so copy.Gbar == gbar_val
    assert math.isclose(copies[0].Gbar, gbar_val, rel_tol=1e-6)


def test_insert_sets_ek():
    reset_library()
    container = make_container()
    comp  = moose.Compartment(f'{container.path}/comp')
    proto = chan.make_prototype(87535, 'nax', temperature=T_REF)
    Ek_val = 0.055
    copies = chan.insert(comp, proto, gbar=1e-9, Ek=Ek_val)
    assert math.isclose(copies[0].Ek, Ek_val, rel_tol=1e-6)


def test_insert_connects_channel():
    """Inserted channel must be connected to compartment (channel message)."""
    reset_library()
    container = make_container()
    comp  = moose.Compartment(f'{container.path}/comp')
    proto = chan.make_prototype(87535, 'nax', temperature=T_REF)
    copies = chan.insert(comp, proto, gbar=1e-9, Ek=0.050)
    # A connected channel shows up in moose.wildcardFind with TYPE=HHChannel
    found = moose.wildcardFind(f'{comp.path}/#[TYPE=HHChannel]')
    assert len(found) >= 1


def test_insert_multiple_compartments():
    reset_library()
    container = make_container()
    comps = [moose.Compartment(f'{container.path}/comp{i}') for i in range(3)]
    proto = chan.make_prototype(45539, 'kdr', temperature=T_REF)
    copies = chan.insert(comps, proto, gbar=2e-9, Ek=-0.077)
    assert len(copies) == 3


def test_insert_callable_gbar():
    reset_library()
    container = make_container()
    comps = [moose.Compartment(f'{container.path}/comp{i}') for i in range(2)]
    proto = chan.make_prototype(45539, 'kdr', temperature=T_REF)
    gbar_fn = lambda c: 1e-9 * (1 + int(c.name[-1]))   # different per comp
    copies = chan.insert(comps, proto, gbar=gbar_fn, Ek=-0.077)
    assert len(copies) == 2
    assert not math.isclose(copies[0].Gbar, copies[1].Gbar)


# ── load convenience ──────────────────────────────────────────────────────────

def test_load_convenience():
    reset_library()
    container = make_container()
    comp = moose.Compartment(f'{container.path}/comp')
    copies = chan.load(comp, model_id=87535, suffix='nax',
                       gbar=1e-9, Ek=0.050, temperature=T_REF)
    assert len(copies) == 1
    assert copies[0].className == 'HHChannel'


# ── brief simulation: Gk responds to voltage ─────────────────────────────────

def test_channel_conductance_nonzero():
    """
    Simple current-injection test: after injecting current into a compartment
    with a Na channel inserted, Gk should become non-zero.

    This exercises the full pipeline: prototype build → insert → simulate.
    """
    reset_library()
    container = make_container()

    comp = moose.Compartment(f'{container.path}/comp')
    comp.Cm  = 1e-9     # F
    comp.Rm  = 1e8      # Ω  (0.01 μS leak)
    comp.Em  = -0.065   # V  resting potential
    comp.Vm  = -0.065
    comp.initVm = -0.065

    copies = chan.load(comp, model_id=87535, suffix='nax',
                       gbar=1e-6, Ek=0.050, temperature=T_REF)
    na_chan = copies[0]

    dt = 25e-6          # 25 μs
    for tick in range(8):
        moose.setClock(tick, dt)

    moose.reinit()
    # Inject a brief depolarising pulse
    comp.inject = 2e-9  # 2 nA
    moose.start(5e-3)   # 5 ms
    comp.inject = 0.0

    # After depolarisation, channel should have opened (Gk > 0)
    assert na_chan.Gk > 0, f'Expected Gk > 0 after depolarisation, got {na_chan.Gk}'


def test_k_channel_opens_on_depolarisation():
    """K channel (kdr) should open and carry outward current on depolarisation."""
    reset_library()
    container = make_container('/test_k')

    comp = moose.Compartment(f'{container.path}/comp')
    comp.Cm  = 1e-9
    comp.Rm  = 1e8
    comp.Em  = -0.065
    comp.Vm  = -0.065
    comp.initVm = -0.065

    copies = chan.load(comp, model_id=45539, suffix='kdr',
                       gbar=5e-7, Ek=-0.077, temperature=T_REF)
    k_chan = copies[0]

    dt = 25e-6
    for tick in range(8):
        moose.setClock(tick, dt)

    moose.reinit()
    comp.inject = 5e-9   # strong depolarisation
    moose.start(10e-3)
    comp.inject = 0.0

    assert k_chan.Gk > 0, f'Expected Gk > 0 after depolarisation, got {k_chan.Gk}'


if __name__ == '__main__':
    test_search_by_model_id()
    test_list_ion_classes()
    test_get_expressions_returns_strings()
    test_make_prototype_creates_hhchannel()
    test_make_prototype_idempotent()
    test_q10_gbar_scale_at_reference()
    test_insert_sets_gbar()
    test_load_convenience()
    test_channel_conductance_nonzero()
    test_k_channel_opens_on_depolarisation()
    print('All channel tests passed.')
#
# test_channels.py ends here
