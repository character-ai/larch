//! The Rust-owned `report-tokens analyze` command.
//!
//! One invocation synchronizes the run-log corpus once, scans the selected
//! skill's runs, prices each one, renders the report, writes the durable NDJSON
//! cache snapshot and the plot child's input, prints the analysis, and
//! optionally files the analysis issue.
//!
//! Two boundaries are worth naming. Every advertised artifact lives under one
//! temporary root that is removed unless something durable was written into it,
//! so a run that produced nothing leaves nothing behind. And the issue post
//! goes through [`IssueMutationOwner`], which is the same reviewed
//! authorization and outbound-redaction path every other larch issue write
//! uses; the retired Python owner shelled out to `gh issue create` with no gate
//! at all.

use std::{
    collections::BTreeMap,
    env,
    ffi::OsString,
    fs,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_core::{
    GitHubRepositoryRef, IssueCreateRequest, RunLogSlug, redact, redact_secrets,
    report::{
        PricedRun, RunLogSelection, TokenCorpusScan, TokenObservation, TokenObservations,
        TokenScanEvent, assemble_issue_body, cache_ndjson, display_rates, plot_input_json,
        price_run, render_report, title_for_skill,
    },
};

use crate::{
    argparse_compat::parse_with_flags,
    github_repository_resolution::{ambient_repo, repository_ref, validate_repo_slug},
    github_service::{ServiceFailure, with_github_service},
    issue_mutation_support::{authorization_request, authorized, create_with_rollback},
    run_log_publication_commands::synchronized_corpus_root,
};

/// GitHub refuses an issue body over this many bytes.
const BODY_LIMIT: usize = 65_536;
/// `config.EXIT_BAIL`: the analyzer could not finish its work.
const EXIT_BAIL: u8 = 4;
/// Basename of the durable NDJSON snapshot the report advertises.
const CACHE_BASENAME: &str = "report-cache.ndjson";
/// Basename of the plot child's JSON input contract.
const PLOT_INPUT_BASENAME: &str = "plot-input.json";

const OPTIONS: &[&str] = &[
    "--skill",
    "--plot-from",
    "--context-file",
    "--run-id",
    "--trusted-root",
];
const FLAGS: &[&str] = &["--no-issue", "--no-plot", "--operator-invoked"];
const USAGE: &str = "usage: cli.py report-tokens analyze [-h] --skill {design,implement}\n                                    [--no-issue] [--no-plot]";

/// One resolved `report-tokens analyze` command line.
struct Analyze {
    skill: String,
    no_issue: bool,
    no_plot: bool,
    context_file: String,
    run_id: String,
    trusted_root: String,
    operator_invoked: bool,
}

/// Read one environment flag with Python's `env_flag_enabled` truthiness.
fn env_flag_enabled(name: &str) -> bool {
    let value = env::var(name).unwrap_or_default().trim().to_lowercase();
    !matches!(value.as_str(), "" | "0" | "false" | "no")
}

/// Read the operator's out-of-band actual spend, warning on a bad value.
fn actual_spend() -> Option<f64> {
    let raw = env::var("LARCH_REPORT_TOKENS_ACTUAL_SPEND").unwrap_or_default();
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return None;
    }
    trimmed.parse::<f64>().ok().or_else(|| {
        eprintln!("Warning: LARCH_REPORT_TOKENS_ACTUAL_SPEND is not numeric; ignoring");
        None
    })
}

/// Bound how many run directories the scan inspects.
///
/// Returns the refusal message for a value that is not a non-negative integer.
fn scan_limit() -> Result<Option<usize>, String> {
    let raw = env::var("LARCH_REPORT_TOKENS_LIMIT").unwrap_or_default();
    let trimmed = raw.trim().to_owned();
    if trimmed.is_empty() {
        return Ok(None);
    }
    match trimmed.parse::<usize>() {
        Ok(value) if trimmed.chars().all(|c| c.is_ascii_digit()) => {
            Ok((value > 0).then_some(value))
        }
        _invalid => {
            Err("ERROR: LARCH_REPORT_TOKENS_LIMIT must be a non-negative integer".to_owned())
        }
    }
}

