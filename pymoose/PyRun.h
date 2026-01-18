// Filename: PyRun.h
// Description:
// Author: subha
// Created: Sat Oct 11 14:40:45 2014 (+0530)

#pragma once

#include <climits>
#include <string>

#ifdef _DEBUG
#undef _DEBUG
#include <Python.h>
#define _DEBUG
#else
#include <Python.h>
#endif

#include <nanobind/nanobind.h>
#include <nanobind/eval.h>
#include <nanobind/stl/string.h>


namespace nb = nanobind;


/**
   PyRun allows running Python statements from moose.
 */
class PyRun
{
public:
    static const int RUNPROC; // only process call
    static const int RUNTRIG; // only trigger call
    static const int RUNBOTH; // both

    PyRun();
    ~PyRun();

    // Note: because of template limitations in ValueFinfo, we cannot
    // use const std::string&, instead use std::string everywhere. As
    // these are infrequently used, the performance penalty is not
    // much.
    void setInitString(std::string str);
    std::string getInitString() const;

    void setRunString(std::string str);
    std::string getRunString() const;

    void setGlobals(nb::dict globals);
    nb::dict getGlobals() const;

    void setLocals(nb::dict locals);
    nb::dict getLocals() const;

    void setMode(int flag);
    int getMode() const;

    void setEvalOnReinit(bool flag);
    bool getEvalOnReinit() const;

    /// Specify which variable should be used as input
    void setInputVar(std::string name);
    std::string getInputVar() const;

    /// Specify which variable should be used as output
    void setOutputVar(std::string name);
    std::string getOutputVar() const;

    /// Get value of `outputVar` set in Python
    double getOutputValue() const;

    /// Run specified Python statement
    // Note: this uses string instead of const string& because
    void run(const Eref& e, std::string statement);

     /// Way to trigger execution via incoming message
    void trigger(const Eref& e, double input);

    void process(const Eref& e, ProcPtr p);
    void reinit(const Eref& e, ProcPtr p);

    static const Cinfo * initCinfo();

protected:
    bool evalOnReinit_;  // flag to indicate if runString should be evaluated on reinit
    int mode_;                    // flag to decide when to run the Python string
    std::string initstr_;              // statement str for running at reinit
    std::string runstr_;               // statement str for running in each process call
    nb::dict globals_;          // global env dict
    nb::dict locals_;           // local env dict
    nb::object runcompiled_;      // compiled form of procstr_
    nb::object initcompiled_;     // coimpiled form of initstr_
    std::string inputvar_;             // identifier for input variable.
    std::string outputvar_;            // identifier for output variable
};
