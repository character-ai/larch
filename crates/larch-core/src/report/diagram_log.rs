//! Diagram-capture sanitizer and bounded failure logging.
//!
//! Ports `larch.report.design_diagram_log` whole: the capture sanitizers plus
//! the bounded warning bullet and sidecar writer that `/design` Step 5b.5 and
//! `/implement` Step 7a emit when diagram generation fails. Diagram bodies must
//! never reach a durable run-log artifact, so a body that still looks like
//! Mermaid after stripping collapses to a fixed token, and every emitted line
//! passes the stripper again before it is written.
//!
//! The Python owner stays in place for now because its two callers, `design
//! publish` and `pr create`, belong to umbrellas #7680 and #7681; this module is
//! the Rust owner their cutover leaves adopt.

use std::{
    fs,
    io::Result as IoResult,
    path::{Path, PathBuf},
    sync::LazyLock,
};

use regex::Regex;

use crate::{redaction, text::trim_python_whitespace};

const REDACTED_TOKEN: &str = "diagram-content-redacted";
/// Longest bounded `reason=` or `detail=` value, in characters.
const DETAIL_LIMIT: usize = 240;

static SECTION: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u)^##[ \t]+(?:Architecture Diagram|Code Flow Diagram)[ \t]*$")
        .expect("static section regex must compile")
});
static HEADING: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^#{1,2}(\s|$)").expect("static heading regex must compile"));
static FENCE_OPEN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^ {0,3}`{3,}\s*\S*").expect("static fence-open regex must compile")
});
static FENCE_CLOSE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^ {0,3}`{3,}\s*$").expect("static fence-close regex must compile")
});
static MERMAID_LINE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i-u)^\s*(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)\b",
    )
    .expect("static mermaid-line regex must compile")
});
static MERMAID_KEYWORD_LINE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i-u)^\s*(participant|actor|subgraph|classDef|style)\b")
        .expect("static mermaid-keyword regex must compile")
});
static SEQUENCE_ARROW: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^\s*\S+\s*->>\s*\S+").expect("static sequence-arrow regex must compile")
});
static EDGE_LINE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"^\s*[\w\[\]()"'-]+\s*(-->|---|-\.-|==>|\.+)\s*[\w\[\]()"'-]+"#)
        .expect("static edge-line regex must compile")
});
static MERMAID_REMAINS: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"(?i-u)(```|\b(?:graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey)\b|\b(?:participant|actor|subgraph|classDef|style)\b|->>|-->|-\.-|==>)",
    )
    .expect("static mermaid-remains regex must compile")
});
static FENCE_RUN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"`{3,}").expect("static fence-run regex must compile"));
static MERMAID_WORD: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i-u)mermaid").expect("static mermaid-word regex must compile"));
static WHITESPACE_RUN: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\s+").expect("static whitespace-run regex must compile"));
static UNSAFE_SLUG_RUN: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"[^A-Za-z0-9._-]+").expect("static slug-token regex must compile")
});

fn line_is_mermaid_syntax(line: &str) -> bool {
    MERMAID_LINE.is_match(line)
        || MERMAID_KEYWORD_LINE.is_match(line)
        || SEQUENCE_ARROW.is_match(line)
        || EDGE_LINE.is_match(line)
}

/// Remove diagram sections, fenced blocks, and unfenced graph syntax.
#[must_use]
pub fn strip_diagram_sections(text: &str) -> String {
    let mut kept: Vec<&str> = Vec::new();
    let mut in_diagram_section = false;
    let mut in_fence = false;
    let mut fence_len = 3_usize;
    for line in text.lines() {
        if in_fence {
            if let Some(matched) = FENCE_CLOSE.find(line)
                && matched.as_str().trim_start().len() >= fence_len
            {
                in_fence = false;
            }
            continue;
        }
        if in_diagram_section {
            if SECTION.is_match(line) {
                continue;
            }
            if HEADING.is_match(line) {
                in_diagram_section = false;
            } else {
                continue;
            }
        }
        if SECTION.is_match(line) {
            in_diagram_section = true;
            continue;
        }
        if line_is_mermaid_syntax(line) {
            continue;
        }
        if let Some(matched) = FENCE_OPEN.find(line) {
            let opener = matched.as_str().trim_start();
            fence_len = opener.len() - opener.trim_start_matches('`').len();
            in_fence = true;
            continue;
        }
        kept.push(line);
    }
    let out = kept.join("\n").trim().to_owned();
    if out.is_empty() { out } else { out + "\n" }
}