fn parse_arguments(arguments: &[OsString]) -> Result<Analyze, (String, u8)> {
    if arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
    {
        println!("{USAGE}");
        return Err((String::new(), 0));
    }
    let parsed = parse_with_flags(arguments, OPTIONS, FLAGS, 0);
    if let Some(error) = parsed.error() {
        return Err((format!("{USAGE}\n{error}"), 2));
    }
    if parsed.value("--plot-from").is_some() {
        return Err((
            format!(
                "{USAGE}\ncli.py report-tokens analyze: error: argument --plot-from: \
--plot-from has been removed; use the synchronized run-log cache instead"
            ),
            2,
        ));
    }
    let text = |name: &str| {
        parsed
            .value(name)
            .and_then(|value| value.to_str())
            .unwrap_or_default()
            .to_owned()
    };
    let skill = text("--skill");
    if !matches!(skill.as_str(), "design" | "implement") {
        let detail = if skill.is_empty() {
            "cli.py report-tokens analyze: error: the following arguments are required: --skill"
                .to_owned()
        } else {
            format!(
                "cli.py report-tokens analyze: error: argument --skill: \
invalid choice: '{skill}' (choose from 'design', 'implement')"
            )
        };
        return Err((format!("{USAGE}\n{detail}"), 2));
    }
    Ok(Analyze {
        skill,
        no_issue: parsed.flag("--no-issue") || env_flag_enabled("LARCH_REPORT_TOKENS_NO_ISSUE"),
        no_plot: parsed.flag("--no-plot") || env_flag_enabled("LARCH_REPORT_TOKENS_NO_PLOT"),
        context_file: text("--context-file"),
        run_id: text("--run-id"),
        trusted_root: text("--trusted-root"),
        operator_invoked: parsed.flag("--operator-invoked"),
    })
}

/// Resolve the repository slug the report links issues against.
///
/// An explicit override must still be a safe `OWNER/REPO` slug; a bad one is
/// fatal, while an unresolvable ambient repository only disables issue links.
fn repo_slug() -> Result<Option<String>, String> {
    let override_value = env::var("LARCH_REPORT_TOKENS_REPO").unwrap_or_default();
    if !override_value.is_empty() {
        if validate_repo_slug(&override_value)
            && !override_value
                .split('/')
                .any(|part| matches!(part, "." | ".."))
        {
            return Ok(Some(override_value));
        }
        return Err("ERROR: LARCH_REPORT_TOKENS_REPO must be a safe OWNER/REPO slug".to_owned());
    }
    let Some(resolved) = ambient_repo() else {
        eprintln!("ERROR: could not resolve GitHub repo owner/name");
        return Ok(None);
    };
    Ok(Some(resolved))
}

/// A temporary root that is removed unless something durable landed in it.
struct TempRoot {
    path: PathBuf,
    preserve: bool,
}

impl TempRoot {
    /// Create one owner-only root, refusing to adopt a directory that exists.
    ///
    /// `create_dir` rather than `create_dir_all` is the point: the root is
    /// removed wholesale on the way out, so adopting a path someone else owns
    /// would make this a deletion of their data.
    fn new() -> Result<Self, String> {
        let base = env::temp_dir().join(format!(
            "larch-report-tokens.{}.{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_or(0, |value| value.as_nanos())
        ));
        fs::create_dir(&base).map_err(|error| format!("ERROR: {error}"))?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt as _;
            fs::set_permissions(&base, fs::Permissions::from_mode(0o700))
                .map_err(|error| format!("ERROR: {error}"))?;
        }
        Ok(Self {
            path: base,
            preserve: false,
        })
    }
}

impl Drop for TempRoot {
    fn drop(&mut self) {
        if !self.preserve {
            let _removed = fs::remove_dir_all(&self.path);
        }
    }
}

/// Print one advertised artifact line, scrubbing secrets but keeping the path.
fn print_artifact(line: &str) {
    println!("{}", redact_secrets(line).text());
}

/// Print one report line through the full path-and-secret redaction.
fn print_redacted(text: &str) {
    println!("{}", redact(text).text());
}

/// Render one extraction or pricing observation as a stderr warning.
///
/// The observations are a Rust addition: the Python scanner dropped an unknown
/// model or usage field silently, and #8086 made them reportable. Surfacing
/// them here is what keeps that promise for the analyzer.
fn observation_line(observation: &TokenObservation) -> String {
    let lane = observation.vendor();
    let scope = if lane.is_empty() {
        String::new()
    } else {
        format!(" ({lane})")
    };
    format!(
        "token scan{scope}: {:?}: {}",
        observation.kind(),
        observation.detail()
    )
}

