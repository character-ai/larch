//! Changed-path Cargo Clippy selection for bounded local Rust checks.
//!
//! Given a set of changed repository-relative paths (explicit, or discovered
//! from Git), this resolves the smallest sound `cargo clippy` invocation: a
//! workspace-wide lint when a shared input changed, otherwise a per-package,
//! per-target selection derived from Cargo metadata. The stdout `RUST_CLIPPY_*`
//! grammar, the selection rules, and the exit codes are byte-compatible with the
//! retired Python owner so `make rust-check`, the pre-commit hook, and the
//! `checks run-relevant` fallback keep the same observable contract.

use std::{
    collections::{BTreeMap, BTreeSet, HashSet},
    ffi::OsString,
    io::Write as _,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process::{Command, ExitCode, ExitStatus},
};

use cargo_metadata::{Metadata, MetadataCommand};
use larch_adapters::{ExactDiffRequest, GitRef, GixRepository};
use larch_core::{Head, ObjectId, ObjectKind, RepositoryRead, Revision, StatusOptions};

use crate::git_command_runtime::GitCommandRuntime;

const CARGO_CLI: &str = "cargo";
const WORKSPACE_INPUTS: &[&str] = &[
    "Cargo.lock",
    "Cargo.toml",
    "deny.toml",
    "rust-toolchain.toml",
];
const TARGET_KINDS: &[&str] = &["bin", "test", "example", "bench"];
const DIFF_CAPTURE_LIMIT: usize = 8 * 1024 * 1024;
const HELP: &str =
    "usage: cli.py checks rust-clippy --repo-root REPO_ROOT [--changed-from-git] [paths ...]";

/// One selection error surfaces as a fail-closed Clippy refusal.
#[derive(Debug)]
struct ClippyError(String);

impl ClippyError {
    fn new(message: impl Into<String>) -> Self {
        Self(message.into())
    }
}

type ClippyResult<T> = Result<T, ClippyError>;

/// One Cargo target with the raw kind strings and its repository-relative source.
struct CargoTarget {
    name: String,
    kinds: Vec<String>,
    source_path: String,
}

impl CargoTarget {
    /// The single selectable kind for this target, or `None` when it is a
    /// library, proc-macro, build script, or otherwise not directly selectable.
    fn selection_kind(&self) -> Option<&str> {
        let mut matches = self
            .kinds
            .iter()
            .filter(|kind| TARGET_KINDS.contains(&kind.as_str()));
        match (matches.next(), matches.next()) {
            (Some(kind), None) => Some(kind.as_str()),
            _ => None,
        }
    }
}

struct CargoPackage {
    package_id: String,
    name: String,
    manifest_path: String,
    root_path: String,
    targets: Vec<CargoTarget>,
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
struct TargetSelection {
    kind: String,
    name: String,
}

#[derive(Debug)]
struct PackageSelection {
    package_name: String,
    defaults: bool,
    targets: Vec<TargetSelection>,
    command: Vec<String>,
}

/// Whether a changed set demands a workspace-wide lint or per-package selection.
#[derive(Debug)]
enum PlanKind {
    Workspace(Vec<String>),
    Packages(Vec<String>),
}

#[derive(Debug)]
struct RustClippyPlan {
    changed_paths: Vec<String>,
    workspace: bool,
    packages: Vec<PackageSelection>,
}

impl RustClippyPlan {
    fn commands(&self) -> Vec<Vec<String>> {
        if self.workspace {
            return vec![vec![
                CARGO_CLI.to_owned(),
                "clippy".to_owned(),
                "--locked".to_owned(),
                "--workspace".to_owned(),
                "--".to_owned(),
                "-D".to_owned(),
                "warnings".to_owned(),
            ]];
        }
        self.packages
            .iter()
            .map(|selection| selection.command.clone())
            .collect()
    }

    fn selected_packages(&self) -> Vec<String> {
        if self.workspace {
            return vec!["workspace".to_owned()];
        }
        self.packages
            .iter()
            .map(|selection| selection.package_name.clone())
            .collect()
    }

