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

awk -v F2="$tmp2" -v F3="$tmp3" -v CPATH="$conflict_path" '
function readfile(fn, arr,    n, line) {
    n = 0
    while ((getline line < fn) > 0) {
        arr[++n] = line
    }
    close(fn)
    return n
}
function basename_path(p,    x) {
    x = p
    sub(/^.*\//, "", x)
    return x
}
# --- Markdown (## headings) ---
function md_first_heading_line(arr, n,    i) {
    for (i = 1; i <= n; i++) {
        if (arr[i] ~ /^## /) {
            return arr[i]
        }
    }
    return ""
}
function md_first_heading_index(arr, n,    i) {
    for (i = 1; i <= n; i++) {
        if (arr[i] ~ /^## /) {
            return i
        }
    }
    return 0
}
function md_second_heading_index(arr, n, start,    i) {
    for (i = start + 1; i <= n; i++) {
        if (arr[i] ~ /^## /) {
            return i
        }
    }
    return 0
}
# --- reStructuredText (title + underline section headers) ---
function is_rst_adornment(ul, title,    len_t, k, c) {
    len_t = length(title)
    if (ul == "" || title == "") {
        return 0
    }
    if (length(ul) < len_t || length(ul) < 3) {
        return 0
    }
    if (ul !~ /^[#*=-~^"'\''`:.+_-]+$/) {
        return 0
    }
    c = substr(ul, 1, 1)
    for (k = 1; k <= length(ul); k++) {
        if (substr(ul, k, 1) != c) {
            return 0
        }
    }
    return 1
}
function rst_first_title_line(arr, n,    i) {
    for (i = 1; i < n; i++) {
        if (arr[i] == "" || arr[i + 1] == "") {
            continue
        }
        if (arr[i] ~ /^[[:space:]]/) {
            continue
        }
        if (!(arr[i] ~ /[A-Za-z0-9]/)) {
            continue
        }
        if (is_rst_adornment(arr[i + 1], arr[i])) {
            return arr[i]
        }
    }
    return ""
}
function rst_first_title_index(arr, n,    i) {
    for (i = 1; i < n; i++) {
        if (arr[i] == "" || arr[i + 1] == "") {
            continue
        }
        if (arr[i] ~ /^[[:space:]]/) {
            continue
        }
        if (!(arr[i] ~ /[A-Za-z0-9]/)) {
            continue
        }
        if (is_rst_adornment(arr[i + 1], arr[i])) {
            return i
        }
    }
    return 0
}
function rst_second_title_index(arr, n, fh,    i) {
    for (i = fh + 2; i < n; i++) {
        if (arr[i] == "" || arr[i + 1] == "") {
            continue
        }
        if (arr[i] ~ /^[[:space:]]/) {
            continue
        }
        if (!(arr[i] ~ /[A-Za-z0-9]/)) {
            continue
        }
        if (is_rst_adornment(arr[i + 1], arr[i])) {
            return i
        }
    }
    return 0
}
BEGIN {
    n2 = readfile(F2, a2)
    n3 = readfile(F3, a3)
    bn = basename_path(CPATH)
    if (bn ~ /\.rst$/) {
        mode = "rst"
    } else if (bn ~ /\.md$/) {
        mode = "md"
    } else {
        h2m = md_first_heading_line(a2, n2)
        h3m = md_first_heading_line(a3, n3)
        if (h2m != "" && h3m != "" && h2m == h3m) {
            mode = "md"
        } else {
            mode = "rst"
        }
    }
    if (mode == "md") {
        h2 = md_first_heading_line(a2, n2)
        h3 = md_first_heading_line(a3, n3)
        if (h2 == "" || h3 == "" || h2 != h3) {
            exit 1
        }
        fh2 = md_first_heading_index(a2, n2)
        fh3 = md_first_heading_index(a3, n3)
        sh2 = md_second_heading_index(a2, n2, fh2)
        sh3 = md_second_heading_index(a3, n3, fh3)
        body_off = 1
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
        for (i = fh2 + body_off; i <= end2; i++) {
            print a2[i]
            seen[a2[i]] = 1
        }
        for (i = fh3 + body_off; i <= end3; i++) {
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
    }
    # rst
    h2 = rst_first_title_line(a2, n2)
    h3 = rst_first_title_line(a3, n3)
    if (h2 == "" || h3 == "" || h2 != h3) {
        exit 1
    }
    fh2 = rst_first_title_index(a2, n2)
    fh3 = rst_first_title_index(a3, n3)
    sh2 = rst_second_title_index(a2, n2, fh2)
    sh3 = rst_second_title_index(a3, n3, fh3)
    body_off = 2
    for (i = 1; i < fh2; i++) {
        print a2[i]
    }
    print a2[fh2]
    print a2[fh2 + 1]
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
    for (i = fh2 + body_off; i <= end2; i++) {
        print a2[i]
        seen[a2[i]] = 1
    }
    for (i = fh3 + body_off; i <= end3; i++) {
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
