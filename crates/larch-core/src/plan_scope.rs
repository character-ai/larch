//! The `## Files to modify/create` scope grammar shared by plan consumers.
//!
//! Ports Python `larch.issue.issue_wire.extract_scope_paths` over the heading
//! events of `larch.design.plan_grammar`. Two commands read the same plan the
//! same way — `plan scope-paths` publishes the list and `dirty-tree
//! scope-check` compares a touched-path set against it — so the grammar has one
//! owner here rather than a copy behind each command.
//!
//! Markers inside balanced code fences are examples and never contribute a
//! path, matching every other larch plan reader.

/// The path a plan with no recognized scope heading falls back to.
///
/// A plan that names no file still has to bound a scope, and `/design` edits
/// its own skill surface more often than any other path, so an empty result
/// reads as that single file rather than as "every path is in scope".
pub const SCOPE_PATH_FALLBACK: &str = "skills/design/SKILL.md";

/// Return the ordered, deduplicated scope paths a plan declares.
///
/// Paths are collected from the recognized `### NEW:` / `### UPDATED:` /
/// `### REWRITTEN:` / `### MAY_UPDATE:` headings inside the
/// `## Files to modify` section, or from the whole plan when it declares no
/// such section. A `+`-prefixed candidate is a diff marker, not a path. The
/// result is never empty: it falls back to [`SCOPE_PATH_FALLBACK`].
#[must_use]
pub fn extract_scope_paths(plan: &str) -> Vec<String> {
    let paths = collect_scope_paths(plan, true);
    if paths.is_empty() {
        vec![SCOPE_PATH_FALLBACK.to_owned()]
    } else {
        paths
    }
}

/// Return only the firm scope paths a plan declares, with no fallback.
///
/// `### MAY_UPDATE:` names an optional path, so plan-coverage attribution — which
/// judges whether declared work landed — excludes it and reports an empty result
/// for a plan that declares no firm path rather than substituting
/// [`SCOPE_PATH_FALLBACK`]. Ports Python `extract_scope_paths(use_fallback=False,
/// include_optional=False)`.
#[must_use]
pub fn extract_firm_scope_paths(plan: &str) -> Vec<String> {
    collect_scope_paths(plan, false)
}

fn collect_scope_paths(plan: &str, include_optional: bool) -> Vec<String> {
    let lines = visible_plan_lines(plan);
    let has_scope_section = lines
        .iter()
        .any(|line| is_generic_level_two(line) && is_scope_heading(line));
    let mut in_section = !has_scope_section;
    let mut paths = Vec::new();
    for line in lines {
        if is_scope_heading(line) {
            in_section = true;
            continue;
        }
        if in_section && let Some((kind, tail)) = recognized_heading(line) {
            if kind == "MAY_UPDATE" && !include_optional {
                continue;
            }
            for candidate in heading_paths(tail) {
                if !candidate.starts_with('+') && !paths.contains(&candidate) {
                    paths.push(candidate);
                }
            }
            continue;
        }
        if has_scope_section && in_section && is_generic_level_two(line) {
            break;
        }
    }
    paths
}

fn visible_plan_lines(text: &str) -> Vec<&str> {
    let lines = text.lines().collect::<Vec<_>>();
    let mut hidden = vec![false; lines.len()];
    let mut opener: Option<(usize, char, usize)> = None;
    for (index, line) in lines.iter().enumerate() {
        let Some((marker, suffix)) = fence_marker(line) else {
            continue;
        };
        let character = marker.as_bytes()[0] as char;
        let length = marker.len();
        match opener {
            None => opener = Some((index, character, length)),
            Some((open_index, open_character, open_length))
                if character == open_character
                    && length >= open_length
                    && suffix.trim().is_empty() =>
            {
                for value in &mut hidden[open_index + 1..index] {
                    *value = true;
                }
                opener = None;
            }
            Some(_) => {}
        }
    }
    lines
        .into_iter()
        .enumerate()
        .filter_map(|(index, line)| {
            (!hidden[index] && fence_marker(line).is_none()).then_some(line)
        })
        .collect()
}

fn fence_marker(line: &str) -> Option<(&str, &str)> {
    let trimmed = line.trim();
    let first = *trimmed.as_bytes().first()?;
    if !matches!(first, b'`' | b'~') {
        return None;
    }
    let length = trimmed.bytes().take_while(|byte| *byte == first).count();
    (length >= 3).then_some((&trimmed[..length], &trimmed[length..]))
}

fn is_scope_heading(line: &str) -> bool {
    let Some(rest) = line.strip_prefix("##") else {
        return false;
    };
    let Some(first) = rest.chars().next() else {
        return false;
    };
    if !first.is_whitespace() {
        return false;
    }
    matches!(
        rest.split_whitespace().collect::<Vec<_>>().as_slice(),
        ["Files", "to", "modify" | "modify/create"]
    )
}

