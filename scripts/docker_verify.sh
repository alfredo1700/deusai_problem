#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== docker version ==="
docker --version
docker compose version

echo "=== build + run tests ==="
docker compose --profile test run --rm --build test

echo "=== start api ==="
docker compose up --build -d api
sleep 5
docker compose ps

echo "=== health ==="
curl -sS http://127.0.0.1:8000/health
echo

echo "=== chat premium flow ==="
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H "content-type: application/json" \
  -d '{"session_id":"docker-demo","message":"Hello"}'
echo
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H "content-type: application/json" \
  -d '{"session_id":"docker-demo","message":"My name is Lisa phone +1122334455 IBAN DE89370400440532013000"}'
echo
curl -sS -X POST http://127.0.0.1:8000/chat \
  -H "content-type: application/json" \
  -d '{"session_id":"docker-demo","message":"Yoda"}'
echo

echo "=== api logs ==="
docker compose logs --tail=40 api

echo "=== teardown ==="
docker compose down
echo DONE
