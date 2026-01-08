# Changelog
*See https://keepachangelog.com/en/1.0.0/ for how to maintain changelog*

## Unreleased
*Unreleased changes go here*

## [4.1.4] - 2025-01-09
Jhangri

### Fixed
- Function class (PR #40): Fixed ordering of computation of function value and collecting y variables
- Function class: Added `Function::clearVariables()` for proper symbol table cleanup
- Function class: Updated `Function::clearAll()` variable clearing
- MooseParser: Removed singleton parser - each expression now gets own symbol table
- MooseParser: `symbolTable` is now a member variable
- MooseParser: Added `ParseVariables()` for expression validation and variable extraction
- MooseParser: `ClearVariable` ensures release of expression before clearing symbol table
- MooseParser: Added `GetConstants()` to retrieve defined constants from symbol table
- `Variable::ref()` renamed to `Variable::ptr()` to reflect its function
- `test_function.py`: Updated expected values for corrected evaluation order

### Added
- Global function `init_symtab()` to initialize functions and constants in symbol table

### Changed
- SWC reader: New hierarchical naming scheme for dendritic compartments using format `name{branch_no}[_{segment_no}].{sub_branch_no}...`
- MooseParser: `Reformat()` made static
- Build: Changed workflow trigger from `on: push` to `workflow_dispatch` for manual control
- Build: Added `permissions: contents: write` for release creation
- Documentation: Updated macOS build instructions

### Removed
- `Function::findXsYs()`, `addXByIndex()`, `addXByName()`, `addY()`, `addVariable()`
- `MooseParser::CompleExprWithUnknown` - use `CompileExpr(bool allow_unknown)` instead
- `MooseParser::findAllVars()`
- `MooseParser::LinkVariables`

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

