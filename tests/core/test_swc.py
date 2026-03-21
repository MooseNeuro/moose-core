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

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/test_3point_soma.swc'), 'test_3pt_soma_swc')

moose.loadModel(os.path.join(os.path.dirname(__file__),'../data/h10.CNG.swc'), 'test_swc')


#
# test_swc.py ends here
