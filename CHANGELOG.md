# Changelog
*See https://keepachangelog.com/en/1.0.0/ for how to maintain changelog*

## Unreleased
*Unreleased changes go here*

## [5.0.0] - 2026-09-30

Mysore Pak

### Breaking Changes

* moose.readSBML() and moose.writeSBML() now use the new reader/writer directly. They return a single model object and raise on failure, instead of the previous tuple return. moose.SBML.readSBML.mooseReadSBML is now deprecated

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

### Improvements

* Replaced the SBML reader with a new, general-purpose one supporting a much wider range of standard model files
* Added support for loading and simulating SBML models with multiple compartments
* Added an SBML writer to the new reader/writer module, with broader support than the old legacy writer, and a round-trip with the reader verified to floating-point precision
* loadpath is now optional when loading an SBML model, defaulting to /library/{model_name}
* Added moose.NA, moose.FaradayConst, and other physical constants as directly accessible Python attributes
* Added a set of ready-to-use Allen Brain Database neuron morphologies to MOOSE's built-in library
* loadKkit() now shows a deprecation notice recommending loadModel()
* NeuroML2 ComponentType Dynamics rates are now evaluated with exprtk through a scratch moose.Function instead of exec() with numpy; expressions that cannot be translated raise UnsupportedMath
* modelpath is now optional in NML2Reader.read, defaulting to /model
* HHGate2D (2D-dependent gates) now supports specifying gate tables as alpha/beta or tau/inf expressions (alphaExpr/betaExpr/tauExpr/infExpr), the same way HHGate already does for 1D gates

### Bug Fixes

* Fixed Dsolve objects returning the wrong path they now correctly report their actual location in the model tree
* Fixed creating MOOSE objects with attributes passed as keyword arguments (e.g. moose.Pool('/x', concInit=9.99))
* Fixed creating an object at a path already holding a different type silently returning the wrong object instead of raising an error
* Fixed Function expressions with more than 10 input variables silently ignoring variables past the 10th
* Fixed SWC morphology files that number nodes starting from 0 (including real Allen Brain Database files) failing to load
* Fixed an inconsistent value used for the Nernst equation's R/F constant
* Fixed wildcardFind to correctly resolve . and .. in search paths
* Fixed import moose crashing when the optional pyneuroml package is not installed
* Fixed chemMerge failing on SBML files due to a call to a non-existent function
* Fixed the NeuroML2 temperature fallback returning 25 K instead of 298.15 K when a model specifies no temperature
* Fixed no vector<vector<double>> field could be written from Python (e.g. assigning HHGate2D.tableA)
* Fixed a 2D gate lookup from Python crashing (e.g. HHGate2D.A([v, ca]))
* Rate ComponentTypes derived from NEURON .mod files now receive rateScale, the gate's Q10 factor
* Fixed a Case condition with a leading space causing NeuroML2 channels (e.g. Gran_NaF_98) to fail loading with IndentationError
* moose.readNML2 now takes filepath and an optional modelpath, instead of passing the single argument on as the file path
* Fixed Ubuntu installs failing to import moose due to the extension not carrying a runtime search path to its GSL dependency
* Fixed HHChannel2D/HHChannelF2D channels using a single-axis dependency mode (VOLT_INDEX/C1_INDEX/C2_INDEX) crashing
* Fixed a singularity check in HHGate's tau/inf expression evaluation that could miss near-zero values

### Documentation

* Converged all MOOSE-authored source files to a uniform GNU GPLv3 license header
* Updated LICENSE file links to current gnu.org URLs

## [4.3.1] - 2026-07-02

Lavang Latika

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


## [4.3.0] - 2026-05-21

Lavang Latika

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

The SWC conversion utilities (`moose.swc_utils.p_to_swc`) and morphology
processing features are based on **ShapeShifter**, developed by
**Prof. Avrama Blackwell and her team** at George Mason University.

ShapeShifter is a morphology processing utility that converts 3D neuronal
morphology files (`.swc` or GENESIS `.p`) into electrical compartmental
structures suitable for simulations. It can combine compartments with the
same (or similar) radius and reduce file size by up to 90% while preserving
electrotonic response.

- **Repository:** https://github.com/neurord/ShapeShifter
- **Used in:** `moose.swc_utils`, `moose.morphologies` (GENESIS `.p` file support),
  `python/moose/ShapeShifter/`

If you use morphology conversion or reduction features in your research,
please acknowledge Prof. Blackwell's group and the ShapeShifter project.


## [4.2.0] - 2026-03-31

Kalakand

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

## [4.1.4] - 2026-01-12
Jhangri

### Bug Fixes
- Fixed a crash (segmentation fault) that could occur when deleting Function objects
- Fixed incorrect evaluation order in Function objects that could lead to wrong results in some models
- Improved stability of expression parsing when working with dynamically changing expressions

### Model Import Improvements
- Improved SWC morphology reader with clearer hierarchical naming scheme for dendritic compartments, making imported neuron structures easier to interpret and debug

### Documentation
- Updated build instructions for macOS

### Build and Packaging
- Improved GitHub Actions workflows for release packages
- Enabled manual triggering of release workflows
- Fixed permission issues during GitHub release creation



## [4.1.1] - 2025-06-23
Jhangri

### Added 
- Added `HHChannelF` and `HHGateF` for formula-based evaluation of Hodgkin-Huxley type gating parameters
- Added a formula interface for `HHGate`: Users can now assign string formula in `exprtk` syntax to `alphaExpr`, `betaExpr`, `tauExpr` and `infExpr` to fill up the               tables. These can take either `v` for voltage or `c` for concentration as independent variable names in the formula.
- Added `moose.sysfields` to display system fields like `fieldIndex`, `numData` etc.

### FIXED
1. `bool` attribute handling added to `moose.vec`
2. More informative error message for unhandled attributes in `moose.vec`
3. Fixed issue #505
4. `moose.setCwe()` now handles str, element (ObjId) and vec (Id) parameters correctly
5. fixed `moose.showmsg()` mixing up incoming and outgoing messages.

## [4.1.0] - 2024-11-28
Jhangri
### Added
- Support for 2D HHGate/HHChannel in NeuroML reader
- Native binaries for Windows

### Fixed
- Updated to conform to c/c++-17 standard

### Changed
- `HHGate2D`: separate `xminA`, `xminB`, etc. for `A` and `B` tables
   replaced by single `xmin`, `xmax`, `xdivs`, `ymin`, `ymax`, and
   `ydivs` fields for both tables.
- Build system switched from `cmake` to `meson`

### Removed
- Temporarily removed NSDF support due to issues with finding HDF5 in
  a platform independent manner.

## [4.0.0] - 2022-04-15
Jalebi
### Added 
-  Addition of a thread-safe and faster parser based on ExprTK

### Changed
- A major under-the-hood change to numerics for chemical calculations,
  eliminating the use of 'zombie' objects for the solvers. This
  simplifies and cleans up the code and object access, but doesn't
  alter runtimes.

- Another major under-the-hood change to use pybind11 as a much
  cleaner way to interface the parser with the C++ numerical code.

- Resurrected objects for handling simulation output saving using HDF5
  format. There is an HDFWriter class, an NSDFWriter, and a new
  NSDFWriter2. The latter two implement storage in NSDF, Neuronal
  Simulation Data Format, Ray et al Neuroinformatics 2016. NSDF is
  built on HDF5 and builds up a specification designed to ensure ready
  replicability as well as self- description of model output.

- Multiple enhancements to rdesigneur, including vastly improved 3-D
  graphics output using VPython.

### Fixed
- Various bugfixes

