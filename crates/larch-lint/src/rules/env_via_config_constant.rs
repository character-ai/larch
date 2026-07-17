use std::collections::{BTreeMap, HashMap, HashSet};

use syn::{
    Expr, ExprCall, ExprPath, Item, ItemConst, ItemUse, Lit, UseTree,
    visit::Visit,
};

use crate::suppression;
use crate::syntax::RustSyntax;
use crate::{Finding, LintError, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

use super::path_discovery;

const NAME: &str = "env-via-config-constant";
const DESCRIPTION: &str =
    "Reject bare environment-key literals already owned by shared ENV_* constants";
const SUPPRESSION_TOKEN: &str = "lint-env-via-config-constant";
const OWNER_PATH: &str = "crates/larch-lint/policy/env_constants.rs";
const EXEMPTIONS_PATH: &str = "crates/larch-lint/policy/env-via-config-constant-exemptions.json";
const ENV_FNS: &[&str] = &["var", "var_os", "set_var", "remove_var"];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/env-via-config-constant.toml",
);

#[derive(Debug)]
pub struct EnvViaConfigConstantRule;

pub static RULE: EnvViaConfigConstantRule = EnvViaConfigConstantRule;

impl Rule for EnvViaConfigConstantRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let constants = load_owned_constants(repository)?;
        if constants.is_empty() {
            return Ok(RuleOutput::clean());
        }
        let exemptions = load_exemptions(repository)?;
        let mut findings = Vec::new();
        for path in path_discovery::selected_rust_sources(repository)? {
            if path.as_str() == OWNER_PATH || is_test_path(path.as_str()) {
                continue;
            }
            let source = repository.read_utf8(path)?;
            findings.extend(scan_source(
                path.as_str(),
                &source,
                &constants,
                &exemptions,
            )?);
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Clone, Debug, Eq, PartialEq)]
struct Exemption {
    file: String,
    env_name: Option<String>,
    constant: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct RawFinding {
    env_name: String,
    constant: String,
    access: String,
    occurrence: u32,
}

fn load_owned_constants(repository: &Repository) -> Result<BTreeMap<String, String>, LintError> {
    let owner = RepoPath::from_trusted(OWNER_PATH);
    if repository.paths().binary_search(&owner).is_err() {
        return Ok(BTreeMap::new());
    }
    let source = repository.read_utf8(&owner)?;
    parse_env_constants(OWNER_PATH, &source)
}

fn parse_env_constants(path: &str, source: &str) -> Result<BTreeMap<String, String>, LintError> {
    let syntax = RustSyntax::parse(path, source)?;
    let mut values: BTreeMap<String, Vec<String>> = BTreeMap::new();
    for item in &syntax.file().items {
        let Item::Const(item) = item else {
            continue;
        };
        if let Some((name, value)) = const_env_binding(item) {
            values.entry(value).or_default().push(name);
        }
    }
    let mut constants = BTreeMap::new();
    let mut duplicates = Vec::new();
    for (value, mut names) in values {
        names.sort();
        names.dedup();
        if names.len() > 1 {
            duplicates.push(format!("{value}: {}", names.join(", ")));
            continue;
        }
        constants.insert(value, names.remove(0));
    }
    if !duplicates.is_empty() {
        return Err(LintError::new(format!(
            "{path}: duplicate ENV_* values: {}",
            duplicates.join("; ")
        )));
    }
    Ok(constants)
}

fn const_env_binding(item: &ItemConst) -> Option<(String, String)> {
    let name = item.ident.to_string();
    if !name.starts_with("ENV_") {
        return None;
    }
    let Expr::Lit(expr) = item.expr.as_ref() else {
        return None;
    };
    let Lit::Str(lit) = &expr.lit else {
        return None;
    };
    let value = lit.value();
    if value.ends_with("_SH") {
        return None;
    }
    Some((name, value))
}

fn load_exemptions(repository: &Repository) -> Result<Vec<Exemption>, LintError> {
    let path = RepoPath::from_trusted(EXEMPTIONS_PATH);
    if repository.paths().binary_search(&path).is_err() {
        return Ok(Vec::new());
    }
    let source = repository.read_utf8(&path)?;
    parse_exemptions(EXEMPTIONS_PATH, &source)
}

fn parse_exemptions(path: &str, source: &str) -> Result<Vec<Exemption>, LintError> {
    let items = parse_json_array_of_objects(path, source.trim())?;
    let mut exemptions = Vec::with_capacity(items.len());
    for (index, item) in items.into_iter().enumerate() {
        let file = required_string(&item, "file", path, index)?;
        let reason = required_string(&item, "reason", path, index)?;
        if reason.trim().is_empty() {
            return Err(LintError::new(format!(
                "{path}: exemption {index} has invalid reason"
            )));
        }
        let env_name = optional_string(&item, "env_name", path, index)?;
        let constant = optional_string(&item, "constant", path, index)?;
        if let Some(name) = &constant
            && !name.starts_with("ENV_")
        {
            return Err(LintError::new(format!(
                "{path}: exemption {index} has invalid constant"
            )));
        }
        for key in item.keys() {
            if !matches!(key.as_str(), "file" | "reason" | "env_name" | "constant") {
                return Err(LintError::new(format!(
                    "{path}: exemption {index} has unknown key {key}"
                )));
            }
        }
        exemptions.push(Exemption {
            file,
            env_name,
            constant,
        });
    }
    Ok(exemptions)
}

fn parse_json_array_of_objects(
    path: &str,
    source: &str,
) -> Result<Vec<BTreeMap<String, String>>, LintError> {
    let Some(body) = source.strip_prefix('[').and_then(|rest| rest.strip_suffix(']')) else {
        return Err(LintError::new(format!(
            "{path}: exemptions must be a JSON array"
        )));
    };
    let body = body.trim();
    if body.is_empty() {
        return Ok(Vec::new());
    }
    let mut objects = Vec::new();
    let mut rest = body;
    loop {
        let (object, remaining) = parse_json_object(path, rest)?;
        objects.push(object);
        rest = remaining.trim_start();
        if rest.is_empty() {
            break;
        }
        let Some(after_comma) = rest.strip_prefix(',') else {
            return Err(LintError::new(format!(
                "{path}: exemptions array entries must be comma-separated objects"
            )));
        };
        rest = after_comma.trim_start();
        if rest.is_empty() {
            return Err(LintError::new(format!(
                "{path}: exemptions array has a trailing comma"
            )));
        }
    }
    Ok(objects)
}

fn parse_json_object<'source>(
    path: &str,
    source: &'source str,
) -> Result<(BTreeMap<String, String>, &'source str), LintError> {
    let source = source.trim_start();
    let Some(source) = source.strip_prefix('{') else {
        return Err(LintError::new(format!(
            "{path}: exemption entries must be JSON objects"
        )));
    };
    let mut fields = BTreeMap::new();
    let mut rest = source.trim_start();
    if let Some(end) = rest.strip_prefix('}') {
        return Ok((fields, end));
    }
    loop {
        let (key, after_key) = parse_json_string(path, rest)?;
        rest = after_key.trim_start();
        let Some(after_colon) = rest.strip_prefix(':') else {
            return Err(LintError::new(format!(
                "{path}: exemption object is missing a colon"
            )));
        };
        rest = after_colon.trim_start();
        let (value, after_value) = parse_json_string(path, rest)?;
        if fields.insert(key.clone(), value).is_some() {
            return Err(LintError::new(format!(
                "{path}: exemption object has duplicate key {key}"
            )));
        }
        rest = after_value.trim_start();
        if let Some(end) = rest.strip_prefix('}') {
            return Ok((fields, end));
        }
        let Some(after_comma) = rest.strip_prefix(',') else {
            return Err(LintError::new(format!(
                "{path}: exemption object fields must be comma-separated"
            )));
        };
        rest = after_comma.trim_start();
    }
}

