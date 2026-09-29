"""Adapter registration hub.

Importing this package imports each adapter for its ``@register`` side effect, so
``build_data_source`` can resolve every source by name. Adding a source = a new
subpackage + one import line here; no other adapter is touched.
"""

from algo_download.adapters import dukascopy, gdelt, gdelt_ngrams, gpr  # noqa: F401
