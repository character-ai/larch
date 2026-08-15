//! Normative plan heading and trailer grammar.
//!
//! Ports `python/larch/design/plan_grammar.py`. Heading and trailer syntax plus
//! the executable-plan contract (M1 shape facets and M2 repository-scope path
//! checks) live here. Callers keep policy decisions such as whether an
//! operator-authored oversize override is trusted.

use crate::{balanced_fence_line_indices, glob_matches, trim_python_whitespace};
use regex::Regex;
use std::{
    collections::{BTreeSet, HashSet},
    path::{Component, Path},
    sync::LazyLock,
};

/// Plan heading kinds accepted by the grammar.
pub const HEADING_KINDS: [&str; 4] = ["NEW", "UPDATED", "REWRITTEN", "MAY_UPDATE"];
/// Firm (non-optional) heading kinds.
pub const FIRM_HEADING_KINDS: [&str; 3] = ["NEW", "UPDATED", "REWRITTEN"];
/// Canonical trailer keys in composition order.
pub const TRAILER_KEYS: [&str; 8] = [
    "review_status",
    "rounds_completed",
    "difficulty",
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
    "diff_lines",
];
/// Optional size trailers that may appear above `diff_lines`.
pub const OPTIONAL_SIZE_TRAILER_KEYS: [&str; 4] = [
    "diff_added",
    "diff_deleted",
    "mechanical_churn",
    "oversize_override",
];
/// Alias for the canonical trailer composition order.
pub const CANONICAL_TRAILER_ORDER: [&str; 8] = TRAILER_KEYS;

/// M1 shape defect tokens in emission order.
pub const M1_DEFECT_TOKENS: [&str; 8] = [
    "missing-plan-block",
    "multiple-plan-blocks",
    "missing-firm-scope",
    "missing-ordered-implementation",
    "missing-acceptance",
    "missing-closed-decisions",
    "missing-breaking-migration",
    "missing-diff-lines",
];
/// M2 repository-scope defect tokens in emission order.
pub const M2_DEFECT_TOKENS: [&str; 4] = [
    "empty-plan-glob",
    "missing-updated-plan-path",
    "existing-new-plan-path",
    "unsafe-plan-path",
];
/// Combined defect order used by validation results.
pub const PLAN_DEFECT_ORDER: [&str; 12] = [
    "missing-plan-block",
    "multiple-plan-blocks",
    "missing-firm-scope",
    "missing-ordered-implementation",
    "missing-acceptance",
    "missing-closed-decisions",
    "missing-breaking-migration",
    "missing-diff-lines",
    "empty-plan-glob",
    "missing-updated-plan-path",
    "existing-new-plan-path",
    "unsafe-plan-path",
];
/// Operator-facing `--force` contract error string.
pub const FORCE_PLAN_CONTRACT_ERROR: &str = concat!(
    "ERROR: --force can skip semantic plan review, but it cannot run without ",
    "a valid issue-body larch:plan block"
);

static HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^(?P<level>##|###)[ \t]+(?P<kind>NEW|UPDATED|REWRITTEN|MAY_UPDATE)(?:[ \t]*:[ \t]*(?P<colon>.+?)|[ \t]+\[(?P<bracket>[^]\r\n]+)\][ \t]*:?)[ \t]*$",
    )
    .expect("heading regex")
});
static TRAILER_LINE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r"^(?P<key>review_status|rounds_completed|difficulty|diff_added|diff_deleted|mechanical_churn|oversize_override|diff_lines): (?P<value>[^\r\n]+)$",
    )
    .expect("trailer regex")
});
static SIZE_INTEGER_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?:0[0-7]*|[1-9][0-9]*)").expect("size integer regex"));
static DIGITS_RE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"[0-9]+").expect("digits regex"));
static SECTION_HEADING_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(#{2,3})[ \t]+(.+?)[ \t]*$").expect("section heading regex"));
static NUMBERED_STEP_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*\d+\.[ \t]+\S").expect("numbered step regex"));
static CLOSED_DECISIONS_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^closed[ \t]+decisions(?:[ \t]+and[ \t]+ownership)?$")
        .expect("closed decisions regex")
});
static ORDERED_IMPLEMENTATION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^ordered[ \t]+implementation$").expect("ordered implementation regex")
});
static ACCEPTANCE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)^acceptance$").expect("acceptance regex"));
static BREAKING_MIGRATION_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^breaking[ \t]+changes[ \t]+and[ \t]+migration$")
        .expect("breaking migration regex")
});
static BACKTICK_PATH_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"`([^`]+)`").expect("backtick path regex"));
static PAREN_SUFFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\(.*$").expect("paren suffix regex"));

/// One accepted heading kind.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HeadingKind {
    New,
    Updated,
    Rewritten,
    MayUpdate,
}

impl HeadingKind {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::New => "NEW",
            Self::Updated => "UPDATED",
            Self::Rewritten => "REWRITTEN",
            Self::MayUpdate => "MAY_UPDATE",
        }
    }

    /// Whether this heading is firm scope.
    #[must_use]
    pub const fn firm(self) -> bool {
        matches!(self, Self::New | Self::Updated | Self::Rewritten)
    }

    fn parse(raw: &str) -> Option<Self> {
        match raw {
            "NEW" => Some(Self::New),
            "UPDATED" => Some(Self::Updated),
            "REWRITTEN" => Some(Self::Rewritten),
            "MAY_UPDATE" => Some(Self::MayUpdate),
            _ => None,
        }
    }
}

