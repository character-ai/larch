//! `checks contains-pins` scanner: verify literal pins in `test-*.sh` scripts.
//!
//! Port of the Python `check_contains_pins` scanner (`checks_run_relevant.py`).
//! Each `scripts/test-*.sh` and `skills/*/scripts/test-*.sh` script may assert,
//! through the shell `contains "$VAR" "literal"` grammar, that a canonical file
//! still embeds a literal. This module re-derives every assertion's target from
//! `$REPO_ROOT/...` and `$SCRIPT_DIR/../...` assignments and reports a `DEFECT`
//! for any literal that has drifted out of its target, plus per-assertion
//! diagnostics for shapes outside the v1 grammar.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::io;
use std::path::{Path, PathBuf};

use regex::{Captures, Regex};

/// Ordered scan result: defect count plus stdout/stderr lines to emit.
#[derive(Debug, Default)]
pub struct ContainsPinsScan {
    /// Number of drifted literals discovered.
    pub defects: usize,
    /// `DEFECT: ...` lines, in encounter order (Python prints these to stdout).
    pub stdout_lines: Vec<String>,
    /// `SKIPPED_NON_CANONICAL`/`UNRESOLVED_VAR` lines (Python prints to stderr).
    pub stderr_lines: Vec<String>,
}

/// Compiled pin-grammar regexes, matching the Python `Final` patterns.
struct PinRegexes {
    repo_assign: Regex,
    script_assign: Regex,
    contains: Regex,
}

impl PinRegexes {
    fn new() -> Self {
        Self {
            repo_assign: Regex::new(r#"^\s*([A-Za-z_][A-Za-z0-9_]*)="\$REPO_ROOT/([^"]*)"\s*$"#)
                .expect("static repo-assign pin regex"),
            script_assign: Regex::new(
                r#"^\s*([A-Za-z_][A-Za-z0-9_]*)="\$SCRIPT_DIR/\.\./([^"]*)"\s*$"#,
            )
            .expect("static script-assign pin regex"),
            contains: Regex::new(r#"^\s*contains\s+"\$([A-Za-z_][A-Za-z0-9_]*)"\s+"#)
                .expect("static contains-prefix pin regex"),
        }
    }
}

/// Shared, per-scan context threaded to the per-script/per-line helpers.
struct ScanCtx<'a> {
    repo_root: &'a Path,
    repo_root_canon: &'a Path,
    changed: Option<&'a HashSet<String>>,
    re: &'a PinRegexes,
}

/// Per-line location context for diagnostic messages.
#[derive(Clone, Copy)]
struct LineCtx<'a> {
    script_rel: &'a str,
    line_no: usize,
}

/// Scan every contains-pin test script and collect defects and diagnostics.
///
/// `repo_root` should be the resolved (canonical) repository root; `changed`,
/// when present, limits reporting to assertions whose script or target is in
/// that already-normalized repo-relative set.
// Callers pass the default-hasher `HashSet` the CLI layer builds.
#[allow(clippy::implicit_hasher)]
#[must_use]
pub fn scan_contains_pins(repo_root: &Path, changed: Option<&HashSet<String>>) -> ContainsPinsScan {
    let mut scan = ContainsPinsScan::default();
    let re = PinRegexes::new();
    let repo_root_canon = fs::canonicalize(repo_root).unwrap_or_else(|_| repo_root.to_path_buf());
    let ctx = ScanCtx {
        repo_root,
        repo_root_canon: &repo_root_canon,
        changed,
        re: &re,
    };
    for script in contains_pin_test_scripts(repo_root) {
        scan_one_script(&script, &ctx, &mut scan);
    }
    scan
}

/// Build the changed-scope set from a changed-files list, normalizing each row.
///
/// # Errors
/// Returns the underlying I/O error when the file cannot be read.
pub fn read_changed_scope(path: &Path, repo_root: &Path) -> io::Result<HashSet<String>> {
    let text = String::from_utf8_lossy(&fs::read(path)?).into_owned();
    let mut rels: HashSet<String> = HashSet::new();
    for line in py_splitlines(&text) {
        let raw = py_strip(line);
        if !raw.is_empty() {
            let _ = rels.insert(normalize_rel(raw, repo_root));
        }
    }
    Ok(rels)
}

