# Filename: test_hhchan.py
# Description:
# Author: Subhasis Ray
# Created: Thu Jan 23 13:33:22 2025 (+0530)
#

# Code:
"""Tests for HHChannel class.

Usage: python test_hhchan.py
"""

import moose
import math
import pytest
from ephys import create_voltage_clamp, setup_step_command


def make_container(path='/test'):
    if moose.exists(path):
        moose.delete(path)
    return moose.Neutral(path)


def test_hhgate_creation():
    containter = make_container()
    ch = moose.HHChannel(f'{containter.path}/ch')
    ch.Xpower = 1
    ch.Ypower = 2
    assert math.isclose(ch.Xpower, 1)
    assert moose.exists(f'{ch.path}/gateX')
    assert math.isclose(ch.Ypower, 2), 'Ypower not set'
    assert moose.exists(f'{ch.path}/gateY'), 'gateY object does not exist'
    print(moose.le())


def test_hh_k_vclamp(steptime=5.0):
    """Simulate a voltage clamp with Hodhkin and Huxley's K+ channel.

    Parameters
    ----------
    steptime: float
        Time of the voltage step
    """
    container = make_container()
    comp = moose.Compartment(f'{container.path}/comp0')
    chan = moose.HHChannel(f'{comp.path}/K')
    moose.connect(chan, 'channel', comp, 'channel')
    chan.Gbar = 36.0
    chan.Ek = -12.0
    chan.Xpower = 4
    n_gate = moose.element(f'{chan.path}/gateX')
    vdivs = 150
    vmin = -30.0
    vmax = 120.0
    x_alpha_params = [0.1, -0.01, -1.0, -10.0, -10.0]
    x_beta_params = [0.125, 0, 0, 0, 80.0]
    # Note that `+` operator with lists as operands concatenates them
    x_params = x_alpha_params + x_beta_params + [vdivs, vmin, vmax]
    n_gate.setupAlpha(x_params)
    n_gate.useInterpolation = True
    comp.Em = 0  # Hodgkin and Huxley used resting voltage as 0
    comp.Vm = 0
    comp.initVm = 0
    comp.Cm = 1
    comp.Rm = 1 / 0.3  # G_leak is 0.3 mS/cm^2
    dt = 0.01
    for tick in range(8):
        moose.setClock(tick, dt)
    # This must be after setting clock dt because parameters depend on dt
    vclamp, command, commandtab = create_voltage_clamp(comp, f'{container.path}/elec')
    # Hodgkin and Huxley 1952, "Currents carried by sodium and
    # potassium ions ...", find maximum conductance
    simtime = 100.0 + steptime
    # Precalculated steady state K conductance
    vm_gk = {
        0: 0.3666444556069115,
        # 10: 1.8401,  # this is a discontinuity
        20: 5.287062775435651,
        30: 10.176967265218654,
        40: 15.220230442170081,
        50: 19.596740114488156,
        60: 23.1009379487905,
        70: 25.821065780738117,
        80: 27.91721528657564,
        90: 29.537324370047777,
        100: 30.79812392487768,
    }

    for vstep, gk in vm_gk.items():
        setup_step_command(command, 0.0, delay=steptime, level=vstep)
        moose.reinit()
        moose.start(simtime)
        assert math.isclose(
            gk, chan.Gk, abs_tol=1e-6
        ), f'Vm={vstep} Gk={chan.Gk}, expected={gk}'


