//! Whether a run actually disposed of the out-of-scope work it accepted.
//!
//! Ports Python `larch.issue.oos_disposition` plus the counting half of the
//! `larch.issue.file_oos` gate. A run may accept an OOS observation and then
//! finish without doing anything about it; the disposition model exists to
//! make that visible. Four counters answer the question: how many non-security
//! OOS records the run accepted, how many issues it filed, how many items it
//! triaged inline in its own commits, and how many it explicitly rejected.
//!
//! Every counter is fail-closed. An unreadable file counts zero, which can
//! only make the gate stricter, and an unparseable batch is reported as a
//! parse error rather than silently reducing the rejected count to zero.
//!
//! Python carried two rejected-marker readers that disagreed, and #8178
//! reconciled them here into one. The reader now folds case in the outer
//! presence check, because the per-line scan below it always folded case and a
//! gate that disagrees with its own scan returns zero for a body it can read.
//! The presence check remains a narrowing fast path: it looks for the literal
//! section text, so a heading spaced more widely than the scan requires is
//! skipped. That direction only under-counts rejections, which blocks the gate
//! rather than clearing it.
//! It ends the rejected section on any line opening with exactly two `#`,
//! rather than only on `##` followed by whitespace, because a bare `##Accepted`
//! is a section boundary in every artifact that writes one and reading past it
//! would count an accepted item as rejected — the one direction that lets an
//! undisposed run look disposed.

use crate::issue::oos_record::count_non_security_blocks;
use crate::text::{python_str, split_text_lines, trim_python_whitespace, universal_newlines};
use regex::Regex;
use serde_json::Value;
use std::collections::BTreeSet;
use std::fs;
use std::path::Path;
use std::sync::LazyLock;

/// The accepted-OOS artifacts a run may write, in the order the audit reads.
pub const ACCEPTED_OOS_FILENAMES: [&str; 3] = [
    "oos-accepted-main-agent.md",
    "oos-accepted-design.md",
    "oos-accepted-review.md",
];
/// The run-log files an inline-triage scan reads.
pub const INLINE_TRIAGE_SOURCES: [&str; 2] =
    ["codex-commit-message.txt", "session-transcript.jsonl"];
/// The marker a commit writes when it triaged an OOS item inline.
pub const INLINE_TRIAGE_MARKER: &str = "Inline-triage rule";

static REJECTED_MARKER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"OOS_[0-9]+").expect("rejected marker expression"));
static REJECTED_SECTION_END_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^##[^#]|^##$").expect("rejected section end expression"));
static STRICT_FILED_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?m)^[ \t]*-[ \t]+\*\*Filed[ \t]URL\*\*[ \t]*:[ \t]+(https://[^\s\x1c-\x1f]+/issues/[0-9]+)(?:[ \t].*)?$",
    )
    .expect("strict filed url expression")
});
static REJECTED_SECTION_START_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^##[\s\x1c-\x1f]*rejected").expect("rejected section start expression")
});

/// What one run directory recorded about its OOS disposition.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct OosDispositionCounts {
    /// Accepted OOS records that are not security tagged.
    pub non_security_oos_blocks: usize,
    /// Distinct GitHub issue URLs the run recorded as filed.
    pub issue_urls: usize,
    /// Distinct inline-triage lines the run recorded.
    pub inline_triage_hits: usize,
    /// Distinct `OOS_<n>` markers an issue body explicitly rejected.
    pub rejected_oos_markers: usize,
    /// Whether the filing batch could not be read as newline-delimited JSON.
    pub ndjson_parse_error: bool,
}

/// The terminal state one disposition check reaches.
///
/// The set is closed on purpose. A caller that cannot name its state has not
/// checked, and "not checked" must never read as "cleared".
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DispositionState {
    /// Every accepted OOS record was filed, triaged, or explicitly rejected.
    Cleared,
    /// Accepted OOS records remain undisposed; filing must not proceed.
    Blocked,
    /// The public side cleared, but a private security sidecar still needs one.
    SecuritySidecarPending,
}

