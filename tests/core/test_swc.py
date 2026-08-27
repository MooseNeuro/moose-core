# test_swc.py ---
#
# Filename: test_swc.py
# Description: Test loading of neuronal morphologies from SWC files.
# Author: Subhasis Ray
# Created: Sat Mar 21 11:36:29 2026 (+0530)
#

# Code:
import os
import moose

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

# Full reconstructions exercised by loadSwc(). Each is loaded twice: once with
# the default compartment length limit and once unconstrained (max_len=None).
SWC_FILES = ['barrionuevo_cell1zr.CNG.swc',
             'DHC-neuron.CNG.swc',
             'gc.CNG.swc',
             'h10.CNG.swc',
             'K-18.CNG.swc',
             'ko20x-07.CNG.swc',
             'VHC-neuron.CNG.swc']


def test_load_point_somas():
    """loadModel() should read the 1/2/3-point soma SWC files and produce a
    soma with the expected geometry (L=10 um, D=10 um)."""
    container = moose.Neutral('test')
    moose.ce('test')
    try:
        for ii in range(1, 4):
            moose.loadModel(
                os.path.join(DATA_DIR, f'test_{ii}point_soma.swc'),
                f'test_{ii}pt')
        soma_list = [moose.element(f'test_{ii}pt/soma') for ii in range(1, 4)]
        for soma in soma_list:
            print(f'{soma.path}: L={soma.length * 1e6:0.3g}, '
                  f'D={soma.diameter * 1e6:0.3g}')
            assert abs(soma.length * 1e6 - 10) < 1e-3, soma.length
            assert abs(soma.diameter * 1e6 - 10) < 1e-3, soma.diameter
    finally:
        moose.ce('..')
        moose.delete(container)


def test_load_full_morphologies():
    """loadSwc() should read each full reconstruction (constrained and
    unconstrained) and create at least one compartment for it."""
    for fname in SWC_FILES:
        fpath = os.path.join(DATA_DIR, fname)
        mpath = fname.partition('.')[0].replace('-', '_')
        try:
            moose.loadSwc(fpath, mpath)
            moose.loadSwc(fpath, f'{mpath}_raw', max_len=None)
            for path in (mpath, f'{mpath}_raw'):
                comps = moose.wildcardFind(f'/{path}/##[ISA=Compartment]')
                assert len(comps) > 0, f'no compartments loaded for {path}'
        finally:
            for path in (mpath, f'{mpath}_raw'):
                if moose.exists(f'/{path}'):
                    moose.delete(f'/{path}')

#
# test_swc.py ends here