def test_hh_na_vclamp(steptime=5.0):
    """Simulate a voltage clamp with Hodhkin and Huxley's K+ channel.

    Parameters
    ----------
    steptime: float
        Time of the voltage step
    """
    container = make_container()
    comp = moose.Compartment(f'{container.path}/comp0')
    chan = moose.HHChannel(f'{comp.path}/Na')
    moose.connect(chan, 'channel', comp, 'channel')
    chan.Gbar = 120.0
    chan.Ek = 115.0
    chan.Xpower = 3
    chan.Ypower = 1
    vdivs = 150
    vmin = -30.0
    vmax = 120.0
    m_gate = moose.element(f'{chan.path}/gateX')
    x_alpha_params = [2.5, -0.1, -1.0, -25.0, -10.0]
    x_beta_params = [4, 0, 0, 0, 18.0]
    # Note that `+` operator with lists as operands concatenates them
    x_params = x_alpha_params + x_beta_params + [vdivs, vmin, vmax]
    m_gate.setupAlpha(x_params)
    m_gate.useInterpolation = True
    h_gate = moose.element(f'{chan.path}/gateY')
    y_alpha_params = [0.07, 0, 0, 0, 20.0]
    y_beta_params = [1, 0, 1, -30, -10.0]
    # Note that `+` operator with lists as operands concatenates them
    y_params = y_alpha_params + y_beta_params + [vdivs, vmin, vmax]
    h_gate.setupAlpha(y_params)
    h_gate.useInterpolation = True
    comp.Em = 0  # Hodgkin and Huxley used resting voltage as 0
    comp.Vm = 0
    comp.initVm = 0
    comp.Cm = 1
    comp.Rm = 1 / 0.3  # G_leak is 0.3 mS/cm^2
    dt = 0.01
    for tick in range(8):
        moose.setClock(tick, dt)
    # This must be after setting clock dt because parameters depend on dt
    vclamp, command, commandtab = create_voltage_clamp(comp, modelpath=f'{container.path}/elec')
    # Hodgkin and Huxley 1952, "Currents carried by sodium and
    # potassium ions ...", find maximum conductance
    simtime = 100.0 + steptime
    # Precalculated steady state Na conductance
    vm_gna = {
        0: 0.010609192838829854,
        10: 0.12443211458767735,
        20: 0.527787746095522,
        30: 0.8966173682113173,
        40: 0.8361209504788413,
        50: 0.5983994566094422,
        60: 0.3893933499995894,
        70: 0.24432304663465443,
        80: 0.15080726000137287,
        90: 0.09232255449417581,
        100: 0.0562750224683144,
    }

    for vstep, gna in vm_gna.items():
        setup_step_command(command, 0.0, delay=steptime, level=vstep)
        moose.reinit()
        moose.start(simtime)
        assert math.isclose(
            gna, chan.Gk, abs_tol=1e-6
        ), f'Vm={vstep} Gk={chan.Gk}, expected={gna}'


def test_hhchan_eval():
    """Test the evaluation of hhchannel conductance using Hodgkin and
    Huxleys Na channel model

    """
    container = make_container()
    comp = moose.Compartment(f'{container.path}/comp0')
    chan = moose.HHChannel(f'{comp.path}/Na')
    moose.connect(chan, 'channel', comp, 'channel')
    chan.Gbar = 120.0
    chan.Ek = 115.0
    chan.Xpower = 3
    chan.Ypower = 1
    m_gate = moose.element(f'{chan.path}/gateX')
    h_gate = moose.element(f'{chan.path}/gateY')
    vdivs = 150
    vmin = -30.0
    vmax = 120.0
    x_alpha_params = [2.5, -0.1, -1.0, -25.0, -10.0]
    x_beta_params = [4, 0, 0, 0, 18.0]
    # Note that `+` operator with lists as operands concatenates them
    x_params = x_alpha_params + x_beta_params + [vdivs, vmin, vmax]
    m_gate.setupAlpha(x_params)
    m_gate.useInterpolation = True
    h_gate = moose.element(f'{chan.path}/gateY')
    y_alpha_params = [0.07, 0, 0, 0, 20.0]
    y_beta_params = [1, 0, 1, -30, -10.0]
    # Note that `+` operator with lists as operands concatenates them
    y_params = y_alpha_params + y_beta_params + [vdivs, vmin, vmax]
    h_gate.setupAlpha(y_params)
    h_gate.useInterpolation = True
    comp.Em = 0  # Hodgkin and Huxley used resting voltage as 0
    comp.Vm = 0
    comp.initVm = 0
    comp.Cm = 1
    comp.Rm = 1 / 0.3  # G_leak is 0.3 mS/cm^2
    moose.reinit()
    t = 0
    tdelta = comp.dt * 1000
    for ii in range(10):
        moose.start(tdelta)
        t += tdelta
        print(f'time={t} Gk={chan.Gk} Vm={comp.Vm}')
    comp.inject = 1.0
    print('Starting current injection...')
    for ii in range(10):
        moose.start(tdelta)
        t += tdelta
        print(f'time={t} Gk={chan.Gk} Vm={comp.Vm}')


