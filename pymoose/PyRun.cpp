// PyRun.cpp ---
//
// Filename: PyRun.cpp
// Description:
// Author: subha
// Created: Sat Oct 11 14:47:22 2014 (+0530)

#include "../basecode/header.h"

#include "PyRun.h"

const int PyRun::RUNPROC = 0;
const int PyRun::RUNTRIG = 1;
const int PyRun::RUNBOTH = 2;

static SrcFinfo1<double>* outputOut()
{
    static SrcFinfo1<double> outputOut(
        "output",
        "Sends out the value of local variable called `output`. Thus, you can"
        " have Python statements which compute some value and assign it to the"
        " variable called `output` (which is defined at `reinit` call). This"
        " will be sent out to any target connected to the `output` field.");
    return &outputOut;
}

const Cinfo* PyRun::initCinfo()
{
    static ValueFinfo<PyRun, string> runstring(
        "runString", "String to be executed at each time step.",
        &PyRun::setRunString, &PyRun::getRunString);

    static ValueFinfo<PyRun, string> initstring(
        "initString", "String to be executed at initialization (reinit).",
        &PyRun::setInitString, &PyRun::getInitString);

    static ValueFinfo<PyRun, string> inputvar(
        "inputVar",
        "Name of local variable in which input balue is to be stored. Default"
        " is `input_` (to avoid conflict with Python's builtin function"
        " `input`).",
        &PyRun::setInputVar, &PyRun::getInputVar);

    static ValueFinfo<PyRun, string> outputvar(
        "outputVar",
        "Name of local variable for storing output. Default is `output`.",
        &PyRun::setOutputVar, &PyRun::getOutputVar);

    static ValueFinfo<PyRun, int> mode(
        "mode",
        "Flag to indicate whether runString "
        "should be executed for both trigger "
        "and process, or one of them.  0: run only process, 1: run only "
        "trigger, and 2: run both (default 0)",
        &PyRun::setMode, &PyRun::getMode);

    static ValueFinfo<PyRun, bool> evalOnReinit(
        "evalOnReinit",
        "Flag to indicate whether runString should be executed upon reinit().",
        &PyRun::setEvalOnReinit, &PyRun::getEvalOnReinit);

    static ReadOnlyValueFinfo<PyRun, double> outputValue(
        "outputValue",
        "Get the (computed) value stored in output variable (named "
        "in `outputVar` field).",
        &PyRun::getOutputValue);

    static DestFinfo trigger(
        "trigger",
        "Executes the current runString whenever a message arrives. It stores"
        " the incoming value in local variable named"
        " `input_`, which can be used in the"
        " `runString` (the underscore is added to avoid conflict with Python's"
        " builtin function `input`).",
        new EpFunc1<PyRun, double>(&PyRun::trigger));

    static DestFinfo run("run",
                         "Runs a specified string. Does not modify existing "
                         "run or init strings.",
                         new EpFunc1<PyRun, string>(&PyRun::run));

    static DestFinfo process(
        "process", "Handles process call. Runs the current runString.",
        new ProcOpFunc<PyRun>(&PyRun::process));

    static DestFinfo reinit("reinit",
                            "Handles reinit call. Runs the current initString.",
                            new ProcOpFunc<PyRun>(&PyRun::reinit));

    static Finfo* processShared[] = {&process, &reinit};
    static SharedFinfo proc(
        "proc",
        "This is a shared message to receive Process messages "
        "from the scheduler objects."
        "The first entry in the shared msg is a MsgDest "
        "for the Process operation. It has a single argument, "
        "ProcInfo, which holds lots of information about current "
        "time, thread, dt and so on. The second entry is a MsgDest "
        "for the Reinit operation. It also uses ProcInfo. ",
        processShared, sizeof(processShared) / sizeof(Finfo*));

    static Finfo* pyRunFinfos[] = {
        &runstring,  &initstring, &mode,        &evalOnReinit,
        &inputvar,   &outputvar,  &outputValue, &trigger,
        outputOut(), &run,        &proc,
    };

    static string doc[] = {
        "Name",        "PyRun",
        "Author",      "Subhasis Ray",
        "Description", "Runs Python statements from inside MOOSE."};
    static Dinfo<PyRun> dinfo;
    static Cinfo pyRunCinfo("PyRun", Neutral::initCinfo(), pyRunFinfos,
                            sizeof(pyRunFinfos) / sizeof(Finfo*), &dinfo, doc,
                            sizeof(doc) / sizeof(string));
    return &pyRunCinfo;
}

static const Cinfo* pyRunCinfo = PyRun::initCinfo();

PyRun::PyRun()
    : evalOnReinit_(false),
      mode_(0),
      initstr_(""),
      runstr_(""),
      globals_(),
      locals_(),
      runcompiled_(),
      initcompiled_(),
      inputvar_("input_"),
      outputvar_("output")
{
}

PyRun::~PyRun()
{
}

void PyRun::setRunString(string statement)
{
    runstr_ = statement;
}

string PyRun::getRunString() const
{
    return runstr_;
}

void PyRun::setInitString(string statement)
{
    initstr_ = statement;
}

string PyRun::getInitString() const
{
    return initstr_;
}

void PyRun::setInputVar(string name)
{
    inputvar_ = name;
}