/// One accepted trailer key.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum TrailerKey {
    ReviewStatus,
    RoundsCompleted,
    Difficulty,
    DiffAdded,
    DiffDeleted,
    MechanicalChurn,
    OversizeOverride,
    DiffLines,
}

impl TrailerKey {
    /// Stable wire token.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ReviewStatus => "review_status",
            Self::RoundsCompleted => "rounds_completed",
            Self::Difficulty => "difficulty",
            Self::DiffAdded => "diff_added",
            Self::DiffDeleted => "diff_deleted",
            Self::MechanicalChurn => "mechanical_churn",
            Self::OversizeOverride => "oversize_override",
            Self::DiffLines => "diff_lines",
        }
    }

    fn parse(raw: &str) -> Option<Self> {
        match raw {
            "review_status" => Some(Self::ReviewStatus),
            "rounds_completed" => Some(Self::RoundsCompleted),
            "difficulty" => Some(Self::Difficulty),
            "diff_added" => Some(Self::DiffAdded),
            "diff_deleted" => Some(Self::DiffDeleted),
            "mechanical_churn" => Some(Self::MechanicalChurn),
            "oversize_override" => Some(Self::OversizeOverride),
            "diff_lines" => Some(Self::DiffLines),
            _ => None,
        }
    }
}

/// Typed trailer value after grammar validation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TrailerValue {
    Text(String),
    Int(i64),
    Bool(bool),
}

/// One accepted whole-line plan heading.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HeadingMatch {
    /// Heading kind.
    pub kind: HeadingKind,
    /// Path token from the heading.
    pub path: String,
    /// Markdown heading level (`2` or `3`).
    pub level: u8,
    /// 1-based source line number.
    pub line_number: usize,
}

impl HeadingMatch {
    /// Whether this heading is firm scope.
    #[must_use]
    pub const fn firm(&self) -> bool {
        self.kind.firm()
    }
}

/// One non-fenced heading event, recognized or generic level-two.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HeadingEvent {
    /// 1-based source line number.
    pub line_number: usize,
    /// Raw line text.
    pub text: String,
    /// Recognized heading when present.
    pub heading: Option<HeadingMatch>,
    /// Whether the line is a generic `##` heading.
    pub generic_level_two: bool,
}

/// One typed whole-line trailer match.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TrailerMatch {
    /// Trailer key.
    pub key: TrailerKey,
    /// Raw value text.
    pub value: String,
    /// Parsed typed value.
    pub parsed_value: TrailerValue,
}

/// Final contiguous trailer block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanTrailers {
    /// Raw trailer lines in document order.
    pub lines: Vec<String>,
    /// Typed matches in document order.
    pub matches: Vec<TrailerMatch>,
    /// 1-based start line of the trailer block.
    pub start_line: usize,
    /// Duplicate keys retained for consumer policy.
    pub duplicates: Vec<TrailerKey>,
}

impl PlanTrailers {
    /// Last match for `key`, if any.
    #[must_use]
    pub fn get(&self, key: TrailerKey) -> Option<&TrailerMatch> {
        self.matches.iter().rev().find(|item| item.key == key)
    }

    /// Terminal `diff_lines` integer when present and typed.
    #[must_use]
    pub fn diff_lines(&self) -> Option<i64> {
        match self
            .get(TrailerKey::DiffLines)
            .map(|item| &item.parsed_value)
        {
            Some(TrailerValue::Int(value)) => Some(*value),
            _ => None,
        }
    }
}

/// Frozen executable-plan validation outcome with ordered defect tokens.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanValidationResult {
    /// Ordered defect tokens.
    pub defects: Vec<&'static str>,
}

impl PlanValidationResult {
    /// Whether validation found no defects.
    #[must_use]
    pub const fn ok(&self) -> bool {
        self.defects.is_empty()
    }
}

/// Return whether a line is a Markdown fence marker.
#[must_use]
pub fn is_fence_marker(line: &str) -> bool {
    fence_marker(trim_python_whitespace(line)).is_some()
}

/// Match one accepted whole-line plan heading.
#[must_use]
pub fn match_heading(line: &str, line_number: usize) -> Option<HeadingMatch> {
    let trimmed = line.trim_end_matches(['\r', '\n']);
    let captures = HEADING_RE.captures(trimmed)?;
    if captures.get(0)?.as_str() != trimmed {
        return None;
    }
    let path = captures
        .name("colon")
        .or_else(|| captures.name("bracket"))
        .map(|value| value.as_str().trim())
        .unwrap_or_default();
    if path.is_empty() {
        return None;
    }
    Some(HeadingMatch {
        kind: HeadingKind::parse(captures.name("kind")?.as_str())?,
        path: path.to_owned(),
        level: u8::try_from(captures.name("level")?.as_str().len()).unwrap_or(0),
        line_number,
    })
}

