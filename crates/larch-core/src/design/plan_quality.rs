//! Plan-quality analysis core for /design validation flows.
//!
//! Ports the pure analysis surface of `python/larch/design/plan_quality.py` and
//! command extraction from `_plan_quality_commands.py`. Command registration,
//! autofix, and revision waterfall stay with later leaves.

#![allow(
    clippy::assigning_clones,
    clippy::too_many_lines,
    clippy::option_if_let_else,
    clippy::single_match_else
)]

use crate::design::plan_grammar::{
    self, HeadingKind, TrailerKey, TrailerValue, iter_firm_headings, match_heading,
    parse_final_trailers,
};
use crate::{balanced_fence_line_indices, difficulty};
use regex::Regex;
use std::{
    collections::HashSet,
    path::{Path, PathBuf},
    sync::LazyLock,
};

/// Plan body line budget before the size trigger fires.
pub const PLAN_SIZE_MAX_PLAN_BODY_LINES: usize = 800;
/// Self-declared `diff_added` budget before the size trigger fires.
pub const PLAN_SIZE_MAX_DIFF_ADDED: i64 = 2000;
/// Terminal `diff_lines` budget before the size trigger fires.
pub const PLAN_SIZE_MAX_DIFF_LINES: i64 = 1500;
/// Firm heading count budget before the size trigger fires.
pub const PLAN_SIZE_MAX_FIRM_HEADINGS: usize = 25;
/// Distinct surface budget before the size trigger fires.
pub const PLAN_SIZE_MAX_SURFACES: usize = 4;
/// Trusted oversize override trailer value.
pub const OVERSIZE_OVERRIDE_OPERATOR: &str = "operator";

/// TSV header for parsed plan-command rows.
pub const HEADER: &str = "row_type\tsource_line\tscript_path\tflag\tflag_value\tnote\tcmd_uid";

static FILES_CREATE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^###[ \t]+Files[ \t]+to[ \t]+create([ \t]|$)").expect("files create regex")
});
static FILES_UPDATE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^###[ \t]+Files[ \t]+to[ \t]+update([ \t]|$)").expect("files update regex")
});
static H3_MISC_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^###[ \t]+").expect("h3 misc regex"));
static H2_MISC_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^##[ \t]+").expect("h2 misc regex"));
static FILES_CREATE_OR_UPDATE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^###[ \t]+Files[ \t]+to[ \t]+(create|update)").expect("files create/update regex")
});
static H2_FILES_CREATE_OR_UPDATE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^##[ \t]+Files[ \t]+to[ \t]+(create|update)")
        .expect("h2 files create/update regex")
});
static ADDS_FLAG_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*-[ \t]+Adds[ \t]+flag:").expect("adds flag regex"));
static ADDS_FLAG_INDENTED_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[ \t]+-[ \t]+Adds[ \t]+flag:").expect("adds flag indented regex")
});
static HASH_HEADING_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^#{2,3}[ \t]+").expect("hash heading regex"));
static BASH_FENCE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[ \t]*```[ \t]*(bash|sh)[ \t]*$").expect("bash fence regex"));
static CONTINUATION_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\\\s*$").expect("continuation regex"));
static DOUBLE_CONTINUATION_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\\\\\s*$").expect("double continuation regex"));
static HEREDOC_DELIM_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[A-Za-z0-9_]+").expect("heredoc delim regex"));
static EVAL_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(^|\s)eval(\s|$)").expect("eval regex"));
static ENV_ASSIGN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z_][A-Za-z0-9_]*=").expect("env assign regex"));
static ADDS_FLAG_STRIP_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[ \t]*-[ \t]+Adds[ \t]+flag:[ \t]*").expect("adds flag strip regex")
});
static ADDS_FLAG_INDENTED_STRIP_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[ \t]+-[ \t]+Adds[ \t]+flag:[ \t]*").expect("adds flag indented strip regex")
});
static NEW_BOLD_STRIP_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[^*]*\*\*NEW\*\*:[ \t]*").expect("new bold strip regex"));
static UPDATED_BOLD_STRIP_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^[^*]*\*\*UPDATED\*\*:[ \t]*").expect("updated bold strip regex")
});
static TICK_PREFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^\s*`+").expect("tick prefix regex"));
static TICK_SUFFIX_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"`+\s*$").expect("tick suffix regex"));

