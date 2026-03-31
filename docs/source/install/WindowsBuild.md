# Building MOOSE on Windows with MSVC

## Install requirements

### 1. Visual Studio Build Tools

1. Download the appropriate version of Visual Studio Installer. Building MOOSE from source requires **Visual Studio 2019 or later**: https://visualstudio.microsoft.com/downloads/

2. Run the installer and in the "Workloads" tab, select **"Desktop Development with C++"**.

3. You can uncheck all the optional components in the right-hand pane (Installation details) except:
   - **MSVC Build Tools for x64/x86 (Latest)**
   - **Windows NN SDK** (where NN is 10 for Windows 10, 11 for Windows 11, etc.)

4. Add the path to this folder in your `PATH` environment variable.

### 2. Install Git for Windows

Download and install Git as described here: https://git-scm.com/downloads/win

### 3. Install LLVM Compiler Infrastructure

Install LLVM from https://releases.llvm.org/download.html

You can either install it directly (adding its `bin` folder to the `PATH` environment variable), or install it with winget from the command line:

```powershell
winget install llvm
```

To add LLVM executables to PATH in PowerShell:
```powershell
$env:PATH="$env:PATH;C:\Program Files\LLVM\bin"
```

Alternatively, if using `cmd.exe` command prompt:
```cmd
set PATH="%PATH%;C:\Program Files\LLVM\bin"
```

### 4. MPI Support (Optional - Skip for now)

For MPI, install MS-MPI: https://github.com/microsoft/Microsoft-MPI/releases/

> **Note:** MPI-build on Windows is not supported yet (TODO).

---

## Python virtual environment

