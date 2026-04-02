"""
moose.channels._db
==================
Database layer: load channel_db.csv / modeldb_popularity.csv and provide
search + expression-building utilities.

Adapted from icg_moose_channel.py (Chintaluri et al. 2025 omnimodel).

SM model equations (V in mV inside exprtk, v in Volts from MOOSE):
  Steady-state:
    SM1/3/4/5:  σ(V) = 1 / (1 + exp(-a·V + b))
    SM2:        σ(V) = c / (1 + exp(-a·V + b)) + d

  Time constant:
    τ(V) = A / (exp(-(b1·dV + c1·dV² + d1·dV³ [+e1·dV⁴])) +
                exp( (b2·dV + c2·dV² + d2·dV³ [+e2·dV⁴])))
    where dV = V - vh  (V in mV, τ in ms → converted to s in exprtk)
"""

import csv
import re
from collections import defaultdict
from textwrap import shorten

# ── default reversal potentials (V) ──────────────────────────────────────────

DEFAULT_EK = {
    'Na':    0.050,
    'K':    -0.077,
    'Ca':    0.120,
    'KCa':  -0.077,
    'IH':   -0.030,
    'Other': 0.000,
}

_ION_EK_HINTS = [
    (re.compile(r'\bna[fpxs]?\b',              re.I), 'Na'),
    (re.compile(r'\bca[lntrphq]?\b|hva|lva',  re.I), 'Ca'),
    (re.compile(r'\bk[adm]?r?\b|kdr|kahp|kv\d|kc\b|k2\b|kcnq', re.I), 'K'),
    (re.compile(r'\bkca\b|bk\b|sk\b',         re.I), 'KCa'),
    (re.compile(r'\bih\b|hcn|h\b',            re.I), 'IH'),
]


def infer_ion(name: str) -> str:
    """Guess ion class from channel suffix name."""
    name = name.lower()
    for pattern, ion in _ION_EK_HINTS:
        if pattern.search(name):
            return ion
    return 'Other'


# ── exprtk expression builders ────────────────────────────────────────────────

def _fmt(x) -> str:
    """Format a float for exprtk: wrap negatives in parens to avoid sign errors."""
    if x is None:
        return '0'
    s = f'{float(x):.10g}'
    return f'({s})' if float(x) < 0 else s


def build_inf_expr(sm_type: int, a, b, c=1.0, d=0.0) -> str:
    """
    Return an exprtk infExpr string.  v is in Volts (MOOSE SI); the expression
    converts internally: V_mV = v * 1e3.

    SM1/3/4/5:  1 / (1 + exp(-(a * V_mV) + b))
    SM2:        c * (above) + d   when c≠1 or d≠0
    """
    a_s  = _fmt(a)
    b_s  = _fmt(b)
    core = f'1 / (1 + exp(-({a_s} * (v * 1e3)) + {b_s}))'
    if sm_type == 2 and (
        abs(float(c or 1.0) - 1.0) > 1e-6 or abs(float(d or 0.0)) > 1e-6
    ):
        return f'{_fmt(c)} * ({core}) + {_fmt(d)}'
    return core


def _poly_term(coeff, dv_expr: str, power: int) -> str:
    """Return ' + coeff*dV^power' exprtk fragment; empty string if coeff ≈ 0."""
    if coeff is None or abs(float(coeff)) < 1e-30:
        return ''
    c_s = _fmt(coeff)
    if power == 1:
        return f' + {c_s} * {dv_expr}'
    return f' + {c_s} * ({dv_expr})^{power}'


def build_tau_expr(A, vh, b1, c1=None, d1=None, e1=None,
                   b2=None, c2=None, d2=None, e2=None,
                   tau_scale: float = 1.0) -> str:
    """
    Return an exprtk tauExpr string (v in Volts, result in seconds).

    τ(V) = A_s / (exp(-(poly1)) + exp(poly2))
    where dV = v*1e3 - vh  (mV), A is converted ms → s.

    Parameters
    ----------
    tau_scale : float
        Multiplicative factor applied to A before conversion.
        Used to bake in Q10 temperature correction at prototype-build time:
        ``tau_scale = Q10_tau ** ((T_ref - T) / 10)``
        so that the expression evaluates correctly at temperature T without
        needing a temperature variable in the expression.
    """
    A_s  = _fmt(float(A) * tau_scale * 1e-3)   # ms → s, with Q10 scaling
    vh_s = _fmt(vh)
    dv   = f'(v * 1e3 - {vh_s})'

    p1  = f'{_fmt(b1)} * {dv}'
    p1 += _poly_term(c1, dv, 2)
    p1 += _poly_term(d1, dv, 3)
    p1 += _poly_term(e1, dv, 4)

    p2  = f'{_fmt(b2)} * {dv}'
    p2 += _poly_term(c2, dv, 2)
    p2 += _poly_term(d2, dv, 3)
    p2 += _poly_term(e2, dv, 4)

    return f'{A_s} / (exp(-({p1})) + exp({p2}))'


