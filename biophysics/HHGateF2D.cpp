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
#include "HHGateF2D.h"

const Cinfo* HHGateF2D::initCinfo()
{
    ///////////////////////////////////////////////////////
    // Field definitions.
    ///////////////////////////////////////////////////////
    static ReadOnlyLookupValueFinfo<HHGateF2D, vector<double>, double> A(
        "A",
        "lookupA: Compute the A gate value from two doubles, passed"
        " in as a vector.\n"
        " This is same as `alpha(V)` the gate transition rate"
        " from closed to open state in the Hodgkin-Huxley formulation.\n"
        " Unlike HHGate2D, HHGateF2D uses formula"
        " evaluation to get more accurate value, which is also"
        " slower.",
        &HHGateF2D::lookupA);
    static ReadOnlyLookupValueFinfo<HHGateF2D, vector<double>, double> B(
        "B",
        "lookupB: Compute B gate value from two doubles in a vector.\n"
        " This is same as `alpha(V)+beta(V)` in the Hodgkin-Huxley formulation,"
        " where alpha(V) is the gate transition rate from closed to open and "
        "beta(V)"
        " is the transition rate from open to closed state.",
        &HHGateF2D::lookupB);

    ///////////////////////////////////////////////////////
    // DestFinfos
    ///////////////////////////////////////////////////////
    static Finfo* HHGateF2DFinfos[] = {
        &A,  // ReadOnlyLookupValue
        &B,  // ReadOnlyLookupValue
    };

    static string doc[] = {
        "Name",
        "HHGateF2D",
        "Author",
        "Subhasis Ray, 2025, CHINTA. This is based on HHGate2D"
        " implementation by Niraj Dudani, 2009, NCBS.",
        "Description",
        "HHGateF2D: Gate for Hodkgin-Huxley type channels, equivalent to the"
        " m and h terms on the Na squid channel and the n term on K.\n"
        " This is specialized for dependency on two variables, voltage"
        " and concentration (usually [Ca2+]).\n"
        " Unlike HHGate2D, HHGateF2D evaluates the formulas for the gate"
        " parameters directly. This is slower than HHGate2D's"
        " interpolation-table lookup, but numerically more accurate, which can"
        " be important when the concentration can vary in an exponential"
        " scale. It also saves one from the large memory requirement for"
        " storing large 2D arrays.\n"
        " The formulas must be specified as in the form f(v, c),"
        " where v and c are the variable names. For example:\n"
        " \"1500/(1 + (c / 1.5e-4 * exp(-77 * v)))\"\n"
        " While the names correspond to voltage and concentration, they can be"
        " any two parameters mapped to the corresponding fields in"
        " HHChannelF2D.\n"
        " Additionally, like HHGateF, HHGateF2D provides the following "
        " predefined variable names to facilitate intermediate "
        " calculations:\n"
        "  `alpha` for forward rate,\n"
        "  `beta` for backward rate,\n"
        "  `tau` for time constant, and\n"
        "  `inf` for steady state open fraction\n"
        " as per Hodgkin and Huxley's formulation.\n"

    };

    static Dinfo<HHGateF2D> dinfo;
    static Cinfo HHGateF2DCinfo("HHGateF2D", HHGateF::initCinfo(),
                                HHGateF2DFinfos,
                                sizeof(HHGateF2DFinfos) / sizeof(Finfo*),
                                &dinfo, doc, sizeof(doc) / sizeof(string));

    return &HHGateF2DCinfo;
}

static const Cinfo* hhGate2DCinfo = HHGateF2D::initCinfo();
///////////////////////////////////////////////////
HHGateF2D::HHGateF2D()
{
    cerr << "Warning: HHGateF2D::HHGateF2D(): this should never be called"
         << endl;
}

HHGateF2D::HHGateF2D(Id originalChanId, Id originalGateId)
    : HHGateF(originalChanId, originalGateId)
{
    symTab_.add_variable("c", conc_);
    symTab_.add_variable("alpha", alphav_);
    symTab_.add_variable("beta", betav_);
    symTab_.add_variable("tau", tauv_);
    symTab_.add_variable("inf", infv_);
    alpha_.register_symbol_table(symTab_);
    beta_.register_symbol_table(symTab_);
}

HHGateF2D& HHGateF2D::operator=(const HHGateF2D& rhs)
{
    // protect from self-assignment.
    if(this == &rhs)
        return *this;

    v_ = rhs.v_;
    conc_ = rhs.conc_;
    symTab_.add_variable("v", v_);
    symTab_.add_variable("c", conc_);
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
double HHGateF2D::lookupA(vector<double> v) const
{
    if(v.size() < 2) {
        cerr << "Error: HHGateF2D::lookupA: 2 real numbers needed to lookup "
                "2D table.\n";
        return 0.0;
    }

    if(v.size() > 2) {
        cerr << "Error: HHGateF2D::lookupA: Only 2 real numbers needed to "
                "lookup 2D table. "
                "Using only first 2.\n";
    }
    v_ = v[0];
    conc_ = v[1];
    return tauInf_ ? beta_.value() / alpha_.value() : alpha_.value();
}

double HHGateF2D::lookupB(vector<double> v) const
{
    if(v.size() < 2) {
        cerr << "Error: HHGateF2D::lookupB: 2 real numbers needed to lookup "
                "2D table.\n";
        return 0.0;
    }

    if(v.size() > 2) {
        cerr << "Error: HHGateF2D::lookupB: Only 2 real numbers needed to "
                "lookup 2D table. "
                "Using only first 2.\n";
    }
    v_ = v[0];
    conc_ = v[1];
    return tauInf_ ? 1.0 / alpha_.value() : alpha_.value() + beta_.value();
}

void HHGateF2D::lookupBoth(double v, double c, double* A, double* B) const
{
    *A = lookupA(vector<double>{v, c});
    *B = lookupB(vector<double>{v, c});
    // cerr << "HHGateF2D::lookupBoth(" << v << ", " << c << ",*A=" << * A << ",
    // *B="<< * B << ")" << endl;
}
