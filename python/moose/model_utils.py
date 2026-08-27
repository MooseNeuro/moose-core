# -*- coding: utf-8 -*-
# Utilties for loading NML and SBML models.
# Authored and maintained by Harsha Rani


import os
import moose._moose as _moose

import logging

logger_ = logging.getLogger("moose.model")

# sbml import: the moose.io.sbml reader/writer (symbolic rate-law
# recognition, multi-compartment cross-reactions, no annotations needed).
# This is what loadModel()/_loadModel() and moose.readSBML()/writeSBML()
# dispatch to. The old mass-action-only, annotation-dependent reader/writer
# (moose.SBML.readSBML/writeSBML) are no longer wired to any moose.* name,
# but stay directly importable for anyone who needs their tuple-return
# contract.
sbml2Import_, sbml2Error_ = True, ""
try:
    from moose.io.sbml import SBMLHandler as _SBMLHandler
except Exception as e:
    sbml2Import_ = False
    sbml2Error_ = str(e)

# NeuroML2 import.
nml2Import_, nml2ImportError_ = True, ""
try:
    import moose.neuroml2 as _neuroml2
except Exception as e:
    nml2Import_ = False
    nml2ImportError_ = str(e)

chemImport_, chemError_ = True, ""
try:
    import moose.chemUtil as _chemUtil
except Exception as e:
    chemImport_ = False
    chemError_ = str(e)

kkitImport_, kkitImportErr_ = True, ""
try:
    import moose.genesis.writeKkit as _writeKkit
except ImportError as e:
    kkitImport_ = False
    kkitImportErr_ = str(e)

mergechemImport_, mergechemError_ = True, ""
try:
    import moose.chemMerge as _chemMerge
except Exception as e:
    mergechemImport_ = False
    mergechemError_ = str(e)

def _normalize_solver(solverclass):
    """Map the many spellings loadModel()/readSBML() accept for a solver
    class to the canonical 'gssa' / 'gsl' / 'ee' every backend understands."""
    sc = solverclass.lower().replace(" ", "")
    if sc in ["gssa", "gillespie", "stochastic", "gsolve"]:
        return "gssa"
    if sc in ["gsl", "deterministic", "rungekutta", "rk5", "rk"]:
        return "gsl"
    return "ee"


# SBML related functions.
def mooseReadSBML2(filepath, loadpath=None, solver="gsl", validate=False):
    """Load an SBML model with the moose.io.sbml reader (inner helper
    function for loadModel() and moose.readSBML()).

    ``loadpath`` defaults to ``/library/{model_name}`` (see
    ``moose.io.sbml.reader.read``) when not given; loadModel() itself always
    passes one through explicitly, so this only matters when called directly.

    Recognizes mass-action/Michaelis-Menten kinetics symbolically (not just
    by grabbing the first two kinetic-law parameters), supports
    multi-compartment cross-compartment reactions, and needs no
    MOOSE-specific annotations. Any construct it cannot represent faithfully
    (events, algebraic rules, ...) is recorded rather than silently dropped
    -- see the returned handler's ``report`` (also logged at WARNING level
    here if non-empty).

    ``validate`` defaults to False here (unlike SBMLHandler.read's own
    stricter default): loadModel() is a best-effort "just load whatever this
    file is" entry point, so a real-world file with a minor validation
    complaint should still load with its gaps reported, not raise.
    """
    global sbml2Import_, sbml2Error_
    if not sbml2Import_:
        raise ImportError(
            "moose.io.sbml could not be loaded because of '%s'" % sbml2Error_
        )
    handler = _SBMLHandler()
    element = handler.read(
        filepath, loadpath, solver=_normalize_solver(solver), validate=validate)
    if handler.report is not None and not handler.report.fully_supported:
        logger_.warning(handler.report.summary())
    return element


