//! Byte-for-byte port of the Python `checks` failure-digest builder.
//!
//! Turns an already-redacted relevant-checks log into the bounded
//! `CHECKS_FAILURE_DIGEST v1` string consumed by the ci-fixer subagent. The
//! Ported from the retired Python `_build_checks_failure_digest` implementation;
//! this module is now the source of truth.

use std::collections::HashMap;
use std::sync::LazyLock;

use regex::Regex;

const CHECKS_FAILURE_DIGEST_MAX_BYTES: usize = 8192;
const CHECKS_FAILURE_DIGEST_ERROR_MAX_BYTES: usize = 512;

static MARKER_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"ERROR:|Error:|FAILED|Failed|Traceback|AssertionError|DEFECT:")
        .expect("marker regex should compile")
});
static LINT_ROW_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[^\s:][^:]*:\d+(?::\d+)?(?::)?\s+[A-Z][A-Z0-9]*\d+[A-Z0-9]*(?:\s|$)")
        .expect("lint-row regex should compile")
});
static MAKE_ERROR_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^make(?:\[\d+\])?: \*\*\* .*\bError \d+\b")
        .expect("make-error regex should compile")
});
// Python's `_CHECKS_FAILURE_DIGEST_LOCATION_RE` uses a `(?<![\w./-])` lookbehind
// that the `regex` crate cannot express; the lookbehind is emulated in
// `search_location` by rejecting candidate start positions whose preceding char
// is in `[\w./-]`. This anchored form is the pattern minus that lookbehind.
static LOCATION_ANCHORED_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^((?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+):(\d+)(?::\d+)?\b")
        .expect("location regex should compile")
});
static PRECOMMIT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(.+?)(?:\.{2,}|\s{2,})Failed\b").expect("precommit regex should compile")
});
static DIRECT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^=== Running direct relevant make target\(s\): (.+) ===$")
        .expect("direct-target regex should compile")
});

#[derive(Clone)]
struct Record {
    check: String,
    failure_count: u64,
    first_location: String,
    first_error: String,
}

impl Record {
    fn new(check: &str) -> Self {
        Self {
            check: check.to_owned(),
            failure_count: 0,
            first_location: "unknown".to_owned(),
            first_error: "unknown".to_owned(),
        }
    }
}

/// Insertion-ordered `check -> Record` map, mirroring Python dict ordering.
#[derive(Default)]
struct Records {
    order: Vec<String>,
    map: HashMap<String, Record>,
}

impl Records {
    fn contains(&self, check: &str) -> bool {
        self.map.contains_key(check)
    }

    const fn is_empty(&self) -> bool {
        self.order.is_empty()
    }

    fn get_or_create(&mut self, check: &str) -> &mut Record {
        if !self.map.contains_key(check) {
            self.order.push(check.to_owned());
            let _ = self.map.insert(check.to_owned(), Record::new(check));
        }
        self.map
            .get_mut(check)
            .expect("record inserted above must exist")
    }

    fn ordered(&self) -> impl Iterator<Item = &Record> {
        self.order
            .iter()
            .map(move |key| self.map.get(key).expect("ordered key must exist"))
    }
}

#[derive(Default)]
struct ParseState {
    records: Records,
    current_check: String,
    fallback_line: String,
    pending_location: Option<String>,
    pending_error_line: String,
}

/// Whether `c` is in the lookbehind class `[\w./-]` guarding a location match.
fn is_lookbehind_class(c: char) -> bool {
    c.is_alphanumeric() || c == '_' || c == '.' || c == '/' || c == '-'
}

/// Match Python `str.isspace()` for the strip set (Unicode whitespace plus the
/// C0 separators `\x1c..=\x1f` that Rust's `char::is_whitespace` omits).
const fn is_py_space(c: char) -> bool {
    c.is_whitespace() || matches!(c, '\u{1c}'..='\u{1f}')
}

fn py_strip(text: &str) -> &str {
    text.trim_matches(is_py_space)
}

