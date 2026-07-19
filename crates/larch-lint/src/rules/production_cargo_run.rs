//! Reject Cargo and target-directory execution from production runtime surfaces.

use std::{collections::BTreeSet, path::Path, sync::LazyLock};

use regex::Regex;
use tree_sitter::Node;

use crate::{
    Finding, LintError, Repository, Rule, RuleMetadata, RuleOutput,
    syntax::{FenceState, MarkdownDocument, leaf_bash_commands, parse_bash, parse_python},
};

use super::larch_runtime_entrypoint::is_production_surface;

const NAME: &str = "production-cargo-run";
const DESCRIPTION: &str = "Reject production Cargo and target-directory larch execution";
const MESSAGE: &str =
    "production runtime must use scripts/larch.sh; cargo and target-directory execution are development-only";
const RELEASE_OWNER: &str = ".claude/skills/release/SKILL.md";

static INLINE_COMMAND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:run|execute|invoke|call|use)\s*:?\s*$")
        .expect("inline command lead-in is valid")
});
static NEGATED_INLINE_COMMAND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(?i)\b(?:do\s+not|don't|never)\s+(?:run|execute|invoke|call|use)\s*:?\s*$")
        .expect("negated inline command lead-in is valid")
});
static INLINE_CODE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"`([^`\n]+)`").expect("inline code expression is valid")
});
static JSON_COMMAND: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?s)\"command\"\s*:\s*\"((?:\\.|[^\"\\])*)\""#)
        .expect("JSON command expression is valid")
});

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/production-cargo-run.toml",
);

#[derive(Debug)]
pub struct ProductionCargoRunRule;

pub static RULE: ProductionCargoRunRule = ProductionCargoRunRule;

impl Rule for ProductionCargoRunRule {
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
            if !is_production_surface(path_text) || is_fixture_surface(path_text) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            let extension = extension(path_text).unwrap_or("");
            findings.extend(if extension.eq_ignore_ascii_case("sh") {
                check_shell(path_text, &source, 0)?
            } else if extension.eq_ignore_ascii_case("py") {
                check_python(path_text, &source)?
            } else if extension.eq_ignore_ascii_case("md") {
                check_markdown(path_text, &source)?
            } else if extension.eq_ignore_ascii_case("json") {
                check_json(path_text, &source)?
            } else {
                Vec::new()
            });
        }
        findings.sort();
        findings.dedup();
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

fn extension(path: &str) -> Option<&str> {
    Path::new(path).extension()?.to_str()
}

fn is_fixture_surface(path: &str) -> bool {
    path.split('/').any(|part| part == "fixtures")
        || path
            .rsplit('/')
            .next()
            .is_some_and(|name| name.starts_with("test-"))
}

fn check_shell(path: &str, source: &str, line_offset: usize) -> Result<Vec<Finding>, LintError> {
    let tree = parse_bash(source)?;
    let mut lines = BTreeSet::new();
    for command in leaf_bash_commands(&tree) {
        let words = shell_command_words(command, source);
        if prohibited_argv(&words) && !is_allowed_release_command(path, &words) {
            lines.insert(command.start_position().row + line_offset + 1);
        }
    }
    lines
        .into_iter()
        .map(|line| {
            let number = u32::try_from(line)
                .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
            Ok(Finding::new(path, number, MESSAGE))
        })
        .collect()
}

fn shell_command_words(command: Node<'_>, source: &str) -> Vec<String> {
    let Some(name) = command.child_by_field_name("name") else {
        return Vec::new();
    };
    let mut words = vec![node_text(name, source)];
    let mut cursor = command.walk();
    words.extend(
        command
            .children_by_field_name("argument", &mut cursor)
            .map(|argument| node_text(argument, source)),
    );
    words
}

fn node_text(node: Node<'_>, source: &str) -> String {
    normalize_word(source.get(node.byte_range()).unwrap_or(""))
}

fn normalize_word(word: &str) -> String {
    word.replace("\\\n", "")
        .replace(['\"', '\''], "")
        .replace('\\', "/")
}

fn prohibited_argv(words: &[String]) -> bool {
    let Some(index) = executable_index(words) else {
        return false;
    };
    let program = &words[index];
    if is_target_larch(program) {
        return true;
    }
    is_cargo(program)
        && cargo_subcommand(words, index).is_some_and(|word| matches!(word, "run" | "install"))
}

fn executable_index(words: &[String]) -> Option<usize> {
    let mut index = 0;
    loop {
        while words
            .get(index)
            .is_some_and(|word| word.starts_with('-') || word.contains('='))
        {
            index += 1;
        }
        let program = words.get(index)?;
        if matches!(program.as_str(), "command" | "env" | "exec" | "sudo") {
            index += 1;
            continue;
        }
        return Some(index);
    }
}

