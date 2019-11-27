##########################################
Release Notes
##########################################

PyPSA-Eur 0.1.0 (DATE)
======================

This is the first release of PyPSA-Eur:

* Documentation on installation, workflows and configuration settings is now available online at `pypsa-eur.readthedocs.io <pypsa-eur.readthedocs.io>`_ (`#65 <https://github.com/PyPSA/pypsa-eur/pull/65>`_).

* The ``conda`` environment files were updated and extended (`#81 <https://github.com/PyPSA/pypsa-eur/pull/81>`_).

* The power plant database was updated with extensive filtering options via ``pandas.query`` functionality (`#84 <https://github.com/PyPSA/pypsa-eur/pull/84>`_ and `#94 <https://github.com/PyPSA/pypsa-eur/pull/94>`_).

* Continuous integration testing with `Travis CI <https://travis-ci.org>`_ is now included for Linux, Mac and Windows (`#82 <https://github.com/PyPSA/pypsa-eur/pull/82>`_).

* Data dependencies were moved to `zenodo <https://zenodo.org/>`_ and are now versioned (`#60 <https://github.com/PyPSA/pypsa-eur/issues/60>`_).

* Data dependencies are now retrieved directly from within the snakemake workflow (`#86 <https://github.com/PyPSA/pypsa-eur/pull/86>`_).

* Emission prices can be added to marginal costs of generators through the keyworks ``Ep`` in the ``{opts}`` wildcard (`#100 <https://github.com/PyPSA/pypsa-eur/pull/100>`_).

* An option is introduced to add extendable nuclear power plants to the network (`#98 <https://github.com/PyPSA/pypsa-eur/pull/98>`_).

* Focus weights can now be specified for particular countries for the network clustering, which allows to set a proportion of the total number of clusters for particular countries (`#87 <https://github.com/PyPSA/pypsa-eur/pull/87>`_).

* A new rule :mod:`add_extra_components` allows to add additional components to the network only after clustering. It is thereby possible to model storage units (e.g. battery and hydrogen) in more detail via a combination of ``Store``, ``Link`` and ``Bus`` elements (`#97 <https://github.com/PyPSA/pypsa-eur/pull/97>`_).
