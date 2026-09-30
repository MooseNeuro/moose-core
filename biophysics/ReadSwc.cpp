/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment.
**           Copyright (C) 2003-2015 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU General Public License version 3
** See the file LICENSE in the MOOSE source root for the full notice.
**********************************************************************/

#include "../basecode/header.h"
#include "../shell/Shell.h"
#include "../utility/Vec.h"
#include "SwcSegment.h"
#include "ReadSwc.h"
#include "CompartmentBase.h"
#include "Compartment.h"
#include "SymCompartment.h"
#include <fstream>
#include <iomanip>

// Minimum allowed radius of segment, in microns
// Believe it or not, some otherwise reasonable files do have smaller radii
static const double MinRadius = 0.04;

bool isWhitespaceOnly(const std::string& s)
{
    if (s.empty()) {
        return true;
    }
    for (char c : s) {
        if (!std::isspace(static_cast<unsigned char>(c))) {
            return false;  // Found a non-whitespace character
        }
    }
    return true;  // All characters were whitespace
}

ReadSwc::ReadSwc(const string& fname)
{
    ifstream fin(fname.c_str());
    if (!fin) {
        cerr << "ReadSwc:: could not open file " << fname << endl;
        return;
    }

    string temp;
    int badSegs = 0;
    // Raw parent field per accepted segment. Needed only for 0-based
    // normalization below: the SwcSegment string constructor collapses both
    // parent == -1 (a genuine root) and parent == 0 (a 0-based child of node 0)
    // to the ~0U "no parent" sentinel, so the raw value is the only way to tell
    // them apart.
    vector<int> rawParents;
    long minIndex = -1;
    while (getline(fin, temp)) {
        if (isWhitespaceOnly(temp))
            continue;
        auto pos = temp.find_first_not_of("\t ");
        if (pos == string::npos)
            continue;
        if (temp[pos] == '#')
            continue;

        SwcSegment t(temp);
        if (t.OK()) {
            segs_.push_back(t);
            // t.OK() implies the line had 7 whitespace-separated fields.
            stringstream ss(temp);
            vector<string> args;
            string tok;
            while (ss >> tok)
                args.push_back(tok);
            rawParents.push_back(atoi(args[6].c_str()));
            if (minIndex < 0 || static_cast<long>(t.myIndex()) < minIndex)
                minIndex = t.myIndex();
        }
        else
            badSegs++;
    }

    // The SWC standard numbers nodes from 1, and the rest of this reader
    // assumes it (validate() checks myIndex == i+1; parent lookups use
    // segs_[parent-1]). Some sources (e.g. Allen Cell Types Database) number
    // from 0 instead. Detect that here and shift every index and parent by +1
    // so the file is treated as 1-based from this point on. Genuine 1-based
    // files (minIndex == 1) are left untouched.
    if (minIndex == 0) {
        for (unsigned int i = 0; i < segs_.size(); ++i) {
            segs_[i].setIndex(segs_[i].myIndex() + 1);
            int rawPa = rawParents[i];
            segs_[i].setParent(rawPa < 0 ? ~0U
                                         : static_cast<unsigned int>(rawPa + 1));
        }
        cout << "ReadSwc: detected 0-based node indexing; "
                "normalized to 1-based." << endl;
    }

    bool valid = validate();
    if (valid) {
        assignKids();
        cleanMultipointSoma();
        cleanZeroLength();
        parseBranches();
    }
    cout << "ReadSwc: " << fname << "    : NumSegs = " << segs_.size()
         << ", bad = " << badSegs << ", Validated = " << valid
         << ", numBranches = " << branches_.size() << endl;
    diagnostics();
}

bool ReadSwc::validate() const
{
    int numStart = 0;
    int numOrphans = 0;
    int badIndex = 0;
    int badRadius = 0;
    for (unsigned int i = 0; i < segs_.size(); ++i) {
        const SwcSegment& s = segs_[i];
        if (s.myIndex() != i + 1)
            badIndex++;
        if (s.parent() == ~0U) {
            numStart++;
        }
        else {
            if (s.parent() > i) {
                numOrphans++;
            }
        }
        if (s.radius() < MinRadius) {
            badRadius++;
        }
    }
    bool valid = (numStart == 1 && numOrphans == 0 && badRadius == 0);
    if (!valid) {
        cout << "ReadSwc::validate() failed: \nNumSegs = " << segs_.size()
             << ", numStart = " << numStart << ", orphans = " << numOrphans
             << ", badIndex = " << badIndex << ", badRadius = " << badRadius
             << ", numBranches = " << branches_.size() << endl;
    }
    return valid;
}