impl DispositionState {
    /// Render the wire token for this state.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Cleared => "cleared",
            Self::Blocked => "blocked",
            Self::SecuritySidecarPending => "security-sidecar-pending",
        }
    }

    /// Return the process exit code this state reports.
    #[must_use]
    pub const fn exit_code(self) -> i32 {
        match self {
            Self::Cleared => 0,
            Self::Blocked => 1,
            Self::SecuritySidecarPending => 3,
        }
    }

    /// Read a state back from its wire token, refusing anything else.
    ///
    /// `skipped` is refused by name: earlier wire formats used it to mean the
    /// check never ran, and admitting it here would let a run that skipped
    /// disposition resume as if it had passed.
    #[must_use]
    pub fn from_wire(value: &str) -> Option<Self> {
        match trim_python_whitespace(value) {
            "cleared" => Some(Self::Cleared),
            "blocked" => Some(Self::Blocked),
            "security-sidecar-pending" => Some(Self::SecuritySidecarPending),
            _unknown => None,
        }
    }
}

/// The four counters the disposition gate compares.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct DispositionCounters {
    /// Accepted OOS records that are not security tagged.
    pub non_security: usize,
    /// Distinct filed GitHub issue URLs.
    pub filed_urls: usize,
    /// Distinct inline-triage lines in the commit range.
    pub inline_triage: usize,
    /// Distinct explicitly rejected `OOS_<n>` markers.
    pub rejected_markers: usize,
}

impl DispositionCounters {
    /// Report whether these counters clear the gate.
    ///
    /// Nothing accepted clears trivially. Otherwise one filed URL clears the
    /// run, and inline triage or explicit rejection clears it only by covering
    /// every accepted record.
    #[must_use]
    pub const fn cleared(&self) -> bool {
        self.non_security == 0
            || self.filed_urls > 0
            || self.inline_triage >= self.non_security
            || self.rejected_markers >= self.non_security
    }

    /// Classify these counters into a terminal state.
    #[must_use]
    pub const fn state(&self, security_sidecar_present: bool) -> DispositionState {
        if !self.cleared() {
            DispositionState::Blocked
        } else if security_sidecar_present {
            DispositionState::SecuritySidecarPending
        } else {
            DispositionState::Cleared
        }
    }

    /// Render the single diagnostic line a blocked gate reports.
    #[must_use]
    pub fn failure_line(&self, commit_range: &str) -> String {
        format!(
            "oos-disposition-gate: FAIL non_security_oos={} filed_urls={} inline_triage_lines={} rejected_oos_markers={} (commit-range {commit_range})",
            self.non_security, self.filed_urls, self.inline_triage, self.rejected_markers,
        )
    }
}

/// Build the GitHub issue-URL pattern for one `GH_HOST` setting.
///
/// An enterprise host is accepted alongside `github.com`, never instead of it:
/// a run may record URLs from both while a repository is being moved.
///
/// # Panics
///
/// Never in practice: the host is regex-escaped before it is interpolated, so
/// the composed expression always compiles.
#[must_use]
pub fn issue_url_pattern(gh_host: &str) -> Regex {
    let host = if gh_host.is_empty() || gh_host == "github.com" {
        r"github\.com".to_owned()
    } else {
        format!(r"(?:{}|github\.com)", regex::escape(gh_host))
    };
    Regex::new(&format!(
        r"https://{host}/[^\s\x1c-\x1f/]+/[^\s\x1c-\x1f/]+/issues/[0-9]+"
    ))
    .expect("issue URL expression")
}

