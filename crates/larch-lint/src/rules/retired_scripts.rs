//! Reject references to paths recorded as retired by the Python migration.
//!
//! # Crate survey (issue #7609)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | Tracked-file discovery | direct `git ls-files`, shared `Repository` | Reuse the validated repository snapshot and restrict the scan to indexed paths, matching the retired-reference contract. |
//! | Path selection | filesystem walk, workspace `globset` | Use the repository's stable path list; the small exclusion set is exact-path policy rather than a glob family. |
//! | Text matching | handwritten byte scan, workspace `regex` | Reuse `regex` for bare-basename boundaries; bespoke code remains limited to larch's manifest and legacy-shim semantics. |

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
    sync::LazyLock,
};

use regex::Regex;

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "retired-scripts";
const DESCRIPTION: &str = "Reject references to retired script paths";
const MANIFEST_PATH: &str = "python/migrated-scripts.tsv";
const IMPLEMENT_SKILL_PATH: &str = "skills/implement/SKILL.md";
const EMBEDDED_LEGACY_MODULES: [&str; 1] = ["python/larch/review/plan_review.py"];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/retired-scripts.toml",
);

#[derive(Debug)]
pub struct RetiredScriptsRule;

pub static RULE: RetiredScriptsRule = RetiredScriptsRule;

impl Rule for RetiredScriptsRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let retired = manifest_paths(repository)?;
        if retired.is_empty() {
            return Ok(output(Vec::new(), 0, 0, 0));
        }

        let still_present: Vec<_> = retired
            .iter()
            .filter(|path| repository.root().join(path).exists())
            .cloned()
            .collect();
        if !still_present.is_empty() {
            let findings = still_present
                .into_iter()
                .map(|path| Finding::new(path, 1, "retired path is still present in the tree"))
                .collect();
            return Ok(output(findings, retired.len(), 0, 0));
        }

        let retired_by_basename = RetiredLookup::new(&retired)?;
        let mut findings = Vec::new();
        for path in repository
            .paths()
            .iter()
            .filter(|path| repository.is_committed(path) && included(path.as_str()))
        {
            let bytes = repository.read_bytes(path)?;
            if bytes.contains(&0) {
                continue;
            }
            let source = String::from_utf8_lossy(&bytes);
            let rel_dir = parent(path.as_str());
            for (index, line) in source.lines().enumerate() {
                let candidates = retired_by_basename.candidates(line);
                for retired_path in candidates {
                    if line_references_retired(
                        repository,
                        path.as_str(),
                        rel_dir,
                        line,
                        retired_path,
                    ) {
                        findings.push(Finding::new(
                            path.as_str(),
                            line_number(index),
                            format!("references retired path {retired_path:?}"),
                        ));
                    }
                }
            }
        }

        let embedded = embedded_legacy_paths(repository, &retired)?;
        let ref_count = findings.len();
        Ok(output(findings, retired.len(), ref_count, embedded.len()))
    }
}

crate::register_rule!(METADATA, RULE);

fn manifest_paths(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    let manifest = RepoPath::from_trusted(MANIFEST_PATH);
    let source = repository.read_required_utf8(
        &manifest,
        format!("manifest not found: {MANIFEST_PATH}"),
    )?;
    let mut retired = BTreeSet::new();
    for (index, raw) in source.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let mut fields = line.split('\t');
        let path = fields.next().unwrap_or_default().trim();
        if path.is_empty() || fields.next().is_none() {
            return Err(LintError::new(format!(
                "manifest line {} malformed (expected path<TAB>retired_by): {raw:?}",
                line_number(index)
            )));
        }
        validate_manifest_path(path)?;
        retired.insert(path.to_owned());
    }
    Ok(retired)
}

fn validate_manifest_path(path: &str) -> Result<(), LintError> {
    let candidate = Path::new(path);
    if candidate.is_absolute()
        || candidate.components().any(|component| {
            matches!(
                component,
                std::path::Component::CurDir
                    | std::path::Component::ParentDir
                    | std::path::Component::RootDir
                    | std::path::Component::Prefix(_)
            )
        })
    {
        return Err(LintError::new(format!("unsafe retired manifest path: {path:?}")));
    }
    Ok(())
}

