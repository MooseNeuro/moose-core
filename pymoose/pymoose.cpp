// pymoose.cpp ---
//
// Filename: pymoose.cpp
// Description:
// Author: Subhasis Ray
// Created: Fri Dec 26 14:45:14 2025 (+0530)
//

// Code:
#include <Python.h>
#include <nanobind/nanobind.h>

#include <string>
#include <csignal>

#include "../basecode/global.h"
#include "../basecode/header.h"
#include "../randnum/randnum.h"
#include "../shell/Shell.h"
#include "../shell/Wildcard.h"
#include "MooseVec.h"
#include "Finfo.h"
#include "pymoose.h"
#include "docs.h"

using namespace std;
using namespace nb::literals;
using pymoose::MooseVec;
using pymoose::MooseVecIterator;

namespace docs = pymoose::docs;

NB_MODULE(_moose, m)
{
    m.doc() =
        R"mdoc(MOOSE: The Multiscale Object-Oriented Simulation Environment

Designed to simulate neural systems at multiple scales: From subcellular components and biochemical reactions to complex models of individual neurons, neural circuits, and large-scale neuronal networks.
)mdoc";

    // Must initialize shell before all else
    pymoose::initShell();

    // Message directions - to allow both numeric and enum values
    nb::enum_<pymoose::MsgDirection>(m, "MsgDirection", nb::is_arithmetic())
        .value("Out", pymoose::MsgDirection::Out)
        .value("In", pymoose::MsgDirection::In)
        .value("Both", pymoose::MsgDirection::Both);

    nb::class_<pymoose::LookupField>(m, "LookupField")
        .def("__getitem__", &pymoose::LookupField::get)
        .def("__setitem__", &pymoose::LookupField::set)
        .def("__call__", &pymoose::LookupField::get)  // also callable
        .def("__repr__", [](pymoose::LookupField &f) {
            return "<LookupField " + f.finfo_->name() + "{" + f.keyType_ +
                   ": " + f.valueType_ + "}:  of " + f.oid_.path() + ">";
        });

    nb::class_<pymoose::ElementFieldIterator>(m, "ElementFieldIterator")
        .def("__iter__",
             [](pymoose::ElementFieldIterator &self) { return self; })
        .def("__next__", &pymoose::ElementFieldIterator::next);

    nb::class_<pymoose::ElementField>(m, "ElementField")
        .def("__len__", &pymoose::ElementField::size)
        .def("__getitem__", &pymoose::ElementField::getItem)
        .def("__iter__", &pymoose::ElementField::iter)
        .def_prop_ro(
            "path",
            [](const pymoose::ElementField &f) { return f.foid_.path(); })
        .def("__repr__",
             [](pymoose::ElementField &f) {
                 return "<ElementField: " + f.finfo_->name() +
                        " size=" + std::to_string(f.size()) + " of " +
                        f.oid_.path() + ">";
             })
        .def("__getattr__", &pymoose::ElementField::getAttribute)
        .def("__setattr__", &pymoose::ElementField::setAttribute);

    // Access LookupField for vec objects
    nb::class_<pymoose::VecLookupField>(m, "VecLookupField")
        .def("__getitem__", &pymoose::VecLookupField::get)
        .def("__setitem__", &pymoose::VecLookupField::set)
        .def("__repr__", [](pymoose::VecLookupField &f) {
            return "<VecLookupField " + f.finfo_->name() + "{" + f.keyType_ +
                   ": " + f.valueType_ + "}:  of " + f.id_.path() + ">";
        });

    nb::class_<pymoose::VecElementField>(m, "VecElementField")
        .def("__len__", &pymoose::VecElementField::size)
        .def("__getitem__", &pymoose::VecElementField::getParent)
        .def_prop_ro("sizes", &pymoose::VecElementField::sizes)
        .def_prop_ro("path",
                     [](const pymoose::VecElementField &f) {
                         return f.parentId_.path() + "/" + f.finfo_->name();
                     })

        .def("__getattr__", &pymoose::VecElementField::getAttribute)
        .def("__setattr__", &pymoose::VecElementField::setAttribute)
        .def("__repr__", [](pymoose::VecElementField &f) {
            return "<VecElementField " + f.finfo_->name() + " of " +
                   f.parentId_.path() + ">";
        });

    // Id class wrapper
    nb::class_<Id>(m, "Id")
        .def_prop_ro("path", &Id::path, docs::Id_path)
        .def("__getitem__",
             [](const Id &id, size_t index) { return ObjId(id, index); })
        // Id attributes are same as ObjItem attributes.
        .def("__getattr__",
             [](const Id &id, const string &key) {
                 return pymoose::getFieldGeneric(ObjId(id), key);
             })
        .def("__setattr__",
             [](const Id &id, const string &key, const nb::object &val) {
                 return pymoose::setFieldGeneric(ObjId(id), key, val);
             })
        .def("__repr__",
             [](const Id &id) {
                 return "<Id: id=" + to_string(id.value()) +
                        " path=" + id.path() +
                        " class=" + id.element()->cinfo()->name() + ">";
             })
        .def("__eq__", [](const Id &a, const Id &b) { return a == b; })
        .def("__ne__", [](const Id &a, const Id &b) { return a != b; })
        .def("__hash__", &Id::value);

    // ObjId class wrapper
    nb::class_<ObjId>(m, "ObjId")
        .def(nb::init<>(), docs::ObjId_init_root)
        .def(nb::init<const ObjId &>(), nb::arg("other"),
             docs::ObjId_init_other)
        .def(nb::init<Id, unsigned int, unsigned int>(), nb::arg("i"),
             nb::arg("d") = 0, nb::arg("f") = 0, docs::ObjId_init_id)
        .def(nb::init<const string &>(), nb::arg("path"), docs::ObjId_init_path)
        .def_prop_ro(
            "vec", [](const ObjId &oid) { return MooseVec(oid); },
            docs::ObjId_vec)
        .def_prop_ro(
            "name", [](ObjId oid) { return oid.element()->getName(); },
            docs::ObjId_name)
        .def_prop_ro(
            "className",
            [](ObjId oid) { return oid.element()->cinfo()->name(); },
            docs::ObjId_className)
        .def_prop_ro(
            "type", [](ObjId oid) { return oid.element()->cinfo()->name(); },
            "Class of the element")
        .def_prop_ro(
            "parent", [](const ObjId &oid) { return Neutral::parent(oid); },
            docs::ObjId_parent)
        .def_prop_ro(
            "children",
            [](const ObjId &oid) {
                vector<Id> childIds;
                Neutral::children(oid.eref(), childIds);
                vector<ObjId> ret;
                ret.reserve(childIds.size());
                for(const Id &id : childIds) {
                    ret.emplace_back(ObjId(id));
                }
                return ret;
            },
            docs::ObjId_children)
        .def_ro("id", &ObjId::id, docs::ObjId_id)
        .def_ro("dataIndex", &ObjId::dataIndex, docs::ObjId_dataIndex)
        .def_ro("fieldIndex", &ObjId::fieldIndex, docs::ObjId_fieldIndex)
        .def("__eq__", [](const ObjId &a, const ObjId &b) { return a == b; })
        .def("__ne__", [](const ObjId &a, const ObjId &b) { return a != b; })
        .def("__hash__", [](const ObjId &oid) { return oid.id.value(); })
        .def("__getattr__", &pymoose::getFieldGeneric)
        .def("__setattr__", &pymoose::setFieldGeneric)
        .def(
            "connect",
            [](const ObjId &self, const string &srcfield, const ObjId &dest,
               const string &destfield, const string &msgtype) {
                return pymoose::connect(self, srcfield, dest, destfield,
                                        msgtype);
            },
            nb::arg("srcfield"), nb::arg("dest"), nb::arg("destfield"),
            nb::arg("msgtype") = "Single", docs::ObjId_connect)
        .def(
            "connect",
            [](const ObjId &self, const string &srcfield, const MooseVec &dest,
               const string &destfield, const string &msgtype) {
                return pymoose::connectToVec(self, srcfield, dest, destfield,
                                             msgtype);
            },
            nb::arg("srcfield"), nb::arg("dest"), nb::arg("destfield"),
            nb::arg("msgtype") = "Single", docs::ObjId_connect)
        .def("__repr__", [](const ObjId &oid) {
            return "<moose." + oid.element()->cinfo()->name() +
                   " id=" + to_string(oid.id.value()) +
                   " dataIndex=" + to_string(oid.eref().dataIndex()) +
                   " path=" + oid.path() + ">";
        });

    nb::class_<MooseVecIterator>(m, "MooseVecIterator")
        .def("__iter__", [](MooseVecIterator &self) { return self; })
        .def("__next__", &MooseVecIterator::next);

    // vec class for vectorization over dataIndex or fieldIndex.
    nb::class_<MooseVec>(m, "vec")
        .def(nb::init<const string &, unsigned int, const string &>(),
             nb::arg("path"), nb::arg("n") = 1, nb::arg("dtype") = "",
             docs::MooseVec_init)  // Default
        .def(nb::init<const ObjId &>())
        .def("__eq__", [](const MooseVec &a,
                          const MooseVec &b) { return a.oid() == b.oid(); })
        .def("__ne__", [](const MooseVec &a,
                          const MooseVec &b) { return a.oid() != b.oid(); })
        .def("__len__", &MooseVec::size)

        .def("__iter__", [](MooseVec &self) { return MooseVecIterator(self); })
        .def("__getitem__", &MooseVec::getItem)
        .def("__getitem__", &MooseVec::getItemRange)

        // Templated function won't work here. The first one is always called.
        .def("__getattr__", &MooseVec::getAttribute)
        .def("__setattr__", &MooseVec::setAttribute)
        .def("__repr__",
             [](const MooseVec &v) -> string {
                 return "<moose.vec class=" + v.dtype() + " path=" + v.path() +
                        " id=" + std::to_string(v.id()) +
                        " size=" + std::to_string(v.size()) + ">";
             })
        .def_prop_ro("type", [](const MooseVec &v) { return "moose.vec"; })
        .def("connect", &MooseVec::connectToSingle, nb::arg("srcfield"),
             nb::arg("dest"), nb::arg("destfield"),
             nb::arg("msgtype") = "Single", docs::MooseVec_connect)
        .def("connect", &MooseVec::connectToVec, nb::arg("srcfield"),
             nb::arg("dest"), nb::arg("destfield"),
             nb::arg("msgtype") = "Single", docs::MooseVec_connect)

        // Thi properties are not vectorised.
        .def_prop_ro("parent", &MooseVec::parent)
        .def_prop_ro("children", &MooseVec::children)
        .def_prop_ro("name", &MooseVec::name)
        .def_prop_ro("path", &MooseVec::path)
        // Wrapped object.
        .def_prop_ro("oid", &MooseVec::oid);

    // Module functions
    m.def(
        "seed", [](nb::object &a) { moose::mtseed(nb::cast<int>(a)); },
        docs::seed);
    m.def(
        "rand", [](double a, double b) { return moose::mtrand(a, b); },
        nb::arg("a") = 0, nb::arg("b") = 1, docs::rand);
    // This is a wrapper to Shell::wildcardFind. The python interface must
    // override it.
    m.def("wildcardFind", &::wildcardFind2);

    m.def("element", &pymoose::convertToObjId, docs::convertToObjId);
    m.def("delete", &pymoose::doDelete, docs::doDelete);
    m.def("copy", &pymoose::copy, nb::arg("orig"), nb::arg("parent"),
          nb::arg("name") = "", nb::arg("num") = 1, nb::arg("toGlobal") = false,
          nb::arg("copyExtMsgs") = false, docs::copy);
    m.def("move", &pymoose::move, nb::arg("orig"), nb::arg("parent"),
          docs::move);

    m.def("reinit", []() { pymoose::getShellPtr()->doReinit(); }, docs::reinit);
    m.def("start", &pymoose::start, nb::arg("runtime"),
          nb::arg("notify") = false, docs::start);
    m.def("stop", []() { pymoose::getShellPtr()->doStop(); }, docs::stop);
    m.def(
        "isRunning", []() { return pymoose::getShellPtr()->isRunning(); },
        docs::isRunning);

    m.def(
        "exists",
        [](string path) {
            return Id(path) != Id() && path != "/" && path != "/root";
        },
        nb::arg("path"), docs::exists);

    m.def("getCwe", &pymoose::getCwe, docs::getCwe);

    m.def("pwe", &pymoose::getCwe, docs::getCwe);

    m.def("setCwe", &pymoose::setCwe, docs::setCwe);
    m.def("ce", &pymoose::setCwe, docs::setCwe);
    m.def("le", &pymoose::listElements, nb::arg("path") = ".",
          docs::listElements);
    m.def("showmsg", &pymoose::showMsg, nb::arg("obj"),
          nb::arg("direction") = pymoose::MsgDirection::Both, docs::showMsg);
    m.def("listmsg", &pymoose::listMsg, nb::arg("element"),
          nb::arg("direction") = pymoose::MsgDirection::Both, docs::listMsg);

    m.def("neighbors", &pymoose::getNeighbors, nb::arg("obj"),
          nb::arg("field") = "*", nb::arg("msgType") = "", nb::arg("direction"),
          docs::getNeighbors);

    m.def("connect", &pymoose::connect, nb::arg("src"), nb::arg("srcfield"),
          nb::arg("dest"), nb::arg("destfield"), nb::arg("msgtype") = "Single",
          docs::connect);

    m.def("connect", &pymoose::connectToVec, nb::arg("src"),
          nb::arg("srcfield"),

          nb::arg("dest"), nb::arg("destfield"), nb::arg("msgtype") = "Single",
          docs::connect);

    m.def("getFieldNames", &pymoose::getFieldNames, nb::arg("classname"),
          nb::arg("fieldtype") = "*", docs::getFieldNames);

    m.def("getFieldTypeDict", &pymoose::getFieldTypeDict, nb::arg("classname"),
          nb::arg("fieldtype") = "*", docs::getFieldTypeDict);

    m.def("getField", &pymoose::getFieldGeneric, nb::arg("obj"),
          nb::arg("field"), docs::getFieldGeneric);

    m.def("setClock", &pymoose::setClock, nb::arg("tick"), nb::arg("dt"),
          docs::setClock);
    m.def("useClock", &pymoose::useClock, nb::arg("tick"), nb::arg("path"),
          nb::arg("fn"), docs::useClock);

    m.def("loadModelInternal", &pymoose::loadModelInternal);

    m.def("getDoc", &pymoose::getDoc, docs::getDoc);

    m.def("version_info", &pymoose::getVersionInfo);
    // ----------------------------------------------------------------------
    // Global Constant Attributes.
    // ----------------------------------------------------------------------
    m.attr("NA") = NA;
    m.attr("PI") = PI;
    m.attr("FaradayConst") = FaradayConst;
    m.attr("GasConst") = GasConst;
    m.attr("OUTMSG") = 0;
    m.attr("INMSG") = 1;
    m.attr("ALLMSG") = 2;
    // PyRun mode
    m.attr("PYRUN_PROC") = 0;
    m.attr("PYRUN_TRIG") = 1;
    m.attr("PYRUN_BOTH") = 2;

    // Version information.
    m.attr("__version__") = MOOSE_VERSION;
    m.attr("__generated_by__") = "nanobind";
}

//
// pymoose.cpp ends here
