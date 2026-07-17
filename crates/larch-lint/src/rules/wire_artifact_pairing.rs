//! Require a production Rust or shell writer for every wire-artifact reader.
//!
//! This is the future-state Rust equivalent of the Python
//! `wire-artifact-pairing` lint. It scans production Rust sources and residual
//! shell writers for a curated manifest of larch wire artifacts and reports any
//! artifact that has reader evidence but no paired production writer. Existing
//! one-sided artifacts are grandfathered in a reason-bearing baseline that only
//! shrinks.
//!
//! Scope note: the larch-lint crate is excluded from the scanned surface. It
//! names wire artifacts as lint configuration, not as run-time reads or writes,
//! so including it would report meta-references as one-sided artifacts. The
//! runtime migration lands larch runtime code in its own crate, which this rule
//! scans.
//!
//! Crate survey: manifest and baseline parsing reuse the workspace `toml` and
//! `serde` crates; Rust reader and writer evidence reuses the shared `syn`
//! parser behind [`crate::syntax::RustSyntax`]; path selection reuses the
//! `globset`-backed [`PathSelector`]. The bespoke code expresses only the larch
//! artifact manifest schema, the artifact-token matching (basename boundary and
//! relative-path membership), and the shell writer grammar, none of which a
//! general crate owns.

use std::collections::BTreeSet;

use serde::Deserialize;
use syn::visit::{self, Visit};

use crate::syntax::RustSyntax;
use crate::{Finding, LintError, PathSelector, RepoPath, Repository, Rule, RuleMetadata, RuleOutput};

const NAME: &str = "wire-artifact-pairing";
const DESCRIPTION: &str = "Require a production writer for every wire-artifact reader";
const MANIFEST_PATH: &str = "crates/larch-lint/data/wire-artifact-manifest.toml";
const BASELINE_PATH: &str = "crates/larch-lint/data/wire-artifact-pairing-baseline.toml";
const RUST_SCOPE_INCLUDE: &str = "crates/*/src/**/*.rs";
const LINTER_CRATE_EXCLUDE: &str = "crates/larch-lint/**";
const SHELL_SCOPES: [&str; 2] = ["scripts/**", "skills/*/scripts/**"];
const SHELL_TEST_PREFIX: &str = "test-";
const VALID_SIDES: [&str; 3] = ["external-writer", "external-reader", "intentionally-one-sided"];

pub static METADATA: RuleMetadata = RuleMetadata::new(
    NAME,
    DESCRIPTION,
    "crates/larch-lint/migration-ledger/wire-artifact-pairing.toml",
);

#[derive(Debug)]
pub struct WireArtifactPairingRule;

pub static RULE: WireArtifactPairingRule = WireArtifactPairingRule;

/// How a manifest artifact token is matched against source evidence.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
enum Kind {
    /// Match the bare filename on non-word boundaries.
    Basename,
    /// Match a slash-separated repository-relative path.
    RelativePath,
}

impl Kind {
    const fn label(self) -> &'static str {
        match self {
            Self::Basename => "basename",
            Self::RelativePath => "relative_path",
        }
    }
}

