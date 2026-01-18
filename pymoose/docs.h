/* docs.h ---
 *
 * Filename: docs.h
 * Description:
 * Author: Subhasis Ray
 * Created: Tue Dec 30 13:20:01 2025 (+0530)
 */

/* Code: */
#pragma once

namespace pymoose::docs {

constexpr const char* Id_path = "Path of the moose object";
constexpr const char* ObjId_init_root = "Create ObjId pointing to root element";
constexpr const char* ObjId_init_other = "Copy constructor";
constexpr const char* ObjId_init_id =
    "Create ObjId from Id with optional data and field indices";
constexpr const char* ObjId_init_path =
    "Create reference to existing ObjId at path";
constexpr const char* ObjId_name = "Name of the moose element";
constexpr const char* ObjId_className = "Class of the element";
constexpr const char* ObjId_parent = "Parent element of this object";
constexpr const char* ObjId_children = "List of child elements of this object";
constexpr const char* ObjId_id =
    "Id of this element. Every moose element is an entry in a `vec` object. "
    "The Id identifies the `vec` object.";

constexpr const char* ObjId_dataIndex =
    "index of this element in the `vec` object that contains it.";

constexpr const char* ObjId_fieldIndex =
    "If this is a FieldElement, the index of this element within that";
constexpr const char* ObjId_connect = R"(Connect to another object"

Parameters
----------
srcfield: str
    Source field on this object
dest: ObjId
    Target object
destfield: str
    Target field on destination object

Returns
-------
ObjId
   Msg object for the connection
)";

constexpr const char* ObjId_vec = "`vec` object this element belongs to.";

constexpr const char* ObjId_connectToVec = R"(Connect to a `vec` object"

Parameters
----------
srcfield: str
    Source field on this object
dest: MooseVec
    Target vec object
destfield: str
    Target field on destination object

Returns
-------
ObjId
   Msg object for the connection
)";

constexpr const char* MooseVec_init =
    R"(Create a vec object with `n` elements at `path`.

Parameters
----------
path: str
    Path of the created object
n: unsigned int
    Number of elements in the object (default: 1)
dtype: str
    Class of the vec to create
)";

constexpr const char* MooseVec_connect = R"(Connect to another object"
Parameters
----------
srcfield: str
    Source field on source object
dest: ObjId or vec
    Target object
destfield: str
    Target field on destination object

Returns
-------
ObjId
   Msg object for the connection
)";


constexpr const char* ElementField_num =
    R"(number of entries in the field element)";
constexpr const char* ElementField_id =
    R"(Id of the field element)";
constexpr const char* ElementField_oid =
    R"(ObjId of the field element)";
constexpr const char* ElementField_owner =
    R"(ObjId of the owner of the field element)";
constexpr const char* ElementField_vec =
    R"(Access to the field element as a vec object)";

// =============================
// Utility functions
// =============================
constexpr const char* seed = R"(Seed the random number generator in MOOSE

Note that MOOSE has an independent random number generator using
C++ std::mersenne_twister_engine. This is separate from numpy or python
random number generator. Thus setting seed or generating a new random
number with moose.rand in MOOSE does not affect other generators, nor
does the state of any other random number generator affect the generator
in MOOSE.

)";

constexpr const char* rand = R"(Generate random number from MOOSE.

Note that MOOSE has an independent random number generator using
C++ std::mersenne_twister_engine. This is separate from numpy or python
random number generator. Thus setting seed or generating a new random
number with moose.rand in MOOSE does not affect other generators, nor
does the state of any other random number generator affect the generator
in MOOSE.
)";

constexpr const char* convertToObjId = R"(Get a handle for existing element.

Convert a path or an object to the appropriate builtin moose class instance

Parameters
----------
arg : str/vec/moose object
    path of the moose element to be converted or another element (possibly
    available as a superclass instance).

Returns
-------
melement
    MOOSE element (object) corresponding to the `arg` converted to write
    subclass.

Raises
------
RunTimeError if `args` is a string path, but no such element exists.)";


constexpr const char* exists = "Return True if an element with this path exists, False otherwise.";

constexpr const char* getCwe = "Get current working element";

constexpr const char* setCwe = "Set current working element";

constexpr const char* listElements = "List elements under `path`, or the current working element if "
    "`path` is not specified.";

constexpr const char* showMsg =
    R"(Display message connections for an element.

Parameters
----------
obj : ObjId
    Element to inspect
direction : MsgDirection, optional
    Which messages to show (default: Both). Also takes
    integers, 0 for outgoing, 1 for incoming and 2 for both.
)";

constexpr const char* listMsg = R"(List of message connection objects (of class `Msg`).

Parameters
----------
obj: ObjId
    Element to inspect
direction: MsgDirection, optional
    Which messages to include (default: Both). Also takes
    integers, 0 for outgoing, 1 for incoming and 2 for both.
)";

constexpr const char* getNeighbors =
    R"(Get elements connected via messages.

Parameters
----------
obj: melement, ObjId or Id
    The source element
field: str, optional
    Find neighbors connected to this field: a source or dest field name or
    "*" for all fields (default: "*")
msgType: str, optional
    Message type to include. It can be 'Single', 'OneToOne',
    'OneToAll', 'Diagonal', or 'Sparse'. It is not case-sensitive. If an
    empty string is specified, messages of all types are
    included (default: "").
