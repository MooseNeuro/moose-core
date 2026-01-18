/* Finfo.h ---
 *
 * Filename: Finfo.h
 * Description:
 * Author: Dilawar Singh <dilawar.s.rajput@gmail.com>
 * Created: 2020-03-30
 * Mainainer: Subhasis Ray
 * Updated: 2025-12-29
 */

/* Code: */

#include <string>
#include <nanobind/nanobind.h>

#include "../basecode/header.h"
#include "../builtins/Variable.h"
#include "../msg/OneToOneMsg.h"
#include "../msg/OneToAllMsg.h"
#include "../msg/SingleMsg.h"
#include "../msg/SparseMsg.h"
#include "../msg/DiagonalMsg.h"

#include "../mpi/PostMaster.h"
#include "../scheduling/Clock.h"
#include "../shell/Shell.h"
#include "../utility/strutil.h"

#include "MooseVec.h"

namespace nb = nanobind;
using namespace std;

namespace pymoose {
/// For LookupValueFinfo - dict-like access
struct LookupField {
    ObjId oid_;
    const Finfo* finfo_;
    string keyType_;
    string valueType_;
    LookupField(const ObjId& oid, const Finfo* f);
    nb::object get(const nb::object& key);
    bool set(const nb::object& key, const nb::object& val);
};

/// Iterator class for ElementField
struct ElementFieldIterator {
    ObjId fieldOid_;
    size_t index_;
    size_t size_;

    ElementFieldIterator(const ObjId& fieldOid, size_t size)
        : fieldOid_(fieldOid), index_(0), size_(size)
    {
    }
    ObjId next();
};

/// For FieldElementFinfo - vector of elements
struct ElementField {
    ObjId oid_;  /// Owner ObjId
    const Finfo* finfo_;
    ObjId foid_;    /// Finfo ObjId

    ElementField(const ObjId& oid, const Finfo* f);
    unsigned int getNum() const;
    bool setNum(unsigned int n);
    size_t size() const;
    ObjId getItem(int index) const;  // supports negative indexing
    ElementFieldIterator iter() const;
    nb::object getAttribute(const string& field);
    bool setAttribute(const string& field, nb::object value);
};

/// Modified LookupField to allow vectorized assignment and lookup
struct VecLookupField {
    Id id_;                 // Base Id of the vector
    const Finfo* finfo_;
    string keyType_;
    string valueType_;
    size_t numData_;        // Number of elements in the vec

    VecLookupField(const Id& id, const Finfo* f);
    nb::object get(const nb::object& key);
    bool set(const nb::object& key, const nb::object& val);
};


struct VecElementField {
    Id parentId_; // this should be id of the owner
    const Finfo* finfo_;
    size_t numParents_;
    VecElementField(const Id& id, const Finfo* f);

    // Total count across all parents
    size_t size() const;

    // Get sizes per parent as numpy array
    nb::ndarray<unsigned int, nb::numpy> sizes() const;

    // Get flat numpy array or list for an attribute across all sub-elements
    nb::object getAttribute(const string& name);

    // Set attribute - broadcasts or one-to-one
    bool setAttribute(const string& name, const nb::object& val);

    // Get the ElementField for a specific parent index
    ElementField getItem(int index) const;
};
}  // namespace pymoose

/* Finfo.h ends here */