fn cargo_subcommand(words: &[String], cargo_index: usize) -> Option<&str> {
    words[cargo_index + 1..]
        .iter()
        .find(|word| !word.starts_with('-'))
        .map(String::as_str)
}

fn is_allowed_release_command(path: &str, words: &[String]) -> bool {
    if path != RELEASE_OWNER {
        return false;
    }
    let Some(cargo_index) = executable_index(words) else {
        return false;
    };
    if !is_cargo(&words[cargo_index]) || cargo_subcommand(words, cargo_index) != Some("run") {
        return false;
    }
    words.windows(2).any(|pair| pair == ["--package", "larch-cli"])
        && words.windows(2).any(|pair| {
            pair[0] == "upgrade-larch"
                && matches!(pair[1].as_str(), "release-step7-root" | "run")
        })
}

fn is_cargo(word: &str) -> bool {
    word.rsplit('/').next().is_some_and(|name| matches!(name, "cargo" | "cargo.exe"))
}

fn is_target_larch(word: &str) -> bool {
    let normalized = word
        .replace('\\', "/")
        .trim_start_matches("./")
        .to_ascii_lowercase();
    normalized.ends_with("target/debug/larch")
        || normalized.ends_with("target/debug/larch.exe")
        || normalized.ends_with("target/release/larch")
        || normalized.ends_with("target/release/larch.exe")
}

fn check_python(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let tree = parse_python(source)?;
    let callables = subprocess_callables(tree.root_node(), source);
    let mut lines = BTreeSet::new();
    collect_python_calls(tree.root_node(), source, &callables, &mut lines);
    lines
        .into_iter()
        .map(|line| {
            let number = u32::try_from(line)
                .map_err(|_| LintError::new(format!("{path}: line number exceeds u32")))?;
            Ok(Finding::new(path, number, MESSAGE))
        })
        .collect()
}

fn subprocess_callables(root: Node<'_>, source: &str) -> BTreeSet<String> {
    let mut callables = subprocess_method_names("subprocess");
    collect_subprocess_imports(root, source, &mut callables);
    callables
}

fn collect_subprocess_imports(node: Node<'_>, source: &str, callables: &mut BTreeSet<String>) {
    let text = source.get(node.byte_range()).unwrap_or("");
    if node.kind() == "import_statement" {
        let imports = text.trim().strip_prefix("import ").unwrap_or("");
        for item in imports.split(',').map(str::trim) {
            let mut words = item.split_whitespace();
            if words.next() == Some("subprocess") {
                let module = match (words.next(), words.next()) {
                    (Some("as"), Some(alias)) => alias,
                    _ => "subprocess",
                };
                callables.extend(subprocess_method_names(module));
            }
        }
        return;
    }
    if node.kind() == "import_from_statement" {
        let normalized = text.replace(['\n', '(', ')'], " ");
        if let Some(imports) = normalized.trim().strip_prefix("from subprocess import ") {
            for item in imports.split(',').map(str::trim) {
                let mut words = item.split_whitespace();
                let Some(name) = words.next() else {
                    continue;
                };
                if !is_subprocess_method(name) {
                    continue;
                }
                let callable = match (words.next(), words.next()) {
                    (Some("as"), Some(alias)) => alias,
                    _ => name,
                };
                callables.insert(callable.to_owned());
            }
        }
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_subprocess_imports(child, source, callables);
    }
}

fn subprocess_method_names(module: &str) -> BTreeSet<String> {
    ["run", "Popen", "call", "check_call", "check_output"]
        .into_iter()
        .map(|method| format!("{module}.{method}"))
        .collect()
}

fn is_subprocess_method(name: &str) -> bool {
    matches!(name, "run" | "Popen" | "call" | "check_call" | "check_output")
}

fn collect_python_calls(
    node: Node<'_>,
    source: &str,
    callables: &BTreeSet<String>,
    lines: &mut BTreeSet<usize>,
) {
    if node.kind() == "call" && python_call_is_prohibited(node, source, callables) {
        lines.insert(node.start_position().row + 1);
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_calls(child, source, callables, lines);
    }
}

fn python_call_is_prohibited(
    call: Node<'_>,
    source: &str,
    callables: &BTreeSet<String>,
) -> bool {
    let Some(function) = call.child_by_field_name("function") else {
        return false;
    };
    let function = source.get(function.byte_range()).unwrap_or("");
    if !callables.contains(function) {
        return false;
    }
    let Some(arguments) = call.child_by_field_name("arguments") else {
        return false;
    };
    let mut cursor = arguments.walk();
    let Some(argv) = arguments
        .named_children(&mut cursor)
        .find_map(|argument| {
            if argument.kind() != "keyword_argument" {
                return Some(argument);
            }
            let name = argument.child_by_field_name("name")?;
            (source.get(name.byte_range()) == Some("args"))
                .then(|| argument.child_by_field_name("value"))
                .flatten()
        })
    else {
        return false;
    };
    if argv.kind() == "string" {
        let command = python_string_value(argv, source);
        return parse_bash(&command)
            .ok()
            .is_some_and(|tree| {
                leaf_bash_commands(&tree)
                    .into_iter()
                    .any(|node| prohibited_argv(&shell_command_words(node, &command)))
            });
    }
    let words = python_argv_words(argv, source);
    prohibited_argv(&words)
}

