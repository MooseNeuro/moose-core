# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

# Author: Subhasis Ray
# Maintainer: Dilawar Singh, Harsha Rani, Upi Bhalla

raise ImportError('This submodule contains legacy code only for reference. Not to be imported by users')

import warnings
import os
import pydoc
import io
from contextlib import closing

import moose._moose as _moose
import moose.utils as mu


def about():
    """info: Return some 'about me' information.
    """
    return dict(path=os.path.dirname(__file__),
                version=_moose.VERSION,
                docs='https://moose.readthedocs.io/en/latest/')


# Version
def version():
    # Show user version.
    return _moose.VERSION


def pwe():
    """Print present working element. Convenience function for GENESIS
    users. If you want to retrieve the element in stead of printing
    the path, use moose.getCwe()

    >>> pwe()
    >>> '/'
    """
    pwe_ = _moose.getCwe()
    print(pwe_.path)
    return pwe_


def le(el=None):
    """List elements under `el` or current element if no argument
    specified.

    Parameters
    ----------
    el : str/melement/vec/None
        The element or the path under which to look. If `None`, children
         of current working element are displayed.

    Returns
    -------
    List of path of child elements

    """
    if el is None:
        el = _moose.getCwe()
    elif isinstance(el, str):
        if not _moose.exists(el):
            raise ValueError('no such element')
        el = _moose.element(el)
    elif isinstance(el, _moose.vec):
        el = el[0]
    print("Elements under '%s'" % el.path)
    for ch in el.children:
        print(" %s" % ch.path)
    return [child.path for child in el.children]


# ce is a GENESIS shorthand for change element.
ce = _moose.setCwe


def syncDataHandler(target):
    """Synchronize data handlers for target.

    Parameters
    ----------
    target : melement/vec/str
        Target element or vec or path string.

    Raises
    ------
    NotImplementedError
        The call to the underlying C++ function does not work.

    Notes
    -----
    This function is defined for completeness, but currently it does not work.

    """
    raise NotImplementedError(
        'The implementation is not working for IntFire - goes to invalid objects. \
First fix that issue with SynBase or something in that line.')
    if isinstance(target, str):
        if not _moose.exists(target):
            raise ValueError('%s: element does not exist.' % (target))
        target = _moose.vec(target)
        _moose.syncDataHandler(target)


