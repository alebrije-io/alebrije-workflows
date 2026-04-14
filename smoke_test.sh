#!/usr/bin/env bash
# scripts/smoke_test.sh
#
# Post-deployment health check for Alebrije services.
#
# Verifies that critical endpoints respond after deployment:
#   - /health or /healthz endpoint returns 200 OK
#   - Service is reachable and responding
#   - Basic connectivity is established
#
# USAGE:
#   ./scripts/smoke_test.sh [url] [timeout]
#
# EXAMPLES:
#   # Default: http://localhost:8000/health
#   ./scripts/smoke_test.sh
#
#   # Custom URL and 30s timeout
#   ./scripts/smoke_test.sh "http://myservice:8080/healthz" 30
#
#   # With environment variable
#   SERVICE_URL="http://api.alebrije.local" ./scripts/smoke_test.sh
#
# ENVIRONMENT VARIABLES:
#   SERVICE_URL  - Endpoint to check (default: http://localhost:8000/health)
#   TIMEOUT      - Max seconds to wait (default: 20)
#   MAX_RETRIES  - Retry attempts (default: 5)
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================
SERVICE_URL="${1:-${SERVICE_URL:-http://localhost:8000/health}}"
TIMEOUT="${2:-${TIMEOUT:-20}}"
MAX_RETRIES="${MAX_RETRIES:-5}"
RETRY_DELAY="${RETRY_DELAY:-2}"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ============================================================================
# Smoke Test
# ============================================================================
echo ">>> Smoke test: checking $SERVICE_URL"
echo "    Timeout: ${TIMEOUT}s, Max retries: ${MAX_RETRIES}"
echo ""

ATTEMPT=1
while [ "$ATTEMPT" -le "$MAX_RETRIES" ]; do
  echo -n "  Attempt $ATTEMPT/$MAX_RETRIES ... "

  # Use curl with timeout and follow redirects
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time "$TIMEOUT" \
    --connect-timeout 5 \
    "$SERVICE_URL" 2>/dev/null || echo "000")

  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    echo -e "${GREEN}✅ HTTP $HTTP_CODE${NC}"
    echo ""
    echo -e "${GREEN}✅ Service is healthy and responding${NC}"
    exit 0
  fi

  echo -e "${YELLOW}HTTP $HTTP_CODE${NC}"

  if [ "$ATTEMPT" -lt "$MAX_RETRIES" ]; then
    echo "     Waiting ${RETRY_DELAY}s before retry..."
    sleep "$RETRY_DELAY"
  fi

  ATTEMPT=$((ATTEMPT + 1))
done

# ============================================================================
# Failure
# ============================================================================
echo ""
echo -e "${RED}❌ Service failed health check after $MAX_RETRIES attempts${NC}"
echo ""
echo "   URL:     $SERVICE_URL"
echo "   Timeout: ${TIMEOUT}s"
echo ""
echo "   Possible causes:"
echo "   - Service is not running or not accessible"
echo "   - Port is not exposed or bound"
echo "   - Network connectivity issue"
echo "   - Health endpoint returns non-200 status"
echo ""
exit 1
