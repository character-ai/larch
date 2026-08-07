//! Bounded, redacted vendor failure diagnostics.
//!
//! Everything here is effect-free. The adapter layer reads and writes the
//! files; this module owns the artifact-path family, the section ordering, the
//! line and byte budgets, and the redaction routing.

use regex::Regex;
use std::{
    ffi::OsString,
    path::{Path, PathBuf},
    sync::LazyLock,
};

use crate::{
    redaction::redact,
    text::{split_text_lines, tail_lines, truncate_utf8_bytes},
};

/// Hard ceiling on one composed failure-diagnostic carrier.
pub const VENDOR_FAILURE_DIAG_BYTE_CAP: usize = 16384;
/// Default per-section line budget inside a composed failure diagnostic.
pub const VENDOR_FAILURE_DIAG_SECTION_LINES: usize = 120;
/// Default tail length for a failed-agent stderr excerpt.
pub const FAILED_AGENT_STDERR_TAIL_LINES: usize = 30;
/// Hard ceiling on a failed-agent stderr excerpt.
pub const FAILED_AGENT_STDERR_TAIL_BYTE_CAP: usize = 5120;

/// Sink path that must never be read as a diagnostic source.
const NULL_DEVICE: &str = "/dev/null";

static FAILURE_EVENT_PATTERN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i-u:error|fail|quota|usage[ _-]?limit|rate[ _-]?limit|turn\.failed|unauthor|forbidden|denied|timed?[ _-]?out|exception|panic|fatal|unhealthy|exit[ _-]?code)",
    )
    .expect("static failure event regex must compile")
});

/// One artifact in the launcher's output-file family.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum LauncherArtifactKind {
    /// Wrapper completion sentinel carrying the launcher exit code.
    Done,
    /// Inner completion sentinel written by the launched vendor.
    InnerDone,
    /// Launch metadata record.
    Meta,
    /// Vendor stderr sidecar.
    Sidecar,
    /// Launcher diagnostic capture.
    Diag,
    /// Structured vendor event stream.
    Events,
    /// Token accounting record.
    TokenRecord,
    /// Composed failure-diagnostic carrier.
    FailureDiag,
    /// Rendered prompt sent to the vendor.
    Prompt,
    /// Bounded stderr excerpt for a failed agent.
    StderrTail,
    /// Stall detector state.
    StallJson,
    /// Raw vendor stderr capture.
    Stderr,
    /// Stderr captured while starting the launcher.
    LaunchStderr,
    /// Stderr emitted by the launcher wrapper itself.
    LauncherStderr,
    /// Rolled-over sidecar history across attempts.
    SidecarHistory,
    /// Rolled-over event history across attempts.
    EventsHistory,
    /// Mid-run dirty-tree status sidecar.
    DirtyTree,
    /// Pre-launch untracked-file baseline for cursor dirty-tree comparison.
    UntrackedBaseline,
    /// Tracked dirty paths recorded beside a dirty-tree sidecar.
    DirtyTreeTrackedPaths,
    /// New untracked paths recorded beside a dirty-tree sidecar.
    DirtyTreeNewUntrackedPaths,
    /// Token-budget cap-hit carrier written beside the output.
    CapHit,
}

impl LauncherArtifactKind {
    /// Return the suffix appended to the launcher output path.
    #[must_use]
    pub const fn suffix(self) -> &'static str {
        match self {
            Self::Done => ".done",
            Self::InnerDone => ".inner.done",
            Self::Meta => ".meta",
            Self::Sidecar => ".sidecar",
            Self::Diag => ".diag",
            Self::Events => ".events.jsonl",
            Self::TokenRecord => ".token-record",
            Self::FailureDiag => ".failure-diag",
            Self::Prompt => ".prompt",
            Self::StderrTail => ".stderr-tail",
            Self::StallJson => ".stall.json",
            Self::Stderr => ".stderr",
            Self::LaunchStderr => ".launch-stderr",
            Self::LauncherStderr => ".launcher-stderr",
            Self::SidecarHistory => ".sidecar.history",
            Self::EventsHistory => ".events.history",
            Self::DirtyTree => ".dirty-tree",
            Self::UntrackedBaseline => ".untracked-baseline",
            Self::DirtyTreeTrackedPaths => ".dirty-tree.tracked-paths",
            Self::DirtyTreeNewUntrackedPaths => ".dirty-tree.new-untracked-paths",
            Self::CapHit => ".cap-hit",
        }
    }
}