/// Strip diagram content from an untrusted capture, failing closed on remainder.
#[must_use]
pub fn sanitize_diagram_capture(text: &str) -> String {
    let stripped = strip_diagram_sections(text);
    let stripped = FENCE_RUN.replace_all(&stripped, "");
    let stripped = MERMAID_WORD.replace_all(&stripped, "");
    let stripped = stripped.trim();
    if stripped.is_empty() || MERMAID_REMAINS.is_match(stripped) {
        return REDACTED_TOKEN.to_owned();
    }
    // Python re-appends a newline only when the trimmed body already ends with
    // one, which `str.strip()` makes impossible; the token-free body is returned
    // verbatim.
    stripped.to_owned()
}

/// Collapse untrusted text into one bounded, Mermaid-free `KEY=value` value.
///
/// Ports `_sanitize_bounded_text`. Python guarded its redaction call and fell
/// back to `redaction-failed`; the Rust redactor is total, so the fallback has
/// no reachable branch here.
fn sanitize_bounded_text(raw: &str) -> String {
    let stripped = strip_diagram_sections(raw);
    let stripped = FENCE_RUN.replace_all(&stripped, "");
    let stripped = MERMAID_WORD.replace_all(&stripped, "");
    let redacted = redaction::redact(&stripped);
    let collapsed = WHITESPACE_RUN.replace_all(redacted.text(), " ");
    let detail = trim_python_whitespace(&collapsed);
    if detail.is_empty() {
        return "unknown".to_owned();
    }
    if MERMAID_REMAINS.is_match(detail) {
        return REDACTED_TOKEN.to_owned();
    }
    bound_detail(detail)
}

/// Trim a value to [`DETAIL_LIMIT`] characters, keeping the tail behind `...`.
fn bound_detail(detail: &str) -> String {
    let length = detail.chars().count();
    if length <= DETAIL_LIMIT {
        return detail.to_owned();
    }
    let tail: String = detail
        .chars()
        .skip(length - (DETAIL_LIMIT - 3))
        .collect::<String>();
    format!("...{tail}")
}

/// Read one raw capture and reduce it to a bounded `detail=` value.
///
/// A missing path, a non-regular file, a symlink, or an unreadable file yields
/// the empty string, which the writer treats as "emit no `detail=` line".
fn bounded_detail(raw_capture_path: Option<&Path>) -> String {
    let Some(path) = raw_capture_path else {
        return String::new();
    };
    let Ok(metadata) = fs::symlink_metadata(path) else {
        return String::new();
    };
    if !metadata.file_type().is_file() {
        return String::new();
    }
    let Ok(bytes) = fs::read(path) else {
        return String::new();
    };
    sanitize_bounded_text(&String::from_utf8_lossy(&bytes))
}

/// Compose the Mermaid-free warning bullet `execution-issues.md` carries.
#[must_use]
pub fn bounded_diagram_warning_body(reason: &str, exit_code: &str) -> String {
    let stripped = strip_diagram_sections(reason);
    let collapsed = WHITESPACE_RUN.replace_all(&stripped, " ");
    let trimmed = trim_python_whitespace(&collapsed);
    let safe_reason = if trimmed.is_empty() {
        "unknown"
    } else {
        trimmed
    };
    let fenceless = safe_reason.replace("```", "");
    let safe_reason = MERMAID_WORD.replace_all(&fenceless, "");
    format!("- **Diagram failure**: reason={safe_reason}; exit-code={exit_code}")
}

/// Write a bounded sidecar carrying only `KEY=value` lines and return its path.
///
/// The sidecar is named for `site`, so one tmpdir holds one file per failure
/// site rather than one growing log. Every emitted line passes the stripper a
/// second time, so no fence, keyword, or arrow can survive composition.
///
/// # Errors
///
/// Returns the directory-creation or write failure unchanged.
pub fn write_bounded_diagram_failure_log(
    tmpdir: &Path,
    site: &str,
    reason: &str,
    exit_code: &str,
    raw_capture_path: Option<&Path>,
) -> IoResult<PathBuf> {
    fs::create_dir_all(tmpdir)?;
    let lowered = trim_python_whitespace(site).to_lowercase();
    let slug = UNSAFE_SLUG_RUN.replace_all(&lowered, "-");
    let slug = slug.trim_matches('-');
    let slug = if slug.is_empty() { "diagram" } else { slug };
    let path = tmpdir.join(format!("{slug}-diagram-failure.bounded.log"));
    let mut lines = vec![
        format!("site={site}"),
        format!("reason={}", sanitize_bounded_text(reason)),
        format!("exit-code={exit_code}"),
    ];
    let detail = bounded_detail(raw_capture_path);
    if !detail.is_empty() {
        lines.push(format!("detail={detail}"));
    }
    let text = lines.join("\n") + "\n";
    let text = strip_diagram_sections(&text).replace("```", "");
    let text = MERMAID_WORD.replace_all(&text, "");
    fs::write(&path, text.as_bytes())?;
    Ok(path)
}

