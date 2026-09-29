# Filename: test_hhchannel2d.py
# Description: Tests HHChannel2D and its table-based HHGate2D
# Author: Subhasis Ray and Claude
# Created: Wed Sep 30 2026
#
"""Tests HHChannel2D class and HHGate2D's expression-based table fill.

Usage: pytest test_hhchannel2d.py
"""
import math
import numpy as np
import moose
from ephys import create_voltage_clamp, setup_step_command


def test_hhchannel2d_creation():
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)
    chan = moose.HHChannel2D('ch')

    chan.Xpower = 1
    chan.Ypower = 2
    assert math.isclose(chan.Xpower, 1), 'Xpower not set'
    assert moose.exists(f'{chan.path}/gateX'), 'gateX object does not exist'
    assert math.isclose(chan.Ypower, 2), 'Ypower not set'
    assert moose.exists(f'{chan.path}/gateY'), 'gateY object does not exist'

    moose.ce(cwe)
    moose.delete(container)


def test_alpha_beta():
    """Test set/get alpha and beta expressions, and that `form` tracks it"""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)
    chan = moose.HHChannel2D('ch')
    chan.Xpower = 1
    xgate = moose.element(f'{chan.path}/gateX')
    # From the KCa channel in Eric De Schutter's granule cell model
    alpha = '2500 / (1 + 1.5e-3 * exp(-85*v)/c)'
    beta = '1500 / (1 + c / (1.5e-4 * exp (-77*v)))'
    xgate.alphaExpr = alpha
    xgate.betaExpr = beta
    assert xgate.alphaExpr == alpha, 'alpha not set'
    assert xgate.betaExpr == beta, 'beta not set'
    assert xgate.tauExpr == '', 'tau not reset'
    assert xgate.infExpr == '', 'inf not reset'
    assert xgate.form == 1, 'form should be 1 (alpha/beta) once alphaExpr is set'
    moose.ce(cwe)
    moose.delete(container)


def test_tau_inf():
    """Test set/get tau and inf expressions, and that `form` tracks it"""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)
    chan = moose.HHChannel2D('ch')
    chan.Xpower = 1
    xgate = moose.element(f'{chan.path}/gateX')
    alpha = '2500 / (1 + 1.5e-3 * exp(-85*v)/c)'
    beta = '1500 / (1 + c / (1.5e-4 * exp (-77*v)))'
    tau = f'1/({alpha} + {beta})'
    minf = f'({alpha}) / ({alpha} + {beta})'
    xgate.tauExpr = tau
    xgate.infExpr = minf
    assert xgate.tauExpr == tau, 'tau not set'
    assert xgate.infExpr == minf, 'inf not set'
    assert xgate.alphaExpr == '', 'alpha not reset'
    assert xgate.betaExpr == '', 'beta not reset'
    assert xgate.form == 2, 'form should be 2 (tau/inf) once tauExpr is set'
    moose.ce(cwe)
    moose.delete(container)


def _grid(vmin, vmax, vdivs, cmin, cmax, cdivs):
    dv = (vmax - vmin) / vdivs
    dc = (cmax - cmin) / cdivs
    v = [vmin + i * dv for i in range(vdivs + 1)]
    c = [cmin + j * dc for j in range(cdivs + 1)]
    return v, c


