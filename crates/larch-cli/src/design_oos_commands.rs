//! Rust owner for `design file-oos-prepare` and `design file-oos-annotate` (#8590).

use std::{
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    PathIntent, TemporaryRoot, atomic_write_utf8_in, ensure_directory_chain,
    github::LiveMutationRequest, remove_optional_file,
};
use larch_core::{
    BlockBoundary, FILE_CONFLICT_DEFAULT_CLUSTER_CAP, FILE_CONFLICT_DEFAULT_GLOBAL_CAP,
    OosItemKind, apply_issue_cap, count_non_security_blocks, design_oos_annotate,
    design_oos_has_filed_urls, design_oos_has_priority, design_oos_identity_signature,
    design_oos_priority_map, design_oos_promote_pool, design_oos_recover_accepted,
    design_oos_unfiled, parse_design_oos_issue_output, parse_issue_input, parse_oos_blocks,
    plan_file_conflict_deps, render_deps_tsv,
};

use crate::{
    argparse_compat::parse_with_flags,
    issue_mutation_support::{authorization_request, authorized},
    launcher_support::read_optional_confined_checked,
    oos_commands::{conflict_cap, issue_cap_value},
    oos_file_commands::{apply_priority_label, ensure_priority_label},
    run_log_entry_commands::append_execution_issue_filtered,
};

const ISSUE_STDOUT_FILE: &str = "oos-issue.stdout.txt";
const AGGREGATE_POOL_FILE: &str = "oos-aggregate-pool.md";
const ACCEPTED_FILE: &str = "oos-accepted-design.md";
const COMBINED_FILE: &str = "oos-combined.md";
const DEPS_FILE: &str = "oos-intra-batch-deps.tsv";
const ORDER_FILE: &str = "oos-design-filing-order.txt";
const SENTINEL_FILE: &str = "oos-issues-created.md";
const PRIORITY_PENDING: &str = ".oos-priority-label-pending";
const PREPARE_USAGE: &str = concat!(
    "usage: design file-oos-prepare [--design-tmpdir DESIGN_TMPDIR]\n",
    "                               [--issue-number ISSUE_NUMBER] [--repo REPO]\n",
    "                               [--clear-cross-session-cache]",
);
const ANNOTATE_USAGE: &str = concat!(
    "usage: design file-oos-annotate [--design-tmpdir DESIGN_TMPDIR]\n",
    "                                [--issue-stdout-file ISSUE_STDOUT_FILE]\n",
    "                                [--issue-number ISSUE_NUMBER] [--repo REPO]\n",
    "                                [--context-file CONTEXT_FILE] [--run-id RUN_ID]\n",
    "                                [--trusted-root TRUSTED_ROOT] [--operator-invoked]\n",
    "                                [--label-only]",
);

#[derive(Clone, Debug, Default)]
struct Arguments {
    design_tmpdir: String,
    issue_number: String,
    issue_stdout_file: String,
    repo: String,
    context_file: String,
    run_id: String,
    trusted_root: String,
    operator_invoked: bool,
    label_only: bool,
    clear_cache: bool,
}

trait PriorityEffects {
    fn ensure(&self, repo: &str) -> Result<(), String>;
    fn apply(
        &self,
        repo: &str,
        url: &str,
        authorization: &LiveMutationRequest<'_>,
    ) -> Result<(), String>;
}

struct LivePriorityEffects;

impl PriorityEffects for LivePriorityEffects {
    fn ensure(&self, repo: &str) -> Result<(), String> {
        ensure_priority_label(repo)
    }

    fn apply(
        &self,
        repo: &str,
        url: &str,
        authorization: &LiveMutationRequest<'_>,
    ) -> Result<(), String> {
        apply_priority_label(repo, url, authorization)
    }
}

/// Entry point for `larch design file-oos-prepare`.
#[must_use]
pub fn file_oos_prepare_main(arguments: &[OsString]) -> ExitCode {
    ExitCode::from(prepare(arguments))
}

/// Entry point for `larch design file-oos-annotate`.
#[must_use]
pub fn file_oos_annotate_main(arguments: &[OsString]) -> ExitCode {
    ExitCode::from(annotate(arguments, &LivePriorityEffects))
}

fn parse_arguments(arguments: &[OsString], annotate: bool) -> Result<Arguments, ()> {
    let values = if annotate {
        &[
            "--context-file",
            "--design-tmpdir",
            "--issue-number",
            "--issue-stdout-file",
            "--repo",
            "--run-id",
            "--trusted-root",
        ][..]
    } else {
        &["--design-tmpdir", "--issue-number", "--repo"][..]
    };
    let flags = if annotate {
        &["--label-only", "--operator-invoked"][..]
    } else {
        &["--clear-cross-session-cache"][..]
    };
    let parsed = parse_with_flags(arguments, values, flags, 0);
    if let Some(error) = parsed.error() {
        usage_error(annotate, &error);
        return Err(());
    }
    let value = |name: &str| {
        parsed
            .value(name)
            .map_or_else(String::new, |item| item.to_string_lossy().into_owned())
    };
    Ok(Arguments {
        design_tmpdir: value("--design-tmpdir"),
        issue_number: value("--issue-number"),
        issue_stdout_file: value("--issue-stdout-file"),
        repo: value("--repo"),
        context_file: value("--context-file"),
        run_id: value("--run-id"),
        trusted_root: value("--trusted-root"),
        operator_invoked: parsed.flag("--operator-invoked"),
        label_only: parsed.flag("--label-only"),
        clear_cache: parsed.flag("--clear-cross-session-cache"),
    })
}

fn usage_error(annotate: bool, detail: &str) {
    let (usage, program) = if annotate {
        (ANNOTATE_USAGE, "design file-oos-annotate")
    } else {
        (PREPARE_USAGE, "design file-oos-prepare")
    };
    eprintln!("{usage}\n{program}: error: {detail}");
}

fn design_root(parsed: &mut Arguments, annotate: bool) -> Result<TemporaryRoot, u8> {
    if parsed.design_tmpdir.is_empty() {
        parsed.design_tmpdir = env::var("DESIGN_TMPDIR").unwrap_or_default();
    }
    let program = if annotate {
        "design file-oos-annotate"
    } else {
        "design file-oos-prepare"
    };
    if parsed.design_tmpdir.is_empty() {
        eprintln!("{program}: DESIGN_TMPDIR unset");
        return Err(2);
    }
    let path = PathBuf::from(&parsed.design_tmpdir);
    let absolute = if path.is_absolute() {
        path
    } else {
        env::current_dir().map_or_else(|_| path.clone(), |cwd| cwd.join(&path))
    };
    let Ok(root) = TemporaryRoot::resolve(Some(&absolute)) else {
        eprintln!("{program}: DESIGN_TMPDIR not a directory");
        return Err(2);
    };
    parsed.design_tmpdir = root.path().to_string_lossy().into_owned();
    Ok(root)
}

