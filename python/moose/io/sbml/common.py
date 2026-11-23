"""Shared SBML reaction helpers and internal reader/writer metadata.

These are used by the reader, the symbolic analyzer and the verifier, all of
which otherwise re-wrote the same ``range(reac.getNumReactants())`` loops.
"""

# Private Annotator child on reader-generated inputs; not biological notes.
INPUT_MIRROR_INFO = '_sbml_input_info'
INPUT_MIRROR_TAG = 'moose.sbml.input_mirror:1'


def stoich(ref):
    """Stoichiometry of a SpeciesReference, defaulting to 1 when unset."""
    return ref.getStoichiometry() if ref.isSetStoichiometry() else 1.0


def participants(reac):
    """Return ``(reactants, products, modifiers)`` for a reaction, where
    reactants/products are ``(species_id, stoichiometry)`` tuples and modifiers
    are species ids."""
    subs = [(reac.getReactant(i).getSpecies(), stoich(reac.getReactant(i)))
            for i in range(reac.getNumReactants())]
    prds = [(reac.getProduct(i).getSpecies(), stoich(reac.getProduct(i)))
            for i in range(reac.getNumProducts())]
    mods = [reac.getModifier(i).getSpecies()
            for i in range(reac.getNumModifiers())]
    return subs, prds, mods
