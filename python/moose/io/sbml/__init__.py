"""Clean-room SBML reader for MOOSE.

Design
------
Standard SBML is the baseline; MOOSE-specific annotations are optional
enrichment, never required. The reader is a general SBML->ODE compiler:

1. **Normalize** (``normalize.py``) via libsbml converters -- inline function
   definitions, promote local parameters, fold initial assignments, sort
   rules -- so the mapper sees one canonical shape.
2. **Map** (``reader.py``): compartments -> CubeMesh, species -> Pool/BufPool,
   reactions and rules -> MOOSE objects. Each kinetic law is decomposed
   **symbolically** (``symbolic.py`` -- build a sympy expression from the AST
   and inspect its algebra): a polynomial with <=2 monomials is mass-action
   (exact Kf/Kb; a modifier appearing multiplicatively is a *catalyst*, mapped
   as a buffered substrate+product), and a degree-1 rational in one substrate
   is Michaelis-Menten (kcat/Km) -> native Reac / MMenz -- including a rate law
   that lumps a constant, untracked enzyme concentration into Vmax and
   declares no modifier at all (common in curated SBML exports of models
   whose original, e.g. GENESIS/kkit, form held a phosphatase concentration
   fixed and explicit): a synthetic constant-concentration enzyme pool is
   invented so it still maps natively rather than falling back. The
   extraction is numerically self-verified (``identify.py``); anything not
   recognized (or that fails verification) is compiled to a MOOSE
   ``Function`` (exprtk via ``mathconv.py``) driving the same Ksolve ODE
   system. Rate rules and assignment rules likewise become Functions.
3. **Report** (``report.py``): every construct that could not be represented
   faithfully (events, algebraic rules, unresolved symbols) is recorded, so
   the reader never silently mis-simulates.

Multiple compartments
---------------------
A model with several compartments gets one Ksolve+Dsolve+Stoich per
compartment. Reactions that span compartments (a reactant and product in
different compartments -- i.e. transport) are placed in the smaller-volume
compartment and then split by ``fixXreacs`` into per-compartment halves coupled
through proxy pools; the two solvers exchange those proxies each tick, and a
Dsolve mesh junction couples any species carrying a diffusion constant. Because
that exchange is operator-split at the solver tick, multi-compartment models
need a fine simulation ``dt`` for accuracy (and use the default explicit
integrator -- LSODA cannot cross the junction).

A cross-compartment coupling that is *not* native mass-action is reported
unsupported and no solver is built: the Function fallback reads pools by index
within one solver's scope and cannot reach across compartments.

Diffusion constants declared with the SBML Level 3 *spatial* package are read
onto ``pool.diffConst``. They only take physical effect once the spatial
geometry (coordinate systems / domains) is turned into a multi-voxel MOOSE
mesh, which is not built yet -- so a spatial model is reported as simulated
well-mixed for now.

Hard limits (reported, not faked): SBML discrete events and algebraic rules
have no MOOSE equivalent; non-mass-action cross-compartment coupling; and
SBML-spatial geometry is not yet mapped to a mesh (only its diffusion
constants are captured).

``handler.py`` adapts ``reader.read``/``writer.write`` to the
``moose.io.base.FormatHandler`` protocol as ``SBMLHandler`` -- the public
entry point re-exported below.

Writing
-------
``SBMLHandler.write`` (``writer.py``) is the inverse map: compartments,
Pool/BufPool, Reac, MMenz, Enz and diffusion constants go out as standard
SBML, using the same unit convention the reader assumes on the way in
(substance=mole, volume in m^3, species amount-based) so a model written by
this package reads back through this package unchanged. A Function driving a
pool via 'increment'/'setN' is converted to a rate/assignment rule by
substituting its x0, x1, ... inputs and parsing the result as an SBML
formula; constructs that parser can't express (or a pool mixing native
kinetics with a Function remainder) are reported unsupported rather than
silently dropped. See ``writer.py``'s docstring for the exact rate-constant
conversions.
"""

from .handler import SBMLHandler
from .reader import SBMLValidationError
from .report import LoadReport, WriteReport
from .writer import UnsupportedModel

__all__ = ['SBMLHandler', 'SBMLValidationError', 'LoadReport', 'WriteReport',
           'UnsupportedModel']
