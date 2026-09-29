/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment.
**           Copyright (C) 2003-2007 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU General Public License version 3
** See the file LICENSE in the MOOSE source root for the full notice.
**********************************************************************/

#include <cmath>

#include "exprtk.hpp"

#include "../basecode/header.h"
#include "../basecode/ElementValueFinfo.h"
#include "../builtins/Interpol2D.h"
#include "../utility/strutil.h"
#include "HHGateBase.h"
#include "HHGate2D.h"

static const double SINGULARITY = 1.0e-6;

const Cinfo* HHGate2D::initCinfo()
{
    ///////////////////////////////////////////////////////
    // Field definitions.
    ///////////////////////////////////////////////////////
    static ReadOnlyLookupValueFinfo<HHGate2D, vector<double>, double> A(
        "A",
        "lookupA: Look up the A gate value from two doubles, passed"
        "in as a vector. Uses linear interpolation in the 2D table"
        "The range of the lookup doubles is predefined based on "
        "knowledge of voltage or conc ranges, and the granularity "
        "is specified by the xmin, xmax, and dx field, and their "
        "y-axis counterparts.",
        &HHGate2D::lookupA);
    static ReadOnlyLookupValueFinfo<HHGate2D, vector<double>, double> B(
        "B", "lookupB: Look up B gate value from two doubles in a vector.",
        &HHGate2D::lookupB);

    static ElementValueFinfo<HHGate2D, vector<vector<double>>> tableA(
        "tableA", "Table of A entries", &HHGate2D::setTableA,
        &HHGate2D::getTableA);

    static ElementValueFinfo<HHGate2D, vector<vector<double>>> tableB(
        "tableB", "Table of B entries", &HHGate2D::setTableB,
        &HHGate2D::getTableB);

    static ElementValueFinfo<HHGate2D, string> alphaExpr(
        "alphaExpr",
        "Explicit expression for computing `alpha`."
        " For using this, `betaExpr` must be set as well.\n"
        " SYNTAX: The expression evaluation uses exprtk syntax,"
        " with predefined variables `alpha`, `beta`, `tau`, `inf`, `v` and"
        " `c`. `v` is bound to whichever input the parent channel's"
        " `Xindex`/`Yindex`/`Zindex` maps to the first dependency (e.g."
        " voltage for `VOLT_C1_INDEX` or `VOLT_C2_INDEX`, or the first"
        " concentration input for `C1_C2_INDEX`); `c` is bound to the"
        " second dependency (e.g. a concentration input for"
        " `VOLT_C1_INDEX`/`VOLT_C2_INDEX`, or the second concentration"
        " input for `C1_C2_INDEX`). See `HHChannel2D::Xindex` for the"
        " full list of dependency modes. `c1` and `c2` are aliases for"
        " `v` and `c` respectively - convenient names to use instead"
        " when both axes are concentrations, as in `C1_C2_INDEX`. The"
        " others (`alpha`, `beta`, `tau`, `inf`) can be used as local"
        " variables for intermediate computations, exactly as in"
        " `HHGate::alphaExpr`.",
        &HHGate2D::setAlphaExpr, &HHGate2D::getAlphaExpr);

    static ElementValueFinfo<HHGate2D, string> betaExpr(
        "betaExpr",
        "Explicit expression for computing `beta`."
        " For using this, `alphaExpr` must be set as well."
        " See `alphaExpr` and `HHChannel2D::Xindex` documentation.",
        &HHGate2D::setBetaExpr, &HHGate2D::getBetaExpr);

    static ElementValueFinfo<HHGate2D, string> tauExpr(
        "tauExpr",
        "Explicit expression for computing `tau`."
        " For using this, `infExpr` must be set as well."
        " See `alphaExpr` and `HHChannel2D::Xindex` documentation.",
        &HHGate2D::setTauExpr, &HHGate2D::getTauExpr);

    static ElementValueFinfo<HHGate2D, string> infExpr(
        "infExpr",
        "Explicit expression for computing `inf`."
        " When using this, `tauExpr` must be set as well."
        " See `alphaExpr` and `HHChannel2D::Xindex` documentation.",
        &HHGate2D::setInfExpr, &HHGate2D::getInfExpr);

    static ReadOnlyValueFinfo<HHGate2D, int> form(
        "form",
        "Form of the gate specification:\n 0 for old-style tables,\n"
        " 1 for expression string in alpha-beta form, and\n"
        " 2 for expression string in tau-inf form.\n"
        "This is set automatically when the user assigns the gate"
        " tables or the expressions.",
        &HHGate2D::getForm);

    static ElementValueFinfo<HHGate2D, double> xmin(
        "xmin", "Minimum x (first dimension) for lookup (see `HHChannel2D.Xindex` for documentation on how variables are assigned to lookup dimensions)", &HHGate2D::setXmin,
        &HHGate2D::getXmin);

    static ElementValueFinfo<HHGate2D, double> xmax(
        "xmax", "Maximum x (first dimension) for lookup (see `HHChannel2D.Xindex` for documentation on how variables are assigned to lookup dimensions)", &HHGate2D::setXmax,
        &HHGate2D::getXmax);

    static ElementValueFinfo<HHGate2D, unsigned int> xdivs(
        "xdivs", "Divisions along first dimension for lookup (see `HHChannel2D.Xindex` for documentation on how variables are assigned to lookup dimensions)",
        &HHGate2D::setXdivs, &HHGate2D::getXdivs);

    static ElementValueFinfo<HHGate2D, double> ymin(
        "ymin", "Minimum y (second dimension) for lookup (see `HHChannel2D.Xindex` for documentation on how variables are assigned to lookup dimensions)", &HHGate2D::setYmin,
        &HHGate2D::getYmin);

    static ElementValueFinfo<HHGate2D, double> ymax(
        "ymax", "Maximum y (second dimension) for lookup (see `HHChannel2D.Xindex` for documentation on how variables are assigned to lookup dimensions)", &HHGate2D::setYmax,
        &HHGate2D::getYmax);

    static ElementValueFinfo<HHGate2D, unsigned int> ydivs(
        "ydivs", "Divisions along second dimension for lookup (see `HHChannel2D.Xindex` for documentation on how variables are assigned to lookup dimensions)",
        &HHGate2D::setYdivs, &HHGate2D::getYdivs);

    ///////////////////////////////////////////////////////
    // DestFinfos
    ///////////////////////////////////////////////////////
    static DestFinfo fillFromExpr(
        "fillFromExpr",
        "If the gating variables are specified as string expressions"
        " (alphaExpr/betaExpr/tauExpr/infExpr), then fill up the"
        " tables by evaluating the expressions over the (v, c) grid"
        " defined by xmin/xmax/xdivs and ymin/ymax/ydivs.",
        new EpFunc0<HHGate2D>(&HHGate2D::fillFromExpr));

    static Finfo* HHGate2DFinfos[] = {
        &A,          // ReadOnlyLookupValue
        &B,          // ReadOnlyLookupValue
        &tableA,     // ElementValue
        &tableB,     // ElementValue
        &alphaExpr,  // ElementValue
        &betaExpr,   // ElementValue
        &tauExpr,    // ElementValue
        &infExpr,    // ElementValue
        &form,       // ReadOnlyValue
        &xmin,   &xmax, &xdivs, &ymin, &ymax, &ydivs,
        &fillFromExpr,  // Dest
    };

    static string doc[] = {
        "Name",
        "HHGate2D",
        "Author",
        "Niraj Dudani, 2009, NCBS. Updated by Subhasis Ray, 2014, 2024 NCBS.",
        "Description",
        "HHGate2D: Gate for Hodkgin-Huxley type channels, equivalent to the "
        "m and h terms on the Na squid channel and the n term on K. "
        "This takes the voltage and state variable from the channel, "
        "computes the new value of the state variable and a scaling, "
        "depending on gate power, for the conductance. These two "
        "terms are sent right back in a message to the channel.",
    };

    static Dinfo<HHGate2D> dinfo;
    static Cinfo HHGate2DCinfo("HHGate2D", Neutral::initCinfo(), HHGate2DFinfos,
                               sizeof(HHGate2DFinfos) / sizeof(Finfo*), &dinfo,
                               doc, sizeof(doc) / sizeof(string));

    return &HHGate2DCinfo;
}

