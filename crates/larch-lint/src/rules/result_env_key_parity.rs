//! Compare sibling result-env writers and reject divergent key sets.
//!
//! # Crate survey (issue #7617)
//!
//! | Need | Candidates | Selection |
//! |------|------------|-----------|
//! | Rust syntax | workspace `syn` | Use `syn` visitors to collect literal writer calls. Line numbers come from the source text (no new `proc-macro2` feature; leaves must not add workspace dependencies). Custom code owns only writer-name, basename, and key-tuple shapes. |
//! | Suppression parsing | workspace shared `suppression` module | Reuse the reason-bearing `lint-<rule>: ok <reason>` helper from #7604. |
//! | Serialization / baselines | workspace `serde`/`toml` | Not required: the Rust corpus starts at zero findings, so no grandfathering baseline ships. |
//!
//! No workspace `Cargo.toml` dependency is added (umbrella concurrency contract).

use std::collections::{BTreeMap, BTreeSet};

use syn::{
    Expr, ExprCall, ExprMethodCall, ExprPath, Lit, Member,
    visit::{self, Visit},
};

use crate::{
    Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, suppression,
    syntax::RustSyntax,
};

const NAME: &str = "result-env-key-parity";
const DESCRIPTION: &str =
    "Reject divergent key sets across sibling writers of the same result-env basename";
const SUPPRESSION_TOKEN: &str = "lint-result-env-key-parity";
const WRITER_EXACT_NAMES: &[&str] = &["phase_driver_write_result_env", "write_result_env"];
const WRITER_SUFFIX: &str = "_write_result_env";
const MIN_SIBLING_WRITERS: usize = 2;

/// Per-basename keys a writer may omit without violating parity (G-Cfg-3).
const OPTIONAL_KEYS: &[(&str, &[&str])] = &[];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/result-env-key-parity.toml",
);

#[derive(Debug)]
pub struct ResultEnvKeyParityRule;

pub static RULE: ResultEnvKeyParityRule = ResultEnvKeyParityRule;

impl Rule for ResultEnvKeyParityRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<Vec<Finding>, LintError> {
        let selector = PathSelector::new(&["crates/**/*.rs"], &[])?;
        let mut writers = Vec::new();
        let mut sources: BTreeMap<String, String> = BTreeMap::new();
        for path in selector.select(repository) {
            let source = repository.read_utf8(path)?;
            writers.extend(collect_writers(path, &source)?);
            sources.insert(path.as_str().to_owned(), source);
        }
        for writer in &mut writers {
            writer.line = resolve_writer_line(
                sources.get(&writer.path).map_or("", String::as_str),
                &writer.callee,
                &writer.basename,
                writer.occurrence,
            );
        }
        findings_for_writers(&writers, &sources)
    }
}

crate::register_rule!(METADATA, RULE);

#[derive(Clone, Debug, Eq, PartialEq)]
struct WriterCall {
    path: String,
    line: u32,
    callee: String,
    basename: String,
    keys: BTreeSet<String>,
    occurrence: usize,
}

fn collect_writers(path: &RepoPath, source: &str) -> Result<Vec<WriterCall>, LintError> {
    let syntax = RustSyntax::parse(path.as_str(), source)?;
    let mut visitor = WriterVisitor {
        path: path.as_str().to_owned(),
        writers: Vec::new(),
        occurrence_by_key: BTreeMap::new(),
    };
    visitor.visit_file(syntax.file());
    Ok(visitor.writers)
}

struct WriterVisitor {
    path: String,
    writers: Vec<WriterCall>,
    occurrence_by_key: BTreeMap<(String, String), usize>,
}

impl<'ast> Visit<'ast> for WriterVisitor {
    fn visit_expr_call(&mut self, node: &'ast ExprCall) {
        if let Some(name) = callee_name(&node.func)
            && is_writer_name(&name)
        {
            self.maybe_record(&name, node.args.iter());
        }
        visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast ExprMethodCall) {
        let name = node.method.to_string();
        if is_writer_name(&name) {
            self.maybe_record(&name, node.args.iter());
        }
        visit::visit_expr_method_call(self, node);
    }
}

