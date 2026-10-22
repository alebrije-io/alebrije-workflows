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
WORKFLOW = os.path.join(REPO_ROOT, ".github", "workflows", "cross-repo-trigger.yml")


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
        resources.append(
            (sid, Resource.from_contents(doc, default_specification=DRAFT7))
        )
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
        "rewards.earned",
        {"user_id": "22222222-2222-2222-2222-222222222222", "amount": 10},
    )
    errors = [e.message for e in v.iter_errors(event)]
    assert errors == [], f"real rewards.earned outbox event rejected: {errors}"


def test_rewards_redeemed_validates_against_real_outbox_envelope_shape():
    v = _validator_for("rewards.redeemed.v1.json")
    event = _outbox_envelope(
        "rewards.redeemed",
        {"user_id": "22222222-2222-2222-2222-222222222222", "amount": 5},
    )
    errors = [e.message for e in v.iter_errors(event)]
    assert errors == [], f"real rewards.redeemed outbox event rejected: {errors}"


def test_rewards_points_expiring_soon_validates_against_real_outbox_envelope_shape():
    """ADR-001 v2 of rewards (D2, fase 1.6): the notice leaves through the outbox
    with the member's subject; contact fields are optional, the expiry is not."""
    v = _validator_for("rewards.points.expiring_soon.v1.json")
    data = {
        "event_type": "rewards.points.expiring_soon",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "user_id": "22222222-2222-2222-2222-222222222222",
        "contact_id": "33333333-3333-3333-3333-333333333333",
        "contact_phone": "525555501941",
        "amount": 140,
        "reason": "expiring_soon",
        "metadata": {"expires_at": "2026-10-24T03:00:00Z", "expires_on": "2026-10-24"},
        "occurred_at": "2026-10-21T06:00:00Z",
    }
    errors = [e.message for e in v.iter_errors(_outbox_envelope("rewards.points.expiring_soon", data))]
    assert errors == [], f"real rewards.points.expiring_soon outbox event rejected: {errors}"

    no_subject = {k: val for k, val in data.items() if k not in ("contact_id", "contact_phone")}
    assert [e.message for e in v.iter_errors(_outbox_envelope("rewards.points.expiring_soon", no_subject))] == []

    bad_phone = dict(data, contact_phone="+52 55 5550 1941")
    assert list(v.iter_errors(_outbox_envelope("rewards.points.expiring_soon", bad_phone))), \
        "a non-canonical phone must be rejected (ADR-142)"
    no_expiry = dict(data, metadata={})
    assert list(v.iter_errors(_outbox_envelope("rewards.points.expiring_soon", no_expiry))), \
        "the expiry is required"


def _field_ops_envelope(event_type: str, data: dict) -> dict:
    """Mirrors AlebrijeCommon.Events.Publish.build_envelope/3 as field-ops'
    Workers.EventPublisher calls it (telemetry metadata under data)."""
    return {
        "event_id": "0190b8c0-3333-7a4b-9c2d-3e4f5a6b7c8d",
        "event_type": event_type,
        "event_version": "1.0",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "timestamp": "2026-10-21T08:40:00Z",
        "producer": {"service": "alebrije-mod-field-ops-ex", "version": "0.0.118"},
        "data": data,
    }


def test_field_ops_inventory_moved_validates_and_rejects_impossible_movements():
    """ADR-37 §18.4: one movement of the inventory book, as EventPublisher relays it."""
    v = _validator_for("field_ops.inventory.moved.v1.json")
    data = {
        "movement_id": "44444444-4444-4444-4444-444444444444",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "context_id": None,
        "technician_id": "55555555-5555-5555-5555-555555555555",
        "part_id": "66666666-6666-6666-6666-666666666666",
        "kind": "sale",
        "quantity_delta": -3,
        "balance_after": 9,
        "document_type": "sale",
        "document_id": "77777777-7777-7777-7777-777777777777",
        "transfer_id": None,
        "occurred_at": "2026-10-21T08:39:00Z",
        "m_count": 1,
    }
    event = _field_ops_envelope("field_ops.inventory.moved", data)
    assert [e.message for e in v.iter_errors(event)] == []

    for bad in (
        dict(data, quantity_delta=0),
        dict(data, balance_after=-1),
        dict(data, kind="teleport"),
        {k: val for k, val in data.items() if k != "movement_id"},
    ):
        assert list(v.iter_errors(_field_ops_envelope("field_ops.inventory.moved", bad))), bad


