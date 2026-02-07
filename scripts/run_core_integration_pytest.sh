#!/usr/bin/env bash
# Backward-compatible wrapper.
#
# The universal frontend is now: scripts/bonfire-core
#
# This file is kept to avoid breaking existing docs/scripts.
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/bonfire-core" "$@"