static const Cinfo* hhGate2DCinfo = HHGate2D::initCinfo();
///////////////////////////////////////////////////
HHGate2D::HHGate2D()
    : originalChanId_(0),
      originalGateId_(0),
      form_(0)
{
    ;
}

HHGate2D::HHGate2D(Id originalChanId, Id originalGateId)
    : HHGateBase(originalChanId, originalGateId),
      form_(0)
{
    ;
}

///////////////////////////////////////////////////
// Field function definitions
///////////////////////////////////////////////////
double HHGate2D::lookupA(vector<double> v) const
{
    if(v.size() < 2) {
        cerr << "Error: HHGate2D::getAValue: 2 real numbers needed to lookup "
                "2D table.\n";
        return 0.0;
    }

    if(v.size() > 2) {
        cerr << "Error: HHGate2D::getAValue: Only 2 real numbers needed to "
                "lookup 2D table. "
                "Using only first 2.\n";
    }

    return A_.innerLookup(v[0], v[1]);
}

double HHGate2D::lookupB(vector<double> v) const
{
    if(v.size() < 2) {
        cerr << "Error: HHGate2D::getAValue: 2 real numbers needed to lookup "
                "2D table.\n";
        return 0.0;
    }

    if(v.size() > 2) {
        cerr << "Error: HHGate2D::getAValue: Only 2 real numbers needed to "
                "lookup 2D table. "
                "Using only first 2.\n";
    }

    return B_.innerLookup(v[0], v[1]);
}

