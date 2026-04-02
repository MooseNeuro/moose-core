"""
moose.models._registry
=======================
Bundled NeuroML2 / GENESIS model files shipped with pymoose.

Each entry dict may contain:
  name        str   Short identifier used in moose.models.load('name', ...)
  filename    str   File inside moose/models/data/
  format      str   'nml2' | 'genesis' | 'sbml'
  description str   One-line description
  source      str   Original publication or database
"""

from moose._registry_base import Registry

_registry = Registry('Model', 'moose.models.load()')

_registry.add([
    # Entries will be added here as model files are curated and bundled.
    # Example (uncomment and add file to data/ when ready):
    #
    # {
    #     'name':        'HH_neuron',
    #     'filename':    'HH_neuron.nml',
    #     'format':      'nml2',
    #     'description': 'Single-compartment Hodgkin-Huxley neuron',
    #     'source':      'Hodgkin & Huxley (1952)',
    # },
    # {
    #     'name':        'CA1_Migliore2018',
    #     'filename':    'CA1_Migliore2018.nml',
    #     'format':      'nml2',
    #     'description': 'Detailed CA1 pyramidal neuron (Migliore et al. 2018)',
    #     'source':      'ModelDB 244688',
    # },
])

get         = _registry.get
all_entries = _registry.all_entries