/// Optional size/difficulty trailers from the final contiguous trailer block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OptionalMetadata {
    /// Trailer lines above terminal `diff_lines`.
    pub metadata_trailer_lines: usize,
    /// Raw `diff_added` value when present.
    pub diff_added: Option<String>,
    /// Raw `diff_deleted` value when present.
    pub diff_deleted: Option<String>,
    /// Canonical `mechanical_churn` token (`true`/`false`).
    pub mechanical_churn: String,
    /// Trusted oversize override value when present.
    pub oversize_override: Option<String>,
    /// Present optional/difficulty keys in stable order.
    pub keys: Vec<String>,
    /// Canonical `key=value` snapshots for present size trailers.
    pub values: Vec<String>,
}

/// One parsed plan-command row.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanCommandRow {
    /// Row discriminator.
    pub row_type: String,
    /// 1-based source line.
    pub source_line: usize,
    /// Script path when applicable.
    pub script_path: String,
    /// Flag name without leading `--`.
    pub flag: String,
    /// Flag value when present.
    pub flag_value: String,
    /// Parse note when applicable.
    pub note: String,
    /// Stable command uid within the document.
    pub cmd_uid: String,
}

impl PlanCommandRow {
    fn new(
        row_type: impl Into<String>,
        source_line: usize,
        script_path: impl Into<String>,
        flag: impl Into<String>,
        flag_value: impl Into<String>,
        note: impl Into<String>,
        cmd_uid: impl Into<String>,
    ) -> Self {
        Self {
            row_type: row_type.into(),
            source_line,
            script_path: script_path.into(),
            flag: flag.into(),
            flag_value: flag_value.into(),
            note: note.into(),
            cmd_uid: cmd_uid.into(),
        }
    }

    /// Render one TSV row with Python-compatible escaping.
    #[must_use]
    pub fn to_tsv(&self) -> String {
        [
            self.row_type.as_str(),
            &self.source_line.to_string(),
            &tsv_escape(&self.script_path),
            &tsv_escape(&self.flag),
            &tsv_escape(&self.flag_value),
            &tsv_escape(&self.note),
            &tsv_escape(&self.cmd_uid),
        ]
        .join("\t")
    }
}

/// Pure plan-size trigger assessment.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PlanSizeAssessment {
    /// Firm heading count.
    pub firm_headings: usize,
    /// Distinct surface count.
    pub surfaces: usize,
    /// Trigger reason tokens in emission order.
    pub reasons: Vec<&'static str>,
    /// Whether mechanical churn softens a raw size trigger.
    pub soft: bool,
    /// Whether a trusted operator override suppresses the hard trigger.
    pub override_suppressed: bool,
}

/// Parse optional metadata from the final contiguous trailer block.
#[must_use]
pub fn parse_optional_metadata(plan_text: &str) -> OptionalMetadata {
    let trailers = parse_final_trailers(plan_text, true);
    let mut diff_added = None;
    let mut diff_deleted = None;
    let mut mechanical = "false".to_owned();
    let mut oversize_override = None;
    let mut has_added = false;
    let mut has_deleted = false;
    let mut has_mech = false;
    let mut has_difficulty = false;
    let mut has_oversize_override = false;
    for item in &trailers.matches {
        match item.key {
            TrailerKey::DiffAdded => {
                diff_added = Some(item.value.clone());
                has_added = true;
            }
            TrailerKey::DiffDeleted => {
                diff_deleted = Some(item.value.clone());
                has_deleted = true;
            }
            TrailerKey::MechanicalChurn => {
                mechanical = match &item.parsed_value {
                    TrailerValue::Bool(true) => "true".to_owned(),
                    _ => "false".to_owned(),
                };
                has_mech = true;
            }
            TrailerKey::OversizeOverride => {
                oversize_override = Some(OVERSIZE_OVERRIDE_OPERATOR.to_owned());
                has_oversize_override = true;
            }
            TrailerKey::Difficulty => has_difficulty = true,
            _ => {}
        }
    }
    let keys = [
        ("difficulty", has_difficulty),
        ("diff_added", has_added),
        ("diff_deleted", has_deleted),
        ("mechanical_churn", has_mech),
        ("oversize_override", has_oversize_override),
    ]
    .into_iter()
    .filter(|&(_, present)| present)
    .map(|(key, _)| key.to_owned())
    .collect::<Vec<_>>();
    let mut values = Vec::new();
    if has_added && let Some(value) = &diff_added {
        values.push(format!("diff_added={value}"));
    }
    if has_deleted && let Some(value) = &diff_deleted {
        values.push(format!("diff_deleted={value}"));
    }
    if has_mech {
        values.push(format!("mechanical_churn={mechanical}"));
    }
    if has_oversize_override && let Some(value) = &oversize_override {
        values.push(format!("oversize_override={value}"));
    }
    OptionalMetadata {
        metadata_trailer_lines: trailers.lines.len().saturating_sub(1),
        diff_added,
        diff_deleted,
        mechanical_churn: mechanical,
        oversize_override,
        keys,
        values,
    }
}

