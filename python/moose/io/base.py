# base.py ---
#
# Filename: base.py
# Description:
# Author: Subhasis Ray
# Created: Mon Jan 19 00:03:40 2026 (+0530)
#

# Code:
# Postpone evaluation of annotations (PEP 563): this module is reachable
# from moose/__init__.py's own early `from moose import model_utils` (which
# now imports moose.io.sbml for loadModel's SBML dispatch), well before
# `moose.ObjId` exists on the partially-initialized `moose` module -- without
# this, the `-> moose.ObjId` annotations below would be evaluated immediately
# at class-definition time and raise AttributeError.
from __future__ import annotations

from typing import List, Optional, Protocol

import moose


class FormatHandler(Protocol):
    """Protocol for model format handlers."""

    extensions: tuple[str, ...]

    def read(self, filepath: str, loadpath: str, **options) -> moose.ObjId: ...

    def write(self, modelpath: str, filepath: str, **options) -> moose.ObjId: ...


class ModelLoadError(Exception):
    """Failed to load model."""

    def __init__(self, message, filepath=None, loadpath=None):
        super().__init__(message)
        self.filepath = filepath
        self.loadpath = loadpath


#
# base.py ends here