You may want to use a system like Anaconda (or [Miniforge with Mamba, or Micromamba](https://mamba.readthedocs.io/en/latest/)), which will allow you to create isolated Python environments. There are binary packages for most of the requirements in the conda channel `conda-forge`.

If you want to keep things slim, **micromamba** may be ideal because it is a single statically linked C++ executable and does not install any base environment.

In this guide, `conda` command can be replaced by `mamba` or `micromamba` if you are using one of those systems.

### Installing Micromamba (Step-by-Step)

Install micromamba following this guide: https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html#windows

Briefly:

1. Open PowerShell. By default it starts in `C:\Windows\system32` folder, which is a system folder. Change to your home directory:
   ```powershell
   cd $HOME
   ```

2. Download micromamba:
   ```powershell
   Invoke-Webrequest -URI https://micro.mamba.pm/api/micromamba/win-64/latest -OutFile micromamba.tar.bz2
   ```

3. Extract the contents:
   ```powershell
   tar xf micromamba.tar.bz2
   ```

4. Move the micromamba executable to a suitable location:
   ```powershell
   MOVE -Force Library\bin\micromamba.exe .\micromamba.exe
   ```

5. Set the root-prefix for micromamba (everything micromamba installs goes here):
   ```powershell
   $Env:MAMBA_ROOT_PREFIX="$HOME\micromamba"
   ```
   
   You have to create this folder if required:
   ```powershell
   md "micromamba"
   ```

6. Update PowerShell initialization to include micromamba:
   ```powershell
   .\micromamba.exe shell init -s powershell -r "$HOME\micromamba"
   ```

7. Restart PowerShell.

### Fixing PowerShell Execution Policy

After restarting, you may see an error message like this:

```
. : File C:\Users\{username}\Documents\WindowsPowerShell\profile.ps1 cannot be loaded because running scripts is disabled
on this system. For more information, see about_Execution_Policies at https:/go.microsoft.com/fwlink/?LinkID=135170.
At line:1 char:3
+ . 'C:\Users\{username}\Documents\WindowsPowerShell\profile.ps1'
+   ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : SecurityError: (:) [], PSSecurityException
    + FullyQualifiedErrorId : UnauthorizedAccess
```

This is because Windows does not allow PowerShell to execute scripts by default. To bypass this, modify the execution policy:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Restart PowerShell and the new window should have no error message.

### Verify Micromamba Installation

Ensure micromamba is available to PowerShell:

```powershell
micromamba env list
```

This should show a list of existing Python environments, which usually includes base:

```
  Name  Active  Path
---------------------------------------------
  base  *       C:\Users\{your-user-name}\micromamba
```

### Create the MOOSE Environment

To create an environment, open Anaconda command prompt and enter:

```powershell
conda create -n moose meson ninja meson-python gsl hdf5 numpy matplotlib vpython pkg-config clang -c conda-forge
```

> **Note:** Please make sure you are using the `conda-forge` channel (`-c conda-forge`) for installing GSL and not the Anaconda `defaults`. The latter causes linking errors.

This will create an environment named `moose`. In some terminals (Windows `cmd`) you may get an error for options with brackets. Put them inside quotes to work around it.

Then activate this environment for your build:

```powershell
conda activate moose
```

---

## Build and install moose using `pip`

```powershell
pip install git+https://github.com/MooseNeuro/moose-core
```

---

## Build moose for development

> **Note:** The commands below are designed for PowerShell.

### Step 1: Clone the Repository

Get moose source code by cloning `moose-core` source code using git:

```powershell
git clone https://github.com/MooseNeuro/moose-core --depth 50
cd moose-core
```

### Step 2: Set LLVM Path (if not already done)

If you have not already set the path to LLVM binaries:

```powershell
$env:PATH="$env:PATH;C:\Program Files\LLVM\bin"
```

### Step 3: Activate the Visual C++ Development Environment

This is done by a batch script installed in the Visual Studio Directory. There are different scripts specific to 32-bit and 64-bit systems, and must match your Python. See here for information about cross compilation with MSVC Build Tools: https://learn.microsoft.com/en-us/cpp/build/building-on-the-command-line?view=msvc-170 (Use the developer tools in an existing command window).

First, run Python from a command prompt to check its build information:

```powershell
python
```

This will show something like:

```
Python 3.13.0 | packaged by conda-forge | (main, Dec 2 2025, 19:51:43) [MSC v.1944 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

The `[MSC v.1944 64 bit (AMD64)] on win32` part tells us that it is **64-bit Python** running on a **32-bit Windows system**. Thus, MOOSE needs cross compilation from 32-bit to 64-bit.

Run the appropriate Visual C++ environment script:

| Your System | Script | Example Path |
|-------------|--------|--------------|
| 64-bit Windows, 64-bit Python | `vcvars64.bat` | `C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat` |
| 32-bit Windows, 64-bit Python (cross-compile) | `vcvarsx86_amd64.bat` | `C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvarsx86_amd64.bat` |

Run the script by entering the full path in the PowerShell prompt.

### Step 4: Configure, Build and Install

```powershell
meson setup --wipe _build -Duse_mpi=false --buildtype=release --vsenv
meson compile -vC _build
meson install -C _build
```

> **Note:** If you want to keep the installation in local folder, replace the first command with:
> ```powershell
> meson setup --wipe _build --prefix={absolute-path} -Duse_mpi=false --buildtype=release --vsenv
> ```
> where `{absolute-path}` is the full path of the folder you want to install it in. You will have to add the `Lib\site-packages` directory within this to your `PYTHONPATH` environment variable to make `moose` module visible to Python.

**Known Issue:** If meson setup shows an error like:

```
Need python for x86, but found x86_64
Run-time dependency python found: NO 
meson.build:49:16: ERROR: Python dependency not found
```

Or:

```
meson.build:13:0: ERROR: Compiler cl cannot compile programs
```

You may be using 32-bit Visual C++ build tools on a 64-bit computer. Refer to Step 3 above.

### Step 5: Set PYTHONPATH (for local installation)

This will create `moose` module inside `moose-core/_build_install` directory. To make moose importable from any terminal, add this directory to your `PYTHONPATH` environment variable.

**Temporary (current session only):**

```powershell
$env:PYTHONPATH = "{location-of-moose-core}\moose-core\_build_install\Lib\site-packages"
```

**Permanent Setup:**

You have to do the above every time you open PowerShell to use MOOSE. To make it permanent:

1. Go to **Windows System Settings**
2. Find **Advanced System Settings**
3. In the System Properties window, click the **"Environment Variables..."** button
4. In the popup window, under "User variables for {your-user-name}", look for `PYTHONPATH`
5. If it does not exist already, click **"New"**
6. Put `PYTHONPATH` in the "Variable Name" text box
7. Put the location of MOOSE installation in the "Variable value" textbox

---

## Verify Installation

Start the Python interpreter and try to import moose to check if the installation worked:

```powershell
python
>>> import moose
```

If this does not throw any errors, you are good to go.

---

## Note on Debug build on Windows

Debug build tries to link with debug build of Python, and this is not readily available on Windows, unless you build the Python interpreter (CPython) itself from sources in debug mode. Therefore, debug build of moose will fail at the linking stage complaining that the linker could not find `python3x_d.lib`.

The workaround, as pointed out by Ali Ramezani [here](https://stackoverflow.com/questions/66162568/lnk1104cannot-open-file-python39-d-lib), is to make a copy of `python3x.lib` named `python3x_d.lib` in the same directory (`libs`). After that, you can run meson setup as follows:

```powershell
meson setup --wipe _build --prefix=$PWD\_build_install -Duse_mpi=false --buildtype=debug --vsenv
```

and then go through the rest of the steps.

### Build Type Options

Meson provides many builtin options: https://mesonbuild.com/Builtin-options.html

Meson options are supplied in the command line to `meson setup` in the format `-Doption=value`.

- **Buildtype:** If you want a development build with debug enabled, pass `-Dbuildtype=debug` in the `meson setup`.

  ```powershell
  meson setup --wipe _build --prefix=$PWD\_build_install -Duse_mpi=false -Dbuildtype=debug --vsenv
  ```

  You can either use `buildtype` option alone or use the two options `debug` and `optimization` for finer grained control over the build. According to meson documentation:
  - `-Dbuildtype=debug` will create a debug build with optimization level 0 (i.e., no optimization, passing `-O0 -g` to GCC)
  - `-Dbuildtype=debugoptimized` will create a debug build with optimization level 2 (equivalent to `-Ddebug=true -Doptimization=2`)
  - `-Dbuildtype=release` will create a release build with optimization level 3 (equivalent to `-Ddebug=false -Doptimization=3`)
  - `-Dbuildtype=minsize` will create a release build with space optimization (passing `-Os` to GCC)

- **Optimization level:** To set optimization level, pass `-Doptimization=level`, where level can be `plain`, `0`, `g`, `1`, `2`, `3`, `s`.

---

## Using WinDbg for Debugging

A free graphical debugger available for MS Windows is WinDbg: https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/

You can use it to attach to a running Python process and set breakpoints at target function/line etc.

In WinDbg command line you find the moose module name with:

```
lm m _moose*
```

This will show something like `_moose_cp311_win_amd64` when your build produced `_moose.cp311-win_amd64.lib`.

Now you can set a breakpoint to a class function with the module name as prefix as follows:

```
bp _moose_cp311_win_amd64!ChanBase::setGbar
```
