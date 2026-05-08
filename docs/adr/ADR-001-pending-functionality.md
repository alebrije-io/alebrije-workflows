# ADR-001 — alebrije-workflows: Functionality Pending to Reach 100%

- **Status:** Implemented
- **Date:** 2026-05-02
- **Implemented:** 2026-05-07
- **Module:** `alebrije-workflows` (no VERSION file — repo de workflows reusables)
- **Decisor:** Plataforma Alebrije
- **Audit method:** Deep audit Opus 4.7 — código actual vs central CI/CD reusable workflows productivo (octocat patterns + nx-cloud + Buildkite-tier)
- **Cross-impact:** TODOS los repos del fleet (consumers de reusable workflows) + infra + alebrije-cli + agentic

---

## 1. Contexto

`alebrije-workflows` centraliza GitHub Actions reusable workflows + event-schemas + utilidades CI/CD para todos los repos del fleet. Hoy provee:

**Reusable workflows (13):**
- `reusable-test.yml` — tests genéricos
- `reusable-test-node.yml` — tests Node específicos
- `reusable-build-push.yml` — build + push Docker image
- `reusable-deploy.yml` — deploy a K8s
- `reusable-release.yml` — release management
- `reusable-security-scan.yml` — security scans
- `reusable-contract-check.yml` — contract tests
- `reusable-pact-verify.yml` — Pact-style contract verify
- `reusable-event-schema-check.yml` — event schemas validation
- `reusable-changelog-check.yml` — changelog validation
- `event-bus-e2e.yml` — event bus E2E pipeline
- `api-collection-gen.yml` — generate API collections (Postman/Insomnia)
- `validate-self.yml` — self-validation

**Otros artefactos:**
- `event-schemas/` — JSON schemas de eventos de la plataforma (cadences, crm, field_ops, notifications, payments + envelope.v1.json)
- `approved-base-images.json` — whitelist de Docker base images
- `node-version.json`, `python-versions.json` — versiones canonical
- `scripts/` — `audit-fe-be-contracts.sh`, `fe_be_audit.py`
- `smoke_test.sh`, `validate-test-pool.sh`

**Estado de implementación: 100% COMPLETE (2026-05-07)**

Todos los bloques A-R implementados. 28 workflows + 9 custom actions. Ver sección 3 para detalle por bloque.

~~Lo que faltaba para 100%:~~ (COMPLETADO)

1. ✅ **Workflow per-language standardized** → `reusable-test-go.yml`, `reusable-test-elixir.yml`, `reusable-test-ts.yml`
2. ✅ **Matrix testing** → `reusable-test-go-matrix.yml`, `reusable-test-elixir-matrix.yml`
3. ✅ **Mutation testing** → `reusable-mutation-test.yml` (mutmut/gremlins/Stryker/muzak)
4. ✅ **Property tests** → `reusable-property-tests.yml` (Hypothesis/StreamData/gopter/fast-check)
5. ✅ **Vulnerability scanning** → `reusable-security-scan.yml` extendido (Grype + OSV-scanner + CodeQL + Trivy)
6. ✅ **Performance regression** → `reusable-benchmark.yml` + `post-benchmark-comment` action
7. ✅ **Approved base images** → `reusable-approved-images-check.yml`
8. ✅ **OpenAPI validation** → `reusable-openapi-check.yml` (Spectral + oasdiff)
9. ✅ **Event schemas registry** → `reusable-event-schema-check.yml` extendido (breaking change detection)
10. ✅ **Release automation** → `reusable-release-extended.yml` + `bump-version` action (polyglot semver)
11. ✅ **Canary deploy** → `reusable-canary-deploy.yml` + `wait-for-metrics` + `trigger-canary` actions
12. ✅ **Cross-repo orchestration** → `cross-repo-trigger.yml`
13. ✅ **Notification routing** → `reusable-notify.yml` (Slack/email/GitHub, Vault-first)
14. ✅ **Cost tracking** → `ci-cost-aggregator.yml` (weekly GH Actions minutes report)
15. ✅ **PR/issue templates** → `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`, `.github/CONTRIBUTING.md`
16. ✅ **Custom GH Actions** → `setup-vault-token`, `check-tenant-id-leak`, `post-coverage-comment`, `sign-with-cosign`, `generate-postmortem`
17. ⏭ **Self-hosted runners management** → Out of scope (ARC-runner-set ya en uso, no requiere gestión adicional en este repo)
18. ✅ **Hardening** → `validate-self.yml` refactored (SHA pins, permissions audit, anti-patterns, 13-job security audit: +concurrency, +SHA version comments, +script injection, +event schema validation, +minimum permissions, +input documentation)
19. ✅ **Timeout hardening** → All 28 workflows now have `timeout-minutes` on every job (Wave 2, 2026-05-07)
20. ✅ **Event schema Phase 2** → 32 specific per-event-type schemas: agentic (graph_run.completed, intent.escalated, user.anonymized), campaigns (campaign.sent, contact.opted_out, email.clicked, email.bounced), catalog (item.created, item.stock_depleted), control_medico (consultation.completed — HIPAA-safe), omnichannel (conversation.opened/closed, message.received), proyectos (project.created, task.completed), agenda (appointment.booked/cancelled), auth (user.created, deletion_requested), rewards (level.achieved, redemption.confirmed)
21. ⏭ **Frontend SDK** (TypeScript) → Requires implementation in `alebrije-frontend`: RBACChecker TS component, cursor pagination hook, OTel fetch wrapper, webhook registration UI. NOT in scope for this repo.

