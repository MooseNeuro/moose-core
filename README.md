[![Python package](https://github.com/MooseNeuro/moose-core/actions/workflows/pymoose.yml/badge.svg)](https://github.com/MooseNeuro/moose-core/actions/workflows/pymoose.yml)

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


-------------
  
# Installation

See [docs/source/install/INSTALL.md](docs/source/install/INSTALL.md) for instructions on installation.

# Examples and Tutorials
- Have a look at examples, tutorials and demo scripts here
https://github.com/MooseNeuro/moose-examples.

- A set of jupyter notebooks with step by step examples with explanation are available here:
https://github.com/MooseNeuro/moose-notebooks.

# v4.1.4 – Incremental Release over v4.1.0 "Jhangri"
Patch release focusing on accurate version reporting, bug fixes, and documentation improvements.

# ABOUT VERSION 4.1.4, `Jhangri`

[`Jhangri`](https://en.wikipedia.org/wiki/Imarti) is an Indian sweet
in the shape of a flower. It is made of white-lentil (*Vigna mungo*)
batter, deep-fried in ornamental shape to form the crunchy, golden
body, which is then soaked in sugar syrup lightly flavoured with
spices.

This release has the following changes:

# Installation
Installing released version from PyPI using `pip`

This version is available for installation via `pip`. To install the latest release, run

```
conda create -n moose python=3.13 gsl hdf5 numpy vpython matplotlib -c conda-forge
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

    >>> import moose

# Bug Fixes
-  Fixed a crash (segmentation fault) that could occur when deleting function objects  
-  Fixed incorrect evaluation order in function objects that could lead to wrong results in some models
-  Improved stability of expression parsing when working with dynamically changing expressions  
-  Fixed setNumVar issue in Function class - setting the number of x variables with `numVar` field is no longer required, simply updating  
   the expression now works correctly
# Model Import Improvements
- Improved SWC morphology reader with clearer hierarchical naming scheme for dendritic compartments, making imported neuron structures easier to interpret and debug

# Documentation
- Updated build instructions for macOS

# Build and Packaging
- Improved GitHub Actions workflows for release packages
- Enabled manual triggering of release workflows
- Fixed permission issues during GitHub release creation
   
# LICENSE

MOOSE is released under GPLv3.
