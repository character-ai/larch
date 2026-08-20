//! Pure `design publish` gates ported from `python/larch/design/design_publish.py`.
//!
//! The publish orchestrator lives in `larch-cli`; every decision it makes that
//! needs no process, GitHub call, or sibling verb lives here so the Gate C
//! assessment ladder, the review-provenance read, the provenance splice, and the
//! validate-log defect count stay provable offline.

use std::collections::BTreeMap;
use std::fs;
use std::fmt::Write as _;
use std::path::Path;
use std::sync::LazyLock;

use regex::Regex;

use super::plan_grammar::{OPTIONAL_SIZE_TRAILER_KEYS, TrailerKey, parse_final_trailers};
use crate::architectural_assessment::{ASSESSMENT_OUTCOME_CLEAN, classify_note_for_kind};
use crate::architectural_guidelines::{
    ArchitecturalKind, ArchitecturalStatus, read_architectural_knowledge,
};
use crate::env_file::{KvDocument, ParseOptions};
use crate::run_log::AssessmentKind;
use crate::text::balanced_fence_line_indices;

/// Every key any `design publish` result-env write may carry.
///
/// Mirrors the Python `PUBLISH_RESULT_ENV_ALLOW` frozenset exactly: a key the
/// orchestrator adds without listing here fails the write closed rather than
/// publishing a row no consumer parses.
pub const PUBLISH_RESULT_ENV_ALLOW: [&str; 34] = [
    "ARCHITECTURE_SOURCE",
    "ARCH_GUIDE_ASSESSMENT_ARTIFACT",
    "ARCH_GUIDE_ASSESSMENT_PRESENT",
    "ARCH_GUIDE_ASSESSMENT_REQUIRED",
    "ARCH_GUIDE_ASSESSMENT_STATUS",
    "ARCH_INVARIANT_ASSESSMENT_ARTIFACT",
    "ARCH_INVARIANT_ASSESSMENT_PRESENT",
    "ARCH_INVARIANT_ASSESSMENT_REQUIRED",
    "ARCH_INVARIANT_ASSESSMENT_STATUS",
    "CACHE_DIR",
    "DESIGNED_ADMISSION_READY",
    "FINAL_SUMMARY_PATH",
    "LATEST_PHASE",
    "LOG_PUBLISH_ATTEMPTED",
    "LOG_PUBLISH_COMPLETED",
    "LOG_RECOVERY_BRANCH",
    "NEW_TITLE",
    "PLAN_WRITE_OK",
    "PR_NUMBER",
    "PR_URL",
    "PUBLISH_ATTEMPT_ID",
    "PUBLISH_OK",
    "PUBLISH_RC_SOURCE",
    "PUBLISH_REFUSE_REASON",
    "RECOVERY_BRANCH",
    "REMOTE_KEY",
    "RENAMED",
    "UPSERT_STATUS",
    "VALIDATE_DEFECT_COUNT",
    "VALIDATE_LOG_FILE",
    "VALIDATE_MISSING_SCRIPT_COUNT",
    "VALIDATE_SKIPPED_COUNT",
    "VALIDATE_STATUS",
    "VALIDATE_UNSAFE_TOKEN_COUNT",
];

/// Review-loop statuses that publish accepts only with a Step 3 sentinel.
pub const TERMINAL_STATUSES_REQUIRING_SENTINEL: [&str; 2] = ["complete", "cap-hit"];
/// Review-loop statuses that block publish outright.
pub const BLOCKED_REVIEW_STATUSES: [&str; 2] = ["panel-init-failed", "panel-skipped"];

static DIGITS_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[0-9]+$").expect("digits expression"));
static ATTEMPT_ID_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9._-]{8,128}$").expect("attempt id expression"));
static REPO_SLUG_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$").expect("repository slug expression")
});
static EXCEPTION_LEAD_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^\s*Exception:").expect("exception lead expression"));
static DESIGN_EXCEPTION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^\s*Exception:\s+(?P<rationale>\S[^\n]*?)\s+\(author:\s*main-agent,\s+date:\s*(?P<date>\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01]))\)\s*$",
    )
    .expect("design exception expression")
});
static REASON_TOKEN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"REASON_TOKEN=([^ \t);,]+)").expect("reason token expression"));

