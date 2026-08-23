//! Effect-free Mermaid fence extraction and sanitizer decisions.
//!
//! The command wire and PR composer intentionally choose their own input mode,
//! but both consume this one structured validator so safety policy cannot drift.

use std::sync::LazyLock;

use regex::Regex;

/// Flowchart node labels cannot contain an unquoted pipe.
pub const PIPE_IN_NODE: &str = "pipe-in-node-label";
/// Sequence participant aliases cannot contain an HTML line break.
pub const BR_IN_ALIAS: &str = "br-in-participant-alias";
/// Sequence participant aliases cannot contain a dollar sign.
pub const DOLLAR_IN_ALIAS: &str = "dollar-in-participant-alias";
/// Mermaid YAML frontmatter must have a closing delimiter.
pub const UNCLOSED_FRONTMATTER: &str = "unclosed-frontmatter";

static FENCE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[ \t]{0,3}(`{3,})([^`]*)$").expect("static Mermaid fence expression")
});
static FLOWCHART_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(flowchart|graph)(\s|$)").expect("static flowchart expression"));
static PARTICIPANT_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^(participant|actor)\s+[^\s]+\s+as\s+").expect("static participant expression")
});
static ALIAS_PREFIX_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[^\s]+\s+[^\s]+\s+as\s+").expect("static alias-prefix expression")
});
static BR_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)<br\s*/?>").expect("static participant-break expression"));

/// One Mermaid fence and the recognized section heading immediately above it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MermaidFence {
    pub lines: Vec<String>,
    pub heading: &'static str,
}

/// One sanitizer refusal with stable token and one-based coordinates.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MermaidReason {
    pub token: &'static str,
    pub fence: usize,
    pub line: usize,
}

/// Extract Mermaid fences when `from_markdown`, otherwise inspect the full text.
#[must_use]
pub fn inspect_mermaid(text: &str, from_markdown: bool) -> (Vec<MermaidFence>, Vec<MermaidReason>) {
    let fences = if from_markdown {
        extract_mermaid_fences(text)
    } else {
        vec![MermaidFence {
            lines: python_lines(text),
            heading: "unknown",
        }]
    };
    let mut reasons = Vec::new();
    for (index, fence) in fences.iter().enumerate() {
        validate_lines(&fence.lines, index + 1, &mut reasons);
    }
    (fences, reasons)
}

fn python_lines(text: &str) -> Vec<String> {
    text.lines()
        .map(|line| line.strip_suffix('\r').unwrap_or(line).to_owned())
        .collect()
}

fn heading_for(history: &[String]) -> &'static str {
    let title = |line: &String| {
        let title = line.trim_end().strip_prefix("##").and_then(|rest| {
            rest.chars()
                .next()
                .is_some_and(char::is_whitespace)
                .then(|| rest.trim())
        });
        title.map(str::to_owned)
    };
    let recent = history
        .iter()
        .rev()
        .take(5)
        .filter_map(title)
        .collect::<Vec<_>>();
    if recent
        .iter()
        .any(|title| title.eq_ignore_ascii_case("Code Flow Diagram"))
    {
        return "code-flow";
    }
    if recent
        .iter()
        .any(|title| title.eq_ignore_ascii_case("Architecture Diagram"))
    {
        return "architecture";
    }
    "unknown"
}

fn extract_mermaid_fences(text: &str) -> Vec<MermaidFence> {
    let mut fences = Vec::new();
    let mut history = Vec::<String>::new();
    let mut outer: Option<(usize, bool)> = None;
    for line in python_lines(text) {
        if let Some(captures) = FENCE_RE.captures(&line) {
            let width = captures[1].len();
            let rest = &captures[2];
            match outer {
                None => {
                    let mermaid = rest.trim() == "mermaid";
                    outer = Some((width, mermaid));
                    if mermaid {
                        fences.push(MermaidFence {
                            lines: Vec::new(),
                            heading: heading_for(&history),
                        });
                    }
                    continue;
                }
                Some((opening, _)) if width >= opening && rest.trim().is_empty() => {
                    outer = None;
                    continue;
                }
                Some(_) => {}
            }
        }
        if outer.is_some_and(|(_, mermaid)| mermaid) {
            fences
                .last_mut()
                .expect("Mermaid outer fence creates a report")
                .lines
                .push(line);
        } else if outer.is_none() && !line.trim().is_empty() {
            history.push(line);
            if history.len() > 5 {
                let _ = history.remove(0);
            }
        }
    }
    fences
}

fn validate_lines(lines: &[String], fence: usize, reasons: &mut Vec<MermaidReason>) {
    let mut frontmatter = false;
    let mut frontmatter_started = false;
    let mut first = None;
    for (index, line) in lines.iter().enumerate() {
        let stripped = line.trim();
        if stripped.is_empty() || stripped.starts_with("%%") {
            continue;
        }
        if !frontmatter_started && stripped == "---" {
            frontmatter = true;
            frontmatter_started = true;
            continue;
        }
        if frontmatter {
            if stripped == "---" {
                frontmatter = false;
            }
            continue;
        }
        first = Some(index);
        break;
    }
    if frontmatter {
        reasons.push(MermaidReason {
            token: UNCLOSED_FRONTMATTER,
            fence,
            line: lines.len(),
        });
        return;
    }
    let Some(start) = first else { return };
    let first_line = lines[start].trim();
    if FLOWCHART_RE.is_match(first_line) {
        if let Some(offset) = lines[start..]
            .iter()
            .position(|line| flowchart_rejects_pipe(line))
        {
            reasons.push(MermaidReason {
                token: PIPE_IN_NODE,
                fence,
                line: start + offset + 1,
            });
        }
    } else if first_line == "sequenceDiagram" {
        for (index, line) in lines.iter().enumerate().skip(start) {
            let stripped = line.trim();
            if !PARTICIPANT_RE.is_match(stripped) {
                continue;
            }
            let alias = ALIAS_PREFIX_RE.replace(stripped, "");
            if BR_RE.is_match(&alias) {
                reasons.push(MermaidReason {
                    token: BR_IN_ALIAS,
                    fence,
                    line: index + 1,
                });
            }
            if alias.contains('$') {
                reasons.push(MermaidReason {
                    token: DOLLAR_IN_ALIAS,
                    fence,
                    line: index + 1,
                });
            }
        }
    }
}

fn flowchart_rejects_pipe(line: &str) -> bool {
    let mut depth = 0_u32;
    let mut quote = false;
    let mut escape = false;
    for character in line.chars() {
        if depth > 0 && quote {
            if escape {
                escape = false;
            } else if character == '\\' {
                escape = true;
            } else if character == '"' {
                quote = false;
            }
        } else if depth > 0 && character == '"' {
            quote = true;
        } else if "[{(".contains(character) {
            depth += 1;
        } else if depth > 0 && "]})".contains(character) {
            depth -= 1;
        } else if depth > 0 && character == '|' {
            return true;
        }
    }
    false
}
