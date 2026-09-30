/**********************************************************************
 ** This program is part of 'MOOSE', the
 ** Messaging Object Oriented Simulation Environment.
 **           Copyright (C) 2003-2007 Upinder S. Bhalla. and NCBS
 ** It is made available under the terms of the
 ** GNU General Public License version 3
 ** See the file LICENSE in the MOOSE source root for the full notice.
 **********************************************************************/

#include "../basecode/header.h"
#include "../basecode/ElementValueFinfo.h"
#include "HHGateF.h"

const Cinfo* HHGateF::initCinfo()
{
    ///////////////////////////////////////////////////////
    // Field definitions.
    ///////////////////////////////////////////////////////
    static ReadOnlyLookupValueFinfo<HHGateF, double, double> A(
        "A",
        "lookupA: Compute the A gate value from a double. "
        "This is done by evaluating the expressions for alpha/beta"
        " or tau/inf.",
        &HHGateF::lookupA);
    static ReadOnlyLookupValueFinfo<HHGateF, double, double> B(
        "B",
        "lookupB: Look up the B gate value from a double."
        "This is done by evaluating the expressions for alpha/beta"
        " or tau/inf.",
        &HHGateF::lookupB);

    static ElementValueFinfo<HHGateF, string> alpha(
        "alphaExpr",
        "Expression for voltage-dependent rates, forward rate `alpha`. "
        "This requires the expression for `beta` to be defined as well.\n"
        "The syntax follows exprtk, with variable name `v` for input variable"
        " (which can be voltage or concentration depending on message "
        "connection in case of HHGateF which takes only one input).\n"
        "For HHGateF2D which depends on two inputs, the variable names are "
        "`v` for voltage, and `c` for concentration.\n"
        "And additional set of variable names are available for cases "
        "that require intermediate calculations. These are:\n"
        " `alpha` for forward rate,\n"
        " `beta` for backward rate,\n"
        " `tau` for time constant, and\n"
        " `inf` for steady state open fraction\n"
        "as per Hodgkin and Huxley's formulation.\n"
        "This is useful for conditional values for these parameters:\n"
        "Example:\n"
        "~(alpha:=0.3 * exp(-80 * (v -(-46e-3))) + 3.5, alpha < 3.8? 3.8: "
        "alpha)\n"
        " first computes `alpha` by the first formula, and returns it "
        "only if the computed value is >= 3.8, otherwise it returns 3.8.",
        &HHGateF::setAlpha, &HHGateF::getAlpha);

    static ElementValueFinfo<HHGateF, string> beta(
        "betaExpr",
        "Expression for voltage-dependent rates, backward rate `beta`. "
        "This requires the expression for `alpha` to be defined as well. See"
        " documentation on `alpha` for details on predefined variable names.",
        &HHGateF::setBeta, &HHGateF::getBeta);

    static ElementValueFinfo<HHGateF, string> tau(
        "tauExpr",
        "Expression for voltage-dependent rates, time constant `tau`. "
        "This requires the expression for `inf` to be defined as well.\n"
        "See documentation for `alpha` for details on predefined variable"
        " names. Example of a complex conditional expression (based on "
        "Maex and De Schutter 1998):\n"
        "~(alpha := 750 * exp(81 * (v - (-39e-3))), "
        "beta := 750 * exp(-66 * (v - (-39e-3))), "
        "tau := 1/(alpha + beta), tau < 1e-5? 1e-5)"
        "\nThis computes alpha and beta and then from those, tau. "
        "However if the calculated value of tau falls under "
        "1e-5, it makes the value 1e-5.",
        &HHGateF::setTau, &HHGateF::getTau);

    static ElementValueFinfo<HHGateF, string> inf(
        "infExpr",
        "Expression for voltage-dependent rates, steady state open fraction "
        "`inf`. "
        "This requires the expression for `tau` to be defined as well.",
        &HHGateF::setInf, &HHGateF::getInf);

    ///////////////////////////////////////////////////////
    // DestFinfos
    ///////////////////////////////////////////////////////
    static Finfo* HHGateFFinfos[] = {
        &A,      // ReadOnlyLookupValue
        &B,      // ReadOnlyLookupValue
        &alpha,  // Value
        &beta,   // Value
        &tau,    // Value
        &inf,    // Value
    };

    static string doc[] = {
        "Name",
        "HHGateF",
        "Author",
        "Subhasis Ray, 2025, CHINTA",
        "Description",
        "Gating component of Hodkgin-Huxley type channels, equivalent to the "
        "m and h terms on the Na squid channel and the n term on K. "
        "This takes the voltage and state variable from the channel, "
        "computes the new value of the state variable and a scaling, "
        "depending on gate power, for the conductance. As opposed to HHGate, "
        "which uses lookup tables for speed, this evaluates explicit "
        "expressions for accuracy. This is a single variable gate, either "
        "voltage or concentration. So the expression also allows only one "
        "indpendent variable, which is assumed `v`. See the documentation of "
        "``Function`` class for details on the praser.",
    };

    static Dinfo<HHGateF> dinfo;
    static Cinfo HHGateFCinfo("HHGateF", Neutral::initCinfo(), HHGateFFinfos,
                              sizeof(HHGateFFinfos) / sizeof(Finfo*), &dinfo,
                              doc, sizeof(doc) / sizeof(string));

    return &HHGateFCinfo;
}

