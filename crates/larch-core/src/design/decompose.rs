//! Pure design-decomposition logic ported from `python/larch/design/decompose.py`.
//!
//! Leaf #8588 of the #7680 Rust migration owns the `decompose` verbs. This
//! module holds the offline-deterministic core: partition-file parsing, the
//! filed-issue title prefixer, the dependency-graph acyclicity check, the
//! prepared-partition body builder whose artifacts stay hash-compatible with the
//! `/umbrella` consumer, and the dependency-migration algorithm over an
//! injectable graph seam. The impure orchestration (filesystem, GitHub, external
//! waterfall dispatch, redaction) lives in `larch-cli`.

use std::collections::{BTreeSet, HashSet, VecDeque};
use std::sync::LazyLock;

use regex::Regex;
use serde::{Deserialize, Serialize};

use crate::{
    compose_named_block, extract_firm_scope_paths, leading_square_bracket_prefix, match_heading,
    neutralize_named_block_markers, strip_lifecycle_prefix,
};

/// The four decomposition archetype lenses, in dispatch order.
pub const DECOMPOSE_ARCHETYPES: [&str; 4] = [
    "decomposition-specialist",
    "dependency-analyst",
    "scope-minimalist",
    "risk-isolation",
];

/// Minimum pieces a valid partition proposal must declare.
pub const MIN_PARTITION_PIECES: usize = 2;

/// Maximum archetype-prompt prefix lines the generic-Claude panel echoes.
pub const PROMPT_PREFIX_LINE_MAX: usize = 8;

/// The inert `larch:plan` stub every filed partition piece carries.
pub const PLAN_STUB_INNER: &str = "## Plan\n\n(needs /design \u{2014} operator runs `/design` on this filed piece and reaches Gate C approval before `[DESIGNED]` or `/implement`.)\n";

static PIECE_HEADING_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?m)^###\s+Piece\s+(\d+)\s*:\s*([^\n]+)$").expect("piece regex"));
static BLOCKED_BY_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)blocked-by\b(.*)$").expect("blocked-by regex"));
static DEP_SPLIT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i),|\s+and\b").expect("dependency split regex"));
static PIECE_REF_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)^Piece\s+(\d+)$").expect("piece ref regex"));
static BACKTICK_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"`([^`]+)`").expect("backtick regex"));
static SCOPE_SPLIT_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r",|\s+").expect("scope split regex"));
static TESTING_HEADING_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)^(#+)\s+Testing strategy\s*$").expect("testing heading regex")
});
static ANY_HEADING_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(#+)\s+").expect("heading regex"));
static ISSUE_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"^https://github\.com/([^/]+/[^/]+)/issues/([1-9][0-9]*)$")
        .expect("issue url regex")
});

/// One filed partition piece bound to the issue it created.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct FiledPiece {
    /// The 1-based piece number within the partition.
    pub piece: u64,
    /// The GitHub issue number filed for this piece.
    pub issue: u64,
    /// The `owner/name` slug the issue lives in.
    pub repo: String,
}

/// One directed blocked-by edge: `blocked` is blocked by `blocker`.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq, Serialize, Deserialize)]
pub struct PartitionEdge {
    /// The issue that is blocked.
    pub blocked: u64,
    /// The issue that blocks it.
    pub blocker: u64,
}

/// The persisted plan for migrating one original issue's dependency graph onto
/// its filed partition pieces.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
pub struct DependencyMigration {
    /// Manifest schema version; always `"1"` today.
    #[serde(default = "default_schema_version")]
    pub schema_version: String,
    /// The original issue being partitioned.
    pub original_issue: u64,
    /// The repository slug for every issue in the migration.
    pub repo: String,
    /// The filed pieces the original's edges move onto.
    pub pieces: Vec<FiledPiece>,
    /// The original's incoming (blocked-by) edges.
    pub incoming: Vec<PartitionEdge>,
    /// The original's outgoing (blocking) edges.
    pub outgoing: Vec<PartitionEdge>,
}

fn default_schema_version() -> String {
    "1".to_owned()
}

/// A live dependency-graph seam the migration algorithm reads and mutates.
///
/// The command path binds this to the hardened GitHub service; tests bind an
/// in-memory graph, matching how the Python tests injected `_read_dependencies`
/// and `_run_dependency_mutation`.
pub trait DependencyGraph {
    /// Return `(blocked_by, blocking)` issue numbers for `issue`, each a
    /// sorted, de-duplicated list. An error aborts the migration loudly.
    ///
    /// # Errors
    ///
    /// Returns a diagnostic when the dependency read fails or returns an
    /// unusable shape.
    fn read_dependencies(&self, issue: u64) -> Result<(Vec<u64>, Vec<u64>), String>;

    /// Add (`remove == false`) or remove (`remove == true`) the blocked-by edge
    /// and return whether the mutation and its read-back proof succeeded.
    fn mutate(&self, remove: bool, blocked: u64, blocker: u64) -> bool;
}

/// Whether an all-ASCII-digit, non-empty token would satisfy Python `str.isdigit`.
#[must_use]
pub fn is_ascii_digits(value: &str) -> bool {
    !value.is_empty() && value.bytes().all(|byte| byte.is_ascii_digit())
}

/// Prefix zero-width spaces before line-leading `###` so an embedded excerpt
/// cannot forge a partition piece heading.
#[must_use]
pub fn neutralize_markdown_h3_line_starts(text: &str) -> String {
    let mut output = String::with_capacity(text.len());
    for segment in text.split_inclusive('\n') {
        if segment.starts_with("###") {
            output.push('\u{200b}');
        }
        output.push_str(segment);
    }
    output
}