fn read_lossy(root: &TemporaryRoot, path: &Path) -> Result<Option<String>, String> {
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(error.to_string()),
        Ok(metadata) if !metadata.is_file() || metadata.file_type().is_symlink() => {
            Err(format!("refusing non-regular file: {}", path.display()))
        }
        Ok(_) => {
            root.confine(path, PathIntent::Read)
                .map_err(|error| error.to_string())?;
            read_optional_confined_checked(path).map(Some)
        }
    }
}

fn read_or_empty(root: &TemporaryRoot, path: &Path) -> Result<String, String> {
    read_lossy(root, path).map(Option::unwrap_or_default)
}

fn command_read(root: &TemporaryRoot, path: &Path, program: &str) -> Result<String, u8> {
    read_or_empty(root, path).map_err(|error| {
        eprintln!("{program}: {error}");
        2
    })
}

fn write_text(root: &TemporaryRoot, path: &Path, text: &str) -> Result<(), String> {
    atomic_write_utf8_in(root, path, text, true, 0o644).map_err(|error| error.to_string())
}

fn remove(root: &TemporaryRoot, path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error.to_string()),
        Ok(_) => {
            root.confine(path, PathIntent::Cleanup)
                .map_err(|error| error.to_string())?;
            remove_optional_file(path).map_err(|error| error.to_string())
        }
    }
}

fn issue_number(explicit: &str) -> String {
    let value = if explicit.is_empty() {
        env::var("ISSUE_NUMBER").unwrap_or_default()
    } else {
        explicit.to_owned()
    };
    let trimmed = value.trim();
    if !trimmed.is_empty() && trimmed.chars().all(|value| value.is_ascii_digit()) {
        trimmed.to_owned()
    } else {
        String::new()
    }
}

fn cache_directory(issue: &str, create: bool) -> Option<TemporaryRoot> {
    if issue.is_empty() {
        return None;
    }
    let directory = PathBuf::from(env::var_os("HOME")?).join(".cache/larch/design-oos-filed");
    if create && ensure_directory_chain(&directory).is_err() {
        return None;
    }
    TemporaryRoot::resolve(Some(&directory)).ok()
}

fn cache_path(root: &TemporaryRoot, issue: &str, suffix: &str) -> PathBuf {
    if suffix.is_empty() {
        root.path().join(format!("{issue}.md"))
    } else {
        root.path().join(format!("{issue}.{suffix}"))
    }
}

fn file_nonempty(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|metadata| metadata.is_file() && metadata.len() > 0)
}

fn kv_last(text: &str, key: &str) -> String {
    text.lines()
        .filter_map(|line| {
            line.strip_prefix(key)
                .and_then(|rest| rest.strip_prefix('='))
        })
        .next_back()
        .unwrap_or_default()
        .trim()
        .trim_matches(['\'', '"'])
        .to_owned()
}

fn read_key(root: &TemporaryRoot, path: &Path, key: &str) -> String {
    read_lossy(root, path)
        .ok()
        .flatten()
        .map_or_else(String::new, |text| kv_last(&text, key))
}

fn append_warning(root: &TemporaryRoot, site: &str, tool: &str, detail: &str) {
    let entry = format!(
        "- **Step {site}: {tool} failed (exit 1)**:\n  ```\n{}\n  ```\n",
        detail.trim_end()
    );
    let _result = append_execution_issue_filtered(
        &root.path().join("execution-issues.md"),
        "Warnings",
        &entry,
        None,
        true,
        true,
    );
}

fn copy_between(
    source_root: &TemporaryRoot,
    source: &Path,
    target_root: &TemporaryRoot,
    target: &Path,
) -> Result<(), String> {
    let text = read_lossy(source_root, source)?.ok_or_else(|| source.display().to_string())?;
    write_text(target_root, target, &text)
}

fn clear_cache(issue: &str) {
    let Some(cache) = cache_directory(issue, false) else {
        return;
    };
    for suffix in [
        "",
        "priority-pending",
        "combined.md",
        "filing-order.txt",
        "accepted-design.md",
    ] {
        let _removed = remove(&cache, &cache_path(&cache, issue, suffix));
    }
}

fn pending(design: &TemporaryRoot, issue: &str) -> bool {
    if design.path().join(PRIORITY_PENDING).is_file() {
        return true;
    }
    if let Some(cache) = cache_directory(issue, false)
        && cache_path(&cache, issue, "priority-pending").is_file()
    {
        return true;
    }
    ["oos-filing-prepare.env", "oos-filing-annotate.stdout.txt"]
        .iter()
        .any(|name| {
            read_key(design, &design.path().join(name), "FILE_DESIGN_OOS_STATUS")
                == "annotate-label-failed"
        })
}

fn restore_retry_sidecars(design: &TemporaryRoot, issue: &str) -> bool {
    let Some(cache) = cache_directory(issue, false) else {
        return false;
    };
    let sentinel = cache_path(&cache, issue, "");
    if !cache_path(&cache, issue, "priority-pending").is_file() || !sentinel.is_file() {
        return false;
    }
    let result = copy_between(
        &cache,
        &sentinel,
        design,
        &design.path().join(SENTINEL_FILE),
    )
    .and_then(|()| {
        for (suffix, name) in [
            ("combined.md", COMBINED_FILE),
            ("filing-order.txt", ORDER_FILE),
        ] {
            let source = cache_path(&cache, issue, suffix);
            if source.is_file() {
                copy_between(&cache, &source, design, &design.path().join(name))?;
            }
        }
        write_text(design, &design.path().join(PRIORITY_PENDING), "pending\n")
    });
    if let Err(error) = result {
        append_warning(
            design,
            "design file-design-oos label-retry cache",
            "scripts/larch.sh design file-oos-prepare",
            &format!("label retry sidecar restore failed: {error}"),
        );
        return false;
    }
    true
}

