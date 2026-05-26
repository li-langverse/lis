#!/bin/sh
# PH-DB-3 / WP-H: migrate + register plans, then hold container for compose healthchecks.
set -eu

lis db start --json
# In-process embed only — no TCP listener yet (registry-min). Keep container alive for dev.
exec tail -f /dev/null
