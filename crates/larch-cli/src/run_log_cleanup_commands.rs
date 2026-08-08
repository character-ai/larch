//! Rust-owned cleanup for completed historical `/implement` run logs.
//!
//! The command deliberately selects runs through [`RunLogCorpus`] rather than
//! walking the corpus itself. Every destructive operation is then confined to
//! its selected run and revalidated immediately before it is applied.

use std::{
    collections::{BTreeMap, BTreeSet},
    env,
    ffi::OsString,
    fmt::Write as _,
    fs,
    io::Read as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{
    ConfinedPath, PathIntent, RepositoryRoot, atomic_write_utf8, open_confined_read, read_utf8,
};
use larch_core::{
    OrderedJson, RunLogCorpus, RunLogCorpusEvent, RunLogRun, RunLogSelection, RunLogSlug,
    python_json_dumps,
};

use crate::{
    argparse_compat::parse_with_flags,
    run_log_migration_commands::{ordered_field, ordered_insert, ordered_value_is_truthy},
};

const OPTIONS: &[&str] = &["--run-dir"];
const FLAGS: &[&str] = &["--execute"];
const USAGE: &str = "usage: cli.py [-h] [--execute] [--run-dir PATH]";
const HELP: &str = "usage: cli.py [-h] [--execute] [--run-dir PATH]\n\ncleanup_implement_logs.py: clean redundant artifacts from completed implement run logs.\n\noptions:\n  -h, --help      show this help message and exit\n  --execute       Actually perform the cleanup. Without this flag, runs in dry-run mode.\n  --run-dir PATH  Restrict to one manifest-accepted run directory.";
const INPUT_CAP_CHARS: usize = 1024;
const SIDECAR_EXTENSIONS: &[&str] = &[".meta", ".json"];

/// Run the historical `/implement` artifact cleanup.
#[must_use]
pub fn cleanup_implement_logs(arguments: &[OsString]) -> ExitCode {
    if has_help(arguments) {
        println!("{HELP}");
        return ExitCode::SUCCESS;
    }
    let parsed = parse_with_flags(arguments, OPTIONS, FLAGS, 0);
    if let Some(error) = parsed.error() {
        return argument_failure(&error);
    }
    let requested_run = parsed.value("--run-dir").map(PathBuf::from);
    let execute = parsed.flag("--execute");
    let cwd = match env::current_dir() {
        Ok(path) => path,
        Err(error) => {
            return failure(&format!(
                "could not determine the current directory: {error}"
            ));
        }
    };
    let mut outcome = match cleanup(&cwd, requested_run.as_deref()) {
        Ok(outcome) => outcome,
        Err(error) => return failure(&error),
    };

    if !execute {
        println!("DRY-RUN mode: pass --execute to apply changes");
    }
    for warning in &outcome.warnings {
        eprintln!("WARNING: {warning}");
    }
    for protected in &outcome.protected_runs {
        println!("PROTECTED_RUN={}", protected.display());
    }
    for plan in &outcome.plans {
        for action in &plan.actions {
            if execute {
                match action.apply(&plan.root) {
                    Ok(()) => {
                        outcome.stats.increment(action.counter());
                        println!("CHANGED_PATH={}", action.path().display());
                    }
                    Err(error) => outcome.errors.push(error),
                }
            } else {
                outcome.stats.increment(action.counter());
                println!("DRY_RUN_PATH={}", action.path().display());
            }
        }
    }
    println!();
    outcome.stats.report(&outcome.errors);
    if outcome.errors.is_empty() {
        ExitCode::SUCCESS
    } else {
        ExitCode::FAILURE
    }
}

fn has_help(arguments: &[OsString]) -> bool {
    arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
}

fn argument_failure(message: &str) -> ExitCode {
    eprintln!("{USAGE}");
    eprintln!("cli.py run-log cleanup-implement-logs: error: {message}");
    ExitCode::from(2)
}

fn failure(message: &str) -> ExitCode {
    eprintln!(
        "cleanup-implement-logs failed: {}",
        message.replace(['\n', '\r'], " ")
    );
    ExitCode::FAILURE
}

struct Outcome {
    plans: Vec<RunPlan>,
    protected_runs: Vec<PathBuf>,
    warnings: Vec<String>,
    errors: Vec<String>,
    stats: Stats,
}

fn cleanup(cwd: &Path, requested_run: Option<&Path>) -> Result<Outcome, String> {
    let (repository, implementation_root) = implementation_root(cwd)?;
    let requested_run = requested_run
        .map(|path| resolve_requested_run(path, repository.path(), &implementation_root))
        .transpose()?;
    let skill = RunLogSlug::parse("implement").map_err(|error| error.to_string())?;
    let corpus = RunLogCorpus::new(repository.path().join("larch-logs"));
    let mut runs = Vec::new();
    let mut warnings = Vec::new();
    for event in corpus.select(RunLogSelection::for_skill(skill)) {
        match event {
            RunLogCorpusEvent::Run(run) => runs.push(*run),
            RunLogCorpusEvent::Warning(warning) => warnings.push(warning.message().to_owned()),
        }
    }

    if let Some(requested) = requested_run {
        runs.retain(|run| fs::canonicalize(run.directory()).is_ok_and(|path| path == requested));
        if runs.is_empty() {
            return Err(format!(
                "--run-dir must name a manifest-accepted non-symlinked run directory inside {}",
                implementation_root.display()
            ));
        }
    }

    let mut outcome = Outcome {
        plans: Vec::new(),
        protected_runs: Vec::new(),
        warnings,
        errors: Vec::new(),
        stats: Stats::default(),
    };
    for run in runs {
        match run_is_eligible(&run) {
            Eligibility::Eligible => match plan_run(&run) {
                Ok(plan) => outcome.plans.push(plan),
                Err(error) => outcome.errors.push(error),
            },
            Eligibility::Protected(reason) => {
                outcome.protected_runs.push(run.directory().to_owned());
                outcome.stats.protected_runs += 1;
                outcome.warnings.push(format!(
                    "skipping protected run {}: {reason}",
                    run.directory().display()
                ));
            }
        }
    }
    Ok(outcome)
}

fn implementation_root(cwd: &Path) -> Result<(RepositoryRoot, PathBuf), String> {
    let canonical_cwd = fs::canonicalize(cwd)
        .map_err(|error| format!("could not resolve {}: {error}", cwd.display()))?;
    let repository =
        RepositoryRoot::resolve(Some(&canonical_cwd)).map_err(|error| error.to_string())?;
    let logs_root = repository.path().join("larch-logs");
    let implementation_root = logs_root.join("implement");
    for path in [&logs_root, &implementation_root] {
        let metadata = fs::symlink_metadata(path)
            .map_err(|_error| format!("{} not found", implementation_root.display()))?;
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return Err(format!("{} not found", implementation_root.display()));
        }
    }
    let implementation_root = fs::canonicalize(&implementation_root)
        .map_err(|error| format!("could not resolve implementation run-log root: {error}"))?;
    if !implementation_root.starts_with(repository.path()) {
        return Err(format!(
            "implementation run-log root escapes {}",
            repository.path().display()
        ));
    }
    Ok((repository, implementation_root))
}