# ── CSV loading ───────────────────────────────────────────────────────────────

def load_channel_db(path) -> list:
    """Load channel_db.csv → list of row dicts with typed fields."""
    float_fields = {
        'gbar_default', 'q10_tau', 'q10_g',
        'sm1_err1_ss', 'sm1_err1_tau', 'sm2_err1_ss', 'sm2_err1_tau',
        'sm3_err1_ss', 'sm3_err1_tau', 'sm4_err1_ss', 'sm4_err1_tau',
        'sm5_err1_ss', 'sm5_err1_tau',
        'a', 'b', 'c', 'd', 'A', 'vh',
        'b1', 'c1', 'd1', 'e1', 'b2', 'c2', 'd2', 'e2',
    }
    int_fields  = {'model_id', 'best_sm', 'gate_power'}
    bool_fields = {'sm1_fit', 'sm2_fit', 'sm3_fit', 'sm4_fit', 'sm5_fit'}
    rows = []
    with open(path, newline='', encoding='utf-8') as fh:
        for row in csv.DictReader(fh):
            for f in float_fields - int_fields:
                v = row.get(f, '')
                row[f] = float(v) if v not in ('', 'None', None) else None
            for f in int_fields:
                try:
                    row[f] = int(row.get(f, ''))
                except (ValueError, TypeError):
                    row[f] = None
            for f in bool_fields:
                row[f] = row.get(f, '').lower() == 'true'
            rows.append(row)
    return rows


