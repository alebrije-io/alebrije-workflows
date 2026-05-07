# Contributing to alebrije-workflows

## Overview

This repository centralizes **reusable GitHub Actions workflows** for the entire Alebrije platform fleet. Every change here cascades to all 16+ microservices and infrastructure repos. Contributions require rigorous testing and documentation.

**Key principle:** Changes here are NOT safe to iterate on production repos — they must be verified exhaustively locally first.

---

## Local Development Setup

### Prerequisites

- **Docker Desktop with Kubernetes enabled** (not docker-compose)
  - Rationale: alebrije-workflows is tested against real K8s topologies
  - Run: `make dev-deploy` from `alebrije-infra` to spin up local cluster
  - Dashboard: `http://localhost:9000/dashboard/`

- **GitHub CLI** (`gh`): v2.30+
  - Test: `gh auth status`

- **yamllint**: v1.26+
  - Install: `pip install yamllint` or `brew install yamllint`
  - Test: `yamllint --version`

### Branch Naming

- `feat/` — new features (workflows, actions, capabilities)
- `bugfix/` — bug fixes
- `docs/` — documentation only (no code changes)
- `chore/` — dependencies, maintenance, no behavior change

Example: `feat/ci-cost-aggregator-v2` or `bugfix/vault-rotation-deadlock`

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(test-go): add streaming progress reporter for long-running tests
fix(security-scan): correct grype SARIF upload path
docs(setup): update local K8s prerequisite
chore(deps): bump aquasecurity/trivy-action to v0.36.0
```

**CRITICAL:** Every commit must be **100% user-attributed** — NO `Co-Authored-By`, NO AI references. All commits appear under your local git identity only.

---

## Writing Workflows

### Naming Convention

- **Reusable workflows:** `reusable-<verb>-<noun>.yml`
  - Example: `reusable-test-python.yml`, `reusable-security-scan.yml`
  
- **Trigger workflows:** `<event>-<noun>.yml`
  - Example: `ci-cost-aggregator.yml`, `cross-repo-trigger.yml`

### Mandatory Structure

Every workflow **MUST include:**

```yaml
name: Workflow Name

on:
  # Trigger configuration
  workflow_dispatch:    # Always allow manual trigger

permissions:           # Explicit, minimal permissions
  contents: read
  actions: read
  # Add sparingly for specific needs

jobs:
  job-name:
    runs-on: ubuntu-latest  # or appropriate runner
    concurrency:
      group: ${{ github.workflow }}-${{ github.ref }}
      cancel-in-progress: true

    steps:
      # Implementation
```

### Quality Gates — NON-NEGOTIABLE

**Coverage gate: ≥90% is IMMOVABLE** (Alebrije Rule G).

- [ ] No `|| true` in any test/quality step
- [ ] No `continue-on-error: true` for quality checks
- [ ] No `--no-verify` flags
- [ ] No skipping linters, tests, or security scans
- [ ] If a check fails, **fix the root cause**, do not degrade the gate

**Example — FORBIDDEN:**
```yaml
- run: pytest --cov=my_service || echo "Tests failed but continuing"  # ❌ WRONG
```

**Example — CORRECT:**
```yaml
- run: pytest --cov=my_service --cov-fail-under=90
- name: Report coverage
  run: python -m coverage report
```

### Prepush Ritual (OBLIGATORY)

Before pushing ANY changes to this repo:

```bash
# 1. Validate all YAML
yamllint -d relaxed .github/workflows/ .github/*.yml

# 2. Test against schema (if available)
# From alebrije-infra or your workflow runner:
bash scripts/validate-workflows.sh

# 3. If modifying reusable workflows, test in a consumer repo:
cd ../alebrije-svc-auth
git checkout -b test/workflows-integration
# Add test caller that invokes your new reusable workflow
# Run manually via GitHub UI
# Verify no breaking changes

# 4. Only after all pass locally — commit and push
git add .github/workflows/
git commit -m "feat(test-go): add coverage reports"
git push
```

---

## Testing Workflows

### Unit Testing (YAML Validation)

```bash
yamllint -d "{extends: default, rules: {line-length: {max: 180}}}" .github/workflows/my-workflow.yml
```

### Integration Testing

Create a test-caller workflow in a branch that invokes your new reusable workflow:

```yaml
# .github/workflows/test-my-reusable.yml
name: Test my-reusable-workflow

on:
  workflow_dispatch:

jobs:
  test:
    uses: ./.github/workflows/reusable-my-new-feature.yml
    with:
      input-param: value
```

Trigger manually from GitHub UI, verify results.

### Consumer Testing

Before merging, test in a real consumer repo:

```bash
cd ../alebrije-svc-auth
git checkout -b test/your-workflows-change

# In .github/workflows/ci.yml, update to point to your branch:
# uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-test-go.yml@your-branch

git push
# Trigger CI manually
# Verify no regressions
```

---

## Documentation Requirements

Every workflow **MUST include:**

1. **Header comment** with design decisions
   ```yaml
   # Weekly cost aggregation from GitHub Actions API.
   #
   # Design decisions:
   # 1. Runs on ubuntu-latest (no Vault needed)
   # 2. Uses public GitHub API with GH_TOKEN (not PAT)
   # 3. Produces both JSON and markdown reports
   # 4. Artifacts retained 90 days for trend analysis
   ```

2. **Inline comments** for non-obvious logic
   ```yaml
   # Calculate cost: (ubuntu_minutes * 0.0035) + (macos_minutes * 0.014)
   - name: Calculate costs
     run: python3 scripts/cost_math.py
   ```

3. **README or docs/** entry linking to the workflow
   ```
   - `reusable-test-python.yml` — Run pytest with coverage reporting. 
     Inputs: `python-version`, `cov-threshold`. 
     See [docs/workflows/test-python.md](docs/workflows/test-python.md).
   ```

---

## Fleet Impact Analysis

Changes to reusable workflows affect **all 16+ repos** that consume them. Before merging:

### 1. Identify consumers
```bash
grep -r "alebrije-workflows.*reusable-" ../*/\.github/workflows/ | cut -d: -f1 | sort -u
```

### 2. Test backward compatibility
- Existing callers with old `with:` inputs must still work
- New inputs must have sensible defaults
- If removing an input: deprecate in 2 releases, then remove

### 3. Document breaking changes
If a breaking change is unavoidable:
- Create a migration guide in `docs/`
- Bump workflow version tag: `reusable-test-go@v2` (if previously `v1`)
- Announce in `#platform` and `#releases`
- Stagger rollout: update one high-value repo first, monitor, then fleet-wide