/// Validate trailing difficulty metadata.
#[must_use]
pub fn validate_difficulty_metadata(plan_text: &str, require: bool) -> (bool, String) {
    let lines = difficulty::trailing_plan_metadata_lines(plan_text);
    let mut found = String::new();
    let mut malformed = String::new();
    for raw in lines {
        if let Some(value) = raw.strip_prefix("difficulty:") {
            let value = value.trim();
            if difficulty::tier_valid(value) {
                found.clear();
                found.push_str(value);
            } else {
                malformed = if value.is_empty() {
                    "missing".to_owned()
                } else {
                    value.to_owned()
                };
            }
        }
    }
    if !malformed.is_empty() {
        return (false, format!("invalid difficulty metadata: {malformed}"));
    }
    if require && found.is_empty() {
        return (false, "missing difficulty metadata".to_owned());
    }
    (true, found)
}

/// Firm heading path tokens with markdown ticks stripped.
#[must_use]
pub fn firm_heading_paths(text: &str) -> Vec<String> {
    iter_firm_headings(text)
        .into_iter()
        .map(|heading| heading.path.trim_matches('`').to_owned())
        .collect()
}

/// Firm heading count.
#[must_use]
pub fn firm_heading_count(text: &str) -> usize {
    firm_heading_paths(text).len()
}

/// Distinct surfaces touched by firm headings.
#[must_use]
pub fn plan_surfaces(text: &str) -> HashSet<String> {
    firm_heading_paths(text)
        .into_iter()
        .filter_map(|path| {
            let surface = plan_surface(&path);
            (!surface.is_empty()).then_some(surface)
        })
        .collect()
}

/// Assess plan-size trigger reasons without reading the filesystem.
#[must_use]
pub fn assess_plan_size(
    meta: &OptionalMetadata,
    text: &str,
    plan_lines: usize,
    diff_lines: i64,
    oversize_override: Option<&str>,
) -> PlanSizeAssessment {
    let firm_headings = firm_heading_count(text);
    let surfaces = plan_surfaces(text).len();
    let mut reasons = Vec::new();
    if plan_lines > PLAN_SIZE_MAX_PLAN_BODY_LINES {
        reasons.push("plan-body-lines");
    }
    let size_diff_added = meta
        .diff_added
        .as_ref()
        .and_then(|value| value.parse::<i64>().ok())
        .is_some_and(|value| value > PLAN_SIZE_MAX_DIFF_ADDED);
    let size_diff_lines = diff_lines > PLAN_SIZE_MAX_DIFF_LINES;
    let size_diff_raw = size_diff_added || size_diff_lines;
    let soft = meta.mechanical_churn == "true" && size_diff_raw;
    if size_diff_added {
        reasons.push("diff-added");
    }
    if size_diff_lines {
        reasons.push("diff-lines");
    }
    if firm_headings > PLAN_SIZE_MAX_FIRM_HEADINGS {
        reasons.push("firm-headings");
    }
    if surfaces > PLAN_SIZE_MAX_SURFACES {
        reasons.push("surfaces");
    }
    let override_suppressed =
        !reasons.is_empty() && oversize_override == Some(OVERSIZE_OVERRIDE_OPERATOR);
    PlanSizeAssessment {
        firm_headings,
        surfaces,
        reasons,
        soft,
        override_suppressed,
    }
}

/// Render plan-command rows as TSV matching the Python owner.
#[must_use]
pub fn render_plan_command_tsv(rows: &[PlanCommandRow]) -> String {
    let mut out = String::from(HEADER);
    out.push('\n');
    for row in rows {
        out.push_str(&row.to_tsv());
        out.push('\n');
    }
    out
}