fn is_generic_level_two(line: &str) -> bool {
    let Some(rest) = line.strip_prefix("##") else {
        return false;
    };
    rest.is_empty() || rest.starts_with([' ', '\t'])
}

fn recognized_heading(line: &str) -> Option<(&'static str, &str)> {
    let rest = line
        .strip_prefix("###")
        .or_else(|| line.strip_prefix("##"))?;
    let leading = rest.trim_start_matches([' ', '\t']);
    if leading.len() == rest.len() {
        return None;
    }
    let (kind, after_kind) = ["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"]
        .into_iter()
        .find_map(|kind| leading.strip_prefix(kind).map(|tail| (kind, tail)))?;
    recognized_heading_tail(after_kind).map(|tail| (kind, tail))
}

fn recognized_heading_tail(after_kind: &str) -> Option<&str> {
    if let Some(tail) = after_kind.strip_prefix(':') {
        let path = tail.trim_matches([' ', '\t']);
        return (!path.is_empty()).then_some(path);
    }
    let separated = after_kind.trim_start_matches([' ', '\t']);
    if separated.len() == after_kind.len() {
        return None;
    }
    if let Some(tail) = separated.strip_prefix(':') {
        let path = tail.trim_matches([' ', '\t']);
        return (!path.is_empty()).then_some(path);
    }
    let bracket = separated.strip_prefix('[')?;
    let closing = bracket.find(']')?;
    let path = bracket[..closing].trim_matches([' ', '\t']);
    let suffix = bracket[closing + 1..].trim_matches([' ', '\t']);
    (!path.is_empty() && (suffix.is_empty() || suffix == ":")).then_some(path)
}

fn heading_paths(tail: &str) -> Vec<String> {
    let mut paths = backtick_paths(tail);
    if paths.is_empty() {
        let candidate = tail
            .split_whitespace()
            .next()
            .map_or("", |value| {
                value.split_once('(').map_or(value, |(before, _)| before)
            })
            .trim();
        if !candidate.is_empty() {
            paths.push(candidate.to_owned());
        }
    }
    paths
}

fn backtick_paths(tail: &str) -> Vec<String> {
    let mut paths = Vec::new();
    let mut remainder = tail;
    while let Some(open) = remainder.find('`') {
        let after_open = &remainder[open + 1..];
        let Some(close) = after_open.find('`') else {
            break;
        };
        let value = after_open[..close].trim();
        if !value.is_empty() {
            paths.push(value.to_owned());
        }
        remainder = &after_open[close + 1..];
    }
    paths
}

#[cfg(test)]
mod tests {
    use super::{SCOPE_PATH_FALLBACK, extract_firm_scope_paths, extract_scope_paths};

    #[test]
    fn a_scope_section_bounds_collection_and_stops_at_the_next_section() {
        let plan = concat!(
            "### NEW: `before/section.rs`\n",
            "## Files to modify\n",
            "### NEW: `a.rs`\n",
            "### UPDATED: `b.rs` and notes\n",
            "### MAY_UPDATE: c.rs (optional)\n",
            "## Tests\n",
            "### NEW: `after/section.rs`\n",
        );

        assert_eq!(
            extract_scope_paths(plan),
            vec![
                "a.rs".to_owned(),
                "b.rs".to_owned(),
                "c.rs".to_owned(),
                // The bracket form and the `+` diff marker are covered below.
            ]
        );
    }

    #[test]
    fn without_a_scope_section_every_recognized_heading_contributes() {
        let plan = concat!(
            "### REWRITTEN: [`x.rs`]:\n",
            "### NEW: +not-a-path\n",
            "### NEW: `x.rs`\n",
        );

        assert_eq!(extract_scope_paths(plan), vec!["x.rs".to_owned()]);
    }

    #[test]
    fn fenced_headings_are_examples_and_a_pathless_plan_falls_back() {
        let plan = concat!("```\n", "### NEW: `fenced.rs`\n", "```\n", "prose only\n");

        assert_eq!(
            extract_scope_paths(plan),
            vec![SCOPE_PATH_FALLBACK.to_owned()]
        );
    }

    #[test]
    fn firm_extraction_drops_optional_headings_and_never_falls_back() {
        let plan = concat!(
            "## Files to modify\n",
            "### NEW: `a.rs`\n",
            "### MAY_UPDATE: `optional.rs`\n",
        );

        assert_eq!(extract_firm_scope_paths(plan), vec!["a.rs".to_owned()]);
        assert!(extract_firm_scope_paths("### MAY_UPDATE: `only.rs`\n").is_empty());
        assert!(extract_firm_scope_paths("prose only\n").is_empty());
    }
}
