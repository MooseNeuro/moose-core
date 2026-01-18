/***
 *    Description:  moose.vec class.
 *
 *        Created:  2020-03-30

 *         Author:  Dilawar Singh <dilawar.s.rajput@gmail.com>
 *        License:  GPLv3
 *        Maintainer: Subhasis Ray
 *        Updated: 2025-12-30
 */

#pragma once

#include "../basecode/header.h"

#include "pymoose.h"

using namespace std;

namespace pymoose{
class MooseVec
{

public:
    /// Create a MooseVec from path. If path does not exist and dtype
    /// is a valid moose class name, then create the object. Otherwise
    /// python wrapper should raise an error
    MooseVec(const string& path, unsigned int n=1, const string& dtype="");
    MooseVec(const Id& id);
    MooseVec(const ObjId& oid);

    ObjId oid() const;
    const string dtype() const;
    size_t size() const;
    vector<MooseVec> children() const;
    const string path() const;
    const string name() const;
    ObjId parent() const;
    size_t len() const;

    const ObjId& getItemRef(const int i) const;

    // Indexing
    /// Get vector element. Vector element could be `dataIndex` or `fieldIndex`.
    /// Allows negative indexing.
    ObjId getItem(int index) const;
    vector<ObjId> getItemRange(const nb::slice& slice) const;
    ObjId getDataItem(size_t i) const;
    ObjId getFieldItem(size_t i) const;

    // Attribute access
    nb::object getAttribute(const string& key);
    bool setAttribute(const string& name, const nb::object& val);

    // Template methods
    template <typename T>
    nb::ndarray<T, nb::numpy> getAttributeNumpy(const string& name)
    {
        size_t nn = size();
        T* data = new T[nn];
        for(size_t ii = 0; ii < nn; ++ii) {
            data[ii] = Field<T>::get(getItem(ii), name);
        }
        nb::capsule owner(data, [](void* p) noexcept {
            delete[] static_cast<T*>(p);
        });
        return nb::ndarray<T, nb::numpy>(data, {nn}, owner);
    }

    template <typename T>
    bool setAttrOneToAll(const string& name, const T& val)
    {
        auto cinfo = oid_.element()->cinfo();
        auto finfo = cinfo->findFinfo(name);
        if(!finfo) {
            throw nb::attribute_error((name + " not found").c_str());
        }
        bool res = true;
        for (size_t i = 0; i < size(); i++)
        {
                res &= Field<T>::set(getItem(i), name, val);
        }
        return res;
    }

    template <typename T>
    bool setAttrOneToOne(const string& name, const vector<T>& val)
    {
        auto cinfo = oid_.element()->cinfo();
        auto finfo = cinfo->findFinfo(name);
        if(!finfo) {
            throw nb::attribute_error((name + " not found").c_str());
        }
        if (val.size() != size()) {
            throw nb::value_error(("Length mismatch: expected " +
                to_string(size()) + ", got " +
                    to_string(val.size())).c_str());
        }

          bool res = true;
          for (size_t i = 0; i < size(); i++) {
              res &= Field<T>::set(getItem(i), name, val[i]);
          }
          return res;
    }

    const vector<ObjId>& elements();

    ObjId connectToSingle(const string& srcfield, const ObjId& tgt,
                          const string& tgtfield, const string& msgtype);

    ObjId connectToVec(const string& srcfield, const MooseVec& tgt,
                       const string& tgtfield, const string& msgtype);

    size_t id() const;

private:
    // It may seem obvious to store an Id rather than ObjId here. That
    // does not work because of the dichotomy of array elements and
    // field elements. For an Id with multiple data elements, underlying field
    // elements share the Id.
    //
    // For example, SimpleSynHandler with path '/synh', Id=490, numData=2, has
    // two data elements:
    //
    // "/synh[0]", ObjId(id=490, dataIndex=0, fieldIndex=0)
    // "/synh[1]", ObjId(id=490, dataIndex=1, fieldIndex=0)
    //
    // Also, "/synh" as a whole has a field element "synapse":
    // path="/synh/synapse" (Id=491, numFields=0).
    //
    //  Each item in /synh appears to have a separate synapse field,
    //  but they share the id.
    //
    // path="/synh[0]/synapse" ObjId(id=491, dataIndex=0, fieldIndex=0)
    // path="/synh[1]/synapse" ObjId(id=491, dataIndex=1, fieldIndex=0)
    //
    // After setting numField, individual elements inside have changing fieldIndex:
    //
    // path="/synh[0]/synapse[0]" ObjId(id=491, dataIndex=0, fieldIndex=0)
    // path="/synh[0]/synapse[1]" ObjId(id=491, dataIndex=0, fieldIndex=1)
    //
    // path="/synh[1]/synapse[0]" ObjId(id=491, dataIndex=1, fieldIndex=0)
    // path="/synh[1]/synapse[1]" ObjId(id=491, dataIndex=1, fieldIndex=1)
    ObjId oid_;
    vector<ObjId> elements_{};
};

// Simple iterator class
struct MooseVecIterator {
    MooseVec vec;
    size_t index;
    MooseVecIterator(MooseVec& v) : vec(v), index(0) {}

    ObjId next() {
        if (index >= vec.size()) {
            throw nb::stop_iteration();
        }
          return vec.getItem(index++);
    }
};
}
