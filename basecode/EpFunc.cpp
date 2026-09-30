/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment.
**           Copyright (C) 2003-2013 Upinder S. Bhalla. and NCBS
** It is made available under the terms of the
** GNU General Public License version 3
** See the file LICENSE in the MOOSE source root for the full notice.
**********************************************************************/

#include "header.h"
#include "../shell/Shell.h"

template<> Neutral* getEpFuncData< Neutral >( const Eref& e )
{
    static Neutral dummy;
    return &dummy;
}
