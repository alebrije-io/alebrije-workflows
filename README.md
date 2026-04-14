# alebrije-workflows

Centralized GitHub Actions reusable workflows and CI/CD utilities for all Alebrije microservices.

## Reusable Workflows

| Workflow | Purpose |
|---|---|
| reusable-test.yml | Python tests (pytest + coverage, matrix 3.12/3.13) |
| reusable-test-node.yml | Node.js tests |
| reusable-build-push.yml | Docker build + push to Docker Hub + Cosign signing |
| reusable-deploy.yml | Deploy to Kubernetes (OVH) + smoke test |
| reusable-security-scan.yml | Trivy vulnerability scan + SBOM |
| reusable-pact-verify.yml | Contract testing (Pact) |

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

      deploy:
        needs: build-and-push
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

## Scripts

| Script | Purpose |
|---|---|
| validate-test-pool.sh | Detects orphaned tests (files not declared in CI pool) |
| smoke_test.sh | Post-deploy health check |

## Policies

| File | Purpose |
|---|---|
| approved-base-images.json | Allowed Docker base images |
| python-versions.json | Approved Python versions |
| node-version.json | Approved Node.js version |