/// Compose the filed-issue title for one partition piece.
///
/// Preserves any leading square-bracket prefix of the original issue title,
/// then appends the `split-<issue>-<piece>:` token, never double-applying a
/// bracket or token the piece title already carries.
#[must_use]
pub fn prefixed_piece_title(
    original_title: &str,
    issue_number: &str,
    piece_number: u64,
    piece_title: &str,
) -> String {
    let bracket = leading_square_bracket_prefix(strip_lifecycle_prefix(original_title));
    let stripped_piece: String = if bracket.is_empty() {
        piece_title.to_owned()
    } else if let Some(rest) = piece_title.strip_prefix(&format!("{bracket} ")) {
        rest.to_owned()
    } else if let Some(rest) = piece_title.strip_prefix(&bracket) {
        rest.trim_start().to_owned()
    } else {
        piece_title.to_owned()
    };
    let mut parts: Vec<String> = Vec::new();
    if !bracket.is_empty() {
        parts.push(bracket);
    }
    if is_ascii_digits(issue_number) {
        let token = format!("split-{issue_number}-{piece_number}:");
        let token_with_space = format!("{token} ");
        if !stripped_piece.starts_with(&token_with_space) && stripped_piece != token {
            parts.push(token);
        }
    }
    parts.push(stripped_piece);
    parts.join(" ")
}

/// Parse a piece's `Dependencies:` line into the blocker piece numbers.
///
/// Returns `Some(vec)` for a well-formed line (empty when no `blocked-by`
/// clause), and `None` for a malformed reference, mirroring Python's
/// three-valued contract that `bad-dependency-ref` branches on. `index_by_num`
/// maps a piece number to its position so an unknown piece is rejected.
#[must_use]
pub fn parse_dependency(
    dep: &str,
    index_by_num: &std::collections::BTreeMap<u64, usize>,
) -> Option<Vec<u64>> {
    let Some(matched) = BLOCKED_BY_RE.captures(dep) else {
        return Some(Vec::new());
    };
    let remainder = matched.get(1).map_or("", |capture| capture.as_str());
    let segments: Vec<&str> = DEP_SPLIT_RE
        .split(remainder)
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .collect();
    if segments.is_empty() {
        return None;
    }
    let mut blockers: Vec<u64> = Vec::new();
    let mut seen: BTreeSet<u64> = BTreeSet::new();
    for segment in segments {
        let sm = PIECE_REF_RE.captures(segment)?;
        let blocker: u64 = sm.get(1)?.as_str().parse().ok()?;
        if !seen.insert(blocker) || !index_by_num.contains_key(&blocker) {
            return None;
        }
        blockers.push(blocker);
    }
    Some(blockers)
}

/// Return the trimmed value of a `- <field>:` line in a piece body, or `""`.
#[must_use]
pub fn piece_field(body: &str, field: &str) -> String {
    let prefix = format!("- {field}:").to_lowercase();
    for line in body.lines() {
        let stripped = line.trim();
        if stripped.to_lowercase().starts_with(&prefix) {
            return stripped
                .split_once(':')
                .map_or("", |(_head, tail)| tail)
                .trim()
                .to_owned();
        }
    }
    String::new()
}

/// Reduce a firm-heading token to its bare path, accepting parent-plan heading
/// forms such as ``### UPDATED: `path` ``.
#[must_use]
pub fn normalize_firm_heading(value: &str) -> String {
    let candidate = value.trim().trim_matches('`').trim();
    let resolved =
        match_heading(candidate, 0).map_or_else(|| candidate.to_owned(), |heading| heading.path);
    resolved.trim().trim_matches('`').trim().to_owned()
}

/// Split a comma/newline-separated firm-headings value into normalized paths.
#[must_use]
pub fn split_firm_headings(value: &str) -> Vec<String> {
    let mut items = Vec::new();
    for raw in value.split([',', '\n']) {
        let item = normalize_firm_heading(raw);
        if !item.is_empty() {
            items.push(item);
        }
    }
    items
}

fn strip_scope_token(raw: &str) -> String {
    raw.trim()
        .trim_matches(|character| character == ',' || character == ';')
        .to_owned()
}

/// Tokenize a piece `Scope:` value into candidate paths, preserving order.
#[must_use]
pub fn scope_tokens(scope: &str) -> Vec<String> {
    let mut tokens: Vec<String> = Vec::new();
    for capture in BACKTICK_RE.captures_iter(scope) {
        let token = strip_scope_token(&capture[1]);
        if !token.is_empty() {
            tokens.push(token);
        }
    }
    let cleaned = BACKTICK_RE.replace_all(scope, " ");
    for raw in SCOPE_SPLIT_RE.split(&cleaned) {
        let token = strip_scope_token(raw);
        if !token.is_empty() && token != "and" && token != "or" {
            tokens.push(token);
        }
    }
    let mut seen: BTreeSet<String> = BTreeSet::new();
    tokens
        .into_iter()
        .filter(|token| seen.insert(token.clone()))
        .collect()
}

fn path_matches_scope(path: &str, scope_token: &str) -> bool {
    let token = scope_token.trim_end_matches('/');
    path == token || path.starts_with(&format!("{token}/"))
}

/// Derive a piece's firm headings from the parent plan paths its scope covers.
#[must_use]
pub fn derive_firm_headings(parent_paths: &[String], scope: &str) -> Vec<String> {
    let tokens = scope_tokens(scope);
    parent_paths
        .iter()
        .filter(|path| tokens.iter().any(|token| path_matches_scope(path, token)))
        .cloned()
        .collect()
}

