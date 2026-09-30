/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment,
** also known as GENESIS 3 base code.
**           copyright (C) 2003-2005 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU General Public License version 3
** See the file LICENSE in the MOOSE source root for the full notice.
**********************************************************************/
#ifndef _HHGateF2D_h
#define _HHGateF2D_h

#include "../basecode/header.h"
#include "HHGateF.h"

// The parser interface is the same as HHGateF, it only needs the
// additional concentration parameter, and overload lookupA, lookupB,
// and lookupBoth to take a vector<double> parameter containing
// voltage and contration
class HHGateF2D : public HHGateF {
public:
    HHGateF2D();
    HHGateF2D(Id originalChanId, Id originalGateId);
    HHGateF2D& operator=(const HHGateF2D&);
    double lookupA(vector<double> v) const;
    double lookupB(vector<double> v) const;

    /**
     * Single call to get both A and B values in a single
     * lookup
     */
    void lookupBoth(double v, double c, double* A, double* B) const;
    static const Cinfo* initCinfo();

private:
    mutable double conc_;
};

// Used by solver, readcell, etc.

#endif  // _HHGateF2D_h