/// Largest UTF-8-boundary prefix of `text` fitting in `max_bytes`, matching
/// Python `text.encode()[:max_bytes].decode("utf-8", errors="ignore")`.
fn utf8_prefix(text: &str, max_bytes: usize) -> &str {
    if text.len() <= max_bytes {
        return text;
    }
    let mut boundary = max_bytes;
    while boundary > 0 && !text.is_char_boundary(boundary) {
        boundary -= 1;
    }
    &text[..boundary]
}

fn digest_line(text: &str) -> String {
    let stripped = py_strip(text).replace('\r', "");
    let prefixed = utf8_prefix(&stripped, CHECKS_FAILURE_DIGEST_ERROR_MAX_BYTES);
    if prefixed.is_empty() {
        "unknown".to_owned()
    } else {
        prefixed.to_owned()
    }
}

/// Emulated `re.search` for the location pattern with its negative lookbehind.
fn search_location(line: &str) -> Option<(String, String)> {
    let mut prev: Option<char> = None;
    for (index, ch) in line.char_indices() {
        let ok_start = prev.is_none_or(|p| !is_lookbehind_class(p));
        if ok_start && let Some(caps) = LOCATION_ANCHORED_RE.captures(&line[index..]) {
            let path = caps.get(1).map_or("", |m| m.as_str()).to_owned();
            let lineno = caps.get(2).map_or("", |m| m.as_str()).to_owned();
            return Some((path, lineno));
        }
        prev = Some(ch);
    }
    None
}

fn location_string(line: &str) -> Option<String> {
    search_location(line).map(|(path, lineno)| format!("{path}:{lineno}"))
}

fn direct_digest_check(header_targets: &str) -> String {
    let targets: Vec<&str> = header_targets.split_whitespace().collect();
    if targets.len() == 1 {
        targets[0].to_owned()
    } else {
        "direct-make".to_owned()
    }
}

fn precommit_digest_check(line: &str) -> Option<String> {
    let caps = PRECOMMIT_RE.captures(line)?;
    let stripped = caps
        .get(1)
        .map_or("", |m| m.as_str())
        .trim_matches(|c| c == ' ' || c == '.');
    if stripped.is_empty() {
        None
    } else {
        Some(stripped.to_owned())
    }
}

fn digest_check_for_line(line: &str, current_check: &str) -> String {
    if line.starts_with("DEFECT:") {
        return "contains-pins".to_owned();
    }
    if let Some(precommit_check) = precommit_digest_check(line) {
        return precommit_check;
    }
    if line.contains("pre-commit not found") {
        return "pre-commit".to_owned();
    }
    current_check.to_owned()
}

/// Returns `(next_check, is_header)`.
fn digest_header_context(line: &str, current_check: &str) -> (String, bool) {
    if line.contains("=== Running pre-commit") {
        return ("pre-commit".to_owned(), true);
    }
    if let Some(caps) = DIRECT_RE.captures(line) {
        return (
            direct_digest_check(caps.get(1).map_or("", |m| m.as_str())),
            true,
        );
    }
    if line == "=== Running agent-lint ===" {
        return ("agent-lint".to_owned(), true);
    }
    (current_check.to_owned(), false)
}

fn is_checks_failure_error_evidence(line: &str) -> bool {
    LINT_ROW_RE.is_match(line) || MAKE_ERROR_RE.is_match(line)
}

fn apply_digest_location(record: &mut Record, line: &str, pending_location: Option<&str>) {
    if record.first_location != "unknown" {
        return;
    }
    if let Some(location) = location_string(line) {
        record.first_location = location;
    } else if let Some(pending) = pending_location {
        pending.clone_into(&mut record.first_location);
    }
}

struct LineContext<'a> {
    line: &'a str,
    has_marker: bool,
    pending_location: Option<String>,
    is_precommit_banner: bool,
    is_error_evidence: bool,
}

