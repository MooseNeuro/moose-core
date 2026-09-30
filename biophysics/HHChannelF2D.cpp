/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment.
**           Copyright (C) 2003-2007 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU General Public License version 3
** See the file LICENSE in the MOOSE source root for the full notice.
**********************************************************************/

#include "HHChannelF2D.h"

#include "../basecode/ElementValueFinfo.h"
#include "../basecode/header.h"
#include "../builtins/Interpol2D.h"
#include "ChanBase.h"
#include "ChanCommon.h"
#include "HHChannelBase.h"
#include "HHGateF2D.h"

const Cinfo *HHChannelF2D::initCinfo()
{
    /////////////////////////////////////////////////////////////////////
    // Shared messages
    /////////////////////////////////////////////////////////////////////
    ///////////////////////////////////////////////////////
    // Field definitions
    ///////////////////////////////////////////////////////
    static ValueFinfo<HHChannelF2D, string> Xindex(
        "Xindex",
        "String specifying input variable assignment for X gate. This tells the"
        " channel which input (dest field) to use for which parameter in the"
        " gate equations."
        " It can take the following string values:\n"
        " \"VOLT_INDEX\": use only voltage input received via dest field 'Vm'"
        " (assigned to the `v` variable in the equations).\n"
        " \"C1_INDEX\": use only concentration input received via  dest field"
        " 'concen' (assigned to `c` variable in the equations).\n"
        " \"C2_INDEX\": use only concentration input received via dest field"
        " 'concen2'  (assigned to `c` variable in the equations)\n"
        " \"VOLT_C1_INDEX\": assign voltage input 'Vm' to `v` and concentration"
        " input 'concen' to `c`\n"
        " \"VOLT_C2_INDEX\": assign voltage input 'Vm' to `v` and concentration"
        " input 'concen2' to `c`\n"
        " \"C1_C2_INDEX\": assign concentration input 'concen' to `v` and "
        "concentration"
        " input 'concen2' to `c`"

        ,
        &HHChannelF2D::setXindex, &HHChannelF2D::getXindex);
    static ValueFinfo<HHChannelF2D, string> Yindex(
        "Yindex",
        "String specifying input variable assignment for Y gate. See `Xindex`."

        ,
        &HHChannelF2D::setYindex, &HHChannelF2D::getYindex);
    static ValueFinfo<HHChannelF2D, string> Zindex(
        "Zindex",
        "String specifying input variable assignment for Z gate. See `Xindex`.",
        &HHChannelF2D::setZindex, &HHChannelF2D::getZindex);
    static ElementValueFinfo<HHChannelF2D, double> Xpower(
        "Xpower", "Power for X gate", &HHChannelF2D::setXpower,
        &HHChannelF2D::getXpower);
    static ElementValueFinfo<HHChannelF2D, double> Ypower(
        "Ypower", "Power for Y gate", &HHChannelF2D::setYpower,
        &HHChannelF2D::getYpower);
    static ElementValueFinfo<HHChannelF2D, double> Zpower(
        "Zpower", "Power for Z gate", &HHChannelF2D::setZpower,
        &HHChannelF2D::getZpower);
    ///////////////////////////////////////////////////////
    // MsgSrc definitions
    ///////////////////////////////////////////////////////

    ///////////////////////////////////////////////////////
    // MsgDest definitions
    ///////////////////////////////////////////////////////
    static DestFinfo concen(
        "concen",
        "Incoming message from Concen object to specific conc to use"
        "as the first concen variable",
        new OpFunc1<HHChannelF2D, double>(&HHChannelF2D::conc1));
    static DestFinfo concen2(
        "concen2",
        "Incoming message from Concen object to specific conc to use"
        "as the second concen variable",
        new OpFunc1<HHChannelF2D, double>(&HHChannelF2D::conc2));
    ///////////////////////////////////////////////////////
    // FieldElementFinfo definition for HHGates. Note that these are made
    // with the deferCreate flag off, so that the HHGates are created
    // right away even if they are empty.
    // I assume that we only have a single HHGate entry for each one.
    ///////////////////////////////////////////////////////
    static FieldElementFinfo<HHChannelF2D, HHGateF2D> gateX(
        "gateX", "Sets up HHGate X for channel", HHGateF2D::initCinfo(),
        &HHChannelF2D::getXgate, &HHChannelF2D::setNumGates,
        &HHChannelF2D::getNumXgates);
    static FieldElementFinfo<HHChannelF2D, HHGateF2D> gateY(
        "gateY", "Sets up HHGate Y for channel", HHGateF2D::initCinfo(),
        &HHChannelF2D::getYgate, &HHChannelF2D::setNumGates,
        &HHChannelF2D::getNumYgates);
    static FieldElementFinfo<HHChannelF2D, HHGateF2D> gateZ(
        "gateZ", "Sets up HHGate Z for channel", HHGateF2D::initCinfo(),
        &HHChannelF2D::getZgate, &HHChannelF2D::setNumGates,
        &HHChannelF2D::getNumZgates);
    static Finfo *HHChannelF2DFinfos[] = {
        &Xindex,   // Value
        &Yindex,   // Value
        &Zindex,   // Value
        &Xpower,   // Value
        &Ypower,   // Value
        &Zpower,   // Value
        &concen,   // Dest
        &concen2,  // Dest
        &gateX,    // FieldElement
        &gateY,    // FieldElement
        &gateZ     // FieldElement
    };

    static string doc[] = {
        "Name",
        "HHChannelF2D",
        "Author",
        "Niraj Dudani, 2009, NCBS, Updated Upi Bhalla, 2011",
        "Description",
        "HHChannelF2D: Hodgkin-Huxley type voltage-gated Ion channel. "
        "Something "
        "like the old tabchannel from GENESIS, but also presents "
        "a similar interface as hhchan from GENESIS. ",
    };

    static Dinfo<HHChannelF2D> dinfo;
    static Cinfo HHChannelF2DCinfo("HHChannelF2D", ChanBase::initCinfo(),
                                   HHChannelF2DFinfos,
                                   sizeof(HHChannelF2DFinfos) / sizeof(Finfo *),
                                   &dinfo, doc, sizeof(doc) / sizeof(string));

    return &HHChannelF2DCinfo;
}

