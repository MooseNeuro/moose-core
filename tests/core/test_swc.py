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

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/test_3point_soma.swc'), 'test_swc')

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/h10.CNG.swc'), 'h10')
moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/gc.CNG.swc'), 'gc')


#
# test_swc.py ends here
