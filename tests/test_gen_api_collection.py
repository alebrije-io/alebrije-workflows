#!/usr/bin/env python3
"""Behavior tests for scripts/gen_api_collection.py (DEBT-001, reopened 2026-08-21).

Pattern copied from tests/test_approved_base_images.py: standalone-runnable
(``python3 tests/test_gen_api_collection.py``) AND pytest-discoverable, plain
``assert`` (no pytest fixtures required), module-level ``test_*`` functions
picked up automatically by the ``__main__`` block below. Unlike the workflow
gates re-implemented in that file (they live inline as ``shell: python3 {0}``
YAML blocks with no importable module), ``gen_api_collection.py`` is a real
``.py`` file, so these tests import it directly instead of re-implementing it.

The previous close of DEBT-001 was FALSE: the script existed and exited 0,
but its regex only matched gin/mux-style UPPERCASE verbs with a bare-word
handler, so it silently returned 0 endpoints against the fleet's real
go-chi/chi gateway ("exists" != "works"). These tests assert a NONZERO,
counted result against representative chi route shapes and (when the sibling
checkout is available) against the real gateway repo — so a regression back
to the old blind regex fails LOUD instead of exiting 0 with an empty result.

Run with:
    python3 -m pytest tests/test_gen_api_collection.py -v
or stand-alone (no pytest needed):
    python3 tests/test_gen_api_collection.py
"""
from __future__ import annotations

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

from gen_api_collection import APICollectionGenerator  # noqa: E402

# Real fleet gateway checked out as a sibling of alebrije-workflows, if present.
FLEET_ROOT = os.path.dirname(REPO_ROOT)
REAL_GATEWAY = os.path.join(FLEET_ROOT, "alebrije-api-gateway-go")


def _generate_from_content(tmp_dir, filename, content):
    """Write a throwaway .go file under tmp_dir and run the real generator
    against tmp_dir — exercises the exact code path CI invokes, not a
    reimplementation."""
    path = os.path.join(tmp_dir, filename)
    with open(path, "w") as fh:
        fh.write(content)
    gen = APICollectionGenerator(tmp_dir)
    return gen.generate()


def _mk_tmp_dir():
    import tempfile

    return tempfile.mkdtemp(prefix="gen-api-collection-test-")


# --------------------------------------------------------------------------
# DEBT-001 — the exact blind spot: chi Title-case verbs + non-bare handlers.
# --------------------------------------------------------------------------
def test_chi_titlecase_verb_with_bare_handler_is_detected():
    tmp = _mk_tmp_dir()
    collection = _generate_from_content(
        tmp, "router.go", 'r.Get("/health", depsHealth)\n'
    )
    paths = {ep["path"] for ep in collection["endpoints"]}
    assert "/health" in paths, (
        "chi-style Title-case verb (r.Get) with a bare handler must be "
        "detected — this alone was already a gap in the pre-fix regex"
    )


def test_chi_dotted_selector_handler_is_detected():
    """This is the shape that broke the ORIGINAL fix attempt too: the
    handler is a selector expression (pkg.Method), not a bare identifier."""
    tmp = _mk_tmp_dir()
    collection = _generate_from_content(
        tmp,
        "router.go",
        'r.Get("/artifacts/{id}/data/{queryID}", artifactsHandler.ProxyData)\n',
    )
    paths = {ep["path"] for ep in collection["endpoints"]}
    assert "/artifacts/{id}/data/{queryID}" in paths, (
        "chi handler as a dotted selector (artifactsHandler.ProxyData) must "
        "be detected"
    )


def test_chi_call_expression_handler_is_detected():
    """Handler as a zero/multi-arg call, e.g. health.LiveHandler() or
    startupHandler(cfg.WebhookEnabled, deps.db) — a single level of
    call-parens with no nested calls inside."""
    tmp = _mk_tmp_dir()
    collection = _generate_from_content(
        tmp,
        "router.go",
        'r.Get("/ready", health.LiveHandler())\n'
        'r.Get("/startup", startupHandler(cfg.WebhookEnabled, deps.db))\n',
    )
    paths = {ep["path"] for ep in collection["endpoints"]}
    assert "/ready" in paths, "call-expression handler (pkg.Func()) must be detected"
    assert "/startup" in paths, (
        "call-expression handler with args (fn(a, b)) must be detected"
    )


def test_gin_mux_uppercase_style_still_detected_no_regression():
    """The original (working) case this script was written for must keep
    working after widening the pattern for chi."""
    tmp = _mk_tmp_dir()
    collection = _generate_from_content(
        tmp, "router.go", 'router.POST("/api/v1/users", createUser)\n'
    )
    paths = {ep["path"] for ep in collection["endpoints"]}
    assert "/api/v1/users" in paths, "gin/mux UPPERCASE verb style regressed"


def test_zero_endpoints_against_a_file_with_no_routes_is_still_zero():
    """A directory that genuinely has no routes must still report 0 — the
    fix must not overmatch and invent endpoints out of thin air."""
    tmp = _mk_tmp_dir()
    collection = _generate_from_content(tmp, "notes.go", "package handler\n// no routes here\n")
    assert collection["endpoints"] == []


# --------------------------------------------------------------------------
# The exact regression this ticket is about: the REAL fleet gateway must not
# come back as 0 endpoints. Skips (does not silently pass) if the sibling
# checkout isn't present, so CI environments without the monorepo layout
# don't get a false green — the test is a no-op in that case, not a lie.
# --------------------------------------------------------------------------
def test_real_gateway_repo_yields_nonzero_endpoints():
    if not os.path.isdir(REAL_GATEWAY):
        print(f"SKIP: {REAL_GATEWAY} not checked out — cannot exercise real repo")
        return
    gen = APICollectionGenerator(REAL_GATEWAY)
    collection = gen.generate()
    count = len(collection["endpoints"])
    assert count > 0, (
        "Total endpoints: 0 against the REAL gateway is not clean, it's "
        "blind (DEBT-001) — the regex stopped matching this gateway's real "
        "router idiom again"
    )
    print(f"real gateway endpoint count: {count}")


if __name__ == "__main__":
    failures = 0
    for fn_name, fn in sorted(globals().items()):
        if fn_name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {fn_name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {fn_name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