def test_fill_from_expr_alpha_beta():
    """fillFromExpr() must evaluate alphaExpr/betaExpr over the full
    (xmin..xmax) x (ymin..ymax) grid and match a direct Python evaluation."""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)
    chan = moose.HHChannel2D('ch')
    chan.Xpower = 1
    chan.Xindex = 'VOLT_C1_INDEX'
    gate = moose.element(f'{chan.path}/gateX')

    vmin, vmax, vdivs = -0.1, 0.05, 10
    cmin, cmax, cdivs = 1e-6, 1e-3, 8
    gate.xmin, gate.xmax, gate.xdivs = vmin, vmax, vdivs
    gate.ymin, gate.ymax, gate.ydivs = cmin, cmax, cdivs

    alpha = '2500 / (1 + 1.5e-3 * exp(-85 * (v - 10e-3)) / c)'
    beta = '1500 / (1 + c / (1.5e-4 * exp(-77 * (v - 10e-3))))'
    gate.alphaExpr = alpha
    gate.betaExpr = beta
    gate.fillFromExpr()

    tableA = np.asarray(gate.tableA)
    tableB = np.asarray(gate.tableB)
    assert tableA.shape == (vdivs + 1, cdivs + 1)
    assert tableB.shape == (vdivs + 1, cdivs + 1)
    assert np.all(np.isfinite(tableA))
    assert np.all(np.isfinite(tableB))

    v_grid, c_grid = _grid(vmin, vmax, vdivs, cmin, cmax, cdivs)
    for i, v in enumerate(v_grid):
        for j, c in enumerate(c_grid):
            a_exp = 2500 / (1 + 1.5e-3 * math.exp(-85 * (v - 10e-3)) / c)
            b_exp = 1500 / (1 + c / (1.5e-4 * math.exp(-77 * (v - 10e-3))))
            b_total_exp = a_exp + b_exp
            assert math.isclose(tableA[i, j], a_exp, rel_tol=1e-9), (i, j)
            assert math.isclose(tableB[i, j], b_total_exp, rel_tol=1e-9), (i, j)

    # `A`/`B` lookup must agree with the table at grid points
    v0, c0 = v_grid[3], c_grid[4]
    assert math.isclose(gate.A[[v0, c0]], tableA[3, 4], rel_tol=1e-9)
    assert math.isclose(gate.B[[v0, c0]], tableB[3, 4], rel_tol=1e-9)

    moose.ce(cwe)
    moose.delete(container)


def test_fill_from_expr_tau_inf():
    """tau/inf form: B must store 1/tau and A must store inf/tau, matching
    HHGate's convention (X_inf = A/B, time constant = 1/B)."""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)
    chan = moose.HHChannel2D('ch')
    chan.Xpower = 1
    chan.Xindex = 'C1_C2_INDEX'
    gate = moose.element(f'{chan.path}/gateX')

    xmin, xmax, xdivs = 1e-6, 1e-3, 6
    ymin, ymax, ydivs = 1e-6, 1e-3, 6
    gate.xmin, gate.xmax, gate.xdivs = xmin, xmax, xdivs
    gate.ymin, gate.ymax, gate.ydivs = ymin, ymax, ydivs

    gate.tauExpr = '1e-3'
    gate.infExpr = '1 / (1 + c / v)'
    gate.fillFromExpr()

    tableA = np.asarray(gate.tableA)
    tableB = np.asarray(gate.tableB)
    assert np.all(np.isfinite(tableA)) and np.all(np.isfinite(tableB))
    assert np.allclose(tableB, 1000.0), 'B should be 1/tau = 1000 everywhere'

    v_grid, c_grid = _grid(xmin, xmax, xdivs, ymin, ymax, ydivs)
    for i, v in enumerate(v_grid):
        for j, c in enumerate(c_grid):
            inf_exp = 1 / (1 + c / v)
            a_exp = inf_exp / 1e-3
            assert math.isclose(tableA[i, j], a_exp, rel_tol=1e-6), (i, j)

    moose.ce(cwe)
    moose.delete(container)


def test_fill_from_expr_c1_c2_aliases():
    """`c1`/`c2` must be usable as aliases for `v`/`c`, for C1_C2_INDEX
    gates where both axes are concentrations and `v`/`c` naming is
    misleading."""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)
    chan = moose.HHChannel2D('ch')
    chan.Xpower = 1
    chan.Xindex = 'C1_C2_INDEX'
    gate = moose.element(f'{chan.path}/gateX')

    xmin, xmax, xdivs = 1e-6, 1e-3, 6
    ymin, ymax, ydivs = 1e-6, 1e-3, 6
    gate.xmin, gate.xmax, gate.xdivs = xmin, xmax, xdivs
    gate.ymin, gate.ymax, gate.ydivs = ymin, ymax, ydivs

    gate.alphaExpr = '100 * c1 / (c1 + c2)'
    gate.betaExpr = '50 * c2'
    gate.fillFromExpr()

    tableA = np.asarray(gate.tableA)
    tableB = np.asarray(gate.tableB)
    v_grid, c_grid = _grid(xmin, xmax, xdivs, ymin, ymax, ydivs)
    for i, c1 in enumerate(v_grid):
        for j, c2 in enumerate(c_grid):
            a_exp = 100 * c1 / (c1 + c2)
            b_exp = 50 * c2 + a_exp
            assert math.isclose(tableA[i, j], a_exp, rel_tol=1e-9), (i, j)
            assert math.isclose(tableB[i, j], b_exp, rel_tol=1e-9), (i, j)

    moose.ce(cwe)
    moose.delete(container)