    fn selected_targets(&self) -> Vec<String> {
        if self.workspace {
            return vec!["workspace:default-production".to_owned()];
        }
        let mut labels = Vec::new();
        for selection in &self.packages {
            if selection.defaults {
                labels.push(format!("{}:default-production", selection.package_name));
            }
            for target in &selection.targets {
                labels.push(format!(
                    "{}:{}:{}",
                    selection.package_name, target.kind, target.name
                ));
            }
        }
        labels
    }
}

fn has_rs_extension(path: &str) -> bool {
    Path::new(path)
        .extension()
        .is_some_and(|extension| extension == "rs")
}

fn is_rust_relevant_path(path: &str) -> bool {
    WORKSPACE_INPUTS.contains(&path)
        || path.starts_with(".cargo/")
        || (path.starts_with("crates/")
            && (has_rs_extension(path) || path.ends_with("/Cargo.toml")))
}

fn normalize_changed_path(raw: &str) -> ClippyResult<String> {
    if raw.is_empty() || raw.starts_with('/') || raw.contains('\\') {
        return Err(ClippyError::new(format!(
            "changed path must be repository-relative: {raw:?}"
        )));
    }
    if raw.split('/').any(|part| matches!(part, "" | "." | "..")) {
        return Err(ClippyError::new(format!(
            "changed path is not normalized: {raw:?}"
        )));
    }
    Ok(raw.to_owned())
}

fn relative_metadata_path(path: &Path, repo_root: &Path, field: &str) -> ClippyResult<String> {
    let escape = || ClippyError::new(format!("Cargo metadata {field} escapes the repository"));
    let resolved = path.canonicalize().map_err(|_| escape())?;
    let relative = resolved.strip_prefix(repo_root).map_err(|_| escape())?;
    let mut parts = Vec::new();
    for component in relative.components() {
        match component {
            std::path::Component::Normal(value) => {
                parts.push(value.to_str().ok_or_else(escape)?.to_owned());
            }
            _ => return Err(escape()),
        }
    }
    Ok(parts.join("/"))
}

fn posix_parent(path: &str) -> String {
    path.rsplit_once('/')
        .map_or_else(|| ".".to_owned(), |(parent, _)| parent.to_owned())
}

fn posix_stem(path: &str) -> &str {
    let name = path.rsplit_once('/').map_or(path, |(_, name)| name);
    name.rsplit_once('.').map_or(name, |(stem, _)| stem)
}

fn posix_name(path: &str) -> &str {
    path.rsplit_once('/').map_or(path, |(_, name)| name)
}

fn workspace_from_metadata(
    metadata: &Metadata,
    repo_root: &Path,
) -> ClippyResult<Vec<CargoPackage>> {
    let members: HashSet<String> = metadata
        .workspace_members
        .iter()
        .map(|member| member.repr.clone())
        .collect();
    let mut packages = Vec::new();
    for package in &metadata.packages {
        if !members.contains(&package.id.repr) {
            continue;
        }
        let manifest_path = relative_metadata_path(
            package.manifest_path.as_std_path(),
            repo_root,
            "manifest_path",
        )?;
        let root = posix_parent(&manifest_path);
        let root_path = if root == "." { String::new() } else { root };
        let mut targets = Vec::new();
        for target in &package.targets {
            let kinds = target.kind.iter().map(ToString::to_string).collect();
            let source_path = relative_metadata_path(
                target.src_path.as_std_path(),
                repo_root,
                "target src_path",
            )?;
            targets.push(CargoTarget {
                name: target.name.clone(),
                kinds,
                source_path,
            });
        }
        packages.push(CargoPackage {
            package_id: package.id.repr.clone(),
            name: package.name.to_string(),
            manifest_path,
            root_path,
            targets,
        });
    }
    if packages.is_empty() {
        return Err(ClippyError::new(
            "Cargo metadata contains no workspace packages",
        ));
    }
    let unique_names: HashSet<&str> = packages
        .iter()
        .map(|package| package.name.as_str())
        .collect();
    if unique_names.len() != packages.len() {
        return Err(ClippyError::new(
            "Cargo workspace contains duplicate package names",
        ));
    }
    packages.sort_by(|left, right| {
        left.name
            .cmp(&right.name)
            .then_with(|| left.manifest_path.cmp(&right.manifest_path))
    });
    Ok(packages)
}

fn path_in_package(path: &str, package: &CargoPackage) -> bool {
    path == package.manifest_path
        || package.root_path.is_empty()
        || path == package.root_path
        || path.starts_with(&format!("{}/", package.root_path))
}

fn package_for_path<'packages>(
    path: &str,
    packages: &'packages [CargoPackage],
) -> ClippyResult<&'packages CargoPackage> {
    let mut candidates: Vec<&CargoPackage> = packages
        .iter()
        .filter(|package| path_in_package(path, package))
        .collect();
    candidates.sort_by(|left, right| {
        right
            .root_path
            .len()
            .cmp(&left.root_path.len())
            .then_with(|| left.manifest_path.cmp(&right.manifest_path))
    });
    let first = candidates
        .first()
        .ok_or_else(|| ClippyError::new(format!("unmappable Rust path: {path}")))?;
    if candidates.len() > 1 && candidates[0].root_path.len() == candidates[1].root_path.len() {
        return Err(ClippyError::new(format!(
            "ambiguous Cargo package for Rust path: {path}"
        )));
    }
    Ok(first)
}

fn nested_target_match(path: &str, target: &CargoTarget) -> bool {
    let Some(kind) = target.selection_kind() else {
        return false;
    };
    let source = &target.source_path;
    if !has_rs_extension(source) {
        return false;
    }
    if kind == "bin" && !format!("/{source}").contains("/src/bin/") {
        return false;
    }
    let parent = posix_parent(source);
    let target_specific_parent = ["/tests/", "/examples/", "/benches/", "/src/bin/"]
        .iter()
        .any(|marker| format!("/{parent}/").contains(marker));
    let module_dir = if target_specific_parent
        && matches!(posix_name(source), "lib.rs" | "main.rs" | "mod.rs")
    {
        parent
    } else if parent == "." {
        posix_stem(source).to_owned()
    } else {
        format!("{parent}/{}", posix_stem(source))
    };
    path.starts_with(&format!("{module_dir}/"))
}

fn target_for_path(path: &str, package: &CargoPackage) -> ClippyResult<Option<TargetSelection>> {
    if let Some(target) = package
        .targets
        .iter()
        .find(|target| target.source_path == path)
    {
        return Ok(target.selection_kind().map(|kind| TargetSelection {
            kind: kind.to_owned(),
            name: target.name.clone(),
        }));
    }
    let nested: Vec<&CargoTarget> = package
        .targets
        .iter()
        .filter(|target| nested_target_match(path, target))
        .collect();
    if nested.len() > 1 {
        return Err(ClippyError::new(format!(
            "ambiguous Cargo target for Rust path: {path}"
        )));
    }
    if let Some(target) = nested.first() {
        let kind = target
            .selection_kind()
            .expect("a nested target match always has a selection kind");
        return Ok(Some(TargetSelection {
            kind: kind.to_owned(),
            name: target.name.clone(),
        }));
    }
    Ok(None)
}

fn is_default_production_source(path: &str, package: &CargoPackage) -> bool {
    let prefix = package_prefix(package);
    path == format!("{prefix}build.rs") || path.starts_with(&format!("{prefix}src/"))
}

fn package_prefix(package: &CargoPackage) -> String {
    if package.root_path.is_empty() {
        String::new()
    } else {
        format!("{}/", package.root_path)
    }
}