/// Scan and price every run of one skill, reporting warnings as Python did.
fn priced_runs(
    corpus_root: &Path,
    skill: &str,
    slug: Option<&str>,
    limit: Option<usize>,
) -> Vec<PricedRun> {
    let environment: BTreeMap<String, String> = env::vars().collect();
    let Ok(selected) = RunLogSlug::parse(skill) else {
        eprintln!("Warning: {skill} is not a valid run-log skill slug; scanning nothing");
        return Vec::new();
    };
    let selection = RunLogSelection::for_skill(selected);
    let mut runs = Vec::new();
    for event in TokenCorpusScan::new(corpus_root.to_owned(), selection, slug, limit) {
        match event {
            TokenScanEvent::Warning(warning) => {
                eprintln!("Warning: {}", warning.message());
            }
            TokenScanEvent::Observation(observation) => {
                eprintln!("Warning: {}", observation_line(&observation));
            }
            TokenScanEvent::Record(record) => {
                let mut observations = TokenObservations::default();
                let cost = price_run(&record, &environment, &mut observations);
                for observation in observations.entries() {
                    eprintln!("Warning: {}", observation_line(observation));
                }
                runs.push(PricedRun {
                    record: *record,
                    cost,
                });
            }
        }
    }
    runs
}

/// Print the report body, splitting the advertised cache pointer back out.
fn print_analysis(analysis: &str, plot_input: Option<&Path>, no_plot: bool) {
    if let Some((body, suffix)) = analysis.split_once("\n\nCache JSON:") {
        print_redacted(body);
        print_artifact(&format!("Cache JSON:{suffix}"));
    } else {
        print_redacted(analysis);
    }
    match plot_input {
        Some(path) if !no_plot => {
            print_redacted("\nPlot input written to:");
            print_artifact(&format!("- {}", path.display()));
        }
        _absent if no_plot => print_redacted("\nPlot generation disabled."),
        _absent => print_redacted("\nNo plot input generated."),
    }
}

/// File the analysis issue through the shared mutation owner.
fn post_issue(
    request: &Analyze,
    repository: &GitHubRepositoryRef,
    title: &str,
    body: String,
) -> Result<(), String> {
    let authorization = authorization_request(
        &request.context_file,
        &request.run_id,
        &request.trusted_root,
        request.operator_invoked,
    );
    if let Err(reason) = authorized(&authorization) {
        return Err(format!("ERROR: report issue create refused: {reason}"));
    }
    let outcome = with_github_service(async |service, cancellation| {
        let create = IssueCreateRequest {
            repository: repository.clone(),
            title: title.to_owned(),
            body,
            labels: Vec::new(),
        };
        // A create that fails after GitHub already opened the issue leaves an
        // orphan, so this shares `issue create-one`'s rollback rather than
        // leaving a half-filed report issue behind.
        Ok(create_with_rollback(service, cancellation, &authorization, &create).await)
    });
    match outcome {
        Err(ServiceFailure::Setup(detail) | ServiceFailure::Operation(detail)) => {
            Err(format!("ERROR: report issue create failed: {detail}"))
        }
        Ok(Err((failure, rollback))) => {
            let tail = match rollback {
                None => String::new(),
                Some((orphan, Ok(()))) => format!("; closed orphan issue #{orphan}"),
                Some((orphan, Err(detail))) => format!(
                    "; orphan issue #{orphan} still open: {}",
                    redact(&detail).text()
                ),
            };
            Err(format!(
                "ERROR: report issue create failed: {}{tail}",
                redact(&failure.error.to_string()).text()
            ))
        }
        Ok(Ok(created)) => {
            println!("{}", created.url);
            Ok(())
        }
    }
}

/// Execute the Rust-owned `report-tokens analyze` command.
#[must_use]
pub fn analyze(arguments: &[OsString]) -> ExitCode {
    let request = match parse_arguments(arguments) {
        Ok(request) => request,
        Err((message, code)) => {
            if !message.is_empty() {
                eprintln!("{message}");
            }
            return ExitCode::from(code);
        }
    };
    let mut temp = match TempRoot::new() {
        Ok(root) => root,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(EXIT_BAIL);
        }
    };
    let limit = match scan_limit() {
        Ok(limit) => limit,
        Err(message) => {
            eprintln!("{message}");
            return ExitCode::from(EXIT_BAIL);
        }
    };
    let corpus_root = match synchronized_corpus_root(Path::new(".")) {
        Ok(root) => root,
        Err(message) => {
            eprintln!("ERROR: {message}");
            return ExitCode::from(EXIT_BAIL);
        }
    };
    let slug = if request.no_issue {
        None
    } else {
        match repo_slug() {
            Ok(slug) => slug,
            Err(message) => {
                eprintln!("{message}");
                return ExitCode::from(EXIT_BAIL);
            }
        }
    };
    let log_base = corpus_root.join(&request.skill);
    eprintln!(
        "Scanning {} for larch run logs (--skill={})...",
        log_base.display(),
        request.skill
    );
    let runs = priced_runs(&corpus_root, &request.skill, slug.as_deref(), limit);
    if runs.is_empty() {
        return empty_report(&mut temp);
    }
    report(&request, &mut temp, &runs, slug.as_deref())
}

