#!/bin/bash
# Run the pinned local HyperFrames CLI in a film folder, telemetry off, refusing what AGENTS.md forbids.
# The Motion agent can run from a session opened outside this repository, where .claude/settings.json (which turns
# telemetry off) is not loaded: every `npx hyperframes` of motion-studio goes through this wrapper instead.
#
# Usage: bash .claude/skills/motion-studio/scripts/hf.sh <film_dir> <command> [args...]
#   e.g. hf.sh embody-reel-1-pop-up-papier snapshot --at 1.2,3.4
# HF_DRY_RUN=1 prints the command instead of running it (tests).
set -euo pipefail

dir="${1:?usage: hf.sh <film_dir> <hyperframes command> [args...]}"
shift
cmd="${1:?usage: hf.sh <film_dir> <hyperframes command> [args...]}"

case "$cmd" in
  feedback|publish|cloud|lambda|cloudrun|auth|upgrade|skills)
    echo "hf.sh: 'hyperframes $cmd' is forbidden by AGENTS.md (only on the user's explicit request, by hand)" >&2
    exit 3 ;;
esac
for arg in "$@"; do
  case "$arg" in
    --skill=*|--file-issue*|--search-miss*|*@latest*)
      echo "hf.sh: '$arg' is forbidden by AGENTS.md" >&2
      exit 3 ;;
  esac
done

export HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1 HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_UPDATE_CHECK=1
unset HYPERFRAMES_SKILL_BOOTSTRAP_DEPS
cd "$dir"
if [ -n "${HF_DRY_RUN:-}" ]; then
  echo "HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1 HYPERFRAMES_SKIP_SKILLS=1 HYPERFRAMES_NO_UPDATE_CHECK=1 npx --no hyperframes $*"
  exit 0
fi
exec npx --no hyperframes "$@"   # --no: never download, use the pinned node_modules of the repository
