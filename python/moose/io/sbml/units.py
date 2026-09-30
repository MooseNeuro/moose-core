"""Unit conventions between SBML and MOOSE.

MOOSE uses SI: volume in m^3, concentration in mM (= mol/m^3), molecule number
``n = conc * NA * V``. SBML lets each model pick its own substance and size
units (e.g. nanomole, litre), so we resolve two scale factors from the model
and fold them in so MOOSE ends up in true SI:

    size_scale       m^3 per SBML size unit        (litre -> 1e-3, m^3 -> 1)
    substance_scale  mol per SBML substance unit    (nanomole -> 1e-9, mole ->1)

    volume(comp) = size * size_scale                          [m^3]
    subst_factor = NA * substance_scale
    n            = (SBML amount) * subst_factor               [molecules]
      => conc = n/(NA*V_m3) = amount*substance_scale/(size*size_scale)
              = SBML concentration expressed in mol/m^3 = mM.

This makes MOOSE's reported concentrations physical mM (matching kkit and other
MOOSE models), not the SBML's raw value.
"""

import libsbml

# Single source of truth: the same Avogadro number the MOOSE solvers use
# (basecode/Constants.h, exposed as moose.NA).
from moose._moose import NA as AVOGADRO


def _si_factor(unit_def):
    """Numeric value of one of ``unit_def``'s composite unit in SI base units."""
    si = libsbml.UnitDefinition.convertToSI(unit_def)
    factor = 1.0
    for i in range(si.getNumUnits()):
        u = si.getUnit(i)
        factor *= (u.getMultiplier() * 10.0 ** u.getScale()) ** u.getExponent()
    return factor


def substance_scale(model):
    """Moles per SBML substance unit (default: mole -> 1)."""
    ud = model.getUnitDefinition('substance')
    if ud is None or ud.getNumUnits() == 0:
        return 1.0
    return _si_factor(ud)


def size_scale(comp):
    """Cubic metres per this compartment's size unit (default: litre -> 1e-3)."""
    ud = comp.getDerivedUnitDefinition()
    if ud is None or ud.getNumUnits() == 0:
        return 1e-3
    return _si_factor(ud)


def volume(comp):
    """Compartment volume in cubic metres."""
    size = comp.getSize() if comp.isSetSize() else 1.0
    return size * size_scale(comp)


def species_ninit(species, comp, subst_factor):
    """Initial molecule number: (SBML amount) * subst_factor, resolving
    initialConcentration to an amount via the compartment size."""
    if species.isSetInitialAmount():
        amount = species.getInitialAmount()
    elif species.isSetInitialConcentration():
        size = comp.getSize() if comp.isSetSize() else 1.0
        amount = species.getInitialConcentration() * size
    else:
        amount = 0.0
    return amount * subst_factor
