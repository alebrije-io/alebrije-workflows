#!/usr/bin/env bash
# run_prepush.sh — validación local obligatoria antes de push.
#
# Repo de workflows reutilizables: lo que vive aquí es YAML que otros repos
# llaman, JSON de pineo de versiones y esquemas de evento. No hay compilador ni
# suite local que correr, así que los únicos gates que aplican son los de
# credenciales, y los dos son fatales.
#
# 2026-09-07 (DEBT-FLOTA-REPOS-SIN-BASELINE): este repo no tenía prepush, así
# que no tenía NINGÚN gate local de credenciales — ni el Paso 0 canónico ni una
# comparación contra baseline. Se añaden los dos juntos porque uno sin el otro
# deja un hueco: el [1/2] busca patrones de credencial en el fuente, el [2/2]
# congela el conjunto de hallazgos de detect-secrets sobre el árbol de HEAD y
# falla cerrado ante cualquier entrada nueva.
#
# Aquí eso importa más que en otros repos, no menos: este árbol es el sitio
# donde por su propia naturaleza conviven nombres de secreto, rutas de Vault y
# DSN de contenedores efímeros. Congelar hoy ese conjunto es lo que permite ver
# mañana la entrada que no debería estar.
#
# audit-no-hardcoded-creds.sh es réplica byte a byte del canónico
# alebrije-infra/scripts/audit-no-hardcoded-creds.sh; quien lo verifica es
# alebrije-infra/scripts/audit-creds-sync.sh --check, que descubre el censo de
# la flota por la presencia de este mismo run_prepush.sh.
#
# Este script no invoca, activa ni dispara ningún workflow de GitHub: sólo
# ejecuta los dos guards locales.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== $(basename "$SCRIPT_DIR") — pre-push validation ==="

echo "[1/2] audit reglas inquebrantables"
bash ./audit-no-hardcoded-creds.sh

echo "[2/2] detect-secrets scan"
_SECRETS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_SECRETS_LOG="$(mktemp)"
if bash "$_SECRETS_ROOT/scripts/test-check-secrets-baseline.sh" > "$_SECRETS_LOG" 2>&1; then
    _SECRETS_RC=0
else
    _SECRETS_RC=$?
fi
sed 's/^/    /' "$_SECRETS_LOG"
if [ "$_SECRETS_RC" -ne 0 ]; then
    rm -f "$_SECRETS_LOG"
    echo "❌ check-secrets-baseline self-test FAILED — el gate esta roto, no el arbol"
    exit 1
fi
if bash "$_SECRETS_ROOT/scripts/check-secrets-baseline.sh" "$_SECRETS_ROOT" > "$_SECRETS_LOG" 2>&1; then
    _SECRETS_RC=0
else
    _SECRETS_RC=$?
fi
sed 's/^/    /' "$_SECRETS_LOG"
rm -f "$_SECRETS_LOG"
if [ "$_SECRETS_RC" -ne 0 ]; then
    echo "❌ secrets gate FAILED (exit $_SECRETS_RC)"
    exit 1
fi
echo "✅ secrets baseline in sync, all entries audited, no literal defaults"

echo "=== pre-push OK ==="
