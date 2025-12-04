/***
 *    Description:  Wrapper around MooseParser.
 *         Author:  Dilawar Singh <diawar.s.rajput@gmail.com>, Subhasis Ray
 *     Maintainer:  Dilawar Singh <dilawars@ncbs.res.in>
 */

#include <regex>
#include <algorithm>

#include "../basecode/header.h"
#include "../basecode/global.h"
#include "../basecode/ElementValueFinfo.h"
#include "../basecode/LookupElementValueFinfo.h"

#include "../utility/strutil.h"
#include "../utility/numutil.h"
#include "../utility/testing_macros.hpp"
#include "../utility/print_function.hpp"

#include "../builtins/MooseParser.h"

#include "Variable.h"
#include "Function.h"

#include "../ksolve/RateTerm.h"
#include "../basecode/SparseMatrix.h"
#include "../ksolve/KinSparseMatrix.h"
class KsolveBase;
#include "../ksolve/Stoich.h"


static const double TriggerThreshold = 0.0;

static SrcFinfo1<double> *valueOut()
{
    static SrcFinfo1<double> valueOut("valueOut",
            "Evaluated value of the function for the current variable values."
            );
    return &valueOut;
}

static SrcFinfo1< double > *derivativeOut()
{
    static SrcFinfo1< double > derivativeOut("derivativeOut",
            "Value of derivative of the function for the current variable values");
    return &derivativeOut;
}

static SrcFinfo1< double > *rateOut()
{
    static SrcFinfo1< double > rateOut("rateOut",
            "Value of time-derivative of the function for the current variable values"
            );
    return &rateOut;
}

static SrcFinfo1< vector < double > *> *requestOut()
{
    static SrcFinfo1< vector < double > * > requestOut(
            "requestOut",
            "Sends request for input variable from a field on target object");
    return &requestOut;

}