fn update_digest_record(records: &mut Records, check: &str, context: &LineContext<'_>) {
    let record = records.get_or_create(check);
    apply_digest_location(record, context.line, context.pending_location.as_deref());
    if context.is_precommit_banner {
        record.failure_count += 1;
        return;
    }
    if !context.has_marker {
        let has_location = location_string(context.line).is_some();
        if (context.is_error_evidence || has_location) && record.first_error == "unknown" {
            record.first_error = digest_line(context.line);
        }
        return;
    }
    record.failure_count += 1;
    if record.first_error == "unknown" {
        record.first_error = digest_line(context.line);
    }
}

fn flush_pending_digest_record(state: &mut ParseState, check: &str) {
    if state.records.contains(check) || state.pending_error_line.is_empty() {
        return;
    }
    let pending_location = state.pending_location.clone();
    let error = digest_line(&state.pending_error_line);
    let record = state.records.get_or_create(check);
    if let Some(location) = pending_location {
        record.first_location = location;
    }
    record.first_error = error;
}

fn flush_and_reset_pending(state: &mut ParseState) {
    let check = state.current_check.clone();
    flush_pending_digest_record(state, &check);
    state.pending_location = None;
    state.pending_error_line.clear();
}

fn handle_digest_header_line(state: &mut ParseState, line: &str) -> bool {
    let (next_check, is_header) = digest_header_context(line, &state.current_check);
    if !is_header {
        state.current_check = next_check;
        return false;
    }
    flush_and_reset_pending(state);
    state.current_check = next_check;
    true
}

fn handle_precommit_digest_line(state: &mut ParseState, line: &str) -> bool {
    let Some(precommit_check) = precommit_digest_check(line) else {
        return false;
    };
    if precommit_check != state.current_check {
        flush_and_reset_pending(state);
    }
    state.current_check.clone_from(&precommit_check);
    let context = LineContext {
        line,
        has_marker: false,
        pending_location: None,
        is_precommit_banner: true,
        is_error_evidence: false,
    };
    update_digest_record(&mut state.records, &precommit_check, &context);
    true
}

fn handle_defect_digest_context(state: &mut ParseState, line: &str) {
    if !line.starts_with("DEFECT:") {
        return;
    }
    if state.current_check != "contains-pins" {
        flush_and_reset_pending(state);
    }
    "contains-pins".clone_into(&mut state.current_check);
}

fn capture_pending_digest_location(state: &mut ParseState, line: &str) {
    let Some(location) = location_string(line) else {
        return;
    };
    state.pending_location = Some(location);
    if state.pending_error_line.is_empty() {
        line.clone_into(&mut state.pending_error_line);
    }
}

fn record_digest_marker_or_evidence(
    state: &mut ParseState,
    line: &str,
    check: &str,
    has_marker: bool,
) {
    if has_marker {
        if state.fallback_line.is_empty() {
            line.clone_into(&mut state.fallback_line);
        }
        let context = LineContext {
            line,
            has_marker: true,
            pending_location: state.pending_location.clone(),
            is_precommit_banner: false,
            is_error_evidence: false,
        };
        update_digest_record(&mut state.records, check, &context);
        state.pending_location = None;
        state.pending_error_line.clear();
        return;
    }
    if is_checks_failure_error_evidence(line) {
        if state.fallback_line.is_empty() {
            line.clone_into(&mut state.fallback_line);
        }
        let creates_record = !state.records.contains(check);
        let context = LineContext {
            line,
            has_marker: false,
            pending_location: state.pending_location.clone(),
            is_precommit_banner: false,
            is_error_evidence: true,
        };
        update_digest_record(&mut state.records, check, &context);
        if creates_record {
            state.records.get_or_create(check).failure_count += 1;
        }
        return;
    }
    if state.records.contains(check) {
        let context = LineContext {
            line,
            has_marker: false,
            pending_location: state.pending_location.clone(),
            is_precommit_banner: false,
            is_error_evidence: false,
        };
        update_digest_record(&mut state.records, check, &context);
    }
}