/// Parse plan headings and fenced shell commands into typed rows.
#[must_use]
pub fn parse_plan_commands(
    plan_text: &str,
    repo_root: &Path,
    plugin_root: &Path,
) -> Vec<PlanCommandRow> {
    let repo = normalize_root(repo_root);
    let plugin = normalize_root(plugin_root);
    let mut rows = Vec::new();
    let lines: Vec<&str> = plan_text.lines().collect();
    let fenced_lines = balanced_fence_line_indices(&lines);
    let mut fence_ends = std::collections::BTreeMap::new();
    for fence_line in &fenced_lines {
        if fence_ends.contains_key(&(fence_line.saturating_sub(1)))
            || fenced_lines.contains(&fence_line.saturating_sub(1))
        {
            continue;
        }
        let fence_start = fence_line.saturating_sub(1);
        let mut fence_end = *fence_line;
        while fenced_lines.contains(&(fence_end + 1)) {
            fence_end += 1;
        }
        fence_ends.insert(fence_start, fence_end + 1);
    }
    let mut files_section = String::new();
    let mut pending_updated = String::new();
    let mut uid_next = 0_usize;

    for (idx_zero, raw) in lines.iter().enumerate() {
        let idx = idx_zero + 1;
        let fence_start = idx_zero;
        if let Some(&fence_end) = fence_ends.get(&fence_start) {
            if BASH_FENCE_RE.is_match(raw) {
                let text = lines[idx..fence_end].join("\n");
                process_fence(&mut rows, idx, &text, &repo, &plugin, &mut uid_next);
            }
            continue;
        }
        if fenced_lines.contains(&fence_start) || plan_grammar::is_fence_marker(raw) {
            continue;
        }
        if FILES_CREATE_RE.is_match(raw) {
            files_section.clear();
            files_section.push_str("create");
            pending_updated.clear();
            continue;
        }
        if FILES_UPDATE_RE.is_match(raw) {
            files_section.clear();
            files_section.push_str("update");
            pending_updated.clear();
            continue;
        }
        let heading = match_heading(raw, idx);
        let h3_misc = H3_MISC_RE.is_match(raw)
            && !raw.starts_with("####")
            && !FILES_CREATE_OR_UPDATE_RE.is_match(raw);
        let h2_misc = H2_MISC_RE.is_match(raw)
            && !raw.starts_with("###")
            && !H2_FILES_CREATE_OR_UPDATE_RE.is_match(raw);
        if h3_misc || h2_misc {
            if let Some(heading) = heading.as_ref() {
                if heading.kind == HeadingKind::New {
                    emit_new_script(&mut rows, &heading.path, idx);
                }
                if heading.kind == HeadingKind::Updated {
                    pending_updated.clone_from(&heading.path);
                } else {
                    pending_updated.clear();
                }
            } else if HASH_HEADING_RE.is_match(raw) {
                pending_updated.clear();
            }
            if heading.is_none() {
                files_section.clear();
            }
            continue;
        }
        if !pending_updated.is_empty() && ADDS_FLAG_RE.is_match(raw) {
            let flag = ADDS_FLAG_STRIP_RE.replace(raw, "").trim().to_owned();
            emit_updated_flag(&mut rows, &pending_updated, &flag, idx);
            continue;
        }
        if files_section == "create" && raw.contains("**NEW**:") {
            let path = NEW_BOLD_STRIP_RE.replace(raw, "").trim().to_owned();
            emit_new_script(&mut rows, &path, idx);
        }
        if files_section == "update" && raw.contains("**UPDATED**:") {
            pending_updated = strip_md_ticks(UPDATED_BOLD_STRIP_RE.replace(raw, "").trim());
            continue;
        }
        if files_section == "update"
            && !pending_updated.is_empty()
            && ADDS_FLAG_INDENTED_RE.is_match(raw)
        {
            let flag = ADDS_FLAG_INDENTED_STRIP_RE
                .replace(raw, "")
                .trim()
                .to_owned();
            emit_updated_flag(&mut rows, &pending_updated, &flag, idx);
        }
    }
    rows
}