/// One validated manifest artifact.
#[derive(Debug)]
struct ManifestRow {
    kind: Kind,
    artifact: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ManifestFile {
    #[serde(default)]
    artifact: Vec<RawManifestRow>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawManifestRow {
    kind: String,
    name: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct BaselineFile {
    #[serde(default)]
    grandfathered: Vec<RawBaselineRow>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawBaselineRow {
    artifact: String,
    side: String,
    reason: String,
}

/// Reader and writer evidence collected once from the production Rust surface.
#[derive(Default)]
struct RustEvidence {
    reader_texts: Vec<String>,
    writer_scopes: Vec<String>,
}

impl Rule for WireArtifactPairingRule {
    fn name(&self) -> &'static str {
        NAME
    }

    fn description(&self) -> &'static str {
        DESCRIPTION
    }

    fn check(&self, repository: &Repository) -> Result<RuleOutput, LintError> {
        let Some(manifest_text) = read_optional(repository, MANIFEST_PATH)? else {
            return Ok(RuleOutput::clean());
        };
        let manifest = parse_manifest(&manifest_text)?;
        if manifest.is_empty() {
            return Ok(RuleOutput::clean());
        }
        let grandfathered = load_baseline(repository)?;
        let evidence = scan_rust(repository)?;
        let shell_lines = scan_shell(repository)?;
        let matcher = ShellMatcher::new()?;
        let mut findings = Vec::new();
        for row in &manifest {
            if grandfathered.contains(&row.artifact) {
                continue;
            }
            if !evidence.reader_texts.iter().any(|text| mentions(text, row)) {
                continue;
            }
            let has_writer = evidence.writer_scopes.iter().any(|text| mentions(text, row))
                || shell_lines
                    .iter()
                    .any(|line| matcher.writes(line, row));
            if !has_writer {
                findings.push(Finding::new(
                    MANIFEST_PATH,
                    manifest_line(&manifest_text, &row.artifact),
                    format!(
                        "wire artifact {}:{} has reader evidence but no production writer; \
                         add a writer or baseline a one-sided artifact",
                        row.kind.label(),
                        row.artifact
                    ),
                ));
            }
        }
        Ok(RuleOutput::from_findings(findings))
    }
}

/// Read a tracked file when present, returning `None` when it is not tracked.
fn read_optional(repository: &Repository, path: &str) -> Result<Option<String>, LintError> {
    let selector = PathSelector::new(&[path], &[])?;
    match selector.select(repository).first() {
        Some(repo_path) => Ok(Some(repository.read_utf8(repo_path)?)),
        None => Ok(None),
    }
}

fn parse_manifest(text: &str) -> Result<Vec<ManifestRow>, LintError> {
    let parsed: ManifestFile = toml::from_str(text)
        .map_err(|error| LintError::new(format!("{MANIFEST_PATH}: invalid manifest TOML: {error}")))?;
    let mut rows = Vec::with_capacity(parsed.artifact.len());
    let mut seen = BTreeSet::new();
    for raw in parsed.artifact {
        let row = validate_manifest_row(raw)?;
        if !seen.insert((row.kind, row.artifact.clone())) {
            return Err(LintError::new(format!(
                "{MANIFEST_PATH}: duplicate manifest artifact {}:{}",
                row.kind.label(),
                row.artifact
            )));
        }
        rows.push(row);
    }
    Ok(rows)
}

fn validate_manifest_row(raw: RawManifestRow) -> Result<ManifestRow, LintError> {
    let kind = match raw.kind.as_str() {
        "basename" => Kind::Basename,
        "relative_path" => Kind::RelativePath,
        other => {
            return Err(LintError::new(format!(
                "{MANIFEST_PATH}: invalid manifest kind {other:?}"
            )));
        }
    };
    if raw.name.is_empty() {
        return Err(LintError::new(format!(
            "{MANIFEST_PATH}: manifest artifact name must be non-empty"
        )));
    }
    match kind {
        Kind::Basename if raw.name.contains('/') || raw.name == "." || raw.name == ".." => {
            Err(LintError::new(format!(
                "{MANIFEST_PATH}: invalid basename artifact {:?}",
                raw.name
            )))
        }
        Kind::RelativePath if !valid_relative_path(&raw.name) => Err(LintError::new(format!(
            "{MANIFEST_PATH}: invalid relative_path artifact {:?}",
            raw.name
        ))),
        _ => Ok(ManifestRow {
            kind,
            artifact: raw.name,
        }),
    }
}

fn valid_relative_path(value: &str) -> bool {
    !value.is_empty()
        && !value.starts_with('/')
        && value
            .split('/')
            .all(|part| !part.is_empty() && part != "." && part != "..")
}

fn load_baseline(repository: &Repository) -> Result<BTreeSet<String>, LintError> {
    read_optional(repository, BASELINE_PATH)?
        .map_or_else(|| Ok(BTreeSet::new()), |text| parse_baseline(&text))
}

fn parse_baseline(text: &str) -> Result<BTreeSet<String>, LintError> {
    let parsed: BaselineFile = toml::from_str(text)
        .map_err(|error| LintError::new(format!("{BASELINE_PATH}: invalid baseline TOML: {error}")))?;
    let mut grandfathered = BTreeSet::new();
    for row in parsed.grandfathered {
        if !VALID_SIDES.contains(&row.side.as_str()) {
            return Err(LintError::new(format!(
                "{BASELINE_PATH}: invalid baseline side {:?}",
                row.side
            )));
        }
        if row.reason.trim().is_empty() {
            return Err(LintError::new(format!(
                "{BASELINE_PATH}: baseline artifact {:?} needs a non-empty reason",
                row.artifact
            )));
        }
        if !grandfathered.insert(row.artifact.clone()) {
            return Err(LintError::new(format!(
                "{BASELINE_PATH}: duplicate baseline artifact {:?}",
                row.artifact
            )));
        }
    }
    Ok(grandfathered)
}

/// Collect reader literals and writer-bearing function scopes from production
/// Rust, excluding the linter crate and inline `#[cfg(test)]` code.
fn scan_rust(repository: &Repository) -> Result<RustEvidence, LintError> {
    let selector = PathSelector::new(&[RUST_SCOPE_INCLUDE], &[LINTER_CRATE_EXCLUDE])?;
    let mut evidence = RustEvidence::default();
    for path in selector.select(repository) {
        let Ok(source) = repository.read_utf8(path) else {
            continue; // Skip an unreadable (e.g. non-UTF-8) file, mirroring Python `_read_text`.
        };
        let Ok(syntax) = RustSyntax::parse(path.as_str(), &source) else {
            continue; // Skip a file the shared parser cannot read, mirroring the Python leniency.
        };
        let mut scanner = FileScanner::default();
        scanner.visit_file(syntax.file());
        evidence.reader_texts.push(scanner.top_level);
        for scope in scanner.scopes {
            if scope.has_write {
                evidence.writer_scopes.push(scope.text.clone());
            }
            evidence.reader_texts.push(scope.text);
        }
    }
    Ok(evidence)
}

/// Collect non-comment lines from residual shell writer files.
fn scan_shell(repository: &Repository) -> Result<Vec<String>, LintError> {
    let selector = PathSelector::new(&SHELL_SCOPES, &[])?;
    let mut lines = Vec::new();
    for path in selector.select(repository) {
        if is_shell_test_file(path) {
            continue;
        }
        let Ok(source) = repository.read_utf8(path) else {
            // A non-UTF-8 file under the shell scope is not a writer; skip it
            // instead of failing the run, mirroring Python `_read_text`. The
            // scope reads all file types under these trees, not only scripts.
            continue;
        };
        for line in source.lines() {
            if !line.trim_start().starts_with('#') {
                lines.push(line.to_owned());
            }
        }
    }
    Ok(lines)
}

fn is_shell_test_file(path: &RepoPath) -> bool {
    path.as_str()
        .rsplit('/')
        .next()
        .is_some_and(|name| name.starts_with(SHELL_TEST_PREFIX))
}

/// One collected function scope: its string-literal text and write evidence.
struct FnScope {
    text: String,
    has_write: bool,
}

/// File-level collector: top-level reader literals plus per-function scopes.
#[derive(Default)]
struct FileScanner {
    top_level: String,
    scopes: Vec<FnScope>,
}

impl FileScanner {
    fn scan_body(block: &syn::Block) -> FnScope {
        let mut scanner = FnScanner::default();
        scanner.visit_block(block);
        FnScope {
            text: scanner.text,
            has_write: scanner.has_write,
        }
    }
}

impl<'ast> Visit<'ast> for FileScanner {
    fn visit_lit_str(&mut self, node: &'ast syn::LitStr) {
        self.top_level.push_str(&node.value());
        self.top_level.push('\n');
    }

    fn visit_item_mod(&mut self, node: &'ast syn::ItemMod) {
        if has_cfg_test(&node.attrs) {
            return;
        }
        visit::visit_item_mod(self, node);
    }

    fn visit_item_fn(&mut self, node: &'ast syn::ItemFn) {
        if has_cfg_test(&node.attrs) {
            return;
        }
        self.scopes.push(Self::scan_body(&node.block));
    }

    fn visit_impl_item_fn(&mut self, node: &'ast syn::ImplItemFn) {
        if has_cfg_test(&node.attrs) {
            return;
        }
        self.scopes.push(Self::scan_body(&node.block));
    }

    fn visit_trait_item_fn(&mut self, node: &'ast syn::TraitItemFn) {
        if has_cfg_test(&node.attrs) {
            return;
        }
        if let Some(block) = &node.default {
            self.scopes.push(Self::scan_body(block));
        }
    }
}

/// Function-body collector: string literals and write-call evidence.
#[derive(Default)]
struct FnScanner {
    text: String,
    has_write: bool,
}

impl<'ast> Visit<'ast> for FnScanner {
    fn visit_lit_str(&mut self, node: &'ast syn::LitStr) {
        self.text.push_str(&node.value());
        self.text.push('\n');
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        if is_write_name(&node.method.to_string()) {
            self.has_write = true;
        }
        visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        if let syn::Expr::Path(path) = node.func.as_ref()
            && last_segment(&path.path).is_some_and(|name| is_write_name(&name))
        {
            self.has_write = true;
        }
        visit::visit_expr_call(self, node);
    }
}

fn last_segment(path: &syn::Path) -> Option<String> {
    path.segments.last().map(|segment| segment.ident.to_string())
}

/// Whether a call name is generous writer evidence. Over-matching only clears a
/// finding, never invents one, so a broad set is the safe direction.
fn is_write_name(name: &str) -> bool {
    matches!(
        name,
        "write" | "write_all" | "write_fmt" | "create" | "create_new" | "touch"
    ) || name.contains("atomic_write")
        || name.starts_with("write_")
        || name.starts_with("_write")
        || name.ends_with("_atomic")
}

fn has_cfg_test(attrs: &[syn::Attribute]) -> bool {
    attrs.iter().any(|attr| {
        if attr.path().is_ident("test") {
            return true;
        }
        if !attr.path().is_ident("cfg") {
            return false;
        }
        match &attr.meta {
            syn::Meta::List(list) => list.tokens.to_string().contains("test"),
            _ => false,
        }
    })
}

/// Whether collected evidence text mentions a manifest artifact.
fn mentions(text: &str, row: &ManifestRow) -> bool {
    match row.kind {
        Kind::Basename => boundary_contains(text, &row.artifact),
        Kind::RelativePath => {
            text.contains(&row.artifact)
                || text.contains(&format!("/{}", row.artifact))
                || row
                    .artifact
                    .split('/')
                    .filter(|part| !part.is_empty())
                    .all(|part| text.contains(part))
        }
    }
}

/// Substring match that rejects filename-character neighbours, mirroring the
/// Python negative-lookaround boundary over `[A-Za-z0-9_.-]`.
fn boundary_contains(text: &str, needle: &str) -> bool {
    if needle.is_empty() {
        return false;
    }
    let bytes = text.as_bytes();
    let mut offset = 0;
    while let Some(found) = text[offset..].find(needle) {
        let start = offset + found;
        let end = start + needle.len();
        let before_ok = start == 0 || !is_filename_byte(bytes[start - 1]);
        let after_ok = end >= bytes.len() || !is_filename_byte(bytes[end]);
        if before_ok && after_ok {
            return true;
        }
        offset = start + 1;
    }
    false
}

const fn is_filename_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_' || byte == b'.' || byte == b'-'
}

fn manifest_line(text: &str, artifact: &str) -> u32 {
    let needle = format!("\"{artifact}\"");
    for (index, line) in text.lines().enumerate() {
        if line.contains(&needle) {
            return u32::try_from(index + 1).unwrap_or(1);
        }
    }
    1
}

/// Compiled shell writer detectors reused across every line and artifact.
struct ShellMatcher {
    touch: regex::Regex,
    tee: regex::Regex,
    mv: regex::Regex,
}

impl ShellMatcher {
    fn new() -> Result<Self, LintError> {
        Ok(Self {
            touch: compile(r"(^|[;&|[:space:]])touch\b")?,
            tee: compile(r"(^|[;&|[:space:]])tee\b")?,
            mv: compile(r"(^|[;&|[:space:]])mv\b")?,
        })
    }