fn shared_target_selections(path: &str, package: &CargoPackage) -> Option<Vec<TargetSelection>> {
    let prefix = package_prefix(package);
    for (directory, kind) in [
        ("tests", "test"),
        ("examples", "example"),
        ("benches", "bench"),
    ] {
        if !path.starts_with(&format!("{prefix}{directory}/")) {
            continue;
        }
        return Some(
            package
                .targets
                .iter()
                .filter(|target| target.selection_kind() == Some(kind))
                .map(|target| TargetSelection {
                    kind: kind.to_owned(),
                    name: target.name.clone(),
                })
                .collect(),
        );
    }
    None
}

/// Returns `None` when the path selects the package's default production
/// targets, or `Some(targets)` for an explicit target selection.
fn path_selection(
    path: &str,
    package: &CargoPackage,
) -> ClippyResult<Option<Vec<TargetSelection>>> {
    if path == package.manifest_path {
        return Ok(None);
    }
    if let Some(target) = target_for_path(path, package)? {
        return Ok(Some(vec![target]));
    }
    if let Some(shared) = shared_target_selections(path, package)
        && !shared.is_empty()
    {
        return Ok(Some(shared));
    }
    if is_default_production_source(path, package) {
        return Ok(None);
    }
    Err(ClippyError::new(format!("unmappable Rust path: {path}")))
}

const fn target_kind_order(kind: &str) -> u8 {
    match kind.as_bytes() {
        b"bin" => 0,
        b"test" => 1,
        b"example" => 2,
        _ => 3,
    }
}

fn default_target_args(package: &CargoPackage) -> Vec<String> {
    let mut args = Vec::new();
    if package
        .targets
        .iter()
        .any(|target| target.kinds.iter().any(|kind| kind == "lib"))
    {
        args.push("--lib".to_owned());
    }
    let mut bins: Vec<&CargoTarget> = package
        .targets
        .iter()
        .filter(|target| target.selection_kind() == Some("bin"))
        .collect();
    bins.sort_by(|left, right| left.name.cmp(&right.name));
    for target in bins {
        args.push("--bin".to_owned());
        args.push(target.name.clone());
    }
    args
}

fn target_flag(kind: &str) -> &'static str {
    match kind {
        "bin" => "--bin",
        "test" => "--test",
        "example" => "--example",
        _ => "--bench",
    }
}

fn package_command(
    package: &CargoPackage,
    defaults: bool,
    targets: &[TargetSelection],
) -> Vec<String> {
    let mut command = vec![
        CARGO_CLI.to_owned(),
        "clippy".to_owned(),
        "--locked".to_owned(),
        "--package".to_owned(),
        package.name.clone(),
    ];
    if defaults && !targets.is_empty() {
        command.extend(default_target_args(package));
    }
    for target in targets {
        command.push(target_flag(&target.kind).to_owned());
        command.push(target.name.clone());
    }
    command.push("--".to_owned());
    command.push("-D".to_owned());
    command.push("warnings".to_owned());
    command
}

fn classify_changed_paths(changed_paths: &[String]) -> ClippyResult<PlanKind> {
    let normalized: BTreeSet<String> = changed_paths
        .iter()
        .map(|path| normalize_changed_path(path))
        .collect::<ClippyResult<_>>()?;
    let normalized: Vec<String> = normalized.into_iter().collect();
    if normalized.is_empty() {
        return Err(ClippyError::new("no changed Rust paths were supplied"));
    }
    if let Some(invalid) = normalized.iter().find(|path| !is_rust_relevant_path(path)) {
        return Err(ClippyError::new(format!(
            "path is not Rust-relevant: {invalid}"
        )));
    }
    if normalized
        .iter()
        .any(|path| WORKSPACE_INPUTS.contains(&path.as_str()) || path.starts_with(".cargo/"))
    {
        return Ok(PlanKind::Workspace(normalized));
    }
    Ok(PlanKind::Packages(normalized))
}

fn plan_from_packages(
    packages: &[CargoPackage],
    normalized: Vec<String>,
) -> ClippyResult<RustClippyPlan> {
    let mut defaults: BTreeSet<String> = BTreeSet::new();
    let mut targets: BTreeMap<String, HashSet<TargetSelection>> = BTreeMap::new();
    for path in &normalized {
        let package = package_for_path(path, packages)?;
        match path_selection(path, package)? {
            None => {
                defaults.insert(package.package_id.clone());
            }
            Some(path_targets) => {
                targets
                    .entry(package.package_id.clone())
                    .or_default()
                    .extend(path_targets);
            }
        }
    }
    let by_id: BTreeMap<&str, &CargoPackage> = packages
        .iter()
        .map(|package| (package.package_id.as_str(), package))
        .collect();
    let mut selected_ids: Vec<String> = defaults
        .iter()
        .chain(targets.keys())
        .cloned()
        .collect::<BTreeSet<String>>()
        .into_iter()
        .collect();
    selected_ids.sort_by(|left, right| {
        by_id[left.as_str()]
            .name
            .cmp(&by_id[right.as_str()].name)
            .then_with(|| left.cmp(right))
    });
    let mut selections = Vec::new();
    for package_id in &selected_ids {
        let package = by_id[package_id.as_str()];
        let mut selected_targets: Vec<TargetSelection> = targets
            .get(package_id)
            .map(|set| set.iter().cloned().collect())
            .unwrap_or_default();
        selected_targets.sort_by(|left, right| {
            target_kind_order(&left.kind)
                .cmp(&target_kind_order(&right.kind))
                .then_with(|| left.name.cmp(&right.name))
        });
        let is_default = defaults.contains(package_id);
        let command = package_command(package, is_default, &selected_targets);
        selections.push(PackageSelection {
            package_name: package.name.clone(),
            defaults: is_default,
            targets: selected_targets,
            command,
        });
    }
    Ok(RustClippyPlan {
        changed_paths: normalized,
        workspace: false,
        packages: selections,
    })
}

