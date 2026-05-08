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

---

## Workflows Audit — 2026-05-07

A comprehensive audit of all 28 workflows, 9 custom actions, and meta-files was conducted. P1 items fixed in this session are listed below. Remaining items require future work.

### Fixed in session 2026-05-07
- approved-base-images.json: schema key mismatch (base_images→images)
- reusable-notify.yml: deprecated ::set-output replaced with $GITHUB_OUTPUT
- reusable-security-scan.yml: gitleaks step added, OSV exit code configurable
- reusable-benchmark.yml: Python exit code propagation from heredoc fixed
- reusable-openapi-check.yml: [allow-breaking-change] override implemented
- reusable-event-schema-check.yml: JSON parse errors exit 1 (not breaking change), regex narrowed
- validate-self.yml: actionlint job, timeout audit, inputs injection checks added
- reusable-test-go.yml + reusable-test-elixir.yml: inputs.* injection via run blocks fixed
- reusable-mutation-test.yml: Elixir muzak || true removed, hard fail
- reusable-property-tests.yml: artifact uploads added for all 4 languages
- reusable-test-go-matrix.yml: Go 1.25 added
- reusable-test-elixir-matrix.yml: Elixir 1.17+OTP26 added
- ci-cost-aggregator.yml: pagination added, hardcoded git author removed
- cross-repo-trigger.yml: concurrency added, JSON injection fixed
- CODEOWNERS: typo @ileonelperia→@ileonelperea fixed, missing entries added
- README.md: 18 undocumented workflows added to table
- node-version.json: ci_matrix added
- PULL_REQUEST_TEMPLATE.md: documentation checkbox added
- reusable-canary-deploy.yml: sed pipe vulnerability fixed
- bump-version/bump.sh: set -euo pipefail, portable sed
- check-tenant-id-leak: comprehensive UUID regex, case-insensitive matching
- wait-for-metrics: script consolidated to bundled check-metrics.sh, bc fallback
- post-coverage-comment: istanbul-json parsing expanded to branches/functions/statements
- event-schemas: control-medico→control_medico naming fixed (P1)
- event-schemas: auth-enhanced/payments-enhanced/rewards-enhanced hyphen→underscore

### DEBT-W01: reusable-release-extended.yml — No goreleaser/docker/cosign jobs
- **What**: Release workflow missing artifact publishing, Docker image build+push, cosign signing
- **Effort**: L
- **Status**: OPEN

### DEBT-W02: trigger-canary action — Flagger CRD structure may be incorrect
- **What**: canaryMetrics field in patch may not exist in Flagger Canary CRD spec; weights may not apply
- **Effort**: M (requires Flagger docs review + cluster testing)
- **Status**: OPEN

### DEBT-W03: generate-postmortem action — template incomplete
- **What**: Missing incident commander, related services, deployment context, escalation path
- **Effort**: S
- **Status**: OPEN

### DEBT-W04: cross-repo-trigger.yml — PR creation not implemented
- **What**: Does not open PRs in consumer repos with updated workflow version pins
- **Effort**: M
- **Status**: OPEN

### DEBT-W05: ci-cost-aggregator.yml — No Slack reporting or growth alerts
- **Effort**: S — Status: OPEN

### DEBT-W06: reusable-notify.yml — PagerDuty not implemented
- **Vault path needed**: alebrije/data/pagerduty/routing-key
- **Effort**: S — Status: OPEN

### DEBT-W07: validate-self.yml — No approved-base-images.json schema validation job
- **Effort**: XS — Status: OPEN

### DEBT-W08: Dead shell scripts in custom actions
- **What**: bump-version/bump.sh + parse-semver.sh unused; trigger-canary/apply-weight.sh unused
- **Effort**: S — Status: OPEN

### DEBT-W09: README.md — No usage examples for Go, Elixir, TypeScript
- **Effort**: S — Status: OPEN

### DEBT-W10: validate-test-pool.sh — Python-only scope
- **What**: Does not validate Go or Elixir test files
- **Effort**: M — Status: OPEN

### DEBT-W11: Event schemas — 21 required fields missing descriptions
- **What**: cadences, crm, field_ops, notifications, payments schemas lack description on some required fields
- **Effort**: S — Status: OPEN

### DEBT-W12: setup-vault-token — Token masking depends on upstream action
- **Effort**: XS — Status: OPEN