#[derive(Debug)]
struct RetiredLookup {
    paths: BTreeMap<String, Vec<String>>,
    matcher: Regex,
}

impl RetiredLookup {
    fn new(retired: &BTreeSet<String>) -> Result<Self, LintError> {
        let paths = by_basename(retired);
        let expression = paths
            .keys()
            .map(|basename| regex::escape(basename))
            .collect::<Vec<_>>()
            .join("|");
        let matcher = Regex::new(&format!("(?:{expression})"))
            .map_err(|error| LintError::new(format!("cannot compile basename lookup: {error}")))?;
        Ok(Self { paths, matcher })
    }

    fn candidates(&self, line: &str) -> Vec<&str> {
        if !self.matcher.is_match(line) {
            return Vec::new();
        }
        self.paths
            .iter()
            .filter(|(basename, _)| line.contains(basename.as_str()))
            .flat_map(|(_, paths)| paths.iter().map(String::as_str))
            .collect()
    }
}

fn by_basename(retired: &BTreeSet<String>) -> BTreeMap<String, Vec<String>> {
    let mut paths = BTreeMap::<String, Vec<String>>::new();
    for path in retired {
        paths
            .entry(basename(path).to_owned())
            .or_default()
            .push(path.clone());
    }
    paths
}

fn line_references_retired(
    repository: &Repository,
    rel: &str,
    rel_dir: &str,
    line: &str,
    retired_path: &str,
) -> bool {
    if line.contains(retired_path) {
        return true;
    }
    let retired_dir = parent(retired_path);
    let basename = basename(retired_path);
    if rel_dir == retired_dir
        && [
            format!("$SCRIPT_DIR/{basename}"),
            format!("${{SCRIPT_DIR}}/{basename}"),
        ]
        .iter()
        .any(|reference| line.contains(reference))
    {
        return true;
    }
    if line.contains("# lint-ignore") {
        return false;
    }
    if rel == IMPLEMENT_SKILL_PATH && has_bare_basename(line, basename) {
        return true;
    }
    // Keep the old Python rule's case-sensitive `.md` suffix behavior.
    #[allow(clippy::case_sensitive_file_extension_comparisons)]
    if !rel.ends_with(".md")
        || !rel.starts_with(".claude/skills/")
        || rel_dir != retired_dir
        || repository.root().join(with_sh_extension(rel)).exists()
    {
        return false;
    }
    has_bare_basename(line, basename)
}

fn has_bare_basename(line: &str, basename: &str) -> bool {
    line.match_indices(basename).any(|(start, _)| {
        let end = start + basename.len();
        let before = line.as_bytes().get(start.wrapping_sub(1)).copied();
        let after = line.as_bytes().get(end).copied();
        !before.is_some_and(boundary_byte) && !after.is_some_and(boundary_byte)
    })
}

const fn boundary_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'.' | b'/' | b'-')
}

fn embedded_legacy_paths(
    repository: &Repository,
    retired: &BTreeSet<String>,
) -> Result<Vec<(String, u32, String)>, LintError> {
    let mut findings = BTreeSet::new();
    for relative in EMBEDDED_LEGACY_MODULES {
        let path = RepoPath::from_trusted(relative);
        if repository.paths().binary_search(&path).is_err() {
            continue;
        }
        let bytes = repository.read_bytes(&path)?;
        let source = String::from_utf8_lossy(&bytes);
        for (line, retired_path) in legacy_tuple_calls(&source) {
            if retired.contains(&retired_path) {
                findings.insert((relative.to_owned(), line, retired_path));
            }
        }
    }
    Ok(findings.into_iter().collect())
}

