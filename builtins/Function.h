// Function.h ---
// Description: moose.Function class.
// Author: Subhasis Ray
// Maintainer: Dilawar Singh
// Version: See git logs.

#ifndef FUNCTIONH_
#define FUNCTIONH_
#include <memory>

class Variable;
class Eref;
class Cinfo;

namespace moose {
class MooseParser;
};

// Symbol types.
enum VarType { XVAR_INDEX, XVAR_NAMED, YVAR, TVAR, CONSTVAR };

class Function {
public:
    static const int VARMAX;
    Function();

    // Destructor.
    ~Function();

    // copy operator.
    Function& operator=(const Function& rhs);

    static const Cinfo* initCinfo();

    void setExpr(const Eref& e, const string expr);
    bool innerSetExpr(const Eref& e, const string expr);

    string getExpr(const Eref& e) const;

    // get a list of variable identifiers.
    vector<string> getVars() const;
    void setVarValues(vector<string> vars,
                      vector<double> vals);  // subha: where is this defined?

    /// set the value of `index`-th variable
    void setVar(unsigned int index, double value);

    Variable* getX(unsigned int ii);

    // get function eval result
    double getValue() const;
    double getEval() const;
    double getRate() const;

    // get/set operation mode
    void setMode(unsigned int mode);
    unsigned int getMode() const;

    // set/get flag to use trigger mode.
    void setUseTrigger(bool useTrigger);
    bool getUseTrigger() const;

    // set/get flag to do function evaluation at reinit
    void setDoEvalAtReinit(bool doEvalAtReinit);
    bool getDoEvalAtReinit() const;

    void setAllowUnknownVariable(bool value);
    bool getAllowUnknowVariable() const;

    void setNumVar(unsigned int num);
    unsigned int getNumVar() const;

    void setConst(string name, double value);
    double getConst(string name) const;

    void setVarIndex(string name, unsigned int val);
    unsigned int getVarIndex(string name) const;

    void setIndependent(string index);
    string getIndependent() const;

    vector<double> getY() const;

    double getDerivative() const;
    // unsigned int addVar();
    /* void dropVar(unsigned int msgLookup); */

    void process(const Eref& e, ProcPtr p);
    void reinit(const Eref& e, ProcPtr p);

    // // This is also used as callback.
    // void addVariable(const string& name);

    // // Add unknown variable.
    // void callbackAddSymbol(const string& name);

    /**
       Check of symbol named name exists in the Function.

       @param name name of symbol.
       @return true if name exists in symbol table, false otherwise.
    */
    bool symbolExists(const string& name) const;

    /**
       Add ys variable (names of the form "y{digits}")

       @param name set of strings of the form "y{digits}"
    */
    void addYs(vector<string>& names);

    // VarType getVarType(const string& name) const;
  void clearVariables();
    void clearAll();
    void setSolver(const Eref& e, ObjId stoich);

protected:
    bool valid_{true};
    unsigned int numVar_{0};
    double lastValue_{0.0};
    double value_{0.0};
    double rate_{0.0};
    unsigned int mode_{1};
    bool useTrigger_{false};
    bool doEvalAtReinit_{true};
    bool allowUnknownVar_{true};

    double t_{0.0};         // local storage for current time
    string independent_{};  // To take derivative.

    // this stores variables received via incoming messages, identifiers of
    // the form x{i} are included in this
    vector<Variable*> xs_{};

    /// Maps x variable names to their index in vector of x's (xs_).
    map<string, unsigned int> varIndex_{};

    /// last index of the x{i} vars - to track boundary of indexed and named
    /// variables
    unsigned int num_xi_{0};

    // this stores variable values pulled by sending request. identifiers of
    // the form y{i} are included in this
    vector<double*> ys_{};
    map<string, shared_ptr<double>> consts_;

    // Used by kinetic solvers when this is zombified.
    void* stoich_{};

    // pointer to the MooseParser
    moose::MooseParser* parser_{};
};

#endif /* end of include guard: FUNCTIONH_ */
