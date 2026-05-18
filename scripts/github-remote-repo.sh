#!/usr/bin/env bash
# github-remote-repo.sh — Resolve a GitHub remote name or URL to owner/repo.
set -euo pipefail

usage() {
    echo "Usage: github-remote-repo.sh <remote-name-or-url>" >&2
}

if [[ $# -ne 1 ]]; then
    usage
    exit 2
fi

arg="$1"
if [[ "$arg" == *://* || "$arg" == *@* ]]; then
    url="$arg"
else
    url=$(git remote get-url "$arg") || exit 1
fi

url="${url%/}"
url="${url%.git}"
url="${url%/}"

if [[ "$url" =~ ^git@github[.]com:([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)$ ]]; then
    printf '%s/%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    exit 0
fi

if [[ "$url" =~ ^(https?|ssh|git)://([^@]+@)?github[.]com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)$ ]]; then
    printf '%s/%s\n' "${BASH_REMATCH[3]}" "${BASH_REMATCH[4]}"
    exit 0
fi

redacted=$(printf '%s' "$url" | sed -E 's#://[^@]+@#://<REDACTED>@#')
printf 'github-remote-repo.sh: cannot parse %s\n' "$redacted" >&2
exit 2