fn resolve_requested_run(
    requested: &Path,
    repository: &Path,
    implementation_root: &Path,
) -> Result<PathBuf, String> {
    let requested = if requested.is_absolute() {
        requested.to_owned()
    } else {
        repository.join(requested)
    };
    let metadata = fs::symlink_metadata(&requested).map_err(|error| {
        format!(
            "--run-dir must resolve to a path inside {} (could not inspect {}: {error})",
            implementation_root.display(),
            requested.display()
        )
    })?;
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Err(format!(
            "--run-dir must resolve to a non-symlinked directory inside {}",
            implementation_root.display()
        ));
    }
    let resolved = fs::canonicalize(&requested).map_err(|error| {
        format!(
            "--run-dir must resolve to a path inside {} ({error})",
            implementation_root.display()
        )
    })?;
    if resolved.parent() != Some(implementation_root) {
        return Err(format!(
            "--run-dir must resolve to a direct child of {}",
            implementation_root.display()
        ));
    }
    Ok(resolved)
}

enum Eligibility {
    Eligible,
    Protected(String),
}

fn run_is_eligible(run: &RunLogRun) -> Eligibility {
    let status = run
        .manifest()
        .field("status")
        .and_then(|value| value.as_str());
    if status != Some("done") {
        return Eligibility::Protected("status is not done".to_owned());
    }
    let root = match RepositoryRoot::resolve(Some(run.directory())) {
        Ok(root) => root,
        Err(error) => return Eligibility::Protected(format!("run root is unsafe: {error}")),
    };
    let durability = match durability_state(&root) {
        Ok(state) => state,
        Err(error) => {
            return Eligibility::Protected(format!("durability cannot be verified: {error}"));
        }
    };
    if let Some(state) = durability {
        if state != "committed" {
            return Eligibility::Protected(format!("durability state is {state:?}"));
        }
    } else if run
        .manifest()
        .field("publication_mode")
        .is_some_and(|value| value.as_str() != Some("disabled"))
    {
        return Eligibility::Protected(
            "published or unrecognized run has no durability marker".to_owned(),
        );
    }
    Eligibility::Eligible
}

