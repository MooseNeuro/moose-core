/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment.
**           Copyright (C) 2003-2015 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU Lesser General Public License version 2.1
** See the file COPYING.LIB for the full notice.
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

bool isWhitespaceOnly(const std::string& s) {
    if (s.empty()) {
        return true;
    }
    for (char c : s) {
        if (!std::isspace(static_cast<unsigned char>(c))) {
            return false; // Found a non-whitespace character
        }
    }
    return true; // All characters were whitespace
}

ReadSwc::ReadSwc( const string& fname )
{
    ifstream fin( fname.c_str() );
    if ( !fin )
    {
        cerr << "ReadSwc:: could not open file " << fname << endl;
        return;
    }

    string temp;
    int badSegs = 0;
    while( getline( fin, temp ) )
    {
        if ( isWhitespaceOnly(temp) )
            continue;
        auto pos = temp.find_first_not_of( "\t " );
        if ( pos == string::npos )
            continue;
        if ( temp[pos] == '#' )
            continue;

        SwcSegment t( temp );
        if ( t.OK() )
            segs_.push_back( SwcSegment( temp ) );
        else
            badSegs++;
    }
    bool valid = validate();
    if ( valid )
    {
        assignKids();
        cleanZeroLength();
        parseBranches();
    }
    cout << "ReadSwc: " << fname << "    : NumSegs = " << segs_.size() <<
         ", bad = " << badSegs <<
         ", Validated = " << valid <<
         ", numBranches = " << branches_.size() <<
         endl;
    diagnostics();
}

bool ReadSwc::validate() const
{
    int numStart = 0;
    int numOrphans = 0;
    int badIndex = 0;
    int badRadius = 0;
    for ( unsigned int i = 0; i < segs_.size(); ++i )
    {
        const SwcSegment& s = segs_[i];
        if ( s.myIndex() != i + 1 )
            badIndex++;
        if ( s.parent() == ~0U )
        {
            numStart++;
        }
        else
        {
            if ( s.parent() > i )
            {
                numOrphans++;
            }
        }
        if ( s.radius() < MinRadius )
        {
            badRadius++;
        }
    }
    bool valid = ( numStart == 1 && numOrphans == 0 && badRadius == 0 );
    if ( !valid )
    {
        cout << "ReadSwc::validate() failed: \nNumSegs = " <<
             segs_.size() <<
             ", numStart = " << numStart <<
             ", orphans = " << numOrphans <<
             ", badIndex = " << badIndex <<
             ", badRadius = " << badRadius <<
             ", numBranches = " << branches_.size() <<
             endl;
    }
    return valid;
}

void ReadSwc::assignKids()
{
    for ( unsigned int i = 0; i < segs_.size(); ++i )
    {
        const SwcSegment& s = segs_[i];
        assert ( s.parent() != s.myIndex() );
        if ( s.parent() != ~0U )
        {
            segs_[s.parent() - 1].addChild( i + 1 );
        }
    }
    for ( unsigned int i = 0; i < segs_.size(); ++i )
    {
        segs_[i].figureOutType();
    }
}

void ReadSwc::cleanZeroLength()
{
    static double EPSILON = 1e-2; // Assume units in microns.
    for ( unsigned int i = 1; i < segs_.size(); ++i )
    {
        SwcSegment& s = segs_[i];
        SwcSegment& pa = segs_[ s.parent() - 1 ];
        if ( s.distance( pa ) < EPSILON )
        {
            // Remove the zero length child from pa.kids_
            vector< int > temp;
            for ( unsigned int j = 0; j < pa.kids().size(); ++j )
            {
                if ( static_cast< unsigned int >( pa.kids()[j] ) != s.myIndex() )
                    temp.push_back( pa.kids()[j] );
            }
            // Go through all kids of s and reparent them.
            for ( unsigned int j = 0; j < s.kids().size(); ++j )
            {
                SwcSegment& kid = segs_[ s.kids()[j] - 1 ];
                kid.setParent( pa.myIndex() );
                temp.push_back( kid.myIndex() );
            }
            pa.replaceKids( temp );
            s.setBad();
            cout << "ReadSwc:: Cleaned zero length " << s.myIndex() << endl;
        }
    }
}

