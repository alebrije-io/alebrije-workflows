# alebrije-workflows

Centralized GitHub Actions reusable workflows and CI/CD utilities for all Alebrije microservices.

## Reusable Workflows

| Workflow | Purpose |
|---|---|
| reusable-test.yml | Python tests (pytest + coverage, matrix 3.12/3.13) |
| reusable-test-go.yml | Go tests with coverage reporting |
| reusable-test-elixir.yml | Elixir/Phoenix tests with coverage |
| reusable-test-ts.yml | TypeScript tests (vitest/jest) |
| reusable-test-go-matrix.yml | Go tests across multiple Go versions |
| reusable-test-elixir-matrix.yml | Elixir tests across multiple OTP/Elixir versions |
| reusable-test-node.yml | Node.js tests |
| reusable-build-push.yml | Docker build + push to Docker Hub + Cosign signing |
| reusable-deploy.yml | Deploy to Kubernetes (OVH) + smoke test |
| reusable-canary-deploy.yml | Progressive canary deployment with metrics validation |
| reusable-security-scan.yml | Trivy multi-type scan (fs/image/config) + SBOM + Cosign |
| reusable-pact-verify.yml | Contract testing (Pact) |
| reusable-changelog-check.yml | Enforce CHANGELOG on VERSION bumps |
| reusable-release.yml | GitHub Release automation on tag push |
| reusable-release-extended.yml | Extended release workflow with additional validation |
| reusable-contract-check.yml | FE/BE contract audit |
| reusable-event-schema-check.yml | AsyncAPI / event-schemas validation |
| reusable-approved-images-check.yml | Standalone Dockerfile base-image whitelist check (opt-in; the same gate runs inline inside reusable-build-push.yml) |
| reusable-mutation-test.yml | Mutation testing (Stryker/mutmut) |
| reusable-notify.yml | Notification/alert dispatcher |
| reusable-openapi-check.yml | OpenAPI specification validation |
| reusable-property-tests.yml | Property-based testing (StreamData/Hypothesis) |
| reusable-benchmark.yml | Performance benchmarking |
| api-collection-gen.yml | Generate API collection artifacts |
| ci-cost-aggregator.yml | Aggregate CI spend metrics |
| cross-repo-trigger.yml | Cross-repo workflow orchestration |
| event-bus-e2e.yml | End-to-end event bus testing |
| validate-self.yml | Self-validation of workflow syntax |

## Usage

In your service ci.yml:

    jobs:
      test:
        uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-test.yml@main
        secrets: inherit

      build-and-push:
        needs: test
        if: github.ref == 'refs/heads/main'
        uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-build-push.yml@main
        with:
          image-name: ileonelperea/alebrije-my-service
        secrets: inherit

      security:
        needs: build-and-push
        if: github.ref == 'refs/heads/main'
        uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-security-scan.yml@main
        with:
          image-ref: ileonelperea/alebrije-my-service:${{ needs.build-and-push.outputs.version }}
          scan-type: all
          fail-on: CRITICAL,HIGH
        secrets: inherit

      deploy:
        needs: [build-and-push, security]
        if: github.ref == 'refs/heads/main'
        uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-deploy.yml@main
        with:
          deployment-name: alebrije-my-service
          namespace: platform
          manifest-path: k8s/deployment.yaml
        secrets: inherit

Required permissions in calling workflow:

    permissions:
      contents: read
      id-token: write
      packages: write
      security-events: write

### Go service (DEBT-W09)

Inputs shown are the real `workflow_call.inputs` of `reusable-test-go.yml` — every
value below is a **non-default** override to make the shape visible; omit any
input to keep its default (`go-version: "1.23"`, `coverage-threshold: 90`,
`with-services: true`, `lint: true`, `race: true`).

    jobs:
      test:
        uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-test-go.yml@main
        with:
          go-version: "1.23"
          module-path: "."
          with-services: true    # spins up postgres:16 + redis:7 for integration tests
          test-tags: ""          # e.g. "integration" to include //go:build integration files
        secrets:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}

