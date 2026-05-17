#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

load_env_value() {
  local key="$1"
  local file="${2:-.env}"

  [[ -f "$file" ]] || return 1

  local line
  line="$(grep -E "^[[:space:]]*${key}=" "$file" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 1

  local value="${line#*=}"
  value="${value%$'\r'}"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf '%s' "$value"
}

echo "========================================"
echo "      Claude Code Launcher"
echo "========================================"
echo
echo " Select configuration:"
echo
echo " [1] Complex   (deepseek-v4-pro, effort=max)"
echo " [2] Daily     (deepseek-v4-flash, effort=medium)"
echo " [3] Light     (deepseek-v4-flash, effort=low)"
echo
read -r -p "Enter 1-3: " choice

export ANTHROPIC_BASE_URL="${ANTHROPIC_BASE_URL:-https://api.deepseek.com/anthropic}"

if [[ -z "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
  if env_token="$(load_env_value ANTHROPIC_AUTH_TOKEN ".env")"; then
    export ANTHROPIC_AUTH_TOKEN="$env_token"
  elif env_token="$(load_env_value ANTHROPIC_AUTH_TOKEN "job-intelligence-agent/.env")"; then
    export ANTHROPIC_AUTH_TOKEN="$env_token"
  elif env_token="$(load_env_value DEEPSEEK_API_KEY ".env")"; then
    export ANTHROPIC_AUTH_TOKEN="$env_token"
  elif env_token="$(load_env_value DEEPSEEK_API_KEY "job-intelligence-agent/.env")"; then
    export ANTHROPIC_AUTH_TOKEN="$env_token"
  else
    read -r -s -p "Enter DeepSeek API key: " env_token
    echo
    if [[ -z "$env_token" ]]; then
      echo "API key is required. Set ANTHROPIC_AUTH_TOKEN or DEEPSEEK_API_KEY in .env."
      exit 1
    fi
    export ANTHROPIC_AUTH_TOKEN="$env_token"
  fi
fi

export ANTHROPIC_DEFAULT_HAIKU_MODEL="${ANTHROPIC_DEFAULT_HAIKU_MODEL:-deepseek-v4-flash}"
export CLAUDE_CODE_SUBAGENT_MODEL="${CLAUDE_CODE_SUBAGENT_MODEL:-deepseek-v4-flash}"

case "$choice" in
  1)
    export ANTHROPIC_MODEL="deepseek-v4-pro"
    export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro"
    export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-pro"
    export CLAUDE_CODE_EFFORT_LEVEL="max"
    PROFILE="Complex"
    ;;
  2)
    export ANTHROPIC_MODEL="deepseek-v4-flash"
    export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-pro"
    export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-flash"
    export CLAUDE_CODE_EFFORT_LEVEL="medium"
    PROFILE="Daily"
    ;;
  3)
    export ANTHROPIC_MODEL="deepseek-v4-flash"
    export ANTHROPIC_DEFAULT_OPUS_MODEL="deepseek-v4-flash"
    export ANTHROPIC_DEFAULT_SONNET_MODEL="deepseek-v4-flash"
    export CLAUDE_CODE_EFFORT_LEVEL="low"
    PROFILE="Light"
    ;;
  *)
    echo
    echo "Invalid choice. Please enter 1, 2, or 3."
    exit 1
    ;;
esac

if ! command -v claude >/dev/null 2>&1; then
  echo "claude command was not found. Install Claude Code or make sure it is on PATH."
  exit 1
fi

echo
echo "[$PROFILE] Launching Claude Code..."
echo
exec claude "$@"
