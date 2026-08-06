//! Diagram-capture sanitizer for `Warnings` failure bodies.
//!
//! Ported from `strip_diagram_sections` and `sanitize_diagram_capture` in
//! `larch.report.design_diagram_log`. Diagram bodies must never reach a durable
//! run-log artifact, so a body that still looks like Mermaid after stripping
//! collapses to a fixed token.

use std::sync::LazyLock;

use regex::Regex;

const REDACTED_TOKEN: &str = "diagram-content-redacted";

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

#[cfg(test)]
mod tests {
    use super::{sanitize_diagram_capture, strip_diagram_sections};

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
}