Need to test against several Go versions instead of one? Use
`reusable-test-go-matrix.yml` in place of `reusable-test-go.yml` — same
`with:` shape, fans out across the fleet-standard Go versions.

### Elixir/Phoenix service (DEBT-W09)

Inputs shown are the real `workflow_call.inputs` of `reusable-test-elixir.yml`
(defaults: `elixir-version: '1.18'`, `otp-version: '27'`,
`coverage-threshold: 90`, `with-credo: true`, `with-dialyzer: false` — Dialyzer
is opt-in because it is slow).

    jobs:
      test:
        uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-test-elixir.yml@main
        with:
          elixir-version: "1.18"
          otp-version: "27"
          with-credo: true
          with-dialyzer: false   # set true to also run mix dialyzer (slow)
        secrets:
          GH_TOKEN: ${{ secrets.GH_TOKEN }}

Need the OTP/Elixir version matrix instead of one pinned pair? Use
`reusable-test-elixir-matrix.yml` with the same `with:` shape.

### TypeScript / frontend service (DEBT-W09)

Inputs shown are the real `workflow_call.inputs` of `reusable-test-ts.yml`
(defaults: `node-version: '22'`, `coverage-threshold: 90`, `run-e2e: false` —
Playwright E2E is opt-in because it's expensive; `working-directory: '.'` for
monorepo layouts where the app isn't at the repo root).

    jobs:
      test:
        uses: alebrije-io/alebrije-workflows/.github/workflows/reusable-test-ts.yml@main
        with:
          node-version: "22"
          working-directory: "."
          run-e2e: false   # set true to also run Playwright E2E (slow)

Plain Node.js service with no coverage gate (no bundler/frontend build step)?
Use `reusable-test-node.yml` instead — it only takes `node-version` and
`run-e2e`, no `coverage-threshold`/`working-directory`.

## reusable-security-scan.yml

Multi-capa scan post-build. Corre como job independiente después de
`reusable-build-push.yml` y complementa (no reemplaza) la firma/scan
que build-push ya ejecuta en-line.

### Inputs

| Input | Default | Description |
|---|---|---|
| `image-ref` | `""` | Full image ref (e.g. `ileonelperea/alebrije-svc-auth:1.2.3`). Requerido para `image` y `all`. |
| `scan-type` | `all` | Uno de: `image`, `fs`, `config`, `all`. |
| `fail-on` | `CRITICAL,HIGH` | Severidades que fallan los jobs `fs` e `image`. |
| `config-scan-path` | `k8s/` | Path escaneado por trivy config. |
| `sbom-path` | `.` | Path que anchore/sbom-action usa. |
| `scan-secrets` | `true` | Corre detect-secrets audit. |
| `sign-image` | `true` | Firma con Cosign keyless (solo main push, requires `image-ref`). |

### Scan types

- `fs` — escanea dependencias declaradas en el repo (go.sum, requirements.txt, mix.lock). Blocking sobre `fail-on`.
- `image` — escanea la imagen Docker publicada. Blocking sobre `fail-on`. Requiere `image-ref`.
- `config` — escanea `config-scan-path` (default `k8s/`). Advisory-only (exit-code: 0), no bloquea en hallazgos de yaml/dockerfile linting.
- `all` — corre los tres, además de SBOM + detect-secrets + Cosign sign.

### False positives (.trivyignore)

Cada repo define `.trivyignore` en su root. Formato:

    # Python test-only dependency, not shipped in prod image
    CVE-2023-12345

    # Go stdlib CVE con fix only in 1.24+, runner-side mitigation applied
    CVE-2024-99999

Trivy lee este archivo automáticamente. Comentar SIEMPRE la razón para
que el triage sea auditable en la próxima review.

### SBOM artifact

Cada run genera `sbom-cyclonedx-<run_number>` con retención de 90 días.
Descargable desde la UI de Actions o vía `gh run download`.

### Cosign keyless signing

Ejecuta `cosign sign --yes <image-ref>` vía Sigstore OIDC (sin keys
almacenados en el repo). Registra en Rekor transparency log. Solo corre
en `push` a `main` con `sign-image: true` y un `image-ref` no vacío.

## Scripts

| Script | Purpose |
|---|---|
| validate-test-pool.sh | Detects orphaned tests (files not declared in CI pool) |
| smoke_test.sh | Post-deploy health check |
| audit-fe-be-contracts.sh | FE/BE contract audit driver |

## Custom Actions (AQ-003)

`.github/actions/*` — 9 composite actions, each `inputs:`/`outputs:` below taken directly from
the real `action.yml` (not retyped from memory):

| Action | Purpose | Key inputs | Key outputs |
|---|---|---|---|
| bump-version | Bumps `VERSION` from Conventional Commits since last tag | `version-file`, `dry-run` | `new-version`, `bump-type` |
| check-tenant-id-leak | Scans for hardcoded tenant IDs outside test/fixture files (ADR-63 blocking gate) | `scan-path`, `known-tenants-file`, `exclude-patterns`, `fail-on-leak` | `leaks-found`, `leak-report` |
| generate-postmortem | Generates a postmortem markdown template as a build artifact (non-blocking) | `incident-title`, `severity`, `service`, `incident-commander`, `related-services`, `deployment-context`, `escalation-path` | `postmortem-file` |
| post-benchmark-comment | Posts benchmark comparison results as a PR comment | `comparison`, `comparison-file`, `threshold` | (none) |
| post-coverage-comment | Posts a coverage-vs-baseline table as a PR comment (informational, non-blocking) | `coverage-file`, `coverage-format`, `baseline-coverage`, `gate-threshold` | `coverage-pct`, `delta` |
| setup-vault-token | Fleet-standard Vault auth wrapper (Kubernetes SA → env-var secrets) | `vault-url`, `vault-role`, `secrets`, `extra-secrets` | `vault-token` (populated as of DEBT-W12; full Kubernetes-auth E2E still unverified — see TECHNICAL-DEBT.md) |
| sign-with-cosign | Signs a Docker image with Cosign keyless OIDC, `main`-only guard built in | `image-ref`, `image-digest`, `only-on-main` | `signed`, `signature-ref` |
| trigger-canary | Applies Istio/Flagger Canary weight changes for progressive rollout | `service-name`, `namespace`, `weight`, `method` | `weight-applied`, `canary-status` |
| wait-for-metrics | Soaks then validates Prometheus error-rate/p99 thresholds, signals rollback | `duration-minutes`, `prometheus-url`, `error-rate-threshold`, `p99-latency-threshold` | `metrics-healthy`, `error-rate`, `p99-latency` |

## Policies

| File | Purpose |
|---|---|
| approved-base-images.json | Allowed Docker base images (enforced inline by `reusable-build-push.yml` as a pre-build supply-chain gate) |
| python-versions.json | Approved Python versions |
| node-version.json | Approved Node.js version |

### Approved base images gate

`reusable-build-push.yml` validates every `FROM` in the Dockerfile it is about to
build against `approved-base-images.json` **before** the build runs. A non-approved
base image fails the job. This is the enforcement path for all build-push consumers —
no extra `uses:` block is needed in your `ci.yml`.

The matcher ignores `scratch`, intra-Dockerfile multi-stage references
(`FROM builder` where `builder` was declared with `AS builder`), and templated
refs that only resolve at build time (`${BUILDER_IMAGE}`, `golang:${GO_VERSION}-alpine`).

When you bump a base image in a Dockerfile, add the new tag to
`approved-base-images.json` in the same change so the gate stays green. The
canonical language versions live in `go-version.json` / `elixir-version.json` /
`python-versions.json` / `node-version.json`; keep the whitelist tags consistent
with them.