void ReadSwc::assignKids()
{
    for (unsigned int i = 0; i < segs_.size(); ++i) {
        const SwcSegment& s = segs_[i];
        assert(s.parent() != s.myIndex());
        if (s.parent() != ~0U) {
            segs_[s.parent() - 1].addChild(i + 1);
        }
    }
    for (unsigned int i = 0; i < segs_.size(); ++i) {
        segs_[i].figureOutType();
    }
}

void ReadSwc::cleanZeroLength()
{
    static double EPSILON = 1e-2;  // Assume units in microns.
    for (unsigned int i = 1; i < segs_.size(); ++i) {
        SwcSegment& s = segs_[i];
        SwcSegment& pa = segs_[s.parent() - 1];
        if (s.distance(pa) < EPSILON) {
            // Remove the zero length child from pa.kids_
            vector<int> temp;
            for (unsigned int j = 0; j < pa.kids().size(); ++j) {
                if (static_cast<unsigned int>(pa.kids()[j]) != s.myIndex())
                    temp.push_back(pa.kids()[j]);
            }
            // Go through all kids of s and reparent them.
            for (unsigned int j = 0; j < s.kids().size(); ++j) {
                SwcSegment& kid = segs_[s.kids()[j] - 1];
                kid.setParent(pa.myIndex());
                temp.push_back(kid.myIndex());
            }
            pa.replaceKids(temp);
            s.setBad();
            cout << "ReadSwc:: Cleaned zero length " << s.myIndex() << endl;
        }
    }
}

void ReadSwc::cleanMultipointSoma()
{
    // Find the root soma segment (parent == ~0U)
    int rootIdx = -1;
    for (unsigned int i = 0; i < segs_.size(); ++i) {
        if (segs_[i].parent() == ~0U) {
            rootIdx = static_cast<int>(i);
            break;
        }
    }
    if (rootIdx < 0 || segs_[rootIdx].type() != SwcSegment::SOMA)
        return;

    SwcSegment& soma = segs_[rootIdx];

    // Warn if the soma does not match the NeuroMorpho.org 3-point convention:
    // exactly 2 direct soma children, all sharing x,z,radius with root,
    // and y-offsets of exactly ±radius.

    static const double EPS = 1e-3;  // microns
    vector<int> directSomaKids;
    for (int k : soma.kids()) {
        if (segs_[k - 1].type() == SwcSegment::SOMA)
            directSomaKids.push_back(k);
    }
    if (directSomaKids.size() == 2) {
        const SwcSegment& s2 = segs_[directSomaKids[0] - 1];
        const SwcSegment& s3 = segs_[directSomaKids[1] - 1];
        double xs = soma.vec().a0(), ys = soma.vec().a1(), zs = soma.vec().a2(),
               rs = soma.radius();
        bool xzMatch =
            fabs(s2.vec().a0() - xs) < EPS && fabs(s2.vec().a2() - zs) < EPS &&
            fabs(s3.vec().a0() - xs) < EPS && fabs(s3.vec().a2() - zs) < EPS;
        bool radiiMatch =
            fabs(s2.radius() - rs) < EPS && fabs(s3.radius() - rs) < EPS;
        bool yMatch = (fabs(s2.vec().a1() - (ys - rs)) < EPS &&
                       fabs(s3.vec().a1() - (ys + rs)) < EPS) ||
                      (fabs(s3.vec().a1() - (ys - rs)) < EPS &&
                       fabs(s2.vec().a1() - (ys + rs)) < EPS);
        if (!xzMatch || !radiiMatch || !yMatch)
            cout << "ReadSwc::cleanMultipointSoma: Warning: 3-point soma "
                    "does not match "
                 << "NeuroMorpho.org convention"
                 << (!xzMatch ? " [x,z coords differ]" : "")
                 << (!radiiMatch ? " [radii differ]" : "")
                 << (!yMatch ? " [y-offsets != ±r]" : "") << endl;
    }
    else if (!directSomaKids.empty()) {
        // 1 child: may be 2-point (Arbor) soma or a chained soma.
        // >2 children: contour soma or non-standard file.
        cout << "ReadSwc::cleanMultipointSoma: Note: soma has "
             << directSomaKids.size() << " direct soma-type child(ren) "
             << "(NeuroMorpho.org standard expects 2)." << endl;
    }

    // 2-point soma (Arbor style): single direct SOMA child with no chained
    // SOMA grandchildren beneath it. Both points define the cylinder geometry
    // — do not collapse.
    if (directSomaKids.size() == 1) {
        int onlyKidIdx = directSomaKids[0];
        bool hasSomaGrandkids = false;
        for (int gk : segs_[onlyKidIdx - 1].kids()) {
            if (segs_[gk - 1].type() == SwcSegment::SOMA) {
                hasSomaGrandkids = true;
                break;
            }
        }
        if (!hasSomaGrandkids) {
            cout << "ReadSwc::cleanMultipointSoma: 2-point soma detected; "
                    "preserving geometry."
                 << endl;
            return;
        }
        // else: chained soma (child has soma grandkids) — fall through to collapse.
    }

    // Use a queue to handle chained soma segments (e.g. 1->2->3->dendrite)
    // not just direct children of root.
    vector<int> toProcess = soma.kids();
    vector<int> newKids;
    while (!toProcess.empty()) {
        vector<int> nextToProcess;
        for (int k : toProcess) {
            SwcSegment& kid = segs_[k - 1];
            if (kid.type() == SwcSegment::SOMA) {
                for (int grandkid : kid.kids()) {
                    segs_[grandkid - 1].setParent(soma.myIndex());
                    nextToProcess.push_back(grandkid);
                }
                kid.setBad();
                cout << "ReadSwc:: Merged multi-point soma segment " << k
                     << " into root soma" << endl;
            }
            else {
                newKids.push_back(k);
            }
        }
        toProcess = nextToProcess;
    }
    soma.replaceKids(newKids);
}

