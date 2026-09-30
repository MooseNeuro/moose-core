# nml2.py ---
#
# Filename: nml2.py
# Description:
# Author: Subhasis Ray
# Created: Sun Mar 22 12:12:43 2026 (+0530)
#

# Code:
"""NeuroML2 format handler — stub for future implementation."""
from .base import FormatHandler, ModelLoadError


class NML2Handler:
    """FormatHandler for NeuroML2 (.nml, .xml) files.

    TODO: Implement by migrating moose.neuroml2.NML2Reader here,
    wrapping it to conform to the FormatHandler protocol.
    """
    extensions = ('.nml', '.xml')

    def read(self, filepath: str, loadpath: str, **options):
        raise NotImplementedError("NML2Handler.read() not yet implemented")

    def write(self, modelpath: str, filepath: str, **options):
        raise NotImplementedError("NML2Handler.write() not yet implemented")


#
# nml2.py ends here