void ReadSwc::traverseBranch( const SwcSegment& s,
                              double& len, double& L, vector< int >& cable ) const
{
    const SwcSegment* prev = &s;
    cable.resize( 1, s.myIndex() ); // Always include the starting seg.
    // Note that the cable is filled up with entries in reverse order.

    if ( s.parent() == ~0U )
    {
        len = s.radius();
        L = sqrt( len );
        return ;
    }

    do
    {
        // Beware the indexing!
        const SwcSegment& pa = segs_[prev->parent() - 1];
        len += pa.distance( *prev );
        L += pa.L( );
        cable.push_back( pa.myIndex() );
        prev = &pa;
    }
    while ( (prev->parent() != ~0U) && (prev->kids().size() == 1) );
    cable.pop_back(); // Get rid of the last entry, it is on the parent.
}

void ReadSwc::parseBranches()
{
    // Fill vector of all branches.
    for ( unsigned int i = 0; i < segs_.size(); ++i )
    {
        const SwcSegment& s = segs_[i];
        if ( s.OK() && s.kids().size() != 1 )   // Either use a fork or an end.
        {
            vector< int > cable;
            // int branchIndex = branches_.
            // branches_.push_back( i + 1 );
            double len = 0;
            double L = 0;
            traverseBranch( s, len, L, cable );
            // branchGeomLength_.push_back( len );
            // branchElectroLength_.push_back( L );
            SwcBranch br( branches_.size(), s, len, L, cable );
            branches_.push_back( br );
        }
    }
    // Assign the parent of each branch. This is known because the
    // parent of the first segment in the branch is the last segment
    // in the parent branch. I construct a reverse lookup table to find
    // the branch # from its last segment number.
    vector< int > reverseSeg ( segs_.size() + 1, 0 );
    for ( unsigned int i = 0; i < branches_.size(); ++i )
        reverseSeg[ branches_[i].segs_.back() ] = i;
    for ( unsigned int i = 0; i < branches_.size(); ++i )
    {
        int parentSeg = segs_[ branches_[i].segs_[0] - 1 ].parent();
        assert( parentSeg != 0 ); // Note that segment indices start from 1
        branches_[i].setParent( reverseSeg[ parentSeg ] );
    }
}

void ReadSwc::diagnostics() const
{
    vector< int > diag( 14 );
    for ( unsigned int i = 0; i < segs_.size(); ++i )
    {
        const SwcSegment& s = segs_[i];
        if ( s.type() < 14 )
            diag[s.type()]++;
    }

    for ( int i = 0; i < 14; ++i )
        cout << "ReadSwc::diagnostics: " << setw(12) << 
            ": " << setw(5) << diag[i] << endl;

}

static Id makeCompt( Id parent, const string& __name,
                     const SwcSegment& seg, const SwcSegment& pa,
                     double RM, double RA, double CM )
{
    Shell* shell = reinterpret_cast< Shell* >( Id().eref().data() );
    double len = seg.radius() * 2.0;
    Id compt;
    double x0, y0, z0;
    if ( seg.parent() != ~0U )
    {
        len = seg.distance( pa );
        x0 = pa.vec().a0();
        y0 = pa.vec().a1();
        z0 = pa.vec().a2();
    }
    else
    {
        x0 = seg.vec().a0() - len;
        y0 = seg.vec().a1();
        z0 = seg.vec().a2();
    }
    assert( len > 0.0 );
    compt = shell->doCreate( "Compartment", parent, __name, 1 );
    Eref er = compt.eref();
    moose::CompartmentBase *cptr = reinterpret_cast< moose::CompartmentBase* >(
                                       compt.eref().data() );
    double xa = seg.radius() * seg.radius() * PI * 1e-12;
    len *= 1e-6;
    double dia = seg.radius() * 2.0e-6;
    cptr->setRm( er, RM / ( len * dia * PI ) );
    cptr->setRa( er, RA * len / xa );
    cptr->setCm( er, CM * ( len * dia * PI ) );
    cptr->setDiameter( dia );
    cptr->setLength( len );
    cptr->setX0( x0 * 1e-6 );
    cptr->setY0( y0 * 1e-6 );
    cptr->setZ0( z0 * 1e-6 );
    cptr->setX( seg.vec().a0() * 1e-6 );
    cptr->setY( seg.vec().a1() * 1e-6 );
    cptr->setZ( seg.vec().a2() * 1e-6 );
    return compt;
}

