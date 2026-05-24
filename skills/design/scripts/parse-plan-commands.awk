# parse-plan-commands.awk — invoked by parse-plan-commands.sh (-v REPO_ROOT -v PLUGIN_ROOT)
BEGIN {
    FS = ""
    header = "row_type\tsource_line\tscript_path\tflag\tflag_value\tnote\tcmd_uid"
    print header
    CMD_UID = 0
    in_fence = 0
    fence_lang = ""
    fence_start = 0
    buf = ""
    files_section = "" # create | update | ""
    pending_updated = ""
}

function tsv_escape(s,   t) {
    t = s
    gsub(/\r/, "", t)
    gsub(/\n/, "", t)
    gsub(/\t/, "", t)
    return t
}

function bad_field(s) {
    return (index(s, "\t") > 0 || index(s, "\n") > 0 || index(s, "\r") > 0)
}

function emit_parse_note(line, reason,   r) {
    r = tsv_escape(reason)
    if (bad_field(r)) {
        print "parse_note\t" line "\t\t\tcharset-violation\t" > "/dev/stderr"
        print "parse_note\t" line "\t\t\tcharset-violation\t"
        return
    }
    print "parse_note\t" line "\t\t\t" r "\t"
}

function emit_new_script(path, line,   p) {
    p = tsv_escape(path)
    if (bad_field(p)) {
        emit_parse_note(line, "allowlist-path-charset")
        return
    }
    print "new_script\t" line "\t" p "\t\t\t\t"
}

function emit_updated_flag(path, flag, line,   p, f) {
    p = tsv_escape(path)
    f = tsv_escape(flag)
    if (bad_field(p) || bad_field(f)) {
        emit_parse_note(line, "allowlist-charset")
        return
    }
    print "updated_flag\t" line "\t" p "\t" f "\t\t\t"
}

function strip_md_ticks(s,   t) {
    t = s
    gsub(/^[[:space:]]*`+/, "", t)
    gsub(/`+[[:space:]]*$/, "", t)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", t)
    return t
}

function heading_path(kind, line,   rest, idx) {
    idx = index(line, ":")
    if (idx == 0) return ""
    rest = substr(line, idx + 1)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", rest)
    return strip_md_ticks(rest)
}

# `### NEW [path]:` / `### UPDATED [path]:` bracket path (path between [ and ])
function bracket_heading_path(line,   s, e) {
    s = index(line, "[")
    e = index(line, "]")
    if (s == 0 || e == 0 || e <= s) return ""
    return strip_md_ticks(substr(line, s + 1, e - s - 1))
}

