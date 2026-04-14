"""
moose.channels
==============
Search the ICGenealogy channel database and insert ion channel models into
MOOSE compartments as ``HHChannel`` objects.

Channels are built once as **prototypes** under ``/library`` so that gate
tables are shared across all compartments that use the same channel type.
``moose.copy()`` is used to place lightweight copies into individual
compartments, which is significantly faster and more memory-efficient than
constructing each channel independently from Python.

Quick start
-----------
::

    import moose
    import moose.channels as chan
    import moose.morphologies as morph

    # Explore the database
    chan.list_ion_classes()
    results = chan.search(author='Traub', ion_class='Na')
    chan.info(results[0])

    # Load morphology
    cell = morph.load('CA1_pyramidal', '/neuron')

    # Prototype is created once, inserted into every matching compartment
    chan.load(cell.select('##[TYPE=Compartment]'),
              model_id=45539, suffix='naf',
              gbar=120e-12, Ek=0.05)

    # Distance-dependent gradient in apical dendrites
    chan.load(cell.select('apic#'),
              model_id=45539, suffix='naf',
              Ek=0.05,
              gbar=lambda c: 40e-12 * (
                  1 - morph.distance_from_soma(c, cell.soma) / 800e-6))

    # K channel everywhere
    chan.load('/neuron/##[TYPE=Compartment]',
              model_id=45539, suffix='kdr',
              gbar=36e-12, Ek=-0.077)
"""

from pathlib import Path

# Lazy-loaded singleton database — populated on first use
_db = None


def _get_db():
    """Return (and cache) the default ICGChannelDB instance."""
    global _db
    if _db is None:
        from moose.channels._db import ICGChannelDB
        data = Path(__file__).parent / 'data'
        _db = ICGChannelDB(
            data / 'channel_db.csv',
            data / 'modeldb_popularity.csv',
        )
    return _db


# ── public search / info API ──────────────────────────────────────────────────

def list_ion_classes() -> list:
    """Return sorted list of ion classes in the database: Na, K, Ca, KCa, IH."""
    return _get_db().ion_classes()


def search(author=None, year=None, model_id=None,
           ion_class=None, suffix=None, show=True) -> list:
    """
    Search the ICG channel database.

    Parameters
    ----------
    author : str, optional
        Partial, case-insensitive author name (e.g. ``'Traub'``).
    year : int, optional
        Publication year.
    model_id : int, optional
        Exact ModelDB numeric ID.
    ion_class : str, optional
        ``'Na'``, ``'K'``, ``'Ca'``, ``'KCa'``, or ``'IH'``.
    suffix : str, optional
        Partial NMODL SUFFIX name (e.g. ``'naf'``, ``'kdr'``).
    show : bool, optional
        Print a formatted result table (default ``True``).

    Returns
    -------
    list of dict
        Each entry: ``{'model_id': int, 'meta': dict, 'channels': {suffix: [rows]}}``.
    """
    db      = _get_db()
    results = db.search(author=author, year=year, model_id=model_id,
                        ion_class=ion_class, suffix=suffix)
    if show:
        db.show_results(results)
    return results


def info(result_or_model_id, suffix=None):
    """
    Print a gate/power summary for one model.

    Parameters
    ----------
    result_or_model_id : dict or int
        A result dict from :func:`search`, or a ModelDB integer ID.
    suffix : str, optional
        If *result_or_model_id* is an int, narrow the display to this suffix.
    """
    db = _get_db()
    if isinstance(result_or_model_id, int):
        results = db.search(model_id=result_or_model_id,
                            suffix=suffix)
        if not results:
            raise KeyError(f'Model {result_or_model_id} not found in database')
        result = results[0]
    else:
        result = result_or_model_id
    db.show_channels(result)


