# Filename: test_hhchanf2d.py
# Description:
# Author: Subhasis Ray
# Created: Wed Jan 29 13:15:18 2025 (+0530)
#

"""Tests HHChannelF2D class.

Usage: pytest test_hhchanf2d.py
"""
import moose
import math
import pytest
from ephys import create_voltage_clamp, setup_step_command


@pytest.fixture
def container():
    """
    Setup:
        Create a Neutral object as model container and ce to it before
        yielding.

    Teardown:
        ce back to parent and delete the model
        container.

    """
    ret = moose.Neutral('/test')
    moose.ce(ret)
    yield ret
    moose.ce('..')
    moose.delete(ret)


@pytest.fixture
def channel(container):
    """
    Setup:
        Create a HHChannelF2D object.

    Teardown:
        Nothing. The container gets deleted
    """
    return moose.HHChannelF2D('ch')


def test_hhgatef2d_creation(channel):
    channel.Xpower = 1
    channel.Ypower = 2
    assert math.isclose(channel.Xpower, 1), 'Xpower not set'
    assert moose.exists(f'{channel.path}/gateX'), 'gateX object does not exist'
    assert math.isclose(channel.Ypower, 2), 'Ypower not set'
    assert moose.exists(f'{channel.path}/gateY'), 'gateY object does not exist'


def test_alpha_beta(channel):
    """Test set/get alpha and beta expressions"""
    channel.Xpower = 1
    xgate = moose.element(f'{channel.path}/gateX')
    # These are from KCa channel in Eric DeSchutter's granule cell model
    alpha = '2500 / (1 + 1.5e-3 * exp(-85*v)/c)'
    beta = '1500 / (1 + c / (1.5e-4 * exp (-77*v)))'
    xgate.alpha = alpha
    xgate.beta = beta
    assert xgate.alpha == alpha, 'alpha not set'
    assert xgate.beta == beta, 'beta not set'
    assert xgate.tau == '', 'tau not reset'
    assert xgate.inf == '', 'inf not reset'


def test_complex_expr(channel):    
    chan.Xpower = 3
    chan.Ypower = 1
    chan.Ek = 55e-3
    mgate = moose.element(f'{chan.path}/gateX')
    hgate = moose.element(f'{chan.path}/gateY')
    # These are based on NeuroML - for some reason the A parameter is
    # double that in the paper
    mtau ='~(alpha:=1500 * exp(81 *((v - 10e-3) - (-39e-3))), beta:=1500 * exp(-66 * (v - 10e-3) - (-39e-3)), alpha + beta == 0? 0: min(1/(alpha+beta), 5e-5))'
    mgate.tau = tau
    minf = '~(alpha:=1500 * exp(81 *((v - 10e-3) - (-39e-3))), beta:=1500 * exp(-66 * (v - 10e-3) - (-39e-3)), alpha/(alpha+beta))'
    mgate.inf = minf
    htau = '~(alpha:=120*exp(((v - 10e-3) - (-0.04))/(-0.01123596)), beta:=120 * exp(((v - 10e-3) - (-0.04)) / 0.01123596), alpha + beta == 0? 0: min(1/(alpha+beta), 2.25e-4))'
    hgate.tau = htau
    hinf = '~(alpha:=120*exp(((v - 10e-3) - (-0.04))/(-0.01123596)), beta:=120 * exp(((v - 10e-3) - (-0.04)) / 0.01123596), alpha/(alpha+beta))'
    hgate.inf = hinf
    assert mgate.tau == mtau, 'tau not set'
    assert mgate.inf == minf, 'inf not set'
    assert hgate.tau == htau, 'tau not set'
    assert hgate.inf == hinf, 'inf not set'
    
    
def test_tau_inf(channel):
    """Test set/get tau and inf expressions"""
    channel.Xpower = 1
    xgate = moose.element(f'{channel.path}/gateX')
    alpha = '2500 / (1 + 1.5e-3 * exp(-85*v)/c)'
    beta = '1500 / (1 + c / (1.5e-4 * exp (-77*v)))'
    tau = f'1/({alpha} + {beta})'
    minf = f'({alpha}) / ({alpha} + {beta})'
    xgate.tau = tau
    xgate.inf = minf
    assert xgate.tau == tau, 'tau not set'
    assert xgate.inf == minf, 'inf not set'
    assert xgate.alpha == '', 'alpha not reset'
    assert xgate.beta == '', 'beta not reset'


def test_vclamp(container, steptime=5.0):
    """Simulate a voltage clamp experiment with fixed Ca conc

    Parameters
    ----------
    steptime: float
        Time of the voltage step
    """
    comp = moose.Compartment('comp0')
    sarea = 4 * math.pi * (10e-3) ** 3 / 3
    chan = moose.HHChannelF2D(f'{comp.path}/K')
    moose.connect(chan, 'channel', comp, 'channel')
    chan.Gbar = sarea * 17.9811e-3 * 1e4  # 17.9811 mS/cm^2
    print(f'Gbar={chan.Gbar}')
    chan.Ek = -90e-3
    chan.Xpower = 1
    chan.Xindex = 'VOLT_C1_INDEX'
    n_gate = moose.element(f'{chan.path}/gateX')
    n_gate.alpha = '2500 / (1 + 1.5e-3 * exp(-85*(v-0.01))/c)'
    n_gate.beta = '1500 / (1 + c / (1.5e-4 * exp (-77*(v-0.01))))'
    comp.Em = -65e-3  # Hodgkin and Huxley used resting voltage as 0
    comp.initVm = -65e-3
    comp.Cm = sarea * 1e-6 * 1e4  # 1 uS/cm^2
    comp.Rm = 1 / (
        sarea * 0.0330033e-3 * 1e4
    )  # passive conductance is 0.0330033 mS/cm^2
    capool = moose.CaConc(f'{comp.path}/Ca')
    capool.CaBasal = 1e-9
    moose.connect(capool, 'concOut', chan, 'concen')
    vclamp, command, commandtab = create_voltage_clamp(comp)
    simtime = 100.0 + steptime
    # Precalculated steady state K conductance
    v_commands = [
        -75e-3,
        -65e-3,
        -55e-3,
        -45e-3,
        -35e-3,
        -25e-3,
        -15e-3,
        0,
        15e-3,
    ]
    ca_commands = [0.1e-9, 0.3e-9, 0.6e-9, 0.9e-9, 1.2e-9]

    def alpha(v, c):
        return 2500 / (1 + 1.5e-3 * math.exp(-85 * (v - 0.01)) / c)

    def beta(v, c):
        return 1500 / (1 + c / (1.5e-4 * math.exp(-77 * (v - 0.01))))

    vm_ca_gk = [
        [
            chan.Gbar * alpha(v, c) / (alpha(v, c) + beta(v, c))
            for c in ca_commands
        ]
        for v in v_commands
    ]

    for ii, vstep in enumerate(v_commands):
        setup_step_command(command, comp.Em, delay=steptime, level=vstep)
        for jj, ca in enumerate(ca_commands):
            capool.CaBasal = ca
            moose.reinit()
            moose.start(simtime)
            gk = vm_ca_gk[ii][jj]
            print('V', vstep, 'Ca', ca, 'Gk: Computed', gk, 'Simulated', chan.Gk)
            assert math.isclose(
                gk, chan.Gk, abs_tol=1e-10
            ), f'Vm={vstep} [Ca]={ca} Gk={chan.Gk}, expected={gk}'


if __name__ == '__main__':
    test_hhgatef2d_creation()
    test_alpha_beta()
    test_tau_inf()
    test_vclamp()
#
# test_hhchanf2d.py ends here
