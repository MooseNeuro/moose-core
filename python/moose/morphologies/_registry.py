"""
moose.morphologies._registry
=============================
Bundled SWC morphology files shipped with pymoose.

Each entry dict may contain:
  name        str   Short identifier used in moose.morphologies.load('name', ...)
  filename    str   SWC filename inside moose/morphologies/data/swc/
  species     str   Species (e.g. 'rat', 'mouse', 'human')
  cell_type   str   Cell type (e.g. 'CA1 pyramidal', 'L5 pyramidal')
  region      str   Brain region
  source      str   Original database / publication
  description str   One-line description
"""

from moose._registry_base import Registry

_registry = Registry('Morphology', 'moose.morphologies.load()')

_registry.add([
    {
        'name':        'traub91_CA1',
        'filename':    'swc/traub91_CA1.swc',
        'species':     'rat',
        'cell_type':   'CA1 pyramidal',
        'region':      'hippocampus CA1',
        'source':      'Traub et al. 1991, J Neurophysiol 66:635-650',
        'description': '19-compartment CA1 pyramidal (Traub et al. 1991)',
    },
    {
        'name':        'traub91_CA3',
        'filename':    'swc/traub91_CA3.swc',
        'species':     'rat',
        'cell_type':   'CA3 pyramidal',
        'region':      'hippocampus CA3',
        'source':      'Traub et al. 1991, J Neurophysiol 66:635-650',
        'description': '19-compartment CA3 pyramidal (Traub et al. 1991)',
    },
    {
        'name':        'purk_eds1994_full',
        'filename':    'swc/purk_eds1994_full.swc',
        'species':     'guinea pig',
        'cell_type':   'Purkinje',
        'region':      'cerebellum',
        'source':      'De Schutter & Bower 1994, J Neurophysiol 71:375-400',
        'description': '1600-compartment Purkinje cell (De Schutter & Bower 1994)',
    },
    {
        'name':        'gran_bhalla1991_ob',
        'filename':    'swc/gran_bhalla1991_ob.swc',
        'species':     'rat',
        'cell_type':   'granule',
        'region':      'olfactory bulb',
        'source':      'Bhalla & Bower 1993, J Neurophysiol 69:1948-1965',
        'description': '112-compartment olfactory bulb granule cell (Bhalla 1991)',
    },
    {
        'name':        'mit_bhalla1991',
        'filename':    'swc/mit_bhalla1991.swc',
        'species':     'rat',
        'cell_type':   'mitral',
        'region':      'olfactory bulb',
        'source':      'Bhalla & Bower 1993, J Neurophysiol 69:1948-1965',
        'description': '286-compartment detailed mitral cell (Bhalla 1991)',
    },
    {
        'name':        'mit_davison_reduced',
        'filename':    'swc/mit_davison_reduced.swc',
        'species':     'rat',
        'cell_type':   'mitral',
        'region':      'olfactory bulb',
        'source':      'Davison et al. 2003, J Comput Neurosci 15:375-384',
        'description': '7-compartment reduced mitral cell (Davison/Bhalla/Bower)',
    },
    {
        'name':        'gran_migliore_olfactory',
        'filename':    'swc/gran_migliore_olfactory.swc',
        'species':     'rat',
        'cell_type':   'granule',
        'region':      'olfactory bulb',
        'source':      'Migliore & Shepherd 2008, PLoS Comput Biol 4:e1000011',
        'description': '2-compartment olfactory bulb granule cell (Migliore & Shepherd 2008)',
    },
])

get         = _registry.get
all_entries = _registry.all_entries