def _sale_metadata(**overrides) -> dict:
    """The telemetry metadata AlebrijeFieldOps.Sales.emit/2 sends for both sale events."""
    data = {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "context_id": None,
        "sale_id": "88888888-8888-8888-8888-888888888888",
        "seller_id": "55555555-5555-5555-5555-555555555555",
        "folio": 7,
        "customer_crm_contact_id": "99999999-9999-9999-9999-999999999999",
        "modality": "autosale",
        "status": "delivered",
        "currency": "MXN",
        "subtotal": "30.00",
        "discount_total": "2.00",
        "tax_total": "4.48",
        "total": "32.48",
        "line_count": 1,
        "business_date": "2026-10-21",
        "confirmed_at": "2026-10-21T09:00:00.000000Z",
        "cancel_reason": None,
        "m_count": 1,
    }
    data.update(overrides)
    return data


def test_field_ops_sale_confirmed_validates_and_rejects_impossible_sales():
    """ADR-37 §18.4: a confirmed route sale, as EventPublisher relays it."""
    v = _validator_for("field_ops.sale.confirmed.v1.json")
    data = _sale_metadata()
    assert [e.message for e in v.iter_errors(_field_ops_envelope("field_ops.sale.confirmed", data))] == []

    presale = dict(data, modality="presale", status="confirmed", discount_total="0")
    assert [e.message for e in v.iter_errors(_field_ops_envelope("field_ops.sale.confirmed", presale))] == []

    for bad in (
        dict(data, folio=0),
        dict(data, total=32.48),
        dict(data, total="32.485"),
        dict(data, status="pending_authorization"),
        dict(data, status="cancelled"),
        dict(data, modality="consignment"),
        dict(data, cancel_reason="no"),
        dict(data, line_count=0),
        {k: val for k, val in data.items() if k != "folio"},
    ):
        assert list(v.iter_errors(_field_ops_envelope("field_ops.sale.confirmed", bad))), bad


def test_field_ops_sale_cancelled_validates_and_requires_its_reason():
    """ADR-37 §18.4: a cancelled sale that had a folio, as EventPublisher relays it."""
    v = _validator_for("field_ops.sale.cancelled.v1.json")
    data = _sale_metadata(status="cancelled", cancel_reason="devolución")
    assert [e.message for e in v.iter_errors(_field_ops_envelope("field_ops.sale.cancelled", data))] == []

    for bad in (
        dict(data, cancel_reason=None),
        dict(data, cancel_reason=""),
        dict(data, status="delivered"),
        dict(data, folio=None),
        {k: val for k, val in data.items() if k != "cancel_reason"},
    ):
        assert list(v.iter_errors(_field_ops_envelope("field_ops.sale.cancelled", bad))), bad


def test_field_ops_settlement_closed_validates_and_rejects_impossible_days():
    """ADR-37 §18.4: a closed end-of-day settlement, as EventPublisher relays it."""
    v = _validator_for("field_ops.settlement.closed.v1.json")
    data = {
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "context_id": None,
        "settlement_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "seller_id": "55555555-5555-5555-5555-555555555555",
        "business_date": "2026-10-21",
        "currency": "MXN",
        "expected_cash": "30.00",
        "declared_cash": "28.00",
        "cash_difference": "-2.00",
        "card_total": "0.00",
        "transfer_total": "0.00",
        "credit_total": "20.00",
        "stock_difference_value": "-10.00",
        "total_difference": "-12.00",
        "sales_count": 2,
        "closed_at": "2026-10-21T23:10:00.000000Z",
        "m_count": 1,
    }
    event = _field_ops_envelope("field_ops.settlement.closed", data)
    assert [e.message for e in v.iter_errors(event)] == []

    for bad in (
        dict(data, declared_cash="-1.00"),
        dict(data, total_difference=-12.0),
        dict(data, cash_difference="-2.005"),
        dict(data, sales_count=-1),
        {k: val for k, val in data.items() if k != "settlement_id"},
    ):
        assert list(v.iter_errors(_field_ops_envelope("field_ops.settlement.closed", bad))), bad


def test_appointment_rescheduled_validates_and_requires_the_new_place():
    """ADR-37 §18.3: the flat envelope agenda's Outbox.envelope_for/2 stages
    when an appointment's time or home address changes (agenda 0.0.239)."""
    v = _validator_for("appointment.rescheduled.v1.json")
    event = {
        "event_type": "appointment.rescheduled",
        "appointment_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "tenant_id": "22222222-2222-2222-2222-222222222222",
        "calendar_id": "33333333-3333-3333-3333-333333333333",
        "contact_id": "44444444-4444-4444-4444-444444444444",
        "contact_phone": "+525555500990",
        "status": "scheduled",
        "start_time": "2026-10-21T16:00:00.000000Z",
        "end_time": "2026-10-21T16:20:00.000000Z",
        "domicile_address": '{"city":"CDMX","street":"Calle Pruebas 12"}',
        "service_type": "lab_domicile",
        "context_id": "",
    }
    assert [e.message for e in v.iter_errors(event)] == []
    # No home address travels as an empty string, never null.
    assert [e.message for e in v.iter_errors(dict(event, domicile_address=""))] == []

    for bad in (
        dict(event, event_type="appointment.cancelled"),
        dict(event, domicile_address=None),
        {k: val for k, val in event.items() if k != "start_time"},
        {k: val for k, val in event.items() if k != "end_time"},
        {k: val for k, val in event.items() if k != "appointment_id"},
    ):
        assert list(v.iter_errors(bad)), bad


