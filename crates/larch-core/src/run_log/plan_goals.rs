//! `plan-goals` batch sanitizer.
//!
//! Ported from `larch.design.plan_grammar.implementation_plan_body` plus the
//! pointer-only placeholder rejection in `larch.report.run_log_batch`.

use std::sync::LazyLock;

use regex::Regex;

static POINTER_ONLY: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^(?:see plan\.txt|see attached|see linked|tbd|todo)\.?$")
        .expect("static pointer-only regex must compile")
});

/// Extract a non-empty Implementation Plan body from a full plan document.
///
/// # Errors
///
/// Returns the Python-compatible reason when the section is missing or empty.
pub fn implementation_plan_body(text: &str) -> Result<String, String> {
    let mut in_section = false;
    let mut saw_section = false;
    let mut body_lines: Vec<&str> = Vec::new();
    let mut test_plan_index = 0_usize;
    for line in text.lines() {
        if line == "## Implementation Plan" {
            if !saw_section {
                in_section = true;
            }
            saw_section = true;
            continue;
        }
        if in_section {
            body_lines.push(line);
            if line == "## Test plan" {
                test_plan_index = body_lines.len();
            }
        }
    }
    if !saw_section {
        return Err("missing ## Implementation Plan".to_owned());
    }
    let limit = if test_plan_index > 0 {
        test_plan_index - 1
    } else {
        body_lines.len()
    };
    let body = &body_lines[..limit];
    if !body.iter().any(|line| !line.trim().is_empty()) {
        return Err("Implementation Plan body is empty".to_owned());
    }
    let mut joined = body.join("\n").trim_end().to_owned();
    joined.push('\n');
    Ok(joined)
}

/// Reject a `plan-goals` payload with no plan body or a pointer-only body.
///
/// # Errors
///
/// Returns the operator-facing rejection message.
pub fn validate_plan_goals_payload(text: &str) -> Result<(), String> {
    let body = implementation_plan_body(text)
        .map_err(|reason| format!("plan-goals sanitizer rejected: {reason}"))?;
    let first = body
        .lines()
        .map(str::trim)
        .find(|line| !line.is_empty())
        .unwrap_or_default()
        .to_lowercase();
    if POINTER_ONLY.is_match(&first) {
        return Err(
            "plan-goals sanitizer rejected: Implementation Plan body is a pointer-only placeholder"
                .to_owned(),
        );
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{implementation_plan_body, validate_plan_goals_payload};

    #[test]
    fn extracts_body_and_stops_before_test_plan() {
        let text = "# Title\n## Implementation Plan\nstep one\nstep two\n\n## Test plan\ncases\n";
        assert_eq!(
            implementation_plan_body(text).expect("body should extract"),
            "step one\nstep two\n"
        );
    }

    #[test]
    fn missing_and_empty_sections_fail_loudly() {
        assert_eq!(
            implementation_plan_body("# Title\n").expect_err("missing section"),
            "missing ## Implementation Plan"
        );
        assert_eq!(
            implementation_plan_body("## Implementation Plan\n\n\n").expect_err("empty section"),
            "Implementation Plan body is empty"
        );
    }

    #[test]
    fn pointer_only_body_is_rejected() {
        let error = validate_plan_goals_payload("## Implementation Plan\nSee plan.txt\n")
            .expect_err("pointer-only body should fail");
        assert!(error.contains("pointer-only placeholder"));
        assert!(validate_plan_goals_payload("## Implementation Plan\nreal work\n").is_ok());
    }
}