impl WriterVisitor {
    fn maybe_record<'a>(&mut self, callee: &str, args: impl Iterator<Item = &'a Expr>) {
        let args: Vec<&Expr> = args.collect();
        let Some(basename) = args.iter().find_map(|expr| literal_basename(expr)) else {
            return;
        };
        let Some(keys) = args.iter().find_map(|expr| literal_keys(expr)) else {
            return;
        };
        let occurrence_key = (callee.to_owned(), basename.clone());
        let occurrence = self.occurrence_by_key.entry(occurrence_key).or_insert(0);
        *occurrence += 1;
        self.writers.push(WriterCall {
            path: self.path.clone(),
            line: 1,
            callee: callee.to_owned(),
            basename,
            keys,
            occurrence: *occurrence,
        });
    }
}

fn resolve_writer_line(source: &str, callee: &str, basename: &str, occurrence: usize) -> u32 {
    let mut seen = 0usize;
    for (index, line) in source.lines().enumerate() {
        if line.contains(callee) && line.contains(basename) {
            seen += 1;
            if seen == occurrence {
                return u32::try_from(index + 1).unwrap_or(1);
            }
        }
    }
    // Multi-line call: basename may be on a later line than the callee.
    seen = 0;
    let lines: Vec<&str> = source.lines().collect();
    for (index, line) in lines.iter().enumerate() {
        if !line.contains(callee) {
            continue;
        }
        let window = lines[index..].iter().take(6).copied().collect::<Vec<_>>().join("\n");
        if window.contains(basename) {
            seen += 1;
            if seen == occurrence {
                return u32::try_from(index + 1).unwrap_or(1);
            }
        }
    }
    1
}

fn is_writer_name(name: &str) -> bool {
    WRITER_EXACT_NAMES.contains(&name) || name.ends_with(WRITER_SUFFIX)
}

fn callee_name(expr: &Expr) -> Option<String> {
    match expr {
        Expr::Path(ExprPath { path, .. }) => path.segments.last().map(|s| s.ident.to_string()),
        Expr::Field(field) => match &field.member {
            Member::Named(ident) => Some(ident.to_string()),
            Member::Unnamed(_) => None,
        },
        Expr::Paren(paren) => callee_name(&paren.expr),
        _ => None,
    }
}

fn literal_basename(expr: &Expr) -> Option<String> {
    match expr {
        Expr::Lit(lit) => match &lit.lit {
            Lit::Str(string) => basename_from_path(&string.value()),
            _ => None,
        },
        Expr::Reference(reference) => literal_basename(&reference.expr),
        Expr::Paren(paren) => literal_basename(&paren.expr),
        Expr::Call(call) => {
            let name = callee_name(&call.func)?;
            if matches!(name.as_str(), "new" | "from" | "from_str") {
                call.args.iter().find_map(literal_basename)
            } else {
                None
            }
        }
        Expr::MethodCall(method) => {
            let name = method.method.to_string();
            if name == "join" {
                method.args.iter().find_map(literal_basename)
            } else {
                literal_basename(&method.receiver)
                    .or_else(|| method.args.iter().find_map(literal_basename))
            }
        }
        Expr::Binary(binary) if matches!(binary.op, syn::BinOp::Div(_)) => {
            literal_basename(&binary.right)
        }
        _ => None,
    }
}

fn basename_from_path(value: &str) -> Option<String> {
    let base = value.rsplit('/').next().unwrap_or(value);
    if base.is_empty() {
        return None;
    }
    // Result-env basenames are lowercase `.env` by convention; keep the exact
    // suffix check so `Foo.ENV` is not treated as a result-env target.
    #[allow(clippy::case_sensitive_file_extension_comparisons)] // intentional exact `.env`
    if base.ends_with(".env") {
        Some(base.to_owned())
    } else {
        None
    }
}

fn literal_keys(expr: &Expr) -> Option<BTreeSet<String>> {
    match expr {
        Expr::Array(array) => keys_from_elements(array.elems.iter()),
        Expr::Reference(reference) => literal_keys(&reference.expr),
        Expr::Paren(paren) => literal_keys(&paren.expr),
        Expr::Call(call) => call.args.iter().find_map(literal_keys),
        Expr::Macro(mac) => {
            let name = mac
                .mac
                .path
                .segments
                .last()
                .map(|segment| segment.ident.to_string())
                .unwrap_or_default();
            if name == "vec" {
                parse_vec_macro_keys(&mac.mac.tokens.to_string())
            } else {
                None
            }
        }
        _ => None,
    }
}