/// Normalize a path to a repo-relative form, matching Python `_normalize_rel`.
#[must_use]
pub fn normalize_rel(path: &str, repo_root: &Path) -> String {
    let root_text = repo_root.to_string_lossy();
    let mut raw = path;
    let prefix = format!("{root_text}/");
    if let Some(stripped) = raw.strip_prefix(prefix.as_str()) {
        raw = stripped;
    }
    if let Some(stripped) = raw.strip_prefix("./") {
        raw = stripped;
    }
    let mut parts: Vec<&str> = Vec::new();
    for part in raw.split('/') {
        if part.is_empty() || part == "." {
            continue;
        }
        if part == ".." {
            if parts.is_empty() {
                parts.push(part);
            } else {
                let _ = parts.pop();
            }
        } else {
            parts.push(part);
        }
    }
    parts.join("/")
}

/// Ordered `scripts/test-*.sh` then `skills/*/scripts/test-*.sh` regular files.
fn contains_pin_test_scripts(repo_root: &Path) -> Vec<PathBuf> {
    let mut scripts = collect_test_scripts(&repo_root.join("scripts"));
    let skills = repo_root.join("skills");
    if skills.is_dir() {
        let mut skill_scripts: Vec<PathBuf> = Vec::new();
        if let Ok(entries) = fs::read_dir(&skills) {
            for entry in entries.flatten() {
                if entry.file_name().to_string_lossy().starts_with('.') {
                    continue;
                }
                let sdir = entry.path().join("scripts");
                if sdir.is_dir() {
                    skill_scripts.extend(collect_test_scripts(&sdir));
                }
            }
        }
        sort_by_string(&mut skill_scripts);
        scripts.extend(skill_scripts);
    }
    scripts.retain(|path| path.is_file());
    scripts
}

/// Direct `test-*.sh` children of `dir`, sorted by path string.
fn collect_test_scripts(dir: &Path) -> Vec<PathBuf> {
    let mut found: Vec<PathBuf> = Vec::new();
    if dir.is_dir()
        && let Ok(entries) = fs::read_dir(dir)
    {
        for entry in entries.flatten() {
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if name.starts_with("test-") && name.ends_with(".sh") {
                found.push(entry.path());
            }
        }
    }
    sort_by_string(&mut found);
    found
}

fn sort_by_string(paths: &mut [PathBuf]) {
    paths.sort_by(|a, b| a.to_string_lossy().cmp(&b.to_string_lossy()));
}

/// Scan one script: track `$REPO_ROOT`/`$SCRIPT_DIR` assignments, then assert.
fn scan_one_script(script: &Path, ctx: &ScanCtx, scan: &mut ContainsPinsScan) {
    let Some(text) = read_lossy(script) else {
        return;
    };
    let script_rel = normalize_rel(&script.to_string_lossy(), ctx.repo_root);
    let script_parent = script_parent_prefix(&script_rel);
    let mut vars: HashMap<String, String> = HashMap::new();
    for (index, line) in py_splitlines(&text).into_iter().enumerate() {
        if record_assignment(line, ctx, &script_parent, &mut vars) {
            continue;
        }
        let Some(caps) = ctx.re.contains.captures(line) else {
            continue;
        };
        let lctx = LineCtx {
            script_rel: &script_rel,
            line_no: index + 1,
        };
        handle_contains(line, &caps, lctx, &vars, ctx, scan);
    }
}

/// The `$SCRIPT_DIR/..` prefix: parent of the script's directory, or ".".
fn script_parent_prefix(script_rel: &str) -> String {
    let components: Vec<&str> = script_rel.split('/').collect();
    let keep = components.len().saturating_sub(2);
    if keep == 0 {
        ".".to_owned()
    } else {
        components[..keep].join("/")
    }
}

/// Record a `VAR="$REPO_ROOT/..."` or `VAR="$SCRIPT_DIR/../..."` assignment.
fn record_assignment(
    line: &str,
    ctx: &ScanCtx,
    script_parent: &str,
    vars: &mut HashMap<String, String>,
) -> bool {
    if let Some(caps) = ctx.re.repo_assign.captures(line) {
        let _ = vars.insert(caps[1].to_owned(), normalize_rel(&caps[2], ctx.repo_root));
        return true;
    }
    if let Some(caps) = ctx.re.script_assign.captures(line) {
        let raw = if script_parent == "." {
            caps[2].to_owned()
        } else {
            format!("{script_parent}/{}", &caps[2])
        };
        let _ = vars.insert(caps[1].to_owned(), normalize_rel(&raw, ctx.repo_root));
        return true;
    }
    false
}