fn sync_retry_sidecars(design: &TemporaryRoot, issue: &str, pending: bool) {
    let Some(cache) = cache_directory(issue, true) else {
        return;
    };
    let result = (|| {
        for (name, suffix) in [
            (SENTINEL_FILE, ""),
            (COMBINED_FILE, "combined.md"),
            (ORDER_FILE, "filing-order.txt"),
            (ACCEPTED_FILE, "accepted-design.md"),
        ] {
            let source = design.path().join(name);
            if source.is_file() {
                copy_between(design, &source, &cache, &cache_path(&cache, issue, suffix))?;
            }
        }
        let marker = cache_path(&cache, issue, "priority-pending");
        if pending {
            write_text(&cache, &marker, "pending\n")
        } else {
            remove(&cache, &marker)
        }
    })();
    if let Err(error) = result {
        append_warning(
            design,
            "design file-design-oos label-retry cache",
            "scripts/larch.sh design file-oos-annotate",
            &format!("label retry sidecar sync failed: {error}"),
        );
    }
}

fn clear_pending(design: &TemporaryRoot, issue: &str) -> Result<(), String> {
    remove(design, &design.path().join(PRIORITY_PENDING))?;
    if let Some(cache) = cache_directory(issue, false) {
        let _removed = remove(&cache, &cache_path(&cache, issue, "priority-pending"));
    }
    Ok(())
}

fn load_filing_status(design: &TemporaryRoot) -> (usize, usize, usize) {
    let text = read_lossy(design, &design.path().join("oos-issue-sentinel"))
        .ok()
        .flatten()
        .unwrap_or_default();
    let number = |key: &str| kv_last(&text, key).parse().unwrap_or(0);
    (
        number("ISSUES_CREATED"),
        number("ISSUES_FAILED"),
        number("ISSUES_DEDUPLICATED"),
    )
}

fn sentinel_handled(design: &TemporaryRoot, issue: &str) -> Result<bool, String> {
    let accepted_path = design.path().join(ACCEPTED_FILE);
    let sentinel_path = design.path().join(SENTINEL_FILE);
    let accepted = read_or_empty(design, &accepted_path)?;
    if file_nonempty(&sentinel_path) {
        if design_oos_unfiled(&accepted).trim().is_empty() {
            println!("FILE_DESIGN_OOS_STATUS=skip-sentinel");
            return Ok(true);
        }
        remove(design, &sentinel_path)?;
    }
    let (created, failed, deduplicated) = load_filing_status(design);
    if failed == 0 && created + deduplicated > 0 {
        if design_oos_unfiled(&accepted).trim().is_empty() {
            println!("FILE_DESIGN_OOS_STATUS=skip-already-filed-sentinel");
            println!(
                "WARN=file-design-oos prepare: oos-issue-sentinel present (ISSUES_CREATED={created} ISSUES_DEDUPLICATED={deduplicated}) but oos-issues-created.md absent; skipping re-file"
            );
            return Ok(true);
        }
        remove(design, &design.path().join("oos-issue-sentinel"))?;
    }
    let Some(cache) = cache_directory(issue, false) else {
        return Ok(false);
    };
    let cached = cache_path(&cache, issue, "");
    if !file_nonempty(&cached) || !accepted_path.is_file() {
        return Ok(false);
    }
    let cached_accepted = read_lossy(&cache, &cache_path(&cache, issue, "accepted-design.md"))
        .ok()
        .flatten()
        .unwrap_or_default();
    let cached_signature = design_oos_identity_signature(&cached_accepted);
    let current_signature = design_oos_identity_signature(&accepted);
    if cached_signature.is_empty()
        || current_signature.len() < cached_signature.len()
        || current_signature[..cached_signature.len()] != cached_signature
    {
        remove(design, &sentinel_path)?;
        return Ok(false);
    }
    let result = (|| {
        copy_between(&cache, &cached, design, &sentinel_path)?;
        let sentinel = read_lossy(design, &sentinel_path)?.unwrap_or_default();
        let recovered = design_oos_recover_accepted(&accepted, &sentinel)
            .ok_or_else(|| "recover_oos_accepted_from_sentinel_urls failed".to_owned())?;
        write_text(design, &accepted_path, &recovered)?;
        if design_oos_unfiled(&recovered).trim().is_empty() {
            return Ok(true);
        }
        Err("recover_oos_accepted_from_sentinel_urls failed".to_owned())
    })();
    match result {
        Ok(true) => {
            println!("FILE_DESIGN_OOS_STATUS=skip-sentinel");
            Ok(true)
        }
        Ok(false) => Ok(false),
        Err(error) => {
            remove(design, &sentinel_path)?;
            append_warning(
                design,
                "design file-design-oos cross-session",
                "scripts/larch.sh design file-oos-prepare",
                &error,
            );
            Ok(false)
        }
    }
}

fn prepare(arguments: &[OsString]) -> u8 {
    let Ok(mut parsed) = parse_arguments(arguments, false) else {
        return 2;
    };
    let Ok(design) = design_root(&mut parsed, false) else {
        return 2;
    };
    let issue = issue_number(&parsed.issue_number);
    if parsed.clear_cache {
        clear_cache(&issue);
    }
    if pending(&design, &issue) {
        let _restored = restore_retry_sidecars(&design, &issue);
        println!("FILE_DESIGN_OOS_STATUS=label-only-retry");
        println!("NEXT_ACTION=label-only");
        println!("STEP5B_NEEDS_ANNOTATE=true");
        if !parsed.repo.is_empty() {
            println!("REPO={}", parsed.repo);
        }
        return 0;
    }
    let accepted_path = design.path().join(ACCEPTED_FILE);
    let Ok(accepted) = command_read(&design, &accepted_path, "design file-oos-prepare") else {
        return 2;
    };
    let Ok(pool) = command_read(
        &design,
        &design.path().join(AGGREGATE_POOL_FILE),
        "design file-oos-prepare",
    ) else {
        return 2;
    };
    let promoted = design_oos_promote_pool(&accepted, &pool);
    if promoted != accepted && write_text(&design, &accepted_path, &promoted).is_err() {
        return 2;
    }
    match sentinel_handled(&design, &issue) {
        Ok(true) => return 0,
        Ok(false) => {}
        Err(error) => {
            eprintln!("design file-oos-prepare: {error}");
            return 2;
        }
    }
    let Ok(accepted) = command_read(&design, &accepted_path, "design file-oos-prepare") else {
        return 2;
    };
    if accepted.is_empty() {
        println!("FILE_DESIGN_OOS_STATUS=skip-no-items");
        return 0;
    }
    prepare_batch(&design, &parsed.repo, &accepted)
}

