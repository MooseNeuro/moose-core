# handler.py --- moose.io.FormatHandler implementation for SBML
#
# A wrapper over all the read logic in reader.py and all the write
# logic in writer.py, each exposing one module-level function
# (`reader.read`, `writer.write`) that does the real work and needs no
# knowledge of the other direction; this class just adapts them to the
# moose.io.base.FormatHandler protocol (paired read/write methods on
# one object, with the coverage report kept on self so callers can
# inspect what did not come through faithfully).

from moose import _moose

from . import reader, writer


class SBMLHandler:
    """Read and write SBML models as MOOSE reaction(-diffusion) networks.

    After a call to :meth:`read` or :meth:`write`, ``self.report`` holds a
    :class:`~.report.LoadReport` or :class:`~.report.WriteReport`
    respectively, recording what could not be represented faithfully (see
    the package docstring for the two directions' hard limits).
    """

    extensions = ('.xml', '.sbml')

    def __init__(self):
        self.report = None

    def read(self, filepath, loadpath=None, solver='gsl', validate=True):
        """Load the SBML document at ``filepath`` into a new MOOSE subtree
        rooted at ``loadpath`` and return that root element.

        ``loadpath`` defaults to ``/library/{model_name}``, with
        ``model_name`` taken from the SBML model's id/name, or else the
        source filename (see ``reader._default_model_name``).

        ``solver`` picks the chemical solver built over the result:
        ``'gsl'`` (default, deterministic ODE via Ksolve), ``'gssa'``
        (stochastic Gillespie via Gsolve), or ``'ee'`` (no solver built).
        ``validate`` controls whether libsbml errors on the document abort
        the load (:class:`SBMLValidationError`) or are ignored.
        """
        element, self.report = reader.read(
            filepath, loadpath, solver=solver, validate=validate)
        return element

    def write(self, modelpath, filepath, **options):
        """Write the MOOSE reaction(-diffusion) network rooted at
        ``modelpath`` to ``filepath`` as SBML, and return the ``modelpath``
        element unchanged (writing does not modify the MOOSE model).

        **options: 'report' (default None) - if specified, stores the
        report of the write operation in this report object,

        """
        self.report = writer.write(modelpath, filepath, **options)
        return _moose.element(modelpath)
