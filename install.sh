#!/usr/bin/env bash
#
# install.sh — install this repo's prompts into multiple LLM interfaces from a
# single canonical source.
#
# Each prompt lives in prompts/<name>/ as:
#   prompt.md   the interface-agnostic prompt body (the single source of truth)
#   meta.yaml   flat key: value metadata (name, title, description, model)
#
# This script wraps that source in the right format and location for each target:
#   claude   ~/.claude/commands/<name>.md   (slash command)
#            ~/.claude/agents/<name>.md     (subagent)
#   kiro     ~/.kiro/agents/<name>.json     (custom agent)
#   generic  ~/.ai-prompts/<name>.md        (raw portable prompt)
#
# Usage:
#   ./install.sh [--target all|claude|kiro|generic] [--scope global|project]
#                [--only <name>] [--dry-run]
#
#   --target   which interface(s) to install into (default: all)
#   --scope    global installs into $HOME; project installs into ./ (default: global)
#   --only     install only the named prompt directory (default: all under prompts/)
#   --dry-run  print what would be written without writing anything

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPTS_DIR="$REPO_DIR/prompts"

TARGET="all"
SCOPE="global"
ONLY=""
DRY_RUN=0

usage() { sed -n '2,23p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET="${2:?--target needs a value}"; shift 2;;
    --target=*) TARGET="${1#*=}"; shift;;
    --scope) SCOPE="${2:?--scope needs a value}"; shift 2;;
    --scope=*) SCOPE="${1#*=}"; shift;;
    --only) ONLY="${2:?--only needs a value}"; shift 2;;
    --only=*) ONLY="${1#*=}"; shift;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 1;;
  esac
done

case "$TARGET" in all|claude|kiro|generic) ;; *) echo "Invalid --target: $TARGET" >&2; exit 1;; esac
case "$SCOPE" in
  global) CLAUDE_BASE="$HOME/.claude"; KIRO_BASE="$HOME/.kiro"; GENERIC_BASE="$HOME/.ai-prompts";;
  project) CLAUDE_BASE="$PWD/.claude"; KIRO_BASE="$PWD/.kiro"; GENERIC_BASE="$PWD/.ai-prompts";;
  *) echo "Invalid --scope: $SCOPE" >&2; exit 1;;
esac

want() { [ "$TARGET" = "all" ] || [ "$TARGET" = "$1" ]; }

# meta_get <meta-file> <key> — extract a single-line value for a flat key: value.
meta_get() {
  [ -f "$1" ] || return 0
  sed -n "s/^$2:[[:space:]]*//p" "$1" | head -n1 | sed 's/[[:space:]]*$//'
}

# emit <target-path> — write stdin to the path (or announce it under --dry-run).
emit() {
  local target="$1"
  if [ "$DRY_RUN" -eq 1 ]; then
    echo "  [dry-run] would write $target"
    cat >/dev/null
    return 0
  fi
  mkdir -p "$(dirname "$target")"
  cat > "$target"
  echo "  wrote $target"
}

# kiro_json <name> <description> <prompt-file> <model> — build the Kiro agent JSON.
# Uses jq or python3 for correct string escaping; skips (non-fatally) if neither exists.
kiro_json() {
  local name="$1" desc="$2" pf="$3" model="$4"
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg name "$name" --arg desc "$desc" --arg model "$model" --rawfile prompt "$pf" \
      '{name:$name, description:$desc, prompt:$prompt,
        resources:["file://.kiro/steering/**/*.md","file://AGENTS.md","file://CLAUDE.md"]}
       + (if $model=="" then {} else {model:$model} end)'
  elif command -v python3 >/dev/null 2>&1; then
    NAME="$name" DESC="$desc" MODEL="$model" PF="$pf" python3 - <<'PY'
import json, os
obj = {
    "name": os.environ["NAME"],
    "description": os.environ["DESC"],
    "prompt": open(os.environ["PF"]).read(),
    "resources": ["file://.kiro/steering/**/*.md", "file://AGENTS.md", "file://CLAUDE.md"],
}
if os.environ["MODEL"]:
    obj["model"] = os.environ["MODEL"]
print(json.dumps(obj, indent=2))
PY
  else
    return 1
  fi
}

install_prompt() {
  local dir="$1"
  local name desc model pf meta
  pf="$dir/prompt.md"
  meta="$dir/meta.yaml"
  [ -f "$pf" ] || { echo "skip $(basename "$dir"): no prompt.md"; return 0; }

  name="$(meta_get "$meta" name)"; [ -n "$name" ] || name="$(basename "$dir")"
  desc="$(meta_get "$meta" description)"; [ -n "$desc" ] || desc="$name"
  model="$(meta_get "$meta" model)"

  echo "prompt: $name"

  if want claude; then
    { printf -- '---\ndescription: %s\n---\n\n' "$desc"; cat "$pf"; } \
      | emit "$CLAUDE_BASE/commands/$name.md"
    { printf -- '---\nname: %s\ndescription: %s\n' "$name" "$desc"
      [ -n "$model" ] && printf -- 'model: %s\n' "$model"
      printf -- '---\n\n'; cat "$pf"; } \
      | emit "$CLAUDE_BASE/agents/$name.md"
  fi

  if want kiro; then
    if out="$(kiro_json "$name" "$desc" "$pf" "$model")"; then
      printf '%s\n' "$out" | emit "$KIRO_BASE/agents/$name.json"
    else
      echo "  skip kiro: needs jq or python3 for JSON generation" >&2
    fi
  fi

  if want generic; then
    cat "$pf" | emit "$GENERIC_BASE/$name.md"
  fi
}

[ -d "$PROMPTS_DIR" ] || { echo "No prompts/ directory found in $REPO_DIR" >&2; exit 1; }

[ "$DRY_RUN" -eq 1 ] && dry=", dry-run" || dry=""
echo "Installing (target=$TARGET, scope=$SCOPE$dry)"
found=0
for dir in "$PROMPTS_DIR"/*/; do
  [ -d "$dir" ] || continue
  [ -z "$ONLY" ] || [ "$(basename "$dir")" = "$ONLY" ] || continue
  found=1
  install_prompt "$dir"
done
[ "$found" -eq 1 ] || { echo "No matching prompt found${ONLY:+ for --only $ONLY}" >&2; exit 1; }
echo "Done."
