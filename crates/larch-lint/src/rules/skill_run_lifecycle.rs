//! Require every shipped skill to declare and use the shared run lifecycle.
//!
//! # Crate survey (issue #8096)
//!
//! | Need | Candidates | Selection |
//! | --- | --- | --- |
//! | Shipped-skill inventory | recursive filesystem walk, repository snapshot plus direct child inspection | Reuse the validated repository snapshot for prompt content and inspect only the two declared direct-child skill roots for the Python rule's symlink and shape contract. |
//! | Child-call grammar | generic Markdown parser, direct line parser | The existing grammar is a narrow ordered block, so a direct line parser is clearer and preserves its exact accepted bullet shapes without adding a Markdown dependency. |

use std::{
    collections::{BTreeMap, BTreeSet},
    fs,
    path::{Component, Path, PathBuf},
};

use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "skill-run-lifecycle";
const DESCRIPTION: &str = "Require shared run lifecycle declarations and ownership for shipped skills";
const SHARED_CONTRACT: &str = "skills/shared/run-lifecycle.md";
const OWNERSHIP_REGISTRY: &str = "skills/shared/run-lifecycle-ownership.tsv";
const SHARED_REFERENCE: &str = "skills/shared/run-lifecycle.md";
const MARKER_PREFIX: &str = "# larch-run-lifecycle:";
const MARKER_TEMPLATE: &str = "# larch-run-lifecycle: shared-v1 skill=";
const OWNER_HEADER: &str = "skill\tstart_owner\tterminal_owner\tno_archive_exception";
const LIFECYCLE_INSTRUCTION_PREFIX: &str = "**MANDATORY: Follow the complete shared lifecycle contract in `${CLAUDE_PLUGIN_ROOT}/skills/shared/run-lifecycle.md` with declared skill `";
const LIFECYCLE_INSTRUCTION_SUFFIX: &str = "`.**";
const CHILD_CONTEXT_PREFIX: &str = "--lifecycle-parent-context \"$CONTEXT_FILE\" ";
const SKILL_ROOTS: [&str; 2] = ["skills", ".claude/skills"];
const TERMINAL_VERBS: [&str; 4] = [
    "lifecycle-finalize",
    "lifecycle-failure",
    "lifecycle-cancel",
    "lifecycle-early-return",
];
const PYTHON_PUBLISHER_ALLOWLIST: [&str; 2] = [
    "python/larch/report/run_lifecycle.py",
    "python/larch/report/run_log_publish.py",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/skill-run-lifecycle.toml",
);

#[derive(Debug)]
pub struct SkillRunLifecycleRule;

pub static RULE: SkillRunLifecycleRule = SkillRunLifecycleRule;

#[derive(Clone)]
struct Prompt {
    path: RepoPath,
    skill: String,
    text: String,
}

#[derive(Clone)]
struct Ownership {
    start: PathBuf,
    terminal: PathBuf,
    exception: String,
    line: u32,
}