const Cinfo * Function::initCinfo()
{
    // Value fields
    static  ReadOnlyValueFinfo< Function, double > value(
        "value",
        "Value calculated in the last evaluation of the function. This gets"
	" updated in each simulation step.",
        &Function::getValue
    );

    static  ReadOnlyValueFinfo< Function, double > evalResult(
        "evalResult",
        "Result of the function evaluation with current variable values. This"
	" can be used for evaluating the function without running a simulation"
	" step.",
        &Function::getEval
    );

    static ReadOnlyValueFinfo< Function, double > derivative(
        "derivative",
        "Derivative of the function at given variable values. This is calulated"
        " using 5-point stencil "
        " <http://en.wikipedia.org/wiki/Five-point_stencil> at current value of"
        " independent variable. Note that unlike hand-calculated derivatives,"
        " numerical derivatives are not exact.",
        &Function::getDerivative
    );

    static ReadOnlyValueFinfo< Function, double > rate(
        "rate",
        "Derivative of the function at given variable values. This is computed"
        " as the difference of the current and previous value of the function"
        " divided by the time step.",
        &Function::getRate
    );

    static ValueFinfo< Function, unsigned int > mode(
        "mode",
        "Mode of operation (default 1): \n"
        " 1: only the function value will be sent out.\n"
        " 2: only the derivative with respect to the independent variable will be sent out.\n"
        " 3: only rate (time derivative) will be sent out.\n"
        " anything else: all three, value, derivative and rate will be sent out.\n",
        &Function::setMode,
        &Function::getMode
    );

    static ValueFinfo< Function, bool > useTrigger(
        "useTrigger",
        "When *false*, disables event-driven calculation and turns on "
        "Process-driven calculations. \n"
        "When *true*, enables event-driven calculation and turns off "
        "Process-driven calculations. \n"
        "Defaults to *false*. \n",
        &Function::setUseTrigger,
        &Function::getUseTrigger
    );

    static ValueFinfo< Function, bool > doEvalAtReinit(
        "doEvalAtReinit",
        "Deprecated: This does not have any use."
	"When *false*, disables function evaluation at reinit, and "
        "just emits a value of zero to any message targets. \n"
        "When *true*, does a function evaluation at reinit and sends "
        "the computed value to any message targets. \n"
        "Defaults to *false*. \n",
        &Function::setDoEvalAtReinit,
        &Function::getDoEvalAtReinit
    );

    static ValueFinfo< Function, bool > allowUnknownVariable(
        "allowUnknownVariable",
        "When *false*, expression can only have ci, xi, yi and t."
        "When set to *true*, expression can have arbitrary names."
        "Defaults to *true*. \n",
        &Function::setAllowUnknownVariable,
        &Function::getAllowUnknowVariable
    );

    static ElementValueFinfo< Function, string > expr(
        "expr",
        "Mathematical expression defining the function. The underlying parser\n"
        "is exprtk (https://archive.codeplex.com/?p=exprtk) . In addition to the\n"
        "available functions and operators  from exprtk, a few functions are added.\n"
        "\nMajor Functions\n"
        "Name        args    explanation\n"
        "sin         1       sine function\n"
        "cos         1       cosine function\n"
        "tan         1       tangens function\n"
        "asin        1       arcus sine function\n"
        "acos        1       arcus cosine function\n"
        "atan        1       arcus tangens function\n"
        "sinh        1       hyperbolic sine function\n"
        "cosh        1       hyperbolic cosine\n"
        "tanh        1       hyperbolic tangens function\n"
        "asinh       1       hyperbolic arcus sine function\n"
        "acosh       1       hyperbolic arcus tangens function\n"
        "atanh       1       hyperbolic arcur tangens function\n"
        "log2        1       logarithm to the base 2\n"
        "log10       1       logarithm to the base 10\n"
        "log         1       logarithm to the base 10\n"
        "ln          1       logarithm to base e (2.71828...)\n"
        "exp         1       e raised to the power of x\n"
        "sqrt        1       square root of a value\n"
        "sign        1       sign function -1 if x<0; 1 if x>0\n"
        "abs         1       absolute value\n"
        "min         var.    min of all arguments\n"
        "max         var.    max of all arguments\n"
        "sum         var.    sum of all arguments\n"
        "avg         var.    mean value of all arguments\n"
        "rnd         0       rand(), random float between 0 and 1, honors global moose.seed.\n"
        "rand        1       rand(seed), random float between 0 and 1, \n"
        "                    if seed = -1, then a 'random' seed is used.\n"
        "rand2       3       rand(a, b, seed), random float between a and b, \n"
        "                    if seed = -1, a 'random' seed is created using either\n"
        "                    by random_device or by reading system clock\n"
        "\nOperators\n"
        "Op  meaning                      priority\n"
        "=   assignment                     -1\n"
        "&&,and  logical and                1\n"
        "||,or  logical or                  2\n"
        "<=  less or equal                  4\n"
        ">=  greater or equal               4\n"
        "!=,not  not equal                  4\n"
        "==  equal                          4\n"
        ">   greater than                   4\n"
        "<   less than                      4\n"
        "+   addition                       5\n"
        "-   subtraction                    5\n"
        "*   multiplication                 6\n"
        "/   division                       6\n"
        "^   raise x to the power of y      7\n"
        "%   floating point modulo          7\n"
        "\n"
        "?:  if then else operator          C++ style syntax\n"
        "\n\n"
        "For more information see https://archive.codeplex.com/?p=exprtk \n",
        &Function::setExpr,
        &Function::getExpr
    );

    static ReadOnlyValueFinfo< Function, unsigned int > numVars(
        "numVars",
        "Number of variables used by Function. It is determined by parsing"
	" when `expr` is set",
        &Function::getNumVar
    );

    static FieldElementFinfo< Function, Variable > inputs(
        "x",
        "Input variables (indexed) to the function."
	" The values can be passed via messages to the `input` field on each"
	" entry.",
        Variable::initCinfo(),
        &Function::getX,
        &Function::setNumVar,
        &Function::getNumVar
    );


    static LookupValueFinfo < Function, string, double > constants(
        "c",
        "Constants used in the function. These must be assigned before"
        " specifying the function expression.",
        &Function::setConst,
        &Function::getConst
    );

    static LookupValueFinfo< Function, string, unsigned int > xindex(
        "xindex",
        "Returns the index of a given variable which can be used with field `x`."
        " Note that we have a mechanism to map string (variable name) to integer "
        " (variable index).",
        &Function::setVarIndex,
        &Function::getVarIndex
    );

    static ReadOnlyValueFinfo< Function, vector < double > > y(
        "y",
        "Variable values received from target fields by 'requestOut' message",
        &Function::getY
    );

    static ValueFinfo<Function, string> independent(
        "independent",
        "Index of independent variable. Differentiation is done based on this."
        " Defaults to the first assigned variable.",
        &Function::setIndependent,
        &Function::getIndependent
    );

	static DestFinfo setSolver( "setSolver",
		"Assigns solver to this Function.",
		new EpFunc1< Function, ObjId >( &Function::setSolver ) );

    ///////////////////////////////////////////////////////////////////
    // Shared messages
    ///////////////////////////////////////////////////////////////////
    static DestFinfo process( "process",
            "Handles process call, updates internal time stamp.",
            new ProcOpFunc< Function >( &Function::process )
            );

    static DestFinfo reinit( "reinit",
            "Handles reinit call.",
            new ProcOpFunc< Function >( &Function::reinit )
            );

    static Finfo* processShared[] = { &process, &reinit };

    static SharedFinfo proc( "proc",
            "This is a shared message to receive Process messages "
            "from the scheduler objects."
            "The first entry in the shared msg is a MsgDest "
            "for the Process operation. It has a single argument, "
            "ProcInfo, which holds lots of information about current "
            "time, thread, dt and so on. The second entry is a MsgDest "
            "for the Reinit operation. It also uses ProcInfo. ",
            processShared, sizeof( processShared ) / sizeof( Finfo* )
            );


    static Finfo *functionFinfos[] = {
        &value,
	&evalResult,
        &rate,
        &derivative,
        &mode,
        &useTrigger,
        &doEvalAtReinit,
        &allowUnknownVariable,
        &expr,
        &numVars,
        &inputs,
        &xindex,
        &constants,
        &independent,
	&setSolver,			// DestFinfo
        &proc,
        requestOut(),
        valueOut(),
        rateOut(),
        derivativeOut(),
    };

    static string doc[] = {
        "Name", "Function", "Author", "Subhasis Ray/Dilawar Singh",
        "Description",
        R"#(
General purpose function calculator using real numbers.

It can parse mathematical expression defining a function and evaluate it and/or
its derivative for specified variable values.  You can assign expressions of
the form::

 f(t, x, y, var, p, q, Ca, CaMKII) 

NOTE: `t` represents time. You CAN NOT use to for any other purpose.

The constants must be defined before setting the expression using 
the lookup field `c`. Once set, their values cannot be changed.

The interpretation of variable names in expression depends on 
`allowUnknownVariables` flag::

When `allowUnknownVariables` is `True` (default):

- Names of the form "x{n}", where n is a non-negative integer, 
  are treated as input variables that are pushed from fields in
  other objects via incoming messages to the `input` dest of the
  corresponding `x` field.

- Names of the form "y{n}" are treated as input variables, that 
  are requested via the outgoing `requestOut` message from other
  objects' value fields.

- Any name that has already been assigned as a constant (e.g., 
  inserted with `Function.c['name'] = value` or predefined
  mathematical constants like `pi`, `e`) is treated as constant.

- All other names are assumed to be variables and assigned successive
  entries in the `x` field.


When `allowUnknownVariables` is `False`, the allowed names are 
restricted:

- Names of the form "x{n}", where n is a non-negative integer, 
  are treated as input variables that are pushed from fields in
  other objects via incoming messages to the `input` dest of the
  corresponding `x` field.

- Names of the form "y{n}" are treated as input variables, that 
  are requested via the outgoing `requestOut` message from other
  objects' value fields.

- Any name that has already been assigned as a constant (e.g., 
  inserted with `Function.c['name'] = value`), is treated 
  as constant.

- If the expression has any name that is not "t" (for time), or one of
  the above, it throws an error.

Input (independent) variables come from other elements, either pushed
into entries in element field "x" through "input" dest field, or pulled via
"requestOut" message to "get{Field}" dest field on the source element and
collected in the "y" variables. 

In pull-mode, the y-indices correspond to the order of connecting the
messages. This is used when the input variable is not available as a source 
field, but is a value field. For any value field `{field}`, the object has
a corresponding dest field `get{Field}`. The "requestOut" src field is 
connected to this.

This class handles only real numbers (C-double). Predefined constants
are: pi=3.141592..., e=2.718281...


Example::

The following python example illustrates a Function which has a user-defined 
constant 'A', two pushed variables, 'Vm' and 'n', which come from a 
compartment object, and one pulled variable 'y0', which is read from
the 'diameter' field of the compartment. It also uses the global mathematical 
constant 'pi'.


  comp = moose.Compartment('comp')
  comp.diameter = 2.0
  pool = moose.Pool('pool')
  func = moose.Function('f')
  
  # A made-up example to illustrate push, pull vars and constants
  func.c['A'] = 6.022e23   # constant
  func.expr = 'Vm + y0 * n * pi / A'
  
  i_v = func.xindex['Vm']
  i_n = func.xindex['n']
  
  # There should be two x vars, one for `Vm`, the other for `n`
  assert func.x.num == 2 
  
  moose.connect(comp, 'VmOut', func.x[i_v], 'input')
  moose.conncet(pool, 'nOut', func.x[i_n], 'input')
  moose.connect(func, 'requestOut', comp, 'getDiameter')


)#"
    };

    static Dinfo< Function > dinfo;
    static Cinfo functionCinfo("Function",
            Neutral::initCinfo(),
            functionFinfos,
            sizeof(functionFinfos) / sizeof(Finfo*),
            &dinfo,
            doc,
            sizeof(doc)/sizeof(string));
    return &functionCinfo;

}

