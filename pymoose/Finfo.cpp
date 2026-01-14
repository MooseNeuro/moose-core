// =====================================================================================
//
//       Filename:  Finfo.cpp
//
//    Description:
//
//         Author:  Dilawar Singh (), dilawar.s.rajput@gmail.com
//   Organization:  NCBS Bangalore
//
// =====================================================================================

#include "../basecode/header.h"
#include "../builtins/Variable.h"
#include "../utility/print_function.hpp"
#include "../utility/strutil.h"

#include "pymoose.h"
#include "Finfo.h"

using namespace std;

namespace pymoose {

// Use a dispatch table instead of if-else chains for LookupValue fields
template <typename KeyT>
using LookupGetter =
    std::function<nb::object(const ObjId&, const string&, const KeyT&)>;

static const std::map<std::string, LookupGetter<string>> stringKeyGetters = {
    {"bool",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<string, bool>::get(oid, fname, key));
     }},
    {"double",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<string, double>::get(oid, fname, key));
     }},
    {"int",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<string, int>::get(oid, fname, key));
     }},
    {"unsigned int",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<string, unsigned int>::get(oid, fname, key));
     }},
    {"long",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<string, long>::get(oid, fname, key));
     }},
    {"string",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<string, string>::get(oid, fname, key));
     }},
    {"vector<double>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<string, vector<double>>::get(oid, fname, key));
     }},
    {"vector<int>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<string, vector<int>>::get(oid, fname, key));
     }},
    {"vector<unsigned int>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<string, vector<unsigned int>>::get(oid, fname, key));
     }},
    {"vector<string>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<string, vector<string>>::get(oid, fname, key));
     }},
    {"vector<Id>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<string, vector<Id>>::get(oid, fname, key));
     }},
    {"vector<ObjId>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<string, vector<ObjId>>::get(oid, fname, key));
     }},

};

static const std::map<std::string, LookupGetter<int>> intKeyGetters = {
    {"double",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<int, double>::get(oid, fname, key));
     }},
    {"int",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<int, int>::get(oid, fname, key));
     }},
    {"unsigned int",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<int, unsigned int>::get(oid, fname, key));
     }},
    {"long",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<int, long>::get(oid, fname, key));
     }},
    {"string",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<int, string>::get(oid, fname, key));
     }},
    {"vector<double>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<int, vector<double>>::get(oid, fname, key));
     }},
    {"vector<int>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<int, vector<int>>::get(oid, fname, key));
     }},
    {"vector<unsigned int>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<int, vector<unsigned int>>::get(oid, fname, key));
     }},
    {"vector<string>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<int, vector<string>>::get(oid, fname, key));
     }},
};

static const std::map<std::string, LookupGetter<long>> longKeyGetters = {
    {"double",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<long, double>::get(oid, fname, key));
     }},
    {"int",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<long, int>::get(oid, fname, key));
     }},
    {"unsigned int",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<long, unsigned int>::get(oid, fname, key));
     }},
    {"long",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<long, long>::get(oid, fname, key));
     }},
    {"string",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(::LookupField<long, string>::get(oid, fname, key));
     }},
    {"vector<double>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<long, vector<double>>::get(oid, fname, key));
     }},
    {"vector<int>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<long, vector<int>>::get(oid, fname, key));
     }},
    {"vector<unsigned int>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<long, vector<unsigned int>>::get(oid, fname, key));
     }},
    {"vector<string>",
     [](auto& oid, auto& fname, auto& key) {
         return nb::cast(
             ::LookupField<long, vector<string>>::get(oid, fname, key));
     }},

};
static const std::map<std::string, LookupGetter<unsigned int>> uintKeyGetters =
    {
        {"double",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(
                 ::LookupField<unsigned int, double>::get(oid, fname, key));
         }},
        {"int",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(
                 ::LookupField<unsigned int, int>::get(oid, fname, key));
         }},
        {"unsigned int",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(::LookupField<unsigned int, unsigned int>::get(
                 oid, fname, key));
         }},
        {"long",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(
                 ::LookupField<unsigned int, long>::get(oid, fname, key));
         }},
        {"string",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(
                 ::LookupField<unsigned int, string>::get(oid, fname, key));
         }},
        {"vector<double>",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(::LookupField<unsigned int, vector<double>>::get(
                 oid, fname, key));
         }},
        {"vector<int>",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(::LookupField<unsigned int, vector<int>>::get(
                 oid, fname, key));
         }},
        {"vector<unsigned int>",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(
                 ::LookupField<unsigned int, vector<unsigned int>>::get(
                     oid, fname, key));
         }},
        {"vector<string>",
         [](auto& oid, auto& fname, auto& key) {
             return nb::cast(::LookupField<unsigned int, vector<string>>::get(
                 oid, fname, key));
         }},

};