impl Rule for SkillRunLifecycleRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let prompts = collect_prompts(repository)?;
        let mut findings = check_shared_contract(repository)?;
        let (ownership, ownership_findings) = read_ownership(repository)?;
        findings.extend(ownership_findings);
        findings.extend(check_registered_skills(&prompts, &ownership));
        for prompt in &prompts {
            findings.extend(check_prompt(prompt));
            findings.extend(check_prompt_ownership(repository, prompt, &ownership)?);
            findings.extend(check_child_handoffs(prompt));
        }
        findings.extend(check_publishers(repository, &prompts)?);
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn collect_prompts(repository: &Repository) -> Result<Vec<Prompt>, LintError> {
    let mut prompts = Vec::new();
    for root in SKILL_ROOTS {
        let root_path = repository.root().join(root);
        require_directory(&root_path, root)?;
        let mut entries = fs::read_dir(&root_path)
            .map_err(|error| LintError::new(format!("{root}: cannot read skill directory: {error}")))?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| LintError::new(format!("{root}: cannot read skill directory: {error}")))?;
        entries.sort_by_key(fs::DirEntry::file_name);
        for entry in entries {
            let name = entry.file_name();
            let Some(skill) = name.to_str() else {
                return Err(LintError::new(format!("{root}: skill directory name is not UTF-8")));
            };
            if skill == "shared" {
                continue;
            }
            let file_type = entry
                .file_type()
                .map_err(|error| LintError::new(format!("{root}/{skill}: cannot inspect skill directory: {error}")))?;
            if file_type.is_symlink() {
                return Err(LintError::new(format!("{root}/{skill}: skill directory is a symlink")));
            }
            if !file_type.is_dir() {
                continue;
            }
            let prompt_path = entry.path().join("SKILL.md");
            let metadata = match fs::symlink_metadata(&prompt_path) {
                Ok(metadata) => metadata,
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => continue,
                Err(error) => {
                    return Err(LintError::new(format!(
                        "{root}/{skill}/SKILL.md: cannot inspect skill prompt: {error}"
                    )));
                }
            };
            if metadata.file_type().is_symlink() {
                return Err(LintError::new(format!(
                    "{root}/{skill}/SKILL.md: skill prompt is a symlink"
                )));
            }
            if !metadata.is_file() {
                continue;
            }
            let path = RepoPath::from_trusted(&format!("{root}/{skill}/SKILL.md"));
            let text = repository.read_utf8(&path)?;
            prompts.push(Prompt {
                path,
                skill: skill.to_owned(),
                text,
            });
        }
    }
    Ok(prompts)
}

fn require_directory(path: &Path, display: &str) -> Result<(), LintError> {
    let metadata = fs::symlink_metadata(path)
        .map_err(|_| LintError::new(format!("{display}: skill directory is missing or unsafe")))?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(LintError::new(format!(
            "{display}: skill directory is missing or unsafe"
        )));
    }
    Ok(())
}

fn check_shared_contract(repository: &Repository) -> Result<Vec<Finding>, LintError> {
    let path = RepoPath::from_trusted(SHARED_CONTRACT);
    let text = repository.read_required_utf8(
        &path,
        format!("{SHARED_CONTRACT}: shared lifecycle contract is missing or unsafe"),
    )?;
    let required = std::iter::once("lifecycle-start").chain(TERMINAL_VERBS);
    let invalid: Vec<_> = required
        .filter(|verb| text.matches(verb).count() != 1)
        .collect();
    if invalid.is_empty() {
        Ok(Vec::new())
    } else {
        Ok(vec![Finding::new(
            SHARED_CONTRACT,
            1,
            format!(
                "partially wired lifecycle contract; expected each verb exactly once, invalid={}",
                invalid.join(",")
            ),
        )])
    }
}

fn read_ownership(
    repository: &Repository,
) -> Result<(BTreeMap<String, Ownership>, Vec<Finding>), LintError> {
    let path = RepoPath::from_trusted(OWNERSHIP_REGISTRY);
    let text = repository.read_required_utf8(
        &path,
        format!("{OWNERSHIP_REGISTRY}: ownership registry is missing or unsafe"),
    )?;
    let mut findings = Vec::new();
    let mut ownership = BTreeMap::new();
    let mut lines = text.lines();
    if lines.next() != Some(OWNER_HEADER) {
        findings.push(Finding::new(
            OWNERSHIP_REGISTRY,
            1,
            "invalid ownership registry header",
        ));
        return Ok((ownership, findings));
    }
    for (index, line) in lines.enumerate() {
        let line_number = u32::try_from(index + 2)
            .map_err(|_| LintError::new(format!("{OWNERSHIP_REGISTRY}: line number exceeds u32")))?;
        let fields: Vec<_> = line.split('\t').collect();
        if fields.len() != 4 || fields.iter().any(|field| field.is_empty()) {
            findings.push(Finding::new(
                OWNERSHIP_REGISTRY,
                line_number,
                "expected four non-empty fields",
            ));
            continue;
        }
        let [skill, start, terminal, exception] = fields.as_slice() else {
            continue;
        };
        let start = owner_path(start)?;
        let terminal = owner_path(terminal)?;
        if ownership.contains_key(*skill) {
            findings.push(Finding::new(
                OWNERSHIP_REGISTRY,
                line_number,
                format!("duplicate skill {skill:?}"),
            ));
            continue;
        }
        ownership.insert(
            (*skill).to_owned(),
            Ownership {
                start,
                terminal,
                exception: (*exception).to_owned(),
                line: line_number,
            },
        );
    }
    if !ownership.contains_key("*") {
        findings.push(Finding::new(
            OWNERSHIP_REGISTRY,
            1,
            "missing default '*' ownership row",
        ));
    }
    Ok((ownership, findings))
}

