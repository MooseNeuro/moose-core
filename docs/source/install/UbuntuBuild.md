# Building MOOSE on Ubuntu (possibly in WSL)

This guide covers building MOOSE from source on Ubuntu Linux, including Windows Subsystem for Linux (WSL). MOOSE 4.2.0 uses **nanobind** for Python bindings, which is automatically downloaded during the build process - no manual installation required.

## Prerequisites

### 0. Install GNU build tools

```bash
sudo apt install build-essential
```

This installs essential compilation tools including `gcc`, `g++`, and `make`.

---

## Option A: Building with System Python

Use this method if you want to use your system's Python installation.

### 1. Install the dependencies

```bash
# Build dependencies
sudo apt-get install ninja meson pkg-config python-pip python-numpy libgsl-dev g++ libhdf5-dev libz-dev

# Python build tools
pip install meson-python

# Runtime dependencies (required for MOOSE to work)
pip install pyneuroml python-libsbml pint scipy vpython
```

**Explanation of dependencies:**

| Package | Purpose |
|---------|---------|
| `ninja` | Fast build system used by meson |
| `meson` | Build configuration system |
| `pkg-config` | Helps find installed libraries |
| `libgsl-dev` | GNU Scientific Library (numerical computations) |
| `libhdf5-dev` | HDF5 library (data storage) |
| `libz-dev` | Compression library |
| `pyneuroml` | NeuroML2 model support |
| `python-libsbml` | SBML model support |
| `pint` | Unit handling for NeuroML2 |
| `scipy` | Scientific computing for NeuroML2 |

### 2. Install pymoose from GitHub

The simplest way to install is directly from the repository:

```bash
pip install git+https://github.com/MooseNeuro/moose-core --user
```

This command downloads, builds, and installs MOOSE in one step.

---

## Option B: Building with Conda/Mamba/Micromamba (Recommended)

This method provides better isolation and dependency management.

### 1. Install conda or variants

Install conda, mamba, or micromamba. See https://docs.conda.io/projects/conda/en/latest/user-guide/install/linux.html

**Note:** In all commands below, `micromamba` can be replaced by `conda` or `mamba`.

### 2. Create an environment with required packages

```bash
micromamba create -n moose python=3.13 ninja meson meson-python gsl hdf5 numpy matplotlib vpython doxygen pkg-config pint scipy pyneuroml python-libsbml -c conda-forge
```

**Explanation of packages:**

| Category | Packages | Purpose |
|----------|----------|---------|
| Build tools | `ninja`, `meson`, `meson-python` | Build system |
| Core libraries | `gsl`, `hdf5` | Numerical computation, data storage |
| Python packages | `numpy`, `matplotlib`, `vpython` | Data handling, visualization |
| NeuroML2 support | `pint`, `scipy`, `pyneuroml` | Model import |
| SBML support | `python-libsbml` | Model import |
| Documentation | `doxygen` | API documentation |
| Utilities | `pkg-config` | Library detection |

### 3. Activate the environment

```bash
micromamba activate moose
```

---

## After the above steps, for both system Python and conda environment

### 4. Clone the source code

```bash
git clone https://github.com/MooseNeuro/moose-core --depth 50
cd moose-core
```

The `--depth 50` flag downloads only the last 50 commits, making the download faster.

### 5. Build MOOSE

There are two ways to build: using `pip` (simple) or using `meson` directly (more control).

#### Method 1: Using pip (Simple)

```bash
pip install .
```

This handles everything automatically: configuration, compilation, and installation.

For user-local installation (no sudo required):

```bash
pip install . --user
```

**Note:** `pip` builds `pymoose` with default options - it runs `meson` behind the scene. If you are developing MOOSE, want to build it with different options, or need to test and profile it, the `meson` and `ninja` based flow (Method 2) is recommended.

#### Method 2: Using meson (More Control)