    fn writes(&self, line: &str, row: &ManifestRow) -> bool {
        if self.touch.is_match(line) && shell_mentions(line, row) {
            return true;
        }
        if self.tee.is_match(line) && shell_mentions(line, row) {
            return true;
        }
        if self.mv.is_match(line) && mv_target_writes(line, row) {
            return true;
        }
        redirect_writes(line, row)
    }
}

fn compile(pattern: &str) -> Result<regex::Regex, LintError> {
    regex::Regex::new(pattern)
        .map_err(|error| LintError::new(format!("invalid shell pattern {pattern:?}: {error}")))
}

fn mv_target_writes(line: &str, row: &ManifestRow) -> bool {
    let Some((_, tail)) = line.split_once("mv") else {
        return false;
    };
    let targets: Vec<&str> = tail
        .split_whitespace()
        .filter(|token| !token.is_empty() && !token.starts_with('-'))
        .collect();
    targets
        .last()
        .is_some_and(|target| shell_mentions(target, row))
}

fn redirect_writes(line: &str, row: &ManifestRow) -> bool {
    let double = line.rfind(">>");
    let single = line.rfind('>');
    let Some(index) = double.max(single) else {
        return false;
    };
    let width = if line[index..].starts_with(">>") { 2 } else { 1 };
    shell_mentions(&line[index + width..], row)
}

fn shell_mentions(text: &str, row: &ManifestRow) -> bool {
    match row.kind {
        Kind::Basename => boundary_contains(text, &row.artifact),
        Kind::RelativePath => {
            text.contains(&row.artifact) || text.contains(&format!("/{}", row.artifact))
        }
    }
}

crate::register_rule!(METADATA, RULE);

#[cfg(test)]
mod tests {
    use syn::visit::Visit;