fn parse_json_string<'source>(
    path: &str,
    source: &'source str,
) -> Result<(String, &'source str), LintError> {
    let source = source.trim_start();
    let Some(source) = source.strip_prefix('"') else {
        return Err(LintError::new(format!(
            "{path}: exemption strings must be JSON-encoded"
        )));
    };
    let mut out = String::new();
    let mut chars = source.char_indices();
    while let Some((index, character)) = chars.next() {
        match character {
            '"' => return Ok((out, &source[index + 1..])),
            '\\' => {
                let Some((_, escaped)) = chars.next() else {
                    return Err(LintError::new(format!(
                        "{path}: exemption string has a truncated escape"
                    )));
                };
                let decoded = match escaped {
                    '"' | '\\' | '/' => escaped,
                    'n' => '\n',
                    't' => '\t',
                    'r' => '\r',
                    _ => {
                        return Err(LintError::new(format!(
                            "{path}: exemption string has an unsupported escape"
                        )));
                    }
                };
                out.push(decoded);
            }
            character => out.push(character),
        }
    }
    Err(LintError::new(format!(
        "{path}: exemption string is missing a closing quote"
    )))
}

fn required_string(
    item: &BTreeMap<String, String>,
    key: &str,
    path: &str,
    index: usize,
) -> Result<String, LintError> {
    item.get(key)
        .cloned()
        .filter(|value| !value.is_empty())
        .ok_or_else(|| LintError::new(format!("{path}: exemption {index} has invalid {key}")))
}