/// Whether a publish `--repo` value is exactly `owner/name`.
#[must_use]
pub fn is_repo_slug(value: &str) -> bool {
    REPO_SLUG_RE.is_match(value)
}

/// Whether a publish attempt identifier matches the durable-sidecar grammar.
#[must_use]
pub fn is_publish_attempt_id(value: &str) -> bool {
    ATTEMPT_ID_RE.is_match(value)
}

/// Recover the diagram sanitizer's refusal token from its combined streams.
#[must_use]
pub fn sanitizer_reason_token(output: &str) -> String {
    REASON_TOKEN_RE
        .captures(output)
        .and_then(|captures| captures.get(1))
        .map_or_else(|| "unknown".to_owned(), |matched| matched.as_str().to_owned())
}

/// Read a KEY=value document the way the retired Python reader did: CR-free
/// lines, legacy tolerance for malformed rows, last value per key.
fn read_last_kvs(path: &Path) -> Option<BTreeMap<String, String>> {
    if path.is_symlink() || !path.is_file() {
        return None;
    }
    let raw = String::from_utf8_lossy(&fs::read(path).ok()?).into_owned();
    let text = raw
        .split('\n')
        .filter(|line| !line.contains('\r'))
        .collect::<Vec<&str>>()
        .join("\n");
    let document =
        KvDocument::parse(&text, ParseOptions::legacy()).expect("legacy parser is non-rejecting");
    let mut values = BTreeMap::new();
    for row in document.rows() {
        let _prior = values.insert(row.key().to_owned(), row.value().to_owned());
    }
    Some(values)
}

/// The review provenance publish reads before it will write a plan block.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ReviewProvenance {
    /// Normalized review-loop status, empty when the sidecar records none.
    pub status: String,
    /// Rounds the review loop completed.
    pub rounds_completed: u64,
    /// Whether the sidecar recorded any provenance at all.
    pub present: bool,
}

/// Return the launched-round count from `review-round-count.txt` (0 when absent).
fn read_review_round_count(design_tmpdir: &Path) -> u64 {
    let path = design_tmpdir.join("review-round-count.txt");
    if path.is_symlink() || !path.is_file() {
        return 0;
    }
    let Ok(bytes) = fs::read(&path) else {
        return 0;
    };
    let raw = String::from_utf8_lossy(&bytes).trim().to_owned();
    if DIGITS_RE.is_match(&raw) {
        raw.parse::<u64>().unwrap_or(0)
    } else {
        0
    }
}

/// Read `(status, rounds, present)` from `.step3-review-result.env`.
///
/// When a writer omitted both round-count keys, the launched-round count is
/// recovered from the durable `review-round-count.txt` so a cleanly reviewed
/// plan is not refused as `rounds_completed=0` (#5210).
#[must_use]
pub fn review_provenance(design_tmpdir: &Path) -> ReviewProvenance {
    let Some(values) = read_last_kvs(&design_tmpdir.join(".step3-review-result.env")) else {
        return ReviewProvenance::default();
    };
    let empty = String::new();
    let mut status = values
        .get("STEP3_REVIEW_LOOP_STATUS")
        .unwrap_or(&empty)
        .clone();
    if status.is_empty() {
        let loop_status = values.get("LOOP_STATUS").unwrap_or(&empty).as_str();
        let tally = values.get("TALLY_PLAN_REVIEW_STATUS").unwrap_or(&empty);
        status = match loop_status {
            "complete" => "complete".to_owned(),
            "cap-reached" | "cap-hit" => "cap-hit".to_owned(),
            "panel-failed" | "panel-init-failed" | "panel-skipped" | "tally-error"
            | "degraded-empty-collector" | "main-agent-vote-required" | "postplan-failed" => {
                loop_status.to_owned()
            }
            _ => tally.clone(),
        };
    }
    let rounds_raw = match values.get("ROUNDS_COMPLETED") {
        Some(value) if !value.is_empty() => value.clone(),
        _ => values.get("REVIEW_ROUND_COUNT").unwrap_or(&empty).clone(),
    };
    let trimmed = rounds_raw.trim();
    let rounds_completed = if trimmed.is_empty() {
        read_review_round_count(design_tmpdir)
    } else if DIGITS_RE.is_match(trimmed) {
        trimmed.parse::<u64>().unwrap_or(0)
    } else {
        0
    };
    ReviewProvenance {
        present: !status.is_empty() || !trimmed.is_empty(),
        status,
        rounds_completed,
    }
}