fn parse_checks_failure_records(redacted_log_text: &str) -> Records {
    let mut state = ParseState {
        current_check: "unknown".to_owned(),
        ..Default::default()
    };
    for line in py_splitlines(redacted_log_text) {
        if handle_digest_header_line(&mut state, line) {
            continue;
        }
        if handle_precommit_digest_line(&mut state, line) {
            continue;
        }
        handle_defect_digest_context(&mut state, line);
        capture_pending_digest_location(&mut state, line);
        let has_marker = MARKER_RE.is_match(line);
        let check = digest_check_for_line(line, &state.current_check);
        record_digest_marker_or_evidence(&mut state, line, &check, has_marker);
    }
    flush_and_reset_pending(&mut state);
    if state.records.is_empty() {
        let fallback = state.fallback_line.clone();
        let record = state.records.get_or_create("unknown");
        record.first_error = if fallback.is_empty() {
            "unknown".to_owned()
        } else {
            digest_line(&fallback)
        };
    }
    state.records
}

fn digest_record_group(record: &Record) -> String {
    format!(
        "check={}\nfailure_count={}\nfirst_location={}\nfirst_error={}\n",
        record.check, record.failure_count, record.first_location, record.first_error
    )
}

fn checks_failure_digest_header(site: &str, truncated: bool) -> String {
    format!(
        "CHECKS_FAILURE_DIGEST v1\nsite={}\ndigest_truncated={}\n",
        site,
        if truncated { "true" } else { "false" }
    )
}

fn assemble_checks_failure_digest(records: &Records, site: &str) -> String {
    let body_groups: Vec<String> = records.ordered().map(digest_record_group).collect();
    let mut selected: Vec<String> = Vec::new();
    let mut truncated = false;
    let header = checks_failure_digest_header(site, false);
    for group in &body_groups {
        let candidate = format!("{header}{}{group}", selected.concat());
        if candidate.len() > CHECKS_FAILURE_DIGEST_MAX_BYTES {
            truncated = true;
            break;
        }
        selected.push(group.clone());
    }
    let header = checks_failure_digest_header(site, truncated);
    let digest = format!("{header}{}", selected.concat());
    if digest.len() <= CHECKS_FAILURE_DIGEST_MAX_BYTES {
        digest
    } else {
        utf8_prefix(&digest, CHECKS_FAILURE_DIGEST_MAX_BYTES).to_owned()
    }
}

/// Build the bounded `CHECKS_FAILURE_DIGEST v1` string for an already-redacted log.
#[must_use]
pub fn build_checks_failure_digest(redacted_log_text: &str, site: &str) -> String {
    let records = parse_checks_failure_records(redacted_log_text);
    assemble_checks_failure_digest(&records, site)
}

/// Split like Python `str.splitlines()`: on every Python line boundary, with no
/// trailing empty element when the text ends on a boundary.
fn py_splitlines(text: &str) -> Vec<&str> {
    let mut lines: Vec<&str> = Vec::new();
    let bytes_len = text.len();
    let mut start = 0usize;
    let chars: Vec<(usize, char)> = text.char_indices().collect();
    let mut i = 0usize;
    while i < chars.len() {
        let (byte_index, ch) = chars[i];
        if is_line_boundary(ch) {
            lines.push(&text[start..byte_index]);
            // Treat "\r\n" as a single boundary.
            let mut next = byte_index + ch.len_utf8();
            if ch == '\r' && i + 1 < chars.len() && chars[i + 1].1 == '\n' {
                next += '\n'.len_utf8();
                i += 1;
            }
            start = next;
        }
        i += 1;
    }
    if start < bytes_len {
        lines.push(&text[start..]);
    }
    lines
}