void HHGate2D::lookupBoth(double v, double c, double* A, double* B) const
{
    *A = A_.innerLookup(v, c);
    *B = B_.innerLookup(v, c);
}

///////////////////////////////////////////////////
// Access functions for Interpols
///////////////////////////////////////////////////

vector<vector<double>> HHGate2D::getTableA(const Eref& e) const
{
    return A_.getTableVector();
}

void HHGate2D::setTableA(const Eref& e, vector<vector<double>> value)
{
    A_.setTableVector(value);
}

vector<vector<double>> HHGate2D::getTableB(const Eref& e) const
{
    return B_.getTableVector();
}

void HHGate2D::setTableB(const Eref& e, vector<vector<double>> value)
{
    B_.setTableVector(value);
}

///////////////////////////////////////////////////
// Functions to check if this is original or copy
///////////////////////////////////////////////////
bool HHGate2D::isOriginalChannel(Id id) const
{
    return (id == originalChanId_);
}

bool HHGate2D::isOriginalGate(Id id) const
{
    return (id == originalGateId_);
}

Id HHGate2D::originalChannelId() const
{
    return originalChanId_;
}


/// Set/get expression for alpha
void HHGate2D::setAlphaExpr(const Eref& e, string expr)
{
    if(checkOriginal(e.id(), "alphaExpr")) {
        form_ = 1;
        alphaExpr_ = expr;
    }
}

string HHGate2D::getAlphaExpr(const Eref& e) const
{
    return form_ == 1 ? alphaExpr_ : "";
}

/// Set/get expression for beta
void HHGate2D::setBetaExpr(const Eref& e, string expr)
{
    if(checkOriginal(e.id(), "betaExpr")) {
        form_ = 1;
        betaExpr_ = expr;
    }
}

string HHGate2D::getBetaExpr(const Eref& e) const
{
    return form_ == 1 ? betaExpr_ : "";
}

/// Set/get expression for tau
void HHGate2D::setTauExpr(const Eref& e, string expr)
{
    if(checkOriginal(e.id(), "tauExpr")) {
        form_ = 2;
        alphaExpr_ = expr;
    }
}

string HHGate2D::getTauExpr(const Eref& e) const
{
    return form_ == 2 ? alphaExpr_ : "";
}

/// Set/get expression for inf
void HHGate2D::setInfExpr(const Eref& e, string expr)
{
    if(checkOriginal(e.id(), "infExpr")) {
        form_ = 2;
        betaExpr_ = expr;
    }
}

string HHGate2D::getInfExpr(const Eref& e) const
{
    return form_ == 2 ? betaExpr_ : "";
}

int HHGate2D::getForm() const
{
    return form_;
}

