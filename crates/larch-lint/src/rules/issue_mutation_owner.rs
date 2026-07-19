//! Keep GitHub issue field mutation behind the typed issue-mutation owner.

use std::{
    collections::{BTreeMap, BTreeSet},
    path::Path,
};

use tree_sitter::Node;

use crate::{
    Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{
        ShellCommand, json_shell_commands, markdown_shell_commands, parse_python, shell_commands,
    },
};

const NAME: &str = "issue-mutation-owner";
const DESCRIPTION: &str = "Reject raw GitHub issue field mutation outside the typed owner";
const OWNER: &str = "python/larch/issue/issue_mutation.py";
const OWNER_GUIDANCE: &str = "use larch.issue.issue_mutation";

const RAW_HELPERS: &[&str] = &[
    "issue_edit",
    "issue_edit_body_file",
    "issue_edit_body_with_retry",
    "issue_label_add",
    "issue_label_remove",
];
const GRAPHQL_MUTATIONS: &[&str] = &[
    "updateIssue",
    "addLabelsToLabelable",
    "removeLabelsFromLabelable",
];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/issue-mutation-owner.toml",
);

#[derive(Debug)]
pub struct IssueMutationOwnerRule;

pub static RULE: IssueMutationOwnerRule = IssueMutationOwnerRule;

impl Rule for IssueMutationOwnerRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let mut findings = Vec::new();
        for path in repository.paths() {
            let path_text = path.as_str();
            if path_text == OWNER || is_fixture(path_text) {
                continue;
            }
            let Some(surface) = surface(path_text) else {
                continue;
            };
            let source = repository.read_utf8(path)?;
            findings.extend(match surface {
                Surface::Python => check_python(path_text, &source)?,
                Surface::Shell => check_shell(path_text, &source, 0)?,
                Surface::Markdown => check_markdown(path_text, &source)?,
                Surface::Json => check_json(path_text, &source)?,
            });
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Clone, Copy)]
enum Surface {
    Python,
    Shell,
    Markdown,
    Json,
}

fn surface(path: &str) -> Option<Surface> {
    let extension = Path::new(path).extension()?.to_str()?;
    if path.starts_with("python/larch/") && extension.eq_ignore_ascii_case("py") {
        return Some(Surface::Python);
    }
    if path.starts_with("skills/") || path.starts_with("agents/") {
        if extension.eq_ignore_ascii_case("md") {
            return Some(Surface::Markdown);
        }
        if extension.eq_ignore_ascii_case("sh") {
            return Some(Surface::Shell);
        }
    }
    if path.starts_with("hooks/") {
        if extension.eq_ignore_ascii_case("json") {
            return Some(Surface::Json);
        }
        if extension.eq_ignore_ascii_case("sh") {
            return Some(Surface::Shell);
        }
    }
    if path.starts_with("scripts/") && extension.eq_ignore_ascii_case("sh") {
        return Some(Surface::Shell);
    }
    None
}

fn is_fixture(path: &str) -> bool {
    path.split('/')
        .any(|part| matches!(part, "tests" | "fixtures"))
        || path.rsplit('/').next().is_some_and(|name| {
            name.starts_with("test-") || name.starts_with("test_") || name.ends_with("_test.py")
        })
}