bool ReadSwc::testIfOnlyBasalsArePresent() const
{
	/// Some SWCs label all non-soma segments as basals.
	unsigned int numDend = 0;
	unsigned int numBasal = 0;
    for ( unsigned int i = 0; i < branches_.size(); ++i ) {
        const SwcBranch& br = branches_[i];
        for ( unsigned int j = 0; j < br.segs_.size(); ++j ) {
            const SwcSegment& seg = segs_[ br.segs_[j] -1 ];
            numBasal+= ( seg.type() == SwcSegment::BASAL);
            numDend+= ( seg.type() == SwcSegment::DEND);
		}
	}
	return( (numBasal > 0) && (numDend==0) );
}

bool ReadSwc::build( Id parent,
                     double lambda, double RM, double RA, double CM )
{
    Shell* shell = reinterpret_cast< Shell* >( Id().eref().data() );
    vector< Id > compts( segs_.size() );
	unsigned int numSomas = 0;
	unsigned int numRootAxons = 0;
	unsigned int numRootBasals = 0;
	unsigned int numRootDends = 0;
	vector< unsigned int> numBranchesOnMyParent( branches_.size(), 0 );
	vector< string > parentName( segs_.size() );
	string segName;
	string basalName = "basal";
	if ( testIfOnlyBasalsArePresent() )
		basalName = "dend";
    for ( unsigned int i = 0; i < branches_.size(); ++i )
    {
        SwcBranch& br = branches_[i];
		unsigned int myBranchIdx = numBranchesOnMyParent[ br.parent() ];
		numBranchesOnMyParent[ br.parent() ]++;
        for ( unsigned int j = 0; j < br.segs_.size(); ++j )
        {
			stringstream ss;
            Id compt;
            SwcSegment& seg = segs_[ br.segs_[j] -1 ];
            unsigned int paIndex = seg.parent();
            if ( paIndex == ~0U )   // soma
            {
                compt = makeCompt( parent, "soma", seg, seg, RM, RA, CM );
				numSomas++;
            }
            else if ( seg.type() == SwcSegment::SOMA) 
            {
   				ss << "soma" << numSomas;
				segName = ss.str();
                compt = makeCompt( parent, segName, seg, seg, RM, RA, CM );
				numSomas++;
            }
            else
            {
                SwcSegment& pa = segs_[ paIndex - 1 ];
				if (pa.type() != seg.type() ) {
					if ( seg.type() == SwcSegment::AXON) {
        				ss << "axon" << numRootAxons;
						segName = ss.str();
						numRootAxons++;
					} else if ( seg.type() == SwcSegment::BASAL ) {
        				ss << basalName << numRootBasals;
						segName = ss.str();
						numRootBasals++;
					} else {	// Everything else is a dend.
        				ss << "dend" << numRootDends;
						segName = ss.str();
						numRootDends++;
					}
				} else if (j == 0 ) { // extend name with branch idx
					const string& paName=compts[paIndex-1].element()->getName();
					string paBranchName = paName.substr(0,  paName.rfind('_') );
					ss << paBranchName << "." << myBranchIdx << "_0";
					segName = ss.str();
				} else {
					const string& paName=compts[paIndex-1].element()->getName();
					string paBranchName = paName.substr(0, paName.rfind('_') );
					ss << paBranchName << "_" << j;
					segName = ss.str();
				}
                compt = makeCompt( parent, segName, seg, pa, RM, RA, CM);
                assert( compt != Id() );
                assert( compts[ paIndex -1 ] != Id() );
                shell->doAddMsg( "Single",
                                 compts[paIndex-1], "axial", compt, "raxial" );
            }
            assert( compt != Id() );
            compts[ seg.myIndex() -1 ] = compt;
        }
    }
    return true;
}