fn owner_path(value: &str) -> Result<PathBuf, LintError> {
    let path = Path::new(value);
    if path.is_absolute()
        || path.components().any(|component| {
            matches!(
                component,
                Component::CurDir | Component::ParentDir | Component::RootDir | Component::Prefix(_)
            )
        })
    {
        return Err(LintError::new(format!(
            "{OWNERSHIP_REGISTRY}: owner path must be a safe repository-relative path: {value}"
        )));
    }
    Ok(path.to_path_buf())
}

fn check_registered_skills(
    prompts: &[Prompt],
    ownership: &BTreeMap<String, Ownership>,
) -> Vec<Finding> {
    let skills: BTreeSet<_> = prompts.iter().map(|prompt| prompt.skill.as_str()).collect();
    ownership
        .iter()
        .filter(|(skill, _)| skill.as_str() != "*" && !skills.contains(skill.as_str()))
        .map(|(skill, row)| {
            Finding::new(
                OWNERSHIP_REGISTRY,
                row.line,
                format!("ownership row has no shipped skill: {skill}"),
            )
        })
        .collect()
}

fn check_prompt(prompt: &Prompt) -> Vec<Finding> {
    let path = prompt.path.as_str();
    let markers: Vec<_> = prompt
        .text
        .lines()
        .filter(|line| line.contains(MARKER_PREFIX) || line.starts_with("# pending:"))
        .collect();
    if markers.is_empty() {
        return prompt_finding(path, "missing shared run lifecycle declaration");
    }
    if markers.len() != 1 {
        return prompt_finding(path, "expected exactly one run lifecycle declaration");
    }
    let Some(declared) = markers[0]
        .strip_prefix(MARKER_TEMPLATE)
        .filter(|skill| valid_skill(skill))
    else {
        return prompt_finding(path, "malformed or partial run lifecycle declaration");
    };
    if declared != prompt.skill {
        return prompt_finding(
            path,
            format!(
                "declared lifecycle skill {declared:?} does not match directory {:?}",
                prompt.skill
            ),
        );
    }
    if prompt.text.matches(SHARED_REFERENCE).count() != 1 {
        return prompt_finding(
            path,
            format!("shared lifecycle declaration must reference {SHARED_REFERENCE} exactly once"),
        );
    }
    let instruction = format!(
        "{LIFECYCLE_INSTRUCTION_PREFIX}{}{LIFECYCLE_INSTRUCTION_SUFFIX}",
        prompt.skill
    );
    if prompt.text.matches(&instruction).count() != 1 {
        return prompt_finding(
            path,
            "shared lifecycle declaration must include its exact mandatory instruction once",
        );
    }
    if let Some(tools) = prompt
        .text
        .lines()
        .find_map(|line| line.strip_prefix("allowed-tools:").map(str::trim))
        && !tools
            .split(',')
            .map(str::trim)
            .any(|tool| tool == "Bash" || tool.starts_with("Bash("))
    {
        return prompt_finding(path, "shared lifecycle declaration requires Bash permission");
    }
    Vec::new()
}

fn valid_skill(skill: &str) -> bool {
    let mut characters = skill.chars();
    matches!(characters.next(), Some(character) if character.is_ascii_lowercase() || character.is_ascii_digit())
        && characters.all(|character| character.is_ascii_lowercase() || character.is_ascii_digit() || character == '-')
}

fn prompt_finding(path: &str, message: impl Into<String>) -> Vec<Finding> {
    vec![Finding::new(path, 1, message)]
}