fn conflict_caps() -> Result<(usize, usize), String> {
    let cluster = conflict_cap(
        "OOS_FILE_CONFLICT_CLUSTER_CAP",
        FILE_CONFLICT_DEFAULT_CLUSTER_CAP,
    )?;
    let global = conflict_cap(
        "OOS_FILE_CONFLICT_GLOBAL_CAP",
        FILE_CONFLICT_DEFAULT_GLOBAL_CAP,
    )?;
    Ok((cluster, global))
}

fn prepare_batch(design: &TemporaryRoot, repo: &str, accepted: &str) -> u8 {
    let combined_path = design.path().join(COMBINED_FILE);
    let deps_path = design.path().join(DEPS_FILE);
    let order_path = design.path().join(ORDER_FILE);
    for path in [&combined_path, &deps_path, &order_path] {
        if remove(design, path).is_err() {
            return 2;
        }
    }
    let unfiled = design_oos_unfiled(accepted);
    if unfiled.trim().is_empty() {
        println!("FILE_DESIGN_OOS_STATUS=skip-no-items");
        return 0;
    }
    let headers = parse_oos_blocks(&unfiled, BlockBoundary::OosHeading)
        .into_iter()
        .filter(|block| block.kind == OosItemKind::Oos)
        .filter_map(|block| block.item_id.strip_prefix("OOS_").map(str::to_owned))
        .collect::<Vec<_>>();
    if headers.is_empty() {
        println!("FILE_DESIGN_OOS_STATUS=skip-no-items");
        return 0;
    }
    if count_non_security_blocks(&unfiled) == 0 {
        println!("FILE_DESIGN_OOS_STATUS=skip-all-security");
        return 0;
    }
    if write_text(design, &order_path, &format!("{}\n", headers.join("\n"))).is_err() {
        return 2;
    }
    let cap = match issue_cap_value() {
        Ok(value) => value,
        Err(error) => {
            eprintln!("file-design-oos: larch oos issue-cap failed");
            eprintln!("oos-issue-cap: {error}");
            return 2;
        }
    };
    let capped = match apply_issue_cap(&unfiled, cap) {
        Ok(Some(value)) => value,
        Ok(None) => unfiled,
        Err(error) => {
            eprintln!("file-design-oos: larch oos issue-cap failed");
            eprintln!("oos-issue-cap: {}", error.message());
            return 2;
        }
    };
    if write_text(design, &combined_path, &capped).is_err() {
        return 2;
    }
    let deps = conflict_caps().and_then(|(cluster, global)| {
        plan_file_conflict_deps(&parse_issue_input(&capped).items, cluster, global)
            .map_err(|error| error.message())
    });
    let mut deps_rc = 0;
    let deps_available = match deps {
        Ok(plan) => {
            for warning in plan.warnings {
                eprintln!("{warning}");
            }
            let rendered = render_deps_tsv(&plan.deps);
            if rendered.is_empty() {
                false
            } else if write_text(design, &deps_path, &rendered).is_ok() {
                true
            } else {
                deps_rc = 2;
                false
            }
        }
        Err(_error) => {
            deps_rc = 2;
            false
        }
    };
    if !deps_available {
        let _removed = remove(design, &deps_path);
        eprintln!(
            "file-design-oos: larch oos file-conflict-deps exit {deps_rc}: graceful-degrade (no caller TSV)"
        );
    }
    println!(
        "FILE_DESIGN_OOS_DEPS_AVAILABLE={}",
        if deps_available { "true" } else { "false" }
    );
    println!("FILE_DESIGN_OOS_STATUS=ready");
    println!("FILE_DESIGN_OOS_COMBINED={}", combined_path.display());
    println!("FILE_DESIGN_OOS_DEPS_TSV={}", deps_path.display());
    println!("FILE_DESIGN_OOS_ORDER={}", order_path.display());
    if !repo.is_empty() {
        println!("REPO={repo}");
    }
    0
}

fn resolve_repo(design: &TemporaryRoot) -> String {
    for name in [
        "oos-filing-prepare.env",
        "session-env.sh",
        ".design-step0-route-state.env",
    ] {
        let value = read_key(design, &design.path().join(name), "REPO");
        if !value.is_empty() {
            return value;
        }
    }
    env::var("REPO").unwrap_or_default().trim().to_owned()
}

fn parse_order(design: &TemporaryRoot, path: &Path) -> Result<Vec<String>, String> {
    Ok(read_or_empty(design, path)?
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .map(str::to_owned)
        .collect())
}

fn label_input_error(design: &TemporaryRoot, error: &str) -> u8 {
    if write_text(design, &design.path().join(PRIORITY_PENDING), "pending\n").is_err() {
        eprintln!("design file-oos-annotate: could not persist priority label retry state");
    }
    eprintln!("design file-oos-annotate: {error}");
    1
}

struct LabelInputs<'a> {
    issue: &'a str,
    repo: &'a str,
    authorization: &'a LiveMutationRequest<'a>,
    sentinel: &'a Path,
    combined: &'a Path,
    order: Option<&'a Path>,
    stdout: Option<&'a Path>,
}

