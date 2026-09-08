#!/usr/bin/env sh
set -eu

BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "OpsPilot environment verification"
echo "Target: $BASE_URL"

health="$(curl -fsS "$BASE_URL/health")"
echo "[PASS] API health: $health"

ready="$(curl -fsS "$BASE_URL/ready")"
echo "[PASS] Dependencies ready: $ready"

echo "[PASS] OpsPilot foundation is reachable"
