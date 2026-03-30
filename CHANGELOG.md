# Changelog
*See https://keepachangelog.com/en/1.0.0/ for how to maintain changelog*

## Unreleased
*Unreleased changes go here*

## [4.2.0] - 2026-03-30

Kalakand

### Breaking Changes
- Setting `dt` or `tick` directly on a MOOSE object from Python will now raise an error. Use the clock scheduling API to configure timesteps.
- Some legacy and unused Python utility modules have been removed. If your scripts import from `moose.recording`, `moose.constants`, or `moose.method_utils`, you will need to update them.
- `getFieldDict` has been renamed to `getFieldTypeDict` to better reflect what it returns.
- `mooseReadKkitGenesis` has been renamed to `_loadModel` (internal). Use `moose.loadModel()` or `moose.loadKkit()` instead.

### Neuron Morphology (SWC) Improvements
- Improved support for loading neuron morphologies — SWC files with 2-point soma (as used by Arbor) and 3-point soma formats are now handled correctly
- Added a dedicated `moose.loadSwc()` function for loading SWC files explicitly, with optional electrical parameters (RM, RA, CM)
- A warning is shown when the soma format is not compatible with the [neuromorpho.org](http://neuromorpho.org/) convention

### Model Loading Improvements
- SBML and NeuroML2 models can now be loaded directly using `moose.loadModel()` without needing separate format-specific function calls
- Added explicit `moose.loadKkit()` function for loading GENESIS Kkit models
- NeuroML2 model path is now configurable instead of being hardcoded

### Python Interface Improvements
- Consistent and informative string representation for all MOOSE Python objects, making debugging and interactive use easier
- Element fields now behave more like regular MOOSE vectors, with direct access to `id`, `oid`, and `owner` properties
- `getFieldNames()` is now available directly on MOOSE objects

### Bug Fixes
- Fixed incorrect behaviour when setting attributes on element fields via Python
- Fixed an intermittent issue where expression evaluation could fail unpredictably under certain conditions
- Fixed missing runtime dependencies for NeuroML2 module (pint, scipy)

### Build and Packaging
- Python bindings rebuilt on nanobind, replacing pybind11, resulting in a cleaner and more maintainable codebase
- Dependencies are now managed automatically during the build, reducing setup effort for developers building from source
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

