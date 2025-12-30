"""pyMOOSE

Python bindings of MOOSE simulator.

References:
-----------

- `Documentation https://moose.readthedocs.io/en/latest/`
- `Development https://github.com/BhallaLab/moose-core`

"""

# Notes
# -----
#
# 1. Use these guidelines for docstring:
# https://numpydoc.readthedocs.io/en/latest/format.html.
#
# 2. We redefine many functions defined in _moose just to add the
# docstring since Python C-API does not provide a way to add docstring
# to a function defined in the C/C++ extension

import sys
import pydoc
import os
import warnings
import atexit

import moose._moose as _moose
from moose import model_utils


__moose_classes__ = {}

#: These fields are system fields and should not be displayed unless
#: user requests explicitly
_sys_fields = {
    'fieldIndex',
    'idValue',
    'index',
    'numData',
    'numField',
    'path',
    'this',
    'me',
}

# ==============================================
# CONSTANTS
# ==============================================
OUTMSG = 0  #: Outgoing messages
INMSG = 1  #: Incoming messages
ALLMSG = 2  #: All messages"""


class melement(_moose.ObjId):
    """Base class for all moose classes."""

    __type__ = "UNKNOWN"
    __doc__ = ""

    def __init__(self, x, n=1, **kwargs):
        if isinstance(x, str):
            obj = _moose.vec(x, n, self.__type__)
        else:
            obj = _moose.vec(x.path)
        # else:
        #   raise TypeError(f"Expected str or ObjId, got {type(x)}")
        super().__init__(obj.oid)
        for k, v in kwargs.items():
            super().setField(k, v)


def __to_melement(obj):
    global __moose_classes__
    mc = __moose_classes__[obj.type](obj)
    return mc


# # Create MOOSE classes from available Cinfos.
for p in _moose.wildcardFind("/##[TYPE=Cinfo]"):
    cls = type(
        p.name,
        (melement,),
        {"__type__": p.name, "__doc__": _moose.getDoc(p.name)},
    )
    setattr(_moose, cls.__name__, cls)
    __moose_classes__[cls.__name__] = cls


# Import all attributes to global namespace. We must do it here after adding
# class types to _moose.
from moose._moose import *


def version():
    """Returns moose version string."""
    return _moose.__version__


#: MOOSE version string
__version__ = version()


def version_info():
    """Return detailed version information.

    >>> moose.version_info()
    {'build_datetime': 'Friday Fri Apr 17 22:13:00 2020',
     'compiler_string': 'GNU,/usr/bin/c++,7.5.0',
     'major': '3',
     'minor': '3',
     'patch': '1'}
    """
    return _moose.version_info()


def about():
    """general information about pyMOOSE.

    Returns
    -------
    A dict

    Example
    -------
    >>> moose.about()
    {'path': '~/moose-core/_build/python/moose',
     'version': '4.0.0.dev20200417',
     'docs': 'https://moose.readthedocs.io/en/latest/',
     'development': 'https://github.com/BhallaLab/moose-core'}
    """
    return dict(
        path=os.path.dirname(__file__),
        version=_moose.__version__,
        docs="https://moose.readthedocs.io/en/latest/",
        development="https://github.com/MooseNeuro/moose-core",
    )