void ReadSwc::traverseBranch(const SwcSegment& s, double& len, double& L,
                             vector<int>& cable) const
{
    const SwcSegment* prev = &s;
    cable.resize(1, s.myIndex());  // Always include the starting seg.
    // Note that the cable is filled up with entries in reverse order.

    if (s.parent() == ~0U) {
        len = s.radius();
        L = sqrt(len);
        return;
    }

    do {
        // Beware the indexing!
        const SwcSegment& pa = segs_[prev->parent() - 1];
        len += pa.distance(*prev);
        L += pa.L();
        cable.push_back(pa.myIndex());
        prev = &pa;
    } while ((prev->parent() != ~0U) && (prev->kids().size() == 1));
    cable.pop_back();  // Get rid of the last entry, it is on the parent.
}

void ReadSwc::parseBranches()
{
    // Fill vector of all branches.
    for (unsigned int i = 0; i < segs_.size(); ++i) {
        const SwcSegment& s = segs_[i];
        // Branch endpoints: root soma (always), forks (≥2 kids), or leaves (0
        // kids). Root must be explicit: after soma chain cleanup it may have
        // exactly 1 kid.
        if (s.OK() && (s.parent() == ~0U || s.kids().size() != 1)) {
            vector<int> cable;
            // int branchIndex = branches_.
            // branches_.push_back( i + 1 );
            double len = 0;
            double L = 0;
            traverseBranch(s, len, L, cable);
            // branchGeomLength_.push_back( len );
            // branchElectroLength_.push_back( L );
            SwcBranch br(branches_.size(), s, len, L, cable);
            branches_.push_back(br);
        }
    }
    // Assign the parent of each branch. This is known because the
    // parent of the first segment in the branch is the last segment
    // in the parent branch. I construct a reverse lookup table to find
    // the branch # from its last segment number.
    vector<int> reverseSeg(segs_.size() + 1, 0);
    for (unsigned int i = 0; i < branches_.size(); ++i)
        reverseSeg[branches_[i].segs_.back()] = i;
    for (unsigned int i = 0; i < branches_.size(); ++i) {
        int parentSeg = segs_[branches_[i].segs_[0] - 1].parent();
        if (parentSeg == ~0U)  // root - no parent
            continue;

        assert(parentSeg != 0);  // Note that segment indices start from 1
        branches_[i].setParent(reverseSeg[parentSeg]);
    }
}

