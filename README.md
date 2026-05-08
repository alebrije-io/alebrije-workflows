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
| reusable-approved-images-check.yml | Validate base images against approval list |
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

## Policies

| File | Purpose |
|---|---|
| approved-base-images.json | Allowed Docker base images |
| python-versions.json | Approved Python versions |
| node-version.json | Approved Node.js version |