def wildcardFind(pattern):
    """Find objects using wildcard pattern

    Parameters
    ----------
    pattern : str
       Wildcard (see note below)

    .. note:: Wildcard

    MOOSE allows wildcard expressions of the form
    {PATH}/{WILDCARD}[{CONDITION}].

    {PATH} is valid path in the element tree, {WILDCARD} can be
    # or `##`.

    `#` causes the search to be restricted to the children
    of the element specified by {PATH}.

    `##` makes the search to
    recursively go through all the descendants of the {PATH} element.

    {CONDITION} can be:

    - TYPE={CLASSNAME}: an element satisfies this condition if it is of
      class {CLASSNAME}.
    - ISA={CLASSNAME}: alias for TYPE={CLASSNAME}
    - CLASS={CLASSNAME}: alias for TYPE={CLASSNAME}
    - FIELD({FIELDNAME}){OPERATOR}{VALUE} : compare field {FIELDNAME} with
      {VALUE} by {OPERATOR} where {OPERATOR} is a comparison
      operator (=, !=, >, <, >=, <=).

    Returns
    -------
    list
        A list of found MOOSE objects

    Examples
    --------
    Following returns a list of all the objects under /mymodel whose Vm field
    is >= -65.

    >>> moose.wildcardFind('/mymodel/##[FIELD(Vm)>=-65]')


    List of all objects of type `Compartment` under '/neuron'

    >>> moose.wildcardFind('/neuron/#[ISA=Compartment]')


    List all elements under '/library' whose name start with 'Ca':

    >>> moose.wildcardFind('/library/##/Ca#')

    List all elements under '/library' whose names start with 'Ca':

    >>> moose.wildcardFind('/library/##/Ca#')

    List all elements directly under library whose names end with 'Stellate':

    >>> moose.wildcardFind('/library/#Stellate')

    Note that if there is an element called 'SpinyStellate' (a
    celltype in the cortex) under '/library' this will find it, but
    the following will return an empty list:

    >>> moose.wildcardFind('/library/##/#Stellate')

    """
    return [__to_melement(x) for x in _moose.wildcardFind(pattern)]


def connect(src, srcfield, dest, destfield, msgtype="Single"):
    """Create a message between `srcfield` on `src` object to
    `destfield` on `dest` object.

    This function is used mainly, to say, connect two entities, and
    to denote what kind of give-and-take relationship they share.
    It enables the 'destfield' (of the 'destobj') to acquire the
    data, from 'srcfield'(of the 'src').

    Parameters
    ----------
    src : element/vec/string
        the source object (or its path) the one that provides information.
    srcfield : str
        source field on self (type of the information).
    destobj : element
        Destination object to connect to (The one that need to get
        information).
    destfield : str
        field to connect to on `destobj`
    msgtype : str {'Single', 'OneToAll', 'AllToOne', 'OneToOne', 'Reduce', 'Sparse'}
        type of the message. It can be one of the following (default Single).

    Returns
    -------
    msgmanager: melement
        message-manager for the newly created message.

    Note
    -----
    Alternatively, one can also use the following form::

    >>> src.connect(srcfield, dest, destfield, msgtype)


    Examples
    --------
    Connect the output of a pulse generator to the input of a spike generator::

    >>> pulsegen = moose.PulseGen('pulsegen')
    >>> spikegen = moose.SpikeGen('spikegen')
    >>> moose.connect(pulsegen, 'output', spikegen, 'Vm')
    Or,
    >>> pulsegen.connect('output', spikegen, 'Vm')
    """
    if isinstance(src, str):
        src = element(src)
    if isinstance(dest, str):
        dest = element(dest)
    msg = src.connect(srcfield, dest, destfield, msgtype)
    if msg.name == '/':
        raise RuntimeError(
            f'Could not connect {src}.{srcfield} with {dest}.{destfield}'
        )
    return msg


def loadModel(filename, modelpath, solverclass="gsl"):
    """loadModel: Load model (genesis/cspace) from a file to a specified path.

    Parameters
    ----------
    filename: str
        model description file.
    modelpath: str
        moose path for the top level element of the model to be created.
    method: str
        solver type to be used for simulating the model.
        TODO: Link to detailed description of solvers?

    Returns
    -------
    melement
        moose.element if succcessful else None.

    See also
    --------
    moose.readNML2
    moose.writeNML2 (NotImplemented)
    moose.readSBML
    moose.writeSBML
    """
    return model_utils.mooseReadKkitGenesis(filename, modelpath, solverclass)