void ReadSwc::diagnostics() const
{
    vector<int> diag(14);
    for (unsigned int i = 0; i < segs_.size(); ++i) {
        const SwcSegment& s = segs_[i];
        if (s.type() < 14)
            diag[s.type()]++;
    }

    for (int i = 0; i < 14; ++i)
        cout << "ReadSwc::diagnostics: " << setw(12) << ": " << setw(5)
             << diag[i] << endl;
}

static Id makeCompt(Id parent, const string& __name, const SwcSegment& seg,
                    const SwcSegment& pa, double RM, double RA, double CM)
{
    Shell* shell = reinterpret_cast<Shell*>(Id().eref().data());
    double len = seg.radius() * 2.0;
    Id compt;
    double x0, y0, z0;
    if (seg.parent() != ~0U) {
        len = seg.distance(pa);
        x0 = pa.vec().a0();
        y0 = pa.vec().a1();
        z0 = pa.vec().a2();
    }
    else {
        x0 = seg.vec().a0() - len;
        y0 = seg.vec().a1();
        z0 = seg.vec().a2();
    }
    assert(len > 0.0);
    compt = shell->doCreate("Compartment", parent, __name, 1);
    Eref er = compt.eref();
    moose::CompartmentBase* cptr =
        reinterpret_cast<moose::CompartmentBase*>(compt.eref().data());
    double xa = seg.radius() * seg.radius() * PI * 1e-12;
    len *= 1e-6;
    double dia = seg.radius() * 2.0e-6;
    cptr->setRm(er, RM / (len * dia * PI));
    cptr->setRa(er, RA * len / xa);
    cptr->setCm(er, CM * (len * dia * PI));
    cptr->setDiameter(dia);
    cptr->setLength(len);
    cptr->setX0(x0 * 1e-6);
    cptr->setY0(y0 * 1e-6);
    cptr->setZ0(z0 * 1e-6);
    cptr->setX(seg.vec().a0() * 1e-6);
    cptr->setY(seg.vec().a1() * 1e-6);
    cptr->setZ(seg.vec().a2() * 1e-6);
    return compt;
}

bool ReadSwc::testIfOnlyBasalsArePresent() const
{
    /// Some SWCs label all non-soma segments as basals.
    unsigned int numDend = 0;
    unsigned int numBasal = 0;
    for (unsigned int i = 0; i < branches_.size(); ++i) {
        const SwcBranch& br = branches_[i];
        for (unsigned int j = 0; j < br.segs_.size(); ++j) {
            const SwcSegment& seg = segs_[br.segs_[j] - 1];
            numBasal += (seg.type() == SwcSegment::BASAL);
            numDend += (seg.type() == SwcSegment::DEND);
        }
    }
    return ((numBasal > 0) && (numDend == 0));
}

