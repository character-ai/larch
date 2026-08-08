//! Which deferred items may be filed together, and in which order.
//!
//! Ports the conflict half of Python `larch.issue.file_oos` and the create
//! ordering in `larch.issue.oos_filer`. Two out-of-scope items that touch the
//! same lines of the same file cannot be worked in parallel, so filing records
//! a dependency edge between them. The edge is derived from the item's own
//! prose: reviewers write `path/to/file.rs:120-140`, and that is the only
//! signal available before anything is filed.
//!
//! Item bodies are untrusted operator and reviewer text, so path extraction is
//! deliberately narrow. A candidate that escapes its repository, names an
//! absolute path, or could read as an option is dropped rather than repaired,
//! and dropping one only loses an edge — it never creates a wrong one.
//!
//! Two caps bound the blast radius. A cluster whose all-pairs edge count would
//! exceed the cluster cap degrades to a chain, which keeps the ordering honest
//! while shrinking the row count. A plan that still exceeds the global cap is
//! refused, because the downstream batch reader would reject the file anyway.

use crate::issue::input::ParsedItem;
use crate::text::{
    file_reference_alternatives, positive_integer, split_text_lines, trim_python_whitespace,
    unsigned_integer,
};
use regex::Regex;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write as _;
use std::sync::LazyLock;

/// Default per-cluster all-pairs edge budget before chain degradation.
pub const FILE_CONFLICT_DEFAULT_CLUSTER_CAP: usize = 200;
/// Default total row budget: Python `config.ISSUE_INTRA_BATCH_DEPS_MAX_ROWS`,
/// which is the same bound `/issue` enforces on `--intra-batch-deps-file`.
pub const FILE_CONFLICT_DEFAULT_GLOBAL_CAP: usize = 500;
/// A component smaller than this cannot carry an edge.
const MIN_COMPONENT_NODES: usize = 2;
/// Placeholder that hides `..` from the `./` normalizer, then is restored.
const TRAVERSAL_PLACEHOLDER: &str = "\u{1e}";

static FILE_REFERENCE_RE: LazyLock<Regex> = LazyLock::new(|| {
    let [long, short_path, short_line, extensionless] = file_reference_alternatives(false);
    Regex::new(&format!(
        "(?:{long}|{short_path}|{short_line})|(?:{extensionless})"
    ))
    .expect("file reference expression")
});
static RANGE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^(.+):([0-9]+)(-([0-9]+))?$").expect("range expression"));
static SAFE_PATH_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[A-Za-z0-9_./-]+$").expect("safe path expression"));
static LEADING_NOISE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"^[^A-Za-z.]+").expect("leading noise expression"));
static TRAILING_NOISE_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"[^A-Za-z0-9_./:-]+$").expect("trailing noise expression"));
static DOT_SLASH_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(^|[^A-Za-z0-9])\./").expect("dot slash expression"));

/// One file region an item claims.
///
/// `whole` marks a reference with no line range: it conflicts with every other
/// reference to the same path, because the item may touch any of it.
#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct FileConflictRecord {
    /// The repository-relative path, already proven safe.
    pub path: String,
    /// First line of the claimed range, or `0` for a whole-file claim.
    pub start: u64,
    /// Last line of the claimed range, or `0` for a whole-file claim.
    pub end: u64,
    /// Whether the reference claims the whole file.
    pub whole: bool,
}

/// One conflict between two one-based item indices.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FileConflictEdge {
    /// The lower item index.
    pub left: usize,
    /// The higher item index.
    pub right: usize,
    /// Basename of the first path the two items collided on.
    pub basename: String,
}

/// Why a conflict plan could not be produced.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FileConflictError {
    /// The plan exceeds the batch reader's total row budget.
    GlobalCapExceeded {
        /// How many rows the plan would emit.
        rows: usize,
        /// The budget it exceeded.
        cap: usize,
    },
}

impl FileConflictError {
    /// Render the exact diagnostic the caller reports.
    #[must_use]
    pub fn message(&self) -> String {
        let Self::GlobalCapExceeded { rows, cap } = *self;
        format!(
            "ERROR: oos-file-conflict-deps would emit {rows} rows, exceeding the {cap}-row --intra-batch-deps-file cap; split the OOS batch"
        )
    }
}

/// A planned dependency set and the degradations that produced it.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ConflictPlan {
    /// Deduplicated, sorted `(blocker, blocked)` rows.
    pub deps: Vec<(usize, usize)>,
    /// One line per cluster that degraded from all-pairs to a chain.
    pub warnings: Vec<String>,
}