fn apply_labels(
    design: &TemporaryRoot,
    inputs: &LabelInputs<'_>,
    effects: &dyn PriorityEffects,
) -> u8 {
    let (sentinel, combined) = match read_or_empty(design, inputs.sentinel).and_then(|sentinel| {
        read_or_empty(design, inputs.combined).map(|combined| (sentinel, combined))
    }) {
        Ok(inputs) => inputs,
        Err(error) => return label_input_error(design, &error),
    };
    let order = match inputs
        .order
        .map(|path| parse_order(design, path))
        .transpose()
    {
        Ok(order) => order,
        Err(error) => return label_input_error(design, &error),
    };
    let stdout = match inputs
        .stdout
        .map(|path| read_lossy(design, path))
        .transpose()
    {
        Ok(stdout) => stdout.flatten(),
        Err(error) => return label_input_error(design, &error),
    };
    let mapping =
        design_oos_priority_map(&sentinel, &combined, order.as_deref(), stdout.as_deref());
    if design_oos_has_priority(&combined)
        && design_oos_has_filed_urls(&sentinel)
        && mapping.is_empty()
    {
        if write_text(design, &design.path().join(PRIORITY_PENDING), "pending\n").is_err() {
            eprintln!("design file-oos-annotate: could not persist priority label retry state");
            return 1;
        }
        eprintln!("design file-oos-annotate: ambiguous priority label slot mapping");
        return 1;
    }
    let priority_urls: Vec<String> = mapping
        .into_iter()
        .filter_map(|(url, priority)| priority.then_some(url))
        .collect::<Vec<_>>();
    if priority_urls.is_empty() {
        return match clear_pending(design, inputs.issue) {
            Ok(()) => 0,
            Err(error) => label_input_error(design, &error),
        };
    }
    if write_text(design, &design.path().join(PRIORITY_PENDING), "pending\n").is_err() {
        eprintln!("design file-oos-annotate: could not persist priority label retry state");
        return 1;
    }
    sync_retry_sidecars(design, inputs.issue, true);
    if let Err(reason) = authorized(inputs.authorization) {
        eprintln!("design file-oos-annotate: live mutation authorization refused: {reason}");
        return 1;
    }
    if inputs.repo.is_empty() || effects.ensure(inputs.repo).is_err() {
        eprintln!("design file-oos-annotate: priority label provisioning failed");
        return 1;
    }
    for url in priority_urls {
        if effects
            .apply(inputs.repo, &url, inputs.authorization)
            .is_err()
        {
            eprintln!("design file-oos-annotate: priority label application failed for {url}");
            return 1;
        }
    }
    if let Err(error) = clear_pending(design, inputs.issue) {
        eprintln!("design file-oos-annotate: {error}");
        return 1;
    }
    sync_retry_sidecars(design, inputs.issue, false);
    0
}

fn empty_stdout(path: &Path) -> u8 {
    println!("FILE_DESIGN_OOS_STATUS=annotate-failed-empty-stdout");
    println!("NEXT_ACTION=retry-file-and-annotate");
    println!(
        "WARN=file-design-oos annotate: issue-stdout-file empty or missing ({}); oos-issues-created.md not written",
        path.display()
    );
    eprintln!(
        "design file-oos-annotate: issue-stdout-file empty or missing ({})",
        path.display()
    );
    1
}

fn annotate(arguments: &[OsString], effects: &dyn PriorityEffects) -> u8 {
    let Ok(mut parsed) = parse_arguments(arguments, true) else {
        return 2;
    };
    let Ok(design) = design_root(&mut parsed, true) else {
        return 2;
    };
    let issue = issue_number(&parsed.issue_number);
    let authorization = authorization_request(
        &parsed.context_file,
        &parsed.run_id,
        &parsed.trusted_root,
        parsed.operator_invoked,
    );
    let prepare_env = design.path().join("oos-filing-prepare.env");
    let label_only = parsed.label_only
        || read_key(&design, &prepare_env, "FILE_DESIGN_OOS_STATUS") == "label-only-retry"
        || read_key(&design, &prepare_env, "NEXT_ACTION") == "label-only";
    let repo = if parsed.repo.trim().is_empty() {
        resolve_repo(&design)
    } else {
        parsed.repo.trim().to_owned()
    };
    let stdout_path = if parsed.issue_stdout_file.is_empty() {
        design.path().join(ISSUE_STDOUT_FILE)
    } else {
        PathBuf::from(&parsed.issue_stdout_file)
    };
    let sentinel_path = design.path().join(SENTINEL_FILE);
    let combined_path = design.path().join(COMBINED_FILE);
    let order_path = design.path().join(ORDER_FILE);
    if label_only {
        if !sentinel_path.is_file() || !combined_path.is_file() {
            println!("FILE_DESIGN_OOS_STATUS=annotate-label-failed");
            eprintln!(
                "design file-oos-annotate: label-only retry missing sentinel or combined OOS file"
            );
            return 1;
        }
        let rc = apply_labels(
            &design,
            &LabelInputs {
                issue: &issue,
                repo: &repo,
                authorization: &authorization,
                sentinel: &sentinel_path,
                combined: &combined_path,
                order: order_path.is_file().then_some(order_path.as_path()),
                stdout: stdout_path.is_file().then_some(stdout_path.as_path()),
            },
            effects,
        );
        println!(
            "FILE_DESIGN_OOS_STATUS={}",
            if rc == 0 {
                "annotate-label-complete"
            } else {
                "annotate-label-failed"
            }
        );
        return rc;
    }
    annotate_fresh(
        &design,
        &LabelInputs {
            issue: &issue,
            repo: &repo,
            authorization: &authorization,
            sentinel: &sentinel_path,
            combined: &combined_path,
            order: Some(&order_path),
            stdout: Some(&stdout_path),
        },
        effects,
    )
}

fn annotate_fresh(
    design: &TemporaryRoot,
    inputs: &LabelInputs<'_>,
    effects: &dyn PriorityEffects,
) -> u8 {
    let stdout_path = inputs.stdout.expect("fresh annotation stdout");
    let order_path = inputs.order.expect("fresh annotation order");
    let stdout = match read_lossy(design, stdout_path) {
        Ok(Some(text)) if !text.is_empty() => text,
        Ok(_) => return empty_stdout(stdout_path),
        Err(error) => {
            eprintln!("design file-oos-annotate: {error}");
            return 2;
        }
    };
    let accepted_path = design.path().join(ACCEPTED_FILE);
    if !order_path.is_file() {
        eprintln!(
            "file-design-oos: missing {} (run prepare first)",
            order_path.display()
        );
        return 2;
    }
    if !accepted_path.is_file() {
        eprintln!("file-design-oos: missing {}", accepted_path.display());
        return 2;
    }
    let order = match parse_order(design, order_path) {
        Ok(order) => order,
        Err(error) => {
            eprintln!("design file-oos-annotate: {error}");
            return 2;
        }
    };
    let Ok(accepted) = command_read(design, &accepted_path, "design file-oos-annotate") else {
        return 2;
    };
    let Ok(combined) = command_read(design, inputs.combined, "design file-oos-annotate") else {
        return 2;
    };
    let issue_output = parse_design_oos_issue_output(&stdout);
    let annotation = design_oos_annotate(&order, &accepted, &combined, &issue_output);
    if write_text(design, &accepted_path, &annotation.accepted).is_err() {
        return 2;
    }
    let sentinel = if annotation.map_lines.is_empty() {
        String::new()
    } else {
        format!("{}\n", annotation.map_lines.join("\n"))
    };
    if write_text(design, inputs.sentinel, &sentinel).is_err() {
        return 2;
    }
    if apply_labels(design, inputs, effects) != 0 {
        println!("FILE_DESIGN_OOS_STATUS=annotate-label-failed");
        return 1;
    }
    let partial_path = design.path().join("oos-issues-created.partial.md");
    if issue_output.issues_failed > 0 {
        if let Err(error) = write_text(design, &partial_path, &sentinel) {
            eprintln!("design file-oos-annotate: {error}");
            return 2;
        }
        if let Err(error) = remove(design, inputs.sentinel) {
            eprintln!("design file-oos-annotate: {error}");
            return 2;
        }
        println!("FILE_DESIGN_OOS_STATUS=annotate-partial-failed");
        return 1;
    }
    if let Err(error) = remove(design, &partial_path) {
        eprintln!("design file-oos-annotate: {error}");
        return 2;
    }
    if let Some(cache) = cache_directory(inputs.issue, true)
        && let Err(error) = copy_between(
            design,
            inputs.sentinel,
            &cache,
            &cache_path(&cache, inputs.issue, ""),
        )
    {
        append_warning(
            design,
            "design file-design-oos cache",
            "scripts/larch.sh design file-oos-annotate",
            &format!("cross-session cache sync failed: {error}"),
        );
    }
    println!("FILE_DESIGN_OOS_STATUS=annotate-complete");
    0
}

