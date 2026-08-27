"""Structured account of what a load did and did not cover.

The whole point of the new reader is to never silently mis-simulate: whatever
we cannot map faithfully must be visible. A ``LoadReport`` is returned (and
attached to the handler) so callers can inspect coverage programmatically and
so tests can track it as a regression metric.
"""

from dataclasses import dataclass, field


@dataclass
class LoadReport:
    filepath: str = ''
    loadpath: str = ''

    # counts of what mapped, and how
    reactions_native: int = 0      # Reac / MMenz
    reactions_function: int = 0    # arbitrary rate law via Function
    rate_rules: int = 0
    assignment_rules: int = 0

    normalized: list = field(default_factory=list)

    # things we could not represent (each entry is a human-readable reason)
    unsupported: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def unsupported_add(self, msg):
        self.unsupported.append(msg)

    @property
    def fully_supported(self):
        return not self.unsupported

    def summary(self):
        lines = [
            f'SBML load report for {self.filepath} -> {self.loadpath}',
            f'  reactions: {self.reactions_native} native, {self.reactions_function} via Function',
            f'  rules: {self.rate_rules} rate, {self.assignment_rules} assignment',
        ]
        if self.unsupported:
            lines.append(f'  UNSUPPORTED ({len(self.unsupported)}):')
            lines += ['    - ' + u for u in self.unsupported]
        if self.warnings:
            lines.append(f'  warnings ({len(self.warnings)}):')
            lines += ['    - ' + w for w in self.warnings]
        return '\n'.join(lines)

    def __str__(self):
        return self.summary()


@dataclass
class WriteReport:
    """Structured account of what :mod:`writer` did and did not cover, the
    write-side counterpart to :class:`LoadReport`."""

    modelpath: str = ''
    filepath: str = ''

    compartments: int = 0
    species: int = 0
    diffusing_species: int = 0
    reactions: int = 0          # Reac
    enz_reactions: int = 0      # MMenz + Enz (SBML Reaction objects emitted)
    rate_rules: int = 0
    assignment_rules: int = 0

    unsupported: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def unsupported_add(self, msg):
        self.unsupported.append(msg)

    @property
    def fully_supported(self):
        return not self.unsupported

    def summary(self):
        lines = [
            f'SBML write report for {self.modelpath} -> {self.filepath}',
            f'  compartments: {self.compartments}, species: {self.species} '
            f'({self.diffusing_species} diffusing)',
            f'  reactions: {self.reactions} native Reac, {self.enz_reactions} enzymatic',
            f'  rules: {self.rate_rules} rate, {self.assignment_rules} assignment',
        ]
        if self.unsupported:
            lines.append(f'  UNSUPPORTED ({len(self.unsupported)}):')
            lines += ['    - ' + u for u in self.unsupported]
        if self.warnings:
            lines.append(f'  warnings ({len(self.warnings)}):')
            lines += ['    - ' + w for w in self.warnings]
        return '\n'.join(lines)

    def __str__(self):
        return self.summary()