/// Read a positive cap knob, refusing every other spelling.
#[must_use]
pub fn parse_conflict_cap(raw: &str) -> Option<usize> {
    positive_integer(raw).and_then(|value| usize::try_from(value).ok())
}

/// Replace `./` prefixes and list separators so one line yields one reference.
///
/// `..` is hidden first: the `./` rewrite would otherwise turn `../x` into
/// `..x` and hide the traversal the safety check is looking for.
fn normalize_body(body: &str) -> String {
    let protected = body.replace("..", TRAVERSAL_PLACEHOLDER);
    let without_dot_slash = DOT_SLASH_RE.replace_all(&protected, "${1}");
    without_dot_slash
        .replace([',', ';'], "\n")
        .replace(TRAVERSAL_PLACEHOLDER, "..")
}

/// Trim the punctuation the file-reference match swept in on either side.
fn clean_match(raw: &str) -> String {
    let leading = LEADING_NOISE_RE.replace(raw, "");
    let trimmed = TRAILING_NOISE_RE.replace(&leading, "");
    trimmed.strip_prefix("./").unwrap_or(&trimmed).to_owned()
}

/// Report whether a candidate path is safe to treat as repository-relative.
fn path_is_safe(path: &str) -> bool {
    !path.is_empty()
        && !path.starts_with('/')
        && !path.starts_with('-')
        && !path.contains("..")
        && !path.contains(':')
        && SAFE_PATH_RE.is_match(path)
}

/// Turn one cleaned candidate into a record, or drop it.
fn conflict_record(candidate: &str) -> Option<FileConflictRecord> {
    let mut path = candidate;
    let (mut start, mut end, mut whole) = (0, 0, true);
    if let Some(captures) = RANGE_RE.captures(candidate) {
        path = captures.get(1).expect("range path group").as_str();
        let parsed_start = unsigned_integer(&captures[2]).unwrap_or(u64::MAX);
        let parsed_end = captures.get(4).map_or(parsed_start, |found| {
            unsigned_integer(found.as_str()).unwrap_or(u64::MAX)
        });
        if parsed_start > 0 && parsed_start <= parsed_end {
            start = parsed_start;
            end = parsed_end;
            whole = false;
        }
    }
    let path = path.strip_prefix("./").unwrap_or(path);
    path_is_safe(path).then(|| FileConflictRecord {
        path: path.to_owned(),
        start,
        end,
        whole,
    })
}

/// Extract every safe file reference one item's body claims.
#[must_use]
pub fn item_file_records(item: &ParsedItem) -> Vec<FileConflictRecord> {
    let normalized = normalize_body(&item.body);
    let mut records: BTreeSet<FileConflictRecord> = BTreeSet::new();
    for line in split_text_lines(&normalized) {
        for found in FILE_REFERENCE_RE.find_iter(line) {
            if line[..found.start()].ends_with("..") || found.as_str().contains("..") {
                continue;
            }
            let candidate = clean_match(found.as_str());
            if let Some(record) = conflict_record(&candidate) {
                records.insert(record);
            }
        }
    }
    records.into_iter().collect()
}

/// Report whether two records on the same path claim overlapping lines.
fn ranges_conflict(left: &FileConflictRecord, right: &FileConflictRecord) -> bool {
    left.path == right.path
        && (left.whole || right.whole || !(left.start > right.end || right.start > left.end))
}

/// Report whether two items collide on one shared path.
fn path_conflicts<'a>(
    left: &'a [FileConflictRecord],
    right: &'a [FileConflictRecord],
    path: &str,
) -> bool {
    let for_path = |records: &'a [FileConflictRecord]| -> Vec<&'a FileConflictRecord> {
        records
            .iter()
            .filter(|record| record.path == path)
            .collect()
    };
    let (left_records, right_records) = (for_path(left), for_path(right));
    if left_records
        .iter()
        .chain(&right_records)
        .any(|record| record.whole)
    {
        return true;
    }
    left_records.iter().any(|one| {
        right_records
            .iter()
            .any(|other| ranges_conflict(one, other))
    })
}

fn find_parent(parent: &mut [usize], node: usize) -> usize {
    let mut root = node;
    while parent[root] != root {
        root = parent[root];
    }
    let mut current = node;
    while parent[current] != current {
        let next = parent[current];
        parent[current] = root;
        current = next;
    }
    root
}