/// Read a regular file the way Python's `Path.read_text` did.
///
/// Undecodable bytes are replaced rather than failing the read, and line
/// endings are translated, because every counter here ports a reader that
/// opened in universal-newline mode. Public because the OOS verbs read the same
/// artifacts and must not define a second reader that could drift from this
/// one.
#[must_use]
pub fn read_universal_newlines(path: &Path) -> Option<String> {
    if !path.is_file() {
        return None;
    }
    fs::read(path)
        .ok()
        .map(|bytes| universal_newlines(&String::from_utf8_lossy(&bytes)).into_owned())
}

/// Count the distinct GitHub issue URLs across `paths`.
#[must_use]
pub fn count_filed_urls_union_files(paths: &[&Path], gh_host: &str) -> usize {
    let pattern = issue_url_pattern(gh_host);
    let mut urls: BTreeSet<String> = BTreeSet::new();
    for path in paths {
        let Some(text) = read_universal_newlines(path) else {
            continue;
        };
        urls.extend(
            pattern
                .find_iter(&text)
                .map(|found| found.as_str().to_owned()),
        );
    }
    urls.len()
}

/// Count the distinct structured `- **Filed URL**:` rows across `paths`.
///
/// This is the strict half of the gate's evidence. A URL pasted into prose is
/// not disposition; only a URL written as this field is, because that is the
/// field the filer writes and the audit reads back.
#[must_use]
pub fn count_filed_urls_strict_files(paths: &[&Path]) -> usize {
    let mut urls: BTreeSet<String> = BTreeSet::new();
    for path in paths {
        let Some(text) = read_universal_newlines(path) else {
            continue;
        };
        urls.extend(
            STRICT_FILED_URL_RE
                .captures_iter(&text)
                .map(|found| found[1].to_owned()),
        );
    }
    urls.len()
}

/// Count inline-triage breadcrumbs in one commit-message blob.
///
/// Occurrences are counted, not lines and not distinct texts, because a commit
/// may triage several items and each breadcrumb covers exactly one record.
#[must_use]
pub fn count_inline_triage_occurrences(commit_messages: &str) -> usize {
    commit_messages.matches(INLINE_TRIAGE_MARKER).count()
}

/// Count non-security accepted OOS records in one Markdown file.
#[must_use]
pub fn count_non_security_oos_blocks(path: &Path) -> usize {
    read_universal_newlines(path)
        .as_deref()
        .map_or(0, count_non_security_blocks)
}

/// Collect the `OOS_<n>` markers one issue body explicitly rejected.
///
/// The rejected section runs from its own heading to the next second-level
/// heading, so a later section's mention of an item never reads as a
/// rejection of it.
fn rejected_markers_in_body(body: &str, markers: &mut BTreeSet<String>) {
    let lowered_body = body.to_lowercase();
    if !lowered_body.contains("rejected / out-of-scope") && !lowered_body.contains("## rejected") {
        return;
    }
    let mut in_rejected = false;
    let mut tail: Vec<&str> = Vec::new();
    for line in split_text_lines(body) {
        let lowered = line.to_lowercase();
        if REJECTED_SECTION_START_RE.is_match(&lowered)
            || lowered.contains("rejected / out-of-scope")
        {
            in_rejected = true;
            continue;
        }
        if !in_rejected {
            continue;
        }
        if REJECTED_SECTION_END_RE.is_match(line) {
            break;
        }
        tail.push(line);
    }
    markers.extend(
        REJECTED_MARKER_RE
            .find_iter(&tail.join("\n"))
            .map(|m| m.as_str().to_owned()),
    );
}

/// Count distinct rejected `OOS_<n>` markers in a filing batch.
///
/// Returns the count and whether any record failed to parse. A parse error is
/// reported rather than swallowed: an undercounted rejection would let an
/// undisposed run look disposed.
#[must_use]
pub fn count_rejected_oos_markers_from_ndjson(path: &Path) -> (usize, bool) {
    let Some(text) = read_universal_newlines(path).filter(|text| !text.is_empty()) else {
        return (0, false);
    };
    let mut markers: BTreeSet<String> = BTreeSet::new();
    let mut parse_error = false;
    for line in split_text_lines(&text) {
        if trim_python_whitespace(line).is_empty() {
            continue;
        }
        match serde_json::from_str::<Value>(line) {
            Ok(Value::Object(record)) => {
                rejected_markers_in_body(&python_str(record.get("body")), &mut markers);
            }
            Ok(_) | Err(_) => parse_error = true,
        }
    }
    (markers.len(), parse_error)
}

