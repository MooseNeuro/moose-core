# Author: Subhasis Ray
# Date: Sun Jul  7 2024

pymoose_src = [
  'PyRun.cpp',
  'helper.cpp',
  'MooseVec.cpp',
  'Finfo.cpp',
  'pymoose.cpp',
]

python_res = run_command('python', '-c', 'from sysconfig import get_paths as gp; print(gp()["include"])', check: false)
if python_res.returncode() == 0
  inc_dirs = python_res.stdout().strip()
else
  message('ERROR: could not find Python include directory')
  inc_dirs = []
endif

pymoose_lib = static_library('pymoose', pymoose_src, dependencies: nanobind_dep, include_directories: inc_dirs)
