"""
moose.channels._proto
======================
Prototype management: create and cache HHChannel objects under /library.

Every unique (model_id, suffix, temperature) triple maps to exactly one
prototype element at ``/library/{ion}_{suffix}_{model_id}_T{T_int}``.
Prototypes are created once; all subsequent calls return the existing element.
moose.copy() is used at insert time so that gate tables are shared across
compartments.

Q10 temperature correction
--------------------------
The ICG omnimodel was fitted at ``T_REF = 6.3 °C`` (the temperature used in
HHanalyse.py).  When a different simulation temperature is requested:

* **Tau correction** is baked into the expression by scaling the ``A``
  coefficient:  ``tau_scale = Q10_tau ^ ((T_ref - T) / 10)``
  (a lower temperature → slower kinetics → larger tau).

* **Gbar correction** is stored in ``proto.Gbar`` as a multiplicative factor:
  ``gbar_scale = Q10_g ^ ((T - T_ref) / 10)``
  :func:`_insert.insert` then multiplies: ``copy.Gbar = user_gbar * proto.Gbar``.

If ``Q10_tau`` or ``Q10_g`` is ``None`` / 0 in the CSV row, no correction is
applied for that quantity (treated as Q10 = 1).
"""

# Reference temperature at which the omnimodel fits were performed (°C).
T_REF = 6.3

_LIBRARY_PATH = '/library'
_PROTO_SEP    = '_'          # separator in prototype name


def _proto_name(ion_class: str, suffix: str, model_id: int,
                temperature: float) -> str:
    # Encode temperature as integer tenths to avoid decimal in element name
    t_tag = f'T{round(temperature * 10):d}'
    return f'{ion_class}{_PROTO_SEP}{suffix}{_PROTO_SEP}{model_id}{_PROTO_SEP}{t_tag}'


def _ensure_library():
    """Create /library neutral element if it does not exist."""
    import moose
    if not moose.exists(_LIBRARY_PATH):
        moose.Neutral(_LIBRARY_PATH)


def _q10_scale(q10, delta_T: float, default: float = 1.0) -> float:
    """Return ``Q10 ^ (delta_T / 10)``; falls back to *default* if q10 is falsy."""
    if not q10:
        return default
    return float(q10) ** (delta_T / 10.0)


def make_prototype(db, model_id: int, suffix: str, sm_model='best',
                   temperature: float = T_REF):
    """
    Return a MOOSE HHChannel prototype under ``/library``.

    The call is **idempotent**: if the prototype already exists it is returned
    immediately without touching the database or rebuilding expressions.

    ``proto.Gbar`` is set to the Q10 conductance scale factor relative to the
    reference temperature (1.0 when ``temperature == T_REF``).
    :func:`_insert.insert` multiplies this by the user-supplied conductance.

    Parameters
    ----------
    db : ICGChannelDB
        Loaded channel database.
    model_id : int
        ModelDB numeric ID.
    suffix : str
        NMODL SUFFIX name (e.g. ``'naf'``).
    sm_model : int or 'best'
        SM variant (1–5) or ``'best'`` (lowest tau error, default).
    temperature : float
        Simulation temperature in °C.  Default is ``T_REF`` (6.3 °C),
        the temperature at which the omnimodel fits were performed.

    Returns
    -------
    moose.HHChannel
        The prototype element at ``/library/<name>``.
    """
    import moose
    from moose.channels._db import _build_expressions, DEFAULT_EK, infer_ion

    gate_rows = db.get_gate_rows(model_id, suffix)
    ion_class = gate_rows[0].get('ion_class') or infer_ion(suffix)
    name      = _proto_name(ion_class, suffix, model_id, temperature)
    path      = f'{_LIBRARY_PATH}/{name}'

    _ensure_library()

    if moose.exists(path):
        return moose.element(path)

    # ── Q10 scales (use first gate row; same per channel) ─────────────────────
    q10_tau  = gate_rows[0].get('q10_tau')
    q10_g    = gate_rows[0].get('q10_g')
    dT       = temperature - T_REF

    # tau: higher T → faster kinetics → smaller tau  →  scale < 1 when T > T_ref
    tau_scale  = _q10_scale(q10_tau, -dT)   # note: negative dT = T_ref - T
    # gbar: higher T → more conductance → scale > 1 when T > T_ref
    gbar_scale = _q10_scale(q10_g,    dT)

    # ── build channel ─────────────────────────────────────────────────────────
    chan      = moose.HHChannel(path)
    chan.Gbar = gbar_scale                   # Q10-corrected scale; multiplied at insert
    chan.Ek   = DEFAULT_EK.get(ion_class, 0.0)

    if len(gate_rows) > 3:
        import warnings
        extra = [r['gate_var'] for r in gate_rows[3:]]
        warnings.warn(
            f'Channel {suffix!r} (model {model_id}) has {len(gate_rows)} gates '
            f'but HHChannel supports at most 3 (X/Y/Z). '
            f'Gate(s) {extra} will be ignored.',
            UserWarning, stacklevel=3)

    slot_names = ['X', 'Y', 'Z']
    for slot, row in zip(slot_names, gate_rows[:3]):
        sm      = (int(sm_model) if sm_model != 'best'
                   else int(row.get('best_sm') or 1))
        inf_expr, tau_expr = _build_expressions(row, sm, tau_scale=tau_scale)

        power = float(row.get('gate_power') or 1.0)
        setattr(chan, f'{slot}power', power)

        gate = moose.element(f'{path}/gate{slot}')
        gate.infExpr = inf_expr
        gate.tauExpr = tau_expr
        # Required for exprtk expression evaluation: build lookup tables
        gate.divs           = 3000
        gate.min            = -0.12    # V  (-120 mV)
        gate.max            =  0.08    # V  ( +80 mV)
        gate.useInterpolation = True

    return chan


def list_prototypes() -> list:
    """
    Return list of HHChannel prototypes currently in ``/library``.

    Each entry is a dict with keys ``name``, ``path``, ``ion_class``,
    ``suffix``, ``model_id``, ``Ek``.
    """
    import moose
    if not moose.exists(_LIBRARY_PATH):
        return []

    result = []
    for el in moose.wildcardFind(f'{_LIBRARY_PATH}/#[TYPE=HHChannel]'):
        parts = el.name.split(_PROTO_SEP, 3)   # ion, suffix, model_id, Ttag
        entry = {'name': el.name, 'path': el.path, 'Ek': el.Ek,
                 'gbar_scale': el.Gbar}
        if len(parts) >= 3:
            entry['ion_class'] = parts[0]
            entry['suffix']    = parts[1]
            try:
                entry['model_id'] = int(parts[2])
            except ValueError:
                entry['model_id'] = None
        if len(parts) == 4:
            t_tag = parts[3]
            try:
                entry['temperature'] = int(t_tag.lstrip('T')) / 10.0
            except ValueError:
                pass
        result.append(entry)
    return result
