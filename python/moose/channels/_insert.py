"""
moose.channels._insert
=======================
Insert channel prototypes into compartments via moose.copy().

Gate tables are shared between the prototype and all copies — MOOSE's C++
copy mechanism handles this automatically.  Only Gbar and Ek need to be set
per copy.

Compartment selector forms accepted by ``insert()``
-----------------------------------------------------
str      → moose.wildcardFind(pattern)          e.g. '/neuron/##[TYPE=Compartment]'
ObjId    → [element]                            single compartment element
list     → elements as-is                       pre-found list
dict     → {element: gbar_override_S}           per-compartment absolute Gbar

gbar forms
----------
float      → same absolute conductance (S) for every compartment
callable   → gbar(comp) → float (S); called per compartment
dict       → {comp: float} embedded in the compartments argument
"""

# ── compartment resolution ────────────────────────────────────────────────────

def _resolve_compartments(sel):
    """
    Normalise *sel* to (list_of_comps, gbar_dict_or_None).

    Returns
    -------
    comps : list of moose elements
    gbar_map : dict {comp_path: float} or None
    """
    import moose

    if isinstance(sel, dict):
        comps    = list(sel.keys())
        gbar_map = {c.path: g for c, g in sel.items()}
        return comps, gbar_map

    if isinstance(sel, str):
        comps = moose.wildcardFind(sel)
        if not comps:
            raise ValueError(f'No compartments matched wildcard: {sel!r}')
        return list(comps), None

    # single element or iterable of elements
    try:
        iter(sel)
        return list(sel), None
    except TypeError:
        return [sel], None


# ── gbar resolution ───────────────────────────────────────────────────────────

def _resolve_gbar(comp, gbar_spec, gbar_map) -> float:
    """Return absolute Gbar (S) for a single compartment."""
    if gbar_map is not None and comp.path in gbar_map:
        return float(gbar_map[comp.path])
    if callable(gbar_spec):
        return float(gbar_spec(comp))
    return float(gbar_spec)


# ── main insert function ───────────────────────────────────────────────────────

def insert(compartments, proto, gbar, Ek=None) -> list:
    """
    Copy *proto* into each compartment, set Gbar and Ek, and connect.

    Parameters
    ----------
    compartments : str | ObjId | list | dict
        Compartments to insert into.  See module docstring for accepted forms.
    proto : moose.HHChannel
        Prototype element from :func:`_proto.make_prototype`.
    gbar : float | callable | dict
        Conductance in **Siemens**.

        * ``float``    — same value for every compartment.
        * ``callable`` — ``gbar(comp) -> float``; called per compartment.
          Use with :func:`_geometry.distance_from_soma` for gradients.
        * ``dict``     — supply directly via the *compartments* dict form.

        To specify conductance density (S/m²) multiply by surface area::

            from moose.channels import surface_area
            gbar=lambda c: density * surface_area(c)

    Ek : float, optional
        Reversal potential (V).  Defaults to the prototype's Ek value.

    Returns
    -------
    list of moose.HHChannel
        The inserted channel copies, one per compartment, in the same order
        as the resolved compartment list.
    """
    import moose

    comps, gbar_map = _resolve_compartments(compartments)
    if Ek is None:
        Ek = proto.Ek

    # proto.Gbar holds the Q10 gbar scale factor (1.0 at reference temperature)
    gbar_scale = proto.Gbar

    results = []
    for comp in comps:
        g    = _resolve_gbar(comp, gbar, gbar_map)
        # moose.copy returns a vec; index [0] gives the element
        copy = moose.copy(proto, comp, proto.name)[0]
        copy.Gbar = g * gbar_scale
        copy.Ek   = Ek
        moose.connect(copy, 'channel', comp, 'channel')
        results.append(copy)

    return results