def showfields(el, field="*", showtype=False):
    """Show the fields of the element `el`, their data types and
    values in human readable format. Convenience function for GENESIS
    users.

    Parameters
    ----------
    el : melement/str
        Element or path of an existing element.

    field : str
        Field to be displayed. If '*' (default), all fields are displayed.

    showtype : bool
        If True show the data type of each field. False by default.

    Returns
    -------
    None

    """
    el = _moose.element(el)
    print('DEBUG: ', el, type(el))
    result = []
    if field == "*":
        value_field_dict = _moose.getFieldTypeDict(el.className, "valueFinfo")
        max_type_len = max(len(dtype) for dtype in value_field_dict.values())
        max_field_len = max(len(dtype) for dtype in value_field_dict.keys())
        result.append("\n[" + el.path + "]\n")
        # Maintain the common fields first
        common_fields = ['name', 'className', 'tick', 'dt']
        flist = [
            (field, value_field_dict[field], _moose.getField(el, field))
            for field in common_fields
        ]
        for field, dtype in sorted(value_field_dict.items()):
            if (
                (dtype == "bad")
                or dtype.startswith("vector")
                or ("ObjId" in dtype)
                or (field in _sys_fields)
                or (field in common_fields)
            ):
                continue
            flist.append((field, dtype, _moose.getField(el, field)))
        # Extract the length of the longest type name
        max_type_len = len(max(flist, key=lambda x: len(x[1]))[1])
        # Extract the length of the longest field name
        max_field_len = len(max(flist, key=lambda x: len(x[0]))[0])
        for field, dtype, value in flist:
            if showtype:
                result.append(f'{dtype:<{max_type_len+4}} ')
            result.append(f'{field:<{max_field_len + 4}} = {value}\n')
    else:
        try:
            result.append(field + "=" + el.getField(field))
        except AttributeError:
            pass  # Genesis silently ignores non existent fields
    print("".join(result))


def showfield(el, field="*", showtype=False):
    """Alias for showfields."""
    showfields(el, field, showtype)


def sysfields(el, showtype=False):
    """This function shows system fields which are suppressed by `showfields`."""
    el = element(el)
    result = []
    value_field_dict = _moose.getFieldTypeDict(el.className, "valueFinfo")
    max_type_len = max(len(dtype) for dtype in value_field_dict.values())
    max_field_len = max(len(dtype) for dtype in value_field_dict.keys())
    result.append("\n[" + el.path + "]\n")
    for key in sorted(_sys_fields):
        dtype = value_field_dict[key]
        if dtype == "bad" or dtype.startswith("vector") or ("ObjId" in dtype):
            continue
        value = el.getField(key)
        if showtype:
            typestr = dtype.ljust(max_type_len + 4)
            ## The following hack is for handling both Python 2 and
            ## 3. Directly putting the print command in the if/else
            ## clause causes syntax error in both systems.
            result.append(typestr + " ")
        result.append(key.ljust(max_field_len + 4) + "=" + str(value) + "\n")
    print("".join(result))


def doc(arg, paged=True):
    """Display the documentation for class or field in a class.

    Parameters
    ----------
    arg : str/class/melement/vec
        A string specifying a moose class name and a field name
        separated by a dot. e.g., 'Neutral.name'. Prepending `moose.`
        is allowed. Thus moose.doc('moose.Neutral.name') is equivalent
        to the above.
        It can also be string specifying just a moose class name or a
        moose class or a moose object (instance of melement or vec
        or there subclasses). In that case, the builtin documentation
        for the corresponding moose class is displayed.

    paged : bool
        Whether to display the docs via builtin pager or print and
        exit. If not specified, it defaults to False and
        moose.doc(xyz) will print help on xyz and return control to
        command line.

    Returns
    -------
    None

    Raises
    ------
    NameError
        If class or field does not exist.

    """
    text = _moose.getDoc(arg)
    if pydoc.pager:
        pydoc.pager(text)
    else:
        print(text)


# SBML related functions.
def readSBML(filepath, loadpath, solver="ee", validate=True):
    """Load SBML model.

    Parameters
    ----------
    filepath : str
        filepath to be loaded.
    loadpath : str
        Root path for this model e.g. /model/mymodel
    solver : str
        Solver to use (default 'ee').
        Available options are "ee", "gsl", "stochastic", "gillespie"
            "rk", "deterministic"
            For full list see ??
    validate : bool
        When True, run the schema validation.
    """
    return model_utils.mooseReadSBML(filepath, loadpath, solver, validate)