#[cfg(test)]
mod tests {
    use std::{cell::Cell, fs};

    use tempfile::TempDir;

    use super::*;

    #[derive(Default)]
    struct FailingPriority {
        applied: Cell<bool>,
    }

    impl PriorityEffects for FailingPriority {
        fn ensure(&self, _repo: &str) -> Result<(), String> {
            Ok(())
        }

        fn apply(
            &self,
            _repo: &str,
            _url: &str,
            _authorization: &LiveMutationRequest<'_>,
        ) -> Result<(), String> {
            self.applied.set(true);
            Err("failed".into())
        }
    }

    struct RecordingPriority {
        ensure_calls: Cell<usize>,
        apply_calls: Cell<usize>,
        fail_ensure: bool,
    }

    impl RecordingPriority {
        fn successful() -> Self {
            Self {
                ensure_calls: Cell::new(0),
                apply_calls: Cell::new(0),
                fail_ensure: false,
            }
        }

        fn failing_ensure() -> Self {
            Self {
                ensure_calls: Cell::new(0),
                apply_calls: Cell::new(0),
                fail_ensure: true,
            }
        }
    }

    impl PriorityEffects for RecordingPriority {
        fn ensure(&self, _repo: &str) -> Result<(), String> {
            self.ensure_calls.set(self.ensure_calls.get() + 1);
            if self.fail_ensure {
                Err("ensure failed".into())
            } else {
                Ok(())
            }
        }

        fn apply(
            &self,
            _repo: &str,
            _url: &str,
            _authorization: &LiveMutationRequest<'_>,
        ) -> Result<(), String> {
            self.apply_calls.set(self.apply_calls.get() + 1);
            Ok(())
        }
    }

    fn args(root: &TempDir, extra: &[&str]) -> Vec<OsString> {
        let mut values = vec!["--design-tmpdir".into(), root.path().as_os_str().to_owned()];
        values.extend(extra.iter().map(OsString::from));
        values
    }

    fn seed_priority(root: &TempDir) {
        let risky = "### OOS_1: risky\n- **Focus area**: correctness\n";
        fs::write(root.path().join(ACCEPTED_FILE), risky).expect("accepted");
        fs::write(root.path().join(COMBINED_FILE), risky).expect("combined");
        fs::write(root.path().join(ORDER_FILE), "1\n").expect("order");
        fs::write(
            root.path().join(ISSUE_STDOUT_FILE),
            "ISSUE_URL=https://github.com/acme/repo/issues/1\nISSUES_FAILED=0\n",
        )
        .expect("stdout");
    }

    fn resolved(root: &TempDir) -> TemporaryRoot {
        TemporaryRoot::resolve(Some(root.path())).expect("temporary root")
    }

    #[test]
    fn priority_mutation_requires_live_authorization() {
        let root = TempDir::new().expect("tmpdir");
        seed_priority(&root);
        let effects = FailingPriority::default();
        assert_eq!(
            annotate(&args(&root, &["--repo", "acme/repo"]), &effects),
            1
        );
        assert!(!effects.applied.get());
        assert!(root.path().join(PRIORITY_PENDING).is_file());
    }

    #[test]
    fn a_priority_failure_keeps_durable_retry_state() {
        let root = TempDir::new().expect("tmpdir");
        seed_priority(&root);
        let effects = FailingPriority::default();
        assert_eq!(
            annotate(
                &args(&root, &["--repo", "acme/repo", "--operator-invoked"]),
                &effects,
            ),
            1
        );
        assert!(effects.applied.get());
        assert!(root.path().join(PRIORITY_PENDING).is_file());
        assert!(root.path().join(SENTINEL_FILE).is_file());
    }

    #[cfg(unix)]
    #[test]
    fn prepare_refuses_a_symlinked_accepted_file() {
        use std::os::unix::fs::symlink;

        let root = TempDir::new().expect("tmpdir");
        fs::write(root.path().join("outside.md"), "### OOS_1: one\nbody\n").expect("outside");
        symlink(
            root.path().join("outside.md"),
            root.path().join(ACCEPTED_FILE),
        )
        .expect("symlink");
        assert_eq!(prepare(&args(&root, &[])), 2);
    }