def mooseWriteSBML2(modelpath, filepath):
    """Write the model under ``modelpath`` to ``filepath`` as SBML with the
    moose.io.sbml writer (inner helper function for moose.writeSBML()).

    Emits Reac/MMenz/Enz reactions, diffusion, and Function-driven
    rate/assignment rules; its round trip with mooseReadSBML2 is verified to
    floating-point precision. Any construct it cannot represent faithfully
    is recorded rather than silently dropped -- see the returned handler's
    ``report`` (also logged at WARNING level here if non-empty).
    """
    global sbml2Import_, sbml2Error_
    if not sbml2Import_:
        raise ImportError(
            "moose.io.sbml could not be loaded because of '%s'" % sbml2Error_
        )
    handler = _SBMLHandler()
    element = handler.write(modelpath, filepath)
    if handler.report is not None and not handler.report.fully_supported:
        logger_.warning(handler.report.summary())
    return element


def mooseWriteKkit(modelpath, filepath, sceneitems={}):
    """Writes  loaded model under modelpath to a file in Kkit format. (inner
    helper function for moose.writeKkit)"""
    global kkitImport_, kkitImportErr_
    if not kkitImport_:
        raise ImportError(
            "Kkit support could not be enabled becase %s." % kkitImportErr_
        )
    return _writeKkit.mooseWriteKkit(modelpath, filepath, sceneitems)


def mooseDeleteChemSolver(modelpath):
    """deletes solver on all the compartment and its children. (helper function
    for moose.deleteChemSolver)

    Notes
    -----
    This is neccesary while created a new moose object on a pre-existing modelpath,
    this should be followed by mooseAddChemSolver for add solvers on to compartment
    to simulate else default is Exponential Euler (ee)
    """
    if not chemImport_:
        raise ImportError("Failed to load this utility because of %s" % chemError_)
    return _chemUtil.add_Delete_ChemicalSolver.mooseDeleteChemSolver(modelpath)


def mooseAddChemSolver(modelpath, solver):
    """mooseAddChemSolver (helper function for addChemSolver)"""
    if not chemImport_:
        raise ImportError("Could not load chemUtil because %s" % chemError_)
    return _chemUtil.add_Delete_ChemicalSolver.mooseAddChemSolver(modelpath, solver)


def mooseMergeChemModel(src, des):
    """Merges two chemical model.

    File or filepath can be passed source is merged to destination
    """
    global mergechemImport_, mergechemError_
    if not mergechemImport_:
        raise ImportError("Failed to load this utility because of %s" % mergechemError_)
    return _chemMerge.merge.mergeChemModel(src, des)


def readcell_scrambled(filename, target, method="ee"):
    """A special version for handling cases where a .p file has a line
    with specified parent yet to be defined.

    It creates a temporary file with a sorted version based on
    connectivity, so that parent is always defined before child."""
    pfile = open(filename, "r")
    tmpfilename = filename + ".tmp"
    graph = defaultdict(list)
    data = {}
    error = None
    root = None
    ccomment_started = False
    current_compt_params = []
    for line in pfile:
        tmpline = line.strip()
        if not tmpline or tmpline.startswith("//"):
            continue
        elif tmpline.startswith("/*"):
            ccomment_started = True
        if tmpline.endswith("*/"):
            ccomment_started = False
        if ccomment_started:
            continue
        if tmpline.startswith("*set_compt_param"):
            current_compt_params.append(tmpline)
            continue
        node, parent, rest, = tmpline.partition(" ")
        if parent == "none":
            if root is None:
                root = node
            else:
                raise ValueError(
                    "Duplicate root elements: ",
                    root,
                    node,
                    "> Cannot process any further.",
                )
                break
        graph[parent].append(node)
        data[node] = "\n".join(current_compt_params)

    tmpfile = open(tmpfilename, "w")
    stack = [root]
    while stack:
        current = stack.pop()
        children = graph[current]
        stack.extend(children)
        tmpfile.write(data[current])
    tmpfile.close()
    ret = moose.loadModel(tmpfilename, target, method)
    return ret