/// Render, persist, print, and optionally file the report for scanned runs.
fn report(
    request: &Analyze,
    temp: &mut TempRoot,
    runs: &[PricedRun],
    slug: Option<&str>,
) -> ExitCode {
    let spend = actual_spend();
    if spend.is_some() {
        eprintln!(
            "Warning: actual spend was provided; it is printed to stdout but omitted from posted issues unless explicitly enabled."
        );
    }
    let include_actual = env_flag_enabled("LARCH_REPORT_TOKENS_POST_ACTUAL_SPEND");
    let environment: BTreeMap<String, String> = env::vars().collect();
    let rates = display_rates(&environment, "", &mut TokenObservations::default());
    let cache_path = temp.path.join(CACHE_BASENAME);
    let rendered = render_report(
        &request.skill,
        runs,
        &rates,
        spend,
        include_actual,
        &cache_path.display().to_string(),
    );
    let mut durable = false;
    if let Err(error) = fs::write(&cache_path, cache_ndjson(runs)) {
        eprintln!("Warning: could not write the report cache: {error}");
    } else {
        durable = true;
    }
    let plot_input = (!request.no_plot)
        .then(|| write_plot_input(&temp.path, &request.skill, runs))
        .flatten();
    durable = durable || plot_input.is_some();
    temp.preserve = durable;
    print_analysis(&rendered.body, plot_input.as_deref(), request.no_plot);
    if request.no_issue {
        return ExitCode::SUCCESS;
    }
    let Some(slug) = slug else {
        eprintln!(
            "ERROR: could not resolve GitHub repo owner/name; rerun with --no-issue or LARCH_REPORT_TOKENS_REPO"
        );
        return ExitCode::from(EXIT_BAIL);
    };
    let Ok(repository) = repository_ref(slug) else {
        eprintln!(
            "ERROR: could not resolve GitHub repo owner/name; rerun with --no-issue or LARCH_REPORT_TOKENS_REPO"
        );
        return ExitCode::from(EXIT_BAIL);
    };
    let (body, _omitted) = match assemble_issue_body(&rendered.sections, BODY_LIMIT, &request.skill)
    {
        Ok(assembled) => assembled,
        Err(error) => {
            eprintln!("{error}");
            return ExitCode::from(EXIT_BAIL);
        }
    };
    if body.len() > BODY_LIMIT {
        eprintln!("ERROR: report issue body remains over GitHub's 65536-byte limit after trimming");
        return ExitCode::from(EXIT_BAIL);
    }
    let title = title_for_skill(&request.skill, &timestamp());
    if let Err(message) = post_issue(request, &repository, &title, body) {
        eprintln!("{message}");
        return ExitCode::from(EXIT_BAIL);
    }
    ExitCode::SUCCESS
}

/// Render the current UTC minute the way Python's report title did.
fn timestamp() -> String {
    chrono::Utc::now().format("%Y-%m-%d %H:%M UTC").to_string()
}

/// Write the plot child's input, reporting a failure without failing the run.
fn write_plot_input(root: &Path, skill: &str, runs: &[PricedRun]) -> Option<PathBuf> {
    let path = root.join(PLOT_INPUT_BASENAME);
    match fs::write(&path, plot_input_json(skill, runs)) {
        Ok(()) => Some(path),
        Err(error) => {
            eprintln!("Warning: could not write the plot input: {error}");
            None
        }
    }
}

/// Emit the report a corpus with no parseable token report produces.
fn empty_report(temp: &mut TempRoot) -> ExitCode {
    print_redacted("## Report Tokens Analysis");
    println!();
    print_redacted("No parseable token reports found.");
    let cache_path = temp.path.join(CACHE_BASENAME);
    if fs::write(&cache_path, "").is_ok() {
        temp.preserve = true;
    }
    print_artifact(&format!("Cache JSON: {}", cache_path.display()));
    ExitCode::SUCCESS
}