static const Cinfo *HHChannelF2DCinfo = HHChannelF2D::initCinfo();

HHChannelF2D::HHChannelF2D()
    : HHChannelBase(),
      conc1_(0.0),
      conc2_(0.0),
      Xdep0_(-1),
      Xdep1_(-1),
      Ydep0_(-1),
      Ydep1_(-1),
      Zdep0_(-1),
      Zdep1_(-1),
      xGate_(0),
      yGate_(0),
      zGate_(0)
{
    ;
}

///////////////////////////////////////////////////
// Field function definitions
///////////////////////////////////////////////////

string HHChannelF2D::getXindex() const
{
    return Xindex_;
}

void HHChannelF2D::setXindex(string Xindex)
{
    if(Xindex == Xindex_)
        return;

    Xindex_ = Xindex;
    Xdep0_ = dependency(Xindex, 0);
    Xdep1_ = dependency(Xindex, 1);

    assert(Xdep0_ >= 0);
}

string HHChannelF2D::getYindex() const
{
    return Yindex_;
}

void HHChannelF2D::setYindex(string Yindex)
{
    if(Yindex == Yindex_)
        return;

    Yindex_ = Yindex;
    Ydep0_ = dependency(Yindex, 0);
    Ydep1_ = dependency(Yindex, 1);

    assert(Ydep0_ >= 0);
}

string HHChannelF2D::getZindex() const
{
    return Zindex_;
}

void HHChannelF2D::setZindex(string Zindex)
{
    if(Zindex == Zindex_)
        return;

    Zindex_ = Zindex;
    Zdep0_ = dependency(Zindex, 0);
    Zdep1_ = dependency(Zindex, 1);

    assert(Zdep0_ >= 0);
}

////////////////////////////////////////////////////////////////////
// HHGateF2D access funcs
////////////////////////////////////////////////////////////////////

HHGateF2D *HHChannelF2D::getXgate(unsigned int i)
{
    return xGate_;
}

HHGateF2D *HHChannelF2D::getYgate(unsigned int i)
{
    return yGate_;
}

HHGateF2D *HHChannelF2D::getZgate(unsigned int i)
{
    return zGate_;
}

void HHChannelF2D::setNumGates(unsigned int num)
{
    ;
}
unsigned int HHChannelF2D::getNumXgates() const
{
    return xGate_ != nullptr;
}
unsigned int HHChannelF2D::getNumYgates() const
{
    return yGate_ != nullptr;
}
unsigned int HHChannelF2D::getNumZgates() const
{
    return zGate_ != nullptr;
}

