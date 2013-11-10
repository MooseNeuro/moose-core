/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment.
**           Copyright (C) 2003-2010 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU Lesser General Public License version 2.1
** See the file COPYING.LIB for the full notice.
**********************************************************************/

#include "header.h"
#include "DiagonalMsg.h"
#include "OneToAllMsg.h"
#include "../scheduling/Clock.h"
#include "Arith.h"
#include "TableBase.h"
#include "Table.h"
#include <queue>

#include "../shell/Shell.h"

void testArith()
{
	Id a1id = Id::nextId();
	unsigned int size = 10;
	Element* a1 = new DataElement( 
					a1id, Arith::initCinfo(), "a1", size, true );

	Eref a1_0( a1, 0 );
	Eref a1_1( a1, 1 );

	Arith* data1_0 = reinterpret_cast< Arith* >( a1->data( 0 ) );

	data1_0->arg1( 1 );
	data1_0->arg2( 0 );

	ProcInfo p;
	data1_0->process( a1_0, &p );

	assert( data1_0->getOutput() == 1 );

	data1_0->arg1( 1 );
	data1_0->arg2( 2 );

	data1_0->process( a1_0, &p );

	assert( data1_0->getOutput() == 3 );

	a1id.destroy();

	cout << "." << flush;
}

/** 
 * This test uses the Diagonal Msg and summing in the Arith element to
 * generate a Fibonacci series.
 */
void testFibonacci()
{
	if ( Shell::numNodes() > 1 )
		return;
	unsigned int numFib = 20;
	Id a1id = Id::nextId();
	Element* a1 = new DataElement( 
					a1id, Arith::initCinfo(), "a1", numFib, false );

	Arith* data = reinterpret_cast< Arith* >( a1->data( 0 ) );
	if ( data ) {
		data->arg1( 0 );
		data->arg2( 1 );
	}

	const Finfo* outFinfo = Arith::initCinfo()->findFinfo( "output" );
	const Finfo* arg1Finfo = Arith::initCinfo()->findFinfo( "arg1" );
	const Finfo* arg2Finfo = Arith::initCinfo()->findFinfo( "arg2" );
	const Finfo* procFinfo = Arith::initCinfo()->findFinfo( "process" );
	DiagonalMsg* dm1 = new DiagonalMsg( Msg::nextMsgId(), a1, a1 );
	bool ret = outFinfo->addMsg( arg1Finfo, dm1->mid(), a1 );
	assert( ret );
	dm1->setStride( 1 );

	DiagonalMsg* dm2 = new DiagonalMsg( Msg::nextMsgId(), a1, a1 );
	ret = outFinfo->addMsg( arg2Finfo, dm2->mid(), a1 );
	assert( ret );
	dm1->setStride( 2 );

	/*
	bool ret = DiagonalMsg::add( a1, "output", a1, "arg1", 1 );
	assert( ret );
	ret = DiagonalMsg::add( a1, "output", a1, "arg2", 2 );
	assert( ret );
	*/

	Shell* shell = reinterpret_cast< Shell* >( Id().eref().data() );
	shell->doSetClock( 0, 1.0 );
	Eref clocker = Id( 1 ).eref();

	const Finfo* proc0Finfo = Clock::initCinfo()->findFinfo( "process0" );
	OneToAllMsg* otam = new OneToAllMsg( Msg::nextMsgId(), clocker, a1 );
	ret = proc0Finfo->addMsg( procFinfo, otam->mid(), clocker.element() );

	assert( ret );

	shell->doStart( numFib );
	unsigned int f1 = 1;
	unsigned int f2 = 0;
	for ( unsigned int i = 0; i < numFib; ++i ) {
		// if ( a1->dataHandler()->isDataHere( i ) ) {
			Arith* data = reinterpret_cast< Arith* >( a1->data( i ) );
			// cout << Shell::myNode() << ": i = " << i << ", " << data->getOutput() << ", " << f1 << endl;
			assert( data->getOutput() == f1 );
		// }
		unsigned int temp = f1;
		f1 = temp + f2;
		f2 = temp;
	}

	a1id.destroy();
	cout << "." << flush;
}

/** 
 * This test uses the Diagonal Msg and summing in the Arith element to
 * generate a Fibonacci series.
 */
