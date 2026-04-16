"""
moose.morphologies
==================
Load neuronal morphologies into MOOSE compartment trees.

Bundled SWC files ship with pymoose in ``moose/morphologies/data/``.
Any SWC file on disk can also be loaded directly via :func:`load`.

``MorphologyResult`` wraps the loaded cell and provides:

* ``root``         — root element returned by ``moose.loadSwc()``
* ``soma``         — auto-detected root compartment
* ``compartments`` — all Compartment elements in the tree
* ``select(pat)``  — ``wildcardFind`` scoped to this cell

Quick start
-----------
::

    import moose
    import moose.morphologies as morph

    morph.list()                                  # show bundled cells

    cell = morph.load('CA1_pyramidal', '/neuron',
                      RM=1.0, RA=2.5, CM=0.01)

    # By filesystem path
    cell = morph.load('/path/to/my_cell.swc', '/neuron')

    # Select compartment subsets
    soma  = cell.soma
    apics = cell.select('apic#')
    all_c = cell.select('##[TYPE=Compartment]')
    print(f'{len(cell.compartments)} compartments loaded')
"""

from pathlib import Path


# ── MorphologyResult ──────────────────────────────────────────────────────────

class MorphologyResult:
    """
    Wrapper around a MOOSE cell loaded from an SWC file.

    Attributes
    ----------
    root : moose element
        Root element of the loaded cell (returned by ``moose.loadSwc()``).
    soma : moose element
        First compartment whose parent is not a Compartment (root compartment).
    compartments : list
        All ``Compartment`` elements in the cell tree.
    """

    def __init__(self, root):
        import moose
        self.root         = root
        self.compartments = moose.wildcardFind(
            f'{root.path}/##[TYPE=Compartment]')
        self.soma         = self._find_soma()

    def _find_soma(self):
        """Return the topmost compartment (parent is not a Compartment)."""
        import moose

        def _is_comp(el):
            try:
                return el.className in ('Compartment', 'SymCompartment')
            except Exception:
                return False

        for comp in self.compartments:
            if not _is_comp(moose.element(comp.parent)):
                return comp
        # Fallback: first compartment
        return self.compartments[0] if self.compartments else self.root

    def select(self, pattern: str) -> list:
        """
        Run ``moose.wildcardFind`` scoped to this cell.

        The pattern is appended to the cell root path, so you can use
        short forms like ``'apic#'`` or ``'##[TYPE=Compartment]'`` without
        specifying the full path.

        Parameters
        ----------
        pattern : str
            Wildcard pattern relative to the cell root
            (e.g. ``'dend#'``, ``'##[TYPE=Compartment]'``).

        Returns
        -------
        list of moose elements
        """
        import moose
        return moose.wildcardFind(f'{self.root.path}/{pattern}')

    def __repr__(self):
        return (f'MorphologyResult(root={self.root.path!r}, '
                f'soma={self.soma.path!r}, '
                f'compartments={len(self.compartments)})')


# ── public API ────────────────────────────────────────────────────────────────

def list() -> None:
    """Print a table of bundled morphologies available for loading."""
    from moose.morphologies._registry import all_entries
    entries = all_entries()
    if not entries:
        print('No bundled morphologies yet.  '
              'Load any SWC file with moose.morphologies.load("/path/to/file.swc", ...)')
        return
    print(f'\n{"Name":<22} {"Species":<10} {"Cell type":<22} {"Region":<20} {"Source"}')
    print('─' * 90)
    for e in entries:
        print(f'{e["name"]:<22} {e.get("species",""):<10} '
              f'{e.get("cell_type",""):<22} {e.get("region",""):<20} '
              f'{e.get("source","")}')
    print()


def load(name_or_path: str, moose_path: str,
         RM: float = 1.0, RA: float = 1.0, CM: float = 0.01,
         max_len: float = 0.1, f: float = 0.0,
         rad_diff: float = 0.1) -> MorphologyResult:
    """
    Load an SWC morphology into MOOSE and return a :class:`MorphologyResult`.

    Parameters
    ----------
    name_or_path : str
        Either a short name from the bundled registry (e.g.
        ``'CA1_pyramidal'``) **or** a filesystem path to an SWC file.
    moose_path : str
        MOOSE element path where the cell will be created (e.g. ``'/neuron'``).
    RM : float
        Specific membrane resistance (Ω·m²).  Default 1.0.
    RA : float
        Specific axial resistance (Ω·m).  Default 1.0.
    CM : float
        Specific membrane capacitance (F/m²).  Default 0.01.
    max_len : float
        Maximum electrotonic length per compartment; ``moose.loadSwc`` uses
        this to condense the morphology.  Pass ``None`` to skip condensation.
    f : float
        Frequency (Hz) for AC lambda calculation; 0 = DC (default).
    rad_diff : float
        Maximum fractional radius difference for condensation merging.

    Returns
    -------
    MorphologyResult
    """
    import moose

    swc_path = _resolve_path(name_or_path)
    root = moose.loadSwc(str(swc_path), moose_path,
                         RM=RM, RA=RA, CM=CM,
                         max_len=max_len, f=f, rad_diff=rad_diff)
    return MorphologyResult(root)


# ── path resolution ───────────────────────────────────────────────────────────

def _resolve_path(name_or_path: str) -> Path:
    """
    Return a Path to an SWC file.

    Checks (in order):
    1. Bundled registry by short name.
    2. Filesystem path as given.
    """
    p = Path(name_or_path)
    if p.exists():
        return p

    # Try bundled registry
    try:
        from moose.morphologies._registry import get as _get
        entry    = _get(name_or_path)
        data_dir = Path(__file__).parent / 'data'
        bundled  = data_dir / entry['filename']
        if bundled.exists():
            return bundled
        raise FileNotFoundError(
            f'Bundled SWC file {entry["filename"]!r} not found in package data. '
            f'Re-install pymoose or provide the file path directly.'
        )
    except KeyError:
        pass

    raise FileNotFoundError(
        f'{name_or_path!r} is neither a known bundled morphology name '
        f'nor an existing file path.'
    )


def surface_area(comp) -> float:
    """Lateral surface area of a cylindrical compartment: π × diameter × length (m²)."""
    from moose.morphologies._geometry import surface_area as _sa
    return _sa(comp)


def distance_from_soma(comp, soma=None) -> float:
    """
    Path distance (m) from *soma* to *comp* along the morphology tree.

    If *soma* is ``None`` it is auto-detected as the root compartment.
    """
    from moose.morphologies._geometry import distance_from_soma as _dfs
    return _dfs(comp, soma)


__all__ = ['MorphologyResult', 'list', 'load', 'surface_area', 'distance_from_soma',
           'BUNDLED_GENESIS']


# ── GENESIS source files ──────────────────────────────────────────────────────

from pathlib import Path as _Path

_GEN_DIR = _Path(__file__).parent / 'data' / 'genesis'

BUNDLED_GENESIS = {
    'mit_bhalla1991':          str(_GEN_DIR / 'mit_bhalla1991.p'),
    'mit_davison_reduced':     str(_GEN_DIR / 'mit_davison_reduced.p'),
    'gran_migliore_olfactory': str(_GEN_DIR / 'gran_migliore_olfactory.p'),
}
