//! Effect-free `/design` pause marker and routing logic.

use std::collections::BTreeMap;

use sha2::{Digest as _, Sha256};

use crate::{
    DuplicatePolicy, EmptyKeyPolicy, KvDocument, KvError, ParseOptions, WhitespacePolicy, kv_text,
};

pub const DESIGN_PAUSE_START: &str = "<!-- larch:design-pause:start -->";
pub const DESIGN_PAUSE_END: &str = "<!-- larch:design-pause:end -->";

/// Result of locating and parsing the issue-body pause block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PauseMarker {
    Absent,
    Malformed,
    Present(BTreeMap<String, String>),
}

/// Remove every complete or partial pause-marker region, preserving final LF.
#[must_use]
pub fn strip_pause_markers(body: &str) -> String {
    let mut output = Vec::new();
    let mut inside = false;
    for line in body.lines() {
        if line.trim() == DESIGN_PAUSE_START {
            inside = true;
        } else if line.trim() == DESIGN_PAUSE_END {
            inside = false;
        } else if !inside {
            output.push(line);
        }
    }
    let mut stripped = output.join("\n");
    if body.ends_with('\n') {
        stripped.push('\n');
    }
    stripped
}

/// Parse the first pause block using the legacy last-key-wins KV grammar.
#[must_use]
pub fn parse_pause_marker(body: &str) -> PauseMarker {
    let start = body.find(DESIGN_PAUSE_START);
    let end = body.find(DESIGN_PAUSE_END);
    let (Some(start), Some(end)) = (start, end) else {
        return if start.is_none() && end.is_none() {
            PauseMarker::Absent
        } else {
            PauseMarker::Malformed
        };
    };
    if end < start {
        return PauseMarker::Malformed;
    }
    let payload = &body[start + DESIGN_PAUSE_START.len()..end];
    let mut options = ParseOptions::legacy();
    options.empty_keys = EmptyKeyPolicy::Skip;
    options.key_whitespace = WhitespacePolicy::Trim;
    options.value_whitespace = WhitespacePolicy::Trim;
    KvDocument::parse(payload, options).map_or(PauseMarker::Malformed, |document| {
        let values = document.select(DuplicatePolicy::Last);
        if values.is_empty() {
            PauseMarker::Malformed
        } else {
            PauseMarker::Present(values)
        }
    })
}

/// Compute the body binding after removing the mutable pause block.
#[must_use]
pub fn pause_body_hash(body: &str) -> String {
    let stripped = strip_pause_markers(body);
    format!("{:x}", Sha256::digest(stripped.as_bytes()))
}

/// Select the first resumable step from completion truth and the step registry.
#[must_use]
pub fn determine_pause_step(
    reentry: bool,
    completed: impl Fn(&str) -> bool,
    registry: Option<&str>,
) -> String {
    if reentry {
        return "3".to_owned();
    }
    if completed("3") && completed("3.5") && !completed("3b") {
        return "3b".to_owned();
    }
    if completed("3") && completed("3b") && !completed("4") {
        return "4".to_owned();
    }
    if completed("3") && !completed("3.5") {
        return "3.5".to_owned();
    }
    if completed("5b.5") && !completed("5b") {
        return "5b".to_owned();
    }
    if completed("5b") && !completed("5b.5") {
        return "5b.5".to_owned();
    }
    if completed("5b") && completed("5b.5") && !completed("5c") {
        return "5c".to_owned();
    }
    let Some(registry) = registry else {
        return "6".to_owned();
    };
    for line in registry.lines() {
        if line.is_empty() || line.starts_with("step\t") {
            continue;
        }
        let step = line.split_once('\t').map_or(line, |(step, _)| step);
        if step != "0" && step != "5" && !completed(step) {
            return step.to_owned();
        }
    }
    "6".to_owned()
}

/// Render the byte-stable pause pointer consumed by `named-block write`.
///
/// # Errors
///
/// Returns [`KvError`] when an input could forge an additional wire row.
pub fn render_pause_state(
    step: &str,
    issue: &str,
    run_id: &str,
    repo: &str,
    brainstorm_done: bool,
    body_hash: &str,
) -> Result<String, KvError> {
    let mut rows = vec![
        ("STEP", step),
        ("ISSUE_NUMBER", issue),
        ("SESSION_ID", run_id),
        ("RUN_ID", run_id),
    ];
    if !repo.is_empty() {
        rows.push(("REPO", repo));
    }
    rows.push((
        "BRAINSTORM_DONE",
        if brainstorm_done { "true" } else { "false" },
    ));
    rows.push(("BODY_HASH", body_hash));
    kv_text(&rows)
}