fn durability_state(root: &RepositoryRoot) -> Result<Option<String>, String> {
    let path = root.path().join(".durability");
    match fs::symlink_metadata(&path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(format!("could not inspect {}: {error}", path.display())),
        Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_file() => {
            return Err(format!("{} is not a regular file", path.display()));
        }
        Ok(_) => {}
    }
    let text = read_lossy(root, &path)?;
    Ok(Some(
        text.lines()
            .find_map(|line| line.strip_prefix("state=").map(str::trim))
            .unwrap_or_default()
            .to_owned(),
    ))
}

struct RunPlan {
    root: RepositoryRoot,
    actions: Vec<Action>,
}

fn plan_run(run: &RunLogRun) -> Result<RunPlan, String> {
    let root = RepositoryRoot::resolve(Some(run.directory())).map_err(|error| error.to_string())?;
    let files = run_files(run, &root)?;
    let mut builder = PlanBuilder::default();
    plan_dynamic_prompts(&files, &mut builder);
    plan_identical_aggregators(&root, &files, &mut builder)?;
    plan_raw_manifests(&files, &mut builder);
    plan_refresh_sidecars(&files, &mut builder);
    plan_cursor_outputs(&files, &mut builder);
    plan_transcripts(&root, &files, &mut builder)?;
    plan_breadcrumbs(&root, &files, &mut builder)?;
    plan_tally(&root, &files, &mut builder)?;
    Ok(RunPlan {
        root,
        actions: builder.actions,
    })
}

type RunFiles = BTreeMap<PathBuf, PathBuf>;

fn run_files(run: &RunLogRun, root: &RepositoryRoot) -> Result<RunFiles, String> {
    let mut files = BTreeMap::new();
    for path in run.files() {
        let relative = path.strip_prefix(root.path()).map_err(|_error| {
            format!(
                "selected run file {} escapes {}",
                path.display(),
                root.path().display()
            )
        })?;
        files.insert(relative.to_owned(), path);
    }
    Ok(files)
}

#[derive(Default)]
struct PlanBuilder {
    actions: Vec<Action>,
    deleted: BTreeSet<PathBuf>,
    written: BTreeSet<PathBuf>,
}

impl PlanBuilder {
    fn delete(&mut self, path: PathBuf, counter: Counter) {
        if self.deleted.insert(path.clone()) {
            self.actions.push(Action::Delete { path, counter });
        }
    }

    fn delete_with_sidecars(&mut self, relative: &Path, files: &RunFiles, counter: Counter) {
        if let Some(path) = files.get(relative) {
            self.delete(path.clone(), counter);
        }
        for extension in SIDECAR_EXTENSIONS {
            let sidecar = PathBuf::from(format!("{}{}", relative.display(), extension));
            if let Some(path) = files.get(&sidecar) {
                self.delete(path.clone(), counter);
            }
        }
    }

    fn write(&mut self, path: PathBuf, text: String, counter: Counter) {
        if self.written.insert(path.clone()) {
            self.actions.push(Action::Write {
                path,
                text,
                counter,
            });
        }
    }
}

enum Action {
    Delete {
        path: PathBuf,
        counter: Counter,
    },
    Write {
        path: PathBuf,
        text: String,
        counter: Counter,
    },
}

