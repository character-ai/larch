//! Validate topology TSV runtime authorities.
//!
//! # Crate survey (issue #7608)
//!
//! | Need | Candidates | Selection |
//! |---|---|---|
//! | TSV parsing | workspace `csv`, handwritten splitting | Use `csv` with a tab delimiter. It preserves a strict delimiter grammar without adding a parser dependency. |
//! | Repository discovery and tracked state | shared `Repository`, direct `git` calls | Reuse `Repository`; its committed-path index preserves the tracked-authority check. |
//! | Path containment | `camino`, `std::path` | Use `std::path` after canonicalizing the deepest existing ancestor. The rule needs native symlink resolution and does not benefit from a UTF-8-only path type. |
//! | Run identifiers | workspace `uuid`, custom validation | UUID validation would change this rule's existing topology contract, so it is not applicable. |

use std::{
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
};

use csv::{ReaderBuilder, StringRecord};

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "topology-rule-paths";
const DESCRIPTION: &str = "Validate topology TSV runtime authorities";
const TOPOLOGY_PATH: &str = "skills/shared/topology.tsv";
const EXPECTED_COLUMNS: usize = 4;

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/topology-rule-paths.toml",
);

#[derive(Debug)]
pub struct TopologyRulePathsRule;

pub static RULE: TopologyRulePathsRule = TopologyRulePathsRule;