/// Insert review provenance above the optional size trailers and before
/// `diff_lines`, replacing whatever provenance the trailer block already had.
#[must_use]
pub fn splice_plan_provenance(text: &str, review_status: &str, rounds_completed: u64) -> String {
    let mut lines: Vec<String> = crate::text::split_lines_keep_ends(text)
        .into_iter()
        .map(str::to_owned)
        .collect();
    if let Some(last) = lines.last_mut()
        && !last.ends_with('\n')
    {
        last.push('\n');
    }
    let joined = lines.concat();
    let trailers = parse_final_trailers(&joined, true);
    if trailers.matches.is_empty() {
        return text.to_owned();
    }
    let trailer_start = trailers.start_line - 1;
    let diff_index = trailer_start + trailers.matches.len() - 1;
    let mut spliced = lines[..trailer_start].concat();
    let _ = writeln!(spliced, "review_status: {review_status}");
    let _ = writeln!(spliced, "rounds_completed: {rounds_completed}");
    if let Some(difficulty) = trailers.get(TrailerKey::Difficulty) {
        let _ = writeln!(spliced, "difficulty: {}", difficulty.value);
    }
    for (offset, matched) in trailers.matches.iter().enumerate() {
        if OPTIONAL_SIZE_TRAILER_KEYS.contains(&matched.key.as_str()) {
            spliced.push_str(&lines[trailer_start + offset]);
        }
    }
    spliced.push_str(&lines[diff_index..].concat());
    spliced
}

/// One Gate C assessment artifact's completeness verdict.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AssessmentCompleteness {
    /// Knowledge-file status token (`present`, `absent`, or `invalid`).
    pub knowledge_status: String,
    /// Whether this outcome and knowledge state require the artifact.
    pub required: bool,
    /// Whether the artifact is a present regular file.
    pub present: bool,
    /// Artifact basename inside the design tmpdir.
    pub artifact: &'static str,
    /// Diagnostic reason token.
    pub reason: String,
}

const APPROVED_OUTCOMES: [&str; 2] = ["approved", "approved-partition"];

const fn status_token(status: ArchitecturalStatus) -> &'static str {
    match status {
        ArchitecturalStatus::Present => "present",
        ArchitecturalStatus::Absent => "absent",
        ArchitecturalStatus::Invalid => "invalid",
    }
}

/// Classify a required-but-present artifact path the way Python did.
fn artifact_reason(path: &Path, present: bool) -> String {
    if present {
        "present".to_owned()
    } else if path.is_symlink() {
        "artifact-symlink".to_owned()
    } else if path.exists() {
        "artifact-not-regular".to_owned()
    } else {
        "artifact-missing".to_owned()
    }
}

/// Whether the architectural-invariant assessment is required and persisted.
///
/// Invariants require a non-empty parsed entry set as well as a present file:
/// a knowledge file with no `I-*` entries carries no invariant to assess.
#[must_use]
pub fn check_invariant_assessment_completeness(
    design_tmpdir: &Path,
    repo_root: &Path,
    outcome: &str,
) -> AssessmentCompleteness {
    let knowledge = read_architectural_knowledge(repo_root, ArchitecturalKind::Invariants);
    let artifact = AssessmentKind::Invariants.design_assessment_filename();
    let approved = APPROVED_OUTCOMES.contains(&outcome);
    let entries_present = !knowledge.content.trim().is_empty();
    let required =
        approved && knowledge.status == ArchitecturalStatus::Present && entries_present;
    let path = design_tmpdir.join(artifact);
    let present = path.is_file() && !path.is_symlink();
    let reason = if required {
        artifact_reason(&path, present)
    } else if !approved {
        "outcome-not-approved".to_owned()
    } else if knowledge.status == ArchitecturalStatus::Present && !entries_present {
        "invariants-empty".to_owned()
    } else {
        format!("invariants-{}", status_token(knowledge.status))
    };
    AssessmentCompleteness {
        knowledge_status: status_token(knowledge.status).to_owned(),
        required,
        present,
        artifact,
        reason,
    }
}