/// Fill the tables by evaluating expressions
void HHGate2D::fillFromExpr(const Eref& e)
{
    if(form_ == 0) {
        return;
    }
    exprtk::symbol_table<double> symTab_;
    exprtk::expression<double> alpha_;
    exprtk::expression<double> beta_;
    exprtk::parser<double> parser_;
    double v_ = 0.0;
    double c_ = 0.0;
    // Add extra variables to allow intermediate expressions for cases
    // where there is conditional on alpha/beta or tau/inf values
    double a_ = 0.0;
    double b_ = 0.0;
    double tau_ = 0.0;
    double inf_ = 0.0;
    symTab_.add_variable("v", v_);
    symTab_.add_variable("c", c_);
    // Aliases for C1_C2_INDEX, where both axes are concentrations and
    // naming them `v`/`c` is misleading: `c1` is the same value as `v`
    // (the first/x axis), `c2` the same as `c` (the second/y axis).
    symTab_.add_variable("c1", v_);
    symTab_.add_variable("c2", c_);
    symTab_.add_variable("alpha", a_);
    symTab_.add_variable("beta", b_);
    symTab_.add_variable("tau", tau_);
    symTab_.add_variable("inf", inf_);
    symTab_.add_constants();
    alpha_.register_symbol_table(symTab_);
    beta_.register_symbol_table(symTab_);

    if(moose::trim(alphaExpr_).length() == 0) {
        cerr << "Error: Element: " << e.objId().path()
             << ": HHGate2D::fillFromExpr: empty expression for A" << endl;
        return;
    }
    if(!parser_.compile(alphaExpr_, alpha_)) {
        cerr << "Error: Element: " << e.objId().path()
             << ": HHGate2D::fillFromExpr: cannot compile expression!\n"
             << alphaExpr_ << endl
             << parser_.error() << endl;
        return;
    }
    if(moose::trim(betaExpr_).length() == 0) {
        cerr << "Error: Element: " << e.objId().path()
             << ": HHGate2D::fillFromExpr: empty expression for B" << endl;
        return;
    }
    if(!parser_.compile(betaExpr_, beta_)) {
        cerr << "Error: Element: " << e.objId().path()
             << ": HHGate2D::fillFromExpr: cannot compile expression!\n"
             << betaExpr_ << endl
             << parser_.error() << endl;
        return;
    }

    double xmin = A_.getXmin();
    double xmax = A_.getXmax();
    double ymin = A_.getYmin();
    double ymax = A_.getYmax();
    unsigned int xdivs = A_.getXdivs();
    unsigned int ydivs = A_.getYdivs();
    if((xmax == 1) && (xmin == 0)) {
        cout << "Warning: " << e.objId().path()
             << ": HHGate2D::fillFromExpr: `xmin` and `xmax` have default"
                " values. Did you forget to set them?"
             << endl;
    }
    if((ymax == 1) && (ymin == 0)) {
        cout << "Warning: " << e.objId().path()
             << ": HHGate2D::fillFromExpr: `ymin` and `ymax` have default"
                " values. Did you forget to set them?"
             << endl;
    }
    if(xdivs < 1) {
        cerr << "Error: Element: " << e.objId().path()
             << ": HHGate2D::fillFromExpr: xdivs must be >= 1"
             << endl;
        return;
    }

    double dv = (xmax - xmin) / xdivs;
    double dc = ydivs > 0? (ymax - ymin) / ydivs: 0.0;
    // `v` (the x/first axis) and `c` (the y/second axis) are always named
    // this way in the expression, regardless of which physical signal the
    // parent HHChannel2D's Xindex/Yindex/Zindex binds to each axis - see
    // the `Xindex` documentation on HHChannel2D.
    for(unsigned int ii = 0; ii <= xdivs; ++ii) {
        v_ = xmin + ii * dv;
        // `prev*` carry the last valid value forward across a singularity,
        // reset at the start of each row so the carry-forward runs along
        // the c/second-axis sweep for a fixed v.
        double prevA{0}, prevB{0};
        for(unsigned int jj = 0; jj <= ydivs; ++jj) {
            c_ = ymin + jj * dc;
            double a_{alpha_.value()}, b_{beta_.value()};
            // Check for nan
            if(a_ != a_) {
                a_ = prevA;
            }
            if(b_ != b_) {
                b_ = prevB;
            }
            if(form_ == 1) {  // alpha/beta
                b_ += a_;     // B = alpha + beta
                double bval = fabs(b_) < SINGULARITY ? SINGULARITY : b_;
                A_.setTableValue({ii, jj}, a_);
                B_.setTableValue({ii, jj}, bval);
                prevA = a_;
                prevB = bval - a_;
            }
            else {  // form = 2, tau/inf
                if(fabs(a_) <= SINGULARITY) {
                    a_ = prevA;
                    b_ = prevB;
                    B_.setTableValue({ii, jj}, prevA > 0 ? 1 / prevA : 0.0);
                    A_.setTableValue({ii, jj}, prevA > 0 ? prevB / prevA : 0.0);
                }
                else {
                    B_.setTableValue({ii, jj}, 1 / a_);
                    A_.setTableValue({ii, jj}, b_ / a_);
                    prevA = a_;
                    prevB = b_;
                }
            }
        }
    }
}


double HHGate2D::getXmin(const Eref& e) const
{
    return A_.getXmin();
}

void HHGate2D::setXmin(const Eref& e, double value)
{
    A_.setXmin(value);
    B_.setXmin(value);
}

double HHGate2D::getXmax(const Eref& e) const
{
    return A_.getXmax();
}

void HHGate2D::setXmax(const Eref& e, double value)
{
    A_.setXmax(value);
    B_.setXmax(value);
}

unsigned int HHGate2D::getXdivs(const Eref& e) const
{
    return A_.getXdivs();
}

void HHGate2D::setXdivs(const Eref& e, unsigned int value)
{
    A_.setXdivs(value);
    B_.setXdivs(value);
}

double HHGate2D::getYmin(const Eref& e) const
{
    return A_.getYmin();
}

void HHGate2D::setYmin(const Eref& e, double value)
{
    A_.setYmin(value);
    B_.setYmin(value);
}

double HHGate2D::getYmax(const Eref& e) const
{
    return A_.getYmax();
}

void HHGate2D::setYmax(const Eref& e, double value)
{
    A_.setYmax(value);
    B_.setYmax(value);
}

unsigned int HHGate2D::getYdivs(const Eref& e) const
{
    return A_.getYdivs();
}

void HHGate2D::setYdivs(const Eref& e, unsigned int value)
{
    A_.setYdivs(value);
    B_.setYdivs(value);
}