LookupField::LookupField(const ObjId& oid, const Finfo* f)
    : oid_(oid), finfo_(f)
{
    auto rttType = f->rttiType();
    vector<string> tokens;
    moose::tokenize(rttType, ",", tokens);
    if(tokens.size() != 2) {
        throw nb::type_error(
            ("Cannot handle LookupFinfo with type " + rttType).c_str());
    }
    keyType_ = tokens[0];
    valueType_ = tokens[1];
}

nb::object LookupField::get(const nb::object& key)
{
    if(keyType_ == "string") {
        auto it = stringKeyGetters.find(valueType_);
        if(it != stringKeyGetters.end()) {
            return it->second(oid_, finfo_->name(), nb::cast<string>(key));
        }
    }
    else if(keyType_ == "int") {
        auto it = intKeyGetters.find(valueType_);
        if(it != intKeyGetters.end()) {
            return it->second(oid_, finfo_->name(), nb::cast<int>(key));
        }
    }
    if(keyType_ == "unsigned int") {
        auto it = uintKeyGetters.find(valueType_);
        if(it != uintKeyGetters.end()) {
            return it->second(oid_, finfo_->name(),
                              nb::cast<unsigned int>(key));
        }
    }
    else if(keyType_ == "long") {
        auto it = longKeyGetters.find(valueType_);
        if(it != longKeyGetters.end()) {
            return it->second(oid_, finfo_->name(), nb::cast<long>(key));
        }
    }

    throw nb::type_error(
        ("Unsupported lookup type: " + finfo_->rttiType()).c_str());
}