/// Yield non-fenced heading events, with recognized headings taking precedence.
#[must_use]
pub fn iter_heading_events(text: &str) -> Vec<HeadingEvent> {
    let lines: Vec<&str> = text.lines().collect();
    let fenced = balanced_fence_line_indices(&lines);
    let mut events = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        if fenced.contains(&index) || is_fence_marker(line) {
            continue;
        }
        let line_number = index + 1;
        let heading = match_heading(line, line_number);
        let generic_level_two = heading.is_none() && is_generic_level_two(line);
        events.push(HeadingEvent {
            line_number,
            text: (*line).to_owned(),
            heading,
            generic_level_two,
        });
    }
    events
}

/// Iterate recognized plan headings, optionally filtered by kind.
#[must_use]
pub fn iter_plan_headings(text: &str, kinds: Option<&[HeadingKind]>) -> Vec<HeadingMatch> {
    iter_heading_events(text)
        .into_iter()
        .filter_map(|event| event.heading)
        .filter(|heading| kinds.is_none_or(|allowed| allowed.contains(&heading.kind)))
        .collect()
}

/// Iterate firm (non-optional) plan headings.
#[must_use]
pub fn iter_firm_headings(text: &str) -> Vec<HeadingMatch> {
    iter_plan_headings(
        text,
        Some(&[
            HeadingKind::New,
            HeadingKind::Updated,
            HeadingKind::Rewritten,
        ]),
    )
}

/// Return a typed whole-line trailer match, or `None` for malformed input.
#[must_use]
pub fn match_trailer_line(line: &str) -> Option<TrailerMatch> {
    let trimmed = line.trim_end_matches(['\r', '\n']);
    let captures = TRAILER_LINE_RE.captures(trimmed)?;
    if captures.get(0)?.as_str() != trimmed {
        return None;
    }
    let key = TrailerKey::parse(captures.name("key")?.as_str())?;
    let value = captures.name("value")?.as_str().to_owned();
    let parsed_value = parse_trailer_value(key, &value)?;
    Some(TrailerMatch {
        key,
        value,
        parsed_value,
    })
}

/// Scan the whole document for valid trailer lines.
#[must_use]
pub fn iter_trailer_lines(text: &str, keys: Option<&[TrailerKey]>) -> Vec<TrailerMatch> {
    text.lines()
        .filter_map(match_trailer_line)
        .filter(|item| keys.is_none_or(|allowed| allowed.contains(&item.key)))
        .collect()
}

/// Parse the final contiguous valid trailer block.
#[must_use]
pub fn parse_final_trailers(text: &str, require_diff_lines: bool) -> PlanTrailers {
    let mut lines: Vec<&str> = text.lines().collect();
    while lines.last().is_some_and(|line| line.trim().is_empty()) {
        lines.pop();
    }
    let mut matches = Vec::new();
    let mut raw_lines = Vec::new();
    for line in lines.iter().rev() {
        let Some(item) = match_trailer_line(line) else {
            break;
        };
        matches.push(item);
        raw_lines.push((*line).to_owned());
    }
    matches.reverse();
    raw_lines.reverse();
    let mut seen = HashSet::new();
    let mut duplicates = Vec::new();
    for item in &matches {
        if !seen.insert(item.key) && !duplicates.contains(&item.key) {
            duplicates.push(item.key);
        }
    }
    let start_line = if matches.is_empty() {
        lines.len() + 1
    } else {
        lines.len() - matches.len() + 1
    };
    let result = PlanTrailers {
        lines: raw_lines,
        matches,
        start_line,
        duplicates,
    };
    if require_diff_lines
        && (result.matches.is_empty()
            || result.matches.last().map(|item| item.key) != Some(TrailerKey::DiffLines))
    {
        return PlanTrailers {
            lines: Vec::new(),
            matches: Vec::new(),
            start_line: lines.len() + 1,
            duplicates: Vec::new(),
        };
    }
    result
}

/// Return the terminal `diff_lines` value when the final trailer block ends with it.
#[must_use]
pub fn terminal_diff_lines(text: &str) -> Option<i64> {
    parse_final_trailers(text, true).diff_lines()
}

/// Compose validated trailers in canonical order.
///
/// # Errors
///
/// Returns when a supplied value fails trailer grammar validation.
pub fn compose_trailer_lines(values: &[(TrailerKey, TrailerValue)]) -> Result<Vec<String>, String> {
    let mut rendered = Vec::new();
    for key in CANONICAL_TRAILER_ORDER
        .iter()
        .filter_map(|name| TrailerKey::parse(name))
    {
        let Some((_, value)) = values.iter().find(|(item, _)| *item == key) else {
            continue;
        };
        let token = match value {
            TrailerValue::Bool(flag) => {
                if *flag {
                    "true".to_owned()
                } else {
                    "false".to_owned()
                }
            }
            TrailerValue::Int(number) => number.to_string(),
            TrailerValue::Text(text) => text.clone(),
        };
        let line = format!("{}: {token}", key.as_str());
        let Some(matched) = match_trailer_line(&line) else {
            return Err(format!("invalid {} trailer value", key.as_str()));
        };
        rendered.push(format!("{}: {}", key.as_str(), matched.value));
    }
    Ok(rendered)
}