/// Merge two components, keeping the lower root so labels stay deterministic.
fn union_nodes(parent: &mut [usize], left: usize, right: usize) {
    let left_root = find_parent(parent, left);
    let right_root = find_parent(parent, right);
    if left_root == right_root {
        return;
    }
    let (keep, drop) = (left_root.min(right_root), left_root.max(right_root));
    for node in 1..parent.len() {
        if find_parent(parent, node) == drop {
            parent[node] = keep;
        }
    }
}

/// Return the last non-empty path segment, as `PurePosixPath.name` does.
fn basename(path: &str) -> String {
    path.rsplit('/')
        .find(|segment| !segment.is_empty())
        .unwrap_or("")
        .to_owned()
}

/// Return every candidate edge plus the component label of each item.
fn candidate_edges(items: &[ParsedItem]) -> (Vec<FileConflictEdge>, Vec<usize>) {
    let records: Vec<Vec<FileConflictRecord>> = items
        .iter()
        .map(|item| {
            if item.malformed {
                Vec::new()
            } else {
                item_file_records(item)
            }
        })
        .collect();
    let mut parent: Vec<usize> = (0..=items.len()).collect();
    let mut edges = Vec::new();
    for left in 1..=items.len() {
        for right in left + 1..=items.len() {
            let left_paths: BTreeSet<&str> = records[left - 1]
                .iter()
                .map(|record| record.path.as_str())
                .collect();
            let shared: Vec<&str> = records[right - 1]
                .iter()
                .map(|record| record.path.as_str())
                .filter(|path| left_paths.contains(path))
                .collect::<BTreeSet<&str>>()
                .into_iter()
                .collect();
            for path in shared {
                if path_conflicts(&records[left - 1], &records[right - 1], path) {
                    edges.push(FileConflictEdge {
                        left,
                        right,
                        basename: basename(path),
                    });
                    union_nodes(&mut parent, left, right);
                    break;
                }
            }
        }
    }
    let mut roots = Vec::with_capacity(parent.len());
    for index in 0..parent.len() {
        roots.push(find_parent(&mut parent, index));
    }
    (edges, roots)
}

/// Render the warning a degraded cluster reports.
fn chain_warning(basename: &str, edges: usize, cap: usize, nodes: usize) -> String {
    format!(
        "**⚠ /implement: oos-file-conflict-deps cluster on {basename} would emit {edges} dependency rows (cap {cap}, N={nodes}); emitting chain instead of all-pairs (lower robustness under SCC pruning).**"
    )
}

/// Plan the intra-batch dependency rows for one parsed OOS batch.
///
/// # Errors
///
/// Returns [`FileConflictError::GlobalCapExceeded`] when the deduplicated plan
/// is larger than the batch reader accepts.
pub fn plan_file_conflict_deps(
    items: &[ParsedItem],
    cluster_cap: usize,
    global_cap: usize,
) -> Result<ConflictPlan, FileConflictError> {
    let (candidates, roots) = candidate_edges(items);
    let mut nodes_by_root: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for (index, root) in roots.iter().enumerate().skip(1) {
        nodes_by_root.entry(*root).or_default().push(index);
    }
    let mut plan = ConflictPlan::default();
    let mut planned: BTreeSet<(usize, usize)> = BTreeSet::new();
    for nodes in nodes_by_root.values() {
        if nodes.len() < MIN_COMPONENT_NODES {
            continue;
        }
        let cluster: Vec<&FileConflictEdge> = candidates
            .iter()
            .filter(|edge| nodes.contains(&edge.left) && nodes.contains(&edge.right))
            .collect();
        if cluster.len() > cluster_cap {
            let hint = cluster
                .first()
                .map_or("unknown", |edge| edge.basename.as_str());
            plan.warnings
                .push(chain_warning(hint, cluster.len(), cluster_cap, nodes.len()));
            planned.extend(nodes.windows(2).map(|pair| (pair[0], pair[1])));
        } else {
            planned.extend(cluster.iter().map(|edge| (edge.left, edge.right)));
        }
    }
    if planned.len() > global_cap {
        return Err(FileConflictError::GlobalCapExceeded {
            rows: planned.len(),
            cap: global_cap,
        });
    }
    plan.deps = planned.into_iter().collect();
    Ok(plan)
}

/// Render dependency rows as the tab-separated batch file.
#[must_use]
pub fn render_deps_tsv(deps: &[(usize, usize)]) -> String {
    deps.iter()
        .fold(String::new(), |mut rendered, (left, right)| {
            let _ = writeln!(rendered, "{left}\t{right}");
            rendered
        })
}