fn shlex_join(command: &[String]) -> String {
    command
        .iter()
        .map(|token| shlex_quote(token))
        .collect::<Vec<_>>()
        .join(" ")
}

fn shlex_quote(token: &str) -> String {
    if token.is_empty() {
        return "''".to_owned();
    }
    if token
        .bytes()
        .all(|byte| byte.is_ascii_alphanumeric() || b"@%+=:,./-_".contains(&byte))
    {
        return token.to_owned();
    }
    // Mirror Python `shlex.quote`: wrap in single quotes and encode an embedded
    // quote as '"'"' so RUST_CLIPPY_COMMAND stays byte-identical to the retired
    // owner's `shlex.join` output.
    format!("'{}'", token.replace('\'', "'\"'\"'"))
}

fn bounded_cargo_command(program: &str, repo_root: &Path) -> Command {
    let mut command = Command::new(program); // lint-subprocess-via-runner: ok cargo/clippy is a true external build product whose uncapped streamed output the bounded runner cannot carry, mirroring the retired Python runner
    command
        .current_dir(repo_root)
        .env("CARGO_INCREMENTAL", "0")
        .env("CARGO_PROFILE_DEV_DEBUG", "0")
        .env("CARGO_PROFILE_TEST_DEBUG", "0");
    command
}

fn load_metadata(repo_root: &Path) -> Result<Metadata, ()> {
    MetadataCommand::new()
        .current_dir(repo_root)
        .no_deps()
        .other_options(vec!["--locked".to_owned()])
        .exec()
        .map_err(|_| ())
}

fn run_changed_rust_clippy(repo_root: &Path, changed_paths: &[String]) -> ExitCode {
    // Match the retired Python runner: `cargo metadata` runs before any plan is
    // built, so a stale lockfile fails a workspace lint the same way.
    let Ok(metadata) = load_metadata(repo_root) else {
        eprintln!("RUST_CLIPPY_HOOK_RAN=false REASON=cargo-metadata-failed");
        return ExitCode::from(1);
    };
    let plan = match build_plan(&metadata, repo_root, changed_paths) {
        Ok(plan) => plan,
        Err(error) => {
            eprintln!("ERROR: bounded Rust Clippy selection failed: {}", error.0);
            eprintln!("RUST_CLIPPY_HOOK_RAN=false REASON=selection-failed");
            return ExitCode::from(2);
        }
    };
    println!("RUST_CLIPPY_CHANGED_PATHS={}", plan.changed_paths.join(","));
    println!(
        "RUST_CLIPPY_SELECTED_PACKAGES={}",
        plan.selected_packages().join(",")
    );
    println!(
        "RUST_CLIPPY_SELECTED_TARGETS={}",
        plan.selected_targets().join(",")
    );
    for command in plan.commands() {
        println!("RUST_CLIPPY_COMMAND={}", shlex_join(&command));
        let Ok(output) = bounded_cargo_command(&command[0], repo_root)
            .args(&command[1..])
            .output()
        else {
            eprintln!("RUST_CLIPPY_HOOK_RAN=false REASON=clippy-failed");
            return ExitCode::from(1);
        };
        let _ = std::io::stdout().write_all(&output.stdout);
        let _ = std::io::stderr().write_all(&output.stderr);
        if !output.status.success() {
            eprintln!("RUST_CLIPPY_HOOK_RAN=false REASON=clippy-failed");
            return exit_code_from(output.status);
        }
    }
    println!("RUST_CLIPPY_HOOK_RAN=true");
    ExitCode::SUCCESS
}

fn build_plan(
    metadata: &Metadata,
    repo_root: &Path,
    changed_paths: &[String],
) -> ClippyResult<RustClippyPlan> {
    match classify_changed_paths(changed_paths)? {
        PlanKind::Workspace(normalized) => Ok(RustClippyPlan {
            changed_paths: normalized,
            workspace: true,
            packages: Vec::new(),
        }),
        PlanKind::Packages(normalized) => {
            let packages = workspace_from_metadata(metadata, repo_root)?;
            plan_from_packages(&packages, normalized)
        }
    }
}

fn exit_code_from(status: ExitStatus) -> ExitCode {
    status.code().map_or_else(
        || ExitCode::from(1),
        |code| ExitCode::from(u8::try_from(code).unwrap_or(1)),
    )
}

fn resolve_repo_root(raw: &Path) -> ClippyResult<PathBuf> {
    // Reuse the identity command's non-symlink-dir + Git-toplevel validation so
    // both checks commands accept exactly the same roots.
    crate::checks_identity_commands::validate_repo_root(raw)
        .map_err(|_| ClippyError::new("repository root is not a Git work tree"))
}

fn git_name_only(runtime: &GitCommandRuntime, base: Option<&str>, cached: bool) -> Vec<String> {
    let base = match base {
        Some(reference) => match GitRef::new(reference.to_owned()) {
            Ok(reference) => Some(reference),
            Err(_) => return Vec::new(),
        },
        None => None,
    };
    let head = if base.is_some() {
        match GitRef::new("HEAD") {
            Ok(reference) => Some(reference),
            Err(_) => return Vec::new(),
        }
    } else {
        None
    };
    let result = runtime.runtime.block_on(runtime.git_cli().exact_diff(
        ExactDiffRequest {
            cached,
            binary: false,
            no_ext_diff: false,
            unified_context: None,
            name_only: true,
            name_status: false,
            quiet: false,
            exit_code: false,
            base,
            head,
            paths: Vec::new(),
        },
        &runtime.cancellation,
    ));
    match result {
        Ok(result) if !result.truncated() => String::from_utf8_lossy(result.output().stdout())
            .lines()
            .map(str::trim)
            .filter(|line| !line.is_empty())
            .map(ToOwned::to_owned)
            .collect(),
        _ => Vec::new(),
    }
}