/// Return compact drafting guidance from the shared registries.
#[must_use]
pub fn grammar_prompt() -> String {
    let kinds = HEADING_KINDS
        .iter()
        .map(|kind| format!("`### {kind}:`"))
        .collect::<Vec<_>>()
        .join(", ");
    let optional = OPTIONAL_SIZE_TRAILER_KEYS
        .iter()
        .map(|key| format!("`{key}: <value>`"))
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "Use per-file headings {kinds}. Include non-empty \
         `## Closed decisions and ownership`, `## Acceptance`, and \
         `## Breaking changes and migration` sections. Include \
         `## Ordered implementation` with at least one numbered step. End with \
         `difficulty: <TRIVIAL|MODERATE|HARD>`, optional {optional}, and \
         terminal `diff_lines: <N>`."
    )
}

/// Validate executable-plan M1 shape facets without repository path checks.
#[must_use]
pub fn validate_plan_facets(plan_text: &str) -> PlanValidationResult {
    PlanValidationResult {
        defects: ordered_defects(&m1_facet_defects(plan_text)),
    }
}

/// Validate executable-plan facets and repository-scope paths.
///
/// Callers inject `tracked_paths` so the core stays free of Git process
/// spawning. Filesystem checks stay confined under `repo_root`.
#[must_use]
pub fn validate_plan_contract(
    plan_text: &str,
    repo_root: &Path,
    tracked_paths: &HashSet<String, impl std::hash::BuildHasher>,
) -> PlanValidationResult {
    let mut found = m1_facet_defects(plan_text);
    found.extend(m2_path_defects(plan_text, repo_root, tracked_paths));
    PlanValidationResult {
        defects: ordered_defects(&found),
    }
}

fn parse_trailer_value(key: TrailerKey, value: &str) -> Option<TrailerValue> {
    match key {
        TrailerKey::RoundsCompleted | TrailerKey::DiffLines => {
            if DIGITS_RE.find(value).map(|m| m.as_str()) == Some(value) {
                value.parse::<i64>().ok().map(TrailerValue::Int)
            } else {
                None
            }
        }
        TrailerKey::DiffAdded | TrailerKey::DiffDeleted => {
            if SIZE_INTEGER_RE.find(value).map(|m| m.as_str()) != Some(value) {
                return None;
            }
            let parsed = if value.len() > 1 && value.starts_with('0') {
                i64::from_str_radix(value, 8).ok()?
            } else {
                value.parse::<i64>().ok()?
            };
            Some(TrailerValue::Int(parsed))
        }
        TrailerKey::Difficulty => {
            if matches!(value, "TRIVIAL" | "MODERATE" | "HARD") {
                Some(TrailerValue::Text(value.to_owned()))
            } else {
                None
            }
        }
        TrailerKey::MechanicalChurn => match value {
            "true" => Some(TrailerValue::Bool(true)),
            "false" => Some(TrailerValue::Bool(false)),
            _ => None,
        },
        TrailerKey::OversizeOverride => {
            if value == "operator" {
                Some(TrailerValue::Text(value.to_owned()))
            } else {
                None
            }
        }
        TrailerKey::ReviewStatus => {
            if value.trim().is_empty() {
                None
            } else {
                Some(TrailerValue::Text(value.to_owned()))
            }
        }
    }
}

fn ordered_defects(found: &BTreeSet<&'static str>) -> Vec<&'static str> {
    PLAN_DEFECT_ORDER
        .iter()
        .copied()
        .filter(|token| found.contains(token))
        .collect()
}

fn section_title(line: &str) -> Option<(usize, String)> {
    let trimmed = line.trim_end_matches(['\r', '\n']);
    let captures = SECTION_HEADING_RE.captures(trimmed)?;
    if captures.get(0)?.as_str() != trimmed {
        return None;
    }
    Some((
        captures.get(1)?.as_str().len(),
        captures.get(2)?.as_str().trim().to_owned(),
    ))
}

fn iter_section_bodies(text: &str) -> Vec<(String, Vec<String>)> {
    let lines: Vec<&str> = text.lines().collect();
    let fenced = balanced_fence_line_indices(&lines);
    let mut headings = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        if fenced.contains(&index) || is_fence_marker(line) {
            continue;
        }
        if let Some((level, title)) = section_title(line) {
            headings.push((index, level, title));
        }
    }
    let mut bodies = Vec::new();
    for (position, (index, level, title)) in headings.iter().enumerate() {
        let mut end = lines.len();
        for (later_index, later_level, _) in headings.iter().skip(position + 1) {
            if *later_level <= *level {
                end = *later_index;
                break;
            }
        }
        let body = lines[*index + 1..end]
            .iter()
            .map(|line| (*line).to_owned())
            .collect();
        bodies.push((title.clone(), body));
    }
    bodies
}

fn body_nonempty(body: &[String]) -> bool {
    body.iter().any(|line| !line.trim().is_empty())
}