double HHChannelF2D::depValue(int dep)
{
    switch(dep) {
        case 0:
            return Vm_;
        case 1:
            return conc1_;
        case 2:
            return conc2_;
        default:
            // dep=-1 falls through this
            //single-input dependency mode (VOLT_INDEX/C1_INDEX/C2_INDEX):
            // there is no second signal. The gate's second axis should be
            // set to length 1 (ydivs=0), in which case Interpol2D's lookup
            // degenerates to plain 1D interpolation and this value is never
            // actually read, so any constant is safe here.
            return 0.0;
    }
}

int HHChannelF2D::dependency(string index, unsigned int dim)
{
    static vector<map<string, int>> dep;
    if(dep.empty()) {
        dep.resize(2);

        dep[0]["VOLT_INDEX"] = 0;
        dep[0]["C1_INDEX"] = 1;
        dep[0]["C2_INDEX"] = 2;

        dep[0]["VOLT_C1_INDEX"] = 0;
        dep[0]["VOLT_C2_INDEX"] = 0;
        dep[0]["C1_C2_INDEX"] = 1;

        dep[1]["VOLT_INDEX"] = -1;
        dep[1]["C1_INDEX"] = -1;
        dep[1]["C2_INDEX"] = -1;

        dep[1]["VOLT_C1_INDEX"] = 1;
        dep[1]["VOLT_C2_INDEX"] = 2;
        dep[1]["C1_C2_INDEX"] = 2;
    }

    if(dep[dim].find(index) == dep[dim].end())
        return -1;

    if(dep[dim][index] == 0)
        return 0;
    if(dep[dim][index] == 1)
        return 1;
    if(dep[dim][index] == 2)
        return 2;

    return -1;
}

///////////////////////////////////////////////////
// Dest function definitions
///////////////////////////////////////////////////

void HHChannelF2D::conc1(double conc)
{
    conc1_ = conc;
}

void HHChannelF2D::conc2(double conc)
{
    conc2_ = conc;
}

///////////////////////////////////////////////////
// utility function definitions
///////////////////////////////////////////////////

void HHChannelF2D::vProcess(const Eref &e, ProcPtr info)
{
    g_ += ChanBase::getGbar(e);
    double A = 0;
    double B = 0;
    if(Xpower_ > 0) {
        xGate_->lookupBoth(depValue(Xdep0_), depValue(Xdep1_), &A, &B);
        if(instant_ & INSTANT_X)
            X_ = A / B;
        else
            X_ = integrate(X_, info->dt, A, B);
        g_ *= takeXpower_(X_, Xpower_);
    }

    if(Ypower_ > 0) {
        yGate_->lookupBoth(depValue(Ydep0_), depValue(Ydep1_), &A, &B);
        if(instant_ & INSTANT_Y)
            Y_ = A / B;
        else
            Y_ = integrate(Y_, info->dt, A, B);

        g_ *= takeYpower_(Y_, Ypower_);
    }

    if(Zpower_ > 0) {
        zGate_->lookupBoth(depValue(Zdep0_), depValue(Zdep1_), &A, &B);
        if(instant_ & INSTANT_Z)
            Z_ = A / B;
        else
            Z_ = integrate(Z_, info->dt, A, B);

        g_ *= takeZpower_(Z_, Zpower_);
    }

    ChanBase::setGk(e, g_ * vGetModulation(e));
    updateIk();
    // Gk_ = g_;
    // Ik_ = ( Ek_ - Vm_ ) * g_;

    // Send out the relevant channel messages.
    sendProcessMsgs(e, info);
    g_ = 0.0;
}

/**
 * Here we get the steady-state values for the gate (the 'instant'
 * calculation) as A_/B_.
 */
void HHChannelF2D::vReinit(const Eref &er, ProcPtr info)
{
    g_ = ChanBase::getGbar(er);
    Element *e = er.element();

    double A = 0.0;
    double B = 0.0;
    if(Xpower_ > 0) {
        xGate_->lookupBoth(depValue(Xdep0_), depValue(Xdep1_), &A, &B);
        if(B < EPSILON) {
            cout << "Warning: B_ value for " << e->getName()
                 << " is ~0. Check X table\n";
            return;
        }
        if(!xInited_)
            X_ = A / B;
        g_ *= takeXpower_(X_, Xpower_);
    }

    if(Ypower_ > 0) {
        yGate_->lookupBoth(depValue(Ydep0_), depValue(Ydep1_), &A, &B);
        if(B < EPSILON) {
            cout << "Warning: B value for " << e->getName()
                 << " is ~0. Check Y table\n";
            return;
        }
        if(!yInited_)
            Y_ = A / B;
        g_ *= takeYpower_(Y_, Ypower_);
    }

    if(Zpower_ > 0) {
        zGate_->lookupBoth(depValue(Zdep0_), depValue(Zdep1_), &A, &B);
        if(B < EPSILON) {
            cout << "Warning: B value for " << e->getName()
                 << " is ~0. Check Z table\n";
            return;
        }
        if(!zInited_)
            Z_ = A / B;
        g_ *= takeZpower_(Z_, Zpower_);
    }

    ChanBase::setGk(er, g_ * vGetModulation(er));
    updateIk();
    // Gk_ = g_;
    // Ik_ = ( Ek_ - Vm_ ) * g_;

    // Send out the relevant channel messages.
    // Same for reinit as for process.
    sendReinitMsgs(er, info);
    g_ = 0.0;
}

