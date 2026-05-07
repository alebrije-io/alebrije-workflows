#!/bin/bash
# Prometheus metrics checker for canary deployments
# Validates error rate and p99 latency against thresholds
#
# Usage: ./check-metrics.sh <prometheus-url> <service-name> <error-rate-threshold> <p99-latency-threshold> <check-interval> <duration-minutes> <soak-time-minutes>

set -euo pipefail

# Inputs
PROMETHEUS_URL="${1:?Prometheus URL required}"
SERVICE_NAME="${2:?Service name required}"
ERROR_RATE_THRESHOLD="${3:?Error rate threshold required}"
P99_LATENCY_THRESHOLD="${4:?P99 latency threshold required}"
CHECK_INTERVAL="${5:?Check interval required}"
DURATION_MINUTES="${6:?Duration minutes required}"
SOAK_TIME_MINUTES="${7:?Soak time minutes required}"

# Time calculations
SOAK_SECONDS=$((SOAK_TIME_MINUTES * 60))
MAX_SECONDS=$((DURATION_MINUTES * 60))
ELAPSED=0
CHECKS=0
ERROR_RATE=0
P99_LATENCY=0
METRICS_HEALTHY=true

echo "=== Prometheus Metrics Validation ==="
echo "Service: ${SERVICE_NAME}"
echo "Error rate threshold: ${ERROR_RATE_THRESHOLD}%"
echo "P99 latency threshold: ${P99_LATENCY_THRESHOLD}ms"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Soak time: ${SOAK_TIME_MINUTES}m"
echo "Max duration: ${DURATION_MINUTES}m"
echo ""

# If no Prometheus URL, just wait soak time
if [ -z "$PROMETHEUS_URL" ]; then
  echo "::notice::No Prometheus configured — waiting soak time only"
  sleep ${SOAK_SECONDS}
  echo "::notice::Soak time complete (no metrics checked)"
  exit 0
fi

# Verify Prometheus is reachable
if ! curl -sf "${PROMETHEUS_URL}/api/v1/status/config" &>/dev/null; then
  echo "::warning::Prometheus unreachable at ${PROMETHEUS_URL}"
  echo "::notice::Proceeding with soak time only"
  sleep ${SOAK_SECONDS}
  echo "::notice::Soak time complete (Prometheus unavailable)"
  exit 0
fi

echo "Prometheus reachable, starting metrics loop..."
echo ""

# Monitoring loop
while [ ${ELAPSED} -lt ${MAX_SECONDS} ]; do
  # Sleep for check interval
  sleep ${CHECK_INTERVAL}
  ELAPSED=$((ELAPSED + CHECK_INTERVAL))

  # PromQL Query 1: 5xx error rate as percentage
  # Formula: (5xx errors / all requests) * 100
  QUERY_ERROR_RATE="(sum(rate(http_requests_total{job=\"${SERVICE_NAME}\",status=~\"5..\"}[2m])) / sum(rate(http_requests_total{job=\"${SERVICE_NAME}\"}[2m])) * 100)"

  # URL encode and query
  RESPONSE_ER=$(curl -sf "${PROMETHEUS_URL}/api/v1/query" \
    --data-urlencode "query=${QUERY_ERROR_RATE}" \
    2>/dev/null || echo '{"data":{"result":[]}}')

  # Extract value (second element of result[0].value array)
  ERROR_RATE=$(echo "$RESPONSE_ER" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
  ERROR_RATE=$(printf "%.2f" "${ERROR_RATE}")

  # PromQL Query 2: p99 latency in milliseconds
  # Uses histogram_quantile on request duration histogram
  QUERY_P99="histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job=\"${SERVICE_NAME}\"}[2m])) by (le)) * 1000"

  RESPONSE_P99=$(curl -sf "${PROMETHEUS_URL}/api/v1/query" \
    --data-urlencode "query=${QUERY_P99}" \
    2>/dev/null || echo '{"data":{"result":[]}}')

  # Extract value and convert to ms
  P99_LATENCY=$(echo "$RESPONSE_P99" | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "0")
  P99_LATENCY=$(printf "%.0f" "${P99_LATENCY}")

  CHECKS=$((CHECKS + 1))

  # Calculate soak progress
  SOAK_ELAPSED=$((ELAPSED - SOAK_SECONDS))
  if [ ${SOAK_ELAPSED} -lt 0 ]; then
    SOAK_STATUS="soak-wait-$((-SOAK_ELAPSED))s"
  else
    SOAK_STATUS="validating-for-${SOAK_ELAPSED}s"
  fi

  echo "[Check #${CHECKS} | ${SOAK_STATUS}] Error rate: ${ERROR_RATE}% | P99 latency: ${P99_LATENCY}ms"

  # Only validate thresholds AFTER soak time has elapsed
  if [ ${ELAPSED} -ge ${SOAK_SECONDS} ]; then
    # Use bc for decimal comparison
    ER_CHECK=$(echo "${ERROR_RATE} <= ${ERROR_RATE_THRESHOLD}" | bc -l)
    P99_CHECK=$(echo "${P99_LATENCY} <= ${P99_LATENCY_THRESHOLD}" | bc -l)

    if [ "${ER_CHECK}" != "1" ]; then
      echo "::error::Error rate ${ERROR_RATE}% EXCEEDS threshold ${ERROR_RATE_THRESHOLD}%"
      METRICS_HEALTHY=false
      break
    fi

    if [ "${P99_CHECK}" != "1" ]; then
      echo "::error::P99 latency ${P99_LATENCY}ms EXCEEDS threshold ${P99_LATENCY_THRESHOLD}ms"
      METRICS_HEALTHY=false
      break
    fi
  fi
done

# Summary report
echo ""
echo "=== Metrics Validation Summary ==="
echo "Total checks: ${CHECKS}"
echo "Final error rate: ${ERROR_RATE}%"
echo "Final p99 latency: ${P99_LATENCY}ms"
echo "Metrics healthy: ${METRICS_HEALTHY}"
echo ""

if [ "${METRICS_HEALTHY}" == "true" ]; then
  echo "::notice::All metrics within threshold — canary is healthy"
  exit 0
else
  echo "::error::Metrics validation FAILED — initiating rollback"
  exit 1
fi