static const Cinfo * functionCinfo = Function::initCinfo();

Function::Function()
    : valid_(true),
      numVar_(0),
      lastValue_(0.0),
      value_(0.0),
      rate_(0.0),
      mode_(1),
      useTrigger_(false),
      doEvalAtReinit_(false),
      allowUnknownVar_(true),
      t_(0.0),
      independent_("t"),
      stoich_(nullptr),
      parser_(new moose::MooseParser())
{
}

// Careful: This is a critical function. Also since during zombiefication, deep
// copy is expected. Merely copying the parser won't work.
Function& Function::operator=(const Function& rhs)
{
    // protect from self-assignment.
    if( this == &rhs)
        return *this;

    // delete allocated vars, clear parser
    clearAll();

    valid_ = rhs.valid_;
    lastValue_ = rhs.lastValue_;
    value_ = rhs.value_;
    mode_ = rhs.mode_;
    useTrigger_ = rhs.useTrigger_;
    doEvalAtReinit_ = rhs.doEvalAtReinit_;
    allowUnknownVar_ = rhs.allowUnknownVar_;
    t_ = rhs.t_;
    rate_ = rhs.rate_;
    num_xi_ = rhs.num_xi_;

    // Deep copy; create new Variables and constants to link with new parser.
    // Zombification requires it. DO NOT just copy the object/pointer of
    // MooseParser.
    if (rhs.parser_->GetExpr().size() > 0) {
        // Copy the constants
        for (auto cc : rhs.parser_->GetConstants()) {
            parser_->DefineConst(cc.first, cc.second);
        }
        // These are alreay indexed. So its OK to add them by name.
        for (auto *x : rhs.xs_) {
            xs_.push_back(new Variable(x->getName()));
            varIndex_[x->getName()] = xs_.size() - 1;
            parser_->DefineVar(xs_.back()->getName(), xs_.back()->ptr());
        }
        // Add all the Ys now.
        for (unsigned int i = 0; i < rhs.ys_.size(); i++) {
            ys_.push_back(new double(0.0));
            parser_->DefineVar('y' + to_string(i), ys_[i]);
        }
        parser_->DefineVar("t", &t_);
        parser_->SetExpr(rhs.parser_->GetExpr());
    }
    return *this;
}