/// The launcher output path and every artifact derived from it.
///
/// This is the single owner of the launcher artifact-path family. Vendor
/// lifecycle, adapter, and collector work reuses it rather than re-deriving
/// these suffixes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LauncherArtifactPaths {
    output: PathBuf,
}

impl LauncherArtifactPaths {
    /// Anchor the family on one launcher output path.
    #[must_use]
    pub fn new(output: impl Into<PathBuf>) -> Self {
        Self {
            output: output.into(),
        }
    }

    /// Return the launcher output path itself.
    #[must_use]
    pub fn output(&self) -> &Path {
        &self.output
    }

    /// Return the path of one derived artifact.
    #[must_use]
    pub fn path(&self, kind: LauncherArtifactKind) -> PathBuf {
        let mut name = OsString::from(self.output.as_os_str());
        name.push(kind.suffix());
        PathBuf::from(name)
    }
}

/// How a launcher routed the vendor's stderr for this attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StderrCaptureMode {
    /// Both streams landed in the output file.
    Combined,
    /// Only stdout landed in the output file.
    StdoutOnly,
    /// Stderr landed in a dedicated sink or the sidecar.
    Separate,
}

/// Return the ordered candidates for a failed agent's stderr excerpt.
///
/// The caller selects the first candidate that is a non-empty regular file.
#[must_use]
pub fn failed_agent_stderr_candidates(
    paths: &LauncherArtifactPaths,
    mode: StderrCaptureMode,
    stderr_sink: Option<&Path>,
) -> Vec<PathBuf> {
    match mode {
        StderrCaptureMode::Combined => vec![
            paths.output().to_path_buf(),
            paths.path(LauncherArtifactKind::Diag),
        ],
        StderrCaptureMode::StdoutOnly => vec![
            paths.path(LauncherArtifactKind::Diag),
            paths.output().to_path_buf(),
        ],
        StderrCaptureMode::Separate => {
            let mut candidates: Vec<PathBuf> =
                stderr_sink.map(Path::to_path_buf).into_iter().collect();
            candidates.extend([
                paths.path(LauncherArtifactKind::Sidecar),
                paths.output().to_path_buf(),
                paths.path(LauncherArtifactKind::Diag),
            ]);
            candidates
        }
    }
}

/// Render a bounded, redacted tail of a failed agent's stderr.
///
/// Returns an empty string when either budget is zero or the source is empty.
#[must_use]
pub fn render_failed_agent_stderr_tail(text: &str, lines: usize, byte_cap: usize) -> String {
    if lines == 0 || byte_cap == 0 || text.is_empty() {
        return String::new();
    }
    let body = tail_lines(&split_text_lines(text), lines);
    if body.is_empty() {
        return String::new();
    }
    let content = format!("{}\n", body.join("\n"));
    // Every diagnostic write routes through the shared redaction owner.
    let redacted = redact(&content);
    truncate_utf8_bytes(redacted.text(), byte_cap).to_owned()
}

/// One ordered input to a composed failure diagnostic.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FailureDiagSource<'a> {
    /// Section heading written above the body.
    pub label: &'a str,
    /// Path the body was read from, used only for the null-device guard.
    pub path: &'a Path,
    /// Decoded text, empty when the path is not a readable regular file.
    pub text: &'a str,
    /// Whether the body keeps only failure-event lines.
    pub filtered: bool,
}