def load_popularity(path) -> dict:
    """Load modeldb_popularity.csv → {model_id: row_dict}."""
    result = {}
    try:
        with open(path, newline='', encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                try:
                    result[int(row['model_id'])] = row
                except (ValueError, KeyError):
                    pass
    except FileNotFoundError:
        pass
    return result


# ── database class ────────────────────────────────────────────────────────────

class ICGChannelDB:
    """
    Search the ICGenealogy channel database and build exprtk expressions.

    Parameters
    ----------
    channel_db_path : path-like
        Path to channel_db.csv.
    popularity_db_path : path-like, optional
        Path to modeldb_popularity.csv.
    """

    def __init__(self, channel_db_path, popularity_db_path=None):
        self._rows = load_channel_db(channel_db_path)
        self._pop  = (load_popularity(popularity_db_path)
                      if popularity_db_path else {})

        self._by_model  = defaultdict(list)
        self._by_suffix = defaultdict(lambda: defaultdict(list))
        for r in self._rows:
            mid, suf = r['model_id'], r['suffix']
            if mid:
                self._by_model[mid].append(r)
            if mid and suf:
                self._by_suffix[mid][suf].append(r)

    # ── search ────────────────────────────────────────────────────────────────

    def search(self, author=None, year=None, model_id=None,
               ion_class=None, suffix=None) -> list:
        """
        Return list of matching model dicts::

            [{'model_id': int, 'meta': dict, 'channels': {suffix: [gate_rows]}}]

        All parameters are optional; combine freely.

        Parameters
        ----------
        author : str   Partial, case-insensitive author name.
        year   : int   Publication year.
        model_id : int Exact ModelDB ID.
        ion_class : str  'Na', 'K', 'Ca', 'KCa', or 'IH'.
        suffix : str   Partial NMODL SUFFIX name (e.g. 'naf', 'kdr').
        """
        year_s = str(year) if year else None
        mid_i  = int(model_id) if model_id else None

        candidates = set(self._by_model)
        if mid_i is not None:
            candidates &= {mid_i}

        if author or year_s:
            matched = set()
            for mid in candidates:
                meta = self._pop.get(mid, {})
                text = (meta.get('authors', '') + ' ' +
                        meta.get('model_name', '')).lower()
                if author and author.lower() not in text:
                    continue
                if year_s and meta.get('year', '').strip() != year_s:
                    continue
                matched.add(mid)
            candidates = matched

        if ion_class or suffix:
            matched = set()
            for mid in candidates:
                for suf, gates in self._by_suffix[mid].items():
                    if ion_class and gates[0].get('ion_class', '').lower() != ion_class.lower():
                        continue
                    if suffix and suffix.lower() not in suf.lower():
                        continue
                    matched.add(mid)
                    break
            candidates = matched

        results = []
        for mid in sorted(candidates):
            chans = {
                suf: gates
                for suf, gates in self._by_suffix[mid].items()
                if (not ion_class or gates[0].get('ion_class', '').lower() == ion_class.lower())
                and (not suffix or suffix.lower() in suf.lower())
            } or dict(self._by_suffix[mid])
            results.append({'model_id': mid,
                            'meta':     self._pop.get(mid, {}),
                            'channels': chans})
        return results

    def ion_classes(self) -> list:
        """Return sorted list of distinct ion classes in the database."""
        return sorted({
            r['ion_class'] for r in self._rows if r.get('ion_class')
        })

    # ── display ───────────────────────────────────────────────────────────────

    def show_results(self, results, max_rows=20):
        """Pretty-print a table of search results."""
        if not results:
            print('No matches found.')
            return
        print(f'\n{"#":<4} {"ModelDB ID":<12} {"Year":<6} '
              f'{"Authors":<35} {"Channels"}')
        print('─' * 90)
        for i, r in enumerate(results[:max_rows]):
            meta  = r['meta']
            auth  = shorten(meta.get('authors', ''), 34, placeholder='…')
            yr    = meta.get('year', '?')
            chans = shorten(
                ', '.join(
                    f"{s}({g[0]['ion_class']})"
                    for s, g in sorted(r['channels'].items()) if g
                ), 40, placeholder='…')
            print(f'[{i:<2}] {r["model_id"]:<12} {yr:<6} {auth:<35} {chans}')
        if len(results) > max_rows:
            print(f'  … and {len(results) - max_rows} more')
        print()

    def show_channels(self, result):
        """Print gate/power summary for one search result."""
        mid  = result['model_id']
        meta = result['meta']
        name = meta.get('model_name', f'ModelDB {mid}')
        print(f'\nModel {mid}: {shorten(name, 70, placeholder="…")}')
        auth = meta.get('authors', '')
        if auth:
            print(f'  {shorten(auth, 60, placeholder="…")} ({meta.get("year","?")})')
        print(f'\n  {"#":<4} {"Suffix":<16} {"Ion":<6} '
              f'{"Gates (var^power)":<26} {"gbar":<12} {"best SM"}')
        print('  ' + '─' * 72)
        for i, (suf, gates) in enumerate(sorted(result['channels'].items())):
            ion   = gates[0].get('ion_class', '?')
            gbar  = gates[0].get('gbar_default')
            gbar_s = f'{float(gbar):.4g}' if gbar else '?'
            sm    = gates[0].get('best_sm', '?')
            gate_s = '  '.join(
                f"{g['gate_var']}^{int(g['gate_power']) if g['gate_power'] else '?'}"
                for g in sorted(gates, key=lambda x: x['gate_var'])
            )
            print(f'  [{i:<2}] {suf:<16} {ion:<6} {gate_s:<26} {gbar_s:<12} SM{sm}')
        print()

    # ── expression retrieval ──────────────────────────────────────────────────

    def get_gate_rows(self, model_id: int, suffix: str) -> list:
        """Return sorted list of gate rows for (model_id, suffix)."""
        rows = list(self._by_suffix.get(model_id, {}).get(suffix, []))
        if not rows:
            raise KeyError(f'Channel {suffix!r} not found for model {model_id}')
        # activation (positive a) first → X gate
        return sorted(rows, key=lambda r: (0 if (r['a'] or 0) > 0 else 1,
                                           r['gate_var']))

    def get_expressions(self, model_id: int, suffix: str,
                        gate_var: str, sm_model='best') -> tuple:
        """
        Return ``(infExpr, tauExpr)`` strings for a single gate.

        Does not create any MOOSE objects.
        """
        rows = self._by_suffix.get(model_id, {}).get(suffix, [])
        row  = next((r for r in rows if r['gate_var'] == gate_var), None)
        if row is None:
            raise KeyError(
                f'Gate {gate_var!r} not found in {suffix!r} of model {model_id}')
        sm = int(sm_model) if sm_model != 'best' else int(row.get('best_sm') or 1)
        return _build_expressions(row, sm)


# ── expression builder (internal) ─────────────────────────────────────────────

def _build_expressions(row: dict, sm: int, tau_scale: float = 1.0) -> tuple:
    """Build (infExpr, tauExpr) from a gate row at the given SM variant.

    Parameters
    ----------
    tau_scale : float
        Passed through to :func:`build_tau_expr`; bakes Q10 tau correction
        into the expression coefficient.
    """
    a  = row['a'];  b  = row['b']
    c  = row.get('c') or 1.0
    d  = row.get('d') or 0.0
    A  = row['A'];  vh = row['vh']
    b1 = row['b1']; b2 = row.get('b2')
    c1 = row.get('c1'); c2 = row.get('c2')
    d1 = row.get('d1'); d2 = row.get('d2')
    e1 = row.get('e1'); e2 = row.get('e2')

    # Zero out higher-order terms that the SM variant doesn't use
    if sm == 4:
        c1 = d1 = e1 = c2 = d2 = e2 = None
    elif sm == 3:
        d1 = e1 = d2 = e2 = None
    elif sm in (1, 2):
        e1 = e2 = None

    return (build_inf_expr(sm, a, b, c, d),
            build_tau_expr(A, vh, b1, c1, d1, e1, b2, c2, d2, e2,
                           tau_scale=tau_scale))
