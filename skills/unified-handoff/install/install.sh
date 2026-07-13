#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope) SCOPE="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --project-root) PROJECT_ROOT="$2"; shift 2 ;;
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
  PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
  SHARED_DEST="$PROJECT_ROOT/.agents/skills/unified-handoff"
  CLAUDE_DEST="$PROJECT_ROOT/.claude/skills/unified-handoff"
fi

install_to() {
  local destination="$1"
  mkdir -p "$(dirname "$destination")"
  rm -rf "$destination"
  if [[ "$LINK" == "true" ]]; then
    ln -s "$SOURCE_DIR" "$destination"
  else
    cp -R "$SOURCE_DIR" "$destination"
  fi
  echo "Installed: $destination"
}

case "$AGENT" in
  claude) install_to "$CLAUDE_DEST" ;;
  codex|opencode|generic) install_to "$SHARED_DEST" ;;
  all) install_to "$SHARED_DEST"; install_to "$CLAUDE_DEST" ;;
esac