fn check_prompt_ownership(
    repository: &Repository,
    prompt: &Prompt,
    ownership: &BTreeMap<String, Ownership>,
) -> Result<Vec<Finding>, LintError> {
    let Some(row) = ownership
        .get(&prompt.skill)
        .or_else(|| ownership.get("*"))
    else {
        return Ok(prompt_finding(
            prompt.path.as_str(),
            "no lifecycle ownership row resolves",
        ));
    };
    let mut findings = Vec::new();
    if !matches!(row.exception.as_str(), "-" | "no-logs-commit") {
        findings.push(Finding::new(
            OWNERSHIP_REGISTRY,
            row.line,
            format!(
                "unsupported no-archive exception for {}: {}",
                prompt.skill, row.exception
            ),
        ));
    }
    findings.extend(check_owner(repository, &prompt.skill, "start", &row.start)?);
    findings.extend(check_owner(
        repository,
        &prompt.skill,
        "terminal",
        &row.terminal,
    )?);
    Ok(findings)
}

fn check_owner(
    repository: &Repository,
    skill: &str,
    role: &str,
    relative: &Path,
) -> Result<Vec<Finding>, LintError> {
    let path = repository.root().join(relative);
    let display = relative.to_string_lossy();
    let Ok(metadata) = fs::symlink_metadata(&path) else {
        return Ok(vec![Finding::new(
            OWNERSHIP_REGISTRY,
            1,
            format!("{skill} {role} owner is missing or unsafe: {display}"),
        )]);
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Ok(vec![Finding::new(
            OWNERSHIP_REGISTRY,
            1,
            format!("{skill} {role} owner is missing or unsafe: {display}"),
        )]);
    }
    let text = fs::read_to_string(&path)
        .map_err(|error| LintError::new(format!("{display}: cannot read owner source: {error}")))?;
    let wired = if role == "start" {
        text.contains("lifecycle-start") || text.contains("run_lifecycle.start_run(")
    } else {
        TERMINAL_VERBS.iter().any(|verb| text.contains(verb))
            || text.contains("run_lifecycle.finish_run(")
    };
    if wired {
        Ok(Vec::new())
    } else {
        Ok(vec![Finding::new(
            OWNERSHIP_REGISTRY,
            1,
            format!("{skill} {role} owner is not lifecycle-wired: {display}"),
        )])
    }
}

fn check_publishers(repository: &Repository, prompts: &[Prompt]) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for prompt in prompts {
        if ["run-log publish", "publish_log_run("]
            .iter()
            .any(|token| prompt.text.contains(token))
        {
            findings.push(Finding::new(
                prompt.path.as_str(),
                1,
                "direct terminal publisher bypasses lifecycle ownership",
            ));
        }
    }
    for path in repository.paths().iter().filter(|path| {
        path.as_str().starts_with("python/larch/") && path.as_str().strip_suffix(".py").is_some()
    }) {
        if PYTHON_PUBLISHER_ALLOWLIST.contains(&path.as_str()) {
            continue;
        }
        let text = repository.read_utf8(path)?;
        if text.contains("publish_log_run(") {
            findings.push(Finding::new(
                path.as_str(),
                1,
                "second terminal run-log publisher bypasses lifecycle ownership",
            ));
        }
    }
    Ok(findings)
}

fn check_child_handoffs(prompt: &Prompt) -> Vec<Finding> {
    let lines: Vec<_> = prompt.text.lines().collect();
    let mut findings = Vec::new();
    for (index, line) in lines.iter().enumerate() {
        if *line != "Invoke the Skill tool:" {
            continue;
        }
        let Some((line, arguments)) = child_arguments(&lines, index + 1) else {
            continue;
        };
        if arguments.starts_with(CHILD_CONTEXT_PREFIX) {
            continue;
        }
        findings.push(Finding::new(
            prompt.path.as_str(),
            line,
            "child Skill call omits leading lifecycle parent-context handoff",
        ));
    }
    findings
}

fn child_arguments<'a>(lines: &[&'a str], start: usize) -> Option<(u32, &'a str)> {
    for (offset, line) in lines.iter().enumerate().skip(start) {
        if line.trim_matches([' ', '\t']).is_empty()
            || (line.starts_with("- ") && !line.starts_with("- args:"))
        {
            continue;
        }
        let arguments = line.strip_prefix("- args: ")?;
        let line = u32::try_from(offset + 1).ok()?;
        return Some((line, arguments));
    }
    None
}