fn optional_string(
    item: &BTreeMap<String, String>,
    key: &str,
    path: &str,
    index: usize,
) -> Result<Option<String>, LintError> {
    match item.get(key) {
        None => Ok(None),
        Some(value) if value.is_empty() => Err(LintError::new(format!(
            "{path}: exemption {index} has invalid {key}"
        ))),
        Some(value) => Ok(Some(value.clone())),
    }
}

fn is_test_path(path: &str) -> bool {
    path.split('/').any(|part| part == "tests")
        || path.rsplit('/').next().is_some_and(|name| {
            name.starts_with("test_") || name.ends_with("_test.rs") || name == "tests.rs"
        })
}

fn scan_source(
    path: &str,
    source: &str,
    constants: &BTreeMap<String, String>,
    exemptions: &[Exemption],
) -> Result<Vec<Finding>, LintError> {
    let syntax = RustSyntax::parse(path, source)?;
    let mut visitor = EnvVisitor {
        env_modules: HashSet::new(),
        env_fns: HashMap::new(),
        matches: Vec::new(),
    };
    visitor.visit_file(syntax.file());
    let lines: Vec<&str> = source.lines().collect();
    let mut occurrence = 0_u32;
    let mut needle_counts: HashMap<String, u32> = HashMap::new();
    let mut findings = Vec::new();
    for (env_name, access, needle) in visitor.matches {
        let Some(constant) = constants.get(&env_name) else {
            continue;
        };
        occurrence = occurrence.saturating_add(1);
        let needle_occurrence = needle_counts.entry(needle.clone()).or_insert(0);
        *needle_occurrence = needle_occurrence.saturating_add(1);
        let line = line_of_needle(source, &needle, *needle_occurrence)?;
        let raw = RawFinding {
            env_name: env_name.clone(),
            constant: constant.clone(),
            access: access.clone(),
            occurrence,
        };
        if exemptions
            .iter()
            .any(|exemption| exemption_matches(exemption, path, &raw))
        {
            continue;
        }
        let line_index = usize::try_from(line.saturating_sub(1)).unwrap_or(0);
        let line_text = lines.get(line_index).copied().unwrap_or("");
        if suppression::reason(line_text, SUPPRESSION_TOKEN)?.is_some() {
            continue;
        }
        findings.push(Finding::new(
            path,
            line,
            format!(
                "bare environment literal {:?} for {} access {} occurrence {}",
                raw.env_name, raw.constant, raw.access, raw.occurrence
            ),
        ));
    }
    Ok(findings)
}

fn exemption_matches(exemption: &Exemption, path: &str, finding: &RawFinding) -> bool {
    if exemption.file != path {
        return false;
    }
    match (&exemption.env_name, &exemption.constant) {
        (None, None) => true,
        (Some(env_name), Some(constant)) => {
            finding.env_name == *env_name && finding.constant == *constant
        }
        (Some(env_name), None) => finding.env_name == *env_name,
        (None, Some(constant)) => finding.constant == *constant,
    }
}