static const Cinfo* hhGateCinfo = HHGateF::initCinfo();
///////////////////////////////////////////////////
// Core class functions
///////////////////////////////////////////////////
HHGateF::HHGateF() : HHGateBase(0, 0)
{
    cerr << "Warning: HHGateF::HHGateF(): this should never be called" << endl;
}

HHGateF::HHGateF(Id originalChanId, Id originalGateId)
    : HHGateBase(originalChanId, originalGateId)

{
    symTab_.add_variable("v", v_);
    symTab_.add_variable("alpha", alphav_);
    symTab_.add_variable("beta", betav_);
    symTab_.add_variable("tau", tauv_);
    symTab_.add_variable("inf", infv_);
    symTab_.add_constants();
    alpha_.register_symbol_table(symTab_);
    beta_.register_symbol_table(symTab_);
}

HHGateF& HHGateF::operator=(const HHGateF& rhs)
{
    // protect from self-assignment.
    if(this == &rhs)
        return *this;

    v_ = rhs.v_;
    symTab_.add_variable("v", v_);
    symTab_.add_variable("alpha", alphav_);
    symTab_.add_variable("beta", betav_);
    symTab_.add_variable("tau", tauv_);
    symTab_.add_variable("inf", infv_);
    symTab_.add_constants();
    alpha_.register_symbol_table(symTab_);
    beta_.register_symbol_table(symTab_);
    alphaExpr_ = rhs.alphaExpr_;
    betaExpr_ = rhs.betaExpr_;
    parser_.compile(alphaExpr_, alpha_);
    parser_.compile(betaExpr_, beta_);
    tauInf_ = rhs.tauInf_;
    return *this;
}

///////////////////////////////////////////////////
// Field function definitions
///////////////////////////////////////////////////

double HHGateF::lookupA(double v) const
{
    // TODO: check for divide by zero?
    v_ = v;
    return tauInf_ ? beta_.value() / alpha_.value() : alpha_.value();
}

double HHGateF::lookupB(double v) const
{
    // TODO: check for divide by zero?
    v_ = v;
    return tauInf_ ? 1.0 / alpha_.value() : alpha_.value() + beta_.value();
}

void HHGateF::lookupBoth(double v, double* A, double* B) const
{
    *A = lookupA(v);
    *B = lookupB(v);
    // cerr << "# HHGateF::lookupBoth: v=" << v << ", A=" << *A << ", B="<< *B
    // << endl;
}

void HHGateF::setAlpha(const Eref& e, const string expr)
{
    if(checkOriginal(e.id(), "alpha")) {
        if(!parser_.compile(expr, alpha_)) {
            cerr << "Error: Element: " << e.objId().path() << ": HHGateF::setAlpha: cannot compile expression!\n"
                 << parser_.error() << endl;
            return;
        }
        tauInf_ = false;
        alphaExpr_ = expr;
        parser_.compile(alphaExpr_, alpha_);
    }
}

string HHGateF::getAlpha(const Eref& e) const
{
    return tauInf_ ? "" : alphaExpr_;
}

void HHGateF::setBeta(const Eref& e, const string expr)
{
    if(checkOriginal(e.id(), "beta")) {
        if(!parser_.compile(expr, beta_)) {
            cerr << "Error: Element: " << e.objId().path() << ": HHGateF::setBeta: cannot compile expression!\n"		 
                 << parser_.error() << endl;
            return;
        }
        tauInf_ = false;
        betaExpr_ = expr;
        parser_.compile(betaExpr_, beta_);
    }
}

string HHGateF::getBeta(const Eref& e) const
{
    return tauInf_ ? "" : betaExpr_;
}

void HHGateF::setTau(const Eref& e, const string expr)
{
    if(checkOriginal(e.id(), "alpha")) {
        if(!parser_.compile(expr, alpha_)) {
            cerr << "Error: Element: " << e.objId().path() << ": HHGateF::setTau: cannot compile expression!\n"
                 << parser_.error() << endl;
            return;
        }
        tauInf_ = true;
        alphaExpr_ = expr;
        parser_.compile(alphaExpr_, alpha_);
    }
}

string HHGateF::getTau(const Eref& e) const
{
    return tauInf_ ? alphaExpr_ : "";
}

void HHGateF::setInf(const Eref& e, const string expr)
{
    if(checkOriginal(e.id(), "beta")) {
        if(!parser_.compile(expr, beta_)) {
            cerr << "Error: Element: " << e.objId().path() << ": HHGateF::setInf: cannot compile expression!\n"
                 << parser_.error() << endl;
            return;
        }
        tauInf_ = true;
        betaExpr_ = expr;
        parser_.compile(betaExpr_, beta_);
    }
}

string HHGateF::getInf(const Eref& e) const
{
    return tauInf_ ? betaExpr_ : "";
}