    #[test]
    fn helpers_validate_arguments_paths_and_session_values() {
        let parsed = parse_arguments(
            &[
                "--design-tmpdir".into(),
                "/tmp/design".into(),
                "--issue-number".into(),
                " 42 ".into(),
                "--issue-stdout-file".into(),
                "/tmp/stdout".into(),
                "--repo".into(),
                "acme/repo".into(),
                "--context-file".into(),
                "/tmp/context".into(),
                "--run-id".into(),
                "run".into(),
                "--trusted-root".into(),
                "/tmp".into(),
                "--operator-invoked".into(),
                "--label-only".into(),
            ],
            true,
        )
        .expect("valid arguments");
        assert_eq!(parsed.issue_number, " 42 ");
        assert!(parsed.operator_invoked);
        assert!(parsed.label_only);
        assert_eq!(prepare(&["--unknown".into()]), 2);
        assert_eq!(
            annotate(&["--unknown".into()], &RecordingPriority::successful()),
            2
        );

        let root = TempDir::new().expect("tmpdir");
        let design = resolved(&root);
        assert_eq!(
            read_lossy(&design, &root.path().join("missing")).unwrap(),
            None
        );
        assert!(read_lossy(&design, root.path()).is_err());
        assert!(remove(&design, &root.path().join("missing")).is_ok());
        fs::write(root.path().join("remove-me"), "x").expect("seed removable file");
        remove(&design, &design.path().join("remove-me")).expect("remove file");
        assert!(!root.path().join("remove-me").exists());

        assert_eq!(issue_number(" 42 "), "42");
        assert_eq!(issue_number("not-a-number"), "");
        assert_eq!(kv_last("A='one'\nA=\"two\"\n", "A"), "two");
        fs::write(root.path().join("session-env.sh"), "REPO='acme/repo'\n").expect("session");
        assert_eq!(resolve_repo(&design), "acme/repo");
        assert_eq!(cache_path(&design, "42", ""), design.path().join("42.md"));
        assert_eq!(
            cache_path(&design, "42", "combined.md"),
            design.path().join("42.combined.md")
        );
        clear_cache("");
        assert!(!restore_retry_sidecars(&design, ""));
        sync_retry_sidecars(&design, "", true);
        clear_pending(&design, "").expect("empty issue has no cache state");

        let missing = root.path().join("not-a-directory");
        assert_eq!(
            prepare(&["--design-tmpdir".into(), missing.as_os_str().to_owned(),]),
            2
        );
    }

    #[test]
    fn sentinel_handling_is_conservative_without_cross_session_state() {
        let filed = "### OOS_1: filed\n- **Filed URL**: https://github.com/o/r/issues/1\n";

        let root = TempDir::new().expect("tmpdir");
        fs::write(root.path().join(ACCEPTED_FILE), filed).expect("accepted");
        fs::write(root.path().join(SENTINEL_FILE), "filed\n").expect("sentinel");
        assert!(sentinel_handled(&resolved(&root), "").expect("sentinel state"));

        let root = TempDir::new().expect("tmpdir");
        fs::write(root.path().join(ACCEPTED_FILE), filed).expect("accepted");
        fs::write(
            root.path().join("oos-issue-sentinel"),
            "ISSUES_CREATED=1\nISSUES_FAILED=0\nISSUES_DEDUPLICATED=0\n",
        )
        .expect("filing sentinel");
        assert!(sentinel_handled(&resolved(&root), "").expect("filing state"));

        let root = TempDir::new().expect("tmpdir");
        fs::write(
            root.path().join(ACCEPTED_FILE),
            "### OOS_1: pending\nbody\n",
        )
        .expect("accepted");
        fs::write(root.path().join(SENTINEL_FILE), "stale\n").expect("sentinel");
        assert!(!sentinel_handled(&resolved(&root), "").expect("stale state"));
        assert!(!root.path().join(SENTINEL_FILE).exists());
    }

    #[test]
    fn prepare_handles_local_retry_empty_and_capped_batches() {
        let retry = TempDir::new().expect("tmpdir");
        fs::write(retry.path().join(PRIORITY_PENDING), "pending\n").expect("pending");
        assert_eq!(prepare(&args(&retry, &["--repo", "acme/repo"])), 0);

        let empty = TempDir::new().expect("tmpdir");
        assert_eq!(prepare(&args(&empty, &["--clear-cross-session-cache"])), 0);
        assert!(!empty.path().join(COMBINED_FILE).exists());

        let batch = TempDir::new().expect("tmpdir");
        let accepted = concat!(
            "### OOS_1: first\n- **Description**: update `src/shared.rs:1-10`.\n\n",
            "### OOS_2: second\n- **Description**: update `src/shared.rs:5-15`.\n",
        );
        assert_eq!(prepare_batch(&resolved(&batch), "acme/repo", accepted), 0);
        assert_eq!(
            fs::read_to_string(batch.path().join(ORDER_FILE)).expect("order"),
            "1\n2\n"
        );
        assert!(batch.path().join(COMBINED_FILE).is_file());

        assert_eq!(
            prepare_batch(
                &resolved(&batch),
                "",
                "### OOS_9: filed\n- **Filed URL**: https://github.com/o/r/issues/9\n",
            ),
            0
        );
    }