    use super::{
        FileScanner, Kind, ManifestRow, ShellMatcher, boundary_contains, mentions, parse_baseline,
        parse_manifest, valid_relative_path,
    };

    fn basename(artifact: &str) -> ManifestRow {
        ManifestRow {
            kind: Kind::Basename,
            artifact: artifact.to_owned(),
        }
    }

    fn relative(artifact: &str) -> ManifestRow {
        ManifestRow {
            kind: Kind::RelativePath,
            artifact: artifact.to_owned(),
        }
    }

    #[test]
    fn basename_boundary_rejects_filename_character_neighbours() {
        assert!(boundary_contains("logs/final-summary.md here", "final-summary.md"));
        assert!(boundary_contains("final-summary.md", "final-summary.md"));
        // A basename must not match when embedded in a longer filename token.
        assert!(!boundary_contains("run-manifest.json", "manifest.json"));
        assert!(!boundary_contains("manifest.jsonl", "manifest.json"));
    }

    #[test]
    fn relative_path_matches_full_path_and_segment_membership() {
        assert!(mentions("wrote .ship-route-exit-handoff.env", &relative(".ship-route-exit-handoff.env")));
        assert!(mentions("dir/.design-step5c-status.env", &relative(".design-step5c-status.env")));
        assert!(!mentions("unrelated text", &relative(".design-step5c-status.env")));
    }