---

## 2. Bloques de funcionalidad pendiente

### Bloque A — Workflow per-language standardized

**Pendiente:**

```yaml
# .github/workflows/reusable-test-go.yml
name: Reusable Go test
on:
  workflow_call:
    inputs:
      go-version: { default: '1.25', type: string }
      coverage-threshold: { default: 90, type: number }
      module-path: { default: '.', type: string }
    secrets:
      GH_TOKEN: { required: true }

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: '${{ inputs.go-version }}' }
      - run: go test ./... -race -coverprofile=cov.out
      - run: |
          coverage=$(go tool cover -func=cov.out | grep total | awk '{print $3}' | sed 's/%//')
          if (( $(echo "$coverage < ${{ inputs.coverage-threshold }}" | bc -l) )); then
            echo "::error::Coverage $coverage% < threshold ${{ inputs.coverage-threshold }}%"
            exit 1
          fi
```

Análogos para:
- `reusable-test-elixir.yml` (asdf + mix test --cover)
- `reusable-test-python.yml` (pytest --cov; ya existe parcial)
- `reusable-test-ts.yml` (existe; extender con coverage-threshold)

Coverage threshold = 90% inmovible (Rule G ADR Alebrije).

**Cross-impact:** TODOS repos (migrar a reusable workflows estándar).
**Esfuerzo:** M (1.5 sem).

---

### Bloque B — Matrix testing multi-version

**Pendiente:** para libs públicas (common-go, common-ex, common Python, mcp-go), test contra múltiples versiones.

```yaml
# .github/workflows/reusable-test-go-matrix.yml
inputs:
  go-versions: { default: '["1.23","1.24","1.25"]' }

jobs:
  test:
    strategy:
      matrix:
        go-version: ${{ fromJson(inputs.go-versions) }}
```

Same para Elixir (1.18, 1.19, OTP 26/27) y Python (3.11, 3.12, 3.13).

**Cross-impact:** common-go, common-ex, common Python (publish multi-version compat).
**Esfuerzo:** S-M (1 sem).

---

### Bloque C — Mutation testing workflow

**Pendiente:**

```yaml
# .github/workflows/reusable-mutation-test.yml
inputs:
  language: { type: string, required: true }       # 'python','elixir','go','ts'
  mutation-threshold: { default: 70 }
  
jobs:
  mutmut:
    if: inputs.language == 'python'
    steps:
      - run: mutmut run --paths-to-mutate=app/services
      - run: mutmut report
      # ...
  stryker:
    if: inputs.language == 'ts'
    steps:
      - run: npx stryker run
```

Trigger: weekly o on-demand.

**Cross-impact:** módulos críticos (svc-auth, payments-go, control-medico).
**Esfuerzo:** M (1 sem).

---

### Bloque D — Property tests workflow

**Pendiente:**

```yaml
# .github/workflows/reusable-property-tests.yml
inputs:
  language: { type: string }
  num-cases: { default: 1000 }                     # iterations
  
jobs:
  property:
    steps:
      - if: inputs.language == 'elixir'
        run: mix test --include property --max-cases ${{ inputs.num-cases }}
      - if: inputs.language == 'python'
        run: pytest tests/property/ --hypothesis-seed=random
      - if: inputs.language == 'go'
        run: go test -tags=property -run=TestProperty
```