/// Count distinct inline-triage lines recorded in a run directory.
#[must_use]
pub fn count_inline_triage_hits(run_dir: &Path) -> usize {
    let mut lines: BTreeSet<String> = BTreeSet::new();
    for name in INLINE_TRIAGE_SOURCES {
        let Some(text) = read_universal_newlines(&run_dir.join(name)) else {
            continue;
        };
        lines.extend(
            split_text_lines(&text)
                .into_iter()
                .filter(|line| line.contains(INLINE_TRIAGE_MARKER))
                .map(str::to_owned),
        );
    }
    lines.len()
}

/// Summarize the OOS disposition one archived run directory recorded.
#[must_use]
pub fn analyze_run_dir(run_dir: &Path, gh_host: &str) -> OosDispositionCounts {
    let accepted = ACCEPTED_OOS_FILENAMES
        .iter()
        .map(|name| count_non_security_oos_blocks(&run_dir.join(name)))
        .sum();
    let ndjson = run_dir.join("oos-issues.ndjson");
    let created = run_dir.join("oos-issues-created.md");
    let (rejected, parse_error) = count_rejected_oos_markers_from_ndjson(&ndjson);
    let url_files: Vec<&Path> = [ndjson.as_path(), created.as_path()]
        .into_iter()
        .filter(|path| path.is_file())
        .collect();
    OosDispositionCounts {
        non_security_oos_blocks: accepted,
        issue_urls: count_filed_urls_union_files(&url_files, gh_host),
        inline_triage_hits: count_inline_triage_hits(run_dir),
        rejected_oos_markers: rejected,
        ndjson_parse_error: parse_error,
    }
}

#[cfg(test)]
mod tests {
    use super::{
        DispositionCounters, DispositionState, analyze_run_dir, count_filed_urls_strict_files,
        count_filed_urls_union_files, count_inline_triage_hits, count_inline_triage_occurrences,
        count_rejected_oos_markers_from_ndjson, issue_url_pattern,
    };
    use std::fs;
    use std::path::Path;
    use tempfile::tempdir;

    const URL: &str = "https://github.com/character-ai/larch/issues/8177";

    #[test]
    fn an_unnamed_state_never_reads_as_cleared() {
        assert_eq!(
            DispositionState::from_wire(" cleared "),
            Some(DispositionState::Cleared)
        );
        assert_eq!(
            DispositionState::from_wire("blocked"),
            Some(DispositionState::Blocked)
        );
        assert_eq!(
            DispositionState::from_wire("security-sidecar-pending"),
            Some(DispositionState::SecuritySidecarPending)
        );
        for refused in ["skipped", "unknown", "", "CLEARED"] {
            assert_eq!(DispositionState::from_wire(refused), None, "{refused}");
        }
    }

    #[test]
    fn states_render_and_exit_distinctly() {
        for state in [
            DispositionState::Cleared,
            DispositionState::Blocked,
            DispositionState::SecuritySidecarPending,
        ] {
            assert_eq!(DispositionState::from_wire(state.as_str()), Some(state));
        }
        assert_eq!(DispositionState::Cleared.exit_code(), 0);
        assert_eq!(DispositionState::Blocked.exit_code(), 1);
        assert_eq!(DispositionState::SecuritySidecarPending.exit_code(), 3);
    }