/// Handle one `contains "$VAR" <literal>` assertion line.
fn handle_contains(
    line: &str,
    caps: &Captures<'_>,
    lctx: LineCtx,
    vars: &HashMap<String, String>,
    ctx: &ScanCtx,
    scan: &mut ContainsPinsScan,
) {
    let var = &caps[1];
    let end = caps.get(0).map_or(0, |matched| matched.end());
    let target_rel = vars.get(var).map(String::as_str);
    let (literal, canonical) = scan_shell_quoted_literal(&line[end..]);
    if !canonical {
        if assertion_in_scope(lctx.script_rel, target_rel, ctx.changed) {
            scan.stderr_lines.push(format!(
                "SKIPPED_NON_CANONICAL: {}:{}: assertion shape not in v1 grammar",
                lctx.script_rel, lctx.line_no
            ));
        }
        return;
    }
    let Some(target_rel) = target_rel else {
        if assertion_in_scope(lctx.script_rel, None, ctx.changed) {
            scan.stderr_lines.push(unresolved_line(lctx, var));
        }
        return;
    };
    if !assertion_in_scope(lctx.script_rel, Some(target_rel), ctx.changed) {
        return;
    }
    let literal = literal.unwrap_or_default();
    resolve_and_check(&literal, target_rel, var, lctx, ctx, scan);
}

/// Resolve the target file and record a defect when the literal is absent.
fn resolve_and_check(
    literal: &str,
    target_rel: &str,
    var: &str,
    lctx: LineCtx,
    ctx: &ScanCtx,
    scan: &mut ContainsPinsScan,
) {
    let Ok(canon) = fs::canonicalize(ctx.repo_root.join(target_rel)) else {
        scan.stderr_lines.push(unresolved_line(lctx, var));
        return;
    };
    if !canon.starts_with(ctx.repo_root_canon) || !canon.is_file() {
        scan.stderr_lines.push(unresolved_line(lctx, var));
        return;
    }
    let Some(content) = read_lossy(&canon) else {
        scan.stderr_lines.push(unresolved_line(lctx, var));
        return;
    };
    if !content.contains(literal) {
        scan.stdout_lines.push(format!(
            "DEFECT: {}:{}: literal '{literal}' not found in {target_rel}",
            lctx.script_rel, lctx.line_no
        ));
        scan.defects += 1;
    }
}

fn unresolved_line(lctx: LineCtx, var: &str) -> String {
    format!(
        "UNRESOLVED_VAR: {}:{}: could not resolve ${var}",
        lctx.script_rel, lctx.line_no
    )
}

/// Whether an assertion is reported under the changed-scope filter.
fn assertion_in_scope(
    script: &str,
    target: Option<&str>,
    changed: Option<&HashSet<String>>,
) -> bool {
    let Some(set) = changed else {
        return true;
    };
    if set.contains(script) {
        return true;
    }
    matches!(target, Some(t) if !t.is_empty() && set.contains(t))
}

/// Parse a single- or double-quoted shell literal, matching the v1 grammar.
///
/// Returns `(literal, canonical)`. `canonical` is false for any shape outside
/// the grammar, including a bare `$` inside a double-quoted string or a closing
/// quote not followed by whitespace.
fn scan_shell_quoted_literal(rest: &str) -> (Option<String>, bool) {
    let chars: Vec<char> = rest.chars().collect();
    let Some(&quote) = chars.first() else {
        return (None, false);
    };
    if quote == '\'' {
        return scan_single_quoted(&chars);
    }
    if quote != '"' {
        return (None, false);
    }
    scan_double_quoted(&chars)
}

fn scan_single_quoted(chars: &[char]) -> (Option<String>, bool) {
    let Some(rel) = chars[1..].iter().position(|&ch| ch == '\'') else {
        return (None, false);
    };
    let end = rel + 1;
    let literal: String = chars[1..end].iter().collect();
    if chars.get(end + 1).copied().is_some_and(py_isspace) {
        (Some(literal), true)
    } else {
        (None, false)
    }
}