Function::~Function()
{
    for (auto *x : xs_) {
        delete x;
    }
    for (auto *y : ys_) {
        delete y;
    }
    delete parser_;
}

/* --------------------------------------------------------------------------*/
/**
 * @Synopsis  Assign an expression to the parser. Calls innerSetExpr to do the
 * task.
 *
 * @Param eref
 * @Param expression
 */
/* ----------------------------------------------------------------------------*/
void Function::setExpr(const Eref& eref, const string expression)
{
    string expr = moose::trim(expression);
    if(expr.empty())
        return;
    expr = moose::MooseParser::Reformat(expr);
    if (valid_ && expr == parser_->GetExpr()) {
        MOOSE_WARN("No changes in the expression.");
        return;
    }

    try
    {
        valid_ = innerSetExpr(eref, expr);
    }
    catch (moose::Parser::ParserException &e) {
        clearAll();
        valid_ = false;
        cerr << "Error setting expression on: " << eref.objId().path() << endl;
        cerr << "\tExpression: '" << expr << "'" << endl;
        cerr << e.GetMsg() << endl;
    }
}

/* --------------------------------------------------------------------------*/
/**
 * @Synopsis  Set expression in the parser. This function support two mode:
 * with dynamic lookup and without it. When `dynamicLookup_` is set to true,
 * unknown variables are created at the compile time. Otherwise, an error is
 * raised.
 *
 * @Param eref
 * @Param expr Expression to set.
 * @Param dynamicLookup Whether to allow unknown variables in the expression.
 * (default to true in moose>=4.0.0)
 *
 * @Returns  True if compilation was successful. 
 */