fn python_argv_words(node: Node<'_>, source: &str) -> Vec<String> {
    if matches!(node.kind(), "list" | "tuple") {
        let mut cursor = node.walk();
        return node
            .named_children(&mut cursor)
            .map(|element| python_argv_element(element, source))
            .collect();
    }
    vec![python_argv_element(node, source)]
}

fn python_argv_element(node: Node<'_>, source: &str) -> String {
    let mut parts = Vec::new();
    collect_python_strings(node, source, &mut parts);
    parts.join("/")
}

fn collect_python_strings(node: Node<'_>, source: &str, parts: &mut Vec<String>) {
    if node.kind() == "string" {
        parts.push(python_string_value(node, source));
        return;
    }
    let mut cursor = node.walk();
    for child in node.named_children(&mut cursor) {
        collect_python_strings(child, source, parts);
    }
}

fn python_string_value(node: Node<'_>, source: &str) -> String {
    let raw = source.get(node.byte_range()).unwrap_or("");
    let trimmed = raw
        .trim_start_matches(['r', 'R', 'b', 'B', 'f', 'F'])
        .trim_matches(['\"', '\'']);
    normalize_word(trimmed)
}

fn check_markdown(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    let mut block = String::new();
    let mut block_start = 0;
    for line in MarkdownDocument::new(source).lines() {
        let executable = matches!(
            line.fence_state(),
            FenceState::Inside { language: Some(language) } if is_executable_fence(language)
        ) && !line.is_fence_boundary();
        if executable {
            if block.is_empty() {
                block_start = line.number() - 1;
            }
            let text = line
                .text()
                .strip_prefix("$ ")
                .unwrap_or_else(|| line.text());
            block.push_str(text);
            block.push('\n');
        } else if !block.is_empty() {
            findings.extend(check_shell(path, &block, block_start)?);
            block.clear();
        }
        if matches!(line.fence_state(), FenceState::Outside) {
            findings.extend(check_inline_command(path, line.number(), line.text())?);
        }
    }
    if !block.is_empty() {
        findings.extend(check_shell(path, &block, block_start)?);
    }
    Ok(findings)
}

fn is_executable_fence(language: &str) -> bool {
    matches!(language.to_ascii_lowercase().as_str(), "bash" | "sh" | "shell" | "console")
}

fn check_inline_command(path: &str, line: usize, text: &str) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for capture in INLINE_CODE.captures_iter(text) {
        let Some(command) = capture.get(1) else {
            continue;
        };
        let lead_in = &text[..capture.get(0).map_or(0, |matched| matched.start())];
        if !INLINE_COMMAND.is_match(lead_in) || NEGATED_INLINE_COMMAND.is_match(lead_in) {
            continue;
        }
        let scanned = check_shell(path, command.as_str(), line.saturating_sub(1))?;
        findings.extend(scanned);
    }
    Ok(findings)
}

fn check_json(path: &str, source: &str) -> Result<Vec<Finding>, LintError> {
    let mut findings = Vec::new();
    for capture in JSON_COMMAND.captures_iter(source) {
        let Some(raw) = capture.get(1) else {
            continue;
        };
        let encoded = format!("\"{}\"", raw.as_str());
        let command: String = serde_json::from_str(&encoded)
            .map_err(|error| LintError::new(format!("{path}: invalid command string: {error}")))?;
        let line = source[..raw.start()].lines().count();
        findings.extend(check_shell(path, &command, line.saturating_sub(1))?);
    }
    Ok(findings)
}

#[cfg(test)]
mod tests {
    use super::{is_target_larch, prohibited_argv};

    #[test]
    fn recognizes_platform_target_paths() {
        assert!(is_target_larch(r"C:\repo\target\debug\larch.exe"));
        assert!(is_target_larch("./target/release/larch"));
    }

    #[test]
    fn does_not_treat_command_arguments_as_executables() {
        let words = ["echo".to_owned(), "cargo".to_owned(), "run".to_owned()];
        assert!(!prohibited_argv(&words));
        let cargo_metadata = [
            "cargo".to_owned(),
            "metadata".to_owned(),
            "--filter-platform".to_owned(),
            "cargo".to_owned(),
            "run".to_owned(),
        ];
        assert!(!prohibited_argv(&cargo_metadata));
    }
}
