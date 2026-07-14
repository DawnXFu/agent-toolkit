#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SCOPE="user"
AGENT="all"
PROJECT_ROOT="$(pwd)"
LINK="false"

usage() {
  cat <<'USAGE'
Usage: install.sh [--scope user|project] [--agent all|claude|codex|opencode|generic]
                   [--project-root PATH] [--link]
USAGE
}

require_value() {
  local option="$1"
  local value="${2:-}"
  if [[ -z "$value" ]]; then
    echo "Missing value for $option" >&2
    usage
    exit 2
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope) require_value "$1" "${2:-}"; SCOPE="$2"; shift 2 ;;
    --agent) require_value "$1" "${2:-}"; AGENT="$2"; shift 2 ;;
    --project-root) require_value "$1" "${2:-}"; PROJECT_ROOT="$2"; shift 2 ;;
    --link) LINK="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

[[ "$SCOPE" == "user" || "$SCOPE" == "project" ]] || { echo "Invalid scope" >&2; exit 2; }
case "$AGENT" in all|claude|codex|opencode|generic) ;; *) echo "Invalid agent" >&2; exit 2;; esac

if [[ "$SCOPE" == "user" ]]; then
  SHARED_DEST="$HOME/.agents/skills/unified-handoff"
  CLAUDE_DEST="$HOME/.claude/skills/unified-handoff"
else
  PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd -P)"
  SHARED_DEST="$PROJECT_ROOT/.agents/skills/unified-handoff"
  CLAUDE_DEST="$PROJECT_ROOT/.claude/skills/unified-handoff"
fi

canonical_destination() {
  local destination="$1"
  local parent
  parent="$(dirname "$destination")"
  mkdir -p "$parent"
  printf '%s/%s\n' "$(cd "$parent" && pwd -P)" "$(basename "$destination")"
}

install_to() {
  local destination="$1"
  local canonical
  canonical="$(canonical_destination "$destination")"

  if [[ "$canonical" == "$SOURCE_DIR" ]]; then
    echo "Already installed at source location: $destination"
    return 0
  fi

  rm -rf -- "$destination"
  if [[ "$LINK" == "true" ]]; then
    ln -s -- "$SOURCE_DIR" "$destination"
  else
    cp -R -- "$SOURCE_DIR" "$destination"
  fi
  echo "Installed: $destination"
}

case "$AGENT" in
  claude) install_to "$CLAUDE_DEST" ;;
  codex|opencode|generic) install_to "$SHARED_DEST" ;;
  all) install_to "$SHARED_DEST"; install_to "$CLAUDE_DEST" ;;
esac
