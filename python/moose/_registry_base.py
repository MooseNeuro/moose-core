"""
moose._registry_base
=====================
Shared base for file-based bundled-asset registries used by
``moose.morphologies`` and ``moose.models``.

Usage in a subpackage registry module::

    from moose._registry_base import Registry

    _registry = Registry('Morphology', 'moose.morphologies.load()')
    _registry.add([
        {'name': 'CA1_pyramidal', 'filename': 'CA1.swc', ...},
    ])

    get        = _registry.get
    all_entries = _registry.all_entries
"""


class Registry:
    """
    Name-indexed registry of bundled asset metadata dicts.

    Parameters
    ----------
    kind : str
        Human-readable asset kind used in error messages (e.g. ``'Morphology'``).
    load_hint : str
        Suggested call shown in the KeyError message when a name is not found
        (e.g. ``'moose.morphologies.load()'``).
    """

    def __init__(self, kind: str, load_hint: str):
        self._kind      = kind
        self._hint      = load_hint
        self._entries: list[dict] = []
        self._by_name:  dict[str, dict] = {}

    def add(self, entries: list[dict]) -> None:
        """Register a list of entry dicts.  Each must have a ``'name'`` key."""
        for entry in entries:
            name = entry['name']
            self._entries.append(entry)
            self._by_name[name] = entry

    def get(self, name: str) -> dict:
        """Return the entry for *name*, or raise ``KeyError``."""
        if name not in self._by_name:
            available = list(self._by_name)
            raise KeyError(
                f'{self._kind} {name!r} not found in bundled registry.\n'
                f'Available: {available}\n'
                f'To load an arbitrary file use {self._hint} with a file path.'
            )
        return self._by_name[name]

    def all_entries(self) -> list[dict]:
        """Return a copy of the full entry list."""
        return list(self._entries)