/// Return the ordered failure-diagnostic sources for one launcher output.
#[must_use]
pub fn failure_diag_source_order(
    paths: &LauncherArtifactPaths,
    sink: Option<&Path>,
    history: Option<&Path>,
    events: Option<&Path>,
) -> Vec<(&'static str, PathBuf, bool)> {
    let events_path = events.map_or_else(
        || paths.path(LauncherArtifactKind::Events),
        Path::to_path_buf,
    );
    let sidecar = paths.path(LauncherArtifactKind::Sidecar);
    let diag = paths.path(LauncherArtifactKind::Diag);
    let history_path = history.map_or_else(
        || paths.path(LauncherArtifactKind::SidecarHistory),
        Path::to_path_buf,
    );
    let mut ordered = vec![
        ("sidecar.history", history_path, false),
        (
            "events.history (filtered)",
            paths.path(LauncherArtifactKind::EventsHistory),
            true,
        ),
    ];
    // A sink that already appears later in the order is not repeated.
    if let Some(sink) = sink
        .filter(|sink| ![events_path.as_path(), sidecar.as_path(), diag.as_path()].contains(sink))
    {
        ordered.push(("sink", sink.to_path_buf(), false));
    }
    ordered.extend([
        ("sidecar", sidecar, false),
        ("diag", diag, false),
        ("events.jsonl (filtered)", events_path, true),
        ("stderr", paths.path(LauncherArtifactKind::Stderr), false),
        (
            "launch-stderr",
            paths.path(LauncherArtifactKind::LaunchStderr),
            false,
        ),
        (
            "launcher-stderr",
            paths.path(LauncherArtifactKind::LauncherStderr),
            false,
        ),
    ]);
    ordered
}

/// Return the ordered candidates for the diagnostic carrier that best
/// describes one launcher failure.
///
/// The caller selects the first candidate that is a non-empty regular file. The
/// two retry stems come from the Codex retry launchers, which publish their own
/// carriers beside the primary output. Order is most-specific first, so a
/// caller can also ask whether an already-published excerpt came from a
/// less-specific carrier than the one it now has.
#[must_use]
pub fn failure_diagnostic_source_candidates(
    paths: &LauncherArtifactPaths,
    sink: Option<&Path>,
) -> Vec<PathBuf> {
    let output = paths.output().as_os_str().to_string_lossy().into_owned();
    let stem = output.strip_suffix(".txt").unwrap_or(&output);
    let mut candidates = vec![
        paths.path(LauncherArtifactKind::FailureDiag),
        PathBuf::from(format!("{stem}-retry.txt.failure-diag")),
        PathBuf::from(format!("{stem}-ns-retry.txt.failure-diag")),
    ];
    if let Some(sink) = sink {
        candidates.push(sink.to_path_buf());
    }
    candidates.extend([
        paths.path(LauncherArtifactKind::SidecarHistory),
        paths.path(LauncherArtifactKind::Sidecar),
        paths.path(LauncherArtifactKind::Diag),
        paths.path(LauncherArtifactKind::Events),
        paths.path(LauncherArtifactKind::Stderr),
        paths.path(LauncherArtifactKind::LaunchStderr),
        paths.path(LauncherArtifactKind::LauncherStderr),
        paths.output().to_path_buf(),
    ]);
    candidates
}

/// Render one failure-diagnostic section body under its line budget.
#[must_use]
pub fn failure_diag_section_body(source: &FailureDiagSource<'_>, section_lines: usize) -> String {
    if source.text.is_empty() || source.path == Path::new(NULL_DEVICE) {
        return String::new();
    }
    let lines = split_text_lines(source.text);
    let selected = if source.filtered {
        lines
            .into_iter()
            .filter(|line| FAILURE_EVENT_PATTERN.is_match(line))
            .collect()
    } else {
        lines
    };
    tail_lines(&selected, section_lines)
        .join("\n")
        .trim_end_matches('\n')
        .to_owned()
}

/// Compose the bounded, redacted failure-diagnostic body.
///
/// Returns `None` when no section carried content. The ported Python wrote this
/// carrier unredacted; #8105 makes redaction mandatory before any diagnostic
/// write, so the body is scrubbed through the shared owner and then capped.
#[must_use]
pub fn compose_failure_diag(
    sources: &[FailureDiagSource<'_>],
    section_lines: usize,
    byte_cap: usize,
) -> Option<String> {
    let sections: Vec<String> = sources
        .iter()
        .filter_map(|source| {
            let body = failure_diag_section_body(source, section_lines);
            (!body.is_empty()).then(|| format!("===== {} =====\n{body}", source.label))
        })
        .collect();
    if sections.is_empty() {
        return None;
    }
    let joined = format!("{}\n", sections.join("\n"));
    let redacted = redact(&joined);
    Some(truncate_utf8_bytes(redacted.text(), byte_cap).to_owned())
}

/// What a caller should do with a composed diagnostic given the current carrier.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum FailureDiagWrite {
    /// The carrier already contains this body.
    Skip,
    /// Replace the carrier with this body.
    Create(String),
    /// Append this body under an additional-diagnostics heading.
    Append(String),
}

