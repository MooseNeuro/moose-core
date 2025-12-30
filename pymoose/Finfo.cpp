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
#define LOOKUP_SET(K, V)                                        \
    if ((keyType_ == #K) && (valueType_ == #V)) {                \
        return ::LookupField<K, V>::set(oid_, finfo_->name(),   \
            nb::cast<K>(key), nb::cast<V>(value));              \
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
    LOOKUP_SET(double, double)
    LOOKUP_SET(ObjId, ObjId)
    LOOKUP_SET(ObjId, int)
// Used in Stoich::proxyPools
    LOOKUP_SET(Id, vector<Id>)
// Used in Interpol2D
    LOOKUP_SET(vector<double>, double)
    LOOKUP_SET(vector<unsigned int>, double)
#undef LOOKUP_SET

// throw nb::type_error(("Unsupported LookupField type: " + keyType_ + "," + valType_).c_str());
}


// -----------------------------------------------------------------
// ElementField
// -----------------------------------------------------------------
ElementField::ElementField(const ObjId& oid, const Finfo* f)
    : oid_(oid), finfo_(f), foid_(ObjId(oid.path() + "/" + f->name())),
          vec_(MooseVec(foid_)){
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
    return vec_.getAttribute(field);
}

bool ElementField::setAttribute(const string& field, nb::object value)
{
    return vec_.setAttribute(field, value);
}

ObjId ElementFieldIterator::next()
{
    if(index_ >= size_) {
        throw nb::stop_iteration();
    }
    return ObjId(fieldOid_.id, fieldOid_.dataIndex, index_++);
}

}  // namespace pymoose
