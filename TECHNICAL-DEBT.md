# Technical Debt — alebrije-workflows

> Updated: 2026-05-07. Per ADR-001 tracking.

## DEBT-001 — Missing scripts/gen-api-collection.sh

**Status**: CLOSED (both gen-api-collection.sh and gen_api_collection.py exist in scripts/)
**Priority**: P2 (was blocking)
**Impact**: `api-collection-gen.yml` workflow — script was referenced but missing
**Resolution**: Scripts created — now workflow can run

---

## DEBT-002 — Event schema registry incomplete

**Status**: OPEN
**Priority**: P3
**Impact**: ~27 event types published by the fleet now lack registered JSON schemas (agentic, campaigns, omnichannel, proyectos, catalog, agenda, control-medico, rewards, auth enhanced)
**Fix**: Add schemas for all missing event types — partial progress in Wave 1

---

## DEBT-003 — Bloque Q (Self-hosted runners) deferred

**Status**: DEFERRED — out of scope until fleet volume justifies infra ops
**Priority**: P4
**Impact**: Using GH-hosted runners (more expensive at scale)
**Trigger to revisit**: Fleet CI exceeds 5,000 min/month

---

## DEBT-004 — No automated cross-fleet version bump PRs

**Status**: OPEN
**Priority**: P3
**Impact**: When common-go/common-ex/common-python release, consumer repos don't get automatic update PRs with `go get -u`, `mix deps.update`, etc.
**Fix**: Implement worker in cross-repo-trigger.yml that opens PRs with updated dependencies

---

## DEBT-005 — ci-cost-aggregator requires GH App token

**Status**: OPEN
**Priority**: P3
**Impact**: Weekly CI cost report (ci-cost-aggregator.yml) needs a GH App token with Actions read permission across all repos
**Fix**: Create GH App in GitHub + configure secret in alebrije-infra

---

## AQ-001 — Event schema auto-publish to registry not implemented

**Question**: Should event schemas auto-publish to Confluent Schema Registry or a custom registry?
**Status**: NOT DECIDED
**Context**: reusable-event-schema-check.yml has breaking change detection but no auto-publish step

---

## AQ-002 — Multi-language release workflow not battle-tested in production

**Question**: Has reusable-release-extended.yml been validated in production for all language targets?
**Status**: FRAMEWORK EXISTS — not fully validated for Python/Elixir/TS (Go only proven)
**Risk**: May have untested edge cases for non-Go languages in semver bumping, changelog parsing, or publish targets

---

## AQ-003 — Custom actions completeness verification

**Question**: Are all 9 custom actions (.github/actions/*) fully implemented and documented?
**Status**: PARTIAL — all have action.yml but some need inline script review (bump-version/bump.sh, wait-for-metrics/check-metrics.sh, generate-postmortem template completeness)
**Risk**: Hidden issues in shell script portability or edge case handling
