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
              modeldb_id=45539, suffix='naf',
              gbar=120e-12, Ek=0.05)

    # Distance-dependent gradient in apical dendrites
    chan.load(cell.select('apic#'),
              modeldb_id=45539, suffix='naf',
              Ek=0.05,
              gbar=lambda c: 40e-12 * (
                  1 - morph.distance_from_soma(c, cell.soma) / 800e-6))

    # K channel everywhere
    chan.load('/neuron/##[TYPE=Compartment]',
              modeldb_id=45539, suffix='kdr',
              gbar=36e-12, Ek=-0.077)
"""

from pathlib import Path
from moose.channels._insert import insert

# Lazy-loaded singleton database — populated on first use
_db = None


def _get_db():
    """Return (and cache) the default ICGChannelDB instance."""
    global _db
    if _db is None:
        from moose.channels._db import ICGChannelDB
        data = Path(__file__).parent / 'data'
        meta_csv = data / 'icg_channel_meta.csv'
        if not meta_csv.exists():
            meta_csv = data / 'modeldb_popularity.csv'   # legacy fallback
        _db = ICGChannelDB(
            data / 'channel_db.csv',
            meta_csv,
        )
    return _db


# ── helpers ───────────────────────────────────────────────────────────────────

def _resolve(modeldb_id, suffix, icg_id):
    """Resolve (modeldb_id, suffix) from either explicit values or icg_id."""
    if icg_id is not None:
        return _get_db().resolve_icg_id(icg_id)
    if modeldb_id is None:
        raise ValueError('modeldb_id is required when icg_id is not provided')
    if suffix is None:
        raise ValueError('suffix is required when icg_id is not provided')
    return int(modeldb_id), suffix


# ── public search / info API ──────────────────────────────────────────────────

def list_ion_classes() -> list:
    """Return sorted list of ion classes in the database: Na, K, Ca, KCa, IH."""
    return _get_db().ion_classes()


def search(author=None, year=None, modeldb_id=None,
           ion_class=None, suffix=None, icg_id=None, show=True) -> list:
    """
    Search the ICG channel database.

    Parameters
    ----------
    author : str, optional
        Case-insensitive author surname (e.g. ``'Traub'``,
        ``'De Schutter'``). The whole surname must match; append ``*``
        for a prefix match (e.g. ``'Trau*'``). Titles are not searched.
    year : int, optional
        Publication year.
    modeldb_id : int, optional
        Exact ModelDB numeric ID.
    ion_class : str, optional
        ``'Na'``, ``'K'``, ``'Ca'``, ``'KCa'``, or ``'IH'``.
    suffix : str, optional
        Partial NMODL SUFFIX name (e.g. ``'naf'``, ``'kdr'``).
    icg_id : int, optional
        Exact ICGenealogy channel ID.
    show : bool, optional
        Print a formatted result table (default ``True``).

    Returns
    -------
    list of dict
        Each entry: ``{'modeldb_id': int, 'meta': dict, 'channels': {suffix: [rows]}}``.
    """
    db      = _get_db()
    results = db.search(author=author, year=year, modeldb_id=modeldb_id,
                        ion_class=ion_class, suffix=suffix, icg_id=icg_id)
    if show:
        db.show_results(results)
    return results


def info(result_or_modeldb_id=None, suffix=None, *, icg_id=None):
    """
    Print a gate/power summary for one model.

    Parameters
    ----------
    result_or_modeldb_id : dict or int, optional
        A result dict from :func:`search`, or a ModelDB integer ID.
        Required unless *icg_id* is provided.
    suffix : str, optional
        Narrow the display to this suffix when using modeldb_id.
    icg_id : int, optional
        ICGenealogy channel ID as an alternative to modeldb_id + suffix.
    """
    db = _get_db()
    if icg_id is not None:
        mid, suf = db.resolve_icg_id(icg_id)
        results = db.search(modeldb_id=mid, suffix=suf)
    elif isinstance(result_or_modeldb_id, dict):
        db.show_channels(result_or_modeldb_id)
        return
    elif result_or_modeldb_id is not None:
        results = db.search(modeldb_id=result_or_modeldb_id, suffix=suffix)
    else:
        raise ValueError('Provide either a result dict, modeldb_id, or icg_id')
    if not results:
        raise KeyError(f'Channel not found in database '
                       f'(icg_id={icg_id})'
                       if icg_id is not None else
                       f'(modeldb_id={result_or_modeldb_id}, suffix={suffix})')
    db.show_channels(results[0])


def get_icg_id(modeldb_id=None, suffix=None) -> int:
    """
    Return the ICGenealogy channel ID for a given ``(modeldb_id, suffix)`` pair.

    Parameters
    ----------
    modeldb_id : int
    suffix : str

    Returns
    -------
    int
        ICGenealogy channel ID.
    """
    mid, suf = _resolve(modeldb_id, suffix, icg_id=None)
    return _get_db().get_icg_id(mid, suf)


def get_expressions(modeldb_id=None, suffix=None,
                    gate_var=None, sm_model='best', *, icg_id=None) -> tuple:
    """
    Return ``(infExpr, tauExpr)`` strings for a gate without creating MOOSE
    objects.  Useful for inspection or custom channel setup.

    Parameters
    ----------
    modeldb_id : int, optional
    suffix : str, optional
    gate_var : str
        Gate variable name (e.g. ``'m'``, ``'h'``).
    sm_model : int or 'best'
    icg_id : int, optional
        ICGenealogy channel ID as an alternative to modeldb_id + suffix.
    """
    if gate_var is None:
        raise ValueError('gate_var is required')
    mid, suf = _resolve(modeldb_id, suffix, icg_id)
    return _get_db().get_expressions(mid, suf, gate_var, sm_model)


# ── prototype management ──────────────────────────────────────────────────────

def make_prototype(modeldb_id=None, suffix=None, sm_model='best',
                   temperature=None, icg_id=None):
    """
    Build (or retrieve) an HHChannel prototype under ``/library``.

    The call is **idempotent**: repeated calls with the same arguments return
    the same element without rebuilding it.

    Parameters
    ----------
    modeldb_id : int, optional
    suffix : str, optional
    sm_model : int or 'best'
    temperature : float, optional
        Simulation temperature in °C.  Defaults to the omnimodel reference
        temperature (6.3 °C).  When different from the reference, Q10
        corrections are baked into the prototype: tau scaling is embedded in
        the expression coefficient; Gbar scaling is stored in ``proto.Gbar``
        and applied at insert time.
    icg_id : int, optional
        ICGenealogy channel ID as an alternative to modeldb_id + suffix.

    Returns
    -------
    moose.HHChannel
        Prototype at ``/library/<suffix>_<modeldb_id>``.
    """
    from moose.channels._proto import make_prototype as _make, T_REF
    mid, suf = _resolve(modeldb_id, suffix, icg_id)
    T = T_REF if temperature is None else temperature
    return _make(_get_db(), mid, suf, sm_model, temperature=T)


# ── insertion ─────────────────────────────────────────────────────────────────


def load(compartments, *, modeldb_id=None, suffix=None,
         gbar=1.0, Ek=None, sm_model='best', temperature=None,
         icg_id=None) -> list:
    """
    One-step convenience: build prototype (if needed) and insert into
    compartments.

    This is equivalent to::

        proto = moose.channels.make_prototype(modeldb_id, suffix, sm_model,
                                              temperature=temperature)
        moose.channels.insert(compartments, proto, gbar, Ek)

    Parameters
    ----------
    compartments : str | element | list | dict
        Compartment selector (see :func:`insert`).
    modeldb_id : int, optional
    suffix : str, optional
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
    icg_id : int, optional
        ICGenealogy channel ID as an alternative to modeldb_id + suffix.

    Returns
    -------
    list of moose.HHChannel
    """
    proto = make_prototype(modeldb_id, suffix, sm_model, temperature=temperature,
                           icg_id=icg_id)
    return insert(compartments, proto, gbar, Ek)


__all__ = [
    'list_ion_classes', 'search', 'info', 'get_icg_id', 'get_expressions',
    'make_prototype',
    'insert', 'load',
]