def writeSBML(modelpath, filepath, sceneitems={}):
    """Writes loaded model under modelpath to a file in SBML format.

    Parameters
    ----------
    modelpath : str
        model path in moose e.g /model/mymodel
    filepath : str
        Path of output file.
    sceneitems : dict
        UserWarning: user need not worry about this layout position is saved in
        Annotation field of all the moose Object (pool,Reaction,enzyme).
        If this function is called from
        * GUI - the layout position of moose object is passed
        * command line - NA
        * if genesis/kkit model is loaded then layout position is taken from the file
        * otherwise auto-coordinates is used for layout position.
    """
    return model_utils.mooseWriteSBML(modelpath, filepath, sceneitems)


def writeKkit(modelpath, filepath, sceneitems={}):
    """Writes  loded model under modelpath to a file in Kkit format.

    Parameters
    ----------
    modelpath : str
        Model path in moose.
    filepath : str
        Path of output file.
    """
    return model_utils.mooseWriteKkit(modelpath, filepath, sceneitems)


def readNML2(modelpath, verbose=False):
    """Load neuroml2 model.

    Parameters
    ----------
    modelpath: str
        Path of nml2 file.

    verbose: True
        (defalt False)
        If True, enable verbose logging.

    Raises
    ------
    FileNotFoundError: If modelpath is not found or not readable.
    """
    return model_utils.mooseReadNML2(modelpath, verbose)


def writeNML2(outfile):
    """Write model to NML2. (Not implemented)"""
    raise NotImplementedError("Writing to NML2 is not supported yet")


def addChemSolver(modelpath, solver):
    """Add solver on chemical compartment and its children for calculation.
    (For developers)

    Parameters
    ----------
    modelpath : str
        Model path that is loaded into moose.
    solver : str
        Exponential Euler "ee" is default. Other options are Gillespie ("gssa"),
        Runge Kutta ("gsl"/"rk"/"rungekutta").

    TODO
    ----
    Documentation

    See also
    --------
    deleteChemSolver
    """
    return model_utils.mooseAddChemSolver(modelpath, solver)


def deleteChemSolver(modelpath):
    """Deletes solver on all the compartment and its children

    Notes
    -----
    This is neccesary while created a new moose object on a pre-existing modelpath,
    this should be followed by mooseAddChemSolver for add solvers on to compartment
    to simulate else default is Exponential Euler (ee)

    See also
    --------
    addChemSolver
    """
    return model_utils.mooseDeleteChemSolver(modelpath)


def mergeChemModel(modelpath, dest):
    """Merges two models.

    Merge chemical model in a file `modelpath` with existing MOOSE model at
    path `dest`.

    Parameters
    ----------
    modelpath : str
        Filepath containing a chemical model.
    dest : path
        Existing MOOSE path.

    TODO
    ----
        No example file which shows its use. Deprecated?
    """
    return model_utils.mooseMergeChemModel(modelpath, dest)


def isinstance_(el, classobj):
    """Returns True if `el` is an instance of `classobj` or its
    subclass.

    Like Python's builtin `isinstance` method, this returns `True` if
    `el` is an instance of `classobj` or one of its subclasses. This
    calls `Neutral.isA` with the name of the class represented by
    `classobj` as parameter..

    Parameters
    ----------
    el : moose.melement
        moose object
    classobj : class
        moose class

    Returns
    -------
    True if `classobj` is a MOOSE-baseclass of `el`, False otherwise.

    See also
    --------
    ``moose.Neutral.isA``

    """
    return el.isA(classobj.__name__)


def cleanup(verbose=False):
    """Cleanup everything except system elements"""
    if verbose:
        print('Cleaning up')
    for child in element('/').children:
        if child.name not in ['Msgs', 'clock', 'classes', 'postmaster']:
            if verbose:
                print('  Deleting', child.path)
            delete(child.path)


atexit.register(cleanup)