fn branch_merge_base(repository: &GixRepository) -> Option<ObjectId> {
    let head = match repository.head().ok()? {
        Head::Detached { target } | Head::Symbolic { target, .. } => target,
        Head::Unborn { .. } => return None,
    };
    for candidate in ["origin/main", "main"] {
        if let Ok(reference) =
            repository.resolve_revision(&Revision::new(candidate.as_bytes().to_vec()))
            && matches!(repository.object(&reference), Ok(Some(object)) if object.kind == ObjectKind::Commit)
            && let Ok(base) = repository.merge_base(&reference, &head)
        {
            return Some(base);
        }
    }
    None
}

fn changed_paths_from_git(repo_root: &Path) -> ClippyResult<Vec<String>> {
    let repository = GixRepository::discover(repo_root)
        .map_err(|_| ClippyError::new("repository root is not a Git work tree"))?;
    let mut runtime = GitCommandRuntime::for_repository(repo_root)
        .map_err(|_| ClippyError::new("repository root is not a Git work tree"))?;
    runtime.policy = runtime.policy.clone().with_output_limit(
        NonZeroUsize::new(DIFF_CAPTURE_LIMIT).expect("non-zero diff capture limit"),
    );
    let mut changed: BTreeSet<String> = BTreeSet::new();
    if let Some(base) = branch_merge_base(&repository) {
        changed.extend(git_name_only(&runtime, Some(&base.to_hex()), false));
    }
    changed.extend(git_name_only(&runtime, None, true));
    changed.extend(git_name_only(&runtime, None, false));
    if let Ok(status) = repository.local_status(&StatusOptions {
        include_untracked: true,
        ..StatusOptions::default()
    }) {
        for path in &status.untracked {
            changed.insert(String::from_utf8_lossy(path.as_bytes()).into_owned());
        }
    }
    Ok(changed.into_iter().collect())
}

/// `checks rust-clippy` compatibility command.
pub fn rust_clippy(arguments: &[OsString]) -> ExitCode {
    let mut repo_root: Option<String> = None;
    let mut changed_from_git = false;
    let mut paths: Vec<String> = Vec::new();
    let mut index = 0;
    while index < arguments.len() {
        let argument = arguments[index].to_string_lossy();
        match argument.as_ref() {
            "-h" | "--help" => {
                println!("{HELP}");
                return ExitCode::SUCCESS;
            }
            "--changed-from-git" => changed_from_git = true,
            "--repo-root" => {
                index += 1;
                let Some(value) = arguments.get(index) else {
                    eprintln!("checks rust-clippy: --repo-root requires a value");
                    return ExitCode::from(2);
                };
                repo_root = Some(value.to_string_lossy().into_owned());
            }
            other if other.starts_with("--repo-root=") => {
                repo_root = Some(other["--repo-root=".len()..].to_owned());
            }
            other => paths.push(other.to_owned()),
        }
        index += 1;
    }
    let Some(repo_root) = repo_root else {
        eprintln!("checks rust-clippy: --repo-root is required");
        return ExitCode::from(2);
    };
    if changed_from_git && !paths.is_empty() {
        eprintln!("checks rust-clippy: --changed-from-git cannot be combined with explicit paths");
        return ExitCode::from(2);
    }
    if !changed_from_git && paths.is_empty() {
        eprintln!("checks rust-clippy: supply changed Rust paths or --changed-from-git");
        return ExitCode::from(2);
    }
    let repo_root = match resolve_repo_root(Path::new(&repo_root)) {
        Ok(root) => root,
        Err(error) => {
            eprintln!("ERROR: bounded Rust Clippy selection failed: {}", error.0);
            return ExitCode::from(2);
        }
    };
    let raw_paths = if changed_from_git {
        match changed_paths_from_git(&repo_root) {
            Ok(discovered) => discovered,
            Err(error) => {
                eprintln!("ERROR: bounded Rust Clippy selection failed: {}", error.0);
                return ExitCode::from(2);
            }
        }
    } else {
        paths
    };
    let rust_paths: Vec<String> = raw_paths
        .into_iter()
        .filter(|path| is_rust_relevant_path(path))
        .collect();
    if changed_from_git && rust_paths.is_empty() {
        println!("RUST_CLIPPY_HOOK_RAN=false REASON=no-rust-changes");
        return ExitCode::SUCCESS;
    }
    run_changed_rust_clippy(&repo_root, &rust_paths)
}

#[cfg(test)]
mod tests {
    use super::{
        CargoPackage, CargoTarget, PackageSelection, PlanKind, RustClippyPlan,
        classify_changed_paths, is_rust_relevant_path, normalize_changed_path, package_command,
        plan_from_packages, shlex_join,
    };

    fn target(name: &str, kinds: &[&str], source: &str) -> CargoTarget {
        CargoTarget {
            name: name.to_owned(),
            kinds: kinds.iter().map(|kind| (*kind).to_owned()).collect(),
            source_path: source.to_owned(),
        }
    }

    fn cli_package() -> CargoPackage {
        CargoPackage {
            package_id: "path+file:///repo/crates/larch-cli#larch-cli@0.1.0".to_owned(),
            name: "larch-cli".to_owned(),
            manifest_path: "crates/larch-cli/Cargo.toml".to_owned(),
            root_path: "crates/larch-cli".to_owned(),
            targets: vec![
                target("larch-cli", &["lib"], "crates/larch-cli/src/lib.rs"),
                target("larch", &["bin"], "crates/larch-cli/src/main.rs"),
                target("parity", &["test"], "crates/larch-cli/tests/parity.rs"),
            ],
        }
    }