////////////////////////////////////////////////////////////////////////
// Gate management stuff.
////////////////////////////////////////////////////////////////////////

/**
 * If the gate exists and has only this element for input, then change
 * the gate power.
 * If the gate exists and has multiple parents, then make a new gate,
 * 	set its power.
 * If the gate does not exist, make a new gate, set its power.
 *
 * The function is designed with the idea that if copies of this
 * channel are made, then they all point back to the original HHGate.
 * (Unless they are cross-node copies).
 * It is only if we subsequently alter the HHGate of this channel that
 * we need to make our own variant of the HHGate, or disconnect from
 * an existing one.
 * \todo: May need to convert to handling arrays and Erefs.
 */
// Assuming that the elements are simple elements. Use Eref for
// general case

bool HHChannelF2D::checkOriginal(Id chanId) const
{
    bool isOriginal = 1;
    if(xGate_) {
        isOriginal = xGate_->isOriginalChannel(chanId);
    }
    else if(yGate_) {
        isOriginal = yGate_->isOriginalChannel(chanId);
    }
    else if(zGate_) {
        isOriginal = zGate_->isOriginalChannel(chanId);
    }
    return isOriginal;
}

void HHChannelF2D::innerCreateGate(const string &gateName, HHGateF2D **gatePtr,
                                   Id chanId, Id gateId)
{
    // Shell* shell = reinterpret_cast< Shell* >( ObjId( Id(), 0 ).data() );
    if(*gatePtr) {
        cout << "Warning: HHChannelF2D::createGate: '" << gateName
             << "' on Element '" << chanId.path() << "' already present\n";
        return;
    }
    *gatePtr = new HHGateF2D(chanId, gateId);
}

void HHChannelF2D::vCreateGate(const Eref &e, string gateType)
{
    if(!checkOriginal(e.id())) {
        cout << "Warning: HHChannelF2D::createGate: Not allowed from copied "
                "channel:\n"
             << e.id().path() << "\n";
        return;
    }

    if(gateType == "X")
        innerCreateGate("xGate", &xGate_, e.id(), Id(e.id().value() + 1));
    else if(gateType == "Y")
        innerCreateGate("yGate", &yGate_, e.id(), Id(e.id().value() + 2));
    else if(gateType == "Z")
        innerCreateGate("zGate", &zGate_, e.id(), Id(e.id().value() + 3));
    else
        cout << "Warning: HHChannelF2D::createGate: Unknown gate type '"
             << gateType << "'. Ignored\n";
}

void HHChannelF2D::innerDestroyGate(const string &gateName, HHGateF2D **gatePtr,
                                    Id chanId)
{
    if(*gatePtr == nullptr) {
        cout << "Warning: HHChannelF2D::destroyGate: '" << gateName
             << "' on Element '" << chanId.path() << "' not present\n";
        return;
    }
    delete(*gatePtr);
    *gatePtr = nullptr;
}

void HHChannelF2D::destroyGate(const Eref &e, string gateType)
{
    if(!checkOriginal(e.id())) {
        cout << "Warning: HHChannelF2D::destroyGate: Not allowed from copied "
                "channel:\n"
             << e.id().path() << "\n";
        return;
    }

    if(gateType == "X")
        innerDestroyGate("xGate", &xGate_, e.id());
    else if(gateType == "Y")
        innerDestroyGate("yGate", &yGate_, e.id());
    else if(gateType == "Z")
        innerDestroyGate("zGate", &zGate_, e.id());
    else
        cout << "Warning: HHChannelF2D::destroyGate: Unknown gate type '"
             << gateType << "'. Ignored\n";
}