fn testing_strategy_lines(plan_text: &str) -> Vec<String> {
    let lines: Vec<&str> = plan_text.lines().collect();
    let mut start: Option<usize> = None;
    let mut level = 0usize;
    for (index, line) in lines.iter().enumerate() {
        if let Some(matched) = TESTING_HEADING_RE.captures(line) {
            start = Some(index + 1);
            level = matched[1].len();
            break;
        }
    }
    let Some(start) = start else {
        return Vec::new();
    };
    let mut out = Vec::new();
    for line in &lines[start..] {
        if let Some(heading) = ANY_HEADING_RE.captures(line)
            && heading[1].len() <= level
        {
            break;
        }
        let stripped = line.trim();
        if !stripped.is_empty() {
            out.push(stripped.to_owned());
        }
    }
    out
}

/// Derive a piece's acceptance from the parent Testing strategy or its scope.
#[must_use]
pub fn derive_acceptance(plan_text: &str, firm_headings: &[String], scope: &str) -> String {
    let strategy = testing_strategy_lines(plan_text);
    let matches: Vec<&String> = strategy
        .iter()
        .filter(|line| {
            firm_headings
                .iter()
                .any(|path| line.contains(path.as_str()))
        })
        .collect();
    if !matches.is_empty() {
        return matches
            .into_iter()
            .take(5)
            .map(String::as_str)
            .collect::<Vec<_>>()
            .join("\n");
    }
    let scope_summary = if scope.is_empty() {
        firm_headings.join(", ")
    } else {
        scope.to_owned()
    };
    if scope_summary.is_empty() {
        String::new()
    } else {
        format!("Verify {scope_summary} per parent Testing strategy.")
    }
}

/// Resolve one piece's `(scope, firm_headings, acceptance)`, or `None` when a
/// firm heading or acceptance cannot be determined.
#[must_use]
pub fn piece_metadata(
    body: &str,
    parent_plan_text: &str,
    parent_paths: &[String],
) -> Option<(String, Vec<String>, String)> {
    let scope = piece_field(body, "scope");
    let mut firm = split_firm_headings(&piece_field(body, "firm-headings"));
    if firm.is_empty() {
        firm = derive_firm_headings(parent_paths, &scope);
    }
    let mut acceptance = piece_field(body, "acceptance");
    if acceptance.is_empty() {
        acceptance = derive_acceptance(parent_plan_text, &firm, &scope);
    }
    if firm.is_empty() || acceptance.is_empty() {
        return None;
    }
    Some((scope, firm, acceptance))
}

fn acyclic(node_count: usize, edges: &[(usize, usize)]) -> bool {
    let mut adj: Vec<Vec<usize>> = vec![Vec::new(); node_count];
    let mut indeg = vec![0usize; node_count];
    for &(from, to) in edges {
        adj[from].push(to);
        indeg[to] += 1;
    }
    let mut queue: VecDeque<usize> = (0..node_count).filter(|&node| indeg[node] == 0).collect();
    let mut seen = 0usize;
    while let Some(node) = queue.pop_front() {
        seen += 1;
        for &next in &adj[node] {
            indeg[next] -= 1;
            if indeg[next] == 0 {
                queue.push_back(next);
            }
        }
    }
    seen == node_count
}

/// One parsed partition piece: `(number, title, body)`.
type Piece = (u64, String, String);

struct PieceData {
    dep_lines: Vec<String>,
    scopes: Vec<String>,
    firm_heading_lines: Vec<Vec<String>>,
    acceptance_lines: Vec<String>,
    edges: Vec<(usize, usize)>,
}

fn collect_piece_data(
    pieces: &[Piece],
    index_by_num: &std::collections::BTreeMap<u64, usize>,
    parent_plan_text: &str,
    parent_paths: &[String],
) -> Result<PieceData, String> {
    let mut panel_edges: Vec<(usize, usize)> = Vec::new();
    let mut dep_lines = Vec::new();
    let mut scopes = Vec::new();
    let mut firm_heading_lines = Vec::new();
    let mut acceptance_lines = Vec::new();
    for (index, (_pnum, _title, body)) in pieces.iter().enumerate() {
        let dep = {
            let field = piece_field(body, "dependencies");
            if field.is_empty() {
                "none".to_owned()
            } else {
                field
            }
        };
        dep_lines.push(dep.clone());
        let Some(blockers) = parse_dependency(&dep, index_by_num) else {
            return Err("bad-dependency-ref".to_owned());
        };
        for blocker in blockers {
            panel_edges.push((index_by_num[&blocker], index));
        }
        let Some((scope, firm, acceptance)) = piece_metadata(body, parent_plan_text, parent_paths)
        else {
            return Err("missing-piece-metadata".to_owned());
        };
        scopes.push(scope);
        firm_heading_lines.push(firm);
        acceptance_lines.push(acceptance);
    }
    if !parent_paths.is_empty() {
        let parent_firm: BTreeSet<&String> = parent_paths.iter().collect();
        let child_firm: BTreeSet<&String> = firm_heading_lines.iter().flatten().collect();
        if parent_firm != child_firm {
            return Err("firm-heading-coverage-mismatch".to_owned());
        }
    }
    // Deduplicate edges preserving first-seen order.
    let mut seen: BTreeSet<(usize, usize)> = BTreeSet::new();
    let edges: Vec<(usize, usize)> = panel_edges
        .into_iter()
        .filter(|edge| seen.insert(*edge))
        .collect();
    Ok(PieceData {
        dep_lines,
        scopes,
        firm_heading_lines,
        acceptance_lines,
        edges,
    })
}