impl Action {
    fn path(&self) -> &Path {
        match self {
            Self::Delete { path, .. } | Self::Write { path, .. } => path,
        }
    }

    const fn counter(&self) -> Counter {
        match self {
            Self::Delete { counter, .. } | Self::Write { counter, .. } => *counter,
        }
    }

    fn apply(&self, root: &RepositoryRoot) -> Result<(), String> {
        match self {
            Self::Delete { path, .. } => {
                let confined = root
                    .confine(path, PathIntent::Cleanup)
                    .map_err(|error| format!("refusing to remove {}: {error}", path.display()))?;
                confined
                    .revalidate()
                    .map_err(|error| format!("refusing to remove {}: {error}", path.display()))?;
                fs::remove_file(confined.path())
                    .map_err(|error| format!("could not remove {}: {error}", path.display()))
            }
            Self::Write { path, text, .. } => {
                let confined = root
                    .confine(path, PathIntent::Write)
                    .map_err(|error| format!("refusing to write {}: {error}", path.display()))?;
                atomic_write_utf8(&confined, text, 0o600)
                    .map_err(|error| format!("could not write {}: {error}", path.display()))
            }
        }
    }
}

#[derive(Clone, Copy)]
enum Counter {
    DynamicPrompt,
    Aggregator,
    RawManifest,
    Refresh,
    CursorOutput,
    Transcript,
    BreadcrumbDirectory,
    BreadcrumbFile,
    Tally,
}

#[derive(Default)]
struct Stats {
    dynamic_prompts: usize,
    aggregators: usize,
    raw_manifests: usize,
    refresh_sidecars: usize,
    cursor_outputs: usize,
    transcripts: usize,
    breadcrumb_directories: usize,
    breadcrumb_files: usize,
    tally_bodies: usize,
    protected_runs: usize,
}

impl Stats {
    const fn increment(&mut self, counter: Counter) {
        match counter {
            Counter::DynamicPrompt => self.dynamic_prompts += 1,
            Counter::Aggregator => self.aggregators += 1,
            Counter::RawManifest => self.raw_manifests += 1,
            Counter::Refresh => self.refresh_sidecars += 1,
            Counter::CursorOutput => self.cursor_outputs += 1,
            Counter::Transcript => self.transcripts += 1,
            Counter::BreadcrumbDirectory => self.breadcrumb_directories += 1,
            Counter::BreadcrumbFile => self.breadcrumb_files += 1,
            Counter::Tally => self.tally_bodies += 1,
        }
    }

    fn report(&self, errors: &[String]) {
        println!("=== cleanup-implement-logs summary ===");
        println!(
            "  dyn-*-prompt.md deleted:             {}",
            self.dynamic_prompts
        );
        println!(
            "  aggregator-output.txt deleted:       {}",
            self.aggregators
        );
        println!(
            "  scout-round*.json.raw deleted:       {}",
            self.raw_manifests
        );
        println!(
            "  refresh sidecars deleted:            {}",
            self.refresh_sidecars
        );
        println!(
            "  cursor phase/retry files deleted:    {}",
            self.cursor_outputs
        );
        println!(
            "  session-transcript.jsonl upgraded:   {}",
            self.transcripts
        );
        println!(
            "  breadcrumbs dirs consolidated:       {}",
            self.breadcrumb_directories
        );
        println!(
            "  larch-quiet-*.log files removed:     {}",
            self.breadcrumb_files
        );
        println!(
            "  code-review-tally body stripped:     {}",
            self.tally_bodies
        );
        println!("  python/larch-logs/ entries removed:  0");
        println!(
            "  protected/unpublished runs skipped:  {}",
            self.protected_runs
        );
        if !errors.is_empty() {
            println!("  ERRORS ({}):", errors.len());
            for error in errors.iter().take(20) {
                println!("    {error}");
            }
            if errors.len() > 20 {
                println!("    ... and {} more", errors.len() - 20);
            }
        }
    }
}

fn plan_dynamic_prompts(files: &RunFiles, builder: &mut PlanBuilder) {
    for relative in files
        .keys()
        .filter(|relative| file_name_matches(relative, is_dynamic_prompt))
    {
        builder.delete_with_sidecars(relative, files, Counter::DynamicPrompt);
    }
}