/// Read dependency rows back, ignoring every line that is not a pair.
#[must_use]
pub fn parse_intra_batch_deps(text: &str) -> Vec<(usize, usize)> {
    let mut edges = Vec::new();
    for line in split_text_lines(text) {
        if trim_python_whitespace(line).is_empty() {
            continue;
        }
        let fields: Vec<&str> = line.split('\t').collect();
        let [first, second] = fields.as_slice() else {
            continue;
        };
        if let (Some(blocker), Some(blocked)) = (parse_node(first), parse_node(second)) {
            edges.push((blocker, blocked));
        }
    }
    edges
}

fn parse_node(value: &str) -> Option<usize> {
    unsigned_integer(value).and_then(|parsed| usize::try_from(parsed).ok())
}

/// Order items for creation so every blocker is filed before what it blocks.
///
/// The order is total and independent of edge order: ready items are always
/// taken lowest first. An edge set that cannot be ordered — a cycle, or one
/// naming an item outside the batch — falls back to plain index order rather
/// than filing a partial batch.
#[must_use]
pub fn topological_create_order(total: usize, edges: &[(usize, usize)]) -> Vec<usize> {
    let sequential = || (1..=total).collect::<Vec<usize>>();
    if total == 0 {
        return Vec::new();
    }
    if edges.is_empty() {
        return sequential();
    }
    let mut blocked_by: BTreeMap<usize, BTreeSet<usize>> =
        (1..=total).map(|index| (index, BTreeSet::new())).collect();
    let mut blocks: BTreeMap<usize, BTreeSet<usize>> =
        (1..=total).map(|index| (index, BTreeSet::new())).collect();
    for &(blocker, blocked) in edges {
        if blocker == blocked || blocker == 0 || blocked == 0 || blocker > total || blocked > total
        {
            continue;
        }
        blocked_by.entry(blocked).or_default().insert(blocker);
        blocks.entry(blocker).or_default().insert(blocked);
    }
    let mut ready: Vec<usize> = (1..=total)
        .filter(|index| blocked_by[index].is_empty())
        .collect();
    let mut order: Vec<usize> = Vec::new();
    while !ready.is_empty() {
        let current = ready.remove(0);
        order.push(current);
        for dependent in blocks[&current].clone() {
            let waiting = blocked_by.entry(dependent).or_default();
            waiting.remove(&current);
            if waiting.is_empty() {
                ready.push(dependent);
            }
        }
        ready.sort_unstable();
    }
    if order.len() == total {
        order
    } else {
        sequential()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        ConflictPlan, FileConflictError, item_file_records, parse_conflict_cap,
        parse_intra_batch_deps, plan_file_conflict_deps, render_deps_tsv, topological_create_order,
    };
    use crate::issue::input::ParsedItem;

    fn item(body: &str) -> ParsedItem {
        ParsedItem {
            body: body.to_owned(),
            ..ParsedItem::default()
        }
    }

    fn paths(body: &str) -> Vec<String> {
        item_file_records(&item(body))
            .into_iter()
            .map(|record| record.path)
            .collect()
    }

    #[test]
    fn references_are_extracted_from_reviewer_prose() {
        let records = item_file_records(&item("See ./a/b.py:10-20, a/b.py:40 and Makefile.\n"));
        assert_eq!(records.len(), 3);
        assert_eq!(records[0].path, "Makefile");
        assert!(records[0].whole);
        assert_eq!(
            (records[1].start, records[1].end, records[1].whole),
            (10, 20, false)
        );
        assert_eq!(
            (records[2].start, records[2].end, records[2].whole),
            (40, 40, false)
        );
    }

    #[test]
    fn traversal_candidates_are_dropped_rather_than_repaired() {
        assert!(paths("../secrets/keys.py").is_empty());
        assert!(paths("see ../../etc/passwd.py here").is_empty());
        assert_eq!(paths("x/a.py"), ["x/a.py"]);
    }

    #[test]
    fn leading_separators_are_cleaned_off_before_the_safety_check() {
        assert_eq!(paths("/etc/hosts.toml"), ["etc/hosts.toml"]);
        assert_eq!(paths("-rf/a.py"), ["rf/a.py"]);
        assert_eq!(paths("`src/main.rs:12`"), ["src/main.rs"]);
    }

    #[test]
    fn an_invalid_range_degrades_to_a_whole_file_claim() {
        let records = item_file_records(&item("a/b.py:0\n"));
        assert_eq!(records.len(), 1);
        assert!(records[0].whole);
        let backwards = item_file_records(&item("a/b.py:30-10\n"));
        assert!(backwards[0].whole);
    }

    #[test]
    fn a_malformed_item_claims_nothing() {
        let malformed = ParsedItem {
            malformed: true,
            ..item("a/b.py:1-2")
        };
        let plan =
            plan_file_conflict_deps(&[malformed, item("a/b.py:1-2")], 200, 500).expect("plan");
        assert_eq!(plan, ConflictPlan::default());
    }

    #[test]
    fn overlapping_ranges_conflict_and_disjoint_ranges_do_not() {
        let overlap = plan_file_conflict_deps(
            &[
                item("a/b.py:10-20"),
                item("a/b.py:15-25"),
                item("a/b.py:100-110"),
            ],
            200,
            500,
        )
        .expect("plan");
        assert_eq!(overlap.deps, [(1, 2)]);
        assert!(overlap.warnings.is_empty());
    }

    #[test]
    fn a_whole_file_claim_conflicts_with_every_range() {
        let plan = plan_file_conflict_deps(
            &[item("a/b.py"), item("a/b.py:15-25"), item("c/d.py:1")],
            200,
            500,
        )
        .expect("plan");
        assert_eq!(plan.deps, [(1, 2)]);
    }

    #[test]
    fn a_dense_cluster_degrades_to_a_chain_with_one_warning() {
        let items: Vec<ParsedItem> = (0..4).map(|_| item("a/b.py")).collect();
        let plan = plan_file_conflict_deps(&items, 2, 500).expect("plan");
        assert_eq!(plan.deps, [(1, 2), (2, 3), (3, 4)]);
        assert_eq!(plan.warnings.len(), 1);
        assert!(
            plan.warnings[0].contains("cluster on b.py would emit 6 dependency rows (cap 2, N=4)")
        );
    }

    #[test]
    fn an_oversized_plan_is_refused_with_its_row_count() {
        let items: Vec<ParsedItem> = (0..4).map(|_| item("a/b.py")).collect();
        let error = plan_file_conflict_deps(&items, 200, 2).expect_err("cap");
        assert_eq!(
            error,
            FileConflictError::GlobalCapExceeded { rows: 6, cap: 2 }
        );
        assert!(
            error
                .message()
                .starts_with("ERROR: oos-file-conflict-deps would emit 6 rows")
        );
    }

    #[test]
    fn separate_components_keep_their_own_edges() {
        let plan = plan_file_conflict_deps(
            &[
                item("a/b.py"),
                item("c/d.py"),
                item("a/b.py"),
                item("c/d.py"),
            ],
            200,
            500,
        )
        .expect("plan");
        assert_eq!(plan.deps, [(1, 3), (2, 4)]);
    }

    #[test]
    fn dependency_rows_round_trip_through_the_batch_file() {
        let deps = [(1, 2), (2, 3)];
        let rendered = render_deps_tsv(&deps);
        assert_eq!(rendered, "1\t2\n2\t3\n");
        assert_eq!(parse_intra_batch_deps(&rendered), deps);
        assert_eq!(
            parse_intra_batch_deps("\n\nx\ty\n1\t2\t3\n1\t2\n"),
            [(1, 2)]
        );
        assert!(parse_intra_batch_deps("").is_empty());
    }

    #[test]
    fn creation_order_is_independent_of_edge_order() {
        let forward = topological_create_order(4, &[(3, 1), (4, 2)]);
        let reversed = topological_create_order(4, &[(4, 2), (3, 1)]);
        assert_eq!(forward, [3, 1, 4, 2]);
        assert_eq!(forward, reversed);
        assert_eq!(topological_create_order(3, &[]), [1, 2, 3]);
        assert!(topological_create_order(0, &[(1, 2)]).is_empty());
    }

    #[test]
    fn an_unorderable_edge_set_falls_back_to_index_order() {
        assert_eq!(topological_create_order(2, &[(1, 2), (2, 1)]), [1, 2]);
        assert_eq!(
            topological_create_order(2, &[(1, 1), (0, 2), (9, 1)]),
            [1, 2]
        );
    }

    #[test]
    fn cap_knobs_accept_only_positive_decimals() {
        assert_eq!(parse_conflict_cap("200"), Some(200));
        assert_eq!(super::FILE_CONFLICT_DEFAULT_CLUSTER_CAP, 200);
        assert_eq!(super::FILE_CONFLICT_DEFAULT_GLOBAL_CAP, 500);
        for refused in ["0", "-1", "", " 5", "5.0", "two"] {
            assert_eq!(parse_conflict_cap(refused), None, "{refused}");
        }
    }
}