/// The outcome of building the prepared-partition artifacts.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BuildOutcome {
    /// The status token the caller emits as `DECOMPOSE_PARTITION_STATUS`.
    pub status: String,
    /// The cycle witness, populated only for `cycle-detected`.
    pub witness: String,
    /// The `partition-input.txt` body, populated only for `ok`.
    pub input_text: String,
    /// The `partition-deps.tsv` rows as 1-based `(a, b)` index pairs.
    pub deps: Vec<(usize, usize)>,
}

impl BuildOutcome {
    fn status_only(status: &str) -> Self {
        Self {
            status: status.to_owned(),
            witness: String::new(),
            input_text: String::new(),
            deps: Vec::new(),
        }
    }
}

fn parse_pieces(text: &str) -> Vec<Piece> {
    let matches: Vec<regex::Match> = PIECE_HEADING_RE.find_iter(text).collect();
    let captures: Vec<regex::Captures> = PIECE_HEADING_RE.captures_iter(text).collect();
    let mut pieces = Vec::new();
    for (index, capture) in captures.iter().enumerate() {
        let pnum: u64 = capture[1].parse().unwrap_or(0);
        let title = capture[2].trim().to_owned();
        let start = matches[index].end();
        let end = matches
            .get(index + 1)
            .map_or(text.len(), regex::Match::start);
        let body = text[start..end].trim().to_owned();
        pieces.push((pnum, title, body));
    }
    pieces
}

/// Build the prepared-partition artifacts from the offline inputs.
///
/// `parent_plan_text` is `""` when the parent plan is absent; `original_title`
/// is the Step 0 route title (`""` when unbound). The returned artifacts are the
/// hash-compatible input the `/umbrella` consumer reads.
///
/// # Panics
///
/// Panics only if the compile-time `"plan"` named-block marker is rejected as
/// unsupported, which cannot happen for this fixed constant.
#[must_use]
#[allow(clippy::too_many_lines)] // Faithful port of the Python partition builder.
pub fn build_partition(
    partition_text: &str,
    parent_plan_text: &str,
    feature_text: &str,
    original_title: &str,
    issue_number: &str,
) -> BuildOutcome {
    if !partition_text.contains("## Pieces") {
        return BuildOutcome::status_only("invalid-partition-file");
    }
    let mut pieces = parse_pieces(partition_text);
    let piece_status = if pieces.is_empty() {
        "no-pieces"
    } else if pieces.len() < MIN_PARTITION_PIECES {
        "one-piece"
    } else if pieces
        .iter()
        .map(|(pnum, _, _)| *pnum)
        .collect::<BTreeSet<u64>>()
        .len()
        != pieces.len()
    {
        "bad-piece-number"
    } else {
        ""
    };
    if !piece_status.is_empty() {
        return BuildOutcome::status_only(piece_status);
    }
    pieces.sort_by_key(|(pnum, _, _)| *pnum);
    let index_by_num: std::collections::BTreeMap<u64, usize> = pieces
        .iter()
        .enumerate()
        .map(|(index, (pnum, _, _))| (*pnum, index))
        .collect();

    let parent_paths = extract_firm_scope_paths(parent_plan_text);
    let data = match collect_piece_data(&pieces, &index_by_num, parent_plan_text, &parent_paths) {
        Ok(data) => data,
        Err(status) => return BuildOutcome::status_only(&status),
    };

    if !acyclic(pieces.len(), &data.edges) {
        let witness = if data.edges.is_empty() {
            "(edges unavailable)".to_owned()
        } else {
            data.edges
                .iter()
                .map(|&(from, to)| {
                    format!("Piece {}\u{2192}Piece {}", pieces[from].0, pieces[to].0)
                })
                .collect::<Vec<_>>()
                .join("; ")
        };
        return BuildOutcome {
            status: "cycle-detected".to_owned(),
            witness,
            input_text: String::new(),
            deps: Vec::new(),
        };
    }

    let feat = {
        let neutralized_h3 = neutralize_markdown_h3_line_starts(feature_text);
        neutralize_named_block_markers(&neutralized_h3, "plan").expect("plan marker is supported")
    };
    let feat_excerpt: String = feat.chars().take(4000).collect();
    let orig = if is_ascii_digits(issue_number) {
        format!("#{issue_number}")
    } else {
        "(original issue \u{2014} set ISSUE_NUMBER in session)".to_owned()
    };
    let plan_block =
        neutralize_named_block_markers(&compose_named_block("plan", PLAN_STUB_INNER), "plan")
            .expect("plan marker is supported");

    let piece_count = pieces.len();
    let mut lines: Vec<String> = Vec::new();
    for (index, (pnum, title, _body)) in pieces.iter().enumerate() {
        let scope = &data.scopes[index];
        let firm_text = data.firm_heading_lines[index].join(", ");
        let acceptance_text = &data.acceptance_lines[index];
        let prefixed_title = prefixed_piece_title(original_title, issue_number, *pnum, title);
        lines.push(format!("### {prefixed_title}\n"));
        let scope_display = if scope.is_empty() {
            "(see parent partition file)"
        } else {
            scope.as_str()
        };
        let body_text = format!(
            "Partition piece {pnum} of {piece_count} split from {orig}.\n\n\
             **Scope**: {scope_display}\n\n\
             **Firm headings**: {firm_text}\n\n\
             **Acceptance**:\n\n{acceptance_text}\n\n\
             **Dependencies (from proposal)**: {dep}\n\n\
             ```\n{plan_block}```\n\n\
             **Original feature context (excerpt)**:\n\n{feat_excerpt}\n",
            dep = data.dep_lines[index],
        );
        lines.push(neutralize_markdown_h3_line_starts(&body_text));
    }
    let input_text = format!("{}\n", lines.join("\n"));
    let deps = data
        .edges
        .iter()
        .map(|&(from, to)| (from + 1, to + 1))
        .collect();
    BuildOutcome {
        status: "ok".to_owned(),
        witness: String::new(),
        input_text,
        deps,
    }
}