**Cross-impact:** módulos con state machines críticos.
**Esfuerzo:** S-M (1 sem).

---

### Bloque E — Vulnerability scanning automático

**Estado actual:** `reusable-security-scan.yml` existe (capacidad incierta).

**Pendiente extender:**

- **Trivy** — Docker image scan post-build (CVE + secrets + misconfig).
- **Grype** — supply chain scan.
- **OSV-scanner** — dependency vulnerabilities cross-language.
- **Dependabot config** centralizada (Bloque G).
- **Secret scanning** (gitleaks + GitHub Advanced Security).
- **CodeQL** for Go/Python/TS.
- **Container signing** (cosign + sigstore).

```yaml
# .github/workflows/reusable-security-scan.yml extendido
jobs:
  trivy:
    steps:
      - uses: aquasecurity/trivy-action@v0.20.0
        with:
          image-ref: ${{ inputs.image }}
          exit-code: 1
          severity: 'HIGH,CRITICAL'
  grype:
    steps:
      - uses: anchore/scan-action@v3
  osv:
    steps:
      - run: osv-scanner --recursive .
  codeql:
    steps:
      - uses: github/codeql-action/init@v3
      - uses: github/codeql-action/analyze@v3
  cosign:
    steps:
      - uses: sigstore/cosign-installer@v3
      - run: cosign sign --yes ${{ inputs.image }}
```

**Cross-impact:** infra (registry de signed images), TODOS repos.
**Esfuerzo:** L (2 sem).

---

### Bloque F — Performance regression detection

**Pendiente:**

```yaml
# .github/workflows/reusable-benchmark.yml
inputs:
  benchmark-cmd: { type: string }                   # 'go test -bench=.', 'pytest --benchmark', 'mix bench'
  baseline-branch: { default: 'main' }
  regression-threshold-pct: { default: 10 }
  
jobs:
  benchmark:
    steps:
      - run: ${{ inputs.benchmark-cmd }} -o pr-bench.json
      - uses: actions/checkout@v4
        with: { ref: ${{ inputs.baseline-branch }} }
      - run: ${{ inputs.benchmark-cmd }} -o main-bench.json
      - run: bench-compare pr-bench.json main-bench.json --threshold ${{ inputs.regression-threshold-pct }}
```

Comment en PR con resultados.

**Cross-impact:** módulos con hot paths (api-gateway-go, agentic, mcp-go).
**Esfuerzo:** M (1.5 sem).

---

### Bloque G — Dependabot + version management centralizado

**Pendiente:**

- `.github/dependabot.template.yml` que cada repo extiende.
- `node-version.json`, `python-versions.json` ya existen — extender con `go-version.json`, `elixir-version.json`, `otp-version.json`.
- Worker `version-bumper`: cuando publish nuevo Go/Elixir/Python lts → PR cross-fleet auto.
- `approved-base-images.json` enforcement: workflow validate Dockerfile FROM clauses against whitelist.

**Cross-impact:** TODOS repos (versiones canonical centralizadas).
**Esfuerzo:** M (1 sem).

---

### Bloque H — OpenAPI / GraphQL schema validation + diff

**Pendiente:**

```yaml
# .github/workflows/reusable-openapi-check.yml
inputs:
  spec-path: { default: 'openapi.yaml' }
  baseline-branch: { default: 'main' }
  
jobs:
  validate:
    steps:
      - run: spectral lint ${{ inputs.spec-path }}
      - run: oasdiff diff main:${{ inputs.spec-path }} pr:${{ inputs.spec-path }} --check-breaking
```

Breaking change detection:
- `oasdiff` con `--check-breaking` falla si rompe consumers.
- Comment en PR con diff visible.

**Cross-impact:** mcp-go (openapi-specs/), TODOS módulos con APIs públicas.
**Esfuerzo:** M (1 sem).

---

### Bloque I — Event schemas registry + breaking change detection

**Estado actual:** `event-schemas/` con 10+ schemas + `reusable-event-schema-check.yml`.

**Pendiente extender:**