fn plan_surface(path: &str) -> String {
    let normalized = path.trim().trim_matches('`').trim_matches('/').to_owned();
    if normalized.is_empty() {
        return String::new();
    }
    let parts: Vec<&str> = normalized.split('/').collect();
    if parts.len() >= 3 && parts[0] == "python" && parts[1] == "larch" {
        if parts.len() >= 4 {
            return parts[..3].join("/");
        }
        return "python/larch".to_owned();
    }
    parts[0].to_owned()
}

fn normalize_root(path: &Path) -> PathBuf {
    path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
}

fn tsv_escape(text: &str) -> String {
    text.replace(['\r', '\n', '\t'], "")
}

fn bad_field(text: &str) -> bool {
    text.contains(['\t', '\n', '\r'])
}

fn strip_md_ticks(text: &str) -> String {
    let stripped = TICK_PREFIX_RE.replace(text, "");
    TICK_SUFFIX_RE
        .replace(stripped.trim(), "")
        .trim()
        .to_owned()
}

fn emit_parse_note(rows: &mut Vec<PlanCommandRow>, line: usize, reason: &str) {
    if bad_field(reason) {
        rows.push(PlanCommandRow::new(
            "parse_note",
            line,
            "",
            "",
            "",
            "charset-violation",
            "",
        ));
    } else {
        rows.push(PlanCommandRow::new(
            "parse_note",
            line,
            "",
            "",
            "",
            reason,
            "",
        ));
    }
}

fn emit_new_script(rows: &mut Vec<PlanCommandRow>, path: &str, line: usize) {
    let path = strip_md_ticks(path);
    if path.is_empty() {
        return;
    }
    if bad_field(&path) {
        emit_parse_note(rows, line, "allowlist-path-charset");
    } else {
        rows.push(PlanCommandRow::new(
            "new_script",
            line,
            path,
            "",
            "",
            "",
            "",
        ));
    }
}

fn emit_updated_flag(rows: &mut Vec<PlanCommandRow>, path: &str, flag: &str, line: usize) {
    let path = strip_md_ticks(path);
    let mut flag = strip_md_ticks(flag);
    if let Some(stripped) = flag.strip_prefix("--") {
        flag = stripped.to_owned();
    }
    if path.is_empty() || flag.is_empty() {
        return;
    }
    if bad_field(&path) || bad_field(&flag) {
        emit_parse_note(rows, line, "allowlist-charset");
    } else {
        rows.push(PlanCommandRow::new(
            "updated_flag",
            line,
            path,
            flag,
            "",
            "",
            "",
        ));
    }
}

fn join_continuations(text: &str) -> String {
    let lines: Vec<&str> = text.split('\n').collect();
    let mut out = Vec::new();
    let mut i = 0_usize;
    while i < lines.len() {
        let mut line = lines[i].to_owned();
        while CONTINUATION_RE.is_match(&line) && !DOUBLE_CONTINUATION_RE.is_match(&line) {
            line = CONTINUATION_RE.replace(&line, "").into_owned();
            i += 1;
            if i >= lines.len() {
                break;
            }
            line.push_str(lines[i]);
        }
        out.push(line);
        i += 1;
    }
    out.join("\n")
}

fn strip_heredoc_multiline(
    lines: &[&str],
    fence_start: usize,
    rows: &mut Vec<PlanCommandRow>,
) -> Vec<(usize, String)> {
    let mut out = Vec::new();
    let mut i = 0_usize;
    let mut compressed = 0_usize;
    while i < lines.len() {
        let line = lines[i];
        let Some(pos) = line.find("<<") else {
            compressed += 1;
            out.push((fence_start + compressed, line.to_owned()));
            i += 1;
            continue;
        };
        let pre = line[..pos].trim();
        if !pre.is_empty() {
            compressed += 1;
            out.push((fence_start + compressed, pre.to_owned()));
        }
        let rest = line[pos + 2..].trim_start();
        let delim = if let Some(stripped) = rest.strip_prefix('\'') {
            stripped
                .find('\'')
                .map(|q| stripped[..q].to_owned())
                .unwrap_or_default()
        } else if let Some(stripped) = rest.strip_prefix('"') {
            match stripped.find('"') {
                Some(q) => stripped[..q].to_owned(),
                None => {
                    emit_parse_note(
                        rows,
                        fence_start + compressed + 1,
                        "heredoc-unterminated-quote",
                    );
                    String::new()
                }
            }
        } else {
            HEREDOC_DELIM_RE
                .find(rest)
                .map(|m| m.as_str().to_owned())
                .unwrap_or_default()
        };
        if delim.is_empty() {
            compressed += 1;
            out.push((fence_start + compressed, line.to_owned()));
            i += 1;
            continue;
        }
        i += 1;
        while i < lines.len() && lines[i] != delim {
            i += 1;
        }
        if i < lines.len() {
            i += 1;
        }
    }
    out
}