# --- Allow-list scan (runs for every input line) ---
{
    raw = $0
    if (match(raw, /^###[[:space:]]+Files[[:space:]]+to[[:space:]]+create([[:space:]]|$)/)) {
        files_section = "create"
        pending_updated = ""
        next
    }
    if (match(raw, /^###[[:space:]]+Files[[:space:]]+to[[:space:]]+update([[:space:]]|$)/)) {
        files_section = "update"
        pending_updated = ""
        next
    }
    h3_misc = match(raw, /^###[[:space:]]+/) && !match(raw, /^####/) && !match(raw, /^###[[:space:]]+Files[[:space:]]+to[[:space:]]+(create|update)/)
    h2_misc = match(raw, /^##[[:space:]]+/) && !match(raw, /^###/) && !match(raw, /^##[[:space:]]+Files[[:space:]]+to[[:space:]]+(create|update)/)
    if (h3_misc || h2_misc) {
        br_new = (match(raw, /^###[[:space:]]+NEW[[:space:]]+\[/) || match(raw, /^##[[:space:]]+NEW[[:space:]]+\[/))
        br_upd = (match(raw, /^###[[:space:]]+UPDATED[[:space:]]+\[/) || match(raw, /^##[[:space:]]+UPDATED[[:space:]]+\[/))
        if (match(raw, /^###[[:space:]]+NEW:/) || match(raw, /^##[[:space:]]+NEW:/) || br_new) {
            p = br_new ? bracket_heading_path(raw) : heading_path("NEW", raw)
            if (p != "") emit_new_script(p, FNR)
        }
        if (match(raw, /^###[[:space:]]+UPDATED:/) || match(raw, /^##[[:space:]]+UPDATED:/) || br_upd) {
            pending_updated = br_upd ? bracket_heading_path(raw) : heading_path("UPDATED", raw)
        } else if (match(raw, /^###[[:space:]]+/) || (match(raw, /^##[[:space:]]+/) && !match(raw, /^###/))) {
            pending_updated = ""
        }
        if ((match(raw, /^###[[:space:]]+/) && !match(raw, /^###[[:space:]]+(NEW:|UPDATED:)/) && !match(raw, /^###[[:space:]]+NEW[[:space:]]+\[/) && !match(raw, /^###[[:space:]]+UPDATED[[:space:]]+\[/)) || (match(raw, /^##[[:space:]]+/) && !match(raw, /^###/) && !match(raw, /^##[[:space:]]+(NEW:|UPDATED:)/) && !match(raw, /^##[[:space:]]+NEW[[:space:]]+\[/) && !match(raw, /^##[[:space:]]+UPDATED[[:space:]]+\[/))) {
            files_section = ""
        }
        next
    }

    if (pending_updated != "" && match(raw, /^[[:space:]]*-[[:space:]]+Adds[[:space:]]+flag:/)) {
        sub(/^[[:space:]]*-[[:space:]]+Adds[[:space:]]+flag:[[:space:]]*/, "", raw)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", raw)
        fl = strip_md_ticks(raw)
        if (fl != "" && index(fl, "--") == 1) fl = substr(fl, 3)
        if (fl != "") emit_updated_flag(pending_updated, fl, FNR)
    }

    if (files_section == "create" && match(raw, /\*\*NEW\*\*:/)) {
        sub(/^[^*]*\*\*NEW\*\*:[[:space:]]*/, "", raw)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", raw)
        p = strip_md_ticks(raw)
        if (p != "") emit_new_script(p, FNR)
    }
    if (files_section == "update" && match(raw, /\*\*UPDATED\*\*:/)) {
        sub(/^[^*]*\*\*UPDATED\*\*:[[:space:]]*/, "", raw)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", raw)
        pending_updated = strip_md_ticks(raw)
        next
    }
    if (files_section == "update" && pending_updated != "" && match(raw, /^[[:space:]]+-[[:space:]]+Adds[[:space:]]+flag:/)) {
        sub(/^[[:space:]]+-[[:space:]]+Adds[[:space:]]+flag:[[:space:]]*/, "", raw)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", raw)
        fl = strip_md_ticks(raw)
        if (fl != "" && index(fl, "--") == 1) fl = substr(fl, 3)
        if (fl != "") emit_updated_flag(pending_updated, fl, FNR)
    }
}

# --- Fenced code blocks ---
{
    if (match($0, /^```[[:space:]]*(bash|sh)[[:space:]]*$/)) {
        in_fence = 1
        fence_lang = substr($0, RSTART, RLENGTH)
        sub(/^```[[:space:]]*/, "", fence_lang)
        sub(/[[:space:]]*$/, "", fence_lang)
        fence_start = FNR
        buf = ""
        next
    }
    if (in_fence && match($0, /^```[[:space:]]*$/)) {
        process_fence_buffer(fence_start, buf)
        in_fence = 0
        fence_lang = ""
        fence_start = 0
        buf = ""
        next
    }
    if (in_fence) {
        if (buf != "") buf = buf "\n"
        buf = buf $0
        next
    }
}

END {
    if (in_fence && buf != "") {
        process_fence_buffer(fence_start, buf)
    }
}

function process_fence_buffer(start_line, text,   phys, nphys, i, piece, ns, j, seg) {
    if (text == "") return
    text = join_continuations(text)
    nphys = split(text, phys, /\n/)
    nphys = strip_heredoc_multiline(phys, nphys, PHYSOUT, start_line)
    for (i = 1; i <= nphys; i++) {
        piece = PHYSOUT[i]
        if (piece == "") continue
        phys_fnr = start_line + i
        ns = split_segments(piece, SEGS)
        for (j = 1; j <= ns; j++) {
            seg = SEGS[j]
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", seg)
            if (seg == "") continue
            parse_command_segment(phys_fnr, j - 1, seg)
        }
    }
}

# Remove heredoc bodies from physical lines; fill out[1..return]
function strip_heredoc_multiline(phys, n, out, fence_start,   i, line, pos, delim, c, rest, j, pre, qend) {
    j = 0
    for (i = 1; i <= n; i++) {
        line = phys[i]
        pos = index(line, "<<")
        if (pos == 0) {
            j++
            out[j] = line
            continue
        }
        pre = substr(line, 1, pos - 1)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", pre)
        if (pre != "") {
            j++
            out[j] = pre
        }
        rest = substr(line, pos + 2)
        gsub(/^[[:space:]]+/, "", rest)
        delim = ""
        if (substr(rest, 1, 1) == "'") {
            c = index(substr(rest, 2), "'")
            if (c > 0) delim = substr(rest, 2, c - 1)
        } else if (substr(rest, 1, 1) == "\"") {
            qend = index(substr(rest, 2), "\"")
            if (qend == 0) {
                emit_parse_note(fence_start + i, "heredoc-unterminated-quote")
                j++
                out[j] = line
                continue
            }
            delim = substr(rest, 2, qend - 1)
        } else {
            if (match(rest, /^[A-Za-z0-9_]+/)) {
                delim = substr(rest, RSTART, RLENGTH)
            }
        }
        if (delim == "") {
            j++
            out[j] = line
            continue
        }
        i++
        while (i <= n && phys[i] != delim) i++
    }
    return j
}

function join_continuations(s,   out, lines, n, i, line) {
    n = split(s, lines, /\n/)
    out = ""
    for (i = 1; i <= n; i++) {
        line = lines[i]
        while (match(line, /\\[[:space:]]*$/) && !match(line, /\\\\[[:space:]]*$/)) {
            sub(/\\[[:space:]]*$/, "", line)
            if (i < n) {
                i++
                line = line lines[i]
            } else break
        }
        if (out != "") out = out "\n"
        out = out line
    }
    return out
}

# Split on | && || ; outside quotes
function split_segments(s, arr,   n, i, c, len, seg, depth, in_s, in_d, esc, two) {
    n = 0
    seg = ""
    len = length(s)
    depth = 0
    in_s = 0
    in_d = 0
    esc = 0
    for (i = 1; i <= len; i++) {
        c = substr(s, i, 1)
        if (esc) {
            seg = seg c
            esc = 0
            continue
        }
        if (c == "\\" && (in_s || in_d)) {
            seg = seg c
            esc = 1
            continue
        }
        if (!in_d && c == "'" && !in_s) {
            in_s = 1
            seg = seg c
            continue
        }
        if (in_s) {
            seg = seg c
            if (c == "'") in_s = 0
            continue
        }
        if (!in_s && c == "\"" && !in_d) {
            in_d = 1
            seg = seg c
            continue
        }
        if (in_d) {
            seg = seg c
            if (c == "\"") in_d = 0
            continue
        }
        if (c == "(") depth++
        if (c == ")") { if (depth > 0) depth-- }
        if (depth > 0) {
            seg = seg c
            continue
        }
        two = substr(s, i, 2)
        if (two == "&&" || two == "||") {
            if (seg != "") {
                n++
                arr[n] = seg
                seg = ""
            }
            i++
            continue
        }
        if (c == "|" || c == ";") {
            if (seg != "") {
                n++
                arr[n] = seg
                seg = ""
            }
            continue
        }
        seg = seg c
    }
    if (seg != "") {
        n++
        arr[n] = seg
    }
    return n
}

# True when seg contains command substitution "$(..." that is not arithmetic "$((...".
function has_command_substitution(seg,   i, n) {
    n = length(seg)
    for (i = 1; i <= n; i++) {
        if (substr(seg, i, 2) != "$(") {
            continue
        }
        if (substr(seg, i, 3) == "$((") {
            continue
        }
        return 1
    }
    return 0
}

function normalize_token(t,   u, pref) {
    u = t
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", u)
    if (length(u) >= 2) {
        if ((substr(u, 1, 1) == "'" && substr(u, length(u), 1) == "'") ||
            (substr(u, 1, 1) == "\"" && substr(u, length(u), 1) == "\"")) {
            u = substr(u, 2, length(u) - 2)
        }
    }
    # ${CLAUDE_PLUGIN_ROOT}/…
    while (match(u, /\$\{CLAUDE_PLUGIN_ROOT\}\//)) {
        sub(/\$\{CLAUDE_PLUGIN_ROOT\}\//, "", u)
    }
    while (match(u, /\$CLAUDE_PLUGIN_ROOT\//)) {
        sub(/\$CLAUDE_PLUGIN_ROOT\//, "", u)
    }
    pref = PLUGIN_ROOT "/"
    if (index(u, pref) == 1) {
        u = substr(u, length(pref) + 1)
    }
    pref = REPO_ROOT "/"
    if (index(u, pref) == 1) {
        u = substr(u, length(pref) + 1)
    }
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", u)
    return u
}

function shift_tok(TOK, nt,   j) {
    for (j = 2; j <= nt; j++) TOK[j - 1] = TOK[j]
    delete TOK[nt]
    return nt - 1
}

function parse_command_segment(start_line, cmd_idx, seg, TOK, nt, t, script, uid, k, fl, fv, eq, nf, nxt) {
    if (has_command_substitution(seg)) {
        emit_parse_note(start_line, "subshell")
        return
    }
    if (index(seg, "<(") > 0) {
        emit_parse_note(start_line, "process_substitution")
        return
    }
    if (match(seg, /(^|[[:space:]])eval([[:space:]]|$)/)) {
        emit_parse_note(start_line, "eval")
        return
    }
    nt = tokenize(seg, TOK)
    for (;;) {
        if (nt <= 0) return
        t = normalize_token(TOK[1])
        if (t == "bash" || t == "sh" || t == "dash" || t == "/bin/bash" || t == "/bin/sh" || t == "env") {
            nt = shift_tok(TOK, nt)
            continue
        }
        if (t == "-c") {
            emit_parse_note(start_line, "inline-shell")
            return
        }
        if (t == "--") {
            nt = shift_tok(TOK, nt)
            continue
        }
        if (match(t, /^[A-Za-z_][A-Za-z0-9_]*=/)) {
            nt = shift_tok(TOK, nt)
            continue
        }
        break
    }
    if (nt <= 0) return
    script = normalize_token(TOK[1])
    if (script == "" || substr(script, 1, 1) == "-") return
    if (index(script, "..") > 0 || substr(script, 1, 1) == "/") {
        emit_parse_note(start_line, "non-canonical-script-path")
        return
    }
    if (bad_field(script)) {
        emit_parse_note(start_line, "charset-violation")
        return
    }
    uid = ++CMD_UID
    nf = 0
    k = 2
    while (k <= nt) {
        t = normalize_token(TOK[k])
        if (t == "") { k++; continue }
        if (substr(t, 1, 2) != "--") {
            k++
            continue
        }
        if (t == "--") break
        eq = index(t, "=")
        if (eq > 0) {
            fl = substr(t, 3, eq - 3)
            fv = substr(t, eq + 1)
        } else {
            fl = substr(t, 3)
            fv = ""
            if (fl == "") { k++; continue }
            if (k < nt) {
                nxt = normalize_token(TOK[k + 1])
                if (nxt != "" && substr(nxt, 1, 1) != "-") {
                    fv = nxt
                    k++
                }
            }
        }
        if (bad_field(fl) || bad_field(fv)) {
            emit_parse_note(start_line, "charset-violation")
            return
        }
        print "invocation\t" start_line "\t" script "\t" fl "\t" fv "\t\t" uid
        nf++
        k++
    }
    if (nf == 0) {
        print "invocation_no_flags\t" start_line "\t" script "\t\t\t\t" uid
    }
}

# tokenize: split seg on whitespace respecting quotes; fills TOKS[1..n], returns n
function tokenize(seg, TOKS,   n, i, len, c, cur, in_s, in_d, esc) {
    n = 0
    cur = ""
    len = length(seg)
    in_s = in_d = esc = 0
    for (i = 1; i <= len; i++) {
        c = substr(seg, i, 1)
        if (esc) {
            cur = cur c
            esc = 0
            continue
        }
        if (c == "\\" && (in_s || in_d)) {
            cur = cur c
            esc = 1
            continue
        }
        if (!in_d && c == "'" && !in_s) {
            in_s = 1
            cur = cur c
            continue
        }
        if (in_s) {
            cur = cur c
            if (c == "'") in_s = 0
            continue
        }
        if (!in_s && c == "\"" && !in_d) {
            in_d = 1
            cur = cur c
            continue
        }
        if (in_d) {
            cur = cur c
            if (c == "\"") in_d = 0
            continue
        }
        if (c == " " || c == "\t") {
            if (cur != "") {
                n++
                TOKS[n] = cur
                cur = ""
            }
            continue
        }
        cur = cur c
    }
    if (cur != "") {
        n++
        TOKS[n] = cur
    }
    return n
}