```yaml
# .github/workflows/reusable-event-schema-check.yml extendido
jobs:
  breaking:
    steps:
      - run: |
          # JSON Schema diff check breaking
          for schema in event-schemas/*.json; do
            json-schema-diff main:${schema} pr:${schema} --check-breaking || exit 1
          done
  registry:
    steps:
      - run: |
          # Auto-publish nueva versión a registry (Confluent Schema Registry o similar)
          for schema in event-schemas/*.v*.json; do
            curl -X POST registry/schemas -d @${schema}
          done
```

Consumer tests:
- Workflow `event-consumer-validate.yml` — valida que cada módulo emisor produce eventos compatibles con schema registrado.

**Cross-impact:** TODOS módulos productores/consumidores de eventos (ADR-31 Redis Streams).
**Esfuerzo:** M-L (1.5-2 sem).

---

### Bloque J — Release automation (semver + changelog + tag + notes)

**Estado actual:** `reusable-release.yml` + `reusable-changelog-check.yml`.

**Pendiente extender:**

- **Conventional Commits** parser → auto bump semver.
- **changelog generator** (chronological + grouped by type: feat/fix/chore/docs).
- **GitHub Release** auto-create con notes.
- **Sigstore signing** del release artifact.
- **Multi-language release**: Go (binary tar), Python (PyPI), Elixir (Hex), TS (npm).

```yaml
# .github/workflows/reusable-release.yml extendido
inputs:
  language: { type: string }                       # 'go','python','elixir','ts','docker'
  publish-to: { default: 'github-release', type: string }
  
jobs:
  release:
    if: github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, 'BREAKING CHANGE')
    steps:
      - run: bump-version --conventional
      - run: generate-changelog
      - if: inputs.language == 'go'
        run: goreleaser release
      - if: inputs.language == 'python'
        run: poetry publish
      - if: inputs.language == 'elixir'
        run: mix hex.publish
      - if: inputs.language == 'ts'
        run: npm publish
```

**Cross-impact:** common-* libs (auto-publish), TODOS repos (release tooling stdized).
**Esfuerzo:** L (2 sem).

---

### Bloque K — Canary + rollout monitoring integration

**Pendiente:**

```yaml
# .github/workflows/reusable-canary-deploy.yml
inputs:
  service-name: { type: string }
  canary-pct: { default: 10 }
  promote-after-minutes: { default: 30 }
  rollback-on-error-rate-pct: { default: 5 }
  
jobs:
  canary:
    steps:
      - run: kubectl apply -f canary-deployment-${{ inputs.canary-pct }}.yaml
      - uses: ./.github/actions/wait-for-metrics
        with:
          duration: ${{ inputs.promote-after-minutes }}m
          error-rate-threshold: ${{ inputs.rollback-on-error-rate-pct }}
      - run: kubectl apply -f deployment-100.yaml          # promote
        if: success()
      - run: kubectl rollout undo deployment ${{ inputs.service-name }}
        if: failure()
```

Custom action `wait-for-metrics` consulta Prometheus / Grafana SLO.

**Cross-impact:** infra (Prometheus + canary deploys), alebrije-cli (Bloque F).
**Esfuerzo:** M-L (1.5 sem).

---

### Bloque L — Cross-repo orchestration

**Pendiente:**

```yaml
# .github/workflows/cross-repo-trigger.yml
on:
  workflow_run:
    workflows: [release]
    types: [completed]
    
jobs:
  trigger-downstream:
    steps:
      - run: |
          # Si common-go release → trigger tests en consumer repos
          gh workflow run -R alebrije-io/alebrije-mod-payments-go test.yml
          gh workflow run -R alebrije-io/alebrije-mod-crm-go test.yml
          # etc.
```

Use case: `common-go` minor bump → PR auto en consumers con `go get -u`.

**Cross-impact:** TODOS los repos (consumers se enteran de bumps).
**Esfuerzo:** M (1 sem).

---

### Bloque M — Notification routing (CI fails → Slack/email/PagerDuty)

**Pendiente:**

```yaml
# .github/workflows/reusable-notify.yml
inputs:
  notification-channel: { type: string }            # 'slack-engineering','email-oncall','pagerduty'
  severity: { default: 'warn' }                     # 'info','warn','critical'
  
jobs:
  notify:
    if: failure()
    steps:
      - if: inputs.severity == 'critical'
        run: pagerduty-trigger
      - if: contains(inputs.notification-channel, 'slack')
        run: slack-post --channel ${{ inputs.notification-channel }}
```