fn split_segments(segment: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut buf = String::new();
    let mut depth = 0_i32;
    let mut in_s = false;
    let mut in_d = false;
    let mut esc = false;
    let chars: Vec<char> = segment.chars().collect();
    let mut i = 0_usize;
    while i < chars.len() {
        let ch = chars[i];
        if esc {
            buf.push(ch);
            esc = false;
            i += 1;
            continue;
        }
        if ch == '\\' && (in_s || in_d) {
            buf.push(ch);
            esc = true;
            i += 1;
            continue;
        }
        if !in_d && ch == '\'' && !in_s {
            in_s = true;
            buf.push(ch);
            i += 1;
            continue;
        }
        if in_s {
            buf.push(ch);
            if ch == '\'' {
                in_s = false;
            }
            i += 1;
            continue;
        }
        if !in_s && ch == '"' && !in_d {
            in_d = true;
            buf.push(ch);
            i += 1;
            continue;
        }
        if in_d {
            buf.push(ch);
            if ch == '"' {
                in_d = false;
            }
            i += 1;
            continue;
        }
        if ch == '(' {
            depth += 1;
        } else if ch == ')' && depth > 0 {
            depth -= 1;
        }
        if depth > 0 {
            buf.push(ch);
            i += 1;
            continue;
        }
        let two: String = chars[i..].iter().take(2).collect();
        if two == "&&" || two == "||" {
            if !buf.is_empty() {
                parts.push(std::mem::take(&mut buf));
            }
            i += 2;
            continue;
        }
        if matches!(ch, '|' | ';') {
            if !buf.is_empty() {
                parts.push(std::mem::take(&mut buf));
            }
            i += 1;
            continue;
        }
        buf.push(ch);
        i += 1;
    }
    if !buf.is_empty() {
        parts.push(buf);
    }
    parts
}

fn has_command_substitution(seg: &str) -> bool {
    let mut i = 0_usize;
    while let Some(rel) = seg[i..].find("$(") {
        let idx = i + rel;
        if !seg[idx..].starts_with("$((") {
            return true;
        }
        i = idx + 2;
    }
    false
}

fn tokenize(seg: &str) -> Vec<String> {
    let mut toks = Vec::new();
    let mut cur = String::new();
    let mut in_s = false;
    let mut in_d = false;
    let mut esc = false;
    for ch in seg.chars() {
        if esc {
            cur.push(ch);
            esc = false;
            continue;
        }
        if ch == '\\' && (in_s || in_d) {
            cur.push(ch);
            esc = true;
            continue;
        }
        if !in_d && ch == '\'' && !in_s {
            in_s = true;
            cur.push(ch);
            continue;
        }
        if in_s {
            cur.push(ch);
            if ch == '\'' {
                in_s = false;
            }
            continue;
        }
        if !in_s && ch == '"' && !in_d {
            in_d = true;
            cur.push(ch);
            continue;
        }
        if in_d {
            cur.push(ch);
            if ch == '"' {
                in_d = false;
            }
            continue;
        }
        if ch.is_whitespace() {
            if !cur.is_empty() {
                toks.push(std::mem::take(&mut cur));
            }
            continue;
        }
        cur.push(ch);
    }
    if !cur.is_empty() {
        toks.push(cur);
    }
    toks
}

fn normalize_token(token: &str, repo_root: &Path, plugin_root: &Path) -> String {
    let mut value = token.trim().to_owned();
    if value.len() >= 2 {
        let bytes = value.as_bytes();
        if (bytes[0] == b'\'' && *bytes.last().unwrap_or(&0) == b'\'')
            || (bytes[0] == b'"' && *bytes.last().unwrap_or(&0) == b'"')
        {
            value = value[1..value.len() - 1].to_owned();
        }
    }
    value = value
        .replace("${CLAUDE_PLUGIN_ROOT}/", "")
        .replace("$CLAUDE_PLUGIN_ROOT/", "");
    for root in [plugin_root, repo_root] {
        let prefix = format!("{}/", root.to_string_lossy().trim_end_matches('/'));
        if let Some(stripped) = value.strip_prefix(&prefix) {
            value = stripped.to_owned();
        }
    }
    value.trim().to_owned()
}

