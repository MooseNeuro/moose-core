"""Normalize an SBML document to a canonical shape before mapping.

We lean on libsbml's own converters instead of hand-rolling these transforms
(as the legacy reader did). After normalization the mapper only ever sees:
  * function definitions inlined into the expressions that use them,
  * initial assignments folded into initial values where possible,
  * local (per-kinetic-law) parameters promoted to global parameters,
  * assignment rules topologically sorted into evaluation order.

We deliberately do NOT convert SBML level/version: libsbml's read API is
largely level-agnostic, and level conversion can *fail* and reject an otherwise
loadable model. Units are handled explicitly at map time rather than via the
units converter, whose behaviour on under-specified models is unreliable.
"""

import libsbml

# (option-key, human label) in the order they must run.
_STEPS = [
    ('expandFunctionDefinitions', 'inline function definitions'),
    ('promoteLocalParameters', 'promote local parameters to global'),
    ('expandInitialAssignments', 'fold initial assignments'),
    ('sortRules', 'sort assignment rules by dependency'),
]


def normalize(doc):
    """Apply the converter pipeline in place. Returns ``(applied, skipped)``
    lists of human labels; a converter that reports anything other than
    success is recorded in ``skipped`` and left un-applied (non-fatal)."""
    applied, skipped = [], []
    for key, label in _STEPS:
        props = libsbml.ConversionProperties()
        props.addOption(key, True)
        status = doc.convert(props)
        if status == libsbml.LIBSBML_OPERATION_SUCCESS:
            applied.append(label)
        else:
            skipped.append(f'{label} (status={status})')
    return applied, skipped
