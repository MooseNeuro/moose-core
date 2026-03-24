# -* coding: utf-8 -*-
# Utility functions for moose.

import types
import math
from datetime import datetime
from collections import defaultdict
import re

import logging

logger_ = logging.getLogger("moose.utils")

import moose
from moose.moose_constants import *
from moose.print_utils import *

try:
    from moose.network_utils import *
except Exception as e:
    logger_.warning("Network utilities are not loaded due to %s" % e)

# Print and Plot utilities.
try:
    from moose.plot_utils import *
except Exception as e:
    logger_.warning("Plot utilities are not loaded due to '%s'" % e)


def getfields(moose_object):
    """Returns a dictionary of the fields and values in this object."""
    field_names = moose_object.getFieldNames("valueFinfo")
    fields = {}
    for name in field_names:
        fields[name] = moose_object.getField(name)
    return fields


def findAllBut(moose_wildcard, stringToExclude):
    allValidObjects = moose.wildcardFind(moose_wildcard)
    refinedList = []
    for validObject in allValidObjects:
        if validObject.path.find(stringToExclude) == -1:
            refinedList.append(validObject)

    return refinedList


def apply_to_tree(moose_wildcard, python_filter=None, value=None):
    """
    Select objects by a moose/genesis wildcard, apply a python filter on them and apply a value on them.

    moose_wildcard - this follows GENESIS convention.

    {path}/#[{condition}] returns all elements directly under {path} that satisfy condition. For example:

    '/mynetwork/mycell_0/#[TYPE=Compartment]'

    will return all Compartment objects directly under mycell_0 in mynetwork.

    '{path}/##[{condition}]' will recursively go through all the
    objects that are under {path} (i.e. children, grandchildren,
    great-grandchildren and so on up to the leaf level) and a list of
    the ones meet {condition} will be obtained.

    Thus, '/mynetwork/##[TYPE=Compartment]' will return all
    compartments under mynetwork or its children, or children thereof
    and so on.

    python_filter - if a single string, it will be taken as a
    fieldname, and value will be assigned to this field. It can also
    be a lambda function returning True or False which will be applied
    to each id in the id list returned by moose wildcard
    search. Remember, the argument to the lambda will be an Id, so it
    is up to you to wrap it into a moose object of appropriate type. An example is:

    lambda moose_id: Compartment(moose_id).diameter <  2e-6

    If your moose_wildcard selected objects of Compartment class, then
    this lambda function will select only those with diameter less
    than 2 um.

    value - can be a lambda function to apply arbitrary operations on
    the selected objects.

    If python_filter is a string it, the return
    value of applying the lambda for value() will assigned to the
    field specified by python_filter.

    But if it is value is a data object and {python_filter} is a
    string, then {value} will be assigned to the field named
    {python_filter}.


    If you want to assign Rm = 1e6 for each compartment in mycell
    whose name match 'axon_*':

    apply_to_tree('/mycell/##[Class=Compartment]',
            lambda x: 'axon_' in Neutral(x).name,
            lambda x: setattr(Compartment(x), 'Rm', 1e6))

    [you must use setattr to assign value to a field because lambda
    functions don't allow assignments].
    """
    if not isinstance(moose_wildcard, str):
        raise TypeError("moose_wildcard must be a string.")
    id_list = moose.getWildcardList(moose_wildcard, True)
    if isinstance(python_filter, types.LambdaType):
        id_list = [moose_id for moose_id in id_list if python_filter(moose_id)]
    elif isinstance(python_filter, str):
        tmp_id_list = []
        for moose_id in id_list:
            class_ = getattr(moose, moose.element(moose_id).className)
            if hasattr(class_, python_filter):
                tmp_id_list.append(moose_id)
        id_list = tmp_id_list
    else:
        pass
    if isinstance(value, types.LambdaType):
        if isinstance(python_filter, str):
            for moose_id in id_list:
                cls = getattr(moose, moose.Neutral(moose_id).className)
                moose_obj = cls(moose_id)
                setattr(moose_obj, python_filter, value(moose_id))
        else:
            for moose_id in id_list:
                value(moose_id)
    else:
        if isinstance(python_filter, str):
            for moose_id in id_list:
                cls = getattr(moose, moose.Neutral(moose_id).className)
                moose_obj = cls(moose_id)
                setattr(moose_obj, python_filter, value)
        else:
            raise TypeError(
                "Second argument must be a string specifying a field to assign to when third argument is a value"
            )



