/***
 *    Description:  Moose Parser class, wraps exprtk.
 *
 *        Created:  2018-08-25

 *         Author:  Dilawar Singh <dilawars@ncbs.res.in>
 *   Organization:  NCBS Bangalore
 */

#include <vector>
#include <cassert>
#include <regex>
#include <algorithm>

#include "../basecode/header.h"

#include "../randnum/randnum.h"

#include "../utility/testing_macros.hpp"
#include "../utility/print_function.hpp"
#include "../utility/strutil.h"

#include "../builtins/Variable.h"
#include "../builtins/Function.h"
#include "MooseParser.h"

using namespace std;

namespace moose {

void init_symtab(Parser::symbol_table_t& symtab)
{
    symtab.add_function("ln", MooseParser::Ln);
    symtab.add_function("rand", MooseParser::Rand);  // between 0 and 1
    symtab.add_function("rnd", MooseParser::Rand);   // between 0 and 1
    symtab.add_function("srand", MooseParser::SRand);
    symtab.add_function("rand2", MooseParser::Rand2);
    symtab.add_function("srand2", MooseParser::SRand2);
    symtab.add_function("fmod", MooseParser::Fmod);
}

MooseParser::MooseParser()
{
    symbolTable_.add_constants();
    init_symtab(symbolTable_);
    expression_.register_symbol_table(symbolTable_);
    SetExpr(expr_);
}

MooseParser::~MooseParser()
{
}

/*-----------------------------------------------------------------------------
 *  User defined function here.
 *-----------------------------------------------------------------------------*/
double MooseParser::Ln( double v )
{
    return std::log(v);
}

double MooseParser::Rand( )
{
    return moose::mtrand();
}

double MooseParser::SRand( double seed = -1 )
{
    if( seed >= 0 )
        moose::mtseed( (unsigned int) seed );
    return moose::mtrand();
}

double MooseParser::Rand2( double a, double b )
{
    return moose::mtrand( a, b );
}

double MooseParser::SRand2( double a, double b, double seed = -1 )
{
    if( seed >= 0 )
        moose::mtseed( (unsigned int) seed );
    return moose::mtrand( a, b );
}

double MooseParser::Fmod( double a, double b )
{
    return fmod(a, b);
}


/*-----------------------------------------------------------------------------
 *  Get/Set
 *-----------------------------------------------------------------------------*/
Parser::symbol_table_t& MooseParser::GetSymbolTable()
{
    return symbolTable_;
}

double MooseParser::GetVarValue(const string& name) const
{
    return symbolTable_.get_variable(name)->value();
}

Parser::varmap_type MooseParser::GetConstants() const
{
    Parser::varmap_type constants;
    Parser::varmap_type vars;
    symbolTable_.get_variable_list(vars);
    for (auto var : vars) {
        if (symbolTable_.is_constant_node(var.first)) {
            constants.push_back(var);
        }
    }
    return constants;
}

void MooseParser::PrintSymbolTable(void) const
{
    stringstream ss;
    auto symbTable = symbolTable_;
    vector<pair<string, double>> vars;
    auto n = symbTable.get_variable_list(vars);
    ss << "More Information:\nTotal variables " << n << ".";
    for (auto i : vars)
        ss << "\t" << i.first << "=" << i.second << " "
           << symbTable.get_variable(i.first)->ref();
    cerr << ss.str() << endl;
}

/*-----------------------------------------------------------------------------
 *  Other function.
 *-----------------------------------------------------------------------------*/
bool MooseParser::DefineVar( const string varName, double* const val)
{
    // Use in copy assignment.
    auto* existing = symbolTable_.get_variable(varName);
    if (existing){
        existing->ref() = *val;
        return true;
    }
    return symbolTable_.add_variable(varName, *val);
}

void MooseParser::DefineConst( const string& constName, const double value )
{
    if (symbolTable_.is_constant_node(constName)) {
        cout << "Warning: Ignoring attempt to change existing constant "
             << constName << endl;
    }
    else if (!symbolTable_.add_constant(constName, value)) {
        cout << "Warning: Failed to set constant " << constName << " = "
             << value << endl;
    }
}

void MooseParser::DefineFun1( const string& funcName, double (&func)(double) )
{
    // Add a function. This function currently handles only one argument
    // function.
    num_user_defined_funcs_ += 1;
    symbolTable_.add_function(funcName, func);
}


/* --------------------------------------------------------------------------*/
/**
 * @Synopsis  EXPRTK does not have && and || but have 'and' and 'or' symbol.
 * Replace && with 'and' and '||' with 'or'.
 *
 * @Param user_expr
 *
 * @Returns
 */
/* ----------------------------------------------------------------------------*/
string MooseParser::Reformat( const string user_expr )
{
    string expr( user_expr );

    // Replate || with 'or'
    moose::str_replace_all( expr, "||", " or " );
    // Replace && with 'and'
    moose::str_replace_all( expr, "&&", " and " );

    // Trickt business: Replace ! with not but do not change !=
    moose::str_replace_all( expr, "!=", "@@@" ); // placeholder
    moose::str_replace_all( expr, "!", " not " );
    moose::str_replace_all( expr, "@@@", "!=" ); // change back @@@ to !=

    return expr;
}

/* --------------------------------------------------------------------------*/
/**
 * @Synopsis  Set expression on parser.
 *
 * @Param user_expr
 *
 * @Returns
 */
/* ----------------------------------------------------------------------------*/
bool MooseParser::SetExpr(const string& user_expr)
{
    ASSERT_FALSE( user_expr.empty(), "Empty expression" );
    expr_ = Reformat(user_expr);
    return CompileExpr();
}

bool MooseParser::ParseVariables(const string& expr, vector<string>& vars)
{

    ASSERT_FALSE(expr.empty(),
                 __func__ << ": Empty expression not allowed here");

    Parser::symbol_table_t symtab;
    Parser::expression_t expression;
    Parser::parser_t parser;
    parser.enable_unknown_symbol_resolver();
    symtab.add_constants();
    init_symtab(symtab);
    expression.register_symbol_table(symtab);
    bool res = parser.compile(expr, expression);
    if (!res) {
        Parser::varmap_type varmap;
        stringstream ss;
        ss << "Failed to parse '" << expr << "' :" << endl;
        for (unsigned int i = 0; i < parser.error_count(); ++i) {
            Parser::error_t error = parser.get_error(i);
            ss << "Error[" << i << "] Position: " << error.token.position
               << " Type: [" << exprtk::parser_error::to_str(error.mode)
               << "] Msg: " << error.diagnostic << endl;

            // map is
            auto n = symtab.get_variable_list(varmap);
            ss << "More Information:\nTotal variables " << n << ".";
            for (auto i : varmap)
                ss << "\t" << i.first << "=" << i.second << " "
                   << symtab.get_variable(i.first)->ref();
            ss << endl;
        }
        // Throw the error, this is handled in callee.
        throw moose::Parser::exception_type(ss.str());
    }
    vector<string> varlist;
    symtab.get_variable_list(varlist);
    for (auto name : varlist) {
        if (!symtab.is_constant_node(name)) {
            vars.push_back(name);
        }
    }
    return res;
}

/* --------------------------------------------------------------------------*/
/**
 * @Synopsis  Compile a given expression.
 *
 * @Returns Return true if successful, throws exception if compilation fails.
 * Exception includes a detailed diagnostic.
 */
/* ----------------------------------------------------------------------------*/
bool MooseParser::CompileExpr()
{
    // User should make sure that symbol table has been setup. Do not raise
    // exception here. User can set expression again.
    // GCC specific
    ASSERT_FALSE(expr_.empty(),
                 __func__ << ": Empty expression not allowed here");

    // expression_.release();
    // symbolTable_.clear_variables();
    Parser::parser_t parser;
    parser.enable_unknown_symbol_resolver();
    valid_ = parser.compile(expr_, expression_);
    // This should never occur, as we are running this as a second pass
    if (!valid_) {
        expr_ = "";
        stringstream ss;
        ss << "Failed to parse '" << expr_ << "' :" << endl;
        for (unsigned int i = 0; i < parser.error_count(); ++i)
        {
            Parser::error_t error = parser.get_error(i);
            ss << "Error[" << i << "] Position: " << error.token.position
               << " Type: [" << exprtk::parser_error::to_str(error.mode)
               << "] Msg: " << error.diagnostic << endl;

            // map is
            Parser::varmap_type vars;
            auto n = symbolTable_.get_variable_list(vars);
            ss << "More Information:\nTotal variables " << n << ".";
            for (auto i : vars)
                ss << "\t" << i.first << "=" << i.second << " "
                   << symbolTable_.get_variable(i.first)->ref();
            ss << endl;
        }
        valid_ = false;
        throw moose::Parser::exception_type(ss.str());
    }
    return valid_;
}


double MooseParser::Derivative(const string& name, unsigned int nth) const
{
    if(nth > 3)
    {
        cout << "Error: " << nth << "th derivative is not supported." << endl;
        return 0.0;
    }
    if(nth == 3)
        return exprtk::third_derivative(expression_, name);
    if(nth == 2)
        return exprtk::second_derivative(expression_, name);
    return exprtk::derivative(expression_, name);
}

double MooseParser::Eval(bool check) const
{
    if(! valid_)
    {
        throw runtime_error("MooseParser::Eval: Invalid parser state.");
    }

    if(expr_.empty())
    {
        cout << "MooseParser::Eval: Warn: Expr is empty " << endl;
        return 0.0;
    }

    // PrintSymbolTable();
    // Make sure that no symbol is unknown at this point. Else emit error. The
    // Function::reinit must take of it.
    return expression_.value();
}


double MooseParser::Diff( const double a, const double b ) const
{
    return a-b;
}

bool MooseParser::IsConst(const string& name) const
{

    return symbolTable_.is_constant_node(name);
}

double MooseParser::GetConst(const string& name ) const
{
    if(!IsConst(name)) {
    // if(!GetSymbolTable().type_store.is_constant(name)) {
        cout << "Warning: no constant defined with name " << name << endl;
        return 0.0;
    }
    return symbolTable_.get_variable(name)->value();
}

void MooseParser::ClearVariables( )
{
    expr_ = "";
    expression_.release();
    symbolTable_.clear_variables();
}

void MooseParser::ClearAll( )
{
  ClearVariables();
  symbolTable_.clear_local_constants();
}

const string& MooseParser::GetExpr() const
{
    return expr_;
}

// void MooseParser::LinkVariables(vector<Variable*>& xs, vector<double*>& ys, double* t)
// {
//     for(unsigned int i = 0; i < xs.size(); i++)
//         DefineVar('x'+to_string(i), xs[i]->ref());

//     for (unsigned int i = 0; i < ys.size(); i++)
//         DefineVar('y'+to_string(i), ys[i]);

//     DefineVar("t", t);
// }

// void MooseParser::LinkVariables(vector<shared_ptr<Variable>>& xs, vector<shared_ptr<double>>& ys, double* t)
// {
//     for(unsigned int i = 0; i < xs.size(); i++)
//         DefineVar('x'+to_string(i), xs[i]->ref());

//     for (unsigned int i = 0; i < ys.size(); i++)
//         DefineVar('y'+to_string(i), ys[i].get());

//     DefineVar("t", t);
// }



} // namespace moose.