    fn plan_over(packages: &[CargoPackage], paths: &[&str]) -> RustClippyPlan {
        let normalized = match classify_changed_paths(
            &paths
                .iter()
                .map(|path| (*path).to_owned())
                .collect::<Vec<_>>(),
        )
        .expect("classification")
        {
            PlanKind::Packages(normalized) => normalized,
            PlanKind::Workspace(_) => panic!("expected a per-package selection"),
        };
        plan_from_packages(packages, normalized).expect("plan")
    }

    #[test]
    fn relevance_matches_the_python_predicate() {
        assert!(is_rust_relevant_path("Cargo.lock"));
        assert!(is_rust_relevant_path(".cargo/config.toml"));
        assert!(is_rust_relevant_path("crates/larch-cli/src/main.rs"));
        assert!(is_rust_relevant_path("crates/larch-cli/Cargo.toml"));
        assert!(!is_rust_relevant_path("python/cli.py"));
        assert!(!is_rust_relevant_path("crates/larch-cli/README.md"));
    }

    #[test]
    fn normalization_rejects_escaping_paths() {
        assert!(normalize_changed_path("/abs/path").is_err());
        assert!(normalize_changed_path("crates/../secret").is_err());
        assert!(normalize_changed_path("crates/larch-cli/src/main.rs").is_ok());
    }

    #[test]
    fn workspace_input_forces_a_workspace_lint() {
        match classify_changed_paths(&["Cargo.lock".to_owned()]).expect("classification") {
            PlanKind::Workspace(normalized) => assert_eq!(normalized, vec!["Cargo.lock"]),
            PlanKind::Packages(_) => panic!("Cargo.lock must force a workspace lint"),
        }
        let plan = RustClippyPlan {
            changed_paths: vec!["Cargo.lock".to_owned()],
            workspace: true,
            packages: Vec::new(),
        };
        assert_eq!(plan.selected_packages(), vec!["workspace"]);
        assert_eq!(
            plan.commands(),
            vec![vec![
                "cargo".to_owned(),
                "clippy".to_owned(),
                "--locked".to_owned(),
                "--workspace".to_owned(),
                "--".to_owned(),
                "-D".to_owned(),
                "warnings".to_owned(),
            ]]
        );
    }

    #[test]
    fn library_source_selects_package_defaults() {
        let plan = plan_over(&[cli_package()], &["crates/larch-cli/src/lib.rs"]);
        assert!(!plan.workspace);
        assert_eq!(
            plan.selected_targets(),
            vec!["larch-cli:default-production"]
        );
        assert_eq!(
            plan.commands(),
            vec![vec![
                "cargo",
                "clippy",
                "--locked",
                "--package",
                "larch-cli",
                "--",
                "-D",
                "warnings",
            ]]
        );
    }

    #[test]
    fn test_source_selects_that_test_target() {
        let plan = plan_over(&[cli_package()], &["crates/larch-cli/tests/parity.rs"]);
        assert_eq!(plan.selected_targets(), vec!["larch-cli:test:parity"]);
        assert_eq!(
            plan.commands(),
            vec![vec![
                "cargo",
                "clippy",
                "--locked",
                "--package",
                "larch-cli",
                "--test",
                "parity",
                "--",
                "-D",
                "warnings",
            ]]
        );
    }

    #[test]
    fn default_source_plus_test_expands_default_targets() {
        let plan = plan_over(
            &[cli_package()],
            &[
                "crates/larch-cli/src/lib.rs",
                "crates/larch-cli/tests/parity.rs",
            ],
        );
        let selection: &PackageSelection = &plan.packages[0];
        assert!(selection.defaults);
        assert_eq!(
            package_command(&cli_package(), selection.defaults, &selection.targets),
            vec![
                "cargo",
                "clippy",
                "--locked",
                "--package",
                "larch-cli",
                "--lib",
                "--bin",
                "larch",
                "--test",
                "parity",
                "--",
                "-D",
                "warnings",
            ]
        );
        assert_eq!(
            plan.selected_targets(),
            vec!["larch-cli:default-production", "larch-cli:test:parity"]
        );
    }

    #[test]
    fn nested_module_under_a_binary_selects_the_binary_target() {
        let mut package = cli_package();
        package.targets.push(target(
            "helper",
            &["bin"],
            "crates/larch-cli/src/bin/helper.rs",
        ));
        let plan = plan_over(&[package], &["crates/larch-cli/src/bin/helper/mod.rs"]);
        assert_eq!(plan.selected_targets(), vec!["larch-cli:bin:helper"]);
    }

    #[test]
    fn shlex_join_quotes_only_unsafe_tokens() {
        assert_eq!(
            shlex_join(&["cargo".to_owned(), "clippy".to_owned()]),
            "cargo clippy"
        );
        assert_eq!(
            shlex_join(&["a b".to_owned(), "plain".to_owned()]),
            "'a b' plain"
        );
        // Mirror Python shlex.quote for an embedded single quote.
        assert_eq!(super::shlex_quote("a'b"), "'a'\"'\"'b'");
    }

    #[test]
    fn ambiguous_and_unmappable_paths_are_rejected() {
        let package = cli_package();
        let Err(error) = classify_changed_paths(&["crates/larch-cli/README.md".to_owned()]) else {
            panic!("non-Rust path must not classify");
        };
        assert!(error.0.contains("not Rust-relevant"));
        let err = plan_from_packages(&[package], vec!["crates/larch-cli/docs/x.rs".to_owned()])
            .expect_err("unmappable");
        assert!(err.0.contains("unmappable Rust path"));
    }

    // ---- Real-fixture coverage over Git discovery and Cargo metadata ----

    use std::{fs, path::Path, path::PathBuf, process::Command};

