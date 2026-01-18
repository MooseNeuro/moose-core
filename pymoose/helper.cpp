// helper.cpp ---
//
// Filename: helper.cpp
// Description:
// Author: Subhasis Ray
// Created: Sat Dec 27 12:16:04 2025 (+0530)
//

// Code:

#include <string>
#include <set>
#include <csignal>
#include <ctime>

#include <nanobind/stl/string.h>

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

#include "pymoose.h"
#include "MooseVec.h"
#include "Finfo.h"

using namespace std;

namespace pymoose {

Id initShell()
{
    Cinfo::rebuildOpIndex();

    Id shellId;

    Element *shelle =
        new GlobalDataElement(shellId, Shell::initCinfo(), "/", 1);

    Id clockId = Id::nextId();
    assert(clockId.value() == 1);
    Id classMasterId = Id::nextId();
    Id postMasterId = Id::nextId();

    Shell *s = reinterpret_cast<Shell *>(shellId.eref().data());
    s->setHardware(1, 1, 0);
    s->setShellElement(shelle);

    /// Sets up the Elements that represent each class of Msg.
    auto numMsg = Msg::initMsgManagers();

    new GlobalDataElement(clockId, Clock::initCinfo(), "clock", 1);
    new GlobalDataElement(classMasterId, Neutral::initCinfo(), "classes", 1);
    new GlobalDataElement(postMasterId, PostMaster::initCinfo(), "postmaster",
                          1);

    assert(shellId == Id());
    assert(clockId == Id(1));
    assert(classMasterId == Id(2));
    assert(postMasterId == Id(3));

    Shell::adopt(shellId, clockId, numMsg++);
    Shell::adopt(shellId, classMasterId, numMsg++);
    Shell::adopt(shellId, postMasterId, numMsg++);
    assert(numMsg == 10);  // Must be the same on all nodes.

    Cinfo::makeCinfoElements(classMasterId);
    return shellId;
}

map<string, Finfo *> getFinfoDict(const Cinfo *cinfo, const string &fieldType)
{
    // All field types - available via Cinfo.finfoMap()
    if(fieldType == "*") {
        return cinfo->finfoMap();
    }
    map<string, Finfo *> ret;
    // Other cases - for each field type XYZ, Cinfo has
    // getNumXYZFinfo() to get the number of fields of that type,
    // and getXYZFinfo(n) to get the n-th field of that type.
    Finfo *(Cinfo::*finfoGetter)(unsigned int) const = nullptr;
    unsigned int numFinfo{0};
    if(fieldType == "valueFinfo" || fieldType == "value") {
        numFinfo = cinfo->getNumValueFinfo();
        finfoGetter = &Cinfo::getValueFinfo;
    }
    else if(fieldType == "srcFinfo" || fieldType == "src") {
        numFinfo = cinfo->getNumSrcFinfo();
        finfoGetter = &Cinfo::getSrcFinfo;
    }
    else if(fieldType == "destFinfo" || fieldType == "dest") {
        numFinfo = cinfo->getNumDestFinfo();
        finfoGetter = &Cinfo::getDestFinfo;
    }
    else if(fieldType == "lookupFinfo" || fieldType == "lookup") {
        numFinfo = cinfo->getNumLookupFinfo();
        finfoGetter = &Cinfo::getLookupFinfo;
    }
    else if(fieldType == "sharedFinfo" || fieldType == "shared") {
        numFinfo = cinfo->getNumSharedFinfo();
        finfoGetter = &Cinfo::getSharedFinfo;
    }
    else if(fieldType == "element" || fieldType == "elementFinfo" || fieldType == "field" ||
            fieldType == "fieldElement" || fieldType == "fieldElementFinfo") {
        numFinfo = cinfo->getNumFieldElementFinfo();
        finfoGetter = &Cinfo::getFieldElementFinfo;
    }
    if(!finfoGetter) {
        throw nb::value_error("Invalid field type");
    }
    for(unsigned int ii = 0; ii < numFinfo; ++ii) {
        Finfo *finfo = (cinfo->*finfoGetter)(ii);
        ret[finfo->name()] = finfo;
    }
    return ret;
}

vector<string> getFieldNames(const string &className, const string &fieldType)
{
    auto cinfo = Cinfo::find(className);
    if(!cinfo) {
        throw nb::key_error((className + ": no such class found").c_str());
    }
    auto finfoDict = getFinfoDict(cinfo, fieldType);
    vector<string> ret;
    ret.reserve(finfoDict.size());
    for(const auto &it : finfoDict) {
        ret.push_back(it.first);
    }
    return ret;
}

map<string, string> getFieldTypeDict(const string &className,
                                     const string &fieldType)
{
    auto cinfo = Cinfo::find(className);
    if(!cinfo) {
        throw nb::key_error((className + ": no such class found").c_str());
    }
    auto finfoDict = getFinfoDict(cinfo, fieldType);
    map<string, string> ret;
    for(const auto &it : finfoDict) {
        ret[it.first] = it.second->rttiType();
    }
    return ret;
}

string fieldDocFormatted(const string &name, const Cinfo *cinfo,
                         const Finfo *finfo, const string &prefix = "")
{
    return prefix + fmt::format("{0} (type: {1}, class: {3})\n{2}\n\n", name,
                                finfo->rttiType(),
                                moose::textwrap(finfo->docs(), prefix + "  "),
                                cinfo->name());
}

string getClassFieldsDoc(const Cinfo *cinfo, const string &ftype,
                         const string &prefix)
{
    stringstream ss;
    map<string, Finfo *> fmap = getFinfoDict(cinfo, ftype);
    if(fmap.size() == 0)
        return "\n";

    ss << moose::underlined<'-'>(moose::capitalize(ftype) + " Attributes:");

    for(auto v : fmap) {
        ss << fieldDocFormatted(v.first, cinfo, v.second, prefix);
    }

    // There are from base classes.
    const Cinfo *baseClassCinfo = cinfo->baseCinfo();
    while(baseClassCinfo) {
        ss << prefix << "Attributes inherited from " << baseClassCinfo->name()
           << ":\n";
        auto baseFmap = getFinfoDict(baseClassCinfo, ftype);
        for(const auto &vv : baseFmap) {
            if(fmap.find(vv.first) == fmap.end()) {
                fmap[vv.first] = vv.second;
                ss << fieldDocFormatted(vv.first, baseClassCinfo, vv.second,
                                        prefix);
            }
        }
        baseClassCinfo = baseClassCinfo->baseCinfo();
    }
    return ss.str();
}

string getClassDoc(const string &className)
{
    stringstream ss;

    auto cinfo = Cinfo::find(className);
    if(!cinfo) {
        ss << "This class is not valid." << endl;
        return ss.str();
    }
    ss << "class " << className << "\n\n"
       << cinfo->getDocsEntry("Description") << "\n\n"
       << "Author: " << moose::textwrap(cinfo->getDocsEntry("Author"), "  ")
       << "\n\n";
    ss << moose::underlined<'='>("Attributes:");
    ss << endl;

    for(string f : {"value", "lookup", "src", "dest", "shared", "field"})
        ss << getClassFieldsDoc(cinfo, f, "");

    return ss.str();
}

string getDoc(const string &query)
{
    auto getClassAttributeDoc = [](const Cinfo *cinfo,
                                   const string &fname) -> string {
        const Finfo *finfo = cinfo->findFinfo(fname);
        if(!finfo)
            return "Error: '" + fname + "' not found.";
        return fmt::format("{0}: {1} - {2}\n{3}", fname, finfo->rttiType(),
                           cinfo->getFinfoType(finfo), finfo->docs());
    };

    vector<string> tokens;
    moose::tokenize(query, ".", tokens);

    auto cinfo = Cinfo::find(tokens[0]);
    string msg = "Class '" + tokens[0] + "' is not a valid MOOSE class.";
    if(!cinfo)
        throw nb::key_error(msg.c_str());

    if(tokens.size() == 1)
        return getClassDoc(tokens[0]);

    if(tokens.size() == 2) {
        cout << "Query: " << tokens[1] << endl;
        return getClassAttributeDoc(cinfo, tokens[1]);
    }

    throw runtime_error(__func__ + string(":: Not supported '" + query + "'"));
}

bool setFieldGeneric(const ObjId &oid, const string &fieldName,
                     const nb::object &val)
{
    auto cinfo = oid.element()->cinfo();
    auto finfo = cinfo->findFinfo(fieldName);
    if(!finfo) {
        throw nb::attribute_error((__func__ + string("::") + fieldName +
                                   " is not found on path '" + oid.path() +
                                   "'.")
                                      .c_str());
        return false;
    }

    auto fieldType = finfo->rttiType();

    // Remove any space in fieldType
    fieldType.erase(
        std::remove_if(fieldType.begin(), fieldType.end(), ::isspace),
        fieldType.end());

    if(fieldType == "double") {
        return Field<double>::set(oid, fieldName, nb::cast<double>(val));
    }
    if(fieldType == "vector<double>")
        return Field<vector<double>>::set(oid, fieldName,
                                          nb::cast<vector<double>>(val));
    if(fieldType == "float")
        return Field<float>::set(oid, fieldName, nb::cast<float>(val));
    if(fieldType == "unsignedint")
        return Field<unsigned int>::set(oid, fieldName,
                                        nb::cast<unsigned int>(val));
    if(fieldType == "unsignedlong")
        return Field<unsigned long>::set(oid, fieldName,
                                         nb::cast<unsigned long>(val));
    if(fieldType == "int")
        return Field<int>::set(oid, fieldName, nb::cast<int>(val));
    if(fieldType == "bool")
        return Field<bool>::set(oid, fieldName, nb::cast<bool>(val));
    if(fieldType == "string")
        return Field<string>::set(oid, fieldName, nb::cast<string>(val));
    if(fieldType == "vector<string>")
        return Field<vector<string>>::set(oid, fieldName,
                                          nb::cast<vector<string>>(val));
    if(fieldType == "char")
        return Field<char>::set(oid, fieldName, nb::cast<char>(val));
    if(fieldType == "vector<ObjId>")
        return Field<vector<ObjId>>::set(oid, fieldName,
                                         nb::cast<vector<ObjId>>(val));
    if(fieldType == "ObjId")
        return Field<ObjId>::set(oid, fieldName, nb::cast<ObjId>(val));
    if (fieldType == "Id") {
      // NB: Handle MooseVec as well. Note that we send ObjId to the set
      // function. The C++ implicit conversion takes care of the rest.
      // Id tgt;
      if (nb::isinstance<MooseVec>(val)) {
          return Field<Id>::set(oid.id, fieldName, nb::cast<MooseVec>(val).id());
      } else if (nb::isinstance<ObjId>(val)) {
        return Field<Id>::set(oid.id, fieldName, nb::cast<ObjId>(val).id);
      } else if (nb::isinstance<Id>(val)) {
        return Field<Id>::set(oid.id, fieldName, nb::cast<Id>(val));
      }
    }
    if(fieldType == "vector<double>") {
        // NB: Note that we cast to ObjId here and not to Id.
        return Field<vector<double>>::set(oid.id, fieldName,
                                          nb::cast<vector<double>>(val));
    }
    if(fieldType == "vector<vector<double>>") {
        // NB: Note that we cast to ObjId here and not to Id.
        return Field<vector<vector<double>>>::set(
            oid.id, fieldName, nb::cast<vector<vector<double>>>(val));
    }
    if(fieldType == "Variable")
        if(fieldType == "Variable")
            return Field<Variable>::set(oid, fieldName,
                                        nb::cast<Variable>(val));

    throw runtime_error("NotImplemented::setField: '" + fieldName +
                        "' with value type '" + fieldType + "'.");
    return false;
}

nb::object getFieldValue(const ObjId &oid, const Finfo *f)
{
    auto rttType = f->rttiType();
    auto fname = f->name();
    nb::object r = nb::none();
    if(rttType == "double" || rttType == "float") {
        r = nb::float_(Field<double>::get(oid, fname));
    }
    else if(rttType == "vector<double>") {
        vector<double> val = Field<vector<double>>::get(oid, fname);
        // Must copy data - val goes out of scope!
        size_t size = val.size();

        // Allocate numpy array and copy data into it
        auto *data = new double[size];
        std::copy(val.begin(), val.end(), data);

        nb::capsule owner(
            data, [](void *p) noexcept { delete[] static_cast<double *>(p); });
        r = nb::cast(nb::ndarray<nb::numpy, double>(data, {size}, owner));
    }
    else if(rttType == "vector<unsigned int>") {
        vector<unsigned int> val = Field<vector<unsigned int>>::get(oid, fname);
        size_t size = val.size();

        auto *data = new unsigned int[size];
        std::copy(val.begin(), val.end(), data);

        nb::capsule owner(data, [](void *p) noexcept {
            delete[] static_cast<unsigned int *>(p);
        });

        r = nb::cast(nb::ndarray<nb::numpy, unsigned int>(data, {size}, owner));
    }
    else if(rttType == "vector<int>") {
        vector<int> val = Field<vector<int>>::get(oid, fname);
        size_t size = val.size();

        auto *data = new int[size];
        std::copy(val.begin(), val.end(), data);

        nb::capsule owner(
            data, [](void *p) noexcept { delete[] static_cast<int *>(p); });

        r = nb::cast(nb::ndarray<nb::numpy, int>(data, {size}, owner));
    }
    else if(rttType == "string")
        r = nb::cast(Field<string>::get(oid, fname));
    else if(rttType == "char")
        r = nb::int_(Field<char>::get(oid, fname));
    else if(rttType == "int")
        r = nb::int_(Field<int>::get(oid, fname));
    else if(rttType == "unsigned int")
        r = nb::int_(Field<unsigned int>::get(oid, fname));
    else if(rttType == "unsigned long")
        r = nb::int_(Field<unsigned long>::get(oid, fname));
    else if(rttType == "bool")
        r = nb::bool_(Field<bool>::get(oid, fname));
    else if(rttType == "Id")
        r = nb::cast(Field<Id>::get(oid, fname));
    else if(rttType == "ObjId")
        r = nb::cast(Field<ObjId>::get(oid, fname));
    else if(rttType == "Variable")
        r = nb::cast(Field<Variable>::get(oid, fname));
    else if(rttType == "vector<Id>")
        r = nb::cast(Field<vector<Id>>::get(oid, fname));
    else if(rttType == "vector<ObjId>")
        r = nb::cast(Field<vector<ObjId>>::get(oid, fname));
    else if(rttType == "vector<string>")
        r = nb::cast(Field<vector<string>>::get(oid, fname));
    else {
        cerr << "Warning: getValueFinfo:: Unsupported type '" + rttType + "'"
             << endl;
        r = nb::none();
    }
    return r;
}




nb::object createDestFunction(const ObjId& oid, const Finfo* finfo) {
      auto rttiType = finfo->rttiType();
      auto fname = finfo->name();

      // Zero parameters
      if (rttiType == "void") {
          return nb::cpp_function([oid, fname]() {
              return SetGet0::set(oid, fname);
          });
      }

      // One parameter
// Shorthand for defining single arg dest function
#define DEST_FUNC_1(TYPE)                                   \
    if(rttiType == #TYPE) {                                 \
        return nb::cpp_function(                            \
            [oid, fname](TYPE val) {                        \
                return SetGet1<TYPE>::set(oid, fname, val); \
            },                                              \
            nb::arg("value"));                              \
    }


      DEST_FUNC_1(double)
      DEST_FUNC_1(unsigned int)
      DEST_FUNC_1(int)
      DEST_FUNC_1(long)
      DEST_FUNC_1(unsigned long)
      DEST_FUNC_1(bool)
      DEST_FUNC_1(string)
      DEST_FUNC_1(Id)
      DEST_FUNC_1(ObjId)
      DEST_FUNC_1(vector<double>)
      DEST_FUNC_1(vector<int>)
      DEST_FUNC_1(vector<unsigned int>)
      DEST_FUNC_1(vector<Id>)
      DEST_FUNC_1(vector<ObjId>)
      DEST_FUNC_1(vector<string>)
#undef DEST_FUNC_1


      vector<string> types;
      moose::tokenize(rttiType, ",", types);

      // Two parameters
      // Short hand for 2-arg functions
#define DEST_FUNC_2(T1, T2, TOKENS)                                     \
      if (TOKENS[0] == #T1 && TOKENS[1] == #T2) {                       \
          return nb::cpp_function([oid, fname](const T1& a, const T2& b) { \
              return SetGet2<T1, T2>::set(oid, fname, a, b);            \
          }, nb::arg("a"), nb::arg("b"));                               \
      }

      if(types.size() == 2) {
          DEST_FUNC_2(double, double, types)
              DEST_FUNC_2(unsigned int, unsigned int, types)
              DEST_FUNC_2(double, unsigned int, types)
              DEST_FUNC_2(unsigned int, unsigned int, types)
              DEST_FUNC_2(unsigned int, double, types)
              DEST_FUNC_2(double, long, types)
              DEST_FUNC_2(string, string, types)
              DEST_FUNC_2(ObjId, ObjId, types)
              DEST_FUNC_2(Id, double, types)
              DEST_FUNC_2(vector<double>, string, types)
              }
#undef DEST_FUNC_2

      // Three param destFinfo - rarely used (just the 6 specific cases)
      //
      //
      // | CompartmentBase | displace     | double, double, double                                           |
      // | SparseMsg       | setEntry     | unsigned int, unsigned int, unsigned int                         |
      // | SparseMsg       | tripletFill  | vector<unsigned int>, vector<unsigned int>, vector<unsigned int> |
      // | TableBase       | compareXplot | string, string, string                                           |
      // | MarkovRateTable | set2d        | unsigned int, unsigned int, Id                                   |
      // | MarkovRateTable | setconst     | unsigned int, unsigned int, double                               |

#define DEST_FUNC_3(T1, T2, T3, TYPES)                       \
          if (TYPES[0] == #T1 && TYPES[1] == #T2 && TYPES[2] == #T3) { \
              return nb::cpp_function([oid, fname](const T1& a, const T2& b, const T3& c) { \
                  return SetGet3<T1, T2, T3>::set(oid, fname, a, b, c); \
              }, nb::arg("a"), nb::arg("b"), nb::arg("c")); \
          }
      if (types.size() == 3){
      DEST_FUNC_3(double, double, double, types)
      DEST_FUNC_3(unsigned int, unsigned int, unsigned int, types)
      DEST_FUNC_3(unsigned int, unsigned int, double, types)
      DEST_FUNC_3(unsigned int, unsigned int, Id, types)
      DEST_FUNC_3(string, string, string, types)
      DEST_FUNC_3(vector<unsigned int>, vector<unsigned int>,
                  vector<unsigned int>, types)
          }
#undef DEST_FUNC_3

          // 4-arg (just the 4 specific cases)
          //
          //  | Class           | Function   | Types                                        |
          //  |-----------------|------------|----------------------------------------------|
          //  | CubeMesh        | buildMesh  | Id, double, double, double                   |
          //  | TableBase       | loadCSV    | string, int, int, char                       |
          //  | TableBase       | compareVec | string, string, unsigned int, unsigned int   |
          //  | MarkovRateTable | set1d      | unsigned int, unsigned int, Id, unsigned int |
          //
#define DEST_FUNC_4(T1, T2, T3, T4, TYPES)                           \
          if (TYPES[0] == #T1 && TYPES[1] == #T2 && TYPES[2] == #T3 && TYPES[3] == #T4) { \
              return nb::cpp_function([oid, fname](const T1& a, const T2& b, const T3& c, const T4& d) { \
                  return SetGet4<T1, T2, T3, T4>::set(oid, fname, a, b, c, d); \
              }, nb::arg("a"), nb::arg("b"), nb::arg("c"), nb::arg("d")); \
          }

      DEST_FUNC_4(Id, double, double, double, types)
      DEST_FUNC_4(string, int, int, char, types)
      DEST_FUNC_4(string, string, unsigned int, unsigned int, types)
      DEST_FUNC_4(unsigned int, unsigned int, Id, unsigned int, types)
#undef DEST_FUNC_4

      throw nb::type_error(("Unsupported DestFinfo type: " + rttiType).c_str());
  }

nb::object getFieldGeneric(const ObjId &oid, const string &fieldName)
{

    // Special fields that do not depend on a valid element being there: empty
    // FieldElements
    if(fieldName == "numData") {
        return nb::cast(Field<unsigned int>::get(oid, "numData"));
    }
    else if(fieldName == "numFields") {
        return nb::cast(Field<unsigned int>::get(oid, "numField"));
    }

    auto cinfo = oid.element()->cinfo();
    auto finfo = cinfo->findFinfo(fieldName);

    if(!finfo) {
        throw nb::attribute_error(
            (fieldName + " is not found on '" + oid.path() + "'.").c_str());
    }

    string finfoType = cinfo->getFinfoType(finfo);

    if(finfoType == "ValueFinfo") {
        return getFieldValue(oid, finfo);
    }
    else if(finfoType == "FieldElementFinfo") {
        return nb::cast(ElementField(oid, finfo));
    }
    else if(finfoType == "LookupValueFinfo") {
        return nb::cast(LookupField(oid, finfo));
    }
    else if(finfoType == "DestFinfo") {
        return createDestFunction(oid, finfo);
    }

    throw runtime_error("getFieldGeneric::NotImplemented : " + fieldName +
                        " with rttType " + finfo->rttiType() + " and type: '" +
                        finfoType + "'");
    return nb::none();
}

ObjId createElementFromPath(const string &type, const string &p,
                            unsigned int numdata)
{

    // NOTE: This function is bit costly because of regex use. One can replace
    // it with bit more efficient one if required.
    auto path = moose::normalizePath(p);

    if(path.at(0) != '/') {
        string cwe = getShellPtr()->getCwe().path();
        if(cwe.back() != '/')
            cwe += '/';
        path = cwe + path;
    }

    // Split into dirname and basename component.
    auto pp = moose::splitPath(path);
    string name(pp.second);
    if(name.empty()) {
        throw nb::value_error(("path= " + path + ": path must not end with '/' except for root.").c_str());
    }
    if(name.back() == ']')
        name = name.substr(0, name.find_last_of('['));

    // Check if parent exists.
    auto parent = ObjId(pp.first);
    if(parent.bad()) {
        throw std::runtime_error("Parent '" + pp.first +
                                 "' is not found. Not creating...");
        return Id();
    }

    // If path exists and user is asking for the same type then return the
    // underlying object else raise an exception.
    auto oid = ObjId(path);
    if(!oid.bad()) {
        if(oid.element()->cinfo()->name() == type)
            return oid;
        else
            throw runtime_error("An object with path'" + path +
                                "' already "
                                "exists. Use moose.element to access it.");
    }

    Id newId = getShellPtr()->doCreate2(type, ObjId(pp.first), name, numdata);
    return ObjId(newId);
}

nb::object getCwe()
{
    return nb::cast(getShellPtr()->getCwe());
}

ObjId convertToObjId(const nb::object &arg)
{
    ObjId ret;
    if(nb::isinstance<nb::str>(arg)) {
        ret = ObjId(nb::cast<string>(arg));
        if (ret.bad()){
            throw nb::value_error(("object does not exist: " + nb::cast<string>(arg)).c_str());
        }
    }
    else if(nb::isinstance<MooseVec>(arg)) {
        ret = nb::cast<MooseVec>(arg).oid();
    }
    else if(nb::isinstance<Id>(arg)) {
        ret = nb::cast<Id>(arg);
    }
    else if(nb::isinstance<ObjId>(arg)) {
        ret = nb::cast<ObjId>(arg);
    }
    else {
        throw nb::type_error("expected str, ObjId, Id, or MooseVec");
    }
    return ret;
}

void setCwe(const nb::object &arg)
{
    getShellPtr()->setCwe(convertToObjId(arg));
}

bool doDelete(nb::object &arg)
{
    ObjId oid = convertToObjId(arg);
    return getShellPtr()->doDelete(oid);
}

MooseVec copy(const nb::object &elem, const nb::object &newParent,
              const string &newName, unsigned int n, bool toGlobal,
              bool copyExtMsgs)
{
    ObjId orig = convertToObjId(elem);
    ObjId newp = convertToObjId(newParent);
    string name = moose::trim(newName);
    if(name.empty()) {
        name = orig.element()->getName();
    }
    return MooseVec(
        getShellPtr()->doCopy(orig.id, newp, name, n, toGlobal, copyExtMsgs));
}

void move(const nb::object &orig, const nb::object &parent)
{
    Id obj{convertToObjId(orig).id};
    ObjId tgt{convertToObjId(parent)};
    getShellPtr()->doMove(obj, tgt);
}

void listElements(const nb::object &arg)
{
    vector<Id> children;
    vector<string> chPaths;
    ObjId obj = convertToObjId(arg);
    if(obj.bad())
        throw std::runtime_error("no such element.");

    Neutral::children(obj.eref(), children);
    stringstream ss;
    ss << "Elements under " << obj.path() << endl;
    for(auto ch : children) {
        ss << "    " + ch.path() << endl;
        chPaths.push_back(ch.path());
    }
    nb::print(ss.str().c_str());
}

vector<ObjId> listMsg(const nb::object &arg, MsgDirection direction)
{
    ObjId obj = convertToObjId(arg);
    vector<ObjId> res;
    if(direction != MsgDirection::Out) {  // Only for 0 skip INCOMING, all other
                                          // cases keep it
        auto inmsgs = Field<vector<ObjId>>::get(obj, "msgIn");
        for(const auto &inobj : inmsgs) {
            const Msg *msg = Msg::getMsg(inobj);
            if(!msg) {
                cerr << "No incoming Msg found on " << obj.path() << endl;
                continue;
            }
            res.push_back(msg->mid());
        }
    }
    if(direction != MsgDirection::In) {  // Only for 1 skip OUTGOING, all other
                                         // cases keep it
        auto outmsgs = Field<vector<ObjId>>::get(obj, "msgOut");
        for(const auto &outobj : outmsgs) {
            const Msg *msg = Msg::getMsg(outobj);
            if(!msg) {
                cerr << "No outgoing Msg found on " << obj.path() << endl;
                continue;
            }
            res.push_back(msg->mid());
        }
    }
    return res;
}

void showMsg(const nb::object &arg, MsgDirection direction)
{
    stringstream ss;
    ObjId obj = convertToObjId(arg);

    auto formatMessages = [&](const vector<ObjId> &msgs, bool isIncoming) {
        const char *arrow = isIncoming ? "<--" : "-->";

        for(const auto &msgObj : msgs) {
            const Msg *msg = Msg::getMsg(msgObj);
            if(!msg) {
                ss << "  (invalid message)\n";
                continue;
            }

            Id e1 = msg->getE1();
            Id e2 = msg->getE2();
            bool objIsE1 = (obj.id == e1);

            ObjId self = obj;
            ObjId other = objIsE1 ? ObjId(e2) : ObjId(e1);

            vector<string> selfFields, otherFields;
            if(isIncoming) {
                selfFields = objIsE1 ? msg->getDestFieldsOnE1()
                                     : msg->getDestFieldsOnE2();
                otherFields =
                    objIsE1 ? msg->getSrcFieldsOnE2() : msg->getSrcFieldsOnE1();
            }
            else {
                selfFields =
                    objIsE1 ? msg->getSrcFieldsOnE1() : msg->getSrcFieldsOnE2();
                otherFields = objIsE1 ? msg->getDestFieldsOnE2()
                                      : msg->getDestFieldsOnE1();
            }

            ss << fmt::format("  {0} [{1}] {2} {3} [{4}]\n", self.path(),
                              moose::vectorToCSV<string>(selfFields), arrow,
                              other.path(),
                              moose::vectorToCSV<string>(otherFields));
        }
    };
    if(direction != MsgDirection::Out) {
        ss << "INCOMING:\n";
        auto inmsgs = Field<vector<ObjId>>::get(obj, "msgIn");
        formatMessages(inmsgs, true);
        ss << "\n";
    }

    if(direction != MsgDirection::In) {
        ss << "OUTGOING:\n";
        auto outmsgs = Field<vector<ObjId>>::get(obj, "msgOut");
        formatMessages(outmsgs, false);
    }

    nb::print(ss.str().c_str());
}

vector<ObjId> getNeighbors(const nb::object &arg, const string &fieldName,
                           const string &msgType,
                           MsgDirection direction = MsgDirection::Both)
{
    vector<ObjId> result;
    ObjId obj = convertToObjId(arg);
    // Normalize msgType once
    string lowerMsgType = msgType;
    std::transform(lowerMsgType.begin(), lowerMsgType.end(),
                   lowerMsgType.begin(), ::tolower);

    // Collect messages based on direction
    vector<ObjId> msgList;
    if(direction != MsgDirection::Out) {
        auto in = Field<vector<ObjId>>::get(obj, "msgIn");
        msgList.insert(msgList.end(), in.begin(), in.end());
    }
    if(direction != MsgDirection::In) {
        auto out = Field<vector<ObjId>>::get(obj, "msgOut");
        msgList.insert(msgList.end(), out.begin(), out.end());
    }

    for(const auto &mobj : msgList) {
        const Msg *msg = Msg::getMsg(mobj);
        if(!msg)
            continue;

        // Filter by message type
        if(!lowerMsgType.empty()) {
            bool matches = (lowerMsgType == "single" &&
                            dynamic_cast<const SingleMsg *>(msg)) ||
                           (lowerMsgType == "onetoone" &&
                            dynamic_cast<const OneToOneMsg *>(msg)) ||
                           (lowerMsgType == "onetoall" &&
                            dynamic_cast<const OneToAllMsg *>(msg)) ||
                           (lowerMsgType == "diagonal" &&
                            dynamic_cast<const DiagonalMsg *>(msg)) ||
                           (lowerMsgType == "sparse" &&
                            dynamic_cast<const SparseMsg *>(msg));
            if(!matches)
                continue;
        }

        // Determine which end we're on
        Id e1 = msg->getE1();
        Id e2 = msg->getE2();
        bool isE1 = (obj.id == e1);

        // Collect relevant fields based on direction
        set<string> fields;
        if(direction != MsgDirection::Out) {
            auto dest =
                isE1 ? msg->getDestFieldsOnE1() : msg->getDestFieldsOnE2();
            fields.insert(dest.begin(), dest.end());
        }
        if(direction != MsgDirection::In) {
            auto src = isE1 ? msg->getSrcFieldsOnE1() : msg->getSrcFieldsOnE2();
            fields.insert(src.begin(), src.end());
        }

        // Check field match and add neighbor
        if(fieldName == "*" || fields.count(fieldName)) {
            result.push_back(isE1 ? e2 : e1);
        }
    }

    return result;
}

ObjId connect(const ObjId &src, const string &srcField, const ObjId &tgt,
              const string &tgtField, const string &msgType)
{
    return getShellPtr()->doAddMsg(msgType, src, srcField, tgt, tgtField);
}

ObjId connectToVec(const ObjId &src, const string &srcField,
                   const MooseVec &tgt, const string &tgtField,
                   const string &msgType)
{
    return connect(src, srcField, tgt.oid(), tgtField, msgType);
}

void setClock(const unsigned int clockId, double dt)
{
    getShellPtr()->doSetClock(clockId, dt);
}

void useClock(size_t tick, const string &path, const string &fn)
{
    getShellPtr()->doUseClock(path, fn, tick);
}

void handleKeyboardInterrupts(int signum)
{
    getShellPtr()->cleanSimulation();
    exit(signum);
}

void start(double runtime, bool notify)
{
    // TODO: handle keyboard interrupt on _WIN32
#if !defined(_WIN32)
    // Credit:
    // http://stackoverflow.com/questions/1641182/how-can-i-catch-a-ctrl-c-event-c
    struct sigaction sigHandler;
    sigHandler.sa_handler = [](int signum) {
        getShellPtr()->cleanSimulation();
        exit(signum);
    };
    sigemptyset(&sigHandler.sa_mask);
    sigHandler.sa_flags = 0;
    sigaction(SIGINT, &sigHandler, NULL);
#endif
    getShellPtr()->doStart(runtime, notify);
}

ObjId loadModelInternal(const string &fname, const string &modelpath,
                   const string &solverclass)
{
    Id model;
    if(solverclass.empty()) {
        model = getShellPtr()->doLoadModel(fname, modelpath);
    }
    else {
        model = getShellPtr()->doLoadModel(fname, modelpath, solverclass);
    }

    if(model == Id()) {
        throw std::runtime_error("could not load model");
        return Id();
    }
    return ObjId(model);
}

map<string, string> getVersionInfo()
{
    std::time_t t = std::time(nullptr);
    char mbstr[100];
    std::strftime(mbstr, sizeof(mbstr), "%A %c", ::localtime(&t));

    vector<string> vers;
    moose::tokenize(string(MOOSE_VERSION), ".", vers);
    if(vers.size() == 3)
        vers.push_back("1");
    return {{"major", vers[0]},
            {"minor", vers[1]},
            {"micro", vers[2]},
            {"releaselevel", vers[3]},
            {"build_datetime", string(mbstr)},
            {"compiler_string", string(COMPILER_STRING)}};
}

}  // namespace pymoose

//
// helper.cpp ends here