// ------------------------------------------------------------- filed mapping

/// Parse a filed-issue URL and confirm it names `expected_repo`.
///
/// # Errors
///
/// Returns the Python usage message when the URL is malformed or names a
/// different repository.
pub fn parse_issue_url(url: &str, expected_repo: &str) -> Result<u64, String> {
    let mismatch =
        || "migrate-deps: filed issue URL does not match the expected repository".to_owned();
    let matched = ISSUE_URL_RE.captures(url).ok_or_else(mismatch)?;
    if matched.get(1).map(|group| group.as_str()) != Some(expected_repo) {
        return Err(mismatch());
    }
    matched
        .get(2)
        .and_then(|group| group.as_str().parse().ok())
        .ok_or_else(mismatch)
}

/// Parse and validate the `.decompose-issues-filed` sentinel into filed pieces.
///
/// # Errors
///
/// Returns the Python usage message for an invalid record or an incomplete /
/// duplicate mapping.
pub fn parse_filed_pieces(sentinel_text: &str, repo: &str) -> Result<Vec<FiledPiece>, String> {
    let mut pieces: Vec<FiledPiece> = Vec::new();
    for line in sentinel_text.lines() {
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() != 3 || parts[0] != "PARTITION_FILE_MAP" || !is_ascii_digits(parts[1]) {
            return Err("migrate-deps: invalid annotation record".to_owned());
        }
        let piece: u64 = parts[1]
            .parse()
            .map_err(|_error| "migrate-deps: invalid annotation record".to_owned())?;
        let issue = parse_issue_url(parts[2], repo)?;
        pieces.push(FiledPiece {
            piece,
            issue,
            repo: repo.to_owned(),
        });
    }
    let piece_numbers: BTreeSet<u64> = pieces.iter().map(|piece| piece.piece).collect();
    let issue_numbers: BTreeSet<u64> = pieces.iter().map(|piece| piece.issue).collect();
    let expected: BTreeSet<u64> = (1..=pieces.len() as u64).collect();
    if pieces.len() < MIN_PARTITION_PIECES
        || piece_numbers.len() != pieces.len()
        || issue_numbers.len() != pieces.len()
        || piece_numbers != expected
    {
        return Err("migrate-deps: incomplete or duplicate filed mapping".to_owned());
    }
    pieces.sort_by_key(|piece| piece.piece);
    Ok(pieces)
}

/// Parse `partition-deps.tsv` into declared intra-piece blocked-by edges.
///
/// # Errors
///
/// Returns the Python usage message for a malformed row or an unknown piece.
// blocker/blocked piece and issue names mirror the wire grammar; the pairing is
// the point, so the near-identical spellings are intentional.
#[allow(clippy::similar_names)]
pub fn parse_intra_piece_edges(
    tsv_text: &str,
    pieces: &[FiledPiece],
) -> Result<Vec<PartitionEdge>, String> {
    let issue_by_piece: std::collections::BTreeMap<u64, u64> = pieces
        .iter()
        .map(|piece| (piece.piece, piece.issue))
        .collect();
    let mut edges = Vec::new();
    for line in tsv_text.lines() {
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() != 2 || !parts.iter().all(|part| is_ascii_digits(part)) {
            return Err("migrate-deps: invalid partition dependency row".to_owned());
        }
        let blocker_piece: u64 = parts[0]
            .parse()
            .map_err(|_error| "migrate-deps: invalid partition dependency row".to_owned())?;
        let blocked_piece: u64 = parts[1]
            .parse()
            .map_err(|_error| "migrate-deps: invalid partition dependency row".to_owned())?;
        let (Some(&blocked_issue), Some(&blocker_issue)) = (
            issue_by_piece.get(&blocked_piece),
            issue_by_piece.get(&blocker_piece),
        ) else {
            return Err(
                "migrate-deps: partition dependency references an unknown piece".to_owned(),
            );
        };
        if blocker_piece == blocked_piece {
            return Err(
                "migrate-deps: partition dependency references an unknown piece".to_owned(),
            );
        }
        edges.push(PartitionEdge {
            blocked: blocked_issue,
            blocker: blocker_issue,
        });
    }
    Ok(edges)
}

// -------------------------------------------------------- migration algorithm

/// The blocked-by edges the migration installs onto the filed pieces.
#[must_use]
pub fn replacement_edges(migration: &DependencyMigration) -> Vec<PartitionEdge> {
    let mut edges = Vec::new();
    for original in &migration.incoming {
        edges.extend(migration.pieces.iter().map(|piece| PartitionEdge {
            blocked: piece.issue,
            blocker: original.blocker,
        }));
    }
    for original in &migration.outgoing {
        edges.extend(migration.pieces.iter().map(|piece| PartitionEdge {
            blocked: original.blocked,
            blocker: piece.issue,
        }));
    }
    edges
}

fn edge_present(graph: &dyn DependencyGraph, edge: PartitionEdge) -> Result<bool, String> {
    let (blocked_by, _blocking) = graph.read_dependencies(edge.blocked)?;
    Ok(blocked_by.contains(&edge.blocker))
}