### 4. Verify all consumers
```bash
# Example: you modified reusable-test-python.yml
for repo in alebrije-svc-auth alebrije-campaigns-ex alebrije-mod-agentic; do
  echo "Testing $repo..."
  cd ../$repo
  git pull origin main
  gh workflow run ci.yml  # Or specific workflow that uses your reusable
  # Monitor run, verify green
done
```

---

## Conventional Commits Format

### Examples

```
feat(ci-cost): add trend analysis and monthly projections
fix(vault-rotation): resolve K8s secret stale-write race
docs(setup): clarify docker-desktop vs docker-compose requirement
chore(deps): bump actions/checkout to v4.1.0
```

### Scope

Scope refers to the **component or subsystem** modified:

- `ci-cost` — cost aggregation workflows
- `vault-rotation` — secret rotation in K8s
- `test-go` — Go testing workflows
- `security-scan` — vulnerability scanning
- `setup` — documentation and onboarding
- `deps` — dependency updates

---

## Architecture Decisions

All significant design decisions are documented in **[docs/adr/](docs/adr/)**.

Before implementing a new workflow:
1. Check if an ADR exists (e.g., ADR-001 for pending functionality)
2. If modifying patterns, propose an ADR update
3. Link the ADR in your PR description

Example ADRs:
- **ADR-001** — Pending functionality (tool catalog, streaming, resources, etc.)
- **ADR-67** — Production-Like Testing Pillar (zero mocks of infra)
- **ADR-74** — Platform health dashboard (cost reporting, SLOs)

---

## Code Review & Approval

Workflows require **≥1 approval** before merge (GitHub branch protection).

### Reviewer checklist

- [ ] YAML is valid (`yamllint` clean)
- [ ] No hardcoded secrets or credentials
- [ ] Quality gates are not degraded (`|| true`, `--no-verify`, etc.)
- [ ] Coverage floor (90%) is maintained
- [ ] Documentation updated
- [ ] Consumer impact analyzed
- [ ] Tests pass locally and in CI

---

## Release & Rollout

Workflows don't have a formal "release" process like app repos, but follow these practices:

1. **Tag major versions** for reusable workflows when interface changes
   ```bash
   git tag reusable-test-go@v2.0.0
   git push origin reusable-test-go@v2.0.0
   ```

2. **Update consumers gradually**
   - Don't fleet-wide update in one commit
   - Start with 2-3 high-value repos
   - Monitor for 1-2 weeks
   - Then fleet-wide

3. **Deprecation** (if removing a workflow)
   - Keep stub with deprecation notice for 2 releases
   - Example: `reusable-old-flow.yml` → redirect to `reusable-new-flow.yml`
   - Announce in docs and #platform Slack

---

## FAQ & Troubleshooting

**Q: How do I test a reusable workflow locally?**
A: You can't run it directly, but you can:
1. Create a caller workflow in a branch
2. Push the branch
3. Trigger the caller manually from GitHub UI
4. Monitor the run logs

**Q: What if my workflow needs secrets?**
A: Use Vault (ADR-53). Workflows access Vault via:
- K8s ServiceAccount (if pod-level)
- `arc-runner-set` (if GitHub runner with K8s integrations)
- Never hardcode tokens in workflow YAML

**Q: Can I modify an existing reusable workflow's inputs?**
A: Carefully. New inputs must have defaults to avoid breaking existing callers.
Adding optional inputs: ✅ safe
Removing inputs: ❌ breaks callers, requires migration
Changing input behavior: ❌ risky, test all consumers first

**Q: How do I report a bug in a workflow?**
A: File an issue using the [Bug Report](./ISSUE_TEMPLATE/bug_report.yml) template.
Include:
- Affected workflow name
- Consumer repo calling it
- Relevant logs (not secrets!)
- Severity level

---

## Related Documents

- [ADR-001 Pending Functionality](docs/adr/ADR-001-pending-functionality.md)
- [Architecture Decision Records](docs/adr/)
- [Global Alebrije CLAUDE.md](../personal/alebrije/CLAUDE.md) — includes Rule G (90% coverage immovable), prepush ritual, git commits

---

## Questions?

- Check [docs/adr/](docs/adr/) for architectural patterns
- Review existing workflows in `.github/workflows/` for examples
- File an issue with the [Feature Request](./ISSUE_TEMPLATE/feature_request.yml) template
- Reach out in `#platform` (Slack)