fn heading_path_token(raw: &str) -> String {
    let stripped = raw.trim();
    if let Some(captures) = BACKTICK_PATH_RE.captures(stripped) {
        return captures
            .get(1)
            .map(|m| m.as_str().trim().to_owned())
            .unwrap_or_default();
    }
    let Some(first) = stripped.split_whitespace().next() else {
        return String::new();
    };
    PAREN_SUFFIX_RE.replace(first, "").trim().to_owned()
}

fn section_has_numbered_step(body: &[String]) -> bool {
    body.iter().any(|line| NUMBERED_STEP_RE.is_match(line))
}

fn m1_section_flags(plan_text: &str) -> (bool, bool, bool, bool) {
    let mut closed_ok = false;
    let mut ordered_ok = false;
    let mut acceptance_ok = false;
    let mut breaking_ok = false;
    for (title, body) in iter_section_bodies(plan_text) {
        if CLOSED_DECISIONS_RE.is_match(&title) && body_nonempty(&body) {
            closed_ok = true;
        }
        if ORDERED_IMPLEMENTATION_RE.is_match(&title) && section_has_numbered_step(&body) {
            ordered_ok = true;
        }
        if ACCEPTANCE_RE.is_match(&title) && body_nonempty(&body) {
            acceptance_ok = true;
        }
        if BREAKING_MIGRATION_RE.is_match(&title) && body_nonempty(&body) {
            breaking_ok = true;
        }
    }
    (closed_ok, ordered_ok, acceptance_ok, breaking_ok)
}

fn m1_facet_defects(plan_text: &str) -> BTreeSet<&'static str> {
    let mut defects = BTreeSet::new();
    if iter_firm_headings(plan_text).is_empty() {
        defects.insert("missing-firm-scope");
    }
    let (closed_ok, ordered_ok, acceptance_ok, breaking_ok) = m1_section_flags(plan_text);
    if !closed_ok {
        defects.insert("missing-closed-decisions");
    }
    if !ordered_ok {
        defects.insert("missing-ordered-implementation");
    }
    if !acceptance_ok {
        defects.insert("missing-acceptance");
    }
    if !breaking_ok {
        defects.insert("missing-breaking-migration");
    }
    if parse_final_trailers(plan_text, true).diff_lines().is_none() {
        defects.insert("missing-diff-lines");
    }
    defects
}

fn is_glob_path(path: &str) -> bool {
    path.contains(['*', '?', '['])
}

fn path_has_unsafe_shape(path: &str) -> bool {
    if path.is_empty() || path.trim() != path {
        return true;
    }
    if path.starts_with('~') {
        return true;
    }
    let candidate = Path::new(path);
    if candidate.is_absolute() {
        return true;
    }
    let mut components = candidate.components();
    match components.next() {
        None | Some(Component::ParentDir) => return true,
        _ => {}
    }
    candidate
        .components()
        .any(|component| matches!(component, Component::ParentDir))
}

fn path_inside_repo(repo_root: &Path, path: &Path) -> bool {
    let Ok(root) = repo_root.canonicalize() else {
        return false;
    };
    let Ok(resolved) = path.canonicalize() else {
        return false;
    };
    resolved == root || resolved.starts_with(&root)
}

fn existing_parents_safe(repo_root: &Path, rel_path: &str) -> bool {
    if !repo_root.is_dir() {
        return false;
    }
    let mut current = repo_root.to_path_buf();
    let parts: Vec<_> = Path::new(rel_path).components().collect();
    if parts.is_empty() {
        return true;
    }
    for part in &parts[..parts.len() - 1] {
        current.push(part);
        if current.is_symlink() || (current.exists() && !current.is_dir()) {
            return false;
        }
        if !current.exists() {
            return true;
        }
        if !path_inside_repo(repo_root, &current) {
            return false;
        }
    }
    true
}

fn glob_matches_tracked(
    pattern: &str,
    tracked: &HashSet<String, impl std::hash::BuildHasher>,
) -> bool {
    tracked.iter().any(|path| {
        fnmatchcase(path, pattern) || (!pattern.contains('[') && glob_matches(path, pattern))
    })
}

fn fnmatchcase(name: &str, pattern: &str) -> bool {
    let name_chars: Vec<char> = name.chars().collect();
    let pattern_chars: Vec<char> = pattern.chars().collect();
    let (mut name_index, mut pattern_index) = (0_usize, 0_usize);
    let (mut star, mut resume) = (None::<usize>, 0_usize);
    while name_index < name_chars.len() {
        if let Some(next) = glob_atom_end(&pattern_chars, pattern_index, name_chars[name_index]) {
            name_index += 1;
            pattern_index = next;
        } else if pattern_chars.get(pattern_index) == Some(&'*') {
            star = Some(pattern_index);
            pattern_index += 1;
            resume = name_index;
        } else if let Some(index) = star {
            pattern_index = index + 1;
            resume += 1;
            name_index = resume;
        } else {
            return false;
        }
    }
    while pattern_chars.get(pattern_index) == Some(&'*') {
        pattern_index += 1;
    }
    pattern_index == pattern_chars.len()
}