bool LookupField::set(const nb::object& key, const nb::object& value)
{
    // Subha: feeling lazy - will go with macro
#define LOOKUP_SET(K, V)                                                       \
    if((keyType_ == #K) && (valueType_ == #V)) {                               \
        return ::LookupField<K, V>::set(oid_, finfo_->name(),                  \
                                        nb::cast<K>(key), nb::cast<V>(value)); \
    }

    LOOKUP_SET(unsigned int, double)
    LOOKUP_SET(unsigned int, unsigned int)
    LOOKUP_SET(unsigned int, vector<double>)
    LOOKUP_SET(unsigned int, vector<unsigned int>)
    LOOKUP_SET(string, bool)
    LOOKUP_SET(string, unsigned int)
    LOOKUP_SET(string, double)
    LOOKUP_SET(string, long)
    LOOKUP_SET(string, string)
    LOOKUP_SET(string, vector<double>)
    LOOKUP_SET(string, vector<long>)
    LOOKUP_SET(string, vector<string>)
    LOOKUP_SET(ObjId, ObjId)
    LOOKUP_SET(ObjId, int)
    // Used in Stoich::proxyPools
    LOOKUP_SET(Id, vector<Id>)
    // Used in Interpol2D
    LOOKUP_SET(vector<double>, double)
    LOOKUP_SET(vector<unsigned int>, double)
#undef LOOKUP_SET

    throw nb::type_error(
        ("Unsupported LookupField type: " + keyType_ + "," + valueType_)
            .c_str());
}

// -----------------------------------------------------------------
// ElementField
// -----------------------------------------------------------------
ElementField::ElementField(const ObjId& oid, const Finfo* f)
    : oid_(oid),
      finfo_(f),
      foid_(ObjId(oid.path() + "/" + f->name())),
      vec_(MooseVec(foid_))
{
}

unsigned int ElementField::getNum() const
{
    return Field<unsigned int>::get(foid_, "numField");
}

bool ElementField::setNum(unsigned int n)
{
    return Field<unsigned int>::set(foid_, "numField", n);
}

size_t ElementField::size() const
{
    return static_cast<size_t>(getNum());
}

ObjId ElementField::getItem(int index) const
{
    unsigned int numFields = getNum();
    size_t ii = (index < 0) ? numFields + index : static_cast<size_t>(index);

    // Bounds check
    if(ii >= numFields) {
        throw nb::index_error(
            ("Index " + std::to_string(index) +
             " out of range (size=" + std::to_string(numFields) + ")")
                .c_str());
    }

    // Return ObjId with fieldIndex set
    return ObjId(foid_.id, foid_.dataIndex, ii);
}

ElementFieldIterator ElementField::iter() const
{
    return ElementFieldIterator(foid_, size());
}

nb::object ElementField::getAttribute(const string& field)
{
    unsigned int num = getNum();
    if((field == "num") || (field == "numField")) {
        return nb::cast(num);
    }
    if(num > 0) {
        return vec_.getAttribute(field);
    }
    throw nb::index_error(
        "Trying to access attribute of an ElementField with 0 elements");
}

bool ElementField::setAttribute(const string& field, nb::object value)
{
    unsigned int num = getNum();
    if((field == "num") || (field == "numField")) {
        return setNum(nb::cast<unsigned int>(value));
    }
    if(num > 0) {
        return vec_.setAttribute(field, value);
    }
    throw nb::index_error(
        "Trying to access attribute of an ElementField with 0 elements");
}

ObjId ElementFieldIterator::next()
{
    if(index_ >= size_) {
        throw nb::stop_iteration();
    }
    return ObjId(fieldOid_.id, fieldOid_.dataIndex, index_++);
}

VecLookupField::VecLookupField(const Id& id, const Finfo* f)
    : id_(id), finfo_(f)
{
    auto rttType = f->rttiType();
    vector<string> tokens;
    moose::tokenize(rttType, ",", tokens);
    if(tokens.size() != 2) {
        throw nb::type_error(
            ("Cannot handle LookupFinfo with type " + rttType).c_str());
    }
    keyType_ = tokens[0];
    valueType_ = tokens[1];
}

nb::object VecLookupField::get(const nb::object& key)
{
    size_t numData = id_.element()->numData();
    // Macro for simple value types that can be returned as numpy
#define VEC_LOOKUP_GET_NUMPY(KT, VT)                                         \
    if(keyType_ == #KT && valueType_ == #VT) {                               \
        auto typedKey = nb::cast<KT>(key);                                   \
        VT* data = new VT[numData];                                          \
        for(size_t ii = 0; ii < numData; ++ii) {                             \
            ObjId oid(id_, ii);                                              \
            data[ii] =                                                       \
                ::LookupField<KT, VT>::get(oid, finfo_->name(), typedKey);   \
        }                                                                    \
        nb::capsule owner(                                                   \
            data, [](void* p) noexcept { delete[] static_cast<VT*>(p); });   \
        return nb::cast(nb::ndarray<VT, nb::numpy>(data, {numData}, owner)); \
    }

    // Macro for complex value types that return a list
#define VEC_LOOKUP_GET_LIST(KT, VT)                                          \
    if(keyType_ == #KT && valueType_ == #VT) {                               \
        auto typedKey = nb::cast<KT>(key);                                   \
        nb::list result;                                                     \
        for(size_t ii = 0; ii < numData; ++ii) {                             \
            ObjId oid(id_, ii);                                              \
            result.append(nb::cast(                                          \
                ::LookupField<KT, VT>::get(oid, finfo_->name(), typedKey))); \
        }                                                                    \
        return result;                                                       \
    }

    // String key with numeric values -> numpy
    VEC_LOOKUP_GET_NUMPY(string, double)
    VEC_LOOKUP_GET_NUMPY(string, int)
    VEC_LOOKUP_GET_NUMPY(string, unsigned int)
    VEC_LOOKUP_GET_NUMPY(string, long)
    VEC_LOOKUP_GET_NUMPY(string, bool)

    // String key with complex values -> list
    VEC_LOOKUP_GET_LIST(string, string)
    VEC_LOOKUP_GET_LIST(string, vector<double>)
    VEC_LOOKUP_GET_LIST(string, vector<int>)
    VEC_LOOKUP_GET_LIST(string, vector<string>)

    // Int key
    VEC_LOOKUP_GET_NUMPY(int, double)
    VEC_LOOKUP_GET_NUMPY(int, int)
    VEC_LOOKUP_GET_NUMPY(int, unsigned int)
    VEC_LOOKUP_GET_NUMPY(int, long)
    VEC_LOOKUP_GET_LIST(int, string)
    VEC_LOOKUP_GET_LIST(int, vector<double>)

    // Unsigned int key
    VEC_LOOKUP_GET_NUMPY(unsigned int, double)
    VEC_LOOKUP_GET_NUMPY(unsigned int, int)
    VEC_LOOKUP_GET_NUMPY(unsigned int, unsigned int)
    VEC_LOOKUP_GET_NUMPY(unsigned int, long)
    VEC_LOOKUP_GET_LIST(unsigned int, string)
    VEC_LOOKUP_GET_LIST(unsigned int, vector<double>)

    // Long key
    VEC_LOOKUP_GET_NUMPY(long, double)
    VEC_LOOKUP_GET_NUMPY(long, int)
    VEC_LOOKUP_GET_NUMPY(long, unsigned int)
    VEC_LOOKUP_GET_NUMPY(long, long)

#undef VEC_LOOKUP_GET_NUMPY
#undef VEC_LOOKUP_GET_LIST

    throw nb::type_error(
        ("Unsupported VecLookupField type: " + keyType_ + "," + valueType_)
            .c_str());
}

bool VecLookupField::set(const nb::object& key, const nb::object& val)
{
    size_t numData = id_.element()->numData();
    bool isIterable =
        nb::isinstance<nb::iterable>(val) && !nb::isinstance<nb::str>(val);

    // Macro for broadcasting single value to all elements

#define VEC_LOOKUP_SET(KT, VT)                                           \
    if(keyType_ == #KT && valueType_ == #VT) {                           \
        auto typedKey = nb::cast<KT>(key);                               \
        if(isIterable) {                                                 \
            auto vals = nb::cast<vector<VT>>(val);                       \
            if(vals.size() != numData) {                                 \
                throw nb::value_error(("Length mismatch: expected " +    \
                                       to_string(numData) + ", got " +   \
                                       to_string(vals.size()))           \
                                          .c_str());                     \
            }                                                            \
            bool res = true;                                             \
            for(size_t ii = 0; ii < numData; ++ii) {                     \
                res &= ::LookupField<KT, VT>::set(                       \
                    ObjId(id_, ii), finfo_->name(), typedKey, vals[ii]); \
            }                                                            \
            return res;                                                  \
        }                                                                \
        else {                                                           \
            auto typedVal = nb::cast<VT>(val);                           \
            bool res = true;                                             \
            for(size_t ii = 0; ii < numData; ++ii) {                     \
                res &= ::LookupField<KT, VT>::set(                       \
                    ObjId(id_, ii), finfo_->name(), typedKey, typedVal); \
            }                                                            \
            return res;                                                  \
        }                                                                \
    }

    VEC_LOOKUP_SET(unsigned int, double)
    VEC_LOOKUP_SET(unsigned int, unsigned int)
    VEC_LOOKUP_SET(unsigned int, vector<double>)
    VEC_LOOKUP_SET(unsigned int, vector<unsigned int>)
    VEC_LOOKUP_SET(string, bool)
    VEC_LOOKUP_SET(string, unsigned int)
    VEC_LOOKUP_SET(string, double)
    VEC_LOOKUP_SET(string, long)
    VEC_LOOKUP_SET(string, string)
    VEC_LOOKUP_SET(string, vector<double>)
    VEC_LOOKUP_SET(string, vector<long>)
    VEC_LOOKUP_SET(string, vector<string>)
    VEC_LOOKUP_SET(ObjId, ObjId)
    VEC_LOOKUP_SET(ObjId, int)
    VEC_LOOKUP_SET(vector<double>, double)
    VEC_LOOKUP_SET(vector<unsigned int>, double)

#undef VEC_LOOKUP_SET

    throw nb::type_error(("Unsupported VecLookupField set type: " + keyType_ +
                          "," + valueType_ + ". Try looping through elements.")
                             .c_str());
}

VecElementField::VecElementField(const Id& id, const Finfo* f)
    : parentId_(id), finfo_(f), numParents_(id.element()->numData())
{
}

size_t VecElementField::size() const
{
    size_t total = 0;
    for(size_t i = 0; i < numParents_; ++i) {
        ObjId parentOid(parentId_, i);
        string path = parentOid.path() + "/" + finfo_->name();
        ObjId fieldOid(path);
        total += Field<unsigned int>::get(fieldOid, "numField");
    }
    return total;
}

nb::ndarray<unsigned int, nb::numpy> VecElementField::sizes() const
{
    unsigned int* data = new unsigned int[numParents_];
    for(size_t i = 0; i < numParents_; ++i) {
        ObjId parentOid(parentId_, i);
        ObjId fieldOid(parentOid.path() + "/" + finfo_->name());
        data[i] = Field<unsigned int>::get(fieldOid, "numField");
    }
    nb::capsule owner(
        data, [](void* p) noexcept { delete[] static_cast<unsigned int*>(p); });
    return nb::ndarray<unsigned int, nb::numpy>(data, {numParents_}, owner);
}

ElementField VecElementField::getParent(int index) const
{
    size_t idx = (index < 0) ? numParents_ + index : static_cast<size_t>(index);
    if(idx >= numParents_) {
        throw nb::index_error("Index out of range");
    }
    ObjId parentOid(parentId_, idx);
    return ElementField(parentOid, finfo_);
}

nb::object VecElementField::getAttribute(const string& name)
{
    // numField is common to the entire ElementField - return numpy ndarray
    if((name == "numField") || name == "num") {
        return nb::cast(sizes());
    }

    // Other attributes are specific to each entry in the ElementField
    // - return a list of lists
    nb::list result;
    for(size_t p = 0; p < numParents_; ++p) {
        ObjId parentOid(parentId_, p);
        ObjId fieldOid(parentOid.path() + "/" + finfo_->name());
        unsigned int num = Field<unsigned int>::get(fieldOid, "numField");
        nb::list innerList;  // Create inner list for this parent
        for(unsigned int f = 0; f < num; ++f) {
            ObjId elemOid(fieldOid.id, fieldOid.dataIndex, f);
            innerList.append(getFieldGeneric(elemOid, name));
        }
        result.append(innerList);  // Append inner list to outer list
    }
    return result;
}

bool VecElementField::setAttribute(const string& name, const nb::object& val)
{
    bool isSequence =
        nb::isinstance<nb::sequence>(val) && !nb::isinstance<nb::str>(val);

    nb::sequence seq;
    if(isSequence) {
        seq = nb::cast<nb::sequence>(val);
        if(nb::len(seq) != numParents_) {
            throw nb::value_error("Length must match numData of parent vec");
        }
    }

    bool res = true;

    // num is a special field setting the number of elements in an
    // ElementField
    if((name == "num") || (name == "numField")) {
        if(isSequence) {
            for(size_t i = 0; i < numParents_; ++i) {
                ObjId parentOid(parentId_, i);
                ObjId fieldOid(parentOid.path() + "/" + finfo_->name());
                res &= Field<unsigned int>::set(fieldOid, "numField",
                                                nb::cast<unsigned int>(seq[i]));
            }
        }
        else {
            unsigned int numField = nb::cast<unsigned int>(val);
            for(size_t i = 0; i < numParents_; ++i) {
                ObjId parentOid(parentId_, i);
                ObjId fieldOid(parentOid.path() + "/" + finfo_->name());
                res &= Field<unsigned int>::set(fieldOid, "numField", numField);
            }
        }
        return res;
    }
    // All other fields::
    // Scalar value - broadcast
    if(!isSequence) {
        for(size_t i = 0; i < numParents_; ++i) {
            ObjId parentOid(parentId_, i);
            ObjId fieldOid(parentOid.path() + "/" + finfo_->name());
            unsigned int num = Field<unsigned int>::get(fieldOid, "numField");
            for(unsigned int f = 0; f < num; ++f) {
                ObjId elemOid(fieldOid.id, fieldOid.dataIndex, f);
                res &= setFieldGeneric(elemOid, name, nb::borrow(val));
            }
        }
        return res;
    }
    // isSequence::
    // Process inner lists if sequence
    for(size_t p = 0; p < numParents_; ++p) {
        ObjId parentOid(parentId_, p);
        ObjId fieldOid(parentOid.path() + "/" + finfo_->name());
        unsigned int num = Field<unsigned int>::get(fieldOid, "numField");

        if (nb::isinstance<nb::sequence>(seq[p]) && !nb::isinstance<nb::str>(seq[p])){
            nb::sequence inner = nb::cast<nb::sequence>(seq[p]);
            if(nb::len(inner) != num) {
                throw nb::value_error(("Inner sequence " + to_string(p) +
                        " length mismatch: expected " +
                        to_string(num) + ", got " +
                        to_string(nb::len(inner)))
                    .c_str());
            }
            for(unsigned int f = 0; f < num; ++f) {
                ObjId elemOid(fieldOid.id, fieldOid.dataIndex, f);
                res &= setFieldGeneric(elemOid, name, nb::borrow(inner[f]));
            }
        } else { // broadcast scalar across parent's elements
            for(unsigned int f = 0; f < num; ++f) {
                ObjId elemOid(fieldOid.id, fieldOid.dataIndex, f);
                res &= setFieldGeneric(elemOid, name, nb::borrow(seq[p]));
            }
        }
    }
    return res;
} // VecElementField::setAttribute

}  // namespace pymoose
