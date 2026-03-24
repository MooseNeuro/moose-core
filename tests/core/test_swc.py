# test_swc.py ---
#
# Filename: test_swc.py
# Description:
# Author: Subhasis Ray
# Created: Sat Mar 21 11:36:29 2026 (+0530)
#

# Code:
import os
import moose

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/test_1point_soma.swc'), 'test_1pt')

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/test_2point_soma.swc'), 'test_2pt')

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/test_3point_soma.swc'), 'test_3pt')


soma_list = [moose.element(f'test_{ii}pt/soma') for ii in range(1, 4)]
for soma in soma_list:
    print(f'{soma.path}: L={soma.length*1e6:0.3g}, D={soma.diameter*1e6:0.3g}')

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/h10.CNG.swc'), 'h10')

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/gc.CNG.swc'), 'gc')



#
# test_swc.py ends here