/// Whether every replacement edge is present and no original edge remains.
///
/// # Errors
///
/// Propagates a dependency-read failure.
pub fn migration_postcondition(
    graph: &dyn DependencyGraph,
    migration: &DependencyMigration,
) -> Result<bool, String> {
    for edge in replacement_edges(migration) {
        if !edge_present(graph, edge)? {
            return Ok(false);
        }
    }
    for edge in migration.incoming.iter().chain(&migration.outgoing) {
        if edge_present(graph, *edge)? {
            return Ok(false);
        }
    }
    Ok(true)
}

/// Whether the live original graph still matches the persisted migration.
///
/// # Errors
///
/// Propagates a dependency-read failure.
pub fn live_original_edges_match_migration(
    graph: &dyn DependencyGraph,
    migration: &DependencyMigration,
) -> Result<bool, String> {
    let (incoming_numbers, blocking_numbers) = graph.read_dependencies(migration.original_issue)?;
    let live_incoming: HashSet<PartitionEdge> = incoming_numbers
        .iter()
        .map(|&number| PartitionEdge {
            blocked: migration.original_issue,
            blocker: number,
        })
        .collect();
    let live_outgoing: HashSet<PartitionEdge> = blocking_numbers
        .iter()
        .map(|&number| PartitionEdge {
            blocked: number,
            blocker: migration.original_issue,
        })
        .collect();
    let expected_incoming: HashSet<PartitionEdge> = migration.incoming.iter().copied().collect();
    let expected_outgoing: HashSet<PartitionEdge> = migration.outgoing.iter().copied().collect();
    if !live_incoming
        .iter()
        .all(|edge| expected_incoming.contains(edge))
        || !live_outgoing
            .iter()
            .all(|edge| expected_outgoing.contains(edge))
    {
        return Ok(false);
    }
    for edge in expected_incoming.difference(&live_incoming) {
        for piece in &migration.pieces {
            if !edge_present(
                graph,
                PartitionEdge {
                    blocked: piece.issue,
                    blocker: edge.blocker,
                },
            )? {
                return Ok(false);
            }
        }
    }
    for edge in expected_outgoing.difference(&live_outgoing) {
        for piece in &migration.pieces {
            if !edge_present(
                graph,
                PartitionEdge {
                    blocked: edge.blocked,
                    blocker: piece.issue,
                },
            )? {
                return Ok(false);
            }
        }
    }
    Ok(true)
}

/// Whether every declared intra-piece edge is present in the live graph.
///
/// # Errors
///
/// Propagates a dependency-read failure.
pub fn intra_piece_postcondition(
    graph: &dyn DependencyGraph,
    intra_edges: &[PartitionEdge],
) -> Result<bool, String> {
    for edge in intra_edges {
        if !edge_present(graph, *edge)? {
            return Ok(false);
        }
    }
    Ok(true)
}

