## What does this PR do?

<!-- Una descripción clara y concisa del cambio. Por qué fue necesario. -->

## Type of change

- [ ] Bug fix (non-breaking change que resuelve un issue)
- [ ] New feature (non-breaking change que agrega funcionalidad)
- [ ] Breaking change (fix o feature que cambiaría funcionalidad existente)
- [ ] Refactor / cleanup (no cambia funcionalidad)
- [ ] CI/CD / infra change
- [ ] Documentation update

## Testing

<!-- Describe cómo probaste el cambio. -->

- [ ] Tests unitarios / integración pasando localmente
- [ ] Cambios a CI/CD validados con `yamllint`
- [ ] Nueva documentación o cambios en workflows probados

## Coverage & Quality Gates

**Critical:** All changes must maintain **90% code coverage** floor (Rule G — immovable gate).

- [ ] Coverage reported (Before: **_%** → After: **_%**)
- [ ] If coverage decreased, added new tests to compensate
- [ ] No quality gates degraded (no `|| true`, no skip_files, no `--no-verify`)
- [ ] `bash run_prepush.sh` ✅ **PASSED locally** (prepush ritual completed)

## Security & Compliance

- [ ] No hardcoded credentials (all secrets from Vault / env vars)
- [ ] No `Co-Authored-By` or AI references in commits (100% user attribution)
- [ ] No suppressed errors (`rescue _ -> :ok`, `try/except: pass`, `|| true`)
- [ ] No modified quality thresholds to force green status

## Code Quality

- [ ] El código sigue los patrones existentes del módulo (leí al menos 1 archivo del mismo tipo)
- [ ] ADR compliance verified (if modifying patterns in PATTERNS.md or ADR refs)
- [ ] No Phase-2/future comments in production code
- [ ] Consistent with existing service standardization
- [ ] Documentation updated (README entry, workflow header comment, inline comments for non-obvious logic)

## Fleet Impact

- [ ] This change affects [choose all that apply]:
  - [ ] Reusable workflows (affects all consumers)
  - [ ] GitHub Actions configuration
  - [ ] Infrastructure / K8s manifests
  - [ ] Cross-repo patterns
  - [ ] CI/CD pipeline

If affecting reusable workflows:
- [ ] Backward compatibility maintained with existing `with:` inputs
- [ ] Documented breaking changes (if any) with migration path
- [ ] Version tag updated in workflow metadata (if applicable)

## Screenshots / logs (if applicable)

<!-- Para cambios de comportamiento observable — añadir evidencia -->

## Related issues / ADRs

<!-- Closes #XX | Relates to ADR-XX -->