fn glob_atom_end(pattern: &[char], index: usize, value: char) -> Option<usize> {
    match pattern.get(index) {
        Some('?') => Some(index + 1),
        Some('[') => match glob_class(pattern, index, value) {
            Some((end, true)) => Some(end),
            Some(_) => None,
            None => (value == '[').then_some(index + 1),
        },
        Some(expected) if *expected == value => Some(index + 1),
        _ => None,
    }
}

fn glob_class(pattern: &[char], index: usize, value: char) -> Option<(usize, bool)> {
    let mut start = index + 1;
    let negated = matches!(pattern.get(start), Some('!' | '^'));
    if negated {
        start += 1;
    }
    let mut cursor = start;
    let mut matched = false;
    while cursor < pattern.len() {
        if pattern[cursor] == ']' && cursor > start {
            return Some((cursor + 1, matched != negated));
        }
        if cursor + 2 < pattern.len() && pattern[cursor + 1] == '-' && pattern[cursor + 2] != ']' {
            let low = pattern[cursor];
            let high = pattern[cursor + 2];
            if (low..=high).contains(&value) {
                matched = true;
            }
            cursor += 3;
            continue;
        }
        if pattern[cursor] == value {
            matched = true;
        }
        cursor += 1;
    }
    None
}

fn m2_path_defects(
    plan_text: &str,
    repo_root: &Path,
    tracked_paths: &HashSet<String, impl std::hash::BuildHasher>,
) -> BTreeSet<&'static str> {
    let mut defects = BTreeSet::new();
    for heading in iter_plan_headings(plan_text, None) {
        let path = heading_path_token(&heading.path);
        if path.is_empty() || path_has_unsafe_shape(&path) {
            defects.insert("unsafe-plan-path");
            continue;
        }
        let leaf = repo_root.join(&path);
        if leaf.is_symlink() && !path_inside_repo(repo_root, &leaf) {
            defects.insert("unsafe-plan-path");
            continue;
        }
        if !existing_parents_safe(repo_root, &path) {
            defects.insert("unsafe-plan-path");
            continue;
        }
        if heading.kind == HeadingKind::New {
            if tracked_paths.contains(&path) || leaf.exists() {
                defects.insert("existing-new-plan-path");
            }
            continue;
        }
        if is_glob_path(&path) {
            if !glob_matches_tracked(&path, tracked_paths) {
                defects.insert("empty-plan-glob");
            }
            continue;
        }
        if !tracked_paths.contains(&path) {
            defects.insert("missing-updated-plan-path");
        }
    }
    defects
}

fn is_generic_level_two(line: &str) -> bool {
    let Some(rest) = line.strip_prefix("##") else {
        return false;
    };
    // Match Python `^##(?:[ \t]+|$)(?!#)` without lookaround: reject `###…`.
    if rest.starts_with('#') {
        return false;
    }
    rest.is_empty() || rest.starts_with([' ', '\t'])
}

fn fence_marker(line: &str) -> Option<(char, usize, &str)> {
    let marker = line.chars().next()?;
    if marker != '`' && marker != '~' {
        return None;
    }
    let length = line
        .chars()
        .take_while(|character| *character == marker)
        .count();
    if length < 3 {
        return None;
    }
    Some((marker, length, &line[length..]))
}

#[cfg(test)]
mod tests {
    use super::{
        FIRM_HEADING_KINDS, HEADING_KINDS, OPTIONAL_SIZE_TRAILER_KEYS, TRAILER_KEYS, TrailerKey,
        TrailerValue, compose_trailer_lines, grammar_prompt, iter_heading_events,
        iter_plan_headings, match_heading, match_trailer_line, parse_final_trailers,
        terminal_diff_lines, validate_plan_contract, validate_plan_facets,
    };
    use std::{collections::HashSet, fs};
    use tempfile::TempDir;

    fn valid_plan(path: &str) -> String {
        format!(
            "## Plan\n\n\
             ### Closed decisions and ownership\n\n\
             - Extend plan_grammar only.\n\n\
             ### Ordered implementation\n\n\
             1. Validate the contract.\n\
             2. Wire callers.\n\n\
             ## Files to modify/create\n\n\
             ### UPDATED: {path}\n\n\
             ## Acceptance\n\n\
             - Contract holds.\n\n\
             ## Breaking changes and migration\n\n\
             Force no longer accepts raw bodies.\n\n\
             diff_lines: 42\n"
        )
    }

    #[test]
    fn all_heading_forms_match() {
        for level in ["##", "###"] {
            for kind in HEADING_KINDS {
                for shape in [
                    format!("{level} {kind}: path/to/file.py"),
                    format!("{level} {kind} [path/to/file.py]"),
                ] {
                    let matched = match_heading(&shape, 0).expect("heading");
                    assert_eq!(matched.kind.as_str(), kind);
                    assert_eq!(matched.path, "path/to/file.py");
                    assert_eq!(usize::from(matched.level), level.len());
                }
            }
        }
    }

    #[test]
    fn malformed_headings_are_rejected() {
        for line in [
            "# NEW: x",
            "#### NEW: x",
            "## NEW:",
            "## UNKNOWN: x",
            "## NEW [x",
        ] {
            assert!(match_heading(line, 0).is_none(), "{line}");
        }
    }

