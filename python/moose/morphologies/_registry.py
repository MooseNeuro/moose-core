"""
moose.morphologies._registry
=============================
Bundled SWC morphology files shipped with pymoose.

Each entry dict may contain:
  name        str   Short identifier used in moose.morphologies.load('name', ...)
  filename    str   SWC filename inside moose/morphologies/data/
  species     str   Species (e.g. 'rat', 'mouse', 'human')
  cell_type   str   Cell type (e.g. 'CA1 pyramidal', 'L5 pyramidal')
  region      str   Brain region
  source      str   Original database / publication
  description str   One-line description
"""

from moose._registry_base import Registry

_registry = Registry('Morphology', 'moose.morphologies.load()')

_registry.add([
    # Entries will be added here as SWC files are curated and bundled.
    # Example (uncomment and add file to data/ when ready):
    #
    # {
    #     'name':        'CA1_pyramidal',
    #     'filename':    'CA1_pyramidal_Golding2001.swc',
    #     'species':     'rat',
    #     'cell_type':   'CA1 pyramidal',
    #     'region':      'hippocampus CA1',
    #     'source':      'NeuroMorpho NMO_00001',
    #     'description': 'CA1 pyramidal neuron (Golding et al. 2001)',
    # },
])

get         = _registry.get
all_entries = _registry.all_entries