/// Whether the architectural-guideline assessment is required and persisted.
#[must_use]
pub fn check_guideline_assessment_completeness(
    design_tmpdir: &Path,
    repo_root: &Path,
    outcome: &str,
) -> AssessmentCompleteness {
    let knowledge = read_architectural_knowledge(repo_root, ArchitecturalKind::Guidelines);
    let artifact = AssessmentKind::Guidelines.design_assessment_filename();
    let approved = APPROVED_OUTCOMES.contains(&outcome);
    let required = approved && knowledge.status == ArchitecturalStatus::Present;
    let path = design_tmpdir.join(artifact);
    let present = path.is_file() && !path.is_symlink();
    let reason = if required {
        artifact_reason(&path, present)
    } else if approved {
        format!("guidelines-{}", status_token(knowledge.status))
    } else {
        "outcome-not-approved".to_owned()
    };
    AssessmentCompleteness {
        knowledge_status: status_token(knowledge.status).to_owned(),
        required,
        present,
        artifact,
        reason,
    }
}

/// Return the note's non-fenced lines that lead with `Exception:`.
fn active_exception_lines(note: &str) -> Vec<&str> {
    let lines: Vec<&str> = note.lines().collect();
    let fenced = balanced_fence_line_indices(&lines);
    lines
        .iter()
        .enumerate()
        .filter(|(index, line)| !fenced.contains(index) && EXCEPTION_LEAD_RE.is_match(line))
        .map(|(_index, line)| *line)
        .collect()
}

/// Whether `year-month-day` names a real calendar date.
const fn calendar_date_plausible(year: u32, month: u32, day: u32) -> bool {
    let leap = year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400));
    let length = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap => 29,
        2 => 28,
        _ => return false,
    };
    day >= 1 && day <= length
}

/// Whether a deviation note carries exactly one valid documented exception.
///
/// Missing, malformed, empty-rationale, wrong-author, impossible-date,
/// duplicate, and fenced-only notes all fail closed (#7196.2).
#[must_use]
pub fn guideline_exception_valid(note: &str) -> bool {
    let active = active_exception_lines(note);
    if active.len() != 1 {
        return false;
    }
    let Some(captures) = DESIGN_EXCEPTION_RE.captures(active[0]) else {
        return false;
    };
    let rationale = captures
        .name("rationale")
        .map_or("", |matched| matched.as_str())
        .trim();
    if rationale.is_empty() {
        return false;
    }
    let date = captures.name("date").map_or("", |matched| matched.as_str());
    let parts: Vec<&str> = date.split('-').collect();
    let [year, month, day] = parts.as_slice() else {
        return false;
    };
    match (year.parse::<u32>(), month.parse::<u32>(), day.parse::<u32>()) {
        (Ok(year), Ok(month), Ok(day)) => calendar_date_plausible(year, month, day),
        _ => false,
    }
}

/// Classify a present, regular assessment note for the Gate C publish gate.
///
/// Invariants publish only when the note classifies clean; a violation note
/// fails closed. Guidelines publish when the note is clean, or a deviation
/// carries exactly one validated documented exception. An unreadable note
/// fails closed.
#[must_use]
pub fn persisted_note_publishable(path: &Path, kind: AssessmentKind) -> bool {
    let Ok(bytes) = fs::read(path) else {
        return false;
    };
    let note = String::from_utf8_lossy(&bytes).into_owned();
    if classify_note_for_kind(&note, kind) == ASSESSMENT_OUTCOME_CLEAN {
        return true;
    }
    if kind.is_invariant() {
        return false;
    }
    guideline_exception_valid(&note)
}