fn legacy_tuple_calls(source: &str) -> Vec<(u32, String)> {
    static CALL: LazyLock<Regex> = LazyLock::new(|| {
        Regex::new(r"(?m)\b(_run_legacy|run_legacy_script|_p)\s*\(")
            .expect("legacy call expression is valid")
    });
    CALL.find_iter(source)
        .filter_map(|matched| {
            let function = CALL
                .captures(matched.as_str())
                .and_then(|captures| captures.get(1))?
                .as_str();
            let arguments = balanced_call(source, matched.end() - 1)?;
            let tuple = if function == "_p" {
                arguments
            } else {
                arguments.strip_prefix('(')?.strip_suffix(')')?
            };
            let path = tuple_literal_path(tuple)?;
            let line = source[..matched.start()].bytes().filter(|byte| *byte == b'\n').count();
            Some((line_number(line), path))
        })
        .collect()
}

fn balanced_call(source: &str, open_index: usize) -> Option<&str> {
    let bytes = source.as_bytes();
    let mut depth = 0_u32;
    let mut quote = None;
    let mut escaped = false;
    for (offset, byte) in bytes[open_index..].iter().enumerate() {
        if let Some(active) = quote {
            if escaped {
                escaped = false;
            } else if *byte == b'\\' {
                escaped = true;
            } else if *byte == active {
                quote = None;
            }
            continue;
        }
        match *byte {
            b'\'' | b'"' => quote = Some(*byte),
            b'(' => depth += 1,
            b')' => {
                depth = depth.checked_sub(1)?;
                if depth == 0 {
                    return source.get(open_index + 1..open_index + offset);
                }
            }
            _ => {}
        }
    }
    None
}

fn tuple_literal_path(tuple: &str) -> Option<String> {
    let mut values = Vec::new();
    let mut remainder = tuple.trim();
    while !remainder.is_empty() {
        let quote = remainder.as_bytes().first().copied()?;
        if !matches!(quote, b'\'' | b'"') {
            return None;
        }
        let end = quoted_end(remainder, quote)?;
        values.push(remainder.get(1..end)?.to_owned());
        remainder = remainder.get(end + 1..)?.trim_start();
        if remainder.is_empty() {
            break;
        }
        remainder = remainder.strip_prefix(',')?.trim_start();
    }
    // Keep the old Python AST filter's case-sensitive `.sh` suffix behavior.
    #[allow(clippy::case_sensitive_file_extension_comparisons)]
    let is_shell_path = values.last().is_some_and(|value| value.ends_with(".sh"));
    is_shell_path.then_some(())?;
    Some(values.join("/"))
}

fn quoted_end(value: &str, quote: u8) -> Option<usize> {
    let mut escaped = false;
    for (index, byte) in value.bytes().enumerate().skip(1) {
        if escaped {
            escaped = false;
        } else if byte == b'\\' {
            escaped = true;
        } else if byte == quote {
            return Some(index);
        }
    }
    None
}

fn included(path: &str) -> bool {
    !path.starts_with("larch-logs/")
        && path != "CHANGELOG.md"
        && path != ".claude-plugin/plugin.json"
        && path != "python/shard-assignments.json"
        && path != MANIFEST_PATH
}

fn parent(path: &str) -> &str {
    path.rsplit_once('/').map_or("", |(parent, _)| parent)
}

fn basename(path: &str) -> &str {
    path.rsplit_once('/').map_or(path, |(_, basename)| basename)
}

fn with_sh_extension(path: &str) -> String {
    path.strip_suffix(".md")
        .map_or_else(|| path.to_owned(), |stem| format!("{stem}.sh"))
}

fn line_number(index: usize) -> u32 {
    u32::try_from(index + 1).unwrap_or(u32::MAX)
}

fn output(
    findings: Vec<Finding>,
    retired_paths: usize,
    retired_refs: usize,
    embedded_legacy_refs: usize,
) -> RuleOutput {
    let status = if findings.is_empty() { "ok" } else { "findings" };
    RuleOutput::with_contract(
        findings,
        Vec::new(),
        vec![
            format!("LINT_STATUS={status}"),
            format!("RETIRED_PATHS={retired_paths}"),
            format!("RETIRED_REFS={retired_refs}"),
            format!("EMBEDDED_LEGACY_REFS={embedded_legacy_refs}"),
        ],
    )
}