    #[test]
    fn fenced_headings_and_boundaries_are_ignored() {
        let text = "## Files to modify/create\n```md\n## NEW: hidden.py\n## Stop\n```\n## NEW: shown.py\n## Stop\n";
        let events = iter_heading_events(text);
        let paths: Vec<_> = events
            .iter()
            .filter_map(|event| event.heading.as_ref().map(|heading| heading.path.as_str()))
            .collect();
        let generic: Vec<_> = events
            .iter()
            .filter(|event| event.generic_level_two)
            .map(|event| event.text.as_str())
            .collect();
        assert_eq!(paths, ["shown.py"]);
        assert_eq!(generic, ["## Files to modify/create", "## Stop"]);
    }

    #[test]
    fn balanced_fence_helper_covers_backtick_tilde_and_unclosed() {
        assert_eq!(
            crate::balanced_fence_line_indices(&[
                "before",
                "```md",
                "## NEW: hidden.py",
                "```",
                "after"
            ]),
            [2].into_iter().collect()
        );
        assert_eq!(
            crate::balanced_fence_line_indices(&[
                "before",
                "~~~~md",
                "## NEW: hidden.py",
                "~~~~",
                "after"
            ]),
            [2].into_iter().collect()
        );
        assert_eq!(
            crate::balanced_fence_line_indices(&[
                "````md",
                "```",
                "## NEW: still-hidden.py",
                "````"
            ]),
            [1, 2].into_iter().collect()
        );
        assert!(
            crate::balanced_fence_line_indices(&[
                "```md",
                "## NEW: still-open.py",
                "```not-a-close"
            ])
            .is_empty()
        );
        assert!(
            crate::balanced_fence_line_indices(&["```md", "## NEW: after-unclosed.py"]).is_empty()
        );
        assert!(
            crate::balanced_fence_line_indices(&["```md", "## NEW: still-open.py", "~~~"])
                .is_empty()
        );
    }

    #[test]
    fn typed_trailer_recognition_and_rejection() {
        let cases = [
            (
                "review_status: complete",
                TrailerValue::Text("complete".into()),
            ),
            ("rounds_completed: 00", TrailerValue::Int(0)),
            ("difficulty: HARD", TrailerValue::Text("HARD".into())),
            ("diff_added: 007", TrailerValue::Int(7)),
            ("diff_deleted: 0", TrailerValue::Int(0)),
            ("mechanical_churn: true", TrailerValue::Bool(true)),
            (
                "oversize_override: operator",
                TrailerValue::Text("operator".into()),
            ),
            ("diff_lines: 09", TrailerValue::Int(9)),
        ];
        for (line, expected) in cases {
            let matched = match_trailer_line(line).expect(line);
            assert_eq!(matched.parsed_value, expected);
        }
        for line in [
            "diff_added: 08",
            "diff_deleted: 09",
            "mechanical_churn: yes",
            "oversize_override: model",
            "difficulty: hard",
        ] {
            assert!(match_trailer_line(line).is_none(), "{line}");
        }
    }

    #[test]
    fn final_contiguous_block_boundaries_duplicates_and_terminal_requirement() {
        let text = "body\ndifficulty: HARD\nconfidence: high\ndiff_added: 1\ndiff_added: 2\ndiff_lines: 3\n";
        let trailers = parse_final_trailers(text, true);
        assert_eq!(
            trailers.lines,
            ["diff_added: 1", "diff_added: 2", "diff_lines: 3"]
        );
        assert_eq!(trailers.duplicates, [TrailerKey::DiffAdded]);
        assert_eq!(trailers.diff_lines(), Some(3));
        assert!(terminal_diff_lines("body\ndiff_lines: 1\nmore\n").is_none());
        assert_eq!(
            parse_final_trailers("body\ndiff_added: 1\n\ndiff_lines: 2\n", false).lines,
            ["diff_lines: 2"]
        );
    }

    #[test]
    fn registry_drives_recognition_and_composition() {
        assert_eq!(
            TRAILER_KEYS,
            [
                "review_status",
                "rounds_completed",
                "difficulty",
                "diff_added",
                "diff_deleted",
                "mechanical_churn",
                "oversize_override",
                "diff_lines",
            ]
        );
        assert_eq!(
            OPTIONAL_SIZE_TRAILER_KEYS,
            [
                "diff_added",
                "diff_deleted",
                "mechanical_churn",
                "oversize_override",
            ]
        );
        assert_eq!(FIRM_HEADING_KINDS, ["NEW", "UPDATED", "REWRITTEN"]);
        let values = [
            (
                TrailerKey::ReviewStatus,
                TrailerValue::Text("complete".into()),
            ),
            (TrailerKey::RoundsCompleted, TrailerValue::Int(2)),
            (
                TrailerKey::Difficulty,
                TrailerValue::Text("MODERATE".into()),
            ),
            (TrailerKey::DiffAdded, TrailerValue::Int(3)),
            (TrailerKey::DiffDeleted, TrailerValue::Int(4)),
            (TrailerKey::MechanicalChurn, TrailerValue::Bool(false)),
            (
                TrailerKey::OversizeOverride,
                TrailerValue::Text("operator".into()),
            ),
            (TrailerKey::DiffLines, TrailerValue::Int(7)),
        ];
        let lines = compose_trailer_lines(&values).expect("compose");
        assert_eq!(
            lines[lines.len() - 2..],
            ["oversize_override: operator", "diff_lines: 7"]
        );
    }

