# moose.channels — ICGenealogy Ion Channel Database

`moose.channels` provides a curated database of voltage-gated ion channel
models that can be searched and inserted into MOOSE compartment trees as
`HHChannel` objects.

## Channel database

The channel parameters in `data/channel_db.csv` are derived from the
**IonChannelGenealogy (ICG)** database and the **ion channel omnimodel**
described in Chintaluri et al. (2025).

### Selection criteria

Channels were included if:

1. The original NEURON `.mod` file ran without errors in the ICG voltage-clamp
   simulation pipeline (no ERROR FLAGS set in the omnimodel specification
   sheet).
2. At least one of the five standardised model variants (SM1–SM5, see below)
   produced a successful fit to the simulated steady-state and time-constant
   curves.

Of the 3,274 voltage-gated channels in the ICG database with omnimodel
specification sheets, **2,305 channels** (covering Na, K, Ca, KCa, and IH ion
classes) meet both criteria and are included here.  Channels excluded due to
simulation errors (845) or failed fits (288) are silently absent; querying a
missing channel raises a `KeyError`.

IH (HCN, hyperpolarisation-activated) channels activate on hyperpolarisation;
the same sigmoid formulation applies with a negative slope coefficient `a`.
Their SM fits were extracted directly from the pre-fitted ICG pickle
(``icg-pickles/icg-channels-IH.pkl``) using ``pickle_to_csv.py``.

### Standardised model formulation (omnimodel)

Each gating variable *x* is described by two voltage-dependent functions:

**Steady-state** (SM1/SM3/SM4/SM5):

    σ(V) = 1 / (1 + exp(−a·V + b))

**Modified sigmoid** (SM2):

    σ(V) = c / (1 + exp(−a·V + b)) + d

**Time constant** (all variants):

    τ(V) = A / (exp(−P₁) + exp(P₂))
    P₁ = b1·ΔV + c1·ΔV² + d1·ΔV³ [+ e1·ΔV⁴]
    P₂ = b2·ΔV + c2·ΔV² + d2·ΔV³ [+ e2·ΔV⁴]
    ΔV = V − vh

where *V* is in mV and *τ* is in ms.  The five SM variants differ in the
polynomial order used for the time constant:

| Variant | Steady-state | τ polynomial order | Parameters |
|---------|-------------|-------------------|------------|
| SM1     | sigmoid     | 3rd               | vh, A, b1, c1, d1, b2, c2, d2 |
| SM2     | mod. sigmoid | 3rd              | vh, A, b1, c1, d1, b2, c2, d2 |
| SM3     | sigmoid     | 2nd               | vh, A, b1, c1, b2, c2 |
| SM4     | sigmoid     | 1st               | vh, A, b1, b2 |
| SM5     | sigmoid     | 4th               | vh, A, b1, c1, d1, e1, b2, c2, d2, e2 |

The database stores parameters for the best-fitting SM variant for each gate
(lowest mean-squared error on the time-constant curve).

Fitted parameters were extracted from the omnimodel specification sheets
(`.omnimodel.md` files) published by ICGenealogy for each channel.  Parameters
are at the reference temperature **T_ref = 6.3 °C** (the temperature used
during NEURON simulation in HHanalyse).  Q10 correction factors (`q10_tau`,
`q10_g`) are included where available and applied automatically when a
simulation temperature other than T_ref is requested.

## Credits and citation

The channel parameters and omnimodel formulation are the work of the
**ICGenealogy project** and the **Vogels group** at IST Austria.

If you use `moose.channels` in your research, please cite:

> Chintaluri, C., Podlaski, W., Bozelos, P. A., Gonçalves, P. J.,
> Lueckmann, J.-M., Macke, J. H., & Vogels, T. P. (2025).
> **An ion channel omnimodel for standardized biophysical neuron modelling.**
> *bioRxiv*. https://doi.org/10.1101/2025.10.03.680368

and the IonChannelGenealogy database:

> Bahl, A., Stemmler, M. B., Herz, A. V. M., & Roth, A. (2012).
> **Automated optimization of a reduced layer 5 pyramidal cell model based on
> experimental data.**
> *Journal of Neuroscience Methods*, 210(1), 22–34.
> https://doi.org/10.1016/j.jneumeth.2012.04.006

The ICG web application and channel specification sheets are available at:
https://icg-explorer.org/visualizer

## Further reading

- MOOSE simulator: https://mooseneuro.org
- IonChannelGenealogy: https://icg-explorer.org