#[cfg(test)]
mod tests {
    use std::fs;

    use tempfile::tempdir;

    use super::{
        bounded_diagram_warning_body, sanitize_bounded_text, sanitize_diagram_capture,
        strip_diagram_sections, write_bounded_diagram_failure_log,
    };

    #[test]
    fn strips_fenced_blocks_and_diagram_sections() {
        let text = "intro\n## Architecture Diagram\ngraph TD\nA-->B\n## Next\ntail\n";
        assert_eq!(strip_diagram_sections(text), "intro\n## Next\ntail\n");
    }

    #[test]
    fn collapses_a_capture_that_is_all_diagram() {
        assert_eq!(
            sanitize_diagram_capture("```mermaid\ngraph TD\nA-->B\n```\n"),
            "diagram-content-redacted"
        );
    }

    #[test]
    fn keeps_a_diagram_free_capture() {
        assert_eq!(
            sanitize_diagram_capture("generator exited 2\nno output\n"),
            "generator exited 2\nno output"
        );
    }

    #[test]
    fn fails_closed_when_syntax_survives_stripping() {
        // An indented arrow escapes the line filters but not the remainder check.
        assert_eq!(
            sanitize_diagram_capture("note: see A ->> B for detail\n"),
            "diagram-content-redacted"
        );
    }

    #[test]
    fn bounds_a_long_detail_to_its_tail() {
        let bounded = sanitize_bounded_text(&"x".repeat(400));
        assert_eq!(bounded.chars().count(), 240);
        assert!(bounded.starts_with("..."), "{bounded}");
    }

    #[test]
    fn an_empty_capture_reads_as_unknown() {
        assert_eq!(sanitize_bounded_text("   \n\n"), "unknown");
    }

    #[test]
    fn composes_a_mermaid_free_warning_bullet() {
        assert_eq!(
            bounded_diagram_warning_body("generation-failed\trc=2", "2"),
            "- **Diagram failure**: reason=generation-failed rc=2; exit-code=2"
        );
        // The whole line opens a fence, so the stripper consumes it and the
        // bullet degrades to the fixed placeholder rather than leaking a body.
        assert_eq!(
            bounded_diagram_warning_body("```mermaid fence```", "1"),
            "- **Diagram failure**: reason=unknown; exit-code=1"
        );
    }

    #[test]
    fn writes_a_site_named_sidecar_with_key_values_only() {
        let directory = tempdir().expect("tempdir");
        let capture = directory.path().join("raw.log");
        fs::write(&capture, "stderr:\ngraph TD\nA-->B\nplain tail\n").expect("capture");
        let path = write_bounded_diagram_failure_log(
            &directory.path().join("nested"),
            "design Step 5b.5",
            "generation-failed rc=2",
            "2",
            Some(&capture),
        )
        .expect("sidecar");

        assert_eq!(
            path.file_name().and_then(|name| name.to_str()),
            Some("design-step-5b.5-diagram-failure.bounded.log")
        );
        let body = fs::read_to_string(&path).expect("body");
        assert_eq!(
            body,
            "site=design Step 5b.5\nreason=generation-failed rc=2\nexit-code=2\ndetail=stderr: plain tail\n"
        );
    }

    #[test]
    fn a_missing_capture_emits_no_detail_line() {
        let directory = tempdir().expect("tempdir");
        let path = write_bounded_diagram_failure_log(directory.path(), "  ", "", "0", None)
            .expect("sidecar");
        assert_eq!(
            path.file_name().and_then(|name| name.to_str()),
            Some("diagram-diagram-failure.bounded.log")
        );
        assert_eq!(
            fs::read_to_string(&path).expect("body"),
            "site=  \nreason=unknown\nexit-code=0\n"
        );
    }
}