    #[test]
    fn m1_multi_defect_order_is_deterministic() {
        let result = validate_plan_facets("## Plan\n\njust prose\n");
        assert_eq!(
            result.defects,
            [
                "missing-firm-scope",
                "missing-ordered-implementation",
                "missing-acceptance",
                "missing-closed-decisions",
                "missing-breaking-migration",
                "missing-diff-lines",
            ]
        );
    }

    #[test]
    fn valid_plan_contract_has_no_defects_with_injected_tracked_paths() {
        let root = TempDir::new().expect("temp");
        let tracked_path = "python/larch/design/plan_grammar.py";
        let full = root.path().join(tracked_path);
        fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        fs::write(&full, b"x\n").expect("write");
        let mut tracked = HashSet::new();
        tracked.insert(tracked_path.to_owned());
        let result = validate_plan_contract(&valid_plan(tracked_path), root.path(), &tracked);
        assert!(result.ok(), "{:?}", result.defects);
        assert!(validate_plan_facets(&valid_plan(tracked_path)).ok());
    }

    #[test]
    fn m2_empty_glob_missing_updated_existing_new_and_unsafe_paths() {
        let root = TempDir::new().expect("temp");
        let tracked_path = "python/larch/design/plan_grammar.py";
        let full = root.path().join(tracked_path);
        fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        fs::write(&full, b"x\n").expect("write");
        let mut tracked = HashSet::new();
        tracked.insert(tracked_path.to_owned());

        let missing = valid_plan("does/not/exist.py");
        assert!(
            validate_plan_contract(&missing, root.path(), &tracked)
                .defects
                .contains(&"missing-updated-plan-path")
        );
        let empty_glob = valid_plan("does/not/match-any-*.zzz");
        assert!(
            validate_plan_contract(&empty_glob, root.path(), &tracked)
                .defects
                .contains(&"empty-plan-glob")
        );
        let existing_new = valid_plan(tracked_path).replace(
            &format!("### UPDATED: {tracked_path}\n"),
            &format!("### NEW: {tracked_path}\n"),
        );
        assert!(
            validate_plan_contract(&existing_new, root.path(), &tracked)
                .defects
                .contains(&"existing-new-plan-path")
        );
        assert!(
            validate_plan_contract(&valid_plan("/etc/passwd"), root.path(), &tracked)
                .defects
                .contains(&"unsafe-plan-path")
        );
        assert!(
            validate_plan_contract(&valid_plan("../outside.py"), root.path(), &tracked)
                .defects
                .contains(&"unsafe-plan-path")
        );
    }

    #[test]
    fn tracked_glob_and_new_under_safe_parent() {
        let root = TempDir::new().expect("temp");
        let tracked_path = "python/larch/design/plan_grammar.py";
        let full = root.path().join(tracked_path);
        fs::create_dir_all(full.parent().expect("parent")).expect("mkdir");
        fs::write(&full, b"x\n").expect("write");
        let mut tracked = HashSet::new();
        tracked.insert(tracked_path.to_owned());
        let glob_plan = valid_plan(tracked_path).replace(
            &format!("### UPDATED: {tracked_path}\n"),
            "### UPDATED: python/larch/design/plan_*.py\n",
        );
        assert!(validate_plan_contract(&glob_plan, root.path(), &tracked).ok());
        let new_plan = valid_plan(tracked_path).replace(
            &format!("### UPDATED: {tracked_path}\n"),
            "### NEW: python/larch/design/_issue_7780_new_only.py\n",
        );
        assert!(validate_plan_contract(&new_plan, root.path(), &tracked).ok());
    }

    #[test]
    fn grammar_prompt_requires_executable_plan_sections() {
        let prompt = grammar_prompt();
        for heading in [
            "## Closed decisions and ownership",
            "## Ordered implementation",
            "## Acceptance",
            "## Breaking changes and migration",
        ] {
            assert!(prompt.contains(&format!("`{heading}`")), "{heading}");
        }
        assert!(prompt.contains("at least one numbered step"));
    }

    #[test]
    fn headings_after_unmatched_opener_remain_visible() {
        let text = "```md\n## NEW: hidden-if-balanced.py\n## NEW: visible-after-unclosed.py\n";
        let paths: Vec<_> = iter_plan_headings(text, None)
            .into_iter()
            .map(|heading| heading.path)
            .collect();
        assert_eq!(
            paths,
            [
                "hidden-if-balanced.py".to_owned(),
                "visible-after-unclosed.py".to_owned()
            ]
        );
        let closed = "~~~\n## NEW: hidden.py\n~~~\n## NEW: shown.py\n";
        assert_eq!(
            iter_plan_headings(closed, None)
                .into_iter()
                .map(|heading| heading.path)
                .collect::<Vec<_>>(),
            ["shown.py".to_owned()]
        );
    }
}