```bash
# Step 1: Configure the build
meson setup --wipe _build --prefix=$CONDA_PREFIX -Duse_mpi=false -Dbuildtype=release

# Step 2: Compile the code
meson compile -v -C _build

# Step 3: Install to your environment
meson install -C _build
```

This will install `moose` module inside your environment's default module installation (usually `site-packages`) directory. This requires write permission on the target directory. See below for custom location installation if you don't have write permission.

**Note:** You can also use `ninja -v -C _build` instead of `meson compile -v -C _build` - both are equivalent. The `meson compile` command calls ninja internally.

**What each command does:**

| Command | Purpose |
|---------|---------|
| `meson setup` | Configures the build, finds dependencies, downloads nanobind |
| `meson compile` | Compiles all C++ source files and creates the Python module |
| `meson install` | Copies the built module to your Python environment |

**What each option means:**

| Option | Meaning |
|--------|---------|
| `--wipe` | Clean any previous build configuration |
| `_build` | Directory where build files are stored |
| `--prefix=$CONDA_PREFIX` | Install to conda environment (not system-wide) |
| `-Duse_mpi=false` | Disable MPI support (not needed for most users) |
| `-Dbuildtype=release` | Optimized build for best performance |
| `-v` | Verbose output (see what's happening) |
| `-C _build` | Use the `_build` directory |

### 6. Verify the installation

```bash
python -c "import moose; print('Version:', moose.__version__); print('File:', moose.__file__)"
```

Expected output:
```
Version: 4.2.0
File: /path/to/site-packages/moose/__init__.py
```

Quick functionality test:
```bash
python -c "import moose; c = moose.Compartment('/c'); print('dt:', c.dt); moose.le()"
```

---

## Advanced Build Options

Meson provides many builtin options: https://mesonbuild.com/Builtin-options.html

Meson options are supplied in the command line to `meson setup` in the format `-Doption=value`.

### Installation Prefix (Custom Location)

To install MOOSE in a custom location instead of site-packages, you can pass the `--prefix` argument to `meson setup`. For example, if you are in the `moose-core` directory and want to have it installed in `_build_install` subdirectory, you can use:

```bash
meson setup --wipe _build --prefix=`pwd`/_build_install -Duse_mpi=false -Dbuildtype=release
meson compile -v -C _build
meson install -C _build
```

This will build MOOSE in `moose-core/_build` directory and install it as a Python package in the `moose-core/_build_install` directory.

**Important:** Python won't find this custom location automatically. You must add the directory containing `moose` under `_build_install` in your `PYTHONPATH` environment variable. In `bash` shell, this would be:

```bash
export PYTHONPATH="$PYTHONPATH:`pwd`/_build_install/lib/python3.13/site-packages"
```

**Note:** Replace `python3.13` with your Python version (e.g., `python3.11`, `python3.12`).

To make this permanent, add the export line to your `~/.bashrc` file.

### Build Types

| Build Type | Command | Use For |
|------------|---------|---------|
| Release | `-Dbuildtype=release` | Normal use (fastest) |
| Debug | `-Dbuildtype=debug` | Finding bugs (slowest) |
| Debug Optimized | `-Dbuildtype=debugoptimized` | Profiling |
| Min Size | `-Dbuildtype=minsize` | Smallest binary size |

**Release build** (default, recommended):
```bash
meson setup --wipe _build -Duse_mpi=false -Dbuildtype=release
```

**Debug build** (for development):
```bash
meson setup --wipe _build --prefix=`pwd`/_build_install -Duse_mpi=false -Dbuildtype=debug -Ddebug=true
```

You can either use `buildtype` option alone or use the two options `debug` and `optimization` for finer grained control over the build.

According to meson documentation:
- `-Dbuildtype=debug` creates a debug build with optimization level 0 (passes `-O0 -g` to GCC)
- `-Dbuildtype=debugoptimized` creates a debug build with optimization level 2 (equivalent to `-Ddebug=true -Doptimization=2`)
- `-Dbuildtype=release` creates a release build with optimization level 3 (equivalent to `-Ddebug=false -Doptimization=3`)
- `-Dbuildtype=minsize` creates a release build with space optimization (passes `-Os` to GCC)

### Optimization Level

To set a specific optimization level:

```bash
meson setup --wipe _build -Duse_mpi=false -Doptimization=2
```

Available levels: `plain`, `0`, `g`, `1`, `2`, `3`, `s`

For more meson options, see: https://mesonbuild.com/Builtin-options.html

---

## Development Workflow

### Editable Install (for Python Development)

If you're modifying MOOSE's Python code and want changes to take effect immediately:

```bash
python -m pip install --no-build-isolation --editable .
```

This creates a "development mode" installation where your edits to Python source files are immediately reflected without reinstalling.

### Building a Wheel (for Distribution)

To build a wheel (for distribution), run `pip wheel` command in the `moose-core` directory:

```bash
pip wheel -w dist .
```

This will create the `pymoose-{version}-{python}-{abi}-{os}_{arch}.whl` wheel file in the `moose-core/dist` directory. For example:

```
dist/pymoose-4.2.0-cp313-cp313-linux_x86_64.whl
```

This can be installed with:

```bash
pip install dist/pymoose-4.2.0-cp313-cp313-linux_x86_64.whl
```

### Clean Rebuild

To do a clean rebuild, delete the `_build` directory and the generated `_build_install/` directory (if using custom prefix) and continue the steps starting with `meson setup ...`:

```bash
rm -rf _build _build_install
meson setup --wipe _build --prefix=$CONDA_PREFIX -Duse_mpi=false -Dbuildtype=release
meson compile -v -C _build
meson install -C _build
```

To make a debug build, replace the option `-Dbuildtype=release` with `-Dbuildtype=debug`.

---

## How the Build Works

Understanding what happens during the build process:

### Step 1: meson setup

```
┌─────────────────────────────────────────────────────────────┐
│                     meson setup                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Reads meson.build configuration file                    │
│  2. Detects your system (OS, CPU, compilers)                │
│  3. Finds dependencies (GSL, HDF5)                          │
│  4. Downloads nanobind automatically (for Python bindings)  │
│  5. Generates ninja build files in _build/                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 2: meson compile

```
┌─────────────────────────────────────────────────────────────┐
│                    meson compile                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Compiles each .cpp file to .o (object file)             │
│  2. Links all object files together                         │
│  3. Creates _moose.cpython-3xx-xxx.so (Python module)       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 3: meson install

```
┌─────────────────────────────────────────────────────────────┐
│                    meson install                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Copies _moose.cpython-3xx.so to site-packages/moose/    │
│  2. Copies Python files (*.py) to site-packages/moose/      │
│  3. Compiles Python files to .pyc (bytecode)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Error: "No module named 'neuroml'" or "No module named 'pyneuroml'"

**Cause:** Missing runtime dependency.

**Solution:**
```bash
pip install pyneuroml
```

### Error: "Could not find dependency gsl"

**Cause:** GSL library not installed.

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install libgsl-dev

# Conda
conda install gsl -c conda-forge
```

### Error: "Could not find dependency hdf5"

**Cause:** HDF5 library not installed.

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install libhdf5-dev

# Conda
conda install hdf5 -c conda-forge
```

### Error: "Permission denied" during install

**Cause:** Trying to install to system location without sudo.

**Solution:** Either use `--prefix=$CONDA_PREFIX` or `pip install . --user`

### Error: "ninja: command not found"

**Cause:** Ninja build system not installed.

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install ninja

# Conda
conda install ninja -c conda-forge
```

---

## Notes

- **nanobind:** MOOSE 4.2.0 uses nanobind for Python bindings (replacing pybind11). This is fetched automatically by meson during build - no manual installation required.

- **NeuroML2 support:** Requires `pyneuroml`, `pint`, and `scipy` packages.

- **SBML support:** Requires `python-libsbml` package.