fn keys_from_elements<'a>(elements: impl Iterator<Item = &'a Expr>) -> Option<BTreeSet<String>> {
    let mut keys = BTreeSet::new();
    for element in elements {
        let key = match element {
            Expr::Tuple(tuple) if tuple.elems.len() == 2 => string_literal(tuple.elems.first()?),
            Expr::Call(call) if call.args.len() == 2 => string_literal(call.args.first()?),
            _ => None,
        }?;
        keys.insert(key);
    }
    Some(keys)
}

fn string_literal(expr: &Expr) -> Option<String> {
    match expr {
        Expr::Lit(lit) => match &lit.lit {
            Lit::Str(string) => Some(string.value()),
            _ => None,
        },
        Expr::Reference(reference) => string_literal(&reference.expr),
        Expr::Call(call) => call.args.iter().find_map(string_literal),
        Expr::MethodCall(method) => method.args.iter().find_map(string_literal),
        _ => None,
    }
}

fn parse_vec_macro_keys(tokens: &str) -> Option<BTreeSet<String>> {
    let mut keys = BTreeSet::new();
    let mut rest = tokens;
    while let Some(start) = rest.find("(\"") {
        rest = &rest[start + 2..];
        let end = rest.find('"')?;
        keys.insert(rest[..end].to_owned());
        rest = &rest[end + 1..];
        let close = rest.find(')')?;
        rest = &rest[close + 1..];
    }
    if keys.is_empty() { None } else { Some(keys) }
}

fn optional_keys_for(basename: &str) -> BTreeSet<String> {
    OPTIONAL_KEYS
        .iter()
        .find(|(name, _)| *name == basename)
        .map(|(_, keys)| keys.iter().map(|key| (*key).to_owned()).collect())
        .unwrap_or_default()
}

fn findings_for_writers(
    writers: &[WriterCall],
    sources: &BTreeMap<String, String>,
) -> Result<Vec<Finding>, LintError> {
    let mut by_basename: BTreeMap<&str, Vec<&WriterCall>> = BTreeMap::new();
    for writer in writers {
        by_basename
            .entry(writer.basename.as_str())
            .or_default()
            .push(writer);
    }
    let mut required: BTreeMap<&str, BTreeSet<String>> = BTreeMap::new();
    for (basename, group) in &by_basename {
        if group.len() < MIN_SIBLING_WRITERS {
            continue;
        }
        let mut union = BTreeSet::new();
        for writer in group {
            union.extend(writer.keys.iter().cloned());
        }
        for key in optional_keys_for(basename) {
            union.remove(&key);
        }
        required.insert(basename, union);
    }

    let mut findings = Vec::new();
    for writer in writers {
        let Some(needed) = required.get(writer.basename.as_str()) else {
            continue;
        };
        let missing: Vec<&String> = needed.difference(&writer.keys).collect();
        if missing.is_empty() {
            continue;
        }
        let line_text = sources
            .get(&writer.path)
            .and_then(|source| source.lines().nth(usize::try_from(writer.line).ok()?.checked_sub(1)?))
            .unwrap_or("");
        if suppression::reason(line_text, SUPPRESSION_TOKEN)?.is_some() {
            continue;
        }
        for key in missing {
            findings.push(Finding::new(
                writer.path.clone(),
                writer.line,
                format!(
                    "{} writer missing key {key} present in sibling writers",
                    writer.basename
                ),
            ));
        }
    }
    findings.sort();
    findings.dedup();
    Ok(findings)
}

#[cfg(test)]
mod tests {
    use super::{OPTIONAL_KEYS, ResultEnvKeyParityRule};
    use crate::{Git, LintError, Repository, Rule};
    use std::path::{Path, PathBuf};

    struct Fixture {
        _temporary: tempfile::TempDir,
        repository: Repository,
    }

    struct FakeGit {
        root: PathBuf,
        stream: Vec<u8>,
    }

    impl Git for FakeGit {
        fn repository_root(&self, _cwd: &Path) -> Result<PathBuf, LintError> {
            Ok(self.root.clone())
        }

        fn tracked_paths(&self, _root: &Path) -> Result<Vec<u8>, LintError> {
            Ok(self.stream.clone())
        }
    }

