#!/usr/bin/env bash
# agent/example_test.sh
curl -s -X POST "http://127.0.0.1:8000/event" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your_api_key_here" \
  -d '{"ip":"5.6.7.8","payload":"UNION SELECT * FROM users","endpoint":"/login"}' | jq