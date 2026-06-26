"""larch.core: shared leaf utilities.

Home for the most-depended-on leaf modules: ``proc`` (subprocess seam),
``config`` (tunables), ``logging_util`` (breadcrumbs + journal), ``redact``
(secret redaction), ``retry`` (transient retry), and ``run_context`` (frozen
run context). These import only stdlib, ``larch.io``, ``larch.errors``,
``larch.outcomes``, and each other.
"""
