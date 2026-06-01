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

### Fixed in session 2026-05-31

- **reusable-property-tests.yml ts-property step (line 219): `|| true` no-op on `npx vitest run` removed — property gate is now FATAL.**
  - **Problem**: The fast-check step appended `|| true` to `npx vitest run ... --coverage=false`, making the
    property-testing job a no-op across the entire TS fan-out — a failing invariant / shrunk counterexample
    exited 0 and never failed CI. This is the exact anti-pattern that `validate-self.yml:183-189` audits for
    ("`|| true` in test/coverage steps — FATAL anti-pattern", Rule #11).
  - **Root-cause fix**: Dropped `|| true` inside the existing `if find ... | grep -q .` branch. When property
    test files EXIST → `npx vitest run` runs FATALLY (a failing property fails the job). When NO `*.property.test.{ts,js}`
    files exist → the pre-existing `else` branch emits `::notice::No *.property.test.ts files found (optional)` and
    exits 0 — an explicit conditional skip, NOT a no-op. Pattern mirrors `reusable-test-ts.yml:124-158`
    (fatal coverage gate, `# Fail if below threshold (fatal, no || true)`) and the python step of this same
    workflow (lines 86-92, advisory skip on missing `tests/property/`).
  - **Verification** (throwaway vitest@2.1.9 + fast-check@3.23.1 harness in /tmp, `bash -euo pipefail` = GH Actions default shell):
    - Failing property present → NEW step exit **1** (FATAL, vitest "Property failed after 1 tests"); OLD `|| true` line exit **0** (the masked bug).
    - All properties pass → NEW step exit **0** (no false-fail; vitest "Tests 1 passed").
    - No property files → NEW step exit **0** with `::notice::No *.property.test.ts files found (optional)` (explicit skip).
    - YAML re-validated: `yamllint` (CI invocation) exit 0 (only pre-existing document-start/truthy warnings, identical in sibling workflows); `python3 yaml.safe_load` OK, all 4 jobs intact.
  - **Effort**: S — **Status**: CLOSED

### DEBT-W14: reusable-property-tests.yml — Go & Elixir steps mask test failures via `|| { echo ...; }` (SAME no-op class as the just-fixed TS bug) — FIXED 2026-05-31

- **What**: The Go step (`go test ... || { echo "::notice"; }`) and Elixir step (`mix test ... || { echo "::notice"; }`)
  used the brace-block idiom to handle the "no property tests yet" case. Confirmed under `bash -euo pipefail`
  (GitHub Actions default shell) that `<failing-cmd> || { echo ...; }` exits **0** whether the command fails,
  passes, or finds nothing — so a genuinely failing Go/Elixir property silently passed CI. Same no-op class as
  the bare `|| true` removed from the TS step, only less obvious.
- **Root-cause fix**: Re-gated both steps with explicit existence detection → run-fatally / else explicit skip,
  mirroring the ts-property step of this same workflow + `reusable-test-ts.yml:124-158` (fatal coverage gate,
  `# Fail if below threshold (fatal, no || true)`) + `reusable-mutation-test.yml:140-161` (`if [ ! -f ... ]; then ... exit 1`):
  - **Go**: `if grep -rlqE '(func TestProperty)|(//go:build property)|(+build property)' --include='*_test.go' .; then go test -tags=property -run=TestProperty ./... -count=N -v; else echo "::notice::No property tests found ... — optional"; fi`.
    Existence detection is REQUIRED: `go test -run=TestProperty` itself exits 0 with "no tests to run" when nothing
    matches, which is indistinguishable from a real pass without the grep guard.
  - **Elixir**: `if grep -rlq '@tag :property' --include='*.exs' --include='*.ex' .; then mix test --include property --max-cases N; else echo "::notice::No property tests tagged with @tag :property found (optional)"; fi`.
  - Detection uses the EXISTENCE signals named in DEBT spec: Go = `TestProperty`/`+build property`/`//go:build property`;
    Elixir = `@tag :property`. When tests EXIST → fatal. When ABSENT → explicit `::notice::` skip (exit 0), NOT a no-op.
- **Verification** (throwaway exit-code harness in `/tmp`, `bash -e` = GH Actions default shell; output cited):
  - OLD masking idiom, failing cmd → exit **0** (the masked bug reproduced).
  - NEW Go gate: exist+passing → **0**; exist+FAILING → **1** (FATAL); absent → **0** (explicit skip). 3/3 PASS.
  - NEW Elixir gate: exist+passing → **0**; exist+FAILING → **1** (FATAL); absent → **0** (explicit skip). 3/3 PASS.
  - Detection greps (exact YAML commands): `go_has`→MATCH, `go_none`→NO MATCH, `ex_has`→MATCH, `ex_none`→NO MATCH (no false positives on empty dirs / non-`_test.go` files). Harness total: 10 passed, 0 failed; full step sim: 6 passed, 0 failed.
  - YAML re-validated with the EXACT `validate-self.yml` validate-yaml config:
    `yamllint -d "{extends: default, rules: {line-length: {max: 180}, comments: {min-spaces-from-content: 2}}}"`
    → exit **0** (only the two pre-existing `document-start` + `truthy` warnings, identical across sibling workflows, unchanged by this edit). `python3 yaml.safe_load` OK, all 4 jobs intact, `workflow_call` trigger + inputs preserved, no tabs.
  - Anti-pattern audit: zero `|| {` / `|| true` remain on any executable (non-comment) line; remaining matches are documentary comment references to the canonical pattern (consistent with the already-shipped TS step). `validate-self.yml check-anti-patterns` is WARN-only (never `exit 1`).
- **Effort**: M — **Priority**: P2 — **Status**: CLOSED

### DEBT-W13: envelope.v1 — AQ-112 sender_type/branch_id added (DONE) + per-event doc surfacing (OPEN)
- **What (DONE 2026-05-30, lane AQ112-ENVELOPE-PRODUCERS)**: `event-schemas/envelope.v1.json` gained
  two optional+nullable top-level fields — `sender_type` (enum `client|employee|tenant_admin|null`)
  and `branch_id` (string|null, maxLength 36). Neither is in `required`, so all existing events stay
  valid (backward-compat verified with jsonschema: validates with the fields, without them, and with
  explicit nulls; rejects out-of-enum sender_type + over-length branch_id). All `.base.`/event schemas
  inherit these via `allOf $ref envelope.v1.json` — no per-event schema edits were needed.
- **What (DONE 2026-05-31)**: `omnichannel.message.received.v1.json` now surfaces `sender_type` and
  `branch_id` per-event in its own `allOf[-1].properties` (siblings of `event_type`/`data`), each with
  AQ-112 consumer documentation describing the producer source (omnichannel conversation
  `sender_type` column / `context_id`). Constraints mirror the envelope (`sender_type` enum
  `client|employee|tenant_admin|null`, `branch_id` maxLength 36) so the merged `allOf` cannot
  contradict. Behavior verified with the documented jsonschema/draft-07 validator (registry resolves
  the envelope `$ref` by `$id`): events validate with the fields, without them (backward-compat), and
  with explicit nulls; out-of-enum `sender_type` and over-length `branch_id` are rejected. Tests:
  `tests/test_event_schemas.py` (test_aq112_fields_surfaced_in_event_schema,
  test_event_with_aq112_fields_validates, test_invalid_sender_type_rejected,
  test_over_length_branch_id_rejected, + backward-compat cases).
- **Effort**: XS — Status: **CLOSED** (schema DONE; per-event doc surfacing DONE)

---

### DEBT-W14: cross-repo-trigger.yml emitted disabled `::set-output` — orchestration outputs silently empty (FIXED)
- **What (was broken)**: `cross-repo-trigger.yml` (ADR-001 Bloque L) captured its three orchestration
  outputs (`count`, `has-timeout` in prepare-dispatch; `run-ids` in dispatch-workflows) via the
  `print("::set-output name=...")` worker command. GitHub disabled that command on hosted runners in
  2023, so each was a no-op: `prepare-dispatch.outputs.dispatch-count` was empty (report-status job
  printed a blank `Total targets`), and `steps.dispatch.outputs.run-ids` was never set (wait-completion
  run-id correlation degraded). Source: audit `AUDIT_FUNCTIONAL_GAPS_BY_MODULE_20260531.md` workflows
  gap #1 (P1/S), file:linea 94-95 + 210.
- **What (DONE 2026-05-31)**: replaced all three emissions with writes to
  `os.environ["GITHUB_OUTPUT"]` (the canonical pattern already used in
  `reusable-release-extended.yml:142-145`); the `has-timeout` value keeps its
  `${{ inputs.timeout-seconds > 0 }}` Actions expression (template-substituted before the heredoc runs).
  Added regression guard `validate-self.yml` AUDIT 17 `check-no-deprecated-set-output` (FATAL, exit 1,
  wired into `security-audit-summary` needs + fail-gate) — built so the guard never matches its own
  detection literal. Tests: `tests/test_event_schemas.py` (test_no_deprecated_set_output_remains,
  test_outputs_written_to_github_output, test_workflow_yaml_parses_and_keeps_declared_outputs,
  test_has_timeout_expression_still_template_substituted).
- **Side fix**: while editing the `validate-self.yml` `security-audit-summary` `needs:` line (already
  364 chars, over the repo's yamllint 180-char limit before this session — a pre-existing
  `validate-yaml` job failure), converted the flow sequence to a YAML block sequence. yamllint now
  exits 0 (only the two pre-existing `document-start` + `truthy` warnings remain).
- **Known remaining limitation (not in scope of this gap)**: `dispatch-workflows` is a matrix job, so
  `steps.dispatch.outputs.run-ids` still collapses to the last matrix instance's value (a standard
  GitHub Actions matrix-output constraint, independent of the `::set-output` bug). Aggregating run-ids
  across all matrix legs would need a separate fan-in job. See gaps_blocked / DEBT below.
- **Effort**: S — **Priority**: P1 — **Status**: **FIXED** (audit gap closed; matrix fan-in tracked separately)

### DEBT-W15: cross-repo-trigger matrix run-id aggregation (OPEN, follow-up to W14)
- **What (OPEN)**: `dispatch-workflows.outputs.run-ids` maps to `steps.dispatch.outputs.run-ids`, but
  because the job uses `strategy.matrix.repo`, GitHub only preserves the LAST matrix leg's output. To
  correlate run-ids for every dispatched repo, add a fan-in job that collects per-leg outputs (e.g. via
  per-repo artifacts or a JSON-array output keyed by repo). The `::set-output`→`$GITHUB_OUTPUT` fix
  (W14) was a prerequisite; this aggregation is the remaining functional improvement.
- **Effort**: M — **Priority**: P3 — **Status**: OPEN