/// Count `kind=missing-script` defect rows in a validate log, as a wire value.
#[must_use]
pub fn count_missing_script_defects(log_file: &str) -> String {
    if log_file.is_empty() {
        return "0".to_owned();
    }
    let path = Path::new(log_file);
    if path.is_symlink() || !path.is_file() {
        return "0".to_owned();
    }
    let Ok(bytes) = fs::read(path) else {
        return "0".to_owned();
    };
    String::from_utf8_lossy(&bytes)
        .lines()
        .filter(|line| line.contains("kind=missing-script"))
        .count()
        .to_string()
}

/// Return the publish-blocking review-provenance reason, or an empty string.
#[must_use]
pub fn blocked_review_reason(provenance: &ReviewProvenance, step3_sentinel: bool) -> String {
    if BLOCKED_REVIEW_STATUSES.contains(&provenance.status.as_str()) {
        return provenance.status.clone();
    }
    if provenance.present && provenance.rounds_completed == 0 {
        return "rounds_completed=0".to_owned();
    }
    if TERMINAL_STATUSES_REQUIRING_SENTINEL.contains(&provenance.status.as_str())
        && !step3_sentinel
    {
        return format!("{} without .completed/step-3", provenance.status);
    }
    String::new()
}

#[cfg(test)]
mod tests {
    use super::{
        PUBLISH_RESULT_ENV_ALLOW, ReviewProvenance, blocked_review_reason,
        check_guideline_assessment_completeness, check_invariant_assessment_completeness,
        count_missing_script_defects, guideline_exception_valid, is_publish_attempt_id,
        is_repo_slug, persisted_note_publishable, review_provenance, sanitizer_reason_token,
        splice_plan_provenance,
    };
    use crate::run_log::AssessmentKind;
    use std::fs;
    use tempfile::TempDir;

    fn plan_with_trailers() -> String {
        "## Plan\n\nbody\n\nreview_status: stale\nrounds_completed: 9\ndifficulty: MODERATE\n\
         diff_added: 3\ndiff_lines: 42\n"
            .to_owned()
    }

    #[test]
    fn the_result_env_allowlist_matches_the_retired_python_frozenset() {
        assert_eq!(PUBLISH_RESULT_ENV_ALLOW.len(), 34);
        let mut sorted = PUBLISH_RESULT_ENV_ALLOW;
        sorted.sort_unstable();
        assert_eq!(sorted, PUBLISH_RESULT_ENV_ALLOW, "allowlist stays sorted");
        assert!(PUBLISH_RESULT_ENV_ALLOW.contains(&"PUBLISH_REFUSE_REASON"));
        assert!(PUBLISH_RESULT_ENV_ALLOW.contains(&"VALIDATE_MISSING_SCRIPT_COUNT"));
        assert!(!PUBLISH_RESULT_ENV_ALLOW.contains(&"SECRET_SCRUB_VIOLATIONS"));
    }

    #[test]
    fn provenance_splices_above_optional_trailers_and_before_diff_lines() {
        let spliced = splice_plan_provenance(&plan_with_trailers(), "complete", 2);
        assert!(spliced.ends_with(
            "review_status: complete\nrounds_completed: 2\ndifficulty: MODERATE\n\
             diff_added: 3\ndiff_lines: 42\n"
        ));
        assert!(!spliced.contains("rounds_completed: 9"));
    }

    #[test]
    fn a_plan_without_a_terminal_diff_lines_trailer_is_returned_unchanged() {
        let text = "## Plan\n\nbody\n";
        assert_eq!(splice_plan_provenance(text, "complete", 1), text);
    }