/// Apply the migration: install replacement edges, verify the original graph is
/// unchanged, remove the original edges, and re-verify.
///
/// # Errors
///
/// Propagates a dependency-read failure.
pub fn apply_migration(
    graph: &dyn DependencyGraph,
    migration: &DependencyMigration,
) -> Result<bool, String> {
    for edge in replacement_edges(migration) {
        if !edge_present(graph, edge)?
            && (!graph.mutate(false, edge.blocked, edge.blocker) || !edge_present(graph, edge)?)
        {
            return Ok(false);
        }
    }
    if !live_original_edges_match_migration(graph, migration)? {
        return Ok(false);
    }
    for edge in migration.incoming.iter().chain(&migration.outgoing) {
        if edge_present(graph, *edge)?
            && (!graph.mutate(true, edge.blocked, edge.blocker) || edge_present(graph, *edge)?)
        {
            return Ok(false);
        }
    }
    Ok(live_original_edges_match_migration(graph, migration)?
        && migration_postcondition(graph, migration)?)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn index_map(nums: &[u64]) -> std::collections::BTreeMap<u64, usize> {
        nums.iter()
            .enumerate()
            .map(|(index, num)| (*num, index))
            .collect()
    }

    #[test]
    fn prefixed_title_does_not_double_apply_bracket_or_token() {
        assert_eq!(
            prefixed_piece_title("plain title", "42", 1, "Base"),
            "split-42-1: Base"
        );
        assert_eq!(prefixed_piece_title("plain title", "", 1, "Base"), "Base");
        assert_eq!(
            prefixed_piece_title("[FEATURE] foo", "9", 2, "[FEATURE] API"),
            "[FEATURE] split-9-2: API"
        );
        assert_eq!(
            prefixed_piece_title(
                &format!("{} foo", crate::BUG_PREFIX),
                "3",
                1,
                "split-3-1: Base"
            ),
            format!("{} split-3-1: Base", crate::BUG_PREFIX)
        );
    }

    #[test]
    fn normalize_firm_heading_accepts_parent_plan_forms() {
        let cases = [
            (
                "`python/larch/design/decompose.py`",
                "python/larch/design/decompose.py",
            ),
            (
                "### NEW: `python/larch/design/decompose.py`",
                "python/larch/design/decompose.py",
            ),
            (
                "`### UPDATED: skills/design/references/decompose-panel.md`",
                "skills/design/references/decompose-panel.md",
            ),
            (
                "### REWRITTEN: `docs/issue-anchored-plan.md`",
                "docs/issue-anchored-plan.md",
            ),
            ("### MAY_UPDATE: `docs/optional.md`", "docs/optional.md"),
        ];
        for (value, expected) in cases {
            assert_eq!(normalize_firm_heading(value), expected);
        }
    }

    #[test]
    fn parse_dependency_three_valued_contract() {
        let index = index_map(&[1, 2, 3]);
        assert_eq!(parse_dependency("none", &index), Some(Vec::new()));
        assert_eq!(
            parse_dependency("blocked-by Piece 1", &index),
            Some(vec![1])
        );
        assert_eq!(
            parse_dependency("blocked-by Piece 1, Piece 2", &index),
            Some(vec![1, 2])
        );
        // Duplicate reference and unknown piece both reject.
        assert_eq!(
            parse_dependency("blocked-by Piece 1, Piece 1", &index),
            None
        );
        assert_eq!(parse_dependency("blocked-by Piece 9", &index), None);
    }

    #[test]
    fn happy_path_multi_blocker_and_neutralizes_feature() {
        let partition = "## Pieces\n\n\
            ### Piece 1: Base\n- Scope: base\n- Firm-headings: base/file.py\n- Acceptance: verify base\n- Dependencies: none\n\n\
            ### Piece 2: API\n- Scope: api\n- Firm-headings: api/file.py\n- Acceptance: verify api\n- Dependencies: blocked-by Piece 1\n\n\
            ### Piece 3: UI\n- Scope: ui\n- Firm-headings: ui/file.py\n- Acceptance: verify ui\n- Dependencies: blocked-by Piece 1, Piece 2\n";
        let feature = "Feature\n### embedded heading\n";
        let outcome = build_partition(partition, "", feature, "", "123");
        assert_eq!(outcome.status, "ok");
        assert_eq!(outcome.deps, vec![(1, 2), (1, 3), (2, 3)]);
        assert!(outcome.input_text.contains("#123"));
        assert!(outcome.input_text.contains("\u{200b}### embedded heading"));
    }

    #[test]
    fn prefixed_titles_preserve_bracket_and_drop_lifecycle() {
        let partition = "## Pieces\n\n\
            ### Piece 1: Base\n- Scope: base\n- Firm-headings: base/file.py\n- Acceptance: verify base\n- Dependencies: none\n\n\
            ### Piece 2: API\n- Scope: api\n- Firm-headings: api/file.py\n- Acceptance: verify api\n- Dependencies: none\n";
        let outcome = build_partition(
            partition,
            "",
            "Feature\n",
            "[DESIGNING] [BUG] when /design splits",
            "7277",
        );
        assert_eq!(outcome.status, "ok");
        assert!(
            outcome
                .input_text
                .contains("### [BUG] split-7277-1: Base\n")
        );
        assert!(!outcome.input_text.contains("[DESIGNING]"));
    }

    #[test]
    fn rejects_bad_dependency_and_detects_cycle() {
        let bad = "## Pieces\n\n### Piece 1: A\n- Firm-headings: a.py\n- Acceptance: a\n- Dependencies: blocked-by Piece 3\n\n### Piece 2: B\n- Firm-headings: b.py\n- Acceptance: b\n- Dependencies: none\n";
        assert_eq!(
            build_partition(bad, "", "", "", "").status,
            "bad-dependency-ref"
        );
        let cycle = "## Pieces\n\n\
            ### Piece 1: A\n- Firm-headings: a.py\n- Acceptance: verify a\n- Dependencies: blocked-by Piece 2\n\n\
            ### Piece 2: B\n- Firm-headings: b.py\n- Acceptance: verify b\n- Dependencies: blocked-by Piece 1\n";
        let outcome = build_partition(cycle, "", "", "", "");
        assert_eq!(outcome.status, "cycle-detected");
        assert!(outcome.witness.contains("Piece"));
    }

    #[test]
    fn preserves_only_declared_dependency_with_parent_plan() {
        let plan = "## Files to modify\n\n\
            ### UPDATED: `python/larch/design/a.py`\n\
            ### UPDATED: `python/larch/design/b.py`\n\
            ### UPDATED: `python/larch/design/c.py`\n\n\
            ## Testing strategy\n\n\
            - Cover python/larch/design/a.py behavior.\n\
            - Cover python/larch/design/b.py behavior.\n\
            - Cover python/larch/design/c.py behavior.\ndiff_lines: 10\n";
        let partition = "## Pieces\n\n\
            ### Piece 1: A\n- Scope: python/larch/design/a.py\n- Firm-headings: python/larch/design/a.py\n- Acceptance: cover a\n- Dependencies: none\n\n\
            ### Piece 2: B\n- Scope: python/larch/design/b.py\n- Firm-headings: python/larch/design/b.py\n- Acceptance: cover b\n- Dependencies: blocked-by Piece 3\n\n\
            ### Piece 3: C\n- Scope: python/larch/design/c.py\n- Firm-headings: python/larch/design/c.py\n- Acceptance: cover c\n- Dependencies: none\n";
        let outcome = build_partition(partition, plan, "Feature\n", "", "123");
        assert_eq!(outcome.status, "ok");
        assert_eq!(outcome.deps, vec![(3, 2)]);
    }

    #[test]
    fn firm_heading_coverage_mismatch_and_missing_metadata() {
        let plan = "## Files to modify/create\n\n### UPDATED: `python/larch/design/a.py`\n### UPDATED: `python/larch/design/b.py`\ndiff_lines: 10\n";
        let partition = "## Pieces\n\n### Piece 1: A\n- Firm-headings: python/larch/design/a.py\n- Acceptance: cover a\n- Dependencies: none\n\n### Piece 2: B\n- Firm-headings: python/larch/design/a.py\n- Acceptance: cover b\n- Dependencies: none\n";
        assert_eq!(
            build_partition(partition, plan, "", "", "").status,
            "firm-heading-coverage-mismatch"
        );
        let plan2 =
            "## Files to modify\n\n### UPDATED: `python/larch/design/a.py`\ndiff_lines: 10\n";
        let partition2 = "## Pieces\n\n### Piece 1: A\n- Scope: docs/other.md\n- Dependencies: none\n\n### Piece 2: B\n- Scope: docs/also.md\n- Dependencies: none\n";
        assert_eq!(
            build_partition(partition2, plan2, "", "", "").status,
            "missing-piece-metadata"
        );
    }

    #[test]
    fn piece_count_gates() {
        assert_eq!(
            build_partition("no pieces here", "", "", "", "").status,
            "invalid-partition-file"
        );
        assert_eq!(
            build_partition("## Pieces\n\n", "", "", "", "").status,
            "no-pieces"
        );
        let one = "## Pieces\n\n### Piece 1: A\n- Firm-headings: a.py\n- Acceptance: a\n- Dependencies: none\n";
        assert_eq!(build_partition(one, "", "", "", "").status, "one-piece");
    }

    #[test]
    fn filed_pieces_rejects_non_unique_or_non_contiguous() {
        let dup = "PARTITION_FILE_MAP\t1\thttps://github.com/o/r/issues/101\nPARTITION_FILE_MAP\t2\thttps://github.com/o/r/issues/101\n";
        assert!(parse_filed_pieces(dup, "o/r").is_err());
        let gap = "PARTITION_FILE_MAP\t1\thttps://github.com/o/r/issues/101\nPARTITION_FILE_MAP\t3\thttps://github.com/o/r/issues/103\n";
        assert!(parse_filed_pieces(gap, "o/r").is_err());
        let good = "PARTITION_FILE_MAP\t1\thttps://github.com/o/r/issues/101\nPARTITION_FILE_MAP\t2\thttps://github.com/o/r/issues/102\n";
        let pieces = parse_filed_pieces(good, "o/r").expect("valid mapping");
        assert_eq!(pieces.len(), 2);
        assert_eq!(pieces[0].issue, 101);
    }

    struct FakeGraph {
        blocked_by: std::cell::RefCell<std::collections::BTreeMap<u64, BTreeSet<u64>>>,
    }

    impl DependencyGraph for FakeGraph {
        fn read_dependencies(&self, issue: u64) -> Result<(Vec<u64>, Vec<u64>), String> {
            let map = self.blocked_by.borrow();
            let incoming: Vec<u64> = map
                .get(&issue)
                .map(|set| set.iter().copied().collect())
                .unwrap_or_default();
            let outgoing: Vec<u64> = map
                .iter()
                .filter(|(_key, value)| value.contains(&issue))
                .map(|(key, _value)| *key)
                .collect();
            Ok((incoming, outgoing))
        }

        #[allow(clippy::similar_names)] // blocked/blocker is the domain contract.
        fn mutate(&self, remove: bool, blocked: u64, blocker: u64) -> bool {
            let mut map = self.blocked_by.borrow_mut();
            let entry = map.entry(blocked).or_default();
            if remove {
                entry.remove(&blocker);
            } else {
                entry.insert(blocker);
            }
            true
        }
    }

    #[test]
    fn apply_migration_replaces_incoming_and_outgoing_edges() {
        let mut initial = std::collections::BTreeMap::new();
        initial.insert(99u64, BTreeSet::from([7u64]));
        initial.insert(101u64, BTreeSet::new());
        initial.insert(102u64, BTreeSet::from([101u64]));
        initial.insert(8u64, BTreeSet::from([99u64]));
        let graph = FakeGraph {
            blocked_by: std::cell::RefCell::new(initial),
        };
        let pieces = vec![
            FiledPiece {
                piece: 1,
                issue: 101,
                repo: "o/r".to_owned(),
            },
            FiledPiece {
                piece: 2,
                issue: 102,
                repo: "o/r".to_owned(),
            },
        ];
        let migration = DependencyMigration {
            schema_version: "1".to_owned(),
            original_issue: 99,
            repo: "o/r".to_owned(),
            pieces,
            incoming: vec![PartitionEdge {
                blocked: 99,
                blocker: 7,
            }],
            outgoing: vec![PartitionEdge {
                blocked: 8,
                blocker: 99,
            }],
        };
        assert_eq!(apply_migration(&graph, &migration), Ok(true));
        let map = graph.blocked_by.borrow();
        assert_eq!(map[&101], BTreeSet::from([7]));
        assert_eq!(map[&102], BTreeSet::from([7, 101]));
        assert_eq!(map[&8], BTreeSet::from([101, 102]));
        assert_eq!(map[&99], BTreeSet::new());
    }

    #[test]
    fn intra_piece_edges_parse_and_reject() {
        let pieces = vec![
            FiledPiece {
                piece: 1,
                issue: 101,
                repo: "o/r".to_owned(),
            },
            FiledPiece {
                piece: 2,
                issue: 102,
                repo: "o/r".to_owned(),
            },
        ];
        let edges = parse_intra_piece_edges("1\t2\n", &pieces).expect("valid tsv");
        assert_eq!(
            edges,
            vec![PartitionEdge {
                blocked: 102,
                blocker: 101
            }]
        );
        assert!(parse_intra_piece_edges("1\t9\n", &pieces).is_err());
        assert!(parse_intra_piece_edges("1\t1\n", &pieces).is_err());
    }
}