fn scan_double_quoted(chars: &[char]) -> (Option<String>, bool) {
    let mut body = String::new();
    let mut escaped = false;
    let mut bare_dollar = false;
    for (index, &ch) in chars.iter().enumerate().skip(1) {
        if escaped {
            if !matches!(ch, '$' | '"' | '\\') {
                body.push('\\');
            }
            body.push(ch);
            escaped = false;
        } else if ch == '\\' {
            escaped = true;
        } else if ch == '$' {
            bare_dollar = true;
            body.push(ch);
        } else if ch == '"' {
            let suffix_space = chars.get(index + 1).copied().is_some_and(py_isspace);
            if bare_dollar || !suffix_space {
                return (None, false);
            }
            return (Some(body), true);
        } else {
            body.push(ch);
        }
    }
    (None, false)
}

/// Read a file with lossy UTF-8 decoding (Python `read_text(errors="replace")`).
fn read_lossy(path: &Path) -> Option<String> {
    fs::read(path)
        .ok()
        .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
}

/// Whitespace test matching Python `str.isspace()` for a single character.
const fn py_isspace(ch: char) -> bool {
    ch.is_whitespace() || matches!(ch, '\u{1c}' | '\u{1d}' | '\u{1e}' | '\u{1f}')
}

/// Trim leading/trailing whitespace matching Python `str.strip()`.
fn py_strip(text: &str) -> &str {
    text.trim_matches(py_isspace)
}

/// Split on the Python `str.splitlines()` universal-newline set, ends removed.
fn py_splitlines(text: &str) -> Vec<&str> {
    let mut result: Vec<&str> = Vec::new();
    let mut line_start = 0usize;
    let mut iter = text.char_indices().peekable();
    while let Some((idx, ch)) = iter.next() {
        if !is_line_break(ch) {
            continue;
        }
        result.push(&text[line_start..idx]);
        line_start = if ch == '\r'
            && let Some(&(nidx, '\n')) = iter.peek()
        {
            let _ = iter.next();
            nidx + '\n'.len_utf8()
        } else {
            idx + ch.len_utf8()
        };
    }
    if line_start < text.len() {
        result.push(&text[line_start..]);
    }
    result
}

const fn is_line_break(ch: char) -> bool {
    matches!(
        ch,
        '\n' | '\r'
            | '\u{0b}'
            | '\u{0c}'
            | '\u{1c}'
            | '\u{1d}'
            | '\u{1e}'
            | '\u{85}'
            | '\u{2028}'
            | '\u{2029}'
    )
}

#[cfg(test)]
mod tests {
    use super::{normalize_rel, py_splitlines, scan_contains_pins};
    use std::collections::HashSet;
    use std::fs;
    use std::path::{Path, PathBuf};
    use tempfile::TempDir;

    fn repo() -> (TempDir, PathBuf) {
        let dir = TempDir::new().expect("tempdir");
        let root = fs::canonicalize(dir.path()).expect("canonicalize");
        fs::create_dir_all(root.join("scripts")).expect("scripts dir");
        (dir, root)
    }