void testMpiFibonacci()
{
	unsigned int numFib = 20;

	// Id a1id = Id::nextId();
	Shell* shell = reinterpret_cast< Shell* >( Id().eref().data() );

	Id a1id = shell->doCreate( "Arith", ObjId(), "a1", numFib );
	SetGet1< double >::set( a1id, "arg1", 0 );
	SetGet1< double >::set( a1id, "arg2", 1 );

	/*
	Arith* data = reinterpret_cast< Arith* >( a1->dataHandler()->data( 0 ) );

	if ( data ) {
		data->arg1( 0 );
		data->arg2( 1 );
	}
	*/

	MsgId mid1 = shell->doAddMsg( "Diagonal", 
		ObjId( a1id, 0 ), "output", ObjId( a1id, 0 ), "arg1" );
	const Msg* m1 = Msg::getMsg( mid1 );
	Eref er1 = m1->manager();
	bool ret = Field< int >::set( er1.objId(), "stride", 1 );
	assert( ret );

	MsgId mid2 = shell->doAddMsg( "Diagonal", 
		ObjId( a1id, 0 ), "output", ObjId( a1id, 0 ), "arg2" );
	const Msg* m2 = Msg::getMsg( mid2 );
	Eref er2 = m2->manager();
	ret = Field< int >::set( er2.objId(), "stride", 2 );
	assert( ret );
	
	/*
	bool ret = DiagonalMsg::add( a1, "output", a1, "arg1", 1 );
	assert( ret );
	ret = DiagonalMsg::add( a1, "output", a1, "arg2", 2 );
	assert( ret );
	*/

	shell->doSetClock( 0, 1.0 );
	shell->doUseClock( "/a1", "process", 0 );

	shell->doStart( numFib );

	vector< double > retVec;
	Field< double >::getVec( a1id, "outputValue", retVec );
	assert( retVec.size() == numFib );

	unsigned int f1 = 1;
	unsigned int f2 = 0;
	for ( unsigned int i = 0; i < numFib; ++i ) {
		/*
		if ( a1->dataHandler()->isDataHere( i ) ) {
			Arith* data = reinterpret_cast< Arith* >( a1->dataHandler()->data( i ) );
			// cout << Shell::myNode() << ": i = " << i << ", " << data->getOutput() << ", " << f1 << endl;
			assert( data->getOutput() == f1 );
		}
		*/
		assert( doubleEq( retVec[i], f1 ) );
		unsigned int temp = f1;
		f1 = temp + f2;
		f2 = temp;
	}

	a1id.destroy();
	cout << "." << flush;
}

void testUtilsForLoadXplot()
{
	bool isNamedPlot( const string& line, const string& plotname );
	double getYcolumn( const string& line );

	assert( isNamedPlot( "/plotname foo", "foo" ) );
	assert( !isNamedPlot( "/plotname foo", "bar" ) );
	assert( !isNamedPlot( "/newplot", "bar" ) );
	assert( !isNamedPlot( "", "bar" ) );
	assert( !isNamedPlot( "1234.56", "bar" ) );

	assert( doubleEq( getYcolumn( "123.456" ), 123.456 ) );
	assert( doubleEq( getYcolumn( "987	123.456" ), 123.456 ) );
	assert( doubleEq( getYcolumn( "987 23.456" ), 23.456 ) );
	assert( doubleEq( getYcolumn( "987	 3.456" ), 3.456 ) );
	assert( doubleEq( getYcolumn( "987	 0.456" ), 0.456 ) );
	assert( doubleEq( getYcolumn( "987.6	 0.456	1111.1" ), 987.6 ) );
	cout << "." << flush;
}

void testUtilsForCompareXplot()
{
	double getRMSDiff( const vector< double >& v1, const vector< double >& v2 );
	double getRMS( const vector< double >& v );

	double getRMSRatio( const vector< double >& v1, const vector< double >& v2 );

	vector< double > v1;
	vector< double > v2;
	v1.push_back( 0 );
	v1.push_back( 1 );
	v1.push_back( 2 );

	v2.push_back( 0 );
	v2.push_back( 1 );
	v2.push_back( 2 );

	double r1 = sqrt( 5.0 / 3.0 );
	double r2 = sqrt( 1.0 / 3.0 );

	assert( doubleEq( getRMS( v1 ), r1 ) );
	assert( doubleEq( getRMS( v2 ), r1 ) );
	assert( doubleEq( getRMSDiff( v1, v2 ), 0 ) );
	assert( doubleEq( getRMSRatio( v1, v2 ), 0 ) );

	v2[2] = 3;
	assert( doubleEq( getRMS( v2 ), sqrt( 10.0/3.0 ) ) );
	assert( doubleEq( getRMSDiff( v1, v2 ), r2 ) );
	assert( doubleEq( getRMSRatio( v1, v2 ), r2 / ( sqrt( 10.0/3.0 ) + r1 ) ) );
	cout << "." << flush;
}