/* ----------------------------------------------------------------------------*/
bool Function::innerSetExpr(const Eref& eref, const string expr)
{
    ASSERT_FALSE(expr.empty(), "Empty expression not allowed here.");

    // NOTE: Don't clear the expression here. Sometime the user extend the
    // expression by calling this function agian. For example:
    //
    // >>> f.expr = 'x0+x2'
    // >>> # connect x0 and x2
    // >>> f.expr += '+ 100+y0'
    // >>> # connect more etc.

    // First, add the xi, yi and t to the symbol table.
    vector<string> vars;
    parser_->ParseVariables(expr, vars);
    vector<string> xs;      // variable names x0, x1, ...
    vector<string> ys;      // variable names y0, y1, ...
    vector<string> others;  // all other variable names
    const regex xpattern("x\\d+");
    const regex ypattern("y\\d+");
    smatch sm;
    for (auto &name : vars) {
        if (regex_search(name, sm, xpattern)) {
            xs.push_back(name);
        }
        else if (regex_search(name, sm, ypattern)) {
            ys.push_back(name);
        }
        else if (name != "t" && !parser_->IsConst(name)) {
            others.push_back(name);
        }
    }
    std::sort(xs.begin(), xs.end());
    std::sort(ys.begin(), ys.end());
    std::sort(others.begin(), others.end());
    // extract the constants from the parser

    // keep the existing variables aside for relocation
    vector<Variable *> old_xs(xs_);
    unsigned int new_xi_count = num_xi_;
    if (!xs.empty()) {
        unsigned int num_xi_new = std::stoul(xs.back().substr(1)) + 1;
        if (num_xi_new > num_xi_) {
            new_xi_count = num_xi_new;
        }
    }
    if (!allowUnknownVar_ && others.size() > 0) {
        cerr << "Warning: allowUnknownVariables is false. These variables will "
                "be ignored: \n";
        for (auto &name : others) {
            cerr << "  " << name << '\n';
        }
        cerr << endl;
        clearVariables();
        return false;
    }
    // collect the known named variables for relocation
    vector<string> known;
    for (unsigned int ii = num_xi_; ii < xs_.size(); ++ii) {
        known.push_back(xs_[ii]->getName());
    }
    // find the variables do not already exist
    vector<string> new_named;
    std::set_difference(others.begin(), others.end(), known.begin(),
                        known.end(), std::back_inserter(new_named));
    unsigned int new_size = new_xi_count + known.size() + new_named.size();
    xs_.resize(new_size);

    // Fill the new xi vars - resize preserves existing entries
    // Add x variables by index ("x0", "x1", etc.). If N is the
    // largest value for ii for variable names "x{ii}", then a total
    // of N Variable objects, named "x0", "x1", ..., "xN" are
    // created. This is true even if some indices are missing in the
    // parameter names.
    for (unsigned int ii = num_xi_; ii < new_xi_count; ++ii) {
        string name = 'x' + to_string(ii);
        xs_[ii] = new Variable(name);
        varIndex_[name] = ii;
        parser_->DefineVar(name, xs_[ii]->ptr());
    }

    // Now re-fill the known named variables
    for (unsigned int ii = 0; ii < old_xs.size() - num_xi_; ++ii) {
        Variable *var = old_xs[ii + num_xi_];
        xs_[ii + new_xi_count] = var;
        varIndex_[var->getName()] = ii + new_xi_count;
        // already defined in symbol table
    }
    num_xi_ = new_xi_count;
    // Now create and append new named variables
    // Add x variable by name (anything but "x{digits}" and "y{digits}").

    for (unsigned int ii = 0; ii < new_named.size(); ++ii) {
        unsigned int idx = num_xi_ + ii;
        xs_[idx] = new Variable(new_named[ii]);
        parser_->DefineVar(new_named[ii], xs_[idx]->ptr());
        varIndex_[new_named[ii]] = idx;
    }
    // Add ys variable (names of the form "y{digits}")
    if (!ys.empty()) {
        unsigned int old_yi_count = ys_.size();
        unsigned num_yi_new = std::stoul(ys.back().substr(1)) + 1;
        if (old_yi_count < num_yi_new) {
            ys_.resize(num_yi_new);
            for (unsigned int ii = old_yi_count; ii < num_yi_new; ++ii) {
                ys_[ii] = new double(0.0);
                parser_->DefineVar('y' + to_string(ii), ys_[ii]);
            }
        }
    }
    if (others.size() > 0 && allowUnknownVar_) {
    }
    parser_->DefineVar("t", &t_);
    return parser_->SetExpr(expr, allowUnknownVar_);
}