    #[test]
    fn valid_relative_path_rejects_absolute_and_dot_segments() {
        assert!(valid_relative_path("a/b/c.env"));
        assert!(!valid_relative_path("/absolute"));
        assert!(!valid_relative_path("a/../b"));
        assert!(!valid_relative_path("a//b"));
    }

    #[test]
    fn parse_manifest_accepts_valid_rows_and_rejects_malformed() {
        let manifest = parse_manifest(
            "[[artifact]]\nkind = \"basename\"\nname = \"final-summary.md\"\n\
             [[artifact]]\nkind = \"relative_path\"\nname = \"a/b.env\"\n",
        )
        .expect("valid manifest");
        assert_eq!(manifest.len(), 2);
        assert_eq!(manifest[0].kind, Kind::Basename);

        assert!(parse_manifest("[[artifact]]\nkind = \"other\"\nname = \"x\"\n").is_err());
        assert!(parse_manifest("[[artifact]]\nkind = \"basename\"\nname = \"a/b\"\n").is_err());
        assert!(parse_manifest("[[artifact]]\nkind = \"basename\"\nname = \"\"\n").is_err());
        assert!(
            parse_manifest("[[artifact]]\nkind = \"basename\"\nname = \"x\"\nextra = 1\n").is_err()
        );
    }