void testTable()
{
	testUtilsForLoadXplot();
	testUtilsForCompareXplot();
	Shell* shell = reinterpret_cast< Shell* >( Id().eref().data() );
	vector< Id > ret;
	Neutral::children( Id().eref(), ret );
	ObjId tabid = shell->doCreate( "Table", ObjId(), "tab", 1 );
	assert( tabid != ObjId() );
	Table* t = reinterpret_cast< Table* >( tabid.eref().data() );
	for ( unsigned int i = 0; i < 100; ++i ) {
		t->input( sqrt((double) i ) );
	}
	vector< double > values = Field< vector< double > >::get( tabid, "vec");
	assert( values.size() == 100 );
	for ( unsigned int i = 0; i < 100; ++i ) {
		double ret = LookupField< unsigned int, double >::get( tabid, "y", i );
		assert( doubleEq( values[i] , sqrt((double) i ) ) );
		assert( doubleEq( ret , sqrt((double) i ) ) );
	}
	shell->doDelete( tabid );
	cout << "." << flush;
}

/**
 * Tests capacity to send a request for a field value to an object
 */
void testGetMsg()
{
	Shell* shell = reinterpret_cast< Shell* >( Id().eref().data() );
	ObjId tabid = shell->doCreate( "Table", ObjId(), "tab", 1 );
	assert( tabid != ObjId() );
	ObjId arithid = shell->doCreate( "Arith", ObjId(), "arith", 1 );
	assert( arithid != ObjId() );
	// Table* t = reinterpret_cast< Table* >( tabid.eref().data() );
	MsgId ret = shell->doAddMsg( "Single", 
		tabid.eref().objId(), "requestData",
		arithid.eref().objId(), "get_outputValue" );
	assert( ret != Msg::bad );
	ret = shell->doAddMsg( "Single", arithid.eref().objId(), "output",
		arithid.eref().objId(), "arg1" );
	assert( ret != Msg::bad );
	shell->doSetClock( 0, 1 );
	shell->doSetClock( 1, 1 );
	shell->doUseClock( "/arith", "process", 0 );
	shell->doUseClock( "/tab", "process", 1 );
	unsigned int numEntries = Field< unsigned int >::get( tabid, "size" );
	assert( numEntries == 0 );
	Id clockId( 1 );
	clockId.element()->digestMessages();
	tabid.element()->digestMessages();
	arithid.element()->digestMessages();
	shell->doReinit();
	numEntries = Field< unsigned int >::get( tabid, "size" );
	assert( numEntries == 1 ); // One for reinit call.
	SetGet1< double >::set( arithid, "arg1", 0.0 );
	SetGet1< double >::set( arithid, "arg2", 2.0 );
	shell->doStart( 100 );

	numEntries = Field< unsigned int >::get( tabid, "size" );
	assert( numEntries == 101 ); // One for reinit call, 100 for process.
	vector< double > temp = Field< vector< double > >::get( tabid, "vec" );

	for ( unsigned int i = 0; i < 100; ++i ) {
		double ret = LookupField< unsigned int, double >::get( tabid, "y", i );
		assert( doubleEq( ret, 2 * i ) );
		assert( doubleEq( temp[i], 2 * i ) );
	}

	// Perhaps I should do another test without reinit.
	/*
	SetGet2< string, string >::set( 
		tabid.eref(), "xplot", "testfile", "testplot" );
	tabentry.destroy();
		*/
	shell->doDelete( arithid );
	shell->doDelete( tabid );
	cout << "." << flush;
	
}

void testBuiltins()
{
	testArith();
	testTable();
}

void testBuiltinsProcess()
{
//	testFibonacci(); Nov 2013: Waiting till we have the MsgObjects fixed.
	testGetMsg();
}

void testMpiBuiltins( )
{
 	// testMpiFibonacci();
}