def test_vclamp_kca(steptime=0.05):
    """Voltage clamp with fixed Ca2+: simulated steady-state Gk must match
    the analytical value Gbar * alpha/(alpha+beta) at each (V, Ca) pair.

    This is the KCa channel (VOLT_C1_INDEX: v -> Vm, c -> conc1) from Eric De
    Schutter's granule cell model (`granule_cell_hhchannel2.py`), which is
    what originally motivated implementing `fillFromExpr` for HHGate2D.
    """
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)

    comp = moose.Compartment(f'{container.path}/comp')
    comp.Cm = 1e-9
    comp.Rm = 1e8
    comp.Em = -65e-3
    comp.initVm = -65e-3

    chan = moose.HHChannel2D(f'{comp.path}/KCa')
    chan.Ek = -90e-3
    chan.Gbar = 1e-6
    chan.Xpower = 1
    chan.Xindex = 'VOLT_C1_INDEX'
    gate = moose.element(f'{chan.path}/gateX')
    gate.xmin, gate.xmax, gate.xdivs = -0.15, 0.1, 200
    gate.ymin, gate.ymax, gate.ydivs = 1e-3, 0.5, 200
    alpha = '2500 / (1 + 1.5e-3 * exp(-85*(v - 10e-3)) / c)'
    beta = '1500 / (1 + c / (1.5e-4 * exp(-77*(v - 10e-3))))'
    gate.alphaExpr = alpha
    gate.betaExpr = beta
    gate.fillFromExpr()

    moose.connect(chan, 'channel', comp, 'channel')

    capool = moose.CaConc(f'{comp.path}/Ca')
    moose.connect(capool, 'concOut', chan, 'concen')

    vclamp, command, commandtab = create_voltage_clamp(comp)

    v_steps = [-75e-3, -35e-3, -15e-3, 0.0, 35e-3]
    ca_steps = [0.01, 0.05, 0.1, 0.3]

    def analytic_alpha(v, c):
        return 2500 / (1 + 1.5e-3 * math.exp(-85 * (v - 10e-3)) / c)

    def analytic_beta(v, c):
        return 1500 / (1 + c / (1.5e-4 * math.exp(-77 * (v - 10e-3))))

    simtime = steptime + 0.1

    for vstep in v_steps:
        setup_step_command(command, comp.Em, delay=steptime, level=vstep)
        for ca in ca_steps:
            capool.CaBasal = ca
            moose.reinit()
            moose.start(simtime)
            a = analytic_alpha(vstep, ca)
            b = analytic_beta(vstep, ca)
            expected_gk = chan.Gbar * a / (a + b)
            # rel_tol reflects bilinear-interpolation error from the
            # discretized 2D table (unlike HHChannelF2D, which evaluates
            # the expression live with no discretization error).
            assert math.isclose(chan.Gk, expected_gk, rel_tol=1e-2), (
                f'V={vstep * 1e3:.0f} mV  Ca={ca}: '
                f'Gk={chan.Gk:.6g} S  expected={expected_gk:.6g} S')

    moose.ce(cwe)
    moose.delete(container)


