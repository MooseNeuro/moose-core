# __init__.py ---
#
# Filename: __init__.py
# Description:
# Author: Subhasis Ray
# Created: Sun Mar 22 12:12:18 2026 (+0530)
#

# Code:

"""
moose.io — Format-handler refactoring (work in progress)
=========================================================
This package is a planned replacement for the format-specific loading code
currently in moose.model_utils, moose.SBML, and moose.neuroml2.

Design
------
Each format is a class implementing the FormatHandler protocol (see base.py):
    - SBMLHandler   (io/sbml.py)   — partially implemented
    - NML2Handler   (io/nml2.py)   — stub

Integration plan
----------------
When complete, model_utils.load() will dispatch to handlers registered here
instead of calling moose.SBML.readSBML and moose.neuroml2.NML2Reader directly.

Status: NOT YET INTEGRATED. Do not import from this package in production code.
"""
from .base import FormatHandler, ModelLoadError

__all__ = ['FormatHandler', 'ModelLoadError']


#
# __init__.py ends here
