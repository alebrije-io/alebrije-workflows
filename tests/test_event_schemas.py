#!/usr/bin/env python3
"""Behavior tests for the Alebrije event-schema registry and the
cross-repo-trigger orchestrator output wiring.

These cover two functional gaps closed in this repo (see TECHNICAL-DEBT.md):

  * DEBT-W14 — cross-repo-trigger.yml must write its orchestration outputs to
    $GITHUB_OUTPUT, never the deprecated/disabled ``::set-output`` worker
    command (no-op on current runners -> empty audit/report + lost run-id
    correlation).
  * DEBT-W13 — ``omnichannel.message.received.v1`` must surface the AQ-112
    ``sender_type``/``branch_id`` fields per-event (in addition to inheriting
    them from envelope.v1) and validate real events against the registry the
    way the common-lib validators do.

Run with:
    python3 -m pytest tests/test_event_schemas.py -v
or stand-alone (no pytest needed):
    python3 tests/test_event_schemas.py

Validation uses the same jsonschema/draft-07 contract documented in
event-schemas/README.md §5, resolving the envelope ``$ref`` by ``$id`` URL
through a local ``referencing`` registry (the same mapping the Python/Elixir/
Go validators perform when they load the registry from disk).
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

import yaml
from jsonschema import Draft7Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT7

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(REPO_ROOT, "event-schemas")
WORKFLOW = os.path.join(
    REPO_ROOT, ".github", "workflows", "cross-repo-trigger.yml"
)


# ---------------------------------------------------------------------------
# Registry helpers (resolve $id-keyed $ref the way common-lib validators do)
# ---------------------------------------------------------------------------
def _build_registry() -> Registry:
    """Register every schema file under its ``$id`` URL so allOf/$ref resolve."""
    resources = []
    for path in glob.glob(os.path.join(SCHEMA_DIR, "*.json")):
        doc = json.load(open(path))
        sid = doc.get("$id")
        if not sid:
            continue
        resources.append((sid, Resource.from_contents(doc, default_specification=DRAFT7)))
    return Registry().with_resources(resources)


def _validator_for(schema_file: str) -> Draft7Validator:
    schema = json.load(open(os.path.join(SCHEMA_DIR, schema_file)))
    return Draft7Validator(schema, registry=_build_registry())


def _valid_envelope(**overrides) -> dict:
    """A minimal envelope-valid omnichannel.message.received event."""
    event = {
        "event_id": "0190b8c0-1d3e-7a4b-9c2d-3e4f5a6b7c8d",
        "event_type": "omnichannel.message.received",
        "event_version": "1.0",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "timestamp": "2026-05-31T12:00:00Z",
        "producer": {"service": "alebrije-mod-omnichannel", "version": "0.1.0"},
        "data": {
            "conversation_id": "22222222-2222-2222-2222-222222222222",
            "message_id": "33333333-3333-3333-3333-333333333333",
            "channel": "whatsapp",
            "content_type": "text",
        },
    }
    event.update(overrides)
    return event


# ===========================================================================
# Gap 1 (DEBT-W14) — cross-repo-trigger writes to $GITHUB_OUTPUT, not ::set-output
# ===========================================================================
def _workflow_text() -> str:
    with open(WORKFLOW) as f:
        return f.read()


def test_no_deprecated_set_output_remains():
    """::set-output was disabled on GitHub runners in 2023 -> no executable
    emission of it remains (documentary comments are allowed)."""
    text = _workflow_text()
    offenders = []
    for line in text.splitlines():
        stripped = line.strip()
        # Skip pure-comment lines (YAML '#' or Python '#') and YAML comments.
        if stripped.startswith("#"):
            continue
        # The real bug emitted it: print(f"::set-output name=..."). Match the
        # worker-command token only where it is actually written to stdout.
        if "::set-output name=" in line:
            offenders.append(line)
    assert offenders == [], (
        "cross-repo-trigger.yml still emits the disabled ::set-output worker "
        f"command (no-op on current runners): {offenders}"
    )


def test_outputs_written_to_github_output():
    """The three orchestration outputs must write to $GITHUB_OUTPUT."""
    text = _workflow_text()
    # Each output key declared by the jobs must be produced via GITHUB_OUTPUT.
    for key in ("count=", "has-timeout=", "run-ids="):
        assert key in text, f"missing GITHUB_OUTPUT write for {key!r}"
    assert text.count('os.environ["GITHUB_OUTPUT"]') >= 2, (
        "expected GITHUB_OUTPUT writes in both prepare-dispatch and "
        "dispatch-workflows Python steps"
    )


def test_workflow_yaml_parses_and_keeps_declared_outputs():
    """The edit must not break YAML or drop the declared job outputs."""
    doc = yaml.safe_load(_workflow_text())
    jobs = doc["jobs"]
    # prepare-dispatch still declares dispatch-count / has-timeout outputs...
    prep_out = jobs["prepare-dispatch"]["outputs"]
    assert "dispatch-count" in prep_out and "has-timeout" in prep_out
    # ...mapped onto the validate step outputs we now write via $GITHUB_OUTPUT.
    assert "steps.validate.outputs.count" in prep_out["dispatch-count"]
    assert "steps.validate.outputs.has-timeout" in prep_out["has-timeout"]
    # dispatch-workflows still declares run-ids.
    assert "run-ids" in jobs["dispatch-workflows"]["outputs"]


def test_has_timeout_expression_still_template_substituted():
    """The has-timeout value keeps the Actions ${{ }} expression intact."""
    text = _workflow_text()
    assert re.search(
        r'has_timeout\s*=\s*"\$\{\{\s*inputs\.timeout-seconds\s*>\s*0\s*\}\}"',
        text,
    ), "has-timeout must keep the ${{ inputs.timeout-seconds > 0 }} expression"


# ===========================================================================
# Gap 2 (DEBT-W13) — AQ-112 sender_type/branch_id surfaced per-event + validate
# ===========================================================================
SCHEMA_FILE = "omnichannel.message.received.v1.json"


def test_aq112_fields_surfaced_in_event_schema():
    """sender_type + branch_id appear in the event's own properties (not only
    inherited), with AQ-112 documentation for consumers."""
    schema = json.load(open(os.path.join(SCHEMA_DIR, SCHEMA_FILE)))
    branch = schema["allOf"][-1]
    props = branch["properties"]
    assert "sender_type" in props, "sender_type not surfaced per-event"
    assert "branch_id" in props, "branch_id not surfaced per-event"
    # Constraints must mirror the envelope so allOf cannot contradict.
    assert set(props["sender_type"]["enum"]) == {
        "client",
        "employee",
        "tenant_admin",
        None,
    }
    assert props["branch_id"]["maxLength"] == 36
    # Consumer-facing documentation present.
    assert "AQ-112" in props["sender_type"]["description"]
    assert "AQ-112" in props["branch_id"]["description"]


def test_event_with_aq112_fields_validates():
    v = _validator_for(SCHEMA_FILE)
    event = _valid_envelope(sender_type="client", branch_id="branch-abc")
    errors = sorted(v.iter_errors(event), key=str)
    assert errors == [], f"valid AQ-112 event rejected: {[e.message for e in errors]}"


def test_event_without_aq112_fields_still_valid_backward_compat():
    """Backward compat: events emitted before AQ-112 omit the fields."""
    v = _validator_for(SCHEMA_FILE)
    event = _valid_envelope()
    assert list(v.iter_errors(event)) == []


def test_event_with_null_aq112_fields_valid():
    v = _validator_for(SCHEMA_FILE)
    event = _valid_envelope(sender_type=None, branch_id=None)
    assert list(v.iter_errors(event)) == []


def test_invalid_sender_type_rejected():
    v = _validator_for(SCHEMA_FILE)
    event = _valid_envelope(sender_type="hacker")  # not in enum
    msgs = [e.message for e in v.iter_errors(event)]
    assert msgs, "out-of-enum sender_type should be rejected"


def test_over_length_branch_id_rejected():
    v = _validator_for(SCHEMA_FILE)
    event = _valid_envelope(branch_id="x" * 37)  # > maxLength 36
    msgs = [e.message for e in v.iter_errors(event)]
    assert msgs, "branch_id over 36 chars should be rejected"


def test_envelope_still_defines_aq112_fields():
    """Guard the inherited source of truth stays intact."""
    env = json.load(open(os.path.join(SCHEMA_DIR, "envelope.v1.json")))
    assert "sender_type" in env["properties"]
    assert "branch_id" in env["properties"]
    # Neither is required -> all pre-AQ-112 events stay valid.
    assert "sender_type" not in env["required"]
    assert "branch_id" not in env["required"]


# ===========================================================================
# Gap 3 (DEBT-AUDIT-20260701-019-rewards) — envelope regex must admit the
# real 2-segment event_type strings rewards.earned/rewards.redeemed stamp,
# reproducing the exact wire shape alebrije-common-go's
# outbox.Poller.buildEnvelope() produces (event_id/event_type/event_version/
# tenant_id/timestamp/producer/data, event_type = row.EventType verbatim,
# i.e. the literal 2-segment string -- no reformatting happens in the
# poller). Before this fix envelope.v1.json's event_type pattern required
# exactly 3 dotted segments, so no real rewards.earned/redeemed event could
# ever validate (const:"rewards.earned" vs pattern requiring a 3rd segment
# are mutually unsatisfiable).
# ===========================================================================
def _outbox_envelope(event_type: str, data: dict) -> dict:
    """Mirrors alebrije-common-go outbox.Poller.buildEnvelope() (poller.go)."""
    return {
        "event_id": "0190b8c0-2222-7a4b-9c2d-3e4f5a6b7c8d",
        "event_type": event_type,
        "event_version": "1.0",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "timestamp": "2026-07-03T12:00:00Z",
        "producer": {"service": "outbox-poller"},
        "data": data,
    }


def test_envelope_event_type_pattern_admits_2_and_3_segment_names():
    env = json.load(open(os.path.join(SCHEMA_DIR, "envelope.v1.json")))
    pattern = re.compile(env["properties"]["event_type"]["pattern"])
    assert pattern.match("rewards.earned"), "2-segment producer literal must match"
    assert pattern.match("rewards.points.earned"), "3-segment default must still match"
    assert not pattern.match("rewards"), "single segment must still be rejected"
    assert not pattern.match("rewards."), "trailing dot must still be rejected"


def test_rewards_earned_validates_against_real_outbox_envelope_shape():
    v = _validator_for("rewards.earned.v1.json")
    event = _outbox_envelope(
        "rewards.earned", {"user_id": "22222222-2222-2222-2222-222222222222", "amount": 10}
    )
    errors = [e.message for e in v.iter_errors(event)]
    assert errors == [], f"real rewards.earned outbox event rejected: {errors}"


def test_rewards_redeemed_validates_against_real_outbox_envelope_shape():
    v = _validator_for("rewards.redeemed.v1.json")
    event = _outbox_envelope(
        "rewards.redeemed", {"user_id": "22222222-2222-2222-2222-222222222222", "amount": 5}
    )
    errors = [e.message for e in v.iter_errors(event)]
    assert errors == [], f"real rewards.redeemed outbox event rejected: {errors}"


def test_all_event_schemas_still_structurally_valid():
    """Regression of validate-self.yml AUDIT 11 (no schema broken by the edit).

    Mirrors the check-event-schemas-valid step in
    .github/workflows/validate-self.yml: `.example.json` fixtures are sample
    event instances (not schemas) and are excluded, and a schema without
    `allOf` is accepted only under the documented FLAT-payload exception
    (README.md section 2) -- a real producer whose wire shape has no envelope
    nesting, marked by the literal "FLAT payload (does NOT use the
    envelope.v1 data-nested shape)" string in its description.
    """
    errors = []
    for f in glob.glob(os.path.join(SCHEMA_DIR, "*.json")):
        name = os.path.basename(f)
        if "envelope" in name or ".base." in name or ".example." in name:
            continue
        schema = json.load(open(f))
        if "$id" not in schema:
            errors.append(f"{name}: missing $id")
        if "allOf" in schema:
            last = schema["allOf"][-1]
            props = last.get("properties", {})
            if "event_type" not in props:
                errors.append(f"{name}: missing event_type const")
            if "data" not in props:
                errors.append(f"{name}: missing data object")
        else:
            desc = schema.get("description", "")
            if "FLAT payload (does NOT use the envelope.v1 data-nested shape)" not in desc:
                errors.append(f"{name}: missing allOf and missing FLAT payload marker")
            props = schema.get("properties", {})
            if "const" not in props.get("event_type", {}):
                errors.append(f"{name}: missing top-level event_type const (flat schema)")
    assert errors == [], errors


def _required_fields_missing_description(schema_node: dict, path: str = "") -> list[str]:
    """Walk one schema document (JSON-Schema draft-07, this repo's dialect: plain
    ``allOf``/``properties``/``required``, no ``$ref`` resolution needed here since
    every event schema's own ``required`` list only ever names sibling
    ``properties`` it also declares -- not fields pulled in through envelope.v1's
    ``$ref``) and return ``"path.to.field"`` for every field that is BOTH listed
    in a ``required`` array AND missing its own ``description`` key (DEBT-W11).
    """
    missing: list[str] = []

    def walk(node, here: str) -> None:
        if isinstance(node, dict):
            props = node.get("properties", {})
            for req_name in node.get("required", []):
                field = props.get(req_name)
                if isinstance(field, dict) and "description" not in field:
                    missing.append(f"{here}.{req_name}" if here else req_name)
            for sub in node.get("allOf", []):
                walk(sub, here)
            for prop_name, prop_schema in props.items():
                walk(prop_schema, f"{here}.{prop_name}" if here else prop_name)
        elif isinstance(node, list):
            for item in node:
                walk(item, here)

    walk(schema_node, path)
    return missing


def test_required_fields_have_descriptions():
    """DEBT-W11 — every field named in a JSON-Schema ``required`` array (at any
    nesting level, including envelope.v1's own top-level ``required``) must
    carry its own ``description``. ``$ref``-only entries (``{"$ref": "..."}``)
    are skipped -- they have no ``properties``/``required`` of their own to
    walk, the referenced document is checked separately when its own file is
    globbed.

    This is the exact scan (unchanged) that measured 22 real gaps against
    HEAD before this session's fix -- see TECHNICAL-DEBT.md DEBT-W11 for the
    full list and the live rojo/verde control (revert one description with
    Edit, this test fails naming that exact field; restore, it passes).
    """
    errors = []
    for f in sorted(glob.glob(os.path.join(SCHEMA_DIR, "*.json"))):
        name = os.path.basename(f)
        if ".example." in name:
            continue
        schema = json.load(open(f))
        for missing in _required_fields_missing_description(schema):
            errors.append(f"{name}: {missing}")
    assert errors == [], f"{len(errors)} required field(s) missing description: {errors}"


# ---------------------------------------------------------------------------
# Stand-alone runner (no pytest dependency required)
# ---------------------------------------------------------------------------
def _run_standalone() -> int:
    tests = [
        obj
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:  # surface real errors, never swallow
            failures += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures} passed, {failures} failed, {len(tests)} total")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run_standalone())