    #[test]
    fn review_provenance_reads_the_status_ladder_and_round_fallback() {
        let root = TempDir::new().expect("tmpdir");
        let sidecar = root.path().join(".step3-review-result.env");
        fs::write(&sidecar, "LOOP_STATUS=cap-reached\nROUNDS_COMPLETED=3\n").expect("write");
        let read = review_provenance(root.path());
        assert_eq!(
            read,
            ReviewProvenance {
                status: "cap-hit".to_owned(),
                rounds_completed: 3,
                present: true,
            }
        );

        fs::write(&sidecar, "STEP3_REVIEW_LOOP_STATUS=complete\n").expect("write");
        fs::write(root.path().join("review-round-count.txt"), "2\n").expect("write");
        let recovered = review_provenance(root.path());
        assert_eq!(recovered.rounds_completed, 2, "#5210 durable fallback");
        assert!(recovered.present);

        fs::remove_file(&sidecar).expect("remove");
        assert_eq!(review_provenance(root.path()), ReviewProvenance::default());
    }

    #[test]
    fn blocked_review_reasons_cover_every_refusal_the_python_gate_had() {
        let blocked = ReviewProvenance {
            status: "panel-skipped".to_owned(),
            rounds_completed: 4,
            present: true,
        };
        assert_eq!(blocked_review_reason(&blocked, true), "panel-skipped");
        let zero = ReviewProvenance {
            status: "complete".to_owned(),
            rounds_completed: 0,
            present: true,
        };
        assert_eq!(blocked_review_reason(&zero, true), "rounds_completed=0");
        let unsentineled = ReviewProvenance {
            status: "cap-hit".to_owned(),
            rounds_completed: 2,
            present: true,
        };
        assert_eq!(
            blocked_review_reason(&unsentineled, false),
            "cap-hit without .completed/step-3"
        );
        assert!(blocked_review_reason(&unsentineled, true).is_empty());
        assert!(blocked_review_reason(&ReviewProvenance::default(), false).is_empty());
    }

    #[test]
    fn invariant_completeness_requires_present_knowledge_with_parsed_entries() {
        let root = TempDir::new().expect("tmpdir");
        let repo = root.path().join("repo");
        let tmpdir = root.path().join("design");
        fs::create_dir_all(&repo).expect("repo");
        fs::create_dir_all(&tmpdir).expect("tmpdir");

        let absent = check_invariant_assessment_completeness(&tmpdir, &repo, "approved");
        assert!(!absent.required);
        assert_eq!(absent.reason, "invariants-absent");

        fs::write(
            repo.join("ARCHITECTURAL_INVARIANTS.md"),
            "# No invariant entries\n",
        )
        .expect("write");
        let empty = check_invariant_assessment_completeness(&tmpdir, &repo, "approved");
        assert!(!empty.required);
        assert_eq!(empty.reason, "invariants-empty");

        fs::write(
            repo.join("ARCHITECTURAL_INVARIANTS.md"),
            "## I-Core-1: Keep one owner\n\nBody line.\n",
        )
        .expect("write");
        let missing = check_invariant_assessment_completeness(&tmpdir, &repo, "approved");
        assert!(missing.required && !missing.present);
        assert_eq!(missing.reason, "artifact-missing");
        assert_eq!(missing.artifact, "architectural-invariant-assessment.md");

        let unapproved = check_invariant_assessment_completeness(&tmpdir, &repo, "cancelled");
        assert!(!unapproved.required);
        assert_eq!(unapproved.reason, "outcome-not-approved");

        fs::write(tmpdir.join(missing.artifact), "note\n").expect("write");
        let present = check_invariant_assessment_completeness(&tmpdir, &repo, "approved-partition");
        assert!(present.required && present.present);
        assert_eq!(present.reason, "present");
    }

    #[test]
    fn guideline_completeness_only_needs_present_knowledge() {
        let root = TempDir::new().expect("tmpdir");
        let repo = root.path().join("repo");
        let tmpdir = root.path().join("design");
        fs::create_dir_all(&repo).expect("repo");
        fs::create_dir_all(&tmpdir).expect("tmpdir");
        fs::write(repo.join("ARCHITECTURAL_GUIDELINES.md"), "# no entries\n").expect("write");
        let required = check_guideline_assessment_completeness(&tmpdir, &repo, "approved");
        assert!(required.required && !required.present);
        assert_eq!(required.reason, "artifact-missing");
        assert_eq!(required.artifact, "architectural-guideline-assessment.md");
    }

