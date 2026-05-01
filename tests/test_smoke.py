"""Smoke test — verifies the package imports without errors."""


def test_import_arcpoint():
    import arcpoint  # noqa: F401


def test_import_submodules():
    from arcpoint import diagnostics, feedback, observability, routing  # noqa: F401