fn plan_identical_aggregators(
    root: &RepositoryRoot,
    files: &RunFiles,
    builder: &mut PlanBuilder,
) -> Result<(), String> {
    for relative in files
        .keys()
        .filter(|relative| file_name_is(relative, "aggregator-output.txt"))
    {
        let Some(parent) = relative.parent() else {
            continue;
        };
        let findings = parent.join("findings.md");
        let Some(aggregator_path) = files.get(relative) else {
            continue;
        };
        let Some(findings_path) = files.get(&findings) else {
            continue;
        };
        if read_bytes(root, aggregator_path)? == read_bytes(root, findings_path)? {
            builder.delete_with_sidecars(relative, files, Counter::Aggregator);
        }
    }
    for relative in files.keys().filter(|relative| {
        file_name_is(relative, "aggregator-output.txt.meta")
            || file_name_is(relative, "aggregator-output.txt.json")
    }) {
        let Some(parent) = relative.parent() else {
            continue;
        };
        let primary = parent.join("aggregator-output.txt");
        if !path_exists(&root.path().join(primary))?
            && let Some(path) = files.get(relative)
        {
            builder.delete(path.clone(), Counter::Aggregator);
        }
    }
    Ok(())
}

fn plan_raw_manifests(files: &RunFiles, builder: &mut PlanBuilder) {
    for relative in files
        .keys()
        .filter(|relative| file_name_matches(relative, is_raw_manifest))
    {
        builder.delete_with_sidecars(relative, files, Counter::RawManifest);
    }
}

fn plan_refresh_sidecars(files: &RunFiles, builder: &mut PlanBuilder) {
    for relative in files
        .keys()
        .filter(|relative| file_name_matches(relative, is_refresh_sidecar))
    {
        builder.delete_with_sidecars(relative, files, Counter::Refresh);
    }
}

fn plan_cursor_outputs(files: &RunFiles, builder: &mut PlanBuilder) {
    for relative in files
        .keys()
        .filter(|relative| file_name_matches(relative, is_cursor_output))
    {
        builder.delete_with_sidecars(relative, files, Counter::CursorOutput);
    }
}

fn plan_transcripts(
    root: &RepositoryRoot,
    files: &RunFiles,
    builder: &mut PlanBuilder,
) -> Result<(), String> {
    for relative in files
        .keys()
        .filter(|relative| file_name_is(relative, "session-transcript.jsonl"))
    {
        let Some(path) = files.get(relative) else {
            continue;
        };
        if let Some(text) = upgraded_transcript(root, path)? {
            builder.write(path.clone(), text, Counter::Transcript);
        }
    }
    Ok(())
}

fn plan_breadcrumbs(
    root: &RepositoryRoot,
    files: &RunFiles,
    builder: &mut PlanBuilder,
) -> Result<(), String> {
    let breadcrumbs = root.path().join("breadcrumbs");
    let Ok(metadata) = fs::symlink_metadata(&breadcrumbs) else {
        return Ok(());
    };
    if metadata.file_type().is_symlink() || !metadata.is_dir() {
        return Ok(());
    }
    let quiet_relative = Path::new("breadcrumbs/quiet.log");
    if path_exists(&root.path().join(quiet_relative))? {
        return Ok(());
    }
    let individual: Vec<_> = files
        .iter()
        .filter(|(relative, _path)| {
            relative.parent() == Some(Path::new("breadcrumbs"))
                && file_name_matches(relative, |name| {
                    name.starts_with("larch-quiet-") && has_ascii_suffix(name, b".log")
                })
        })
        .collect();
    if individual.is_empty() {
        return Ok(());
    }
    let mut rendered = String::new();
    for (relative, path) in &individual {
        let Some(name) = relative.file_name().and_then(|name| name.to_str()) else {
            continue;
        };
        let _ = writeln!(rendered, "=== {name} ===");
        rendered.push_str(&read_lossy(root, path)?);
    }
    let quiet = root.path().join(quiet_relative);
    builder.write(quiet, rendered, Counter::BreadcrumbDirectory);
    for (_relative, path) in individual {
        builder.delete(path.clone(), Counter::BreadcrumbFile);
    }
    Ok(())
}