# NML2 reader and writer function.
def mooseReadNML2(filepath, modelpath, verbose=False):
    """Read NeuroML model (version 2) and return reader object.
    """
    global nml2Import_, nml2ImportError_
    if not nml2Import_:
        raise RuntimeError("Could not load NML2 support:\n %s" % nml2ImportError_)

    reader = _neuroml2.NML2Reader(verbose=verbose)
    reader.read(filepath, modelpath)
    return reader


def mooseWriteNML2(outfile):
    raise NotImplementedError("Writing to NML2 is not supported yet")


# ----------------------------------------------------------------------
# loadModel() dispatch: one small loader function per format, selected by
# file extension via _EXT_LOADERS. The only ambiguous extension is .xml
# (shared by SBML and NeuroML2), resolved by sniffing the root element
# instead of guessing-by-trial-and-error.
# ----------------------------------------------------------------------
def _load_native(filename, modelpath, solverclass):
    """.swc / .p: handled entirely inside the C++ core."""
    return _moose.loadModelInternal(filename, modelpath, solverclass)


def _load_kkit(filename, modelpath, solverclass):
    """.g / .cspace: GENESIS kkit/cspace chemical models. Always loaded
    unsolved (ee) first, then a real solver is attached only if requested --
    mirrors mooseAddChemSolver's own contract."""
    element = _moose.loadModelInternal(filename, modelpath, "ee")
    method = _normalize_solver(solverclass)
    if method != "ee":
        _chemUtil.add_Delete_ChemicalSolver.mooseAddChemSolver(modelpath, method)
    return element


def _load_sbml(filename, modelpath, solverclass):
    return mooseReadSBML2(filename, modelpath, solverclass)


def _load_nml2(filename, modelpath, solverclass):
    return mooseReadNML2(filename, modelpath)


def _sniff_xml_format(filename):
    """SBML and NeuroML2 both use '.xml'; tell them apart by root element
    instead of trial-and-error (attempt one reader, catch, attempt the
    other) -- that would run partial, discarded loads and blur real parse
    errors from either reader into an unhelpful generic failure."""
    with open(filename, "r", encoding="utf-8", errors="ignore") as f:
        head = f.read(4096)
    if "<sbml" in head:
        return "sbml"
    if "<neuroml" in head or "<Lems" in head:
        return "nml2"
    return None


def _load_xml(filename, modelpath, solverclass):
    fmt = _sniff_xml_format(filename)
    if fmt == "sbml":
        return _load_sbml(filename, modelpath, solverclass)
    if fmt == "nml2":
        return _load_nml2(filename, modelpath, solverclass)
    raise ValueError(
        "%r has a .xml extension but its root element is neither <sbml> "
        "nor <neuroml>/<Lems>; cannot tell SBML from NeuroML2." % filename)


_EXT_LOADERS = {
    ".swc": _load_native,
    ".p": _load_native,
    ".g": _load_kkit,
    ".cspace": _load_kkit,
    ".sbml": _load_sbml,
    ".nml": _load_nml2,
    ".xml": _load_xml,
}

_SUPPORTED_FORMATS = (
    "GENESIS KKIT (.g), GENESIS CSPACE (.cspace), GENESIS PROTO (.p), "
    "SWC (.swc), SBML (.xml, .sbml), NeuroML (.xml, .nml)"
)


def _loadModel(filename, modelpath, solverclass="gsl"):
    """Private dispatcher for loadModel(): pick a loader by file extension
    and load. Errors from the chosen loader propagate as-is -- they are the
    real reason the load failed and are more useful than a generic
    "unknown model type" from a swallowed exception."""
    if not os.path.isfile(os.path.realpath(filename)):
        raise FileNotFoundError("Model file '%s' not found." % filename)

    ext = os.path.splitext(filename)[1]
    loader = _EXT_LOADERS.get(ext)
    if loader is None:
        raise ValueError(
            "Unknown model type: %r. Supported formats: %s"
            % (filename, _SUPPORTED_FORMATS))
    return loader(filename, modelpath, solverclass)
