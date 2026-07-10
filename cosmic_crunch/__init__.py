#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''

cosmic_crunch: download JPL GENESIS COSMIC radio-occultation ASCII files and
convert them to netCDF4.

The single source of truth for the package version lives here (``__version__``)
and is read at build time by hatchling (see ``pyproject.toml`` ->
``[tool.hatch.version]``).

Kept intentionally light: importing the package must not import the ``fetch`` or
``convert`` submodules, so that ``import cosmic_crunch`` has no side effects.

'''

__author__ = "Erick Edward Shepherd"
__version__ = "2.1.0"