    #[test]
    fn the_gate_clears_on_filing_triage_or_explicit_rejection() {
        let base = DispositionCounters {
            non_security: 2,
            ..DispositionCounters::default()
        };
        assert!(!base.cleared());
        assert!(
            DispositionCounters {
                non_security: 0,
                ..base
            }
            .cleared()
        );
        assert!(
            DispositionCounters {
                filed_urls: 1,
                ..base
            }
            .cleared()
        );
        assert!(
            DispositionCounters {
                inline_triage: 2,
                ..base
            }
            .cleared()
        );
        assert!(
            !DispositionCounters {
                inline_triage: 1,
                ..base
            }
            .cleared()
        );
        assert!(
            DispositionCounters {
                rejected_markers: 2,
                ..base
            }
            .cleared()
        );
        assert_eq!(base.state(false), DispositionState::Blocked);
        assert_eq!(base.state(true), DispositionState::Blocked);
        let clear = DispositionCounters {
            filed_urls: 1,
            ..base
        };
        assert_eq!(clear.state(false), DispositionState::Cleared);
        assert_eq!(clear.state(true), DispositionState::SecuritySidecarPending);
    }

    #[test]
    fn the_failure_line_names_every_counter() {
        let counters = DispositionCounters {
            non_security: 3,
            filed_urls: 0,
            inline_triage: 1,
            rejected_markers: 2,
        };
        assert_eq!(
            counters.failure_line("abc..HEAD"),
            "oos-disposition-gate: FAIL non_security_oos=3 filed_urls=0 inline_triage_lines=1 rejected_oos_markers=2 (commit-range abc..HEAD)"
        );
    }

    #[test]
    fn an_enterprise_host_is_accepted_alongside_github_com() {
        let enterprise = issue_url_pattern("gh.example.com");
        assert!(enterprise.is_match("https://gh.example.com/o/r/issues/1"));
        assert!(enterprise.is_match(URL));
        assert!(!issue_url_pattern("github.com").is_match("https://gh.example.com/o/r/issues/1"));
        assert!(issue_url_pattern("").is_match(URL));
    }

    #[test]
    fn filed_urls_are_counted_once_across_files_and_missing_paths() {
        let dir = tempdir().expect("tempdir");
        let first = dir.path().join("a.md");
        let second = dir.path().join("b.md");
        fs::write(&first, format!("- **Filed URL**: {URL}\n{URL}\n")).expect("write");
        fs::write(&second, format!("{URL}\nhttps://github.com/o/r/issues/9\n")).expect("write");
        let missing = dir.path().join("gone.md");
        let paths = [first.as_path(), second.as_path(), missing.as_path()];
        assert_eq!(count_filed_urls_union_files(&paths, ""), 2);
        assert_eq!(count_filed_urls_union_files(&[], ""), 0);
    }

    #[test]
    fn rejected_markers_stop_at_the_next_section() {
        let dir = tempdir().expect("tempdir");
        let path = dir.path().join("oos-issues.ndjson");
        let body =
            "## Rejected / Out-of-Scope\\n- OOS_1 no\\n- OOS_1 again\\n## Accepted\\n- OOS_9 yes";
        fs::write(&path, format!("{{\"body\": \"{body}\"}}\n\n")).expect("write");
        assert_eq!(count_rejected_oos_markers_from_ndjson(&path), (1, false));
    }

