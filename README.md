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

# v4.2.0 – Major Release "Kalakand"
[`Kalakand`](https://en.wikipedia.org/wiki/Kalakand) is a popular
Indian sweet made from solidified sweetened milk and cottage cheese
(paneer), with a soft, grainy texture and a rich, mildly sweet
flavour. It is often garnished with cardamom and pistachios and is
a favourite at festivals and celebrations across India.

# What's New in 4.2.0

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

## Breaking Changes
- Some legacy and unused Python utility modules have been removed.
If your scripts import from `moose.recording`, `moose.constants`, or
`moose.method_utils`, you will need to update them.
- `getFieldDict` has been renamed to `getFieldTypeDict`. If your
scripts use this function, update the name accordingly.

## Neuron Morphology (SWC) Improvements

- Improved support for loading neuron morphologies: SWC files with
2-point soma (as used by Arbor) and 3-point soma formats are now
handled correctly
- Automated SWC compartmentalization using uniform RA and RM based on [ShapeShifter](https://github.com/neurord/ShapeShifter)
- Added a dedicated `moose.loadSwc()` function for loading SWC files
with optional electrical parameters (RM, RA, CM)

## Model Loading Improvements
- Added explicit `moose.loadKkit()` function for loading GENESIS Kkit models
- NeuroML2 model path is now configurable instead of being hardcoded

## Python Interface Improvements

- Consistent and informative string representation for all MOOSE Python
objects, making debugging and interactive use easier
- `getFieldNames()` is now available as a method in MOOSE objects

## Bug Fixes

- Fixed incorrect behaviour when setting attributes on element fields
via Python
- Fixed an intermittent issue where expression evaluation could fail
unpredictably under certain conditions
- Fixed missing runtime dependencies for NeuroML2 module (pint, scipy)

## Build and Packaging

- Python bindings rebuilt on nanobind, replacing pybind11, resulting
in faster and smaller code
- Building MOOSE from source is now simpler, with fewer manual setup
steps required
- Updated CI workflows for the new build system

# LICENSE

MOOSE is released under GPLv3.