# 2012-01-11 19:20:39 (+0530) Subha: checked for compatibility with dh_branch
def printtree(root, vchar="|", hchar="__", vcount=1, depth=0, prefix="", is_last=False):
    """Pretty-print a MOOSE tree.

    root - the root element of the MOOSE tree, must be some derivatine of Neutral.

    vchar - the character printed to indicate vertical continuation of
    a parent child relationship.

    hchar - the character printed just before the node name

    vcount - determines how many lines will be printed between two
    successive nodes.

    depth - for internal use - should not be explicitly passed.

    prefix - for internal use - should not be explicitly passed.

    is_last - for internal use - should not be explicitly passed.

    """
    root = moose.element(root)
    # print('%s: "%s"' % (root, root.children))
    for i in range(vcount):
        print(prefix)

    if depth != 0:
        print(prefix + hchar, end=" ")
        if is_last:
            index = prefix.rfind(vchar)
            prefix = prefix[:index] + " " * (len(hchar) + len(vchar)) + vchar
        else:
            prefix = prefix + " " * len(hchar) + vchar
    else:
        prefix = prefix + vchar

    print(root.name)
    children = []
    for child_vec in root.children:
        try:
            child = moose.element(child_vec)
            children.append(child)
        except TypeError:
            pass
            # print 'TypeError:', child_vec, 'when converting to element.'
    for i in range(0, len(children) - 1):
        printtree(children[i], vchar, hchar, vcount, depth + 1, prefix, False)
    if len(children) > 0:
        printtree(children[-1], vchar, hchar, vcount, depth + 1, prefix, True)


def df_traverse(root, operation, *args):
    """Traverse the tree in a depth-first manner and apply the
    operation using *args. The first argument is the root object by
    default."""
    if hasattr(root, "_visited"):
        return
    operation(root, *args)
    for child in root.children:
        childNode = moose.Neutral(child)
        df_traverse(childNode, operation, *args)
    root._visited = True


def autoposition(root):
    """Automatically set the positions of the endpoints of all the
    compartments under `root`.

    This keeps x and y constant and extends the positions in
    z-direction only. This of course puts everything in a single line
    but suffices for keeping electrical properties intact.

    TODO: in future we may want to create the positions for nice
    visual layout as well. My last attempt resulted in some
    compartments overlapping in space.

    """
    compartments = moose.wildcardFind("%s/##[TYPE=Compartment]" % (root.path))
    stack = [
        compartment
        for compartment in map(moose.element, compartments)
        if len(compartment.neighbors["axial"]) == 0
    ]

    assert len(stack) == 1, (
        "There must be one and only one top level\
            compartment. Found %d"
        % len(stack)
    )
    ret = stack[0]
    while len(stack) > 0:
        comp = stack.pop()
        parentlist = comp.neighbors["axial"]
        parent = None
        if len(parentlist) > 0:
            parent = parentlist[0]
            comp.x0, comp.y0, comp.z0, = parent.x, parent.y, parent.z
        else:
            comp.x0, comp.y0, comp.z0, = (0, 0, 0)
        if comp.length > 0:
            comp.x, comp.y, comp.z, = comp.x0, comp.y0, comp.z0 + comp.length
        else:
            # for spherical compartments x0, y0, z0 are centre
            # position nad x,y,z are on the surface
            comp.x, comp.y, comp.z, = comp.x0, comp.y0, comp.z0 + comp.diameter / 2.0
        # We take z == 0 as an indicator that this compartment has not
        # been processed before - saves against inadvertent loops.
        stack.extend(
            [
                childcomp
                for childcomp in map(moose.element, comp.neighbors["raxial"])
                if childcomp.z == 0
            ]
        )
    return ret


def stepRun(simtime, steptime, verbose=True, logger=None):
    """Run the simulation in steps of `steptime` for `simtime`."""
    global logger_
    if logger is None:
        logger = logger_
    clock = moose.element("/clock")
    if verbose:
        msg = "Starting simulation for %g" % (simtime)
        logger_.info(msg)
    ts = datetime.now()
    while clock.currentTime < simtime - steptime:
        ts1 = datetime.now()
        moose.start(steptime)
        te = datetime.now()
        td = te - ts1
        if verbose:
            msg = "Simulated till %g. Left: %g. %g of simulation took: %g s" % (
                clock.currentTime,
                simtime - clock.currentTime,
                steptime,
                td.days * 86400 + td.seconds + 1e-6 * td.microseconds,
            )
            logger_.info(msg)

    remaining = simtime - clock.currentTime
    if remaining > 0:
        if verbose:
            msg = "Running the remaining %g." % (remaining)
            logger_.info(msg)
        moose.start(remaining)
    te = datetime.now()
    td = te - ts
    dt = min([t for t in moose.element("/clock").dts if t > 0.0])
    if verbose:
        msg = "Finished simulation of %g with minimum dt=%g in %g s" % (
            simtime,
            dt,
            td.days * 86400 + td.seconds + 1e-6 * td.microseconds,
        )
        logger_.info(msg)