/// Decide how a composed diagnostic joins an existing carrier.
#[must_use]
pub fn plan_failure_diag_write(existing: &str, composed: String) -> FailureDiagWrite {
    if existing.is_empty() {
        return FailureDiagWrite::Create(composed);
    }
    if existing.contains(composed.trim_end()) {
        return FailureDiagWrite::Skip;
    }
    FailureDiagWrite::Append(format!(
        "\n===== additional failure diagnostics =====\n{composed}"
    ))
}

/// Render the redacted history entry an attempt contributes before its reset.
///
/// Returns `None` when the stream carried nothing worth preserving. Like
/// [`compose_failure_diag`], this scrubs before the caller writes.
#[must_use]
pub fn stream_reset_history_entry(label: &str, text: &str, section_lines: usize) -> Option<String> {
    let body = tail_lines(&split_text_lines(text), section_lines.saturating_mul(2)).join("\n");
    if body.is_empty() {
        return None;
    }
    let redacted = redact(&body);
    Some(format!("===== {label} =====\n{}\n\n", redacted.text()))
}

#[cfg(test)]
mod tests {
    use std::path::{Path, PathBuf};

    use super::{
        FAILED_AGENT_STDERR_TAIL_BYTE_CAP, FAILED_AGENT_STDERR_TAIL_LINES, FailureDiagSource,
        FailureDiagWrite, LauncherArtifactKind, LauncherArtifactPaths, StderrCaptureMode,
        VENDOR_FAILURE_DIAG_SECTION_LINES, compose_failure_diag, failed_agent_stderr_candidates,
        failure_diag_source_order, plan_failure_diag_write, render_failed_agent_stderr_tail,
        stream_reset_history_entry,
    };

    fn paths() -> LauncherArtifactPaths {
        LauncherArtifactPaths::new("/session/review.txt")
    }

    #[test]
    fn artifact_suffixes_append_to_the_full_output_name() {
        assert_eq!(
            paths().path(LauncherArtifactKind::Events),
            PathBuf::from("/session/review.txt.events.jsonl")
        );
        assert_eq!(
            LauncherArtifactPaths::new("/session/out").path(LauncherArtifactKind::Done),
            PathBuf::from("/session/out.done")
        );
        assert_eq!(
            paths().path(LauncherArtifactKind::DirtyTree),
            PathBuf::from("/session/review.txt.dirty-tree")
        );
        assert_eq!(
            paths().path(LauncherArtifactKind::CapHit),
            PathBuf::from("/session/review.txt.cap-hit")
        );
        assert_eq!(
            paths().path(LauncherArtifactKind::UntrackedBaseline),
            PathBuf::from("/session/review.txt.untracked-baseline")
        );
    }

    #[test]
    fn stderr_candidate_order_depends_on_the_capture_mode() {
        let paths = paths();
        assert_eq!(
            failed_agent_stderr_candidates(&paths, StderrCaptureMode::Combined, None),
            vec![
                PathBuf::from("/session/review.txt"),
                PathBuf::from("/session/review.txt.diag"),
            ]
        );
        assert_eq!(
            failed_agent_stderr_candidates(&paths, StderrCaptureMode::StdoutOnly, None)[0],
            PathBuf::from("/session/review.txt.diag")
        );
        let sink = PathBuf::from("/session/sink.txt");
        let separate =
            failed_agent_stderr_candidates(&paths, StderrCaptureMode::Separate, Some(&sink));
        assert_eq!(separate[0], sink);
        assert_eq!(separate.len(), 4);
    }

    #[test]
    fn the_stderr_tail_redacts_and_respects_both_budgets() {
        let text = "line one\nsk-ant-0123456789012345678901234\nlast line\n";
        let rendered = render_failed_agent_stderr_tail(
            text,
            FAILED_AGENT_STDERR_TAIL_LINES,
            FAILED_AGENT_STDERR_TAIL_BYTE_CAP,
        );
        assert!(!rendered.contains("sk-ant-"), "{rendered}");
        assert!(rendered.contains("<REDACTED-TOKEN>"));
        assert_eq!(
            render_failed_agent_stderr_tail(text, 1, 4096),
            "last line\n"
        );
        assert_eq!(render_failed_agent_stderr_tail(text, 0, 4096), "");
        assert_eq!(render_failed_agent_stderr_tail(text, 30, 0), "");
        assert_eq!(render_failed_agent_stderr_tail("", 30, 4096), "");
    }

