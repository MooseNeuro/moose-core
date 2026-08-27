# conftest.py --- pytest session setup shared by all tests under tests/.
#
# Force a non-interactive matplotlib backend so that any plt.show() -- whether
# in a test or inside library code such as rdesigneur.display()
# (rdesigneur.py: plt.show(block=...)) -- becomes a no-op instead of popping a
# blocking window and hanging the test run. Set both the env var (honoured
# before matplotlib is first imported) and use() (in case it already was).
import os

os.environ.setdefault("MPLBACKEND", "Agg")

try:
    import matplotlib
    matplotlib.use("Agg", force=True)
except Exception:
    pass

import pytest
import moose

# MOOSE keeps a single process-global object tree under '/', and
# moose.reinit()/moose.start() step *every* schedulable object in it. Because
# pytest imports all test modules during collection, any object a module builds
# at import time (or a test leaves behind) stays in the tree and gets simulated
# by every subsequent test -- turning fast tests into apparent hangs. Wipe the
# user-created subtree before each test so every test starts from a clean tree.
#
# These are the objects present in a pristine MOOSE tree; never delete them.
_SYSTEM_PATHS = {'/Msgs[0]', '/clock[0]', '/classes[0]', '/postmaster[0]'}

# Per-tick clock dt values of a pristine MOOSE, captured here at import time
# (before any test has run and mutated them). setClock() changes are global and
# persist across tests: e.g. a test that sets every tick to 1 ms makes a later
# diffusion test take ~1000x as many steps, which looks like a hang.
_DEFAULT_DTS = list(moose.element('/clock').dts)


@pytest.fixture(autouse=True)
def _clean_moose_tree():
    # Reset the current working element to root first: a prior test may have
    # left it (via setCwe/ce) pointing inside a subtree we are about to delete,
    # and creating an object with a relative path against a dangling cwe
    # segfaults.
    moose.setCwe('/')
    for child in moose.element('/').children:
        if child.path not in _SYSTEM_PATHS:
            try:
                moose.delete(child)
            except Exception:
                pass
    # Restore global clock dt state clobbered by a previous test.
    for tick, dt in enumerate(_DEFAULT_DTS):
        try:
            moose.setClock(tick, dt)
        except Exception:
            pass
    yield
