#!/usr/bin/env bash
# scripts/validate-test-pool.sh
#
# CRITICAL: Orphaned Test Detection Guardian
#
# This script enforces the immutable rule:
#   "Every test_*.py file MUST be declared in the CI pool.
#    No test shall be forgotten. No orphaned tests allowed."
#
# It runs BEFORE any tests execute in CI to ensure the test registry is clean.
#
# HOW IT WORKS:
#   1. Scan filesystem for all tests/test_*.py files (ACTUAL state)
#   2. Read TEST_FILES env var (DECLARED state in ci.yml)
#   3. Compare actual vs declared
#   4. Report and FAIL if mismatches exist
#
# USAGE:
#   ./scripts/validate-test-pool.sh
#   TEST_FILES="tests/test_api.py tests/test_db.py" ./scripts/validate-test-pool.sh
#
# CI CONTEXT:
#   Invoked from workflow with:
#     TEST_FILES: ${{ inputs.test-files }}  # Input from ci.yml
#
# EXIT CODES:
#   0 = all tests properly registered
#   1 = orphaned or phantom tests detected

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# PHASE 1: Discover actual test files in filesystem
# ============================================================================
echo ">>> PHASE 1: Scanning filesystem for test_*.py files..."

ACTUAL_TESTS=()
if [ -d "tests" ]; then
  while IFS= read -r -d '' file; do
    # Normalize path (remove leading ./)
    normalized="${file#./}"
    ACTUAL_TESTS+=("$normalized")
  done < <(find tests -name "test_*.py" -type f -print0 2>/dev/null || true)

  # Sort for consistent output
  mapfile -t ACTUAL_TESTS < <(printf '%s\n' "${ACTUAL_TESTS[@]}" | sort)
fi

if [ ${#ACTUAL_TESTS[@]} -eq 0 ]; then
  echo -e "${YELLOW}⚠️  No test_*.py files found in tests/ directory${NC}"
  echo "   (This is OK if your service has no Python tests)"
  exit 0
fi

echo "   Found ${#ACTUAL_TESTS[@]} test file(s):"
for file in "${ACTUAL_TESTS[@]}"; do
  echo "     • $file"
done

# ============================================================================
# PHASE 2: Parse declared test files from TEST_FILES env var
# ============================================================================
echo ""
echo ">>> PHASE 2: Parsing TEST_FILES from environment..."

DECLARED_TESTS=()
if [ -z "${TEST_FILES:-}" ]; then
  echo -e "${YELLOW}⚠️  TEST_FILES environment variable is empty${NC}"
  echo "   (If you have tests, this will cause failures below)"
else
  # Parse space/comma-separated test file list
  # Support both "tests/test_a.py tests/test_b.py" and "tests/test_a.py,tests/test_b.py"
  TEST_FILES_CLEAN="${TEST_FILES//,/ }"  # Replace commas with spaces

  while IFS= read -r file; do
    # Skip empty lines and whitespace
    [ -z "${file// }" ] && continue
    # Normalize path
    normalized="${file#./}"
    DECLARED_TESTS+=("$normalized")
  done < <(echo "$TEST_FILES_CLEAN" | tr ' ' '\n')

  # Remove duplicates and sort
  mapfile -t DECLARED_TESTS < <(printf '%s\n' "${DECLARED_TESTS[@]}" | sort -u)
fi

if [ ${#DECLARED_TESTS[@]} -eq 0 ]; then
  echo -e "${YELLOW}⚠️  No declared tests in TEST_FILES${NC}"
else
  echo "   Found ${#DECLARED_TESTS[@]} declared test file(s):"
  for file in "${DECLARED_TESTS[@]}"; do
    echo "     • $file"
  done
fi

# ============================================================================
# PHASE 3: Detect orphaned tests (actual but not declared)
# ============================================================================
echo ""
echo ">>> PHASE 3: Checking for orphaned tests..."

ORPHANED=()
for actual in "${ACTUAL_TESTS[@]}"; do
  found=0
  for declared in "${DECLARED_TESTS[@]}"; do
    if [ "$actual" = "$declared" ]; then
      found=1
      break
    fi
  done
  if [ $found -eq 0 ]; then
    ORPHANED+=("$actual")
  fi
done

if [ ${#ORPHANED[@]} -gt 0 ]; then
  echo -e "${RED}❌ ORPHANED TESTS DETECTED — tests exist but are NOT in the CI pool:${NC}"
  for file in "${ORPHANED[@]}"; do
    echo -e "  ${RED}• $file${NC}"
  done
  echo ""
  echo -e "${RED}ACTION REQUIRED:${NC}"
  echo "  1. Add these files to your ci.yml TEST_FILES input"
  echo "  2. Add them to run_prepush.sh if it exists"
  echo "  3. Commit and push"
  echo ""
  echo "  Rule: Every test_*.py MUST be declared in the CI pool."
  echo "  See: alebrije-workflows/docs/adding-a-new-service.md"
  echo ""
  exit 1
fi

echo -e "${GREEN}✅ No orphaned tests found${NC}"

# ============================================================================
# PHASE 4: Detect phantom tests (declared but not actual)
# ============================================================================
echo ""
echo ">>> PHASE 4: Checking for phantom tests..."

PHANTOM=()
for declared in "${DECLARED_TESTS[@]}"; do
  found=0
  for actual in "${ACTUAL_TESTS[@]}"; do
    if [ "$actual" = "$declared" ]; then
      found=1
      break
    fi
  done
  if [ $found -eq 0 ]; then
    PHANTOM+=("$declared")
  fi
done

if [ ${#PHANTOM[@]} -gt 0 ]; then
  echo -e "${RED}❌ PHANTOM TESTS DETECTED — declared in CI but files don't exist:${NC}"
  for file in "${PHANTOM[@]}"; do
    echo -e "  ${RED}• $file${NC}"
  done
  echo ""
  echo -e "${RED}ACTION REQUIRED:${NC}"
  echo "  1. Either create these files or remove them from ci.yml TEST_FILES"
  echo "  2. Also update run_prepush.sh if it exists"
  echo "  3. Commit and push"
  echo ""
  echo "  Rule: TEST_FILES must reflect actual test files."
  echo "  See: alebrije-workflows/docs/adding-a-new-service.md"
  echo ""
  exit 1
fi

echo -e "${GREEN}✅ No phantom tests found${NC}"

# ============================================================================
# PHASE 5: Summary
# ============================================================================
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}✅ All test files properly registered in CI pool${NC}"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "   Filesystem: ${#ACTUAL_TESTS[@]} test file(s)"
echo "   CI Pool:    ${#DECLARED_TESTS[@]} declared test file(s)"
echo ""
echo "Status: CLEAN — Ready to execute tests."
echo ""
exit 0