    #[test]
    fn parse_manifest_rejects_duplicate_identity() {
        let duplicate = "[[artifact]]\nkind = \"basename\"\nname = \"dup.json\"\n\
             [[artifact]]\nkind = \"basename\"\nname = \"dup.json\"\n";
        assert!(parse_manifest(duplicate).is_err());
    }

    #[test]
    fn parse_baseline_validates_side_reason_and_uniqueness() {
        let clean = parse_baseline(
            "[[grandfathered]]\nartifact = \"a.env\"\nside = \"intentionally-one-sided\"\n\
             reason = \"produced outside the scanned surface\"\n",
        )
        .expect("valid baseline");
        assert!(clean.contains("a.env"));

        assert!(parse_baseline("grandfathered = []\n").expect("empty").is_empty());
        assert!(
            parse_baseline(
                "[[grandfathered]]\nartifact = \"a\"\nside = \"bogus\"\nreason = \"r\"\n"
            )
            .is_err()
        );
        assert!(
            parse_baseline(
                "[[grandfathered]]\nartifact = \"a\"\nside = \"external-writer\"\nreason = \" \"\n"
            )
            .is_err()
        );
    }

    #[test]
    fn shell_matcher_detects_touch_tee_mv_and_redirect() {
        let matcher = ShellMatcher::new().expect("shell matcher");
        let row = basename("final-summary.md");
        assert!(matcher.writes("  touch \"$dir/final-summary.md\"", &row));
        assert!(matcher.writes("printf x | tee final-summary.md", &row));
        assert!(matcher.writes("mv -f tmp final-summary.md", &row));
        assert!(matcher.writes("printf x >> final-summary.md", &row));
        assert!(!matcher.writes("cat final-summary.md", &row));
        // mv reports the destination token, not the source.
        assert!(!matcher.writes("mv final-summary.md archived", &row));
    }

    #[test]
    fn file_scanner_detects_writers_and_skips_cfg_test() {
        let source = "fn reads() { let _ = std::fs::read_to_string(\"final-summary.md\"); }\n\
             fn writes() { let _ = std::fs::write(\"token-report.json\", b\"\"); }\n\
             #[cfg(test)]\nmod tests { fn t() { let _ = std::fs::write(\"hidden.json\", b\"\"); } }\n";
        let file = syn::parse_file(source).expect("parse fixture");
        let mut scanner = FileScanner::default();
        scanner.visit_file(&file);

        assert_eq!(scanner.scopes.len(), 2, "cfg(test) scope must be skipped");
        let writer_texts: Vec<&str> = scanner
            .scopes
            .iter()
            .filter(|scope| scope.has_write)
            .map(|scope| scope.text.as_str())
            .collect();
        assert_eq!(writer_texts.len(), 1);
        assert!(mentions(writer_texts[0], &basename("token-report.json")));
        // The read-only scope references the artifact but carries no write.
        assert!(
            scanner
                .scopes
                .iter()
                .any(|scope| !scope.has_write && mentions(&scope.text, &basename("final-summary.md")))
        );
        // The cfg(test) literal never reaches reader evidence.
        assert!(!scanner.scopes.iter().any(|scope| mentions(&scope.text, &basename("hidden.json"))));
    }
}
