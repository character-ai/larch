//! Effect-free composition for the Rust ship PR driver.

use std::sync::LazyLock;

use regex::Regex;

use crate::redact_outbound;

const MAX_PR_BODY_BYTES: usize = 65_536;
const PIPE_IN_NODE: &str = "pipe-in-node-label";
const BR_IN_ALIAS: &str = "br-in-participant-alias";
const DOLLAR_IN_ALIAS: &str = "dollar-in-participant-alias";
const UNCLOSED_FRONTMATTER: &str = "unclosed-frontmatter";

static FENCE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(\s{0,3})(`{3,})([^`]*)$").expect("static fence expression"));

/// Inputs for the exact PR-body section and footer contract.
pub struct ShipPrBody<'a> {
    pub summary: &'a str,
    pub mermaid: &'a str,
    pub test_plan: &'a str,
    pub architectural_invariants_note: &'a str,
    pub architectural_guidelines_note: &'a str,
    pub deferred_inventory: &'a str,
    pub issue_number: u64,
    pub partial: bool,
}

/// Compose, validate, and redact one outbound PR body.
///
/// # Errors
/// Returns when Mermaid is unsafe, redaction cannot complete, or the body is oversized.
pub fn compose_ship_pr_body(input: &ShipPrBody<'_>) -> Result<String, String> {
    if !input.mermaid.trim().is_empty() {
        validate_mermaid(input.mermaid, false)
            .map_err(|reasons| format!("mermaid fragment rejected: {}", reasons.join(",")))?;
    }
    let mut parts = vec![input.summary.trim_end().to_owned(), String::new()];
    append_section(
        &mut parts,
        "Architectural invariants",
        input.architectural_invariants_note,
    );
    append_section(
        &mut parts,
        "Architectural guidelines",
        input.architectural_guidelines_note,
    );
    if !input.mermaid.trim().is_empty() {
        parts.extend([
            "## Code Flow Diagram".to_owned(),
            String::new(),
            "```mermaid".to_owned(),
            input.mermaid.trim().to_owned(),
            "```".to_owned(),
            String::new(),
        ]);
    }
    if !input.deferred_inventory.trim().is_empty() {
        parts.extend([
            input.deferred_inventory.trim_end().to_owned(),
            String::new(),
        ]);
    }
    parts.extend([
        "## Test plan".to_owned(),
        String::new(),
        input.test_plan.trim_end().to_owned(),
        String::new(),
    ]);
    let footer = if input.partial { "Part of" } else { "Closes" };
    let mut body = format!(
        "{}\n\n{footer} #{}\n",
        parts.join("\n").trim_end(),
        input.issue_number
    );
    validate_mermaid(&body, true)
        .map_err(|reasons| format!("mermaid in PR body rejected: {}", reasons.join(",")))?;
    body = redact_outbound(&body);
    if body.contains("[content truncated") {
        return Err("redaction failed for PR body".to_owned());
    }
    if body.len() > MAX_PR_BODY_BYTES {
        return Err("PR body exceeds the outbound size limit".to_owned());
    }
    Ok(format!("{}\n", body.trim_end_matches('\n')))
}

/// Derive the frozen issue-prefixed PR title.
#[must_use]
pub fn ship_pr_title(issue: u64, persisted: &str, head_subject: &str) -> String {
    let prefix = format!("Fixes #{issue}: ");
    let title = if persisted.is_empty() {
        if head_subject.is_empty() {
            format!("Implement issue #{issue}")
        } else {
            head_subject.to_owned()
        }
    } else {
        persisted.to_owned()
    };
    let title = if title.starts_with(&prefix) {
        title
    } else {
        format!("{prefix}{title}")
    };
    let title = redact_outbound(&title).replace(['\r', '\n'], " ");
    if title.contains("[content truncated") || title.chars().count() > 256 {
        format!("{prefix}Implement issue #{issue}")
    } else {
        title
    }
}

fn append_section(parts: &mut Vec<String>, heading: &str, body: &str) {
    if !body.trim().is_empty() {
        parts.extend([
            format!("## {heading}"),
            String::new(),
            body.trim().to_owned(),
            String::new(),
        ]);
    }
}

fn validate_mermaid(text: &str, from_markdown: bool) -> Result<(), Vec<&'static str>> {
    let markdown = from_markdown || first_content_is_mermaid_fence(text);
    let fences = if markdown {
        mermaid_fences(text)
    } else {
        vec![text.to_owned()]
    };
    let mut reasons = Vec::new();
    for fence in fences {
        validate_fence(&fence, &mut reasons);
    }
    let mut unique = Vec::new();
    for reason in reasons {
        if !unique.contains(&reason) {
            unique.push(reason);
        }
    }
    if unique.is_empty() {
        Ok(())
    } else {
        Err(unique)
    }
}

fn first_content_is_mermaid_fence(text: &str) -> bool {
    text.lines()
        .find(|line| {
            let stripped = line.trim();
            !stripped.is_empty() && !stripped.starts_with("%%")
        })
        .and_then(|line| FENCE_RE.captures(line))
        .is_some_and(|captures| captures[3].trim() == "mermaid")
}