    fn git(root: &Path, args: &[&str]) {
        let status = Command::new("git") // lint-subprocess-via-runner: ok test-only Git fixture
            .arg("-C")
            .arg(root)
            .args(args)
            .status()
            .expect("run git fixture");
        assert!(status.success(), "git {args:?} failed");
    }

    fn write(root: &Path, rel: &str, body: &str) {
        let path = root.join(rel);
        fs::create_dir_all(path.parent().expect("parent")).expect("dir");
        fs::write(path, body).expect("file");
    }

    fn init_repo() -> tempfile::TempDir {
        let dir = tempfile::tempdir().expect("repo");
        git(dir.path(), &["init", "--quiet"]);
        git(dir.path(), &["config", "user.email", "t@example.invalid"]);
        git(dir.path(), &["config", "user.name", "T"]);
        dir
    }

    #[test]
    fn git_discovery_collects_branch_index_worktree_and_untracked() {
        let repo = init_repo();
        let root = repo.path();
        write(root, "crates/demo/src/lib.rs", "pub fn a() {}\n");
        git(root, &["add", "--all"]);
        git(root, &["commit", "--quiet", "-m", "base"]);
        // A trusted-main ref plus a branch commit above it.
        git(root, &["update-ref", "refs/remotes/origin/main", "HEAD"]);
        write(root, "crates/demo/src/branch.rs", "pub fn b() {}\n");
        git(root, &["add", "--all"]);
        git(root, &["commit", "--quiet", "-m", "branch"]);
        // Staged, unstaged, and untracked changes.
        write(root, "crates/demo/src/staged.rs", "pub fn s() {}\n");
        git(root, &["add", "crates/demo/src/staged.rs"]);
        write(root, "crates/demo/src/lib.rs", "pub fn a() -> u8 { 1 }\n");
        write(root, "crates/demo/src/untracked.rs", "pub fn u() {}\n");

        let resolved = super::resolve_repo_root(root).expect("resolve repo root");
        assert_eq!(resolved, root.canonicalize().expect("canonical"));

        let changed = super::changed_paths_from_git(&resolved).expect("changed set");
        for expected in [
            "crates/demo/src/branch.rs",
            "crates/demo/src/staged.rs",
            "crates/demo/src/lib.rs",
            "crates/demo/src/untracked.rs",
        ] {
            assert!(
                changed.contains(&expected.to_owned()),
                "missing {expected}: {changed:?}"
            );
        }
    }

    #[test]
    fn resolve_repo_root_rejects_a_non_repository() {
        let dir = tempfile::tempdir().expect("dir");
        assert!(super::resolve_repo_root(dir.path()).is_err());
    }

    #[test]
    fn cli_entry_covers_argument_and_short_circuit_paths() {
        // Argument-shape refusals do not touch Git or Cargo.
        let _ = super::rust_clippy(&["--help".into()]);
        let _ = super::rust_clippy(&[]);
        let _ = super::rust_clippy(&["--changed-from-git".into()]);
        let _ = super::rust_clippy(&[
            "--repo-root".into(),
            "/tmp".into(),
            "--changed-from-git".into(),
            "crates/x/src/lib.rs".into(),
        ]);
        let _ = super::rust_clippy(&["--repo-root".into()]);
        let _ = super::rust_clippy(&["--repo-root=/nonexistent-clippy-root".into(), "a.rs".into()]);

        // A changed-from-git run with only non-Rust changes short-circuits to 0.
        let repo = init_repo();
        write(repo.path(), "docs/readme.md", "# doc\n");
        git(repo.path(), &["add", "--all"]);
        git(repo.path(), &["commit", "--quiet", "-m", "base"]);
        write(repo.path(), "docs/other.md", "# other\n");
        let root = repo.path().to_string_lossy().into_owned();
        let _ = super::rust_clippy(&[
            "--repo-root".into(),
            root.into(),
            "--changed-from-git".into(),
        ]);
    }

    fn demo_workspace() -> (tempfile::TempDir, PathBuf) {
        let dir = tempfile::tempdir().expect("workspace");
        let root = dir.path();
        write(
            root,
            "Cargo.toml",
            "[workspace]\nmembers = [\"crates/demo\"]\nresolver = \"2\"\n",
        );
        write(
            root,
            "crates/demo/Cargo.toml",
            "[package]\nname = \"demo\"\nversion = \"0.1.0\"\nedition = \"2021\"\n",
        );
        write(root, "crates/demo/src/lib.rs", "pub fn f() -> u8 { 1 }\n");
        write(root, "crates/demo/src/main.rs", "fn main() {}\n");
        write(root, "crates/demo/src/bin/extra.rs", "fn main() {}\n");
        write(root, "crates/demo/tests/it.rs", "#[test]\nfn t() {}\n");
        write(root, "crates/demo/examples/ex.rs", "fn main() {}\n");
        write(root, "crates/demo/benches/bench.rs", "fn main() {}\n");
        write(root, "crates/demo/build.rs", "fn main() {}\n");
        let canonical = root.canonicalize().expect("canonical workspace");
        (dir, canonical)
    }

    fn metadata(root: &Path) -> cargo_metadata::Metadata {
        cargo_metadata::MetadataCommand::new()
            .current_dir(root)
            .no_deps()
            .exec()
            .expect("cargo metadata")
    }