    fn repository_with(files: &[(&str, &str)]) -> Fixture {
        let temporary = tempfile::tempdir().expect("tempdir");
        let mut stream = Vec::new();
        for (relative, contents) in files {
            let path = temporary.path().join(relative);
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).expect("parents");
            }
            std::fs::write(&path, contents).expect("write");
            stream.extend(relative.as_bytes());
            stream.push(0);
        }
        let repository = Repository::discover(
            &FakeGit {
                root: temporary.path().to_path_buf(),
                stream,
            },
            temporary.path(),
        )
        .expect("repository");
        Fixture {
            _temporary: temporary,
            repository,
        }
    }

    fn writer_src(basename: &str, keys: &[&str], pragma: bool) -> String {
        let open = if pragma {
            "    write_result_env(  // lint-result-env-key-parity: ok fixture divergence\n"
        } else {
            "    write_result_env(\n"
        };
        let items = keys
            .iter()
            .map(|key| format!("(\"{key}\", \"value\")"))
            .collect::<Vec<_>>()
            .join(", ");
        format!(
            "fn emit(path: &str) {{\n{open}        \"{basename}\",\n        [{items}],\n    );\n}}\n"
        )
    }

    #[test]
    fn identical_key_sets_are_clean() {
        let fixture = repository_with(&[
            (
                "crates/a/src/lib.rs",
                &writer_src("slot.env", &["A", "B"], false),
            ),
            (
                "crates/b/src/lib.rs",
                &writer_src("slot.env", &["A", "B"], false),
            ),
        ]);
        assert!(
            ResultEnvKeyParityRule
                .check(&fixture.repository)
                .expect("check")
                .is_empty()
        );
    }

    #[test]
    fn missing_key_names_basename_and_key() {
        let fixture = repository_with(&[
            (
                "crates/a/src/lib.rs",
                &writer_src("slot.env", &["A", "B"], false),
            ),
            (
                "crates/b/src/lib.rs",
                &writer_src("slot.env", &["A"], false),
            ),
        ]);
        let findings = ResultEnvKeyParityRule
            .check(&fixture.repository)
            .expect("check");
        assert_eq!(findings.len(), 1);
        assert_eq!(
            findings[0].to_string(),
            "crates/b/src/lib.rs:2: slot.env writer missing key B present in sibling writers"
        );
    }

    #[test]
    fn single_writer_and_dynamic_keys_are_skipped() {
        let solo = repository_with(&[(
            "crates/a/src/lib.rs",
            &writer_src("solo.env", &["A", "B", "C"], false),
        )]);
        assert!(
            ResultEnvKeyParityRule
                .check(&solo.repository)
                .expect("check")
                .is_empty()
        );

        let dynamic = repository_with(&[
            (
                "crates/a/src/lib.rs",
                &writer_src("slot.env", &["A", "B"], false),
            ),
            (
                "crates/b/src/lib.rs",
                "fn emit(rows: &[(&str, &str)]) {\n    write_result_env(\"slot.env\", rows);\n}\n",
            ),
        ]);
        assert!(
            ResultEnvKeyParityRule
                .check(&dynamic.repository)
                .expect("check")
                .is_empty()
        );
    }

    #[test]
    fn pragma_suppresses_divergent_writer() {
        let fixture = repository_with(&[
            (
                "crates/a/src/lib.rs",
                &writer_src("slot.env", &["A", "B"], false),
            ),
            (
                "crates/b/src/lib.rs",
                &writer_src("slot.env", &["A"], true),
            ),
        ]);
        assert!(
            ResultEnvKeyParityRule
                .check(&fixture.repository)
                .expect("check")
                .is_empty()
        );
    }

    #[test]
    fn join_basename_and_method_call_are_detected() {
        let fixture = repository_with(&[
            (
                "crates/a/src/lib.rs",
                "fn emit(dir: &std::path::Path) {\n    write_result_env(dir.join(\"slot.env\"), [(\"A\", \"1\"), (\"B\", \"2\")]);\n}\n",
            ),
            (
                "crates/b/src/lib.rs",
                "fn emit(helper: Helper) {\n    helper.phase_driver_write_result_env(\"slot.env\", [(\"A\", \"1\")]);\n}\nstruct Helper;\nimpl Helper {\n    fn phase_driver_write_result_env(&self, _path: &str, _kvs: [(&str, &str); 1]) {}\n}\n",
            ),
        ]);
        let findings = ResultEnvKeyParityRule
            .check(&fixture.repository)
            .expect("check");
        assert_eq!(findings.len(), 1);
        assert!(findings[0].to_string().contains("missing key B"));
    }

    #[test]
    fn optional_keys_table_is_the_declared_exception_surface() {
        assert!(OPTIONAL_KEYS.is_empty());
    }
}