fn mermaid_fences(text: &str) -> Vec<String> {
    let mut fences = Vec::new();
    let mut current = Vec::new();
    let mut outer: Option<(usize, bool)> = None;
    for line in text.lines() {
        if let Some(captures) = FENCE_RE.captures(line) {
            let length = captures[2].len();
            let rest = captures[3].trim();
            match outer {
                None => {
                    outer = Some((length, rest == "mermaid"));
                    current.clear();
                }
                Some((opening, mermaid)) if length >= opening && rest.is_empty() => {
                    if mermaid && !current.is_empty() {
                        fences.push(current.join("\n"));
                    }
                    current.clear();
                    outer = None;
                }
                Some(_) => {}
            }
        } else if outer.is_some_and(|(_, mermaid)| mermaid) {
            current.push(line);
        }
    }
    if outer.is_some_and(|(_, mermaid)| mermaid) && !current.is_empty() {
        fences.push(current.join("\n"));
    }
    fences
}

fn validate_fence(body: &str, reasons: &mut Vec<&'static str>) {
    let mut frontmatter = false;
    let mut frontmatter_started = false;
    let mut first = None;
    for (index, line) in body.lines().enumerate() {
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
        reasons.push(UNCLOSED_FRONTMATTER);
        return;
    }
    let Some(start) = first else { return };
    let first_line = body.lines().nth(start).unwrap_or_default().trim();
    if first_line == "flowchart"
        || first_line == "graph"
        || first_line.starts_with("flowchart ")
        || first_line.starts_with("graph ")
    {
        if body.lines().skip(start).any(flowchart_rejects_pipe) {
            reasons.push(PIPE_IN_NODE);
        }
    } else if first_line == "sequenceDiagram" {
        for line in body.lines().skip(start) {
            let lower = line.trim().to_ascii_lowercase();
            if !(lower.starts_with("participant ") || lower.starts_with("actor ")) {
                continue;
            }
            let Some(index) = lower.find(" as ") else {
                continue;
            };
            let alias = &line.trim()[index + 4..];
            if alias.to_ascii_lowercase().contains("<br>")
                || alias.to_ascii_lowercase().contains("<br/>")
                || alias.to_ascii_lowercase().contains("<br />")
            {
                reasons.push(BR_IN_ALIAS);
            }
            if alias.contains('$') {
                reasons.push(DOLLAR_IN_ALIAS);
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

#[cfg(test)]
mod tests {
    use super::{ShipPrBody, compose_ship_pr_body, ship_pr_title};

    fn input<'a>(mermaid: &'a str) -> ShipPrBody<'a> {
        ShipPrBody {
            summary: "- Ship the Rust driver.\n",
            mermaid,
            test_plan: "- [x] `cargo test`\n",
            architectural_invariants_note: "No invariant violations.",
            architectural_guidelines_note: "No guideline deviations.",
            deferred_inventory: "",
            issue_number: 8626,
            partial: false,
        }
    }

    #[test]
    fn body_preserves_sections_footer_and_redaction() {
        let mut body = input("flowchart TD\n  A[driver] --> B[PR]");
        body.deferred_inventory = "## Deferred plan items\n\n- `later`\n";
        let rendered = compose_ship_pr_body(&body).expect("body");
        assert!(rendered.starts_with("- Ship the Rust driver.\n\n## Architectural invariants"));
        assert!(rendered.contains("```mermaid\nflowchart TD"));
        assert!(rendered.contains("## Deferred plan items"));
        assert!(rendered.ends_with("Closes #8626\n"));

        let secret = ["ghp", "_123456789012345678901234567890"].concat();
        let mut redacted = input("");
        redacted.summary = &secret;
        assert!(
            compose_ship_pr_body(&redacted)
                .expect("redacted")
                .contains("<REDACTED-TOKEN>")
        );
    }

    #[test]
    fn unsafe_mermaid_is_rejected_in_raw_and_markdown_forms() {
        let error = compose_ship_pr_body(&input("flowchart TD\n  A[bad | label]"))
            .expect_err("pipe rejected");
        assert_eq!(error, "mermaid fragment rejected: pipe-in-node-label");
        let error = compose_ship_pr_body(&input(
            "```mermaid\nsequenceDiagram\nparticipant A as Cost $5<br/>\n```",
        ))
        .expect_err("alias rejected");
        assert!(error.contains("br-in-participant-alias,dollar-in-participant-alias"));
    }

    #[test]
    fn title_is_prefixed_once_and_has_a_fallback() {
        assert_eq!(
            ship_pr_title(7, "", "Implement parity"),
            "Fixes #7: Implement parity"
        );
        assert_eq!(
            ship_pr_title(7, "Fixes #7: Existing", "ignored"),
            "Fixes #7: Existing"
        );
        assert_eq!(ship_pr_title(7, "", ""), "Fixes #7: Implement issue #7");
        let secret = ["ghp", "_123456789012345678901234567890"].concat();
        assert_eq!(
            ship_pr_title(7, "", &format!("unsafe\n{secret}")),
            "Fixes #7: unsafe <REDACTED-TOKEN>"
        );
        assert_eq!(
            ship_pr_title(7, &"x".repeat(300), ""),
            "Fixes #7: Implement issue #7"
        );
    }
}