string Function::getExpr( const Eref& e ) const
{
    if (!valid_) {
        cerr << __func__ << " Error: " << e.objId().path()
             << "::getExpr() - invalid parser state. Assign a correct "
                "expression."
             << endl;
    }
    return parser_->GetExpr();
}

void Function::setMode(unsigned int mode)
{
    mode_ = mode;
}

unsigned int Function::getMode() const
{
    return mode_;
}

void Function::setUseTrigger(bool useTrigger )
{
    useTrigger_ = useTrigger;
}

bool Function::getUseTrigger() const
{
    return useTrigger_;
}

void Function::setDoEvalAtReinit(bool doEvalAtReinit )
{
    doEvalAtReinit_ = doEvalAtReinit;
}

bool Function::getDoEvalAtReinit() const
{
    return doEvalAtReinit_;
}

void Function::setAllowUnknownVariable(bool value )
{
    allowUnknownVar_ = value;
}

bool Function::getAllowUnknowVariable() const
{
    return allowUnknownVar_;
}


double Function::getValue() const
{
    // return parser_->Eval( );
    return value_;
}

double Function::getEval() const
{
    return parser_->Eval( );
}


double Function::getRate() const
{
    if (!valid_)
        cerr << __func__ << "Error: invalid state" << endl;
    return rate_;
}

void Function::setIndependent(string var)
{
    independent_ = var;
}

string Function::getIndependent() const
{
    return independent_;
}

vector< double > Function::getY() const
{
    vector < double > ret(ys_.size());
    for (unsigned int ii = 0; ii < ret.size(); ++ii)
        ret[ii] = *ys_[ii];
    return ret;
}

double Function::getDerivative() const
{
    double value = 0.0;
    if (!valid_) {
        cerr << __func__ << "Error:  invalid state" << endl;
    }
    else {
        value = parser_->Derivative(independent_);
    }
    return value;
}

void Function::setNumVar(const unsigned int num)
{
    // Deprecated: numVar has no effect. MOOSE infer number of variables
    // from the expression.
    cerr << "Function::setNumVar is deprecated. Function object infers number of variables from the expression." << endl;
}

unsigned int Function::getNumVar() const
{
    return xs_.size();
}

void Function::setVar(unsigned int index, double value)
{
    if(index < xs_.size())
    {
        xs_[index]->setValue(value);
        return;
    }
    MOOSE_WARN("Function: index " << index << " out of bounds.");
}

Variable* Function::getX(unsigned int ii) 
{
    static Variable dummy("DUMMY");
    if(ii >= xs_.size())
    {
        //MOOSE_WARN("No active variable for index " << ii);
        return &dummy;
    }
    return xs_[ii];
}

void Function::setConst(string name, double value)
{
    parser_->DefineConst(name.c_str(), value);
}

double Function::getConst(string name) const
{
    return parser_->GetConst(name);
}

void Function::setVarIndex(string name, unsigned int val)
{
    cerr << "Function::setVarIndex : This should not be used." << endl;
}