def test_formula_alpha_beta_na(steptime=5.0):
    """
    Parameters
    ----------
    container: container element generated by pytest fixture

    steptime: duration for holding command voltage
    """
    container = make_container()
    comp = moose.Compartment(f'{container.path}/comp0')
    chan = moose.HHChannel(f'{comp.path}/Na')
    moose.connect(chan, 'channel', comp, 'channel')
    chan.Gbar = 120.0
    chan.Ek = 115.0
    chan.Xpower = 3
    chan.Ypower = 1
    m_gate = moose.element(f'{chan.path}/gateX')
    h_gate = moose.element(f'{chan.path}/gateY')
    m_gate.alphaExpr = '0.1 * (25 - v)/(exp((25 - v)/10) - 1)'
    m_gate.betaExpr = '4 * exp(-v/18)'
    h_gate.alphaExpr = '0.07 * exp(-v/20)'
    h_gate.betaExpr = '1/(exp((30-v)/10) + 1)'
    for gate in (m_gate, h_gate):
        gate.useInterpolation = True
        gate.divs = 150
        gate.min = -30.0
        gate.max = 120.0

    comp.Em = 0  # Hodgkin and Huxley used resting voltage as 0
    comp.Vm = 0
    comp.initVm = 0
    comp.Cm = 1
    comp.Rm = 1 / 0.3  # G_leak is 0.3 mS/cm^2
    dt = 0.01
    for tick in range(8):
        moose.setClock(tick, dt)
    # This must be after setting clock dt because parameters depend on dt
    vclamp, command, commandtab = create_voltage_clamp(comp, f'{container.path}/elec')
    # Hodgkin and Huxley 1952, "Currents carried by sodium and
    # potassium ions ...", find maximum conductance
    simtime = 100.0 + steptime
    # Precalculated steady state Na conductance
    vm_gna = {
        0: 0.010609192838829854,
        10: 0.12443211458767735,
        20: 0.527787746095522,
        30: 0.8966173682113173,
        40: 0.8361209504788413,
        50: 0.5983994566094422,
        60: 0.3893933499995894,
        70: 0.24432304663465443,
        80: 0.15080726000137287,
        90: 0.09232255449417581,
        100: 0.0562750224683144,
    }
    import numpy as np
    # import matplotlib.pyplot as plt
    # fig, axes = plt.subplots(nrows =len(vm_gna), ncols=4)
    vrange = np.linspace(m_gate.min, m_gate.max, m_gate.divs+1)
    for ii, (vstep, gna) in enumerate(vm_gna.items()):
        setup_step_command(command, 0.0, delay=steptime, level=vstep)
        moose.reinit()
        minf = m_gate.tableA/m_gate.tableB
        mtau = 1/m_gate.tableB
        hinf = h_gate.tableA/h_gate.tableB
        htau = 1/h_gate.tableB
        np.savetxt(f'na_v{vstep:.1f}.txt', np.c_[minf, hinf, mtau, htau])
        moose.start(simtime)
        # axes[ii, 0].plot(vrange, minf, label=f'{vstep} minf')
        # axes[ii, 0].plot(vrange, hinf, label=f'{vstep} hinf')
        # axes[ii, 1].plot(vrange, mtau, label=f'{vstep} mtau')
        # axes[ii, 1].plot(vrange, htau, label=f'{vstep} htau')
        # axes[ii, 2].plot(vrange, m_gate.tableA, label=f'{vstep} mA')
        # axes[ii, 2].plot(vrange, h_gate.tableA, label=f'{vstep} hA')
        # axes[ii, 3].plot(vrange, m_gate.tableB, label=f'{vstep} mB')
        # axes[ii, 3].plot(vrange, h_gate.tableB, label=f'{vstep} hB')

        # assert math.isclose(
        #     gna, chan.Gk, abs_tol=1e-6
        # ), f'Vm={vstep} Gk={chan.Gk}, expected={gna}'
    # plt.show()

if __name__ == '__main__':
    test_hhgate_creation()
    test_hh_k_vclamp()
    test_hh_na_vclamp()
    test_hhchan_eval()
    test_formula_alpha_beta_na()
#
# test_hhchan.py ends here