fn line_of_needle(source: &str, needle: &str, occurrence: u32) -> Result<u32, LintError> {
    let mut seen = 0_u32;
    for (index, line) in source.lines().enumerate() {
        let mut rest = line;
        while let Some(offset) = rest.find(needle) {
            seen = seen.saturating_add(1);
            if seen == occurrence {
                return u32::try_from(index + 1)
                    .map_err(|_| LintError::new("line number exceeds u32"));
            }
            rest = &rest[offset + needle.len()..];
        }
    }
    Err(LintError::new(format!(
        "cannot locate environment literal needle {needle:?}"
    )))
}

struct EnvVisitor {
    env_modules: HashSet<String>,
    env_fns: HashMap<String, String>,
    matches: Vec<(String, String, String)>,
}

impl<'ast> Visit<'ast> for EnvVisitor {
    fn visit_item_use(&mut self, node: &'ast ItemUse) {
        record_use_tree(&node.tree, &mut self.env_modules, &mut self.env_fns, &[]);
        syn::visit::visit_item_use(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast ExprCall) {
        if let Some((access, env_name, call_name)) =
            call_env_access(node, &self.env_modules, &self.env_fns)
        {
            self.matches.push((
                env_name.clone(),
                access,
                format!(
                    "{}(\"{}\"",
                    call_name,
                    escape_rust_string_literal(&env_name)
                ),
            ));
        }
        syn::visit::visit_expr_call(self, node);
    }
}

fn record_use_tree(
    tree: &UseTree,
    env_modules: &mut HashSet<String>,
    env_fns: &mut HashMap<String, String>,
    prefix: &[String],
) {
    match tree {
        UseTree::Path(path) => {
            let mut next = prefix.to_vec();
            next.push(path.ident.to_string());
            record_use_tree(&path.tree, env_modules, env_fns, &next);
        }
        UseTree::Name(name) => apply_use_import(
            env_modules,
            env_fns,
            prefix,
            &name.ident.to_string(),
            &name.ident.to_string(),
        ),
        UseTree::Rename(rename) => apply_use_import(
            env_modules,
            env_fns,
            prefix,
            &rename.ident.to_string(),
            &rename.rename.to_string(),
        ),
        UseTree::Glob(_) => {
            let refs: Vec<&str> = prefix.iter().map(String::as_str).collect();
            if refs == ["std", "env"] || refs == ["env"] {
                for function in ENV_FNS {
                    env_fns.insert((*function).to_owned(), (*function).to_owned());
                }
            }
        }
        UseTree::Group(group) => {
            for item in &group.items {
                record_use_tree(item, env_modules, env_fns, prefix);
            }
        }
    }
}

fn apply_use_import(
    env_modules: &mut HashSet<String>,
    env_fns: &mut HashMap<String, String>,
    prefix: &[String],
    imported: &str,
    local: &str,
) {
    let mut full: Vec<&str> = prefix.iter().map(String::as_str).collect();
    full.push(imported);
    if full == ["std", "env"] || (prefix.is_empty() && imported == "env") {
        env_modules.insert(local.to_owned());
        return;
    }
    let is_env_fn = ENV_FNS.contains(&imported)
        && ((full.len() == 3 && full[0] == "std" && full[1] == "env")
            || (full.len() == 2 && full[0] == "env"));
    if is_env_fn {
        env_fns.insert(local.to_owned(), imported.to_owned());
    }
}

fn call_env_access(
    call: &ExprCall,
    env_modules: &HashSet<String>,
    env_fns: &HashMap<String, String>,
) -> Option<(String, String, String)> {
    let env_name = first_string_arg(call.args.first()?)?;
    let (access, call_name) = match call.func.as_ref() {
        Expr::Path(path) => path_env_access(path, env_modules, env_fns)?,
        _ => return None,
    };
    Some((access, env_name, call_name))
}

fn path_env_access(
    path: &ExprPath,
    env_modules: &HashSet<String>,
    env_fns: &HashMap<String, String>,
) -> Option<(String, String)> {
    let segments: Vec<String> = path
        .path
        .segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect();
    match segments.as_slice() {
        [module, function]
            if env_modules.contains(module) && ENV_FNS.contains(&function.as_str()) =>
        {
            Some((function.clone(), function.clone()))
        }
        [function] => env_fns
            .get(function)
            .cloned()
            .map(|access| (access, function.clone())),
        [std, env, function]
            if std == "std" && env == "env" && ENV_FNS.contains(&function.as_str()) =>
        {
            Some((function.clone(), function.clone()))
        }
        _ => None,
    }
}

fn first_string_arg(expr: &Expr) -> Option<String> {
    match expr {
        Expr::Lit(lit) => match &lit.lit {
            Lit::Str(value) => Some(value.value()),
            _ => None,
        },
        _ => None,
    }
}

fn escape_rust_string_literal(value: &str) -> String {
    let mut escaped = String::with_capacity(value.len());
    for character in value.chars() {
        match character {
            '\\' => escaped.push_str("\\\\"),
            '"' => escaped.push_str("\\\""),
            '\n' => escaped.push_str("\\n"),
            '\r' => escaped.push_str("\\r"),
            '\t' => escaped.push_str("\\t"),
            character => escaped.push(character),
        }
    }
    escaped
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use super::{OWNER_PATH, parse_env_constants, parse_exemptions, scan_source};

    #[test]
    fn parses_owned_env_constants() {
        let constants = parse_env_constants(
            OWNER_PATH,
            "pub const ENV_SESSION: &str = \"SESSION_ID\";\nconst ENV_SKIP_SH: &str = \"SCRIPT_SH\";\n",
        )
        .expect("constants");
        assert_eq!(
            constants,
            BTreeMap::from([("SESSION_ID".to_owned(), "ENV_SESSION".to_owned())])
        );
    }

    #[test]
    fn detects_reads_writes_and_aliases() {
        let constants =
            BTreeMap::from([("SESSION_ID".to_owned(), "ENV_SESSION".to_owned())]);
        let source = r#"
use std::env;
use std::env::var as read_var;
use std::env::{set_var as write_var, remove_var};

fn demo() {
    let _ = env::var("SESSION_ID");
    let _ = std::env::var_os("SESSION_ID");
    let _ = read_var("SESSION_ID");
    write_var("SESSION_ID", "x");
    remove_var("SESSION_ID");
}
"#;
        assert_eq!(
            scan_source("demo.rs", source, &constants, &[])
                .expect("scan")
                .len(),
            5
        );
    }

    #[test]
    fn honors_reason_bearing_suppressions_and_exemptions() {
        let constants =
            BTreeMap::from([("SESSION_ID".to_owned(), "ENV_SESSION".to_owned())]);
        let suppressed = "fn demo() { let _ = std::env::var(\"SESSION_ID\"); // lint-env-via-config-constant: ok fixture\n}\n";
        assert!(
            scan_source("demo.rs", suppressed, &constants, &[])
                .expect("scan")
                .is_empty()
        );
        let exemptions = parse_exemptions(
            "exemptions.json",
            r#"[{"file":"demo.rs","reason":"owner carve-out","env_name":"SESSION_ID"}]"#,
        )
        .expect("exemptions");
        let unsuppressed = "fn demo() { let _ = std::env::var(\"SESSION_ID\");\n}\n";
        assert!(
            scan_source("demo.rs", unsuppressed, &constants, &exemptions)
                .expect("scan")
                .is_empty()
        );
    }

    #[test]
    fn ignores_unknown_literals_and_constant_uses() {
        let constants =
            BTreeMap::from([("SESSION_ID".to_owned(), "ENV_SESSION".to_owned())]);
        let source = r#"
const ENV_SESSION: &str = "SESSION_ID";
fn demo() {
    let _ = std::env::var(ENV_SESSION);
    let _ = std::env::var("UNKNOWN");
}
"#;
        assert!(
            scan_source("demo.rs", source, &constants, &[])
                .expect("scan")
                .is_empty()
        );
    }
}
