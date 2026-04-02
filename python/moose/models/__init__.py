"""
moose.models
============
Load curated reference neuron models bundled with pymoose.

Bundled models live in ``moose/models/data/`` and cover common reference
neurons used for teaching and testing (HH neuron, CA1 PC, L5 PC, etc.).
Any file readable by ``moose.loadModel`` can also be loaded via :func:`load`
by providing a filesystem path.

Quick start
-----------
::

    import moose
    import moose.models as models

    models.list()                         # show available bundled models

    model = models.load('HH_neuron', '/hh')
    model = models.load('/path/to/my_model.nml', '/cell')
"""

from pathlib import Path


def list() -> None:
    """Print a table of bundled models available for loading."""
    from moose.models._registry import all_entries
    entries = all_entries()
    if not entries:
        print('No bundled models yet.  '
              'Load any supported file with moose.models.load("/path/to/file", ...)')
        return
    print(f'\n{"Name":<24} {"Format":<8} {"Description":<40} {"Source"}')
    print('─' * 90)
    for e in entries:
        print(f'{e["name"]:<24} {e.get("format",""):<8} '
              f'{e.get("description",""):<40} {e.get("source","")}')
    print()


def load(name_or_path: str, moose_path: str,
         solver: str = 'ee') -> object:
    """
    Load a model into MOOSE.

    Parameters
    ----------
    name_or_path : str
        Short name from the bundled registry (e.g. ``'HH_neuron'``) **or**
        a filesystem path to a supported model file (``.nml``, ``.xml``,
        ``.g``, ``.p``, ``.sbml``).
    moose_path : str
        MOOSE element path where the model will be created.
    solver : str
        Chemical solver class: ``'ee'``, ``'gsl'``, or ``'gssa'``.
        Only relevant for models with chemical compartments.

    Returns
    -------
    moose element
        Root element of the loaded model.
    """
    import moose

    file_path = _resolve_path(name_or_path)
    return moose.loadModel(str(file_path), moose_path, solver)


# ── path resolution ───────────────────────────────────────────────────────────

def _resolve_path(name_or_path: str) -> Path:
    p = Path(name_or_path)
    if p.exists():
        return p

    try:
        from moose.models._registry import get as _get
        entry    = _get(name_or_path)
        data_dir = Path(__file__).parent / 'data'
        bundled  = data_dir / entry['filename']
        if bundled.exists():
            return bundled
        raise FileNotFoundError(
            f'Bundled model file {entry["filename"]!r} not found in package data.'
        )
    except KeyError:
        pass

    raise FileNotFoundError(
        f'{name_or_path!r} is neither a known bundled model name '
        f'nor an existing file path.'
    )


__all__ = ['list', 'load']