fn parse_command_segment(
    rows: &mut Vec<PlanCommandRow>,
    source_line: usize,
    seg: &str,
    repo_root: &Path,
    plugin_root: &Path,
    uid_next: &mut usize,
) {
    if has_command_substitution(seg) {
        emit_parse_note(rows, source_line, "subshell");
        return;
    }
    if seg.contains("<(") {
        emit_parse_note(rows, source_line, "process_substitution");
        return;
    }
    if EVAL_RE.is_match(seg) {
        emit_parse_note(rows, source_line, "eval");
        return;
    }
    let mut toks = tokenize(seg);
    while !toks.is_empty() {
        let first = normalize_token(&toks[0], repo_root, plugin_root);
        if matches!(
            first.as_str(),
            "bash" | "sh" | "dash" | "/bin/bash" | "/bin/sh" | "env"
        ) {
            toks.remove(0);
            continue;
        }
        if first == "-c" {
            emit_parse_note(rows, source_line, "inline-shell");
            return;
        }
        if first == "--" {
            toks.remove(0);
            continue;
        }
        if ENV_ASSIGN_RE.is_match(&first) {
            toks.remove(0);
            continue;
        }
        break;
    }
    if toks.is_empty() {
        return;
    }
    let script = normalize_token(&toks[0], repo_root, plugin_root);
    if script.is_empty() || script.starts_with('-') {
        return;
    }
    if script.contains("..") || script.starts_with('/') {
        emit_parse_note(rows, source_line, "non-canonical-script-path");
        return;
    }
    if bad_field(&script) {
        emit_parse_note(rows, source_line, "charset-violation");
        return;
    }
    *uid_next += 1;
    let uid = uid_next.to_string();
    let mut flags = 0_usize;
    let mut k = 1_usize;
    while k < toks.len() {
        let tok = normalize_token(&toks[k], repo_root, plugin_root);
        if tok.is_empty() {
            k += 1;
            continue;
        }
        if !tok.starts_with("--") {
            k += 1;
            continue;
        }
        if tok == "--" {
            break;
        }
        let body = &tok[2..];
        if body.is_empty() {
            k += 1;
            continue;
        }
        let (flag, value) = match body.find('=') {
            Some(index) => (body[..index].to_owned(), body[index + 1..].to_owned()),
            None => {
                let mut value = String::new();
                if k + 1 < toks.len() {
                    let nxt = normalize_token(&toks[k + 1], repo_root, plugin_root);
                    if !nxt.is_empty() && !nxt.starts_with('-') {
                        value = nxt;
                        k += 1;
                    }
                }
                (body.to_owned(), value)
            }
        };
        if bad_field(&flag) || bad_field(&value) {
            emit_parse_note(rows, source_line, "charset-violation");
            return;
        }
        rows.push(PlanCommandRow::new(
            "invocation",
            source_line,
            script.clone(),
            flag,
            value,
            "",
            uid.clone(),
        ));
        flags += 1;
        k += 1;
    }
    if flags == 0 {
        rows.push(PlanCommandRow::new(
            "invocation_no_flags",
            source_line,
            script,
            "",
            "",
            "",
            uid,
        ));
    }
}