def showfield(el, field='*', showtype=False):
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
    string

    """
    if isinstance(el, str):
        if not _moose.exists(el):
            raise ValueError('no such element: %s' % el)
        el = _moose.element(el)
    result = []
    if field == '*':
        value_field_dict = _moose.getFieldDict(el.className, 'valueFinfo')
        max_type_len = max(len(dtype) for dtype in value_field_dict.values())
        max_field_len = max(len(dtype) for dtype in value_field_dict.keys())
        result.append('\n[' + el.path + ']\n')
        for key, dtype in sorted(value_field_dict.items()):
            if dtype == 'bad' or key == 'this' or key == 'dummy' \
                or key == 'me' or dtype.startswith('vector') \
                or 'ObjId' in dtype:
                continue
            value = el.getField(key)
            if showtype:
                typestr = dtype.ljust(max_type_len + 4)
                # The following hack is for handling both Python 2 and
                # 3. Directly putting the print command in the if/else
                # clause causes syntax error in both systems.
                result.append(typestr + ' ')
            result.append(
                key.ljust(max_field_len + 4) + '=' + str(value) + '\n')
    else:
        try:
            result.append(field + '=' + el.getField(field))
        except AttributeError:
            pass  # Genesis silently ignores non existent fields
    print(''.join(result))
    return ''.join(result)


def showfields(el, showtype=False):
    """
    Print all fields on a a given element.
    """
    warnings.warn(
        'Deprecated. Use showfield(element, field="*", showtype=True) instead.',
        DeprecationWarning)
    return showfield(el, field='*', showtype=showtype)


# Predefined field types and their human readable names
finfotypes = [('valueFinfo', 'value field'),
              ('srcFinfo', 'source message field'),
              ('destFinfo', 'destination message field'),
              ('sharedFinfo', 'shared message field'),
              ('lookupFinfo', 'lookup field')]


def listmsg(el):
    """Return a list containing the incoming and outgoing messages of
    `el`.

    Parameters
    ----------
    el : melement/vec/str
        MOOSE object or path of the object to look into.

    Returns
    -------
    msg : list
        List of Msg objects corresponding to incoming and outgoing
        connections of `el`.

    """
    obj = _moose.element(el)
    ret = []
    for msg in obj.msgIn:
        ret.append(msg)
    for msg in obj.msgOut:
        ret.append(msg)
    return ret


def showmsg(el):
    """Print the incoming and outgoing messages of `el`.

    Parameters
    ----------
    el : melement/vec/str
        Object whose messages are to be displayed.

    Returns
    -------
    None

    """
    obj = _moose.element(el)
    print('INCOMING:')
    for msg in obj.msgIn:
        print(msg.e2.path, msg.destFieldsOnE2, '<---', msg.e1.path,
              msg.srcFieldsOnE1)
    print('OUTGOING:')
    for msg in obj.msgOut:
        print(msg.e1.path, msg.srcFieldsOnE1, '--->', msg.e2.path,
              msg.destFieldsOnE2)


def getFieldDoc(tokens, indent=''):
    """Return the documentation for field specified by `tokens`.

    Parameters
    ----------
    tokens : (className, fieldName) str
        A sequence whose first element is a MOOSE class name and second
        is the field name.

    indent : str
        indentation (default: empty string) prepended to builtin
        documentation string.

    Returns
    -------
    docstring : str
        string of the form
        `{indent}{className}.{fieldName}: {datatype} - {finfoType}\n{Description}\n`

    Raises
    ------
    NameError
        If the specified fieldName is not present in the specified class.
    """
    assert (len(tokens) > 1)
    classname = tokens[0]
    fieldname = tokens[1]
    while True:
        try:
            classelement = _moose.element('/classes/' + classname)
            for finfo in classelement.children:
                for fieldelement in finfo:
                    baseinfo = ''
                    if classname != tokens[0]:
                        baseinfo = ' (inherited from {})'.format(classname)
                    if fieldelement.fieldName == fieldname:
                        # The field elements are
                        # /classes/{ParentClass}[0]/{fieldElementType}[N].
                        finfotype = fieldelement.name
                        return u'{indent}{classname}.{fieldname}: type={type}, finfotype={finfotype}{baseinfo}\n\t{docs}\n'.format(
                            indent=indent,
                            classname=tokens[0],
                            fieldname=fieldname,
                            type=fieldelement.type,
                            finfotype=finfotype,
                            baseinfo=baseinfo,
                            docs=fieldelement.docs)
            classname = classelement.baseClass
        except ValueError:
            raise NameError('`%s` has no field called `%s`' %
                            (tokens[0], tokens[1]))

def _appendFinfoDocs(classname, docstring, indent):
    """Append list of finfos in class name to docstring"""
    try:
        classElem = _moose.element('/classes/%s' % (classname))
    except ValueError:
        raise NameError('class \'%s\' not defined.' % (classname))
    for ftype, rname in finfotypes:
        docstring.write(u'\n*%s*\n' % (rname.capitalize()))
        try:
            finfo = _moose.element('%s/%s' % (classElem.path, ftype))
            for field in finfo.vec:
                docstring.write(u'%s%s: %s\n' %
                                (indent, field.fieldName, field.type))
        except ValueError:
            docstring.write(u'%sNone\n' % (indent))



def _getMooseDoc(tokens, inherited=False):
    """Return MOOSE builtin documentation.
    """
    indent = '  '
    docstring = io.StringIO()
    with closing(docstring):
        if not tokens:
            return ""
        try:
            classElem = _moose.element('/classes/%s' % (tokens[0]))
        except ValueError:
            raise NameError("Name '%s' not defined." % (tokens[0]))

        if len(tokens) > 1:
            docstring.write(getFieldDoc(tokens))
            return docstring.getvalue()

        docstring.write(u'%s\n' % (classElem.docs))
        _appendFinfoDocs(tokens[0], docstring, indent)
        if not inherited:
            return docstring.getvalue()

        mro = eval('_moose.%s' % (tokens[0])).mro()
        for class_ in mro[1:]:
            if class_ == _moose.melement:
                break
            docstring.write(u"\n# Inherited from '%s'\n" % (class_.__name__))
            _appendFinfoDocs(class_.__name__, docstring, indent)
            if class_ == _moose.Neutral:
                break
        return docstring.getvalue()


__pager = None

def doc(arg, inherited=True, paged=True):
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

    paged: bool
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
    # There is no way to dynamically access the MOOSE docs using
    # pydoc. (using properties requires copying all the docs strings
    # from MOOSE increasing the loading time by ~3x). Hence we provide a
    # separate function.
    global __pager
    if paged and __pager is None:
        __pager = pydoc.pager
    tokens = []
    text = ''
    if isinstance(arg, str):
        tokens = arg.split('.')
        if tokens[0] in ['moose', '_moose']:
            tokens = tokens[1:]
    elif isinstance(arg, type):
        tokens = [arg.__name__]
    elif isinstance(arg, _moose.melement) or isinstance(arg, _moose.vec):
        text = '%s: %s\n\n' % (arg.path, arg.className)
        tokens = [arg.className]
    if tokens:
        text += _getMooseDoc(tokens, inherited=inherited)
    else:
        text += pydoc.getdoc(arg)
    if __pager:
        __pager(text)
    else:
        print(text)


#############################################################
# This is a dump of old code that is no longer needed
# due to updates in moose
#############################################################

#============================================================
# From utils.py
#------------------------------------------------------------

def create_table_path(model, graph, element, field):

    field = field[0].upper() + field[1:]

    tablePathSuffix = element.path.partition(model.path)[-1]
    if tablePathSuffix.startswith("/"):
        tablePathSuffix = tablePathSuffix[1:]

    tablePathSuffix = tablePathSuffix.replace("/", "_") + "." + field
    tablePathSuffix = re.sub(
        ".", lambda m: {"[": "_", "]": "_"}.get(m.group(), m.group()), tablePathSuffix
    )

    if tablePathSuffix.startswith("_0__"):
        tablePathSuffix = tablePathSuffix[4:]

    # tablePath = dataroot + '/' +tablePath
    tablePath = graph.path + "/" + tablePathSuffix
    return tablePath


def create_table(tablePath, element, field, tableType):
    """Create table to record `field` from element `element`

    Tables are created under `dataRoot`, the names are generally
    created by removing `/model` in the beginning of `elementPath`
    and replacing `/` with `_`. If this conflicts with an existing
    table, the id value of the target element (elementPath) is
    appended to the name.
    """
    if moose.exists(tablePath):
        table = moose.element(tablePath)
    else:
        if tableType == "Table2":
            table = moose.Table2(tablePath)
        elif tableType == "Table":
            table = moose.Table(tablePath)
        moose.connect(table, "requestOut", element, "get%s" % (field))
    return table


def readtable(table, filename, separator=None):
    """Reads the file specified by filename to fill the MOOSE table object.

    The file can either have one float on each line, in that case the
    table will be filled with values sequentially.
    Or, the file can have
    index value
    on each line. If the separator between index and value is anything other than
    white space, you can specify it in the separator argument."""

    in_file = open(filename)
    ii = 0
    line_no = 0
    for line in in_file:
        line_no = line_no + 1
        tokens = line.split(separator)
        if not tokens:
            continue
        elif len(tokens) == 1:
            table[ii] = float(tokens[0])
        elif len(tokens) == 2:
            table[int(tokens[0])] = float(tokens[1])
        else:
            print(
                "pymoose.readTable(",
                table,
                ",",
                filename,
                ",",
                separator,
                ") - line#",
                line_no,
                " does not fit.",
            )

############# added by Aditya Gilra -- begin ################


def resetSim(simpaths, simdt, plotdt, simmethod="hsolve"):
    """ For each of the MOOSE paths in simpaths, this sets the clocks and finally resets MOOSE.
    If simmethod=='hsolve', it sets up hsolve-s for each Neuron under simpaths, and clocks for hsolve-s too. """
    print("Solver:", simmethod)
    moose.setClock(INITCLOCK, simdt)
    moose.setClock(ELECCLOCK, simdt)  # The hsolve and ee methods use clock 1
    moose.setClock(
        CHANCLOCK, simdt
    )  # hsolve uses clock 2 for mg_block, nmdachan and others.
    moose.setClock(POOLCLOCK, simdt)  # Ca/ion pools & funcs use clock 3
    moose.setClock(STIMCLOCK, simdt)  # Ca/ion pools & funcs use clock 3
    moose.setClock(PLOTCLOCK, plotdt)  # for tables
    for simpath in simpaths:
        ## User can connect [qty]Out of an element to input of Table or
        ## requestOut of Table to get[qty] of the element.
        ## Scheduling the Table to a clock tick, will call process() of the Table
        ## which will send a requestOut and overwrite any value set by input(),
        ## thus adding garbage value to the vector. Hence schedule only if
        ## input message is not connected to the Table.
        for table in moose.wildcardFind(simpath + "/##[TYPE=Table]"):
            if len(table.neighbors["input"]) == 0:
                moose.useClock(PLOTCLOCK, table.path, "process")
        moose.useClock(ELECCLOCK, simpath + "/##[TYPE=PulseGen]", "process")
        moose.useClock(STIMCLOCK, simpath + "/##[TYPE=DiffAmp]", "process")
        moose.useClock(STIMCLOCK, simpath + "/##[TYPE=VClamp]", "process")
        moose.useClock(STIMCLOCK, simpath + "/##[TYPE=PIDController]", "process")
        moose.useClock(STIMCLOCK, simpath + "/##[TYPE=RC]", "process")
        moose.useClock(STIMCLOCK, simpath + "/##[TYPE=TimeTable]", "process")
        moose.useClock(ELECCLOCK, simpath + "/##[TYPE=LeakyIaF]", "process")
        moose.useClock(ELECCLOCK, simpath + "/##[TYPE=IntFire]", "process")
        moose.useClock(ELECCLOCK, simpath + "/##[TYPE=IzhikevichNrn]", "process")
        moose.useClock(ELECCLOCK, simpath + "/##[TYPE=SpikeGen]", "process")
        moose.useClock(ELECCLOCK, simpath + "/##[TYPE=Interpol]", "process")
        moose.useClock(ELECCLOCK, simpath + "/##[TYPE=Interpol2D]", "process")
        moose.useClock(CHANCLOCK, simpath + "/##[TYPE=HHChannel2D]", "process")
        moose.useClock(CHANCLOCK, simpath + "/##[TYPE=SynChan]", "process")
        ## If simmethod is not hsolve, set clocks for the biophysics,
        ## else just put a clock on the hsolve:
        ## hsolve takes care of the clocks for the biophysics
        if "hsolve" not in simmethod.lower():
            print("Using exp euler")
            moose.useClock(INITCLOCK, simpath + "/##[TYPE=Compartment]", "init")
            moose.useClock(ELECCLOCK, simpath + "/##[TYPE=Compartment]", "process")
            moose.useClock(CHANCLOCK, simpath + "/##[TYPE=HHChannel]", "process")
            moose.useClock(POOLCLOCK, simpath + "/##[TYPE=CaConc]", "process")
            moose.useClock(POOLCLOCK, simpath + "/##[TYPE=Func]", "process")
        else:  # use hsolve, one hsolve for each Neuron
            print("Using hsolve")
            element = moose.Neutral(simpath)
            for childid in element.children:
                childobj = moose.Neutral(childid)
                classname = childobj.className
                if classname in ["Neuron"]:
                    neuronpath = childobj.path
                    h = moose.HSolve(neuronpath + "/solve")
                    h.dt = simdt
                    h.target = neuronpath
                    moose.useClock(INITCLOCK, h.path, "process")
    moose.reinit()


def setupTable(name, obj, qtyname, tables_path=None, threshold=None, spikegen=None):
    """ Sets up a table with 'name' which stores 'qtyname' field from 'obj'.
    The table is created under tables_path if not None, else under obj.path . """
    if tables_path is None:
        tables_path = obj.path + "/data"
    ## in case tables_path does not exist, below wrapper will create it
    tables_path_obj = moose.Neutral(tables_path)
    qtyTable = moose.Table(tables_path_obj.path + "/" + name)
    ## stepMode no longer supported, connect to 'input'/'spike' message dest to record Vm/spiktimes
    # qtyTable.stepMode = TAB_BUF
    if spikegen is None:
        if threshold is None:
            ## below is wrong! reads qty twice every clock tick!
            # moose.connect( obj, qtyname+'Out', qtyTable, "input")
            ## this is the correct method
            moose.connect(qtyTable, "requestOut", obj, "get" + qtyname)
        else:
            ## create new spikegen
            spikegen = moose.SpikeGen(tables_path_obj.path + "/" + name + "_spikegen")
            ## connect the compartment Vm to the spikegen
            moose.connect(obj, "VmOut", spikegen, "Vm")
            ## spikegens for different synapse_types can have different thresholds
            spikegen.threshold = threshold
            spikegen.edgeTriggered = (
                1  # This ensures that spike is generated only on leading edge.
            )
    else:
        moose.connect(
            spikegen, "spikeOut", qtyTable, "input"
        )  ## spikeGen gives spiketimes
    return qtyTable


def connectSynapse(compartment, synname, gbar_factor):
    """
    Creates a synname synapse under compartment, sets Gbar*gbar_factor, and attaches to compartment.
    synname must be a synapse in /library of MOOSE.
    """
    synapseid = moose.copy(moose.SynChan("/library/" + synname), compartment, synname)
    synapse = moose.SynChan(synapseid)
    synapse.Gbar = synapse.Gbar * gbar_factor
    synapse_mgblock = moose.Mstring(synapse.path + "/mgblockStr")
    if (
        synapse_mgblock.value == "True"
    ):  # If NMDA synapse based on mgblock, connect to mgblock
        mgblock = moose.Mg_block(synapse.path + "/mgblock")
        compartment.connect("channel", mgblock, "channel")
    else:
        compartment.connect("channel", synapse, "channel")
    return synapse


def printNetTree():
    """ Prints all the cells under /, and recursive prints the cell tree for each cell. """
    root = moose.Neutral("/")
    for id in root.children:  # all subelements of 'root'
        if moose.Neutral(id).className == "Cell":
            cell = moose.Cell(id)
            print(
                "-------------------- CELL : ",
                cell.name,
                " ---------------------------",
            )
            printCellTree(cell)


def printCellTree(cell):
    """
    Prints the tree under MOOSE object 'cell'.
    Assumes cells have all their compartments one level below,
    also there should be nothing other than compartments on level below.
    Apart from compartment properties and messages,
    it displays the same for subelements of compartments only one level below the compartments.
    Thus NMDA synapses' mgblock-s will be left out.

    FIXME: no lenght cound on compartment.
    """
    for compartmentid in cell.children:  # compartments
        comp = moose.Compartment(compartmentid)
        print(
            "  |-",
            comp.path,
            "l=",
            comp.length,
            "d=",
            comp.diameter,
            "Rm=",
            comp.Rm,
            "Ra=",
            comp.Ra,
            "Cm=",
            comp.Cm,
            "EM=",
            comp.Em,
        )
        # for inmsg in comp.inMessages():
        #    print "    |---", inmsg
        # for outmsg in comp.outMessages():
        #    print "    |---", outmsg
        printRecursiveTree(
            compartmentid, level=2
        )  # for channels and synapses and recursively lower levels


## Use printCellTree which calls this
def printRecursiveTree(elementid, level):
    """ Recursive helper function for printCellTree,
    specify depth/'level' to recurse and print subelements under MOOSE 'elementid'. """
    spacefill = "  " * level
    element = moose.Neutral(elementid)
    for childid in element.children:
        childobj = moose.Neutral(childid)
        classname = childobj.className
        if classname in ["SynChan", "KinSynChan"]:
            childobj = moose.SynChan(childid)
            print(
                spacefill + "|--",
                childobj.name,
                childobj.className,
                "Gbar=",
                childobj.Gbar,
                "numSynapses=",
                childobj.numSynapses,
            )
            return  # Have yet to figure out the children of SynChan, currently not going deeper
        elif classname in ["HHChannel", "HHChannel2D"]:
            childobj = moose.HHChannel(childid)
            print(
                spacefill + "|--",
                childobj.name,
                childobj.className,
                "Gbar=",
                childobj.Gbar,
                "Ek=",
                childobj.Ek,
            )
        elif classname in ["CaConc"]:
            childobj = moose.CaConc(childid)
            print(
                spacefill + "|--",
                childobj.name,
                childobj.className,
                "thick=",
                childobj.thick,
                "B=",
                childobj.B,
            )
        elif classname in ["Mg_block"]:
            childobj = moose.Mg_block(childid)
            print(
                spacefill + "|--",
                childobj.name,
                childobj.className,
                "CMg",
                childobj.CMg,
                "KMg_A",
                childobj.KMg_A,
                "KMg_B",
                childobj.KMg_B,
            )
        elif classname in ["SpikeGen"]:
            childobj = moose.SpikeGen(childid)
            print(
                spacefill + "|--",
                childobj.name,
                childobj.className,
                "threshold",
                childobj.threshold,
            )
        elif classname in ["Func"]:
            childobj = moose.Func(childid)
            print(
                spacefill + "|--",
                childobj.name,
                childobj.className,
                "expr",
                childobj.expr,
            )
        elif classname in [
            "Table"
        ]:  # Table gives segfault if printRecursiveTree is called on it
            return  # so go no deeper
        # for inmsg in childobj.inMessages():
        #    print spacefill+"  |---", inmsg
        # for outmsg in childobj.outMessages():
        #    print spacefill+"  |---", outmsg
        if len(childobj.children) > 0:
            printRecursiveTree(childid, level + 1)


def get_matching_children(parent, names):
    """ Returns non-recursive children of 'parent' MOOSE object
    with their names containing any of the strings in list 'names'. """
    matchlist = []
    for childID in parent.children:
        child = moose.Neutral(childID)
        for name in names:
            if name in child.name:
                matchlist.append(childID)
    return matchlist


def underscorize(path):
    """ Returns: / replaced by underscores in 'path'.
    But async13 branch has indices in the path like [0],
    so just replacing / by _ is not enough,
    should replace [ and ] also by _ """
    return path.replace("/", "_").replace("[", "-").replace("]", "-")


def blockChannels(cell, channel_list):
    """
    Sets gmax to zero for channels of the 'cell' specified in 'channel_list'
    Substring matches in channel_list are allowed
    e.g. 'K' should block all K channels (ensure that you don't use capital K elsewhere in your channel name!)
    """
    for compartmentid in cell.children:  # compartments
        comp = moose.Compartment(compartmentid)
        for childid in comp.children:
            child = moose.Neutral(childid)
            if child.className in ["HHChannel", "HHChannel2D"]:
                chan = moose.HHChannel(childid)
                for channame in channel_list:
                    if channame in chan.name:
                        chan.Gbar = 0.0


def get_child_Mstring(mooseobject, mstring):
    for child in mooseobject.children:
        if child.className == "Mstring" and child.name == mstring:
            child = moose.Mstring(child)
            return child
    return None


def connect_CaConc(compartment_list, temperature=None):
    """ Connect the Ca pools and channels within each of the compartments in compartment_list
     Ca channels should have a child Mstring named 'ion' with value set in MOOSE.
     Ca dependent channels like KCa should have a child Mstring called 'ionDependency' with value set in MOOSE.
     Call this only after instantiating cell so that all channels and pools have been created. """
    for compartment in compartment_list:
        caconc = None
        for child in compartment.children:
            if child.className == "CaConc":
                caconc = moose.CaConc(child)
                break
        if caconc is not None:
            child = get_child_Mstring(caconc, "phi")
            if child is not None:
                caconc.B = float(
                    child.value
                )  # B = phi by definition -- see neuroml 1.8.1 defn
            else:
                ## B has to be set for caconc based on thickness of Ca shell and compartment l and dia,
                ## OR based on the Mstring phi under CaConc path.
                ## I am using a translation from Neuron for mitral cell, hence this method.
                ## In Genesis, gmax / (surfacearea*thick) is set as value of B!
                caconc.B = (
                    1
                    / (2 * FARADAY)
                    / (
                        math.pi
                        * compartment.diameter
                        * compartment.length
                        * caconc.thick
                    )
                )
            for neutralwrap in compartment.children:
                if neutralwrap.className == "HHChannel":
                    channel = moose.HHChannel(child)
                    ## If child Mstring 'ion' is present and is Ca, connect channel current to caconc
                    for childid in channel.children:
                        # in async13, gates which have not been created still 'exist'
                        # i.e. show up as a child, but cannot be wrapped.
                        try:
                            child = moose.element(childid)
                            if child.className == "Mstring":
                                child = moose.Mstring(child)
                                if child.name == "ion":
                                    if child.value in ["Ca", "ca"]:
                                        moose.connect(
                                            channel, "IkOut", caconc, "current"
                                        )
                                        # print 'Connected IkOut of',channel.path,'to current of',caconc.path
                                ## temperature is used only by Nernst part here...
                                if child.name == "nernst_str":
                                    nernst = moose.Nernst(channel.path + "/nernst")
                                    nernst_params = child.value.split(",")
                                    nernst.Cout = float(nernst_params[0])
                                    nernst.valence = int(nernst_params[1])
                                    nernst.Temperature = temperature
                                    moose.connect(nernst, "Eout", channel, "setEk")
                                    moose.connect(caconc, "concOut", nernst, "ci")
                                    # print 'Connected Nernst',nernst.path
                        except TypeError:
                            pass

                if neutralwrap.className == "HHChannel2D":
                    channel = moose.HHChannel2D(child)
                    ## If child Mstring 'ionDependency' is present, connect caconc Ca conc to channel
                    for childid in channel.children:
                        # in async13, gates which have not been created still 'exist'
                        # i.e. show up as a child, but cannot be wrapped.
                        try:
                            child = moose.element(childid)
                            if (
                                child.className == "Mstring"
                                and child.name == "ionDependency"
                            ):
                                child = moose.Mstring(child)
                                if child.value in ["Ca", "ca"]:
                                    moose.connect(caconc, "concOut", channel, "concen")
                                    # print 'Connected concOut of',caconc.path,'to concen of',channel.path
                        except TypeError as e:
                            logger_.warning(e)




def setup_vclamp(compartment, name, delay1, width1, level1, gain=0.5e-5):
    """
    Sets up a voltage clamp with 'name' on MOOSE 'compartment' object:
    adapted from squid.g in DEMOS (moose/genesis)
    Specify the 'delay1', 'width1' and 'level1' of the voltage to be applied to the compartment.
    Typically you need to adjust the PID 'gain'
    For perhaps the Davison 4-compartment mitral or the Davison granule:
    0.5e-5 optimal gain - too high 0.5e-4 drives it to oscillate at high frequency,
    too low 0.5e-6 makes it have an initial overshoot (due to Na channels?)
    Returns a MOOSE table with the PID output.
    """
    ## If /elec doesn't exists it creates /elec and returns a reference to it.
    ## If it does, it just returns its reference.
    moose.Neutral("/elec")
    pulsegen = moose.PulseGen("/elec/pulsegen" + name)
    vclamp = moose.DiffAmp("/elec/vclamp" + name)
    vclamp.saturation = 999.0
    vclamp.gain = 1.0
    lowpass = moose.RC("/elec/lowpass" + name)
    lowpass.R = 1.0
    lowpass.C = 50e-6  # 50 microseconds tau
    PID = moose.PIDController("/elec/PID" + name)
    PID.gain = gain
    PID.tau_i = 20e-6
    PID.tau_d = 5e-6
    PID.saturation = 999.0
    # All connections should be written as source.connect('',destination,'')
    pulsegen.connect("outputSrc", lowpass, "injectMsg")
    lowpass.connect("outputSrc", vclamp, "plusDest")
    vclamp.connect("outputSrc", PID, "commandDest")
    PID.connect("outputSrc", compartment, "injectMsg")
    compartment.connect("VmSrc", PID, "sensedDest")

    pulsegen.trigMode = 0  # free run
    pulsegen.baseLevel = -70e-3
    pulsegen.firstDelay = delay1
    pulsegen.firstWidth = width1
    pulsegen.firstLevel = level1
    pulsegen.secondDelay = 1e6
    pulsegen.secondLevel = -70e-3
    pulsegen.secondWidth = 0.0

    vclamp_I = moose.Table("/elec/vClampITable" + name)
    vclamp_I.stepMode = TAB_BUF  # TAB_BUF: table acts as a buffer.
    vclamp_I.connect("inputRequest", PID, "output")
    vclamp_I.useClock(PLOTCLOCK)

    return vclamp_I


def setup_iclamp(compartment, name, delay1, width1, level1):
    """
    Sets up a current clamp with 'name' on MOOSE 'compartment' object:
    Specify the 'delay1', 'width1' and 'level1' of the current pulse to be applied to the compartment.
    Returns the MOOSE pulsegen that sends the current pulse.
    """
    ## If /elec doesn't exists it creates /elec and returns a reference to it.
    ## If it does, it just returns its reference.
    moose.Neutral("/elec")
    pulsegen = moose.PulseGen("/elec/pulsegen" + name)
    iclamp = moose.DiffAmp("/elec/iclamp" + name)
    iclamp.saturation = 1e6
    iclamp.gain = 1.0
    pulsegen.trigMode = 0  # free run
    pulsegen.baseLevel = 0.0
    pulsegen.firstDelay = delay1
    pulsegen.firstWidth = width1
    pulsegen.firstLevel = level1
    pulsegen.secondDelay = 1e6  # to avoid repeat
    pulsegen.secondLevel = 0.0
    pulsegen.secondWidth = 0.0
    pulsegen.connect("output", iclamp, "plusIn")
    iclamp.connect("output", compartment, "injectMsg")
    return pulsegen

######################################################################
# Subha: Moved all scheduling utilities here. These are not necessary
# any more because scheduling is automatic in the core now.
#
# Date: Sun Mar 22 12:03:47 IST 2026
######################################################################

## Subha: In many scenarios resetSim is too rigid and focussed on
## neuronal simulation.  The setDefaultDt and
## assignTicks/assignDefaultTicks keep the process of assigning dt to
## ticks and assigning ticks to objects separate. reinit() should be
## explicitly called by user just before running a simulation, and not
## when setting it up.
def updateTicks(tickDtMap):
    """Try to assign dt values to ticks.

    Parameters
    ----------
    tickDtMap: dict
    map from tick-no. to dt value. if it is empty, then default dt
    values are assigned to the ticks.

    """
    for tickNo, dt in list(tickDtMap.items()):
        if tickNo >= 0 and dt > 0.0:
            moose.setClock(tickNo, dt)
    if all([(v == 0) for v in list(tickDtMap.values())]):
        setDefaultDt()


def assignTicks(tickTargetMap):
    """
    Assign ticks to target elements.

    Parameters
    ----------
    tickTargetMap:
    Map from tick no. to target path and method. The path can be wildcard expression also.
    """
    if len(tickTargetMap) == 0:
        assignDefaultTicks()
    for tickNo, target in list(tickTargetMap.items()):
        if not isinstance(target, str):
            if len(target) == 1:
                moose.useClock(tickNo, target[0], "process")
            elif len(target) == 2:
                moose.useClock(tickNo, target[0], target[1])
        else:
            moose.useClock(tickNo, target, "process")

    # # This is a hack, we need saner way of scheduling
    # ticks = moose.vec('/clock/tick')
    # valid = []
    # for ii in range(ticks[0].localNumField):
    #     if ticks[ii].dt > 0:
    #         valid.append(ii)
    # if len(valid) == 0:
    #     assignDefaultTicks()


def setDefaultDt(elecdt=1e-5, chemdt=0.01, tabdt=1e-5, plotdt1=1.0, plotdt2=0.25e-3):
    """Setup the ticks with dt values.

    Parameters
    ----------

    elecdt: dt for ticks used in computing electrical biophysics, like
    neuronal compartments, ion channels, synapses, etc.

    chemdt: dt for chemical computations like enzymatic reactions.

    tabdt: dt for lookup tables

    plotdt1: dt for chemical kinetics plotting

    plotdt2: dt for electrical simulations

    """
    moose.setClock(0, elecdt)
    moose.setClock(1, elecdt)
    moose.setClock(2, elecdt)
    moose.setClock(3, elecdt)
    moose.setClock(4, chemdt)
    moose.setClock(5, chemdt)
    moose.setClock(6, tabdt)
    moose.setClock(7, tabdt)
    moose.setClock(8, plotdt1)  # kinetics sim
    moose.setClock(9, plotdt2)  # electrical sim


def assignDefaultTicks(modelRoot="/model", dataRoot="/data", solver="hsolve"):
    if not isinstance(modelRoot, str):
        modelRoot = modelRoot.path
    if not isinstance(dataRoot, str):
        dataRoot = dataRoot.path
    if (
        solver != "hsolve"
        or len(moose.wildcardFind("%s/##[ISA=HSolve]" % (modelRoot))) == 0
    ):
        moose.useClock(0, "%s/##[ISA=Compartment]" % (modelRoot), "init")
        moose.useClock(1, "%s/##[ISA=Compartment]" % (modelRoot), "process")
        moose.useClock(2, "%s/##[ISA=HHChannel]" % (modelRoot), "process")
        # moose.useClock(2, '%s/##[ISA=ChanBase]'  % (modelRoot), 'process')
    moose.useClock(0, "%s/##[ISA=IzhikevichNrn]" % (modelRoot), "process")
    moose.useClock(0, "%s/##[ISA=GapJunction]" % (modelRoot), "process")
    moose.useClock(0, "%s/##[ISA=HSolve]" % (modelRoot), "process")
    moose.useClock(1, "%s/##[ISA=LeakyIaF]" % (modelRoot), "process")
    moose.useClock(1, "%s/##[ISA=IntFire]" % (modelRoot), "process")
    moose.useClock(1, "%s/##[ISA=SpikeGen]" % (modelRoot), "process")
    moose.useClock(1, "%s/##[ISA=PulseGen]" % (modelRoot), "process")
    moose.useClock(1, "%s/##[ISA=StimulusTable]" % (modelRoot), "process")
    moose.useClock(1, "%s/##[ISA=TimeTable]" % (modelRoot), "process")
    moose.useClock(2, "%s/##[ISA=HHChannel2D]" % (modelRoot), "process")
    moose.useClock(2, "%s/##[ISA=SynChan]" % (modelRoot), "process")
    moose.useClock(2, "%s/##[ISA=MgBlock]" % (modelRoot), "process")
    moose.useClock(3, "%s/##[ISA=CaConc]" % (modelRoot), "process")
    moose.useClock(3, "%s/##[ISA=Func]" % (modelRoot), "process")
    # The voltage clamp circuit depends critically on the dt used for
    # computing soma Vm and need to be on a clock with dt=elecdt.
    moose.useClock(0, "%s/##[ISA=DiffAmp]" % (modelRoot), "process")
    moose.useClock(0, "%s/##[ISA=VClamp]" % (modelRoot), "process")
    moose.useClock(0, "%s/##[ISA=PIDController]" % (modelRoot), "process")
    moose.useClock(0, "%s/##[ISA=RC]" % (modelRoot), "process")
    # Special case for kinetics models
    kinetics = moose.wildcardFind("%s/##[FIELD(name)=kinetics]" % modelRoot)
    if len(kinetics) > 0:
        # Do nothing for kinetics models - until multiple scheduling issue is fixed.
        moose.useClock(4, "%s/##[ISA!=PoolBase]" % (kinetics[0].path), "process")
        moose.useClock(5, "%s/##[ISA==PoolBase]" % (kinetics[0].path), "process")
        moose.useClock(18, "%s/##[ISA=Table2]" % (dataRoot), "process")
    else:
        # input() function is called in Table. process() which gets
        # called at each timestep. When a message is connected
        # explicitly to input() dest field, it is driven by the sender
        # and process() adds garbage value to the vector. Hence not to
        # be scheduled.
        for tab in moose.wildcardFind("%s/##[ISA=Table]" % (dataRoot)):
            if len(tab.neighbors["input"]) == 0:
                moose.useClock(9, tab.path, "process")





#
# moose.py ends here