#[derive(Clone, Eq, Ord, PartialEq, PartialOrd)]
enum MutationKind {
    Helper(String),
    Cli,
    Rest,
    GraphQl(&'static str),
}

impl MutationKind {
    fn message(self) -> String {
        match self {
            Self::Helper(name) => {
                format!("raw issue mutation helper {name}; {OWNER_GUIDANCE}")
            }
            Self::Cli => format!("raw gh issue edit argv; {OWNER_GUIDANCE}"),
            Self::Rest => format!("raw issue REST PATCH; {OWNER_GUIDANCE}"),
            Self::GraphQl(name) => {
                format!("raw issue GraphQL mutation {name}; {OWNER_GUIDANCE}")
            }
        }
    }
}

#[derive(Default)]
struct PythonImports {
    gh_modules: BTreeSet<String>,
    helper_calls: BTreeMap<String, String>,
    command_calls: BTreeSet<String>,
}

fn check_python(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let tree = parse_python(source)?;
    let mut imports = PythonImports::default();
    collect_python_imports(tree.root_node(), source, &mut imports);
    let mut matches = BTreeSet::new();
    collect_python_calls(tree.root_node(), source, &imports, &mut matches);
    matches
        .into_iter()
        .map(|(line, kind)| Ok(Finding::new(path, line_number(path, line)?, kind.message())))
        .collect()
}

fn collect_python_imports(node: Node<'_>, source: &str, imports: &mut PythonImports) {
    if matches!(node.kind(), "import_statement" | "import_from_statement") {
        record_python_import(source.get(node.byte_range()).unwrap_or(""), imports);
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_imports(child, source, imports);
    }
}

fn record_python_import(statement: &str, imports: &mut PythonImports) {
    let normalized = statement.replace(['\n', '(', ')'], " ");
    let normalized = normalized.split_whitespace().collect::<Vec<_>>().join(" ");
    if let Some(items) = normalized.strip_prefix("import ") {
        for item in items.split(',').map(str::trim) {
            let words: Vec<&str> = item.split_whitespace().collect();
            if words.first() == Some(&"larch.git.gh") {
                let local = match words.as_slice() {
                    [_, "as", alias] => *alias,
                    _ => "larch.git.gh",
                };
                imports.gh_modules.insert(local.to_owned());
            }
        }
        return;
    }
    let Some((module, names)) = normalized
        .strip_prefix("from ")
        .and_then(|rest| rest.split_once(" import "))
    else {
        return;
    };
    if module == "larch.git" {
        for item in names.split(',').map(str::trim) {
            let words: Vec<&str> = item.split_whitespace().collect();
            if words.first() == Some(&"gh") {
                let local = match words.as_slice() {
                    [_, "as", alias] => *alias,
                    _ => "gh",
                };
                imports.gh_modules.insert(local.to_owned());
            }
        }
    } else if module == "larch.git.gh" {
        for item in names.split(',').map(str::trim) {
            let words: Vec<&str> = item.split_whitespace().collect();
            let Some(name) = words.first().copied() else {
                continue;
            };
            let local = match words.as_slice() {
                [_, "as", alias] => *alias,
                _ => name,
            };
            if RAW_HELPERS.contains(&name) {
                imports
                    .helper_calls
                    .insert(local.to_owned(), name.to_owned());
            } else if name == "command" {
                imports.command_calls.insert(local.to_owned());
            }
        }
    }
}

fn collect_python_calls(
    node: Node<'_>,
    source: &str,
    imports: &PythonImports,
    matches: &mut BTreeSet<(usize, MutationKind)>,
) {
    if node.kind() == "call"
        && let Some(kind) = python_call_kind(node, source, imports)
    {
        matches.insert((node.start_position().row + 1, kind));
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_calls(child, source, imports, matches);
    }
}

fn python_call_kind(call: Node<'_>, source: &str, imports: &PythonImports) -> Option<MutationKind> {
    let function = call.child_by_field_name("function")?;
    let function = source.get(function.byte_range()).unwrap_or("").trim();
    if let Some(helper) = raw_helper(function, imports) {
        return Some(MutationKind::Helper(helper));
    }
    let arguments = call.child_by_field_name("arguments")?;
    let gh_wrapper = is_gh_command(function, imports);
    let mut cursor = arguments.walk();
    for argument in arguments.named_children(&mut cursor) {
        let candidate = if argument.kind() == "keyword_argument" {
            let name = argument.child_by_field_name("name")?;
            if !matches!(source.get(name.byte_range()), Some("args" | "argv")) {
                continue;
            }
            argument.child_by_field_name("value")?
        } else {
            argument
        };
        if !matches!(candidate.kind(), "list" | "tuple") {
            continue;
        }
        let mut words = Vec::new();
        collect_python_strings(candidate, source, &mut words);
        if let Some(kind) = command_mutation(&words, gh_wrapper) {
            return Some(kind);
        }
    }
    None
}

fn raw_helper(function: &str, imports: &PythonImports) -> Option<String> {
    if let Some(helper) = imports.helper_calls.get(function) {
        return Some(helper.clone());
    }
    let (module, helper) = function.rsplit_once('.')?;
    (RAW_HELPERS.contains(&helper)
        && (module == "larch.git.gh" || imports.gh_modules.contains(module)))
    .then(|| helper.to_owned())
}

fn is_gh_command(function: &str, imports: &PythonImports) -> bool {
    if imports.command_calls.contains(function) {
        return true;
    }
    function.rsplit_once('.').is_some_and(|(module, name)| {
        name == "command" && (module == "larch.git.gh" || imports.gh_modules.contains(module))
    })
}

fn collect_python_strings(node: Node<'_>, source: &str, words: &mut Vec<String>) {
    if node.kind() == "call" {
        return;
    }
    if node.kind() == "string" {
        words.push(python_string_value(node, source));
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_strings(child, source, words);
    }
}

fn python_string_value(node: Node<'_>, source: &str) -> String {
    source
        .get(node.byte_range())
        .unwrap_or("")
        .trim_start_matches(['r', 'R', 'b', 'B', 'f', 'F'])
        .trim_matches(['\"', '\''])
        .replace("\\\n", "")
}

fn command_mutation(words: &[String], gh_wrapper: bool) -> Option<MutationKind> {
    if words.windows(3).any(|window| {
        executable_name(&window[0]) == "gh" && window[1] == "issue" && window[2] == "edit"
    }) || (gh_wrapper
        && words
            .windows(2)
            .any(|window| window[0] == "issue" && window[1] == "edit"))
    {
        return Some(MutationKind::Cli);
    }
    if has_patch(words) && words.iter().any(|word| is_issue_endpoint(word)) {
        return Some(MutationKind::Rest);
    }
    GRAPHQL_MUTATIONS
        .iter()
        .copied()
        .find(|mutation| words.iter().any(|word| word.contains(mutation)))
        .map(MutationKind::GraphQl)
}

fn has_patch(words: &[String]) -> bool {
    words.iter().any(|word| word.eq_ignore_ascii_case("PATCH"))
}

fn is_issue_endpoint(word: &str) -> bool {
    let path = word
        .split_once('?')
        .map_or(word, |(path, _)| path)
        .strip_prefix("https://api.github.com/")
        .unwrap_or(word)
        .trim_start_matches('/');
    let parts: Vec<&str> = path.split('/').collect();
    matches!(
        parts.as_slice(),
        ["repos", repository, "issues", issue]
            if repository.starts_with(['{', '$']) && !issue.is_empty()
    ) || matches!(
        parts.as_slice(),
        ["repos", owner, repo, "issues", issue]
            if !owner.is_empty() && !repo.is_empty() && !issue.is_empty()
    )
}

fn check_shell(path: &str, source: &str, line_offset: usize) -> Result<Vec<Finding>, LintError> {
    check_commands(path, shell_commands(source, line_offset)?)
}

fn check_commands(path: &str, commands: Vec<ShellCommand>) -> Result<Vec<Finding>, LintError> {
    commands
        .into_iter()
        .filter_map(|command| {
            command_mutation(command.words(), false).map(|kind| (command.line(), kind))
        })
        .map(|(line, kind)| Ok(Finding::new(path, line_number(path, line)?, kind.message())))
        .collect()
}

fn executable_name(word: &str) -> &str {
    word.rsplit('/').next().unwrap_or(word)
}

fn check_markdown(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    check_commands(path, markdown_shell_commands(source)?)
}

fn check_json(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    check_commands(path, json_shell_commands(path, source)?)
}

fn line_number(path: &str, line: usize) -> Result<u32, LintError> {
    u32::try_from(line).map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))
}
