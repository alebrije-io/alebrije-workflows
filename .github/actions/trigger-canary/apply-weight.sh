#!/bin/bash
# apply-weight.sh — Apply traffic weight to canary deployment via Istio/Flagger or manual K8s

set -e

SERVICE_NAME=""
NAMESPACE="platform"
WEIGHT=""
METHOD="manual"

while [[ $# -gt 0 ]]; do
  case $1 in
    --service) SERVICE_NAME="$2"; shift 2 ;;
    --namespace) NAMESPACE="$2"; shift 2 ;;
    --weight) WEIGHT="$2"; shift 2 ;;
    --method) METHOD="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ -z "$SERVICE_NAME" ] || [ -z "$WEIGHT" ]; then
  echo "Usage: apply-weight.sh --service <name> --namespace <ns> --weight <pct> --method [istio|manual]" >&2
  exit 1
fi

case "$METHOD" in
  istio)
    # Istio/Flagger Canary CRD: patch weight field.
    # Field path is `spec.analysis.maxWeight` -- NOT `spec.analysis.canary.maxWeight`.
    # Verified against the real upstream CRD (fetched from
    # https://raw.githubusercontent.com/fluxcd/flagger/main/artifacts/flagger/crd.yaml,
    # canaries.flagger.app, schema v1beta1): `spec.analysis` has no `canary` sub-object.
    # The old path silently no-oped: `apiextensions.k8s.io/v1` CRDs are structural
    # schemas, so the API server PRUNES unknown fields on a merge patch -- kubectl
    # exits 0 ("patched (no change)") and prints only a non-fatal warning, which the
    # old `2>/dev/null` below hid. `|| { exit 1; }` never fires because pruning is not
    # a kubectl error. Reproduced live against a real Canary CR in the docker-desktop
    # cluster before this fix (maxWeight stayed unchanged after the old payload) and
    # confirmed fixed after (maxWeight actually updates) -- see TECHNICAL-DEBT.md
    # DEBT-W02 for the exact commands/output.
    kubectl patch canary "${SERVICE_NAME}" \
      -n "${NAMESPACE}" \
      --type merge \
      -p "{\"spec\":{\"analysis\":{\"maxWeight\":${WEIGHT}}}}" || {
      echo "::warning::Failed to patch Canary CRD for ${SERVICE_NAME}"
      exit 1
    }
    ;;

  manual)
    # Manual: update label selectors on deployments for weighted traffic splitting
    # Assumes: stable uses label version=stable, canary uses version=canary
    # Ingress/Service routes traffic based on weight

    STABLE_REPLICAS=$(kubectl get deployment/${SERVICE_NAME} -n ${NAMESPACE} -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "1")
    TOTAL_REPLICAS=$((STABLE_REPLICAS + 1))

    # Calculate canary replicas based on weight
    CANARY_REPLICAS=$((WEIGHT * TOTAL_REPLICAS / 100))
    if [ $CANARY_REPLICAS -lt 1 ] && [ $WEIGHT -gt 0 ]; then
      CANARY_REPLICAS=1
    fi

    NEW_STABLE_REPLICAS=$((TOTAL_REPLICAS - CANARY_REPLICAS))

    echo "Applying weight ${WEIGHT}%: stable=${NEW_STABLE_REPLICAS}, canary=${CANARY_REPLICAS} (total=${TOTAL_REPLICAS})"

    # Scale canary
    kubectl scale deployment/${SERVICE_NAME}-canary \
      -n ${NAMESPACE} \
      --replicas=${CANARY_REPLICAS} 2>/dev/null || {
      echo "::warning::Failed to scale canary deployment"
      exit 1
    }

    # Update stable replica count (if not at 100%)
    if [ $WEIGHT -lt 100 ]; then
      kubectl scale deployment/${SERVICE_NAME} \
        -n ${NAMESPACE} \
        --replicas=${NEW_STABLE_REPLICAS} 2>/dev/null || {
        echo "::warning::Failed to scale stable deployment"
        exit 1
      }
    fi
    ;;

  *)
    echo "Unknown method: $METHOD" >&2
    exit 1
    ;;
esac

echo "✓ Applied ${WEIGHT}% weight to ${SERVICE_NAME}"
