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

# Installation

See [docs/source/install/INSTALL.md](docs/source/install/INSTALL.md) for instructions on installation.

# Examples and Tutorials

- Have a look at examples, tutorials and demo scripts here
https://github.com/MooseNeuro/moose-examples.
- A set of jupyter notebooks with step by step examples with explanation are available here:
https://github.com/MooseNeuro/moose-notebooks.

# v5.0.0 – Major Release "Mysore Pak"

[`Mysore Pak`](https://en.wikipedia.org/wiki/Mysore_pak) is a rich,
ghee-based sweet that originated in the kitchens of the Mysore Palace in
Karnataka, India. Made from gram flour (besan), ghee, and sugar syrup, it
is traditionally made in two textures a dense, fudge-like version and a
lighter, porous, melt-in-the-mouth version - depending on how the mixture
is aerated during cooking.

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

## What's New in 5.0.0

### Expanded NeuroML2 Support

MOOSE's NeuroML2 reader now correctly handles V and Ca2+-dependent 2D
channels (`HHChannel2D`) in NeuroML models. Custom ComponentType rate
formulas are now evaluated with exprtk instead of `exec()` with numpy,
along with a few minor fixes.

### Docker-based Installation

MOOSE, JupyterLab, and [JARDesigner](https://github.com/MooseNeuro/jardesigner)
(the web-based model-building GUI) are now available as a single,
self-contained Docker image — no Python setup required, and it runs
identically on Windows, macOS, and Linux. See
[moose-jardesigner-docker](https://github.com/MooseNeuro/moose-jardesigner-docker)
to get started.


## Updates in 5.0.0

### Breaking Changes
- moose.readSBML() and moose.writeSBML() now use the new reader/writer
  directly. They return a single model object and raise on failure,
  instead of the previous tuple return. moose.SBML.readSBML.mooseReadSBML
  is now deprecated

### Improvements
- Replaced the SBML reader with a new, general-purpose one supporting
  a much wider range of standard model files
- Added support for loading and simulating SBML models with multiple
  compartments
- Added an SBML writer to the new reader/writer module, with broader
  support than the old legacy writer, and a round-trip with the reader
  verified to floating-point precision
- loadpath is now optional when loading an SBML model, defaulting to
  /library/{model_name}
- Added moose.NA, moose.FaradayConst, and other physical constants as
  directly accessible Python attributes
- Added a set of ready-to-use Allen Brain Database neuron morphologies
  to MOOSE's built-in library
- loadKkit() now shows a deprecation notice recommending loadModel()
- NeuroML2 ComponentType Dynamics rates are now evaluated with exprtk
  through a scratch moose.Function instead of exec() with numpy;
  expressions that cannot be translated raise UnsupportedMath
- modelpath is now optional in NML2Reader.read, defaulting to /model
- HHGate2D (2D-dependent gates) now supports specifying gate tables as
  alpha/beta or tau/inf expressions (alphaExpr/betaExpr/tauExpr/infExpr),
  the same way HHGate already does for 1D gates

### Documentation
- Converged all MOOSE-authored source files to a uniform GNU GPLv3
  license header
- Updated LICENSE file links to current gnu.org URLs

### Bug Fixes
- Fixed Dsolve objects returning the wrong path they now correctly
  report their actual location in the model tree
- Fixed creating MOOSE objects with attributes passed as keyword
  arguments (e.g. moose.Pool('/x', concInit=9.99))
- Fixed creating an object at a path already holding a different type
  silently returning the wrong object instead of raising an error
- Fixed Function expressions with more than 10 input variables
  silently ignoring variables past the 10th
- Fixed SWC morphology files that number nodes starting from 0
  (including real Allen Brain Database files) failing to load
- Fixed an inconsistent value used for the Nernst equation's R/F constant
- Fixed wildcardFind to correctly resolve . and .. in search paths
- Fixed import moose crashing when the optional pyneuroml package is
  not installed
- Fixed chemMerge failing on SBML files due to a call to a
  non-existent function
- Fixed the NeuroML2 temperature fallback returning 25 K instead of
  298.15 K when a model specifies no temperature
- Fixed no vector<vector<double>> field could be written from Python
  (e.g. assigning HHGate2D.tableA)
- Fixed a 2D gate lookup from Python crashing (e.g. HHGate2D.A([v, ca]))
- Rate ComponentTypes derived from NEURON .mod files now receive
  rateScale, the gate's Q10 factor
- Fixed a Case condition with a leading space causing NeuroML2 channels
  (e.g. Gran_NaF_98) to fail loading with IndentationError
- moose.readNML2 now takes filepath and an optional modelpath, instead
  of passing the single argument on as the file path
- Fixed Ubuntu installs failing to import moose due to the extension
  not carrying a runtime search path to its GSL dependency
- Fixed HHChannel2D/HHChannelF2D channels using a single-axis
  dependency mode (VOLT_INDEX/C1_INDEX/C2_INDEX) crashing
- Fixed a singularity check in HHGate's tau/inf expression evaluation
  that could miss near-zero values


## Featured Libraries

### Ion Channel Library

Access over 3,517 ion channel models from the
[ICGenealogy database](https://icg.neurotheory.ox.ac.uk/) through the
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

The `moose.morphologies` module simplifies loading and working with
neuron morphologies. Load SWC files and access compartments via `.root`,
`.soma`, `.compartments`, and `.select(pattern)`. Includes automatic
re-rooting of SWC files not rooted at soma.

**Bundled morphologies from:**
- [Allen Cell Types Database](https://celltypes.brain-map.org/)
- Traub et al. 2005 thalamocortical network model
- Classic published literature

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
