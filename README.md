![Python package](https://github.com/MooseNeuro/moose-core/actions/workflows/pymoose.yml/badge.svg)

![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS%20%7C%20windows-lightgrey)

# MOOSE

MOOSE is the Multiscale Object-Oriented Simulation Environment. It is designed
to simulate neural systems ranging from subcellular components and biochemical
reactions to complex models of single neurons, circuits, and large networks.
MOOSE can operate at many levels of detail, from stochastic chemical
computations, to multicompartment single-neuron models, to spiking neuron
network models.

MOOSE is multiscale: It can do all these calculations together. For example
it handles interactions seamlessly between electrical and chemical signaling.
MOOSE is object-oriented. Biological concepts are mapped into classes, and
a model is built by creating instances of these classes and connecting them
by messages. MOOSE also has classes whose job is to take over difficult
computations in a certain domain, and do them fast. There are such solver
classes for stochastic and deterministic chemistry, for diffusion, and for
multicompartment neuronal models.

MOOSE is a simulation environment, not just a numerical engine: It provides
data representations and solvers (of course!), but also a scripting interface
with Python, graphical displays with Matplotlib, PyQt, and VPython, and
support for many model formats. These include SBML, NeuroML, GENESIS kkit
and cell.p formats, HDF5 and NSDF for data writing.

This is the core computational engine of [MOOSE
simulator](https://github.com/BhallaLab/moose). This repository
contains C++ codebase and python interface called `pymoose`. For more
details about MOOSE simulator, visit https://moose.ncbs.res.in .

---

# What's New

- **Expanded NeuroML2 Support**: MOOSE's NeuroML2 reader now correctly
  handles V and Ca2+-dependent 2D channels (`HHChannel2D`) in NeuroML
  models. Custom ComponentType rate formulas are now evaluated with
  exprtk instead of `exec()` with numpy, along with a few minor fixes.

- **Docker-based installation**: MOOSE, JupyterLab, and JARDesigner (the
  web-based model-building GUI) are now available as a single, self-contained
  Docker image — no Python setup required, and it runs identically on
  Windows, macOS, and Linux. See
  [moose-jardesigner-docker](https://github.com/MooseNeuro/moose-jardesigner-docker)
  to get started.

# Featured Libraries

- **Ion Channel Library**: Access over 3,517 ion channel models from the
  [ICGenealogy database](https://icg.neurotheory.ox.ac.uk/) through the
  `moose.channels` module. Supported ion classes include Na, K, Ca, KCa, and
  IH. Insert channels into compartments using wildcards, lists, or
  dictionaries, with support for distance-dependent conductance. Channel
  metadata includes both `modeldb_id` (ModelDB reference) and `icg_id`
  (unique ICGenealogy identifier) for precise channel identification.

- **Morphology Library**: The `moose.morphologies` module simplifies loading
  and working with neuron morphologies. Load SWC files and access
  compartments via `.root`, `.soma`, `.compartments`, and `.select(pattern)`.
  Includes automatic re-rooting of SWC files not rooted at soma. Bundled
  morphologies from the
  [Allen Cell Types Database](https://celltypes.brain-map.org/), the
  Traub et al. 2005 thalamocortical network model, and classic published
  literature.

---

# Installation

See [docs/source/install/INSTALL.md](docs/source/install/INSTALL.md) for instructions on installation.

# Examples and Tutorials

- Have a look at examples, tutorials and demo scripts here
https://github.com/MooseNeuro/moose-examples.
- A set of jupyter notebooks with step by step examples with explanation are available here:
https://github.com/MooseNeuro/moose-notebooks.

# v4.3.1 – Incremental Release over v4.3.0 "Lavang Latika"

[`Lavang Latika`](https://en.wikipedia.org/wiki/Laung_lata) (also known as 
Lobongo Lotika or Laung Lata) is a traditional Indian sweet from Bengal, 
Eastern Uttar Pradesh, Odisha, and Bihar. It is made of flour pastry filled 
with khoya (mawa) and nuts, folded and sealed with a clove (lavang), then 
deep-fried and soaked in sugar syrup. The clove gives it a distinctive aroma.

## Quick Install

Installing released version from PyPI using `pip`

This version is available for installation via `pip`. To install the
latest release, we recommend creating a separate environment using
conda, mamba, micromamba, or miniforge to manage dependencies cleanly
and avoid conflicts with other Python packages. The `conda-forge`
channel has all the required libraries available for Linux, macOS,
and Windows.

```
conda create -n moose python=3.13 gsl hdf5 numpy vpython matplotlib -c conda-forge
```
```
conda activate moose
```

```
pip install pymoose
```

## Post installation

You can check that moose is installed and initializes correctly by running:

```
$ python -c "import moose; ch = moose.HHChannel('ch'); moose.le()"
```

This should show

```
Elements under /
    /Msgs
    /clock
    /classes
    /postmaster
    /ch
```

Now you can import moose in a Python script or interpreter with the statement:

```
>>> import moose
```
## Updates in 4.3.1

### Bug Fixes
- Fixed `moose.element()` to return the correct MOOSE object type
  instead of a generic object
- Fixed boolean field assignment to accept Python integers 0 and 1
  in addition to True/False
- Fixed an issue where valid very small time constant (tau) values
  were incorrectly treated as singular in HH gate expressions
- Fixed ICG channel prototypes producing NaN values during simulation
  when copied from a prototype in the library

### Improvements
- Reinstated `setField` function for backward compatibility with
  existing scripts
- Added `plotMorphology` and `plotMorphologyGraph` utilities for
  quick visual inspection of loaded neuron morphologies

## What's New in 4.3.0
 
### Ion Channel Library
 
Access over 3,517 ion channel models from the
[ICGenealogy database](https://icg.neurotheory.ox.ac.uk/) through the new
`moose.channels` module. Supported ion classes include Na, K, Ca, KCa,
and IH. Insert channels into compartments using wildcards, lists, or
dictionaries, with support for distance-dependent conductance.
 
Channel metadata includes both `modeldb_id` (ModelDB reference) and
`icg_id` (unique ICGenealogy identifier) for precise channel identification.
 
**Features:**
- Search, info, and make_prototype accept `icg_id` as an alternative to `modeldb_id`
- Simplified prototype naming format: `{suffix}_{modeldb_id}`
- New `get_icg_id` function to retrieve ICG identifier for a channel
### Morphology Library
 
The new `moose.morphologies` module simplifies loading and working with
neuron morphologies. Load SWC files and access compartments via `.root`,
`.soma`, `.compartments`, and `.select(pattern)`. Includes automatic
re-rooting of SWC files not rooted at soma.
 
**Bundled morphologies from:**
- [Allen Cell Types Database](https://celltypes.brain-map.org/)
- Traub et al. 2005 thalamocortical network model
- Classic published literature

**Utilities:**
- Convert GENESIS `.p` files to SWC format (`moose.swc_utils.p_to_swc`)

### Bug Fixes
 
- Python's `**` operator now works in MOOSE expressions
  (e.g., `func.expr = 'x0**2'`), in addition to the existing `^` operator
- Fixed `ReadSwc` to detect and handle 3-point soma and linear soma chains
- Fixed `HHGateF2D::lookupB` not setting voltage and concentration
  values from input vector
  
### Documentation
 
- Updated Ubuntu build instructions with clearer steps
- Fixed MOOSE website address in README
 
## Credits and Citations
 
### Ion Channel Library
 
The channel parameters and omnimodel formulation are the work of the
**ICGenealogy project** and the **Vogels group** at IST Austria.
 
If you use `moose.channels` in your research, please cite:
 
> Chintaluri, C., Podlaski, W., Bozelos, P. A., Gonçalves, P. J.,
> Lueckmann, J.-M., Macke, J. H., & Vogels, T. P. (2025).
> **An ion channel omnimodel for standardized biophysical neuron modelling.**
> *bioRxiv*. https://doi.org/10.1101/2025.10.03.680368
 
and the IonChannelGenealogy database:
 
> Podlaski, W. F., Seeholzer, A., Groschner, L. N., Miesenboeck, G.,
> Ranjan, R., & Vogels, T. P. (2017).
> **Mapping the function of neuronal ion channels in model and experiment.**
> *eLife*, 6, e22152.
> https://doi.org/10.7554/eLife.22152
 
The ICG web application and channel specification sheets are available at:
https://icg.neurotheory.ox.ac.uk/
 
### Morphology Utilities (ShapeShifter)
> Developed by **Prof. Avrama Blackwell and her team**, George Mason University.
> **ShapeShifter: a morphology processing utility for compartmental neuron models.**
> https://github.com/neurord/ShapeShifter

> **Used in:** `moose.swc_utils`, `moose.morphologies` (GENESIS `.p` file support),
> `python/moose/ShapeShifter/` 

If you use morphology conversion or reduction features in your research,
please acknowledge **Prof. Avrama Blackwell's group** and the ShapeShifter project.

# LICENSE

MOOSE is released under GPLv3.