fn process_fence(
    rows: &mut Vec<PlanCommandRow>,
    start: usize,
    text: &str,
    repo_root: &Path,
    plugin_root: &Path,
    uid_next: &mut usize,
) {
    if text.is_empty() {
        return;
    }
    let joined = join_continuations(text);
    let phys: Vec<&str> = joined.split('\n').collect();
    for (line_no, piece) in strip_heredoc_multiline(&phys, start, rows) {
        if piece.is_empty() {
            continue;
        }
        for seg in split_segments(&piece) {
            let seg = seg.trim();
            if !seg.is_empty() {
                parse_command_segment(rows, line_no, seg, repo_root, plugin_root, uid_next);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        OVERSIZE_OVERRIDE_OPERATOR, assess_plan_size, parse_optional_metadata, parse_plan_commands,
        render_plan_command_tsv, validate_difficulty_metadata,
    };
    use std::{fs, path::PathBuf};

    #[test]
    fn optional_metadata_parses_minimal_full_and_malformed_override() {
        let minimal = parse_optional_metadata("body\ndifficulty: HARD\ndiff_lines: 3\n");
        assert_eq!(minimal.metadata_trailer_lines, 1);
        assert_eq!(minimal.keys, ["difficulty"]);
        assert!(minimal.values.is_empty());
        assert_eq!(minimal.mechanical_churn, "false");

        let full = parse_optional_metadata(
            "body\ndifficulty: MODERATE\ndiff_added: 10\ndiff_deleted: 2\n\
             mechanical_churn: true\noversize_override: operator\ndiff_lines: 12\n",
        );
        assert_eq!(full.metadata_trailer_lines, 5);
        assert_eq!(full.diff_added.as_deref(), Some("10"));
        assert_eq!(full.diff_deleted.as_deref(), Some("2"));
        assert_eq!(full.mechanical_churn, "true");
        assert_eq!(
            full.oversize_override.as_deref(),
            Some(OVERSIZE_OVERRIDE_OPERATOR)
        );
        assert_eq!(
            full.keys,
            [
                "difficulty",
                "diff_added",
                "diff_deleted",
                "mechanical_churn",
                "oversize_override"
            ]
        );
        assert_eq!(
            full.values,
            [
                "diff_added=10",
                "diff_deleted=2",
                "mechanical_churn=true",
                "oversize_override=operator"
            ]
        );

        let malformed = parse_optional_metadata(
            "body\ndifficulty: HARD\noversize_override: model\ndiff_lines: 3\n",
        );
        assert_eq!(malformed.metadata_trailer_lines, 0);
        assert!(malformed.keys.is_empty());
    }

    #[test]
    fn size_assessment_matches_python_oracle_reasons() {
        let text = format!(
            "### UPDATED: a.py\n{}difficulty: HARD\ndiff_added: 3000\ndiff_lines: 2000\n",
            "x\n".repeat(850)
        );
        let meta = parse_optional_metadata(&text);
        let trailers = crate::design::parse_final_trailers(&text, true);
        let plan_lines = trailers.start_line.saturating_sub(1);
        let assessment = assess_plan_size(&meta, &text, plan_lines, 2000, None);
        assert_eq!(plan_lines, 851);
        assert_eq!(assessment.firm_headings, 1);
        assert_eq!(assessment.surfaces, 1);
        assert_eq!(
            assessment.reasons,
            ["plan-body-lines", "diff-added", "diff-lines"]
        );
        assert!(!assessment.soft);
        assert!(!assessment.override_suppressed);
    }

    #[test]
    fn validate_difficulty_metadata_ignores_body_tokens() {
        let text = "difficulty: HARD\nbody mentions difficulty: TRIVIAL\n\ndifficulty: MODERATE\ndiff_lines: 1\n";
        let (ok, value) = validate_difficulty_metadata(text, true);
        assert!(ok);
        assert_eq!(value, "MODERATE");
    }

    #[test]
    fn parse_plan_commands_golden_fixtures_match_python() {
        let fixture_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../../skills/design/scripts/fixtures/parse-plan-commands");
        let mut pairs = Vec::new();
        for entry in fs::read_dir(&fixture_dir).expect("fixtures dir") {
            let entry = entry.expect("entry");
            let path = entry.path();
            if path
                .file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.ends_with("-plan.md"))
            {
                let stem = path.file_stem().unwrap().to_string_lossy();
                let base = stem.trim_end_matches("-plan");
                let tsv = path.with_file_name(format!("{base}.tsv"));
                if tsv.is_file() {
                    pairs.push((path, tsv));
                }
            }
        }
        pairs.sort_by(|left, right| left.0.cmp(&right.0));
        assert_eq!(pairs.len(), 13, "expected 13 golden fixture pairs");
        let repo = PathBuf::from("/tmp/repo");
        for (plan_path, tsv_path) in pairs {
            let plan_text = fs::read_to_string(&plan_path).expect("plan");
            let expected = fs::read_to_string(&tsv_path).expect("tsv");
            let rows = parse_plan_commands(&plan_text, &repo, &repo);
            assert_eq!(
                render_plan_command_tsv(&rows),
                expected,
                "fixture {}",
                plan_path.display()
            );
        }
    }
}