const fn is_line_boundary(c: char) -> bool {
    matches!(
        c,
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
    use super::*;

    #[test]
    fn empty_input_falls_back_to_unknown() {
        let digest = build_checks_failure_digest("", "step3");
        assert_eq!(
            digest,
            "CHECKS_FAILURE_DIGEST v1\nsite=step3\ndigest_truncated=false\n\
             check=unknown\nfailure_count=0\nfirst_location=unknown\nfirst_error=unknown\n"
        );
    }

    #[test]
    fn precommit_banner_failure() {
        let line =
            "ruff.....................................................................Failed";
        let digest = build_checks_failure_digest(line, "step6");
        assert_eq!(
            digest,
            "CHECKS_FAILURE_DIGEST v1\nsite=step6\ndigest_truncated=false\n\
             check=ruff\nfailure_count=1\nfirst_location=unknown\nfirst_error=unknown\n"
        );
    }

    #[test]
    fn agent_lint_lint_row() {
        let log = "=== Running agent-lint ===\npython/foo.py:12:5 E501 line too long\n";
        let digest = build_checks_failure_digest(log, "step3");
        assert_eq!(
            digest,
            "CHECKS_FAILURE_DIGEST v1\nsite=step3\ndigest_truncated=false\n\
             check=agent-lint\nfailure_count=1\nfirst_location=python/foo.py:12\n\
             first_error=python/foo.py:12:5 E501 line too long\n"
        );
    }

    #[test]
    fn defect_contains_pins() {
        let line = "DEFECT: scripts/test-foo.sh:10: literal 'x' not found in docs/y.md";
        let digest = build_checks_failure_digest(line, "step3");
        assert_eq!(
            digest,
            "CHECKS_FAILURE_DIGEST v1\nsite=step3\ndigest_truncated=false\n\
             check=contains-pins\nfailure_count=1\nfirst_location=scripts/test-foo.sh:10\n\
             first_error=DEFECT: scripts/test-foo.sh:10: literal 'x' not found in docs/y.md\n"
        );
    }

    #[test]
    fn make_error_under_unknown() {
        let line = "make: *** [Makefile:5: build] Error 2";
        let digest = build_checks_failure_digest(line, "step3");
        assert_eq!(
            digest,
            "CHECKS_FAILURE_DIGEST v1\nsite=step3\ndigest_truncated=false\n\
             check=unknown\nfailure_count=1\nfirst_location=Makefile:5\n\
             first_error=make: *** [Makefile:5: build] Error 2\n"
        );
    }

    #[test]
    fn multiple_checks_preserve_insertion_order() {
        let log = "ruff...................Failed\n\
                   === Running agent-lint ===\n\
                   python/foo.py:12:5 E501 line too long\n";
        let digest = build_checks_failure_digest(log, "step3");
        let ruff_at = digest.find("check=ruff").expect("ruff group present");
        let agent_at = digest
            .find("check=agent-lint")
            .expect("agent-lint group present");
        assert!(ruff_at < agent_at, "ruff must precede agent-lint: {digest}");
    }

    #[test]
    fn truncation_sets_flag_and_bounds_bytes() {
        use std::fmt::Write as _;
        let mut log = String::new();
        for n in 0..600 {
            let _ = writeln!(
                log,
                "hook{n:04}...................................................Failed"
            );
        }
        let digest = build_checks_failure_digest(&log, "step3");
        assert!(digest.len() <= CHECKS_FAILURE_DIGEST_MAX_BYTES);
        assert!(
            digest.starts_with("CHECKS_FAILURE_DIGEST v1\nsite=step3\ndigest_truncated=true\n"),
            "expected truncated header, got: {}",
            &digest[..digest.len().min(80)]
        );
    }

    #[test]
    fn location_lookbehind_rejects_mid_token() {
        // A path embedded after a word char must not match at the interior.
        assert_eq!(
            search_location("xfoo/bar.py:3"),
            Some(("xfoo/bar.py".to_owned(), "3".to_owned()))
        );
        // Leading separator lets the inner path match cleanly.
        assert_eq!(
            search_location("see foo/bar.py:3 now"),
            Some(("foo/bar.py".to_owned(), "3".to_owned()))
        );
        assert_eq!(search_location("no location here"), None);
    }

    #[test]
    fn utf8_prefix_drops_partial_char() {
        // '€' is 3 bytes; a 2-byte budget over "a€" keeps only "a".
        assert_eq!(utf8_prefix("a\u{20ac}", 2), "a");
        assert_eq!(utf8_prefix("abc", 10), "abc");
    }
}