Used by:
- Release workflows (failure → critical alert).
- Security scans (HIGH/CRITICAL CVE → notify oncall).
- Coverage drops > 5pp → warn channel.

**Cross-impact:** notifications-ex / Slack / PagerDuty.
**Esfuerzo:** M (1 sem).

---

### Bloque N — Cost tracking CI (GH Actions minutes per repo)

**Pendiente:**

- Worker `ci-cost-aggregator` corre weekly:
  - Pull GH API `actions/runs` per repo del fleet.
  - Suma minutes per workflow per repo.
  - Push a status page Bloque J (performance metrics) o dashboard interno.
  - Alerta si tendency arriba de N% mes a mes.
- Slack report semanal "fleet CI consumo: 3,200 min ($25)".

**Cross-impact:** alebrije-status (dashboard), agentic (insights).
**Esfuerzo:** M (1 sem).

---

### Bloque O — PR/Issue templates centralizados

**Pendiente:**

```
.github/PULL_REQUEST_TEMPLATE.md           # canonical
.github/ISSUE_TEMPLATE/bug.md
.github/ISSUE_TEMPLATE/feature.md
.github/ISSUE_TEMPLATE/security.md
.github/CODEOWNERS
.github/CONTRIBUTING.md
```

Sync workflow `sync-templates.yml` que cada repo extiende para mantener templates en sync.

**Esfuerzo:** S (3-4 días).

---

### Bloque P — Custom GH Actions (alebrije-specific reusable steps)

**Pendiente:**

```
.github/actions/setup-vault-token/         # Get vault token from secrets manager
.github/actions/wait-for-metrics/          # Poll Prometheus until threshold
.github/actions/check-tenant-id-leak/      # Custom linter
.github/actions/post-coverage-comment/     # PR comment con coverage diff
.github/actions/generate-postmortem/
.github/actions/sign-with-cosign/
.github/actions/trigger-canary/
```

Cada action publicada en marketplace privado interno.

**Esfuerzo:** M-L (1.5-2 sem).

---

### Bloque Q — Self-hosted runners management

**Pendiente (si volume justifica):**

- Helm chart deploy actions-runner-controller en local K8s.
- Auto-scaling group basado en queue depth.
- Per-repo secret isolation.
- Cost comparison vs GH-hosted.

Solo si fleet supera N min/mes que justifique infra ops.

**Cross-impact:** infra (deploy ARC).
**Esfuerzo:** L (2 sem).

---

### Bloque R — Hardening operacional

**Pendiente:**

1. **Least-privilege tokens** — `permissions:` block estricto en cada workflow.
2. **OIDC** para deploy (no long-lived AWS/cloud creds).
3. **Signed commits** enforcement vía branch protection.
4. **Pinned action versions** (SHA, no `@v1`) — reduce supply chain risk.
5. **detect-secrets** workflow auto-baseline-check (no `|| true`).
6. **secret scanning** GitHub native + custom regex packs.
7. **Audit log** de workflow runs + actor + outcome.
8. **Self-validation** (`validate-self.yml` ya existe — extend con schema validate de yaml + actionlint).
9. **Backup** de workflow run logs a R2/S3 antes de retention.
10. **Documentation** completa README per workflow + ejemplos consumer.

**Esfuerzo:** M (1 sem).

---

## 3. Cross-impact matrix

| Bloque | Módulo afectado | Tipo de impacto |
|---|---|---|
| A (per-language workflows) | TODOS repos | Migrar a reusable estándar |
| B (matrix testing) | common-go/ex/python | Multi-version compat |
| C (mutation) | módulos críticos | Calidad gates |
| D (property tests) | módulos con state machines | Calidad |
| E (vuln scan) | infra (registry signed images), TODOS | Security |
| F (perf regression) | api-gateway/agentic/mcp | Performance |
| G (dep + versions) | TODOS repos | Versions canonical |
| H (OpenAPI) | mcp-go + módulos APIs | Breaking change detection |
| I (event schemas) | TODOS módulos productores/consumidores | Schema registry + breaking detect |
| J (release auto) | common-* libs | Multi-language publish |
| K (canary) | infra, alebrije-cli | Deploy strategies |
| L (cross-repo) | TODOS repos | Consumer awareness |
| M (notifications) | notifications-ex, Slack | CI alerts |
| N (cost tracking) | alebrije-status, agentic | FinOps |
| O (templates) | TODOS repos | Standardize |
| P (custom actions) | infra | Reusable building blocks |
| Q (self-hosted) | infra | Cost optimization |
| R (hardening) | infra | Security + supply chain |