fn plan_tally(
    root: &RepositoryRoot,
    files: &RunFiles,
    builder: &mut PlanBuilder,
) -> Result<(), String> {
    let relative = Path::new("code-review-tally.json");
    let Some(path) = files.get(relative) else {
        return Ok(());
    };
    let text = read_strict(root, path)?;
    let mut value: OrderedJson = serde_json::from_str(&text)
        .map_err(|error| format!("read/parse {}: {error}", path.display()))?;
    if strip_tally_body(&mut value) {
        let mut rendered = serde_json::to_string_pretty(&value)
            .map_err(|error| format!("could not serialize {}: {error}", path.display()))?;
        rendered.push('\n');
        builder.write(path.clone(), rendered, Counter::Tally);
    }
    Ok(())
}

fn file_name_is(relative: &Path, expected: &str) -> bool {
    relative.file_name().and_then(|name| name.to_str()) == Some(expected)
}

fn file_name_matches(relative: &Path, predicate: impl FnOnce(&str) -> bool) -> bool {
    relative
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(predicate)
}

fn is_dynamic_prompt(name: &str) -> bool {
    name.starts_with("dyn-") && name.ends_with("-prompt.md")
}

fn is_raw_manifest(name: &str) -> bool {
    name.starts_with("scout-round") && name.ends_with("-manifest.json.raw")
}

fn is_refresh_sidecar(name: &str) -> bool {
    matches!(
        name,
        "token-report-refresh.json" | "timing-report-refresh.json"
    ) || name.starts_with("session-transcript-refresh.")
}

fn is_cursor_output(name: &str) -> bool {
    if !name.starts_with("cursor-specialist-") || name.contains("ns-retry") {
        return false;
    }
    (name.contains("-output-phase") || has_ascii_suffix(name, b"-output-retry.txt"))
        && has_ascii_suffix(name, b".txt")
}

fn upgraded_transcript(root: &RepositoryRoot, path: &Path) -> Result<Option<String>, String> {
    let raw = read_lossy(root, path)?;
    let lines: Vec<_> = raw.lines().filter(|line| !line.trim().is_empty()).collect();
    let Some(header_line) = lines.first() else {
        return Ok(None);
    };
    let OrderedJson::Object(mut header) = serde_json::from_str::<OrderedJson>(header_line)
        .map_err(|_error| format!("header parse failed: {}", path.display()))?
    else {
        return Err(format!("header parse failed: {}", path.display()));
    };
    if number_is_at_least_two(ordered_field(&header, "v")) {
        return Ok(None);
    }
    ordered_insert(
        &mut header,
        "v",
        OrderedJson::Number(serde_json::Number::from(2)),
    );
    let mut output = vec![compact_json(&OrderedJson::Object(header))?];
    for line in lines.into_iter().skip(1) {
        let Ok(OrderedJson::Object(mut record)) = serde_json::from_str::<OrderedJson>(line) else {
            output.push(line.to_owned());
            continue;
        };
        if ordered_string(&record, "role") == Some("assistant") {
            transform_assistant_blocks(&mut record)?;
        }
        output.push(compact_json(&OrderedJson::Object(record))?);
    }
    Ok(Some(output.join("\n") + "\n"))
}