    #[test]
    fn the_reconciled_reader_folds_case_and_stops_at_a_bare_section() {
        let dir = tempdir().expect("tempdir");
        let path = dir.path().join("oos-issues.ndjson");
        // Upper-cased marker: the outer presence check must agree with the
        // per-line scan, which always folded case.
        fs::write(&path, "{\"body\": \"## REJECTED\\n- OOS_4 no\"}\n").expect("write");
        assert_eq!(count_rejected_oos_markers_from_ndjson(&path), (1, false));
        // A bare `##Accepted` still ends the section, so an accepted item is
        // never counted as a rejection.
        fs::write(
            &path,
            "{\"body\": \"## Rejected\\n- OOS_1 no\\n##Accepted\\n- OOS_2 yes\"}\n",
        )
        .expect("write");
        assert_eq!(count_rejected_oos_markers_from_ndjson(&path), (1, false));
        // A third-level heading is payload inside the section, not a boundary.
        fs::write(
            &path,
            "{\"body\": \"## Rejected\\n### Detail\\n- OOS_5 no\"}\n",
        )
        .expect("write");
        assert_eq!(count_rejected_oos_markers_from_ndjson(&path), (1, false));
        // The cheap presence check is narrower than the scan below it, so a
        // widely spaced heading is skipped. That direction only under-counts
        // rejections, which blocks the gate rather than clearing it.
        fs::write(&path, "{\"body\": \"##  Rejected\\n- OOS_6 no\"}\n").expect("write");
        assert_eq!(count_rejected_oos_markers_from_ndjson(&path), (0, false));
    }

    #[test]
    fn only_a_structured_filed_url_row_counts_as_strict_evidence() {
        let dir = tempdir().expect("tempdir");
        let strict = dir.path().join("accepted.md");
        fs::write(
            &strict,
            format!("- **Filed URL**: {URL}\n- **Filed URL**: {URL} trailing\nprose {URL}\n"),
        )
        .expect("write");
        let missing = dir.path().join("gone.md");
        assert_eq!(
            count_filed_urls_strict_files(&[strict.as_path(), missing.as_path()]),
            1
        );
        assert_eq!(count_filed_urls_strict_files(&[]), 0);
    }

    #[test]
    fn inline_triage_breadcrumbs_are_counted_per_occurrence() {
        assert_eq!(
            count_inline_triage_occurrences(
                "Inline-triage rule 1: x\nbody\nInline-triage rule 1: x\n"
            ),
            2
        );
        assert_eq!(count_inline_triage_occurrences(""), 0);
    }

    #[test]
    fn an_unparseable_batch_reports_a_parse_error() {
        let dir = tempdir().expect("tempdir");
        let path = dir.path().join("oos-issues.ndjson");
        fs::write(&path, "not json\n[1]\n{\"body\": 5}\n").expect("write");
        assert_eq!(count_rejected_oos_markers_from_ndjson(&path), (0, true));
        fs::write(&path, "").expect("write");
        assert_eq!(count_rejected_oos_markers_from_ndjson(&path), (0, false));
        assert_eq!(
            count_rejected_oos_markers_from_ndjson(Path::new("/nonexistent/oos.ndjson")),
            (0, false)
        );
    }

    #[test]
    fn inline_triage_lines_are_deduplicated_across_sources() {
        let dir = tempdir().expect("tempdir");
        fs::write(
            dir.path().join("codex-commit-message.txt"),
            "Inline-triage rule: x\nother\n",
        )
        .expect("write");
        fs::write(
            dir.path().join("session-transcript.jsonl"),
            "Inline-triage rule: x\n",
        )
        .expect("write");
        assert_eq!(count_inline_triage_hits(dir.path()), 1);
        assert_eq!(count_inline_triage_hits(Path::new("/nonexistent/run")), 0);
    }

    #[test]
    fn a_run_directory_summary_joins_every_counter() {
        let dir = tempdir().expect("tempdir");
        fs::write(
            dir.path().join("oos-accepted-review.md"),
            "### OOS_1: keep\n### OOS_2: [security] hold\n",
        )
        .expect("write");
        fs::write(dir.path().join("oos-issues-created.md"), format!("{URL}\n")).expect("write");
        fs::write(
            dir.path().join("codex-commit-message.txt"),
            "Inline-triage rule: y\n",
        )
        .expect("write");
        let counts = analyze_run_dir(dir.path(), "");
        assert_eq!(counts.non_security_oos_blocks, 1);
        assert_eq!(counts.issue_urls, 1);
        assert_eq!(counts.inline_triage_hits, 1);
        assert_eq!(counts.rejected_oos_markers, 0);
        assert!(!counts.ndjson_parse_error);
    }
}