bool ReadSwc::build(Id parent, double lambda, double RM, double RA, double CM)
{
    Shell* shell = reinterpret_cast<Shell*>(Id().eref().data());
    vector<Id> compts(segs_.size());
    unsigned int numSomas = 0;
    unsigned int numRootAxons = 0;
    unsigned int numRootBasals = 0;
    unsigned int numRootDends = 0;
    vector<unsigned int> numBranchesOnMyParent(branches_.size(), 0);
    vector<string> parentName(segs_.size());
    string segName;
    string basalName = "basal";
    if (testIfOnlyBasalsArePresent())
        basalName = "dend";
    for (unsigned int i = 0; i < branches_.size(); ++i) {
        SwcBranch& br = branches_[i];
        unsigned int myBranchIdx = numBranchesOnMyParent[br.parent()];
        numBranchesOnMyParent[br.parent()]++;
        for (unsigned int j = 0; j < br.segs_.size(); ++j) {
            stringstream ss;
            Id compt;
            SwcSegment& seg = segs_[br.segs_[j] - 1];
            unsigned int paIndex = seg.parent();
            if (paIndex == ~0U)  // root soma
            {
                // Collect SOMA-type direct children to detect soma representation.
                vector<const SwcSegment*> somaKids;
                for (int k : seg.kids()) {
                    if (segs_[k - 1].OK() &&
                        segs_[k - 1].type() == SwcSegment::SOMA)
                        somaKids.push_back(&segs_[k - 1]);
                }
                if (somaKids.size() >= 2) {
                    // 3-point soma (2 children of centre, e.g. from p_to_swc):
                    // poles define a cylinder of length 2r and diameter 2r,
                    // giving surface area 4πr² = sphere surface area.
                    compt = makeCompt(parent, "soma", *somaKids[1], *somaKids[0],
                                      RM, RA, CM);
                    for (auto* sk : somaKids)
                        compts[sk->myIndex() - 1] = compt;
                }
                else if (somaKids.size() == 1) {
                    // Linear soma chain (e.g. Neuromorpho 3-point: root→mid→tip).
                    // Follow the chain to the distal SOMA end, pre-filling every
                    // intermediate slot so non-root SOMA processing finds them set.
                    vector<const SwcSegment*> chain;
                    const SwcSegment* distal = somaKids[0];
                    chain.push_back(distal);
                    while (true) {
                        const SwcSegment* next = nullptr;
                        int nsc = 0;
                        for (int k : distal->kids()) {
                            if (segs_[k - 1].OK() &&
                                segs_[k - 1].type() == SwcSegment::SOMA) {
                                if (nsc == 0) next = &segs_[k - 1];
                                nsc++;
                            }
                        }
                        if (nsc == 1) {
                            distal = next;
                            chain.push_back(distal);
                        } else {
                            break;
                        }
                    }
                    compt = makeCompt(parent, "soma", *distal, seg, RM, RA, CM);
                    for (auto* s : chain)
                        compts[s->myIndex() - 1] = compt;
                }
                else {
                    // 1-point soma: artificial cylinder of length = 2*r.
                    compt = makeCompt(parent, "soma", seg, seg, RM, RA, CM);
                }
                numSomas++;
            }
            else if (seg.type() == SwcSegment::SOMA) {
                // Non-root SOMA node: slot was pre-filled during root processing.
                compt = compts[seg.myIndex() - 1];
                if (compt == Id()) {
                    // Unexpected: alias to the parent compartment rather than
                    // creating a duplicate soma element.
                    assert(compts[paIndex - 1] != Id());
                    compt = compts[paIndex - 1];
                }
                // Do NOT increment numSomas — already counted at root soma.
            }
            else {
                SwcSegment& pa = segs_[paIndex - 1];
                if (seg.distance(pa) < 1e-9) {
                    // Zero-length proximal node from 2-node-per-compartment SWC:
                    // alias this slot to the parent compartment without creating
                    // a new element or message.
                    assert(compts[paIndex - 1] != Id());
                    compt = compts[paIndex - 1];
                } else {
                    if (pa.type() != seg.type()) {
                        if (seg.type() == SwcSegment::AXON) {
                            ss << "axon" << numRootAxons;
                            segName = ss.str();
                            numRootAxons++;
                        }
                        else if (seg.type() == SwcSegment::BASAL) {
                            ss << basalName << numRootBasals;
                            segName = ss.str();
                            numRootBasals++;
                        }
                        else {  // Everything else is a dend.
                            ss << "dend" << numRootDends;
                            segName = ss.str();
                            numRootDends++;
                        }
                    }
                    else if (j == 0) {  // extend name with branch idx
                        const string& paName =
                            compts[paIndex - 1].element()->getName();
                        string paBranchName = paName.substr(0, paName.rfind('_'));
                        ss << paBranchName << "." << myBranchIdx << "_0";
                        segName = ss.str();
                    }
                    else {
                        const string& paName =
                            compts[paIndex - 1].element()->getName();
                        string paBranchName = paName.substr(0, paName.rfind('_'));
                        ss << paBranchName << "_" << j;
                        segName = ss.str();
                    }
                    compt = makeCompt(parent, segName, seg, pa, RM, RA, CM);
                    assert(compt != Id());
                    assert(compts[paIndex - 1] != Id());
                    shell->doAddMsg("Single", compts[paIndex - 1], "axial", compt,
                                    "raxial");
                }
            }
            assert(compt != Id());
            compts[seg.myIndex() - 1] = compt;
        }
    }
    return true;
}
