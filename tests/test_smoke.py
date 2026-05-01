"""Smoke test — verifies the package imports without errors."""


def test_import_arbiter():
    import arbiter  # noqa: F401


def test_import_submodules():
    from arbiter import diagnostics, feedback, observability, routing  # noqa: F401
