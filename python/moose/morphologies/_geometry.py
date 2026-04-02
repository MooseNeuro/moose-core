"""
moose.morphologies._geometry
=============================
Compartment geometry utilities: surface area and path distance.
"""

import math


def surface_area(comp) -> float:
    """
    Lateral surface area of a cylindrical compartment (m²).

    Parameters
    ----------
    comp : moose.Compartment element

    Returns
    -------
    float
        π × diameter × length  (m²)
    """
    return math.pi * comp.diameter * comp.length


def distance_from_soma(comp, soma=None) -> float:
    """
    Path distance (m) from *soma* to *comp* along the morphology tree.

    Walks the parent chain from *comp* up to *soma*, summing ``length``
    at each compartment step.  If *soma* is ``None`` the function
    auto-detects the soma as the first ancestor whose parent is not a
    Compartment (i.e. the root of the cell tree).

    Parameters
    ----------
    comp : moose element
        Target compartment.
    soma : moose element, optional
        Root compartment.  Auto-detected if omitted.

    Returns
    -------
    float
        Cumulative path length in metres.  Returns 0.0 if *comp* is the soma.

    Raises
    ------
    RuntimeError
        If the parent chain does not reach *soma* within 10 000 steps
        (guards against malformed trees).
    """
    import moose

    def _is_compartment(el):
        try:
            return el.className in ('Compartment', 'SymCompartment')
        except Exception:
            return False

    # Auto-detect soma: root compartment (parent is not a compartment)
    if soma is None:
        cursor = comp
        for _ in range(10_000):
            parent = moose.element(cursor.parent)
            if not _is_compartment(parent):
                soma = cursor
                break
            cursor = parent
        else:
            raise RuntimeError('Could not auto-detect soma: tree too deep or cyclic')

    if comp.path == soma.path:
        return 0.0

    # Walk from comp toward soma, accumulating length
    dist   = 0.0
    cursor = comp
    for _ in range(10_000):
        if cursor.path == soma.path:
            return dist
        dist  += cursor.length
        parent = moose.element(cursor.parent)
        if not _is_compartment(parent):
            break
        cursor = parent
    raise RuntimeError(
        f'Soma {soma.path!r} not found in parent chain of {comp.path!r}')