def get_expressions(model_id: int, suffix: str,
                    gate_var: str, sm_model='best') -> tuple:
    """
    Return ``(infExpr, tauExpr)`` strings for a gate without creating MOOSE
    objects.  Useful for inspection or custom channel setup.
    """
    return _get_db().get_expressions(model_id, suffix, gate_var, sm_model)


# ── prototype management ──────────────────────────────────────────────────────

def make_prototype(model_id: int, suffix: str, sm_model='best',
                   temperature=None):
    """
    Build (or retrieve) an HHChannel prototype under ``/library``.

    The call is **idempotent**: repeated calls with the same arguments return
    the same element without rebuilding it.

    Parameters
    ----------
    model_id : int
    suffix : str
    sm_model : int or 'best'
    temperature : float, optional
        Simulation temperature in °C.  Defaults to the omnimodel reference
        temperature (6.3 °C).  When different from the reference, Q10
        corrections are baked into the prototype: tau scaling is embedded in
        the expression coefficient; Gbar scaling is stored in ``proto.Gbar``
        and applied at insert time.

    Returns
    -------
    moose.HHChannel
        Prototype at ``/library/<ion>_<suffix>_<model_id>_T<temp>``.
    """
    from moose.channels._proto import make_prototype as _make, T_REF
    T = T_REF if temperature is None else temperature
    return _make(_get_db(), model_id, suffix, sm_model, temperature=T)


def list_prototypes() -> list:
    """Return metadata list of all HHChannel prototypes in ``/library``."""
    from moose.channels._proto import list_prototypes as _list
    return _list()


# ── insertion ─────────────────────────────────────────────────────────────────

def insert(compartments, proto, gbar, Ek=None) -> list:
    """
    Copy *proto* into compartments and connect each copy.

    Parameters
    ----------
    compartments : str | moose element | list | dict
        * ``str``   — wildcard pattern passed to ``moose.wildcardFind``.
        * element   — single compartment ObjId.
        * ``list``  — pre-resolved list of compartment elements.
        * ``dict``  — ``{comp: gbar_S}``; *gbar* argument is ignored.
    proto : moose.HHChannel
        Prototype from :func:`make_prototype`.
    gbar : float | callable
        * ``float``    — same absolute conductance (S) for all compartments.
        * ``callable`` — ``gbar(comp) -> float`` (S); called per compartment.
          Use with :func:`surface_area` and :func:`distance_from_soma` for
          density- or distance-based gradients::

              gbar=lambda c: 120e-12 * moose.channels.surface_area(c)
    Ek : float, optional
        Reversal potential (V).  Defaults to the prototype's Ek.

    Returns
    -------
    list of moose.HHChannel
    """
    from moose.channels._insert import insert as _insert
    return _insert(compartments, proto, gbar, Ek)


def load(compartments, *, model_id: int, suffix: str,
         gbar=1.0, Ek=None, sm_model='best', temperature=None) -> list:
    """
    One-step convenience: build prototype (if needed) and insert into
    compartments.

    This is equivalent to::

        proto = moose.channels.make_prototype(model_id, suffix, sm_model,
                                              temperature=temperature)
        moose.channels.insert(compartments, proto, gbar, Ek)

    Parameters
    ----------
    compartments : str | element | list | dict
        Compartment selector (see :func:`insert`).
    model_id : int
    suffix : str
    gbar : float | callable
        Conductance in Siemens.
    Ek : float, optional
        Reversal potential (V).  Auto-detected from ion class if omitted.
    sm_model : int or 'best'
        SM variant to use.
    temperature : float, optional
        Simulation temperature in °C.  Defaults to the reference temperature
        (6.3 °C).  Q10 corrections are applied automatically when this differs
        from the reference.

    Returns
    -------
    list of moose.HHChannel
    """
    proto = make_prototype(model_id, suffix, sm_model, temperature=temperature)
    return insert(compartments, proto, gbar, Ek)


__all__ = [
    'list_ion_classes', 'search', 'info', 'get_expressions',
    'make_prototype', 'list_prototypes',
    'insert', 'load',
]