# ===========================================================================
# ADR-179 (2026-10-21): approvals. notifications-ex Approvals.Publisher relays
# notifications.approval_outbox to events:approvals with the
# Publish.build_envelope/3 shape (event_id = the outbox row id, context_id
# when the request has one); `data` is Approvals.Record.payload/1.
# ===========================================================================
def _approval_envelope(event_type: str, data: dict) -> dict:
    return {
        "event_id": "0190b8c0-4444-7a4b-9c2d-3e4f5a6b7c8d",
        "event_type": event_type,
        "event_version": "1.0",
        "tenant_id": "11111111-1111-1111-1111-111111111111",
        "timestamp": "2026-10-21T20:00:00Z",
        "producer": {"service": "alebrije-svc-notifications-ex", "version": "0.3.244"},
        "context_id": "22222222-2222-2222-2222-222222222222",
        "data": data,
    }


def _approval_data(**overrides) -> dict:
    data = {
        "approval_id": "0190b8c0-5555-7a4b-9c2d-3e4f5a6b7c8d",
        "kind": "field_ops.sale_discount",
        "subject_module": "field_ops",
        "subject_type": "sale",
        "subject_id": "0190b8c0-6666-7a4b-9c2d-3e4f5a6b7c8d",
        "context_id": "22222222-2222-2222-2222-222222222222",
        "status": "approved",
        "level": 1,
        "amount": "1240.00",
        "currency": "MXN",
        "decided_by_user_id": "0190b8c0-7777-7a4b-9c2d-3e4f5a6b7c8d",
        "decided_at": "2026-10-21T20:00:00.123456Z",
        "decision_channel": "panel",
        "policy_version": 0,
        "idempotency_key": "sale:0190b8c0-6666-7a4b-9c2d-3e4f5a6b7c8d:discount",
    }
    data.update(overrides)
    return data


_UNDECIDED = {"decided_by_user_id": None, "decided_at": None, "decision_channel": None}


def test_approval_decided_validates_and_needs_who_decided():
    """ADR-179 D7: a person decided; who, when and where travel with it."""
    v = _validator_for("approval.decided.v1.json")
    for data in (_approval_data(), _approval_data(status="rejected", amount=None, currency=None)):
        assert [e.message for e in v.iter_errors(_approval_envelope("approval.decided", data))] == []

    for bad in (
        _approval_data(status="expired"),
        _approval_data(decided_by_user_id=None),
        _approval_data(decision_channel="sms"),
        _approval_data(kind="discount"),
        _approval_data(amount=1240.0),
        _approval_data(level=0),
        {k: val for k, val in _approval_data().items() if k != "idempotency_key"},
    ):
        assert list(v.iter_errors(_approval_envelope("approval.decided", bad))), bad


def test_approval_expired_and_cancelled_carry_no_decider():
    """ADR-179 D3/§7.1: expired is nobody answering (counts as a rejection);
    cancelled is the subject gone. Neither names a decider."""
    for event_type, status in (("approval.expired", "expired"), ("approval.cancelled", "cancelled")):
        v = _validator_for(f"{event_type}.v1.json")
        data = _approval_data(status=status, **_UNDECIDED)
        assert [e.message for e in v.iter_errors(_approval_envelope(event_type, data))] == []

        for bad in (
            _approval_data(status="approved", **_UNDECIDED),
            _approval_data(status=status),
            dict(data, policy_version=-1),
        ):
            assert list(v.iter_errors(_approval_envelope(event_type, bad))), (event_type, bad)


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
            if (
                "FLAT payload (does NOT use the envelope.v1 data-nested shape)"
                not in desc
            ):
                errors.append(f"{name}: missing allOf and missing FLAT payload marker")
            props = schema.get("properties", {})
            if "const" not in props.get("event_type", {}):
                errors.append(
                    f"{name}: missing top-level event_type const (flat schema)"
                )
    assert errors == [], errors


def _required_fields_missing_description(
    schema_node: dict, path: str = ""
) -> list[str]:
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
    assert errors == [], (
        f"{len(errors)} required field(s) missing description: {errors}"
    )


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