    #[test]
    fn label_application_covers_ambiguous_benign_failure_and_success_paths() {
        let authorization = authorization_request("", "", "", true);

        let benign = TempDir::new().expect("tmpdir");
        fs::write(benign.path().join(SENTINEL_FILE), "not-a-url\n").expect("sentinel");
        fs::write(
            benign.path().join(COMBINED_FILE),
            "### OOS_1: docs\n- **Focus area**: documentation\n",
        )
        .expect("combined");
        fs::write(benign.path().join(PRIORITY_PENDING), "pending\n").expect("pending");
        let benign_root = resolved(&benign);
        let benign_sentinel = benign_root.path().join(SENTINEL_FILE);
        let benign_combined = benign_root.path().join(COMBINED_FILE);
        let benign_inputs = LabelInputs {
            issue: "",
            repo: "acme/repo",
            authorization: &authorization,
            sentinel: &benign_sentinel,
            combined: &benign_combined,
            order: None,
            stdout: None,
        };
        assert_eq!(
            apply_labels(
                &benign_root,
                &benign_inputs,
                &RecordingPriority::successful()
            ),
            0
        );
        assert!(!benign.path().join(PRIORITY_PENDING).exists());

        let ambiguous = TempDir::new().expect("tmpdir");
        fs::write(
            ambiguous.path().join(SENTINEL_FILE),
            "https://github.com/o/r/issues/1\n",
        )
        .expect("sentinel");
        fs::write(
            ambiguous.path().join(COMBINED_FILE),
            concat!(
                "### OOS_1: one\n- **Focus area**: correctness\n\n",
                "### OOS_2: two\n- **Focus area**: correctness\n",
            ),
        )
        .expect("combined");
        let ambiguous_root = resolved(&ambiguous);
        let ambiguous_sentinel = ambiguous_root.path().join(SENTINEL_FILE);
        let ambiguous_combined = ambiguous_root.path().join(COMBINED_FILE);
        let ambiguous_inputs = LabelInputs {
            issue: "",
            repo: "acme/repo",
            authorization: &authorization,
            sentinel: &ambiguous_sentinel,
            combined: &ambiguous_combined,
            order: None,
            stdout: None,
        };
        assert_eq!(
            apply_labels(
                &ambiguous_root,
                &ambiguous_inputs,
                &RecordingPriority::successful(),
            ),
            1
        );
        assert!(ambiguous.path().join(PRIORITY_PENDING).is_file());

        let priority = TempDir::new().expect("tmpdir");
        seed_priority(&priority);
        fs::write(
            priority.path().join(SENTINEL_FILE),
            "OOS_FILE_MAP\t1\thttps://github.com/acme/repo/issues/1\n",
        )
        .expect("sentinel");
        let priority_root = resolved(&priority);
        let priority_sentinel = priority_root.path().join(SENTINEL_FILE);
        let priority_combined = priority_root.path().join(COMBINED_FILE);
        let priority_order = priority_root.path().join(ORDER_FILE);
        let priority_stdout = priority_root.path().join(ISSUE_STDOUT_FILE);
        let priority_inputs = LabelInputs {
            issue: "",
            repo: "acme/repo",
            authorization: &authorization,
            sentinel: &priority_sentinel,
            combined: &priority_combined,
            order: Some(&priority_order),
            stdout: Some(&priority_stdout),
        };
        let successful = RecordingPriority::successful();
        assert_eq!(
            apply_labels(&priority_root, &priority_inputs, &successful),
            0
        );
        assert_eq!(successful.ensure_calls.get(), 1);
        assert_eq!(successful.apply_calls.get(), 1);
        assert_eq!(
            apply_labels(
                &priority_root,
                &priority_inputs,
                &RecordingPriority::failing_ensure(),
            ),
            1
        );

        let invalid = TempDir::new().expect("tmpdir");
        fs::write(invalid.path().join(SENTINEL_FILE), "sentinel\n").expect("sentinel");
        fs::create_dir(invalid.path().join(COMBINED_FILE)).expect("combined directory");
        let invalid_root = resolved(&invalid);
        let invalid_sentinel = invalid_root.path().join(SENTINEL_FILE);
        let invalid_combined = invalid_root.path().join(COMBINED_FILE);
        let invalid_inputs = LabelInputs {
            issue: "",
            repo: "acme/repo",
            authorization: &authorization,
            sentinel: &invalid_sentinel,
            combined: &invalid_combined,
            order: None,
            stdout: None,
        };
        assert_eq!(
            apply_labels(
                &invalid_root,
                &invalid_inputs,
                &RecordingPriority::successful()
            ),
            1
        );
        assert!(invalid.path().join(PRIORITY_PENDING).is_file());
    }

    #[test]
    fn annotate_handles_label_retry_and_fresh_input_failures() {
        let missing = TempDir::new().expect("tmpdir");
        assert_eq!(
            annotate(
                &args(&missing, &["--label-only"]),
                &RecordingPriority::successful(),
            ),
            1
        );

        let empty_stdout_root = TempDir::new().expect("tmpdir");
        fs::write(
            empty_stdout_root.path().join(ACCEPTED_FILE),
            "### OOS_1: one\nbody\n",
        )
        .expect("accepted");
        fs::write(empty_stdout_root.path().join(ORDER_FILE), "1\n").expect("order");
        fs::write(
            empty_stdout_root.path().join(COMBINED_FILE),
            "### OOS_1: one\nbody\n",
        )
        .expect("combined");
        assert_eq!(
            annotate(
                &args(&empty_stdout_root, &[]),
                &RecordingPriority::successful(),
            ),
            1
        );

        let missing_order = TempDir::new().expect("tmpdir");
        fs::write(
            missing_order.path().join(ISSUE_STDOUT_FILE),
            "ISSUES_FAILED=0\n",
        )
        .expect("stdout");
        fs::write(
            missing_order.path().join(ACCEPTED_FILE),
            "### OOS_1: one\nbody\n",
        )
        .expect("accepted");
        assert_eq!(
            annotate(&args(&missing_order, &[]), &RecordingPriority::successful(),),
            2
        );

        let missing_accepted = TempDir::new().expect("tmpdir");
        fs::write(
            missing_accepted.path().join(ISSUE_STDOUT_FILE),
            "ISSUES_FAILED=0\n",
        )
        .expect("stdout");
        fs::write(missing_accepted.path().join(ORDER_FILE), "1\n").expect("order");
        assert_eq!(
            annotate(
                &args(&missing_accepted, &[]),
                &RecordingPriority::successful(),
            ),
            2
        );

        let complete = TempDir::new().expect("tmpdir");
        seed_priority(&complete);
        let effects = RecordingPriority::successful();
        assert_eq!(
            annotate(
                &args(&complete, &["--repo", "acme/repo", "--operator-invoked"],),
                &effects,
            ),
            0
        );
        assert_eq!(effects.apply_calls.get(), 1);
        fs::write(
            complete.path().join("oos-filing-prepare.env"),
            "NEXT_ACTION=label-only\nREPO=acme/repo\n",
        )
        .expect("prepare env");
        assert_eq!(
            annotate(
                &args(&complete, &["--operator-invoked"]),
                &RecordingPriority::successful(),
            ),
            0
        );

        let no_mapping = TempDir::new().expect("tmpdir");
        fs::write(
            no_mapping.path().join(ACCEPTED_FILE),
            "### OOS_1: docs\n- **Focus area**: documentation\n",
        )
        .expect("accepted");
        fs::write(
            no_mapping.path().join(COMBINED_FILE),
            "### OOS_1: docs\n- **Focus area**: documentation\n",
        )
        .expect("combined");
        fs::write(no_mapping.path().join(ORDER_FILE), "1\n").expect("order");
        fs::write(
            no_mapping.path().join(ISSUE_STDOUT_FILE),
            "ISSUES_FAILED=0\n",
        )
        .expect("stdout");
        assert_eq!(
            annotate(&args(&no_mapping, &[]), &RecordingPriority::successful()),
            0
        );
        assert_eq!(
            fs::read_to_string(no_mapping.path().join(SENTINEL_FILE)).expect("sentinel"),
            ""
        );

        let outside = TempDir::new().expect("outside");
        fs::write(outside.path().join("stdout"), "ISSUES_FAILED=0\n").expect("outside stdout");
        assert_eq!(
            annotate(
                &args(
                    &no_mapping,
                    &[
                        "--issue-stdout-file",
                        outside.path().join("stdout").to_str().expect("utf8 path"),
                    ],
                ),
                &RecordingPriority::successful(),
            ),
            2
        );
    }
}