def test_single_axis_mode_safety():
    """VOLT_INDEX (single-axis mode: dep1 == -1) must not crash, and with a
    degenerate second axis (ydivs=0) must reproduce a pure 1D voltage-gated
    channel's steady state, matching a plain HHChannel with the same rates."""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)

    comp = moose.Compartment(f'{container.path}/comp')
    comp.Cm = 1e-9
    comp.Rm = 1e7
    comp.initVm = -0.065
    comp.Em = -0.065

    chan = moose.HHChannel2D(f'{comp.path}/ch')
    chan.Xpower = 1
    chan.Ek = 0.05
    chan.Xindex = 'VOLT_INDEX'

    gate = moose.element(chan.gateX)
    vmin, vmax, vdivs = -0.1, 0.05, 20
    gate.xmin, gate.xmax, gate.xdivs = vmin, vmax, vdivs
    gate.ymin, gate.ymax, gate.ydivs = 0.0, 1.0, 0  # degenerate second axis

    alpha = '100 * exp(50 * (v - (-0.04)))'
    beta = '100 * exp(-50 * (v - (-0.04)))'
    gate.alphaExpr = alpha
    gate.betaExpr = beta
    gate.fillFromExpr()

    tableA = np.asarray(gate.tableA)
    tableB = np.asarray(gate.tableB)
    assert tableA.shape == (vdivs + 1, 1)
    assert np.all(np.isfinite(tableA)) and np.all(np.isfinite(tableB))

    moose.connect(comp, 'channel', chan, 'channel')
    moose.reinit()

    assert not math.isnan(chan.X), 'X is NaN: depValue(-1) is not being handled safely'

    v = comp.initVm
    a = 100 * math.exp(50 * (v - (-0.04)))
    b = 100 * math.exp(-50 * (v - (-0.04)))
    expected_x = a / (a + b)
    assert math.isclose(chan.X, expected_x, rel_tol=1e-2), (
        f'X={chan.X}, expected steady-state X_inf={expected_x} at Vm={v}'
    )

    moose.start(2e-3)
    assert not math.isnan(chan.X)
    assert not math.isnan(comp.Vm)

    moose.ce(cwe)
    moose.delete(container)


def test_fill_from_expr_degenerate_axis_references_c():
    """With ydivs=0, an expression that references `c`/`c2` must see
    c = ymin, not NaN (dc must not be computed as (ymax-ymin)/0)."""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)
    chan = moose.HHChannel2D('ch')
    chan.Xpower = 1
    chan.Xindex = 'VOLT_INDEX'
    gate = moose.element(chan.gateX)
    gate.xmin, gate.xmax, gate.xdivs = -0.1, 0.05, 10
    gate.ymin, gate.ymax, gate.ydivs = 2.0, 5.0, 0
    gate.alphaExpr = '10 + c'
    gate.betaExpr = '1 + 0 * c2'
    gate.fillFromExpr()

    tableA = np.asarray(gate.tableA)
    tableB = np.asarray(gate.tableB)
    assert tableA.shape == (11, 1)
    assert np.all(np.isfinite(tableA)) and np.all(np.isfinite(tableB))
    assert np.allclose(tableA, 12.0), 'c should evaluate to ymin on a degenerate axis'
    assert np.allclose(tableB, 13.0), 'B = alpha + beta = 12 + 1'

    moose.ce(cwe)
    moose.delete(container)


def test_degenerate_second_axis_ignored():
    """With ydivs=0, the lookup must be independent of the c coordinate."""
    cwe = moose.getCwe()
    container = moose.Neutral('/test')
    moose.ce(container)

    chan = moose.HHChannel2D('ch')
    chan.Xpower = 1
    gate = moose.element(chan.gateX)

    vmin, vmax, vdivs = -0.1, 0.05, 10
    gate.xmin, gate.xmax, gate.xdivs = vmin, vmax, vdivs
    gate.ymin, gate.ymax, gate.ydivs = 0.0, 1.0, 0

    v_grid = np.linspace(vmin, vmax, vdivs + 1)
    a_vals = 100 * np.exp(-50 * (v_grid - (-0.02)))
    gate.tableA = a_vals.reshape(-1, 1).tolist()
    gate.tableB = (5.0 + 0 * v_grid).reshape(-1, 1).tolist()

    v_test = -0.03
    a_ref = gate.A[[v_test, 0.0]]
    for c_test in [-1e9, 0.0, 0.5, 1.0, 1e9]:
        assert math.isclose(gate.A[[v_test, c_test]], a_ref, rel_tol=1e-12)
        assert math.isclose(gate.B[[v_test, c_test]], 5.0, rel_tol=1e-12)

    moose.ce(cwe)
    moose.delete(container)


if __name__ == '__main__':
    test_hhchannel2d_creation()
    test_alpha_beta()
    test_tau_inf()
    test_fill_from_expr_alpha_beta()
    test_fill_from_expr_tau_inf()
    test_fill_from_expr_c1_c2_aliases()
    test_vclamp_kca()
    test_single_axis_mode_safety()
    test_fill_from_expr_degenerate_axis_references_c()
    test_degenerate_second_axis_ignored()
    print('All HHChannel2D tests passed.')

#
# test_hhchannel2d.py ends here