/// Return whether a marker step is part of the stable resume grammar.
#[must_use]
pub fn valid_pause_step(step: &str) -> bool {
    matches!(
        step,
        "1" | "1d"
            | "2"
            | "2b"
            | "3"
            | "3.5"
            | "3b"
            | "4"
            | "4b"
            | "5"
            | "5b"
            | "5b.5"
            | "5c"
            | "6"
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn marker_parse_is_last_wins_and_strip_preserves_final_lf() {
        let body = format!(
            "before\n{DESIGN_PAUSE_START}\nSTEP=2\nSTEP = 3b \n{DESIGN_PAUSE_END}\nafter\n"
        );
        assert_eq!(strip_pause_markers(&body), "before\nafter\n");
        let PauseMarker::Present(values) = parse_pause_marker(&body) else {
            panic!("pause marker should parse");
        };
        assert_eq!(values.get("STEP").map(String::as_str), Some("3b"));
        assert_eq!(
            parse_pause_marker(&format!("{DESIGN_PAUSE_START}\nSTEP=2")),
            PauseMarker::Malformed
        );
        assert_eq!(
            parse_pause_marker(&format!("{DESIGN_PAUSE_START}\n{DESIGN_PAUSE_END}")),
            PauseMarker::Malformed
        );
        assert_eq!(
            parse_pause_marker("ordinary issue body\n"),
            PauseMarker::Absent
        );
        assert_eq!(
            parse_pause_marker(&format!("{DESIGN_PAUSE_END}\n{DESIGN_PAUSE_START}\n")),
            PauseMarker::Malformed
        );
    }

    #[test]
    fn step_selection_preserves_resume_precedence() {
        let registry = "step\tname\n0\tsetup\n1\tone\n2\ttwo\n5\tfive\n6\tdone\n";
        assert_eq!(
            determine_pause_step(false, |step| step == "1", Some(registry)),
            "2"
        );
        assert_eq!(
            determine_pause_step(false, |step| matches!(step, "3" | "3.5"), Some(registry)),
            "3b"
        );
        assert_eq!(
            determine_pause_step(false, |step| step == "3", Some(registry)),
            "3.5"
        );
        assert_eq!(
            determine_pause_step(false, |step| matches!(step, "3" | "3b"), Some(registry)),
            "4"
        );
        assert_eq!(
            determine_pause_step(false, |step| step == "5b.5", Some(registry)),
            "5b"
        );
        assert_eq!(
            determine_pause_step(false, |step| step == "5b", Some(registry)),
            "5b.5"
        );
        assert_eq!(
            determine_pause_step(false, |step| matches!(step, "5b" | "5b.5"), Some(registry)),
            "5c"
        );
        assert_eq!(determine_pause_step(true, |_| false, None), "3");
        assert_eq!(determine_pause_step(false, |_| true, None), "6");
    }

    #[test]
    fn state_wire_is_exact_and_repo_is_optional() {
        assert_eq!(
            render_pause_state("4b", "42", "run-1", "o/r", true, "abc").as_deref(),
            Ok(
                "STEP=4b\nISSUE_NUMBER=42\nSESSION_ID=run-1\nRUN_ID=run-1\nREPO=o/r\nBRAINSTORM_DONE=true\nBODY_HASH=abc\n"
            )
        );
        assert!(
            render_pause_state("1", "42", "r", "", false, "h")
                .is_ok_and(|state| !state.contains("REPO="))
        );
        assert!(render_pause_state("1\nFORGED=x", "42", "r", "", false, "h").is_err());
        for step in [
            "1", "1d", "2", "2b", "3", "3.5", "3b", "4", "4b", "5", "5b", "5b.5", "5c", "6",
        ] {
            assert!(valid_pause_step(step), "{step} must remain resumable");
        }
        assert!(!valid_pause_step("0"));
    }
}