string PyRun::getInputVar() const
{
    return inputvar_;
}

void PyRun::setOutputVar(string name)
{
    outputvar_ = name;
}

string PyRun::getOutputVar() const
{
    return outputvar_;
}

void PyRun::setEvalOnReinit(bool flag)
{
    evalOnReinit_ = flag;
}

bool PyRun::getEvalOnReinit() const
{
    return evalOnReinit_;
}

void PyRun::setMode(int flag)
{
    mode_ = flag;
}

int PyRun::getMode() const
{
    return mode_;
}

double PyRun::getOutputValue() const
{
    if(locals_.contains(outputvar_.c_str())) {
        return nb::cast<double>(locals_[outputvar_.c_str()]);
    }
    throw runtime_error("Output variable `" + outputvar_ +
                        "` not set in Python statements.");
}
void PyRun::setGlobals(nb::dict globals)
{
    globals_ = globals;
}

nb::dict PyRun::getGlobals() const
{
    return globals_;
}

void PyRun::setLocals(nb::dict locals)
{
    locals_ = locals;
}

nb::dict PyRun::getLocals() const
{
    return locals_;
}

void PyRun::trigger(const Eref& e, double input)
{
    if(!runcompiled_.is_valid() || mode_ == RUNPROC) {
        return;
    }

    try {
        locals_[inputvar_.c_str()] = nb::cast(input);

        // Execute the compiled code
        PyObject* result =
            PyEval_EvalCode(runcompiled_.ptr(), globals_.ptr(), locals_.ptr());
        if(!result) {
            throw nb::python_error();
        }
        Py_DECREF(result);

        // Get output variable
        if(locals_.contains(outputvar_.c_str())) {
            double output = nb::cast<double>(locals_[outputvar_.c_str()]);
            outputOut()->send(e, output);
        }
    }
    catch(nb::python_error& err) {
        std::cerr << "ERROR: PyRun::trigger(): " << err.what() << std::endl;
        throw;
    }
}

void PyRun::run(const Eref& e, string statement)
{
    try {
        nb::exec(nb::str(statement.c_str()), globals_, locals_);
        if(locals_.contains(outputvar_.c_str())) {
            double output = nb::cast<double>(locals_[outputvar_.c_str()]);
            outputOut()->send(e, output);
        }
    }
    catch(nb::python_error& err) {
        cerr << "ERROR: PyRun::run(): " << err.what() << endl;
        throw;
    }
}

void PyRun::process(const Eref& e, ProcPtr p)
{
    if(!runcompiled_.is_valid() || mode_ == RUNTRIG) {
        return;
    }

    // RAII-based GIL acquisition - released when scope exits
    nb::gil_scoped_acquire gil;

    try {
        PyObject* result =
            PyEval_EvalCode(runcompiled_.ptr(), globals_.ptr(), locals_.ptr());
        if(!result) {
            throw nb::python_error();
        }
        Py_DECREF(result);

        if(locals_.contains(outputvar_.c_str())) {
            double output = nb::cast<double>(locals_[outputvar_.c_str()]);
            outputOut()->send(e, output);
        }
    }
    catch(nb::python_error& err) {
        std::cerr << "ERROR: PyRun::process(): " << err.what() << std::endl;
        throw;
    }
    // GIL automatically released here when 'gil' goes out of scope
}

void PyRun::reinit(const Eref& e, ProcPtr p)
{

    nb::gil_scoped_acquire gil;

    try {
        // Initialize globals from __main__ if not set
        if(!globals_.is_valid() || globals_.empty()) {
            nb::object main_module = nb::module_::import_("__main__");
            globals_ =
                nb::borrow<nb::dict>(PyModule_GetDict(main_module.ptr()));
        }
        if(!globals_.contains("__builtins__")) {
            globals_["__builtins__"] = nb::borrow(PyEval_GetBuiltins());
        }
        // Initialize locals if not set
        if(!locals_.is_valid()) {
            locals_ = nb::dict();
        }
        // Compile and run init string
        if(!initstr_.empty()) {
            PyObject* compiled = Py_CompileString(
                initstr_.c_str(), "moose.PyRun::reinit", Py_file_input);
            if(!compiled) {
                std::cerr << "Error compiling initString" << std::endl;
                throw nb::python_error();
            }
            initcompiled_ = nb::steal(compiled);

            PyObject* result = PyEval_EvalCode(initcompiled_.ptr(),
                                               globals_.ptr(), locals_.ptr());
            if(!result) {
                throw nb::python_error();
            }
            Py_DECREF(result);
        }

        // Compile and run runString
        PyObject* compiled = Py_CompileString(
            runstr_.c_str(), "moose.PyRun::reinit", Py_file_input);
        if(!compiled) {
            std::cerr << "Error compiling runString" << std::endl;
            throw nb::python_error();
        }
        runcompiled_ = nb::steal(compiled);
        /// init should only run `initStr`
        if(evalOnReinit_) {
            PyObject* result = PyEval_EvalCode(initcompiled_.ptr(),
                                               globals_.ptr(), locals_.ptr());
            if(!result) {
                throw nb::python_error();
            }
            Py_DECREF(result);
        }
    }
    catch(nb::python_error& err) {
        std::cerr << "ERROR: PyRun::reinit(): " << err.what() << std::endl;
        throw;
    }
}
