#!/bin/bash
# v0.3 evidence tunnel template — LOCAL LOOPBACK ONLY.
# Placeholders are intentionally not configured for remote use.
# Fill HOST_B/PORT_B and HOST_A/PORT_A only if you understand the v0.3
# evidence topology; defaults point at localhost and will not connect.
set -euo pipefail
export AUTOSSH_GATETIME=0
pkill -f "ssh.*-L 908" 2>/dev/null || true
sleep 1

HOST_B="${HOST_B:-localhost}"
PORT_B="${PORT_B:-22}"
HOST_A="${HOST_A:-localhost}"
PORT_A="${PORT_A:-22}"

autossh -M 0 -f -N -L 9081:localhost:8081 \
  -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -p "${PORT_B}" "${HOST_B}"
autossh -M 0 -f -N -L 9082:localhost:8081 \
  -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  -p "${PORT_A}" "${HOST_A}"