    #[test]
    fn selection_over_real_cargo_metadata() {
        let (_dir, root) = demo_workspace();
        let meta = metadata(&root);

        let lib =
            super::build_plan(&meta, &root, &["crates/demo/src/lib.rs".to_owned()]).expect("lib");
        assert_eq!(
            lib.commands(),
            vec![vec![
                "cargo",
                "clippy",
                "--locked",
                "--package",
                "demo",
                "--",
                "-D",
                "warnings"
            ]]
        );

        let test =
            super::build_plan(&meta, &root, &["crates/demo/tests/it.rs".to_owned()]).expect("test");
        assert_eq!(test.selected_targets(), vec!["demo:test:it"]);

        let example = super::build_plan(&meta, &root, &["crates/demo/examples/ex.rs".to_owned()])
            .expect("ex");
        assert_eq!(example.selected_targets(), vec!["demo:example:ex"]);

        let bench = super::build_plan(&meta, &root, &["crates/demo/benches/bench.rs".to_owned()])
            .expect("bench");
        assert_eq!(bench.selected_targets(), vec!["demo:bench:bench"]);

        let extra = super::build_plan(&meta, &root, &["crates/demo/src/bin/extra.rs".to_owned()])
            .expect("bin");
        assert_eq!(extra.selected_targets(), vec!["demo:bin:extra"]);

        let build_script =
            super::build_plan(&meta, &root, &["crates/demo/build.rs".to_owned()]).expect("build");
        assert_eq!(
            build_script.selected_targets(),
            vec!["demo:default-production"]
        );

        let mixed = super::build_plan(
            &meta,
            &root,
            &[
                "crates/demo/src/lib.rs".to_owned(),
                "crates/demo/tests/it.rs".to_owned(),
            ],
        )
        .expect("mixed");
        assert_eq!(
            mixed.commands(),
            vec![vec![
                "cargo",
                "clippy",
                "--locked",
                "--package",
                "demo",
                "--lib",
                "--bin",
                "demo",
                "--bin",
                "extra",
                "--test",
                "it",
                "--",
                "-D",
                "warnings",
            ]]
        );

        // A workspace input short-circuits before metadata is consulted.
        let workspace =
            super::build_plan(&meta, &root, &["Cargo.toml".to_owned()]).expect("workspace");
        assert!(workspace.workspace);
    }

    #[test]
    fn run_reports_a_metadata_failure_outside_a_cargo_workspace() {
        let dir = tempfile::tempdir().expect("dir");
        // No Cargo.toml, so `cargo metadata` fails and the runner reports it.
        let _ = super::run_changed_rust_clippy(dir.path(), &["crates/x/src/lib.rs".to_owned()]);
    }

    #[test]
    fn cargo_configuration_inputs_force_a_workspace_lint() {
        for input in [".cargo/config.toml", "deny.toml", "rust-toolchain.toml"] {
            match classify_changed_paths(&[input.to_owned()]).expect("classify") {
                PlanKind::Workspace(_) => {}
                PlanKind::Packages(_) => panic!("{input} must force a workspace lint"),
            }
        }
        assert!(
            classify_changed_paths(&[])
                .expect_err("empty")
                .0
                .contains("no changed Rust paths")
        );
    }

    #[test]
    fn manifest_and_shared_target_directories_select_correctly() {
        let package = CargoPackage {
            package_id: "id".to_owned(),
            name: "demo".to_owned(),
            manifest_path: "crates/demo/Cargo.toml".to_owned(),
            root_path: "crates/demo".to_owned(),
            targets: vec![
                target("demo", &["lib"], "crates/demo/src/lib.rs"),
                target("first", &["example"], "crates/demo/examples/first.rs"),
                target("second", &["example"], "crates/demo/examples/second.rs"),
                target("bench", &["bench"], "crates/demo/benches/bench.rs"),
            ],
        };
        // A package manifest edit selects the package defaults.
        let manifest = plan_over(std::slice::from_ref(&package), &["crates/demo/Cargo.toml"]);
        assert_eq!(manifest.selected_targets(), vec!["demo:default-production"]);

        // A file under examples/ that is not itself a target source selects every
        // example target in the family.
        let shared = plan_over(
            std::slice::from_ref(&package),
            &["crates/demo/examples/shared/util.rs"],
        );
        assert_eq!(
            shared.selected_targets(),
            vec!["demo:example:first", "demo:example:second"]
        );

        // A file under benches/ selects the bench family.
        let bench = plan_over(
            std::slice::from_ref(&package),
            &["crates/demo/benches/extra/data.rs"],
        );
        assert_eq!(bench.selected_targets(), vec!["demo:bench:bench"]);
    }

    #[test]
    fn ambiguous_package_and_target_ownership_is_refused() {
        // Two packages rooted at the same directory make ownership ambiguous.
        let a = CargoPackage {
            package_id: "a".to_owned(),
            name: "a".to_owned(),
            manifest_path: "crates/shared/a/Cargo.toml".to_owned(),
            root_path: "crates/shared".to_owned(),
            targets: vec![target("a", &["lib"], "crates/shared/src/lib.rs")],
        };
        let b = CargoPackage {
            package_id: "b".to_owned(),
            name: "b".to_owned(),
            manifest_path: "crates/shared/b/Cargo.toml".to_owned(),
            root_path: "crates/shared".to_owned(),
            targets: vec![target("b", &["lib"], "crates/shared/src/other.rs")],
        };
        let err = plan_from_packages(&[a, b], vec!["crates/shared/src/lib.rs".to_owned()])
            .expect_err("ambiguous package");
        assert!(err.0.contains("ambiguous Cargo package"), "{}", err.0);

        // Two nested targets both claiming the same nested path are ambiguous.
        let package = CargoPackage {
            package_id: "id".to_owned(),
            name: "demo".to_owned(),
            manifest_path: "crates/demo/Cargo.toml".to_owned(),
            root_path: "crates/demo".to_owned(),
            targets: vec![
                target("one", &["test"], "crates/demo/tests/shared.rs"),
                target("two", &["test"], "crates/demo/tests/shared/mod.rs"),
            ],
        };
        let err = plan_from_packages(
            &[package],
            vec!["crates/demo/tests/shared/deep.rs".to_owned()],
        )
        .expect_err("ambiguous target");
        assert!(err.0.contains("ambiguous Cargo target"), "{}", err.0);
    }
}
