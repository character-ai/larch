#!/usr/bin/env bash
# auto-resolve-changelog.sh — Merge :2:/:3: CHANGELOG stages during rebase (deterministic).
set -euo pipefail

conflict_path=${1:-}
if [[ -z "$conflict_path" ]]; then
    printf 'usage: auto-resolve-changelog.sh CHANGELOG_PATH\n' >&2
    exit 1
fi

tmp2=$(mktemp "${TMPDIR:-/tmp}/larch-arv-up.XXXXXX")
tmp3=$(mktemp "${TMPDIR:-/tmp}/larch-arv-theirs.XXXXXX")
trap 'rm -f "$tmp2" "$tmp3"' EXIT

git show ":2:${conflict_path}" >"$tmp2" 2>/dev/null || exit 1
git show ":3:${conflict_path}" >"$tmp3" 2>/dev/null || exit 1

out_tmp=$(mktemp "${TMPDIR:-/tmp}/larch-arv-out.XXXXXX")
trap 'rm -f "$tmp2" "$tmp3" "$out_tmp"' EXIT

awk -v F2="$tmp2" -v F3="$tmp3" '
function readfile(fn, arr,    n, line) {
    n = 0
    while ((getline line < fn) > 0) {
        arr[++n] = line
    }
    close(fn)
    return n
}
function first_heading_line(arr, n,    i) {
    for (i = 1; i <= n; i++) {
        if (arr[i] ~ /^## /) {
            return arr[i]
        }
    }
    return ""
}
function first_heading_index(arr, n,    i) {
    for (i = 1; i <= n; i++) {
        if (arr[i] ~ /^## /) {
            return i
        }
    }
    return 0
}
function second_heading_index(arr, n, start,    i) {
    for (i = start + 1; i <= n; i++) {
        if (arr[i] ~ /^## /) {
            return i
        }
    }
    return 0
}
BEGIN {
    n2 = readfile(F2, a2)
    n3 = readfile(F3, a3)
    h2 = first_heading_line(a2, n2)
    h3 = first_heading_line(a3, n3)
    if (h2 == "" || h3 == "" || h2 != h3) {
        exit 1
    }
    fh2 = first_heading_index(a2, n2)
    fh3 = first_heading_index(a3, n3)
    sh2 = second_heading_index(a2, n2, fh2)
    sh3 = second_heading_index(a3, n3, fh3)
    for (i = 1; i < fh2; i++) {
        print a2[i]
    }
    print a2[fh2]
    delete seen
    if (sh2 == 0) {
        end2 = n2
    } else {
        end2 = sh2 - 1
    }
    if (sh3 == 0) {
        end3 = n3
    } else {
        end3 = sh3 - 1
    }
    for (i = fh2 + 1; i <= end2; i++) {
        print a2[i]
        seen[a2[i]] = 1
    }
    for (i = fh3 + 1; i <= end3; i++) {
        if (!(a3[i] in seen)) {
            print a3[i]
            seen[a3[i]] = 1
        }
    }
    if (sh2 > 0) {
        for (i = sh2; i <= n2; i++) {
            print a2[i]
        }
    }
    exit 0
}' </dev/null >"$out_tmp" || exit 1

mv "$out_tmp" "$conflict_path"