    #[test]
    fn an_oversized_tail_is_capped_on_a_character_boundary() {
        let text = "é".repeat(4000);
        let rendered = render_failed_agent_stderr_tail(&text, 30, 101);
        assert_eq!(rendered.len(), 100);
        assert!(rendered.chars().all(|character| character == 'é'));
    }

    #[test]
    fn composition_orders_sections_and_filters_event_streams() {
        let events = "quiet progress\nturn.failed hard\nmore quiet\n";
        let sidecar = "plain sidecar body\n";
        let sources = [
            FailureDiagSource {
                label: "sidecar",
                path: Path::new("/session/review.txt.sidecar"),
                text: sidecar,
                filtered: false,
            },
            FailureDiagSource {
                label: "events.jsonl (filtered)",
                path: Path::new("/session/review.txt.events.jsonl"),
                text: events,
                filtered: true,
            },
            FailureDiagSource {
                label: "sink",
                path: Path::new("/dev/null"),
                text: "ignored",
                filtered: false,
            },
        ];
        let composed = compose_failure_diag(&sources, VENDOR_FAILURE_DIAG_SECTION_LINES, 16384)
            .expect("composed diagnostics");
        assert_eq!(
            composed,
            "===== sidecar =====\nplain sidecar body\n===== events.jsonl (filtered) =====\nturn.failed hard\n"
        );
        assert!(compose_failure_diag(&[], 120, 16384).is_none());
        let secret = [FailureDiagSource {
            label: "sidecar",
            path: Path::new("/session/review.txt.sidecar"),
            text: "token sk-ant-0123456789012345678901234 leaked\n",
            filtered: false,
        }];
        let scrubbed = compose_failure_diag(&secret, 120, 16384).expect("composed diagnostics");
        assert!(!scrubbed.contains("sk-ant-"), "{scrubbed}");
        assert!(scrubbed.contains("<REDACTED-TOKEN>"));
    }

    #[test]
    fn the_source_order_skips_a_sink_that_repeats_a_later_section() {
        let paths = paths();
        let sidecar = paths.path(LauncherArtifactKind::Sidecar);
        assert!(
            !failure_diag_source_order(&paths, Some(&sidecar), None, None)
                .iter()
                .any(|(label, _, _)| *label == "sink")
        );
        let sink = PathBuf::from("/session/sink.txt");
        let with_sink = failure_diag_source_order(&paths, Some(&sink), None, None);
        assert_eq!(with_sink[2].0, "sink");
        assert_eq!(with_sink[0].0, "sidecar.history");
    }

    #[test]
    fn carrier_planning_skips_a_body_the_carrier_already_holds() {
        let composed = String::from("===== sidecar =====\nbody\n");
        assert_eq!(
            plan_failure_diag_write("", composed.clone()),
            FailureDiagWrite::Create(composed.clone())
        );
        assert_eq!(
            plan_failure_diag_write(&composed, composed.clone()),
            FailureDiagWrite::Skip
        );
        assert_eq!(
            plan_failure_diag_write("older body\n", composed),
            FailureDiagWrite::Append(String::from(
                "\n===== additional failure diagnostics =====\n===== sidecar =====\nbody\n"
            ))
        );
    }

    #[test]
    fn a_stream_reset_preserves_double_the_section_budget() {
        let text = "a\nb\nc\nd\ne\n";
        assert_eq!(
            stream_reset_history_entry("attempt", text, 2),
            Some(String::from("===== attempt =====\nb\nc\nd\ne\n\n"))
        );
        assert_eq!(stream_reset_history_entry("attempt", "", 120), None);
        let scrubbed = stream_reset_history_entry("attempt", "ghp_012345678901234567890123", 120)
            .expect("history entry");
        assert!(!scrubbed.contains("ghp_"), "{scrubbed}");
    }
}
