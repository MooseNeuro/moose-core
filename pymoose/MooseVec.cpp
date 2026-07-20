/***
 *    Description:  vec api.
 *
 *        Created:  2020-04-01

 *         Author:  Dilawar Singh <dilawar.s.rajput@gmail.com>
 *        License:  MIT License
 */

#include <iomanip>

#include "../basecode/header.h"
#include "../utility/strutil.h"
#include "pymoose.h"

#include "MooseVec.h"
#include "Finfo.h"

using namespace std;


namespace pymoose{

MooseVec::MooseVec(const string& path, unsigned int n, const string& dtype)
{
    // With a dtype, defer to createElementFromPath: it returns the existing
    // element when the path already holds one of the same type, throws when a
    // different type occupies the path, and creates a new one otherwise.
    if(!dtype.empty()) {
        oid_ = createElementFromPath(dtype, path, n);
        return;
    }
    // Without a dtype we can only wrap an element that already exists.
    oid_ = ObjId(path);
    if(oid_.bad()) {
        throw nb::value_error(
            (path +
                ": path does not exist. Pass `dtype=classname` to create.").c_str());
    }
}

MooseVec::MooseVec(const ObjId& oid) : oid_(oid)
{
}

MooseVec::MooseVec(const Id& id) : oid_(id)
{
}

const string MooseVec::dtype() const
{
    return oid_.element()->cinfo()->name();
}

size_t MooseVec::size() const
{
    if(oid_.element()->hasFields()){
        return Field<unsigned int>::get(oid_, "numField");
    }
    return oid_.element()->numData();
}

const string MooseVec::name() const
{
    return oid_.element()->getName();
}

const string MooseVec::path() const
{
    return oid_.path();
}

ObjId MooseVec::parent() const
{
    return Neutral::parent(oid_);
}

vector<MooseVec> MooseVec::children() const
{
    vector<Id> childIds;
    Neutral::children(oid_.eref(), childIds);
    vector<MooseVec> res;
    res.reserve(childIds.size());
    for(const auto& id : childIds) {
        res.emplace_back(id);
    }
    return res;
}

ObjId MooseVec::getItem(const int index) const
{
    // Handle negative indexing.
    size_t i = (index < 0) ? size() + index : static_cast<size_t>(index);
    if(i >= size()) {
        throw nb::index_error(("Index " + to_string(i) + " out of range").c_str());
    }
    if(oid_.element()->hasFields()) {
        return getFieldItem(i);
    }
    return getDataItem(i);
}

vector<ObjId> MooseVec::getItemRange(const nb::slice& slice) const
{
    auto [start, stop, step, length] = slice.compute(size());
    vector<ObjId> res;
    res.reserve(length);
    for(size_t ii = start; ii < stop; ii += step) {
        res.push_back(getItem(static_cast<int>(ii)));
    }
    return res;
}

ObjId MooseVec::getDataItem(const size_t dataIndex) const
{
    return ObjId(oid_.id, dataIndex, oid_.fieldIndex);
}

ObjId MooseVec::getFieldItem(const size_t fieldIndex) const
{
    return ObjId(oid_.id, oid_.dataIndex, fieldIndex);
}

nb::object MooseVec::getAttribute(const string& name)
{
    // Special id level attributes
    if(name == "numData") {
        return nb::cast(Field<unsigned int>::get(oid_, "numData"));
    }
    if(name == "numField") {
        return nb::cast(Field<unsigned int>::get(oid_, "numField"));
    }

    // If type is double, int, bool etc, then return the numpy array. else
    // return the list of python object.
    auto cinfo = oid_.element()->cinfo();
    auto finfo = cinfo->findFinfo(name);
    if (!finfo) {
        throw nb::attribute_error((name + " not found on " + path()).c_str());
    }

    auto rttType = finfo->rttiType();
    if(rttType == "double")
        return nb::cast(getAttributeNumpy<double>(name));
    if(rttType == "unsigned int")
        return nb::cast(getAttributeNumpy<unsigned int>(name));
    if(rttType == "int")
        return nb::cast(getAttributeNumpy<int>(name));
    if(rttType == "bool")
        return nb::cast(getAttributeNumpy<bool>(name));

    string finfoType = cinfo->getFinfoType(finfo);
    if(finfoType == "LookupValueFinfo") {
        return nb::cast(VecLookupField(oid_, finfo));
    }
    if(finfoType == "FieldElementFinfo") {
        return nb::cast(VecElementField(oid_, finfo));
    }
    cerr << "DEBUG: None of the simply handled types:  " << finfoType << endl;
    // For complex types, return list objects
    nb::list result;
    for(size_t ii = 0; ii < size(); ii++){
        result.append(getFieldGeneric(getItem(ii), name));
    }
    return result;
}

/* --------------------------------------------------------------------------*/
/**
 * @Synopsis  API function. Set attribute on vector. This is the top-level
 * generic function.
 *
 * @Param name
 * @Param val
 *
 * @Returns
 */
/* ----------------------------------------------------------------------------*/
bool MooseVec::setAttribute(const string& name, const nb::object& val)
{
    auto cinfo = oid_.element()->cinfo();
    auto finfo = cinfo->findFinfo(name);
    if (!finfo) {
        throw nb::attribute_error((name + " not found on " + path()).c_str());
    }

    auto rttType = finfo->rttiType();

    bool isIterable = nb::isinstance<nb::iterable>(val) && !nb::isinstance<nb::str>(val);

    if(isIterable) {
        if(rttType == "double")
            return setAttrOneToOne<double>(name, nb::cast<vector<double>>(val));
        if(rttType == "unsigned int")
            return setAttrOneToOne<unsigned int>(
                name, nb::cast<vector<unsigned int>>(val));
        if(rttType == "int")
            return setAttrOneToOne<int>(
                name, nb::cast<vector<int>>(val));
        if(rttType == "bool") {
            // Convert each element via Python truthiness (like `bool(x)`) so a
            // list of ints (0/1) works; nanobind's bool caster is strict and
            // only accepts True/False.
            vector<bool> bvec;
            for(auto item : val)
                bvec.push_back(nb::cast<bool>(nb::bool_(item)));
            return setAttrOneToOne<bool>(name, bvec);
        }
        if(rttType == "string")
            return setAttrOneToOne<string>(name, nb::cast<vector<string>>(val));
    }
    else {
        if(rttType == "double")
            return setAttrOneToAll<double>(name, nb::cast<double>(val));
        if(rttType == "unsigned int")
            return setAttrOneToAll<unsigned int>(name,
                nb::cast<unsigned int>(val));
        if(rttType == "int")
            return setAttrOneToAll< int>(name,
                nb::cast<int>(val));
        if(rttType == "bool")
            // Use Python truthiness so ints (0/1) and other objects convert
            // as expected; nanobind's bool caster only accepts True/False.
            return setAttrOneToAll<bool>(name, nb::cast<bool>(nb::bool_(val)));
          if (rttType == "string")
              return setAttrOneToAll<string>(name, nb::cast<string>(val));
    }

    throw nb::type_error(("Unsupported type: " + rttType).c_str());
}

ObjId MooseVec::connectToSingle(const string& srcfield, const ObjId& tgt,
                                const string& tgtfield, const string& msgtype)
{
    return connect(oid_, srcfield, tgt, tgtfield, msgtype);
}

ObjId MooseVec::connectToVec(const string& srcfield, const MooseVec& tgt,
                             const string& tgtfield, const string& msgtype)
{
    if(size() != tgt.size())
        throw nb::value_error(
            ("Length mismatch. " + to_string(size()) +
                " vs " + to_string(tgt.size())).c_str());
    return connect(oid_, srcfield, tgt.oid_, tgtfield, msgtype);
}

ObjId MooseVec::oid() const
{
    return oid_;
}

const vector<ObjId>& MooseVec::elements()
{
    if (elements_.empty()) {
        elements_.reserve(size());
        for (size_t ii = 0; ii < size(); ii++) {
            elements_.push_back(getItem(ii));
        }
    }
    return elements_;
}

size_t MooseVec::id() const
{
    return oid_.id.value();
}

}
