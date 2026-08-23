#!/usr/bin/env python3
"""Behavior tests for README.md's per-language usage examples (DEBT-W09).

DEBT-W09 was "README.md has no usage examples for Go, Elixir, TypeScript" --
closing it with prose alone would repeat the DEBT-001 mistake this session's
TECHNICAL-DEBT.md documents (a mechanism that LOOKS like it does its job but
was never checked against reality). So this isn't just "does the word 'Go'
appear in README.md" -- it re-derives the REAL ``workflow_call.inputs`` of
each reusable-test-*.yml via ``yaml.safe_load`` (ground truth, not retyped)
and asserts the README's example for that language actually names a handful
of those real inputs, inside that language's own section. If a workflow's
inputs change and nobody updates the README, this test goes red naming the
stale input -- the failure mode DEBT-W09 exists to prevent isn't "no
examples", it's "examples nobody keeps honest".

Pattern follows tests/test_approved_base_images.py / tests/test_event_schemas.py
(REPO_ROOT constant, stand-alone runner block, no pytest required).

Run with:
    python3 -m pytest tests/test_readme_examples.py -v
or stand-alone (no pytest needed):
    python3 tests/test_readme_examples.py
"""
from __future__ import annotations

import os
import re
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(REPO_ROOT, "README.md")
WORKFLOWS_DIR = os.path.join(REPO_ROOT, ".github", "workflows")
ACTIONS_DIR = os.path.join(REPO_ROOT, ".github", "actions")


def _real_inputs(workflow_filename: str) -> set[str]:
    """Ground truth: the real `on.workflow_call.inputs` keys of a workflow,
    parsed from the committed YAML -- never retyped/guessed."""
    path = os.path.join(WORKFLOWS_DIR, workflow_filename)
    doc = yaml.safe_load(open(path))
    # PyYAML parses the bare `on:` key as boolean True (YAML 1.1 quirk) --
    # both forms exist in this repo's workflows, so check both.
    on_block = doc.get("on", doc.get(True, {}))
    return set(on_block["workflow_call"]["inputs"].keys())


def _readme_section(heading: str) -> str:
    """Return the README.md text between `### <heading>` and the next `###`
    or `##` heading (whichever comes first)."""
    text = open(README, encoding="utf-8").read()
    start = text.index(f"### {heading}")
    rest = text[start + len(f"### {heading}") :]
    m = re.search(r"\n#{2,3} ", rest)
    return rest[: m.start()] if m else rest


def test_go_example_names_real_reusable_test_go_inputs():
    real_inputs = _real_inputs("reusable-test-go.yml")
    section = _readme_section("Go service (DEBT-W09)")
    assert "reusable-test-go.yml" in section
    named = {inp for inp in real_inputs if f"{inp}:" in section}
    assert len(named) >= 3, (
        f"Go README example names too few real reusable-test-go.yml inputs "
        f"(found {sorted(named)} of real set {sorted(real_inputs)})"
    )
    assert "reusable-test-go-matrix.yml" in section, (
        "Go section must point to the matrix variant for multi-version testing"
    )


def test_elixir_example_names_real_reusable_test_elixir_inputs():
    real_inputs = _real_inputs("reusable-test-elixir.yml")
    section = _readme_section("Elixir/Phoenix service (DEBT-W09)")
    assert "reusable-test-elixir.yml" in section
    named = {inp for inp in real_inputs if f"{inp}:" in section}
    assert len(named) >= 3, (
        f"Elixir README example names too few real reusable-test-elixir.yml "
        f"inputs (found {sorted(named)} of real set {sorted(real_inputs)})"
    )
    assert "reusable-test-elixir-matrix.yml" in section, (
        "Elixir section must point to the matrix variant for multi-version testing"
    )


def test_ts_example_names_real_reusable_test_ts_inputs():
    real_inputs = _real_inputs("reusable-test-ts.yml")
    section = _readme_section("TypeScript / frontend service (DEBT-W09)")
    assert "reusable-test-ts.yml" in section
    named = {inp for inp in real_inputs if f"{inp}:" in section}
    assert len(named) >= 3, (
        f"TS README example names too few real reusable-test-ts.yml inputs "
        f"(found {sorted(named)} of real set {sorted(real_inputs)})"
    )
    assert "reusable-test-node.yml" in section, (
        "TS section must point to reusable-test-node.yml for plain-Node services"
    )


def _readme_h2_section(heading: str) -> str:
    """Same idea as `_readme_section` but for `##` headings (the Custom
    Actions table lives at `##`, not `###`, per README.md's own structure)."""
    text = open(README, encoding="utf-8").read()
    start = text.index(f"## {heading}")
    rest = text[start + len(f"## {heading}") :]
    m = re.search(r"\n#{2,3} ", rest)
    return rest[: m.start()] if m else rest


def test_all_nine_custom_actions_documented_in_readme():
    """AQ-003 asked 'are all 9 custom actions fully implemented and
    documented?'. Ground truth, not a word-count: every real action
    directory under .github/actions/ must be named in the README's Custom
    Actions table, together with at least one of its REAL `inputs:` keys
    (re-derived via yaml.safe_load, same idiom as `_real_inputs` above) --
    so this goes red if a new action is added and never documented, or if
    an action's real inputs drift away from what the table claims."""
    action_dirs = sorted(
        d for d in os.listdir(ACTIONS_DIR)
        if os.path.isfile(os.path.join(ACTIONS_DIR, d, "action.yml"))
    )
    assert len(action_dirs) == 9, (
        f"expected 9 custom actions (AQ-003's own count), found "
        f"{len(action_dirs)}: {action_dirs} -- update AQ-003 and this test "
        f"together, don't let the count drift silently"
    )
    section = _readme_h2_section("Custom Actions (AQ-003)")
    undocumented = []
    for action_dir in action_dirs:
        if action_dir not in section:
            undocumented.append(f"{action_dir}: name missing from README table")
            continue
        doc = yaml.safe_load(
            open(os.path.join(ACTIONS_DIR, action_dir, "action.yml"))
        )
        real_inputs = set((doc.get("inputs") or {}).keys())
        if real_inputs and not any(f"`{inp}`" in section for inp in real_inputs):
            undocumented.append(
                f"{action_dir}: none of its real inputs {sorted(real_inputs)} "
                f"appear in the README table"
            )
    assert not undocumented, "AQ-003 gap(s) found:\n" + "\n".join(undocumented)


def test_ts_example_does_not_claim_a_secrets_block_that_does_not_exist():
    """reusable-test-ts.yml (unlike -go/-elixir) declares no `secrets:` under
    `workflow_call` -- the README must not invent a `secrets: GH_TOKEN`
    requirement for it (that would be documenting a contract that isn't real,
    the exact DEBT-001 failure class this session is hunting)."""
    doc = yaml.safe_load(open(os.path.join(WORKFLOWS_DIR, "reusable-test-ts.yml")))
    on_block = doc.get("on", doc.get(True, {}))
    assert "secrets" not in on_block["workflow_call"], (
        "reusable-test-ts.yml gained a real secrets: block -- update the "
        "README TS example (and this test) to match, don't just leave both stale"
    )
    section = _readme_section("TypeScript / frontend service (DEBT-W09)")
    assert "secrets:" not in section


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
