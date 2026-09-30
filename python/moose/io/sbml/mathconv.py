"""Translate an SBML MathML AST (libsbml ``ASTNode``) into an exprtk
expression string suitable for a MOOSE ``Function``.

The translation is purely structural: operators and built-in MathML functions
are mapped to their exprtk equivalents, and every identifier (``AST_NAME``) is
resolved through a caller-supplied ``resolve`` callback. That callback is where
the reader injects unit/quantity conversions -- e.g. mapping an SBML species id
to ``x0/(NA*V)`` (concentration from molecule number) or a parameter id to its
numeric value.

Nodes we cannot represent (user-defined function calls that survived function
inlining, delay, algebraic constructs) raise :class:`UnsupportedMath` so the
caller can fall back or report the reaction/rule as unsupported rather than
emit a silently wrong expression.
"""

import libsbml

from .units import AVOGADRO


class UnsupportedMath(Exception):
    """The MathML tree contains a construct MOOSE cannot express."""


# MathML relational operators -> exprtk (used inside piecewise / triggers).
_RELATIONAL = {
    libsbml.AST_RELATIONAL_LT: '<',
    libsbml.AST_RELATIONAL_LEQ: '<=',
    libsbml.AST_RELATIONAL_GT: '>',
    libsbml.AST_RELATIONAL_GEQ: '>=',
    libsbml.AST_RELATIONAL_EQ: '==',
    libsbml.AST_RELATIONAL_NEQ: '!=',
}


# MathML built-in unary functions -> exprtk name (applied as name(arg)).
_UNARY = {
    libsbml.AST_FUNCTION_ABS: 'abs',
    libsbml.AST_FUNCTION_EXP: 'exp',
    libsbml.AST_FUNCTION_LN: 'log',
    libsbml.AST_FUNCTION_FLOOR: 'floor',
    libsbml.AST_FUNCTION_CEILING: 'ceil',
    libsbml.AST_FUNCTION_SIN: 'sin',
    libsbml.AST_FUNCTION_COS: 'cos',
    libsbml.AST_FUNCTION_TAN: 'tan',
    libsbml.AST_FUNCTION_ARCSIN: 'asin',
    libsbml.AST_FUNCTION_ARCCOS: 'acos',
    libsbml.AST_FUNCTION_ARCTAN: 'atan',
    libsbml.AST_FUNCTION_SINH: 'sinh',
    libsbml.AST_FUNCTION_COSH: 'cosh',
    libsbml.AST_FUNCTION_TANH: 'tanh',
}


def to_exprtk(node, resolve):
    """Return an exprtk expression string for ``node``.

    Parameters
    ----------
    node : libsbml.ASTNode
        Root of the MathML tree (e.g. from ``KineticLaw.getMath()``).
    resolve : callable(str) -> str
        Maps an SBML identifier to an exprtk sub-expression (already
        parenthesised where needed by the caller).
    """
    if node is None:
        raise UnsupportedMath('empty MathML')
    return _emit(node, resolve)


def _emit(node, resolve):
    t = node.getType()

    # --- literals -------------------------------------------------------
    if t == libsbml.AST_INTEGER:
        return repr(node.getInteger())
    if t in (libsbml.AST_REAL, libsbml.AST_REAL_E, libsbml.AST_RATIONAL):
        return repr(node.getValue())
    if t == libsbml.AST_NAME_AVOGADRO:
        return repr(AVOGADRO)
    if t == libsbml.AST_NAME_TIME:
        return 't'
    if t == libsbml.AST_CONSTANT_E:
        return repr(2.718281828459045)
    if t == libsbml.AST_CONSTANT_PI:
        return 'pi'
    if t in (libsbml.AST_CONSTANT_TRUE,):
        return '1'
    if t in (libsbml.AST_CONSTANT_FALSE,):
        return '0'

    # --- identifiers ----------------------------------------------------
    if t == libsbml.AST_NAME:
        return resolve(node.getName())

    # --- n-ary arithmetic ----------------------------------------------
    if t == libsbml.AST_PLUS:
        return _nary(node, resolve, '+', '0')
    if t == libsbml.AST_TIMES:
        return _nary(node, resolve, '*', '1')
    if t == libsbml.AST_MINUS:
        n = node.getNumChildren()
        if n == 1:  # unary minus
            return f'(-{_emit(node.getChild(0), resolve)})'
        return f'({_emit(node.getChild(0), resolve)} - {_emit(node.getChild(1), resolve)})'
    if t == libsbml.AST_DIVIDE:
        return f'({_emit(node.getChild(0), resolve)} / {_emit(node.getChild(1), resolve)})'
    if t in (libsbml.AST_POWER, libsbml.AST_FUNCTION_POWER):
        return f'pow({_emit(node.getChild(0), resolve)}, {_emit(node.getChild(1), resolve)})'

    # --- built-in functions --------------------------------------------
    if t in _UNARY:
        return f'{_UNARY[t]}({_emit(node.getChild(0), resolve)})'
    if t == libsbml.AST_FUNCTION_ROOT:
        # root(degree, radicand); degree defaults to 2 (sqrt).
        if node.getNumChildren() == 1:
            return f'sqrt({_emit(node.getChild(0), resolve)})'
        deg = _emit(node.getChild(0), resolve)
        rad = _emit(node.getChild(1), resolve)
        return f'pow({rad}, 1.0/({deg}))'
    if t == libsbml.AST_FUNCTION_LOG:
        # log(base, x) -> logn; single arg is log base 10.
        if node.getNumChildren() == 1:
            return f'log10({_emit(node.getChild(0), resolve)})'
        base = _emit(node.getChild(0), resolve)
        x = _emit(node.getChild(1), resolve)
        return f'(log({x}) / log({base}))'
    if t == libsbml.AST_FUNCTION_PIECEWISE:
        return _piecewise(node, resolve)

    # --- relational / logical (used inside piecewise / triggers) --------
    if t in _RELATIONAL:
        return (f'({_emit(node.getChild(0), resolve)} {_RELATIONAL[t]} '
                f'{_emit(node.getChild(1), resolve)})')
    if t == libsbml.AST_LOGICAL_AND:
        return _nary(node, resolve, 'and', '1')
    if t == libsbml.AST_LOGICAL_OR:
        return _nary(node, resolve, 'or', '0')
    if t == libsbml.AST_LOGICAL_NOT:
        return f'(not({_emit(node.getChild(0), resolve)}))'

    name = node.getName() if node.isName() else libsbml.ASTNode.getType(node)
    raise UnsupportedMath(f'unhandled MathML node type={t} name={name!r}')


def _nary(node, resolve, op, identity):
    n = node.getNumChildren()
    if n == 0:
        return identity
    parts = [_emit(node.getChild(i), resolve) for i in range(n)]
    return '(' + f' {op} '.join(parts) + ')'


def _piecewise(node, resolve):
    # children: value0, cond0, value1, cond1, ..., [otherwise]
    n = node.getNumChildren()
    pairs = n // 2
    otherwise = _emit(node.getChild(n - 1), resolve) if n % 2 == 1 else '0'
    expr = otherwise
    for i in reversed(range(pairs)):
        value = _emit(node.getChild(2 * i), resolve)
        cond = _emit(node.getChild(2 * i + 1), resolve)
        expr = f'if({cond}, {value}, {expr})'
    return expr