unsigned int Function::getVarIndex(string name) const
{
    if(varIndex_.find(name) == varIndex_.end())
        return numeric_limits<unsigned int>::max();
    return varIndex_.at(name);
}

bool Function::symbolExists(const string& name) const
{
    return varIndex_.find(name) != varIndex_.end();
}

void Function::process(const Eref &e, ProcPtr p)
{
    if(! valid_)
        return;

    // Update values of incoming variables.
    vector<double> databuf;
    requestOut()->send(e, &databuf);
    for (unsigned int ii = 0; (ii < databuf.size()) && (ii < ys_.size()); ++ii)
        *ys_[ii] = databuf[ii];

    t_ = p->currTime;
    value_ = getEval();
    rate_ = (value_ - lastValue_) / p->dt;

    if (useTrigger_ && value_ < TriggerThreshold) {
        lastValue_ = value_;
        return;
    }

    switch (mode_)
    {
    case 1:
    {
        valueOut()->send(e, value_);
        lastValue_ = value_;
	break;
    }
    case 2:
    {
        derivativeOut()->send(e, getDerivative());
        lastValue_ = value_;
        break;
    }
    case 3:
    {
        rateOut()->send(e, rate_);
        lastValue_ = value_;
	break;
    }
    default:
    {
        valueOut()->send(e, value_);
        derivativeOut()->send(e, getDerivative());
        rateOut()->send(e, rate_);
        lastValue_ = value_;	
    }
    }
}

void Function::reinit(const Eref &e, ProcPtr p)
{
    if (! (valid_ || parser_->GetExpr().empty()))
    {
        MOOSE_WARN("Error: " << e.objId().path() << "::reinit() - invalid parser state"
                << endl << " Expr: '" << parser_->GetExpr() << "'.");
        return;
    }

    t_ = p->currTime;

    if (doEvalAtReinit_){
        lastValue_ = value_ = getEval();
    }
    else
        lastValue_ = value_ = 0.0;

    rate_ = 0.0;

    switch (mode_){
    case 1:
    {
        valueOut()->send(e, value_);
        break;
    }
    case 2:
    {
        derivativeOut()->send(e, 0.0);
        break;
    }
    case 3:
    {
        rateOut()->send(e, rate_);
        break;
    }
    default:
    {
        valueOut()->send(e, value_);
        derivativeOut()->send(e, 0.0);
        rateOut()->send(e, rate_);
        break;
    }
    }
}


void Function::clearVariables()
{
    for (auto *xx : xs_) {
        delete xx;
    }
    for (auto *yy : ys_) {
        delete yy;
    }
    num_xi_ = 0;
    xs_.clear();
    ys_.clear();
    varIndex_.clear();
    parser_->ClearVariables();
}
void Function::clearAll()
{
    clearVariables();
    // moose::Parser::varmap_type vars = parser_->GetConstants();
    parser_->ClearAll();
    // for (auto var : vars) {
    //     parser_->DefineConst(var.first, var.second);
    // }
}

void Function::setSolver( const Eref& e, ObjId newStoich )
{

	if ( newStoich.bad() ) {
		cout << "Warning: Function::setSolver: Bad Stoich " <<
				e.id().path() << endl;
		return;
	}
	if ( newStoich == ObjId() ) { // Unsetting stoich.
		if ( stoich_ != 0 ) {
			auto x = reinterpret_cast< Stoich* >( stoich_ );
			x->notifyRemoveFunc( e );
		}
		stoich_ = 0;
		return;
	}
	if ( !newStoich.element()->cinfo()->isA( "Stoich" ) ) {
		cout << "Warning: Function::setSolver: object " << newStoich.path() << "is not a Stoich for " << e.id().path() << endl;
		return;
	}
	void* stoichPtr = reinterpret_cast< void* >( newStoich.eref().data( ) );
	if ( stoich_ == stoichPtr )
		return;

	if ( stoich_ != 0 ) {
		auto x = reinterpret_cast< Stoich* >( stoich_ );
		x->notifyRemoveFunc( e );
	}
	
	stoich_ = stoichPtr;
	// stoich_->installFunction(;) This is done within the stoich because
	// there are multiple options for where a function may be placed.
	
}