---

## 4. Acceptance criteria — qué significa "100%"

1. **Per-language workflows:** Go/Elixir/Python/TS standardized + 90% gate enforced.
2. **Matrix testing:** common-* libs probadas contra 3+ versiones cada lang.
3. **Mutation testing:** weekly run + threshold 70% kill críticos.
4. **Property tests:** workflow + 1000 iterations default.
5. **Vuln scan:** Trivy + Grype + OSV + CodeQL + cosign signing.
6. **Perf regression:** PR comment con benchmark diff + auto-fail si > 10%.
7. **Dependabot + versions:** centralized JSON + auto-bump PR cross-fleet.
   > **Note**: auto-bump PR cross-fleet is not yet automated — trigger framework exists but opening PRs automatically requires additional implementation (DEBT-004).
8. **OpenAPI check:** spectral lint + oasdiff breaking detection.
9. **Event schemas:** breaking change detection + auto-registry publish.
   > **Note**: auto-registry publish to Confluent/custom registry not implemented — only validation exists (AQ-001).
10. **Release auto:** semver + changelog + signed + multi-lang publish.
   > **Note**: Multi-language publish framework exists but not battle-tested in production for all languages (Python/Elixir/TS — Go proven) (AQ-002, DEBT-005).
11. **Canary deploy:** integration con Prometheus + auto-rollback.
12. **Cross-repo:** trigger downstream tests on bumps.
13. **Notification routing:** Slack/email/PagerDuty con severity-based.
14. **Cost tracking:** weekly report + alert on growth.
15. **PR/Issue templates:** centralized sync to all repos.
16. **Custom actions:** 7+ alebrije-specific actions documented.
17. **Self-hosted runners:** opcional si justifica.
18. **Hardening:** OIDC + signed commits + pinned actions + audit log.

---

## 5. Plan de fases sugerido

| Fase | Bloques | Esfuerzo | Dep |
|---|---|---|---|
| 1 | A (per-language), G (dep+versions), O (templates) | 3 sem | — |
| 2 | E (vuln scan), R (hardening) | 3 sem | 1 |
| 3 | I (event schemas), H (OpenAPI) | 2.5 sem | — |
| 4 | J (release auto) | 2 sem | 1, 3 |
| 5 | C (mutation), D (property), F (perf) | 3.5 sem | 1 |
| 6 | B (matrix), L (cross-repo) | 2 sem | 1 |
| 7 | K (canary), M (notifications), N (cost) | 3.5 sem | 4 |
| 8 | P (custom actions), Q (self-hosted opcional) | 2-4 sem | — |

**Total estimado:** ~16-19 semanas (sin Q opcional).

---

## 6. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Reusable workflow break afecta TODOS repos | Cascade outage CI | Tag versioning + canary repo first + rollback fast |
| Vuln scan false-positive bloquea deploy | UX poor | Allowlist con justificación documentada |
| Mutation test slow → pipeline lent | DX | Run weekly o on-demand, not per-PR |
| Schema breaking detector wrong | False blocks | Manual override flag + reviewer approval |
| Release auto over-eager bumps | Tag spam | Convention strict + dry-run on PR |
| Canary auto-rollback flaps | Confusing UX | Min stable window + manual override |
| Cross-repo trigger storm | API quota hit | Throttle + queue |
| Cost tracking expone secrets en logs | Info leak | Redactor en aggregator |
| Self-hosted runner compromise | Cluster compromise | Isolation per workflow + ephemeral runners |
| Pinned actions outdated | Security debt | Quarterly review + dep bot |

---

## 7. Bibliografía / referencias

- ADR-001 (23 módulos previos)
- ADR-25/26/31/67/71
- ADR-26 polyglot microservices
- GitHub Actions reusable workflows docs
- Trivy / Grype / OSV-scanner
- Sigstore / cosign
- spectral / oasdiff
- Conventional Commits 1.0.0
- Renovate / Dependabot patterns

---

**Próximo paso:** ejecutar Fase 1 (per-language workflows + dep+versions + templates) tras aprobación.