impl Rule for TopologyRulePathsRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let topology = RepoPath::from_trusted(TOPOLOGY_PATH);
        if repository.paths().binary_search(&topology).is_err() {
            return Ok(RuleOutput::from_findings(vec![Finding::new(
                TOPOLOGY_PATH,
                1,
                "topology TSV is missing",
            )]));
        }
        let source = repository.read_utf8(&topology)?;
        let mut findings = Vec::new();
        let mut authorities = 0usize;
        for (index, raw_line) in source.split('\n').enumerate() {
            let line = line_number(index, TOPOLOGY_PATH)?;
            if raw_line.contains('\r') {
                findings.push(Finding::new(
                    TOPOLOGY_PATH,
                    line,
                    "CRLF line endings not allowed (use LF)",
                ));
                continue;
            }
            if raw_line.is_empty() || raw_line.starts_with('#') {
                continue;
            }
            let fields = parse_row(raw_line, line)?;
            if fields.len() != EXPECTED_COLUMNS
                || fields.get(0).is_none_or(str::is_empty)
                || fields.get(1).is_none_or(str::is_empty)
                || fields.get(3).is_none_or(str::is_empty)
            {
                findings.push(Finding::new(
                    TOPOLOGY_PATH,
                    line,
                    "malformed row; expected exactly four tab-separated columns with key, value, and runtime_authority non-empty",
                ));
                continue;
            }
            let value = &fields[1];
            let authority = &fields[3];
            let Some(path) = validate_repo_path(repository, line, authority, &mut findings)? else {
                continue;
            };
            authorities += 1;
            validate_authority(repository, line, value, authority, &path, &mut findings)?;
        }
        if authorities == 0 {
            findings.push(Finding::new(
                TOPOLOGY_PATH,
                1,
                "topology TSV has no data rows",
            ));
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn parse_row(raw_line: &str, line: u32) -> Result<StringRecord, LintError> {
    let mut reader = ReaderBuilder::new()
        .delimiter(b'\t')
        .has_headers(false)
        .flexible(true)
        .quote(0)
        .from_reader(raw_line.as_bytes());
    let record = reader
        .records()
        .next()
        .transpose()
        .map_err(|error| LintError::new(format!("{TOPOLOGY_PATH}:{line}: invalid TSV row: {error}")))?;
    record.ok_or_else(|| LintError::new(format!("{TOPOLOGY_PATH}:{line}: TSV row disappeared")))
}

fn validate_repo_path(
    repository: &Repository,
    line: u32,
    authority: &str,
    findings: &mut Vec<Finding>,
) -> Result<Option<PathBuf>, LintError> {
    let violation = if authority != authority.trim() {
        Some("runtime_authority must not contain leading or trailing whitespace".to_owned())
    } else if authority.is_empty() {
        Some("empty runtime_authority".to_owned())
    } else if authority.starts_with('/') {
        Some(format!("runtime_authority must be repo-relative: {authority}"))
    } else if authority.starts_with("./") {
        Some(format!("runtime_authority must not start with ./ : {authority}"))
    } else if authority.starts_with('-') {
        Some(format!("runtime_authority must not start with -: {authority}"))
    } else if authority.starts_with(':') {
        Some(format!("runtime_authority must not start with : (reserved for git pathspec magic): {authority}"))
    } else if authority.contains("//") {
        Some(format!("runtime_authority must not contain duplicate slash: {authority}"))
    } else if authority.contains('\t') {
        Some("runtime_authority must not contain tabs".to_owned())
    } else if authority.contains('\n') {
        Some("runtime_authority must not contain newlines".to_owned())
    } else if authority.split('/').any(|segment| segment == "..") {
        Some(format!("runtime_authority must not contain parent traversal: {authority}"))
    } else if authority.split('/').any(|segment| segment == ".") {
        Some(format!("runtime_authority must not contain . path segments: {authority}"))
    } else {
        None
    };
    if let Some(message) = violation {
        findings.push(Finding::new(TOPOLOGY_PATH, line, message));
        return Ok(None);
    }
    let full_path = repository.root().join(authority);
    let resolved = resolve_with_missing_suffix(&full_path)?;
    if !resolved.starts_with(repository.root()) {
        findings.push(Finding::new(
            TOPOLOGY_PATH,
            line,
            format!("runtime_authority must resolve within repo root: {authority}"),
        ));
        return Ok(None);
    }
    Ok(Some(full_path))
}

fn resolve_with_missing_suffix(path: &Path) -> Result<PathBuf, LintError> {
    let mut existing = path.to_path_buf();
    let mut suffix = Vec::<OsString>::new();
    while fs::symlink_metadata(&existing).is_err_and(|error| error.kind() == std::io::ErrorKind::NotFound) {
        let name = existing
            .file_name()
            .ok_or_else(|| LintError::new(format!("cannot resolve authority path {}", path.display())))?;
        suffix.push(name.to_owned());
        existing.pop();
    }
    let mut resolved = existing.canonicalize().map_err(|error| {
        LintError::new(format!("cannot resolve authority path {}: {error}", path.display()))
    })?;
    for component in suffix.iter().rev() {
        resolved.push(component);
    }
    Ok(resolved)
}

fn validate_authority(
    repository: &Repository,
    line: u32,
    value: &str,
    authority: &str,
    path: &Path,
    findings: &mut Vec<Finding>,
) -> Result<(), LintError> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            findings.push(Finding::new(
                TOPOLOGY_PATH,
                line,
                format!("runtime_authority file does not exist: {authority}"),
            ));
            return Ok(());
        }
        Err(error) => {
            return Err(LintError::new(format!(
                "{TOPOLOGY_PATH}:{line}: unable to inspect runtime_authority {authority}: {error}"
            )));
        }
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        findings.push(Finding::new(
            TOPOLOGY_PATH,
            line,
            format!("runtime_authority must be a regular file: {authority}"),
        ));
        return Ok(());
    }
    let text = fs::read_to_string(path).map_err(|error| {
        LintError::new(format!(
            "{TOPOLOGY_PATH}:{line}: unable to read runtime_authority {authority}: {error}"
        ))
    })?;
    if !text.contains(value) {
        findings.push(Finding::new(
            TOPOLOGY_PATH,
            line,
            format!("runtime_authority {authority} does not contain value '{value}'"),
        ));
    }
    let repo_path = RepoPath::from_trusted(authority);
    if !repository.is_committed(&repo_path) {
        findings.push(Finding::new(
            TOPOLOGY_PATH,
            line,
            format!("runtime_authority is not tracked by git: {authority}"),
        ));
    }
    Ok(())
}

fn line_number(index: usize, path: &str) -> Result<u32, LintError> {
    u32::try_from(index + 1).map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))
}