    fn write(root: &Path, rel: &str, contents: &str) {
        let path = root.join(rel);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("parent");
        }
        fs::write(path, contents).expect("write");
    }

    #[test]
    fn present_literal_reports_no_defect() {
        let (_guard, root) = repo();
        write(&root, "target.txt", "alpha hello beta");
        write(
            &root,
            "scripts/test-a.sh",
            "FILE=\"$REPO_ROOT/target.txt\"\ncontains \"$FILE\" \"hello\" desc\n",
        );
        let scan = scan_contains_pins(&root, None);
        assert_eq!(scan.defects, 0);
        assert!(scan.stdout_lines.is_empty());
        assert!(scan.stderr_lines.is_empty());
    }

    #[test]
    fn absent_literal_reports_one_defect() {
        let (_guard, root) = repo();
        write(&root, "target.txt", "alpha beta");
        write(
            &root,
            "scripts/test-b.sh",
            "FILE=\"$REPO_ROOT/target.txt\"\ncontains \"$FILE\" \"goodbye\" desc\n",
        );
        let scan = scan_contains_pins(&root, None);
        assert_eq!(scan.defects, 1);
        assert_eq!(
            scan.stdout_lines,
            vec![
                "DEFECT: scripts/test-b.sh:2: literal 'goodbye' not found in target.txt".to_owned()
            ]
        );
    }

    #[test]
    fn single_quoted_present_literal_reports_no_defect() {
        let (_guard, root) = repo();
        write(&root, "target.txt", "has hello here");
        write(
            &root,
            "scripts/test-c.sh",
            "FILE=\"$REPO_ROOT/target.txt\"\ncontains \"$FILE\" 'hello' desc\n",
        );
        let scan = scan_contains_pins(&root, None);
        assert_eq!(scan.defects, 0);
    }

    #[test]
    fn non_canonical_shape_is_skipped() {
        let (_guard, root) = repo();
        write(&root, "target.txt", "x");
        write(
            &root,
            "scripts/test-d.sh",
            "FILE=\"$REPO_ROOT/target.txt\"\ncontains \"$FILE\" $UNQUOTED desc\n",
        );
        let scan = scan_contains_pins(&root, None);
        assert_eq!(scan.defects, 0);
        assert_eq!(
            scan.stderr_lines,
            vec![
                "SKIPPED_NON_CANONICAL: scripts/test-d.sh:2: assertion shape not in v1 grammar"
                    .to_owned()
            ]
        );
    }

    #[test]
    fn unresolved_var_is_reported() {
        let (_guard, root) = repo();
        write(
            &root,
            "scripts/test-e.sh",
            "contains \"$UNKNOWN\" \"literal\" desc\n",
        );
        let scan = scan_contains_pins(&root, None);
        assert_eq!(scan.defects, 0);
        assert_eq!(
            scan.stderr_lines,
            vec!["UNRESOLVED_VAR: scripts/test-e.sh:1: could not resolve $UNKNOWN".to_owned()]
        );
    }

    #[test]
    fn changed_scope_excludes_out_of_scope_assertion() {
        let (_guard, root) = repo();
        write(&root, "target.txt", "alpha beta");
        write(
            &root,
            "scripts/test-f.sh",
            "FILE=\"$REPO_ROOT/target.txt\"\ncontains \"$FILE\" \"goodbye\" desc\n",
        );
        let mut changed: HashSet<String> = HashSet::new();
        let _ = changed.insert("other/file.txt".to_owned());
        let scan = scan_contains_pins(&root, Some(&changed));
        assert_eq!(scan.defects, 0);
        assert!(scan.stdout_lines.is_empty());
        assert!(scan.stderr_lines.is_empty());
    }

    #[test]
    fn changed_scope_includes_target_in_set() {
        let (_guard, root) = repo();
        write(&root, "target.txt", "alpha beta");
        write(
            &root,
            "scripts/test-g.sh",
            "FILE=\"$REPO_ROOT/target.txt\"\ncontains \"$FILE\" \"goodbye\" desc\n",
        );
        let mut changed: HashSet<String> = HashSet::new();
        let _ = changed.insert("target.txt".to_owned());
        let scan = scan_contains_pins(&root, Some(&changed));
        assert_eq!(scan.defects, 1);
    }

    #[test]
    fn script_dir_assignment_resolves_relative_to_parent() {
        let (_guard, root) = repo();
        write(&root, "skills/demo/target.txt", "keeps token");
        write(
            &root,
            "skills/demo/scripts/test-h.sh",
            "FILE=\"$SCRIPT_DIR/../target.txt\"\ncontains \"$FILE\" \"missing\" desc\n",
        );
        let scan = scan_contains_pins(&root, None);
        assert_eq!(scan.defects, 1);
        assert_eq!(
            scan.stdout_lines,
            vec![
                "DEFECT: skills/demo/scripts/test-h.sh:2: literal 'missing' not found in skills/demo/target.txt"
                    .to_owned()
            ]
        );
    }

    #[test]
    fn normalize_rel_strips_root_and_resolves_dotdot() {
        let root = Path::new("/repo/root");
        assert_eq!(normalize_rel("/repo/root/a/b.txt", root), "a/b.txt");
        assert_eq!(normalize_rel("./a/./b.txt", root), "a/b.txt");
        assert_eq!(normalize_rel("a/b/../c.txt", root), "a/c.txt");
        assert_eq!(normalize_rel("../escape.txt", root), "../escape.txt");
    }

    #[test]
    fn py_splitlines_matches_python_semantics() {
        assert!(py_splitlines("").is_empty());
        assert_eq!(py_splitlines("abc"), vec!["abc"]);
        assert_eq!(py_splitlines("abc\n"), vec!["abc"]);
        assert_eq!(py_splitlines("abc\n\n"), vec!["abc", ""]);
        assert_eq!(py_splitlines("abc\r\ndef"), vec!["abc", "def"]);
    }
}