direction: MsgDirection or int
    Direction of the connection. `MsgDirection.Out` or 0 for outgoing,
    `MsgDirection.In` or 1 for incoming, and `MsgDirection.Both` or 2 for
    both incoming and outgoing connections (default: MsgDirection.Both)

Returns
-------
list
    Neighboring elements connected to `obj` via messages
)";

constexpr const char* connect = R"(Connect two objects via messages"

Parameters
----------
src: ObjId
    Source object
srcfield: str
    Source field on source object
dest: ObjId
    Target object
destfield: str
    Target field on destination object

Returns
-------
ObjId
   Msg object for the connection
)";

constexpr const char* getFieldNames =
    R"(Get field names in a MOOSE class.

Parameters
----------
classname : str, ObjId, vec
    Name of the MOOSE class or an element or a vec
fieldtype : str, optional
    Types of fields: "value", "src", "dest", "loookup", "element", or
    "*" (default: "*"). If "*", all types of fields are included.

Returns
-------
list
    Field names
)";

constexpr const char* getFieldTypeDict =
    R"(Get field names and their types for a MOOSE class.

Parameters
----------
classname : str, ObjId, vec
    Name of the MOOSE class or an element of a vec
fieldtype : str, optional
    Type of fields: "value", "src", "dest", "*" (default: "*")
    If "*", all types of fields are included.

Returns
-------
dict
    Mapping of field names to types

Examples
--------
List all the source fields on class Neutral

>>> moose.getFieldDict('Neutral', 'srcFinfo')
   {'childMsg': 'int'}
)";

constexpr const char* getFieldGeneric = R"(Get field `field` of element `obj`.

Parameters
----------
obj: melement
    object to retrieve field of.
field: str
    name of the field to be retrieved

Returns
-------
field value if `field` names a valueFinfo; if `field` names a
destFinfo, the corresponding callable; a LookupField or ElementField
object for those finfo types.
)";

constexpr const char* setClock =
    R"(Set the ticking-interval of clock-tick.

Parameters
----------
tick: unsigned int
    Tick number to set
dt: float
    Tick interval of the clock-tick
)";

constexpr const char* useClock =
    R"(Assign a clock-tick to specified objects.

The sequence of clockticks with the same dt is
according to their number.  This is utilized for controlling the order of
updates in various objects where it matters.

Parameters
----------
tick: unsigned int
    Tick number to assign
path: str
    Path of target objects. Use a wildcard to select all
    elements on a subtree, or for selecting by condition.
fn: str
    Function (dest field) to be execeuted on tick

Examples
--------
In multi-compartmental neuron model a compartment's membrane potential (Vm)
is dependent on its neighbours' membrane potential. Thus it must get the
neighbour's present Vm before computing its own Vm in next time step.  This
ordering is achieved by scheduling the `init` function, which communicates
membrane potential, on tick 0 and `process` function on tick 1.

>>> moose.useClock(0, '/model/compartment_1', 'init')
>>> moose.useClock(1, '/model/compartment_1', 'process'));
)";

constexpr const char* copy = R"(Copy object to a new location.

Parameters
----------
orig: Id, ObjId or MooseVec or str
    Source object or path of source object
parent: Id, ObjId or MooseVec or str
    Existing object into which to copy
name: str
    Name of the new object. If empty, the name of the original
    object is used.
num: unsigned int
    Number of copies (default: 1)
toGlobal: bool
    Whether to make it a global element (default: False)
copyExtMsgs: bool
    Whether to copy the external messages (default: False)

Returns
-------
MooseVec
    Handle of the new copy
)";

constexpr const char* move = R"(Move object to a new location.

This function moves the entire subtree rooted at `orig`.

Parameters
----------
orig: Id, ObjId, MooseVec or str
    Source object or path of source object
parent: Id, ObjId or MooseVec or str
    Existing object into which to move (new parent)
)";

constexpr const char* doDelete =
    R"(Delete the underlying moose object(s). This does not delete any of the
Python objects referring to this vec but does invalidate them. Any
attempt to access them will raise a ValueError.

Parameters
----------
arg : vec/str/melement
    path of the object to be deleted.

Raises
-------
ValueError if given path/object does not exists.
)";

constexpr const char* reinit = R"((Re)initialize simulation.

Reinitializes simulation: time goes to zero, all scheduled
objects are set to initial conditions. If simulation is
already running, first stops it.

After setting up a simulation, you must call moose.reinit() before calling
moose.start(t) to execute the simulation. Otherwise, the simulator behaviour
will be undefined. Once moose.reinit() has been called, you can call
`moose.start(t)` as many time as you like. This will continue the
simulation from the last state for `t` time.

)";

constexpr const char* start = R"(Start simulation.

This function blocking, and returns only when the simulation is done.

Parameters
----------
runtime: float
    Run or continue the simulation for this duration
notify: bool
    Notify user whenever 10\% of simulation is over (default: false).
)";

constexpr const char* stop = R"(Stop simulation.

Cleanly stops simulation, ready to take up again from where
the stop occurred. Waits till current operations are done.
)";

constexpr const char* isRunning = "Returns flag to indicate whether simulation is still running";
constexpr const char* getDoc = "Get documentation as a formatted string";
}  // namespace pymoose::docs

/* docs.h ends here */