fn transform_assistant_blocks(record: &mut Vec<(String, OrderedJson)>) -> Result<(), String> {
    let blocks = match ordered_field(record, "blocks") {
        Some(OrderedJson::Array(blocks)) => blocks.clone(),
        Some(_) => return Ok(()),
        None => Vec::new(),
    };
    let mut transformed = Vec::new();
    for block in blocks {
        let OrderedJson::Object(mut block) = block else {
            transformed.push(block);
            continue;
        };
        if ordered_string(&block, "type") != Some("tool_call") {
            transformed.push(OrderedJson::Object(block));
            continue;
        }
        let name = ordered_string(&block, "name").unwrap_or_default();
        let Some(OrderedJson::Object(input)) = ordered_field(&block, "input") else {
            transformed.push(OrderedJson::Object(block));
            continue;
        };
        if input.is_empty()
            || ordered_field(&block, "elided_input_bytes").is_some()
            || ordered_field(input, "input_bytes").is_some()
        {
            transformed.push(OrderedJson::Object(block));
            continue;
        }
        let rendered_input = python_json_dumps(&OrderedJson::Object(input.clone()))
            .map_err(|error| format!("could not serialize tool input: {error}"))?;
        let input_chars = rendered_input.chars().count();
        if matches!(name, "Edit" | "Write" | "NotebookEdit") {
            let file_path = ["file_path", "notebook_path", "path"]
                .iter()
                .find_map(|key| {
                    ordered_field(input, key).filter(|value| ordered_value_is_truthy(value))
                })
                .cloned()
                .unwrap_or_else(|| OrderedJson::String(String::new()));
            ordered_insert(
                &mut block,
                "input",
                OrderedJson::Object(vec![
                    ("file_path".to_owned(), file_path),
                    (
                        "input_bytes".to_owned(),
                        OrderedJson::Number(serde_json::Number::from(input_chars)),
                    ),
                ]),
            );
        } else if input_chars > INPUT_CAP_CHARS {
            block.retain(|(key, _value)| key != "input");
            ordered_insert(
                &mut block,
                "elided_input_bytes",
                OrderedJson::Number(serde_json::Number::from(input_chars)),
            );
        }
        transformed.push(OrderedJson::Object(block));
    }
    ordered_insert(record, "blocks", OrderedJson::Array(transformed));
    Ok(())
}

fn compact_json(value: &OrderedJson) -> Result<String, String> {
    serde_json::to_string(value).map_err(|error| format!("could not serialize transcript: {error}"))
}

fn ordered_string<'a>(object: &'a [(String, OrderedJson)], field: &str) -> Option<&'a str> {
    match ordered_field(object, field) {
        Some(OrderedJson::String(value)) => Some(value),
        _ => None,
    }
}

fn number_is_at_least_two(value: Option<&OrderedJson>) -> bool {
    matches!(value, Some(OrderedJson::Number(number)) if number.as_u64().is_some_and(|value| value >= 2)
        || number.as_i64().is_some_and(|value| value >= 2)
        || number.as_f64().is_some_and(|value| value >= 2.0))
}

fn strip_tally_body(value: &mut OrderedJson) -> bool {
    match value {
        OrderedJson::Object(record) => remove_body(record),
        OrderedJson::Array(records) => records.iter_mut().fold(false, |changed, record| {
            changed
                | match record {
                    OrderedJson::Object(record) => remove_body(record),
                    _ => false,
                }
        }),
        OrderedJson::Null
        | OrderedJson::Bool(_)
        | OrderedJson::Number(_)
        | OrderedJson::String(_) => false,
    }
}

fn remove_body(record: &mut Vec<(String, OrderedJson)>) -> bool {
    let before = record.len();
    record.retain(|(key, _value)| key != "body");
    record.len() != before
}

fn path_exists(path: &Path) -> Result<bool, String> {
    match fs::symlink_metadata(path) {
        Ok(_) => Ok(true),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(error) => Err(format!("could not inspect {}: {error}", path.display())),
    }
}

fn has_ascii_suffix(name: &str, suffix: &[u8]) -> bool {
    name.as_bytes().ends_with(suffix)
}

fn read_bytes(root: &RepositoryRoot, path: &Path) -> Result<Vec<u8>, String> {
    let confined = read_path(root, path)?;
    let mut file = open_confined_read(&confined)
        .map_err(|error| format!("could not read {}: {error}", path.display()))?;
    let mut bytes = Vec::new();
    file.read_to_end(&mut bytes)
        .map_err(|error| format!("could not read {}: {error}", path.display()))?;
    Ok(bytes)
}

fn read_lossy(root: &RepositoryRoot, path: &Path) -> Result<String, String> {
    Ok(String::from_utf8_lossy(&read_bytes(root, path)?).into_owned())
}

fn read_strict(root: &RepositoryRoot, path: &Path) -> Result<String, String> {
    let confined = read_path(root, path)?;
    read_utf8(&confined).map_err(|error| format!("could not read {}: {error}", path.display()))
}

fn read_path(root: &RepositoryRoot, path: &Path) -> Result<ConfinedPath, String> {
    root.confine(path, PathIntent::Read)
        .map_err(|error| format!("refusing to read {}: {error}", path.display()))
}
