---
name: ADR-001 alebrije-workflows COMPLETE (2026-05-07)
description: All 18 blocks A-R implemented. 28 workflows + 9 custom actions. Commits f835f51 + 349a7ed on main.
type: project
---

ADR-001 alebrije-workflows fully implemented.

**Why:** User requested 100% implementation of all pending CI/CD blocks with no phase-2 deferral.

**How to apply:** ADR-001 status is now Implemented. All consumers can reference the new reusable workflows via `uses: alebrije-io/alebrije-workflows/.github/workflows/<name>.yml@main`.

## Deliverables

### Workflows (28 total, 15 new)
- reusable-test-go.yml + reusable-test-go-matrix.yml (Block A)
- reusable-test-elixir.yml + reusable-test-elixir-matrix.yml (Block A)
- reusable-test-ts.yml (Block A)
- reusable-mutation-test.yml (Block C)
- reusable-property-tests.yml (Block D)
- reusable-benchmark.yml (Block F)
- reusable-approved-images-check.yml (Block G)
- reusable-openapi-check.yml (Block H)
- reusable-release-extended.yml (Block J)
- reusable-canary-deploy.yml (Block K)
- cross-repo-trigger.yml (Block L)
- reusable-notify.yml (Block M)
- ci-cost-aggregator.yml (Block N)

### Custom Actions (9 total, 9 new)
- bump-version (Block J)
- post-benchmark-comment (Block F)
- wait-for-metrics (Block K)
- trigger-canary (Block K)
- setup-vault-token (Block P)
- check-tenant-id-leak (Block P)
- post-coverage-comment (Block P)
- sign-with-cosign (Block P)
- generate-postmortem (Block P)

### Hardening (Block R)
- validate-self.yml: 7-job security audit (SHA pins, permissions, anti-patterns, YAML)
- 187 SHA-pinned action references
- All 28 workflows have explicit permissions: blocks

### Community files
- .github/PULL_REQUEST_TEMPLATE.md
- .github/ISSUE_TEMPLATE/ (4 templates)
- .github/CONTRIBUTING.md
- .github/dependabot.template.yml

### Commits
- f835f51: feat(workflows): ADR-001 complete
- 349a7ed: fix(ci): yamllint YAML syntax fixes
