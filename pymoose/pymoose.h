/* pymoose.h ---
 *
 * Filename: pymoose.h
 * Description:
 * Author: Subhasis Ray
 * Created: Fri Dec 26 14:44:06 2025 (+0530)
 */

/* Code: */

#pragma once
#include <string>
#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>  // std::vector <-> list
#include <nanobind/stl/map.h>     // std::map <-> dict
#include <nanobind/ndarray.h>

#include "../basecode/header.h"
#include "../basecode/Id.h"
#include "../shell/Shell.h"

namespace nb = nanobind;

namespace pymoose {

enum class MsgDirection { Out = 0, In = 1, Both = 2 };

class MooseVec;

///   Shorthand to access shell pointer
inline Shell* getShellPtr(void)
{
    return reinterpret_cast<Shell*>(Id().eref().data());
}

///   Initialize shell object.
Id initShell();

/// Convert Python object wrapping path or ObjId or Id into ObjId
ObjId convertToObjId(const nb::object& arg);

///   Get a map of field names to Finfo*
map<std::string, Finfo*> getFinfoDict(const Cinfo* cinfo,
                                      const std::string& fieldType);
vector<string> getFieldNames(const string& className, const string& fieldType);
map<string, string> getFieldTypeDict(const string& className,
                                     const string& fieldType);

// --------------------------------------
// Documentation related functions
// --------------------------------------

///   Get the class fields documentation
std::string getClassFieldsDoc(const Cinfo* cinfo, const std::string& ftype,
                              const std::string& prefix);
std::string getClassDoc(const std::string& className);
std::string getClassAttributeDoc(const Cinfo* cinfo, const std::string& fname);
std::string getDoc(const std::string& query);

// --------------------------------------
// Field access related functions
// --------------------------------------

///   Common function to get value fiields.
nb::object getFieldValue(const ObjId& oid, const Finfo* f);
bool setFieldGeneric(const ObjId& oid, const std::string& fieldName,
                     const nb::object& val);
nb::object getFieldValue(const ObjId& oid, const Finfo* f);
nb::object getFieldGeneric(const ObjId& oid, const std::string& fieldName);

// ----------------------------------------------------------------------
// Functions for construction and destruction of objects
// ----------------------------------------------------------------------

/// Create a new vector of class `type` at path `p`, with `numdata` elements
ObjId createElementFromPath(const string& type, const string& p,
                            unsigned int numdata);
bool doDelete(nb::object& obj);

// ----------------------------------------------------------------------
// Other utility functions available in python
// ----------------------------------------------------------------------

/// Get current working element
nb::object getCwe();

/// Set current working element (ce)
void setCwe(const nb::object& arg);

/// Show elements (le)
void listElements(const nb::object& arg);

/// Get a list of Msg objects
vector<ObjId> listMsg(const nb::object& arg,
                      MsgDirection direction = MsgDirection::Both);
/// Show messages (showmsg)
void showMsg(const nb::object& arg,
             MsgDirection direction = MsgDirection::Both);

/// Get neighbors of obj connected on `fieldName`, of type `msgType`,
/// in direction `direction`.
vector<ObjId> getNeighbors(const nb::object& obj, const string& fieldName,
                           const string& msgType, MsgDirection direction);

/// Connect to another ObjId
ObjId connect(const ObjId& src, const string& srcField, const ObjId& tgt,
              const string& tgtField, const string& msgType);

/// Connect to a vec object
ObjId connectToVec(const ObjId& src, const string& srcField,
                   const MooseVec& tgt, const string& tgtField,
                   const string& msgType);

/// Copy object, return the copied vec object
MooseVec copy(const nb::object& elem, const nb::object& newParent,
              const string& newName = "", unsigned int n = 1,
              bool toGlobal = false, bool copyExtMsgs = false);

/// Move object, return None
void move(const nb::object& elem, const nb::object& newParent);

/// Model loaders built into Shell, others can be implemented in Python
ObjId loadModelInternal(const string& fname, const string& modelpath,
                        const string& solverclass = "");

// -------------------------------
// Simulation control
// -------------------------------
    void setClock(const unsigned int clockId, double dt);
void useClock(size_t tick, const string& path, const string& fn);
void start(double runtime, bool notify = false);

map<string, string> getVersionInfo();

}  // namespace pymoose

/* pymoose.h ends here */