    #[test]
    fn a_persisted_invariant_note_publishes_only_when_it_classifies_clean() {
        let root = TempDir::new().expect("tmpdir");
        let clean = root.path().join("clean.md");
        fs::write(
            &clean,
            format!(
                "{}\n",
                AssessmentKind::Invariants.clean_presentation_note()
            ),
        )
        .expect("write");
        assert!(persisted_note_publishable(&clean, AssessmentKind::Invariants));

        let violation = root.path().join("violation.md");
        fs::write(&violation, "I-Core-1 is violated by this plan.\n").expect("write");
        assert!(!persisted_note_publishable(
            &violation,
            AssessmentKind::Invariants
        ));
        assert!(!persisted_note_publishable(
            &root.path().join("absent.md"),
            AssessmentKind::Invariants
        ));
    }

    #[test]
    fn a_guideline_deviation_publishes_only_with_one_valid_documented_exception() {
        let root = TempDir::new().expect("tmpdir");
        let bare = root.path().join("bare.md");
        fs::write(&bare, "G-Py-4 applies to this plan.\n").expect("write");
        assert!(!persisted_note_publishable(&bare, AssessmentKind::Guidelines));

        let excepted = root.path().join("excepted.md");
        fs::write(
            &excepted,
            "G-Py-4 applies to this plan.\nException: pragmatic port (author: main-agent, date: 2026-07-13)\n",
        )
        .expect("write");
        assert!(persisted_note_publishable(
            &excepted,
            AssessmentKind::Guidelines
        ));
    }

    #[test]
    fn exception_validation_rejects_fenced_duplicate_and_impossible_dates() {
        let valid = "G-Py-4.\nException: reason here (author: main-agent, date: 2024-02-29)\n";
        assert!(guideline_exception_valid(valid), "leap day is a real date");
        assert!(!guideline_exception_valid(
            "G-Py-4.\nException: reason here (author: main-agent, date: 2023-02-29)\n"
        ));
        assert!(!guideline_exception_valid(
            "G-Py-4.\n```\nException: fenced (author: main-agent, date: 2026-07-13)\n```\n"
        ));
        assert!(!guideline_exception_valid(
            "G-Py-4.\nException: one (author: main-agent, date: 2026-07-13)\n\
             Exception: two (author: main-agent, date: 2026-07-14)\n"
        ));
        assert!(!guideline_exception_valid(
            "G-Py-4.\nException: reason here (author: reviewer, date: 2026-07-13)\n"
        ));
        assert!(!guideline_exception_valid("G-Py-4.\n"));
    }

    #[test]
    fn missing_script_defects_count_only_present_regular_logs() {
        let root = TempDir::new().expect("tmpdir");
        let log = root.path().join("validate-plan-commands.log");
        fs::write(
            &log,
            "DEFECT plan kind=missing-script path=a\nDEFECT plan kind=unsafe path=b\n\
             DEFECT plan kind=missing-script path=c\n",
        )
        .expect("write");
        assert_eq!(count_missing_script_defects(&log.display().to_string()), "2");
        assert_eq!(count_missing_script_defects(""), "0");
        assert_eq!(
            count_missing_script_defects(&root.path().join("absent.log").display().to_string()),
            "0"
        );
    }

    #[test]
    fn argv_token_grammars_match_the_retired_python_expressions() {
        assert!(is_repo_slug("owner/name"));
        assert!(!is_repo_slug("owner/name/extra"));
        assert!(!is_repo_slug("owner"));
        assert!(is_publish_attempt_id("direct-1234-abcdef01"));
        assert!(!is_publish_attempt_id("short"));
        assert!(!is_publish_attempt_id("has space 1234"));
        assert_eq!(
            sanitizer_reason_token("STATUS=rejected REASON_TOKEN=unsafe-node;"),
            "unsafe-node"
        );
        assert_eq!(sanitizer_reason_token("STATUS=rejected"), "unknown");
    }
}
