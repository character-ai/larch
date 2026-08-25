//! Rust-owned `/issue` batch creation, dependency wiring, and recovery.
//!
//! The skill persists two strict `KEY=value` documents: `parse-input` output
//! and the validated Step 5 verdict and edge rows. This command proves both
//! documents and every body before the first mutation, then owns the complete
//! stateful pass: deterministic ordering, create, cached-id edge application,
//! orphan cleanup, descendant skips, dry-run previews, and summary counters.

use std::{
    collections::{BTreeMap, BTreeSet},
    ffi::OsString,
    path::{Path, PathBuf},
    process::ExitCode,
};

use larch_adapters::{ConfinedPath, PathIntent, TemporaryRoot, read_utf8};
use larch_core::{
    BatchCreateItem, BatchCreatePlan, BatchIssueReference, BatchItemVerdict, CreatedIssue,
    GitHubRepositoryRef, emit_kv, wrap_oos_body,
};

use crate::{
    github_repository_resolution::repository_ref,
    issue_create_commands::{
        CreateIssueOutcome, CreateTextSpec, cleanup_created_issue, create_issue_text,
    },
    issue_dependency_commands::{EdgeAuthorization, apply_blocked_by, in_process_edge_with_id},
    issue_mutation_support::{authorization_request, authorized, flat_error},
};

const USAGE: &str = "Usage: issue create-batch --parse-output PATH --edges-file PATH --repo OWNER/REPO [--title-prefix PREFIX] [--label LABEL]... [--operator-invoked | --context-file PATH --run-id ID --trusted-root PATH] [--dry-run]";
const ERROR_CHARS: usize = 500;

/// Run one complete create pass and publish the established `/issue` grammar.
pub fn create_batch(arguments: &[OsString]) -> ExitCode {
    if arguments
        .iter()
        .any(|argument| matches!(argument.to_str(), Some("-h" | "--help")))
    {
        eprintln!("{USAGE}");
        return ExitCode::SUCCESS;
    }
    let options = match BatchOptions::parse(arguments) {
        Ok(options) => options,
        Err(detail) => {
            eprintln!("ERROR: {}", flat_error(&detail, ERROR_CHARS));
            eprintln!("{USAGE}");
            return ExitCode::from(1);
        }
    };
    let (plan, bodies) = match load_batch(&options) {
        Ok(loaded) => loaded,
        Err(detail) => {
            eprintln!("ERROR: {}", flat_error(&detail, ERROR_CHARS));
            return ExitCode::from(1);
        }
    };
    let gateway = LiveBatchGateway::new(&options);
    let mut observer = |message: &str| eprintln!("{message}");
    let report = run_batch(&plan, &bodies, &gateway, &mut observer);
    for (key, value) in report.rows {
        emit_kv(&key, &value);
    }
    emit_kv("ISSUES_CREATED", &report.created.to_string());
    emit_kv("ISSUES_FAILED", &report.failed.to_string());
    emit_kv("ISSUES_DEDUPLICATED", &report.deduplicated.to_string());
    if report.failed == 0 {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}

#[derive(Debug, Default, Eq, PartialEq)]
struct BatchOptions {
    parse_output: String,
    edges_file: String,
    repo: String,
    title_prefix: String,
    labels: Vec<String>,
    context_file: String,
    run_id: String,
    trusted_root: String,
    operator_invoked: bool,
    dry_run: bool,
}

impl BatchOptions {
    fn parse(arguments: &[OsString]) -> Result<Self, String> {
        let mut options = Self::default();
        let mut seen = BTreeSet::new();
        let mut index = 0;
        while index < arguments.len() {
            let token = arguments[index]
                .to_str()
                .ok_or_else(|| "arguments must be UTF-8".to_owned())?;
            match token {
                "--operator-invoked" => {
                    if !seen.insert(token.to_owned()) {
                        return Err(format!("duplicate option {token}"));
                    }
                    options.operator_invoked = true;
                    index += 1;
                    continue;
                }
                "--dry-run" => {
                    if !seen.insert(token.to_owned()) {
                        return Err(format!("duplicate option {token}"));
                    }
                    options.dry_run = true;
                    index += 1;
                    continue;
                }
                "--label" => {
                    let value = arguments
                        .get(index + 1)
                        .and_then(|value| value.to_str())
                        .ok_or_else(|| format!("{token} requires a UTF-8 value"))?;
                    options.labels.push(value.to_owned());
                    index += 2;
                    continue;
                }
                _ => {}
            }
            if !seen.insert(token.to_owned()) {
                return Err(format!("duplicate option {token}"));
            }
            let value = arguments
                .get(index + 1)
                .and_then(|value| value.to_str())
                .ok_or_else(|| format!("{token} requires a UTF-8 value"))?;
            match token {
                "--parse-output" => value.clone_into(&mut options.parse_output),
                "--edges-file" => value.clone_into(&mut options.edges_file),
                "--repo" => value.clone_into(&mut options.repo),
                "--title-prefix" => value.clone_into(&mut options.title_prefix),
                "--context-file" => value.clone_into(&mut options.context_file),
                "--run-id" => value.clone_into(&mut options.run_id),
                "--trusted-root" => value.clone_into(&mut options.trusted_root),
                _ => return Err(format!("unknown option {token}")),
            }
            index += 2;
        }
        if options.parse_output.is_empty()
            || options.edges_file.is_empty()
            || options.repo.is_empty()
        {
            return Err("--parse-output, --edges-file, and --repo are required".to_owned());
        }
        if repository_ref(&options.repo).is_err() {
            return Err("--repo must be OWNER/REPO".to_owned());
        }
        options.validate_authorization()?;
        Ok(options)
    }

    fn validate_authorization(&self) -> Result<(), String> {
        let has_context = !self.context_file.is_empty()
            || !self.run_id.is_empty()
            || !self.trusted_root.is_empty();
        if self.operator_invoked && has_context {
            return Err(
                "--operator-invoked and session authorization options are mutually exclusive"
                    .to_owned(),
            );
        }
        if has_context
            && (self.context_file.is_empty()
                || self.run_id.is_empty()
                || self.trusted_root.is_empty())
        {
            return Err(
                "--context-file, --run-id, and --trusted-root must appear together".to_owned(),
            );
        }
        if self.dry_run {
            return Ok(());
        }
        if !self.operator_invoked && !has_context {
            return Err("missing --operator-invoked or --context-file authorization".to_owned());
        }
        authorized(&authorization_request(
            &self.context_file,
            &self.run_id,
            &self.trusted_root,
            self.operator_invoked,
        ))
        .map_err(|reason| format!("unauthorized-mutation:{reason}"))
    }

    fn edge_authorization(&self) -> EdgeAuthorization<'_> {
        if self.operator_invoked {
            EdgeAuthorization::OperatorInvoked
        } else {
            EdgeAuthorization::Session {
                context_file: &self.context_file,
                run_id: &self.run_id,
                trusted_root: &self.trusted_root,
            }
        }
    }
}

/// The one declared temporary root every batch input must stay below.
struct BatchFiles {
    root: TemporaryRoot,
    declared_root: PathBuf,
}

impl BatchFiles {
    fn from_parse_output(path: &str) -> Result<Self, String> {
        let path = Path::new(path);
        if !path.is_absolute() {
            return Err("--parse-output must be absolute".to_owned());
        }
        let parent = path
            .parent()
            .ok_or_else(|| "--parse-output has no parent".to_owned())?;
        let root = TemporaryRoot::resolve(Some(parent))
            .map_err(|error| format!("invalid batch root: {error}"))?;
        Ok(Self {
            root,
            declared_root: parent.to_path_buf(),
        })
    }

    fn confine(&self, path: &str) -> Result<ConfinedPath, String> {
        let declared = Path::new(path);
        if !declared.is_absolute() {
            return Err(format!("batch input path must be absolute: {path}"));
        }
        let relative = declared
            .strip_prefix(&self.declared_root)
            .map_err(|_| format!("batch input escapes declared root: {path}"))?;
        self.root
            .confine(self.root.path().join(relative), PathIntent::Read)
            .map_err(|error| format!("invalid batch input {path}: {error}"))
    }

    fn read(&self, path: &str) -> Result<String, String> {
        read_utf8(&self.confine(path)?).map_err(|error| format!("cannot read {path}: {error}"))
    }
}

fn load_batch(
    options: &BatchOptions,
) -> Result<(BatchCreatePlan, BTreeMap<usize, String>), String> {
    let files = BatchFiles::from_parse_output(&options.parse_output)?;
    let parse_output = files.read(&options.parse_output)?;
    let decisions = files.read(&options.edges_file)?;
    let plan = BatchCreatePlan::parse(&parse_output, &decisions)
        .map_err(|error| format!("invalid batch plan: {error}"))?;
    let mut bodies = BTreeMap::new();
    for item in plan.items() {
        if !matches!(item.verdict(), BatchItemVerdict::Create) {
            continue;
        }
        let raw = files.read(item.body_file())?;
        let body = if item.is_oos() {
            wrap_oos_body(&raw, item.reviewer(), item.phase(), item.vote_tally())
        } else {
            raw
        };
        let _ = bodies.insert(item.index(), body);
    }
    Ok((plan, bodies))
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum GatewayCreateOutcome {
    DryRun { title: String },
    Created { issue: CreatedIssue, title: String },
}

trait BatchGateway {
    fn create(&self, item: &BatchCreateItem, body: &str) -> Result<GatewayCreateOutcome, String>;
    fn add_blocked_by(
        &self,
        client: u64,
        blocker: u64,
        blocker_id: Option<u64>,
    ) -> Result<(), String>;
    fn cleanup(&self, number: u64) -> Result<(), String>;
}

struct LiveBatchGateway<'options> {
    options: &'options BatchOptions,
    repository: GitHubRepositoryRef,
}

impl<'options> LiveBatchGateway<'options> {
    fn new(options: &'options BatchOptions) -> Self {
        Self {
            options,
            repository: repository_ref(&options.repo).expect("options validate the repository"),
        }
    }
}

impl BatchGateway for LiveBatchGateway<'_> {
    fn create(&self, item: &BatchCreateItem, body: &str) -> Result<GatewayCreateOutcome, String> {
        create_issue_text(&CreateTextSpec {
            title: item.title(),
            title_prefix: &self.options.title_prefix,
            body,
            labels: &self.options.labels,
            repo: &self.options.repo,
            context_file: &self.options.context_file,
            run_id: &self.options.run_id,
            trusted_root: &self.options.trusted_root,
            operator_invoked: self.options.operator_invoked,
            assign_authenticated_user: true,
            dry_run: self.options.dry_run,
        })
        .map(|outcome| match outcome {
            CreateIssueOutcome::DryRun { title } => GatewayCreateOutcome::DryRun { title },
            CreateIssueOutcome::Created { issue, title } => {
                GatewayCreateOutcome::Created { issue, title }
            }
        })
    }

    fn add_blocked_by(
        &self,
        client: u64,
        blocker: u64,
        blocker_id: Option<u64>,
    ) -> Result<(), String> {
        let edge = in_process_edge_with_id(
            self.repository.clone(),
            client,
            blocker,
            blocker_id,
            self.options.edge_authorization(),
        );
        apply_blocked_by(&edge)
    }

    fn cleanup(&self, number: u64) -> Result<(), String> {
        cleanup_created_issue(&self.options.repo, number)
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum ResolvedTarget {
    Remote {
        number: u64,
        url: String,
        id: Option<u64>,
    },
    DryRunItem(usize),
}

struct BatchReport {
    rows: Vec<(String, String)>,
    created: usize,
    failed: usize,
    deduplicated: usize,
}

struct BatchRunState {
    report: BatchReport,
    failed: BTreeSet<usize>,
    targets: BTreeMap<usize, ResolvedTarget>,
}

impl BatchRunState {
    const fn new() -> Self {
        Self {
            report: BatchReport {
                rows: Vec::new(),
                created: 0,
                failed: 0,
                deduplicated: 0,
            },
            failed: BTreeSet::new(),
            targets: BTreeMap::new(),
        }
    }
}

fn run_batch(
    plan: &BatchCreatePlan,
    bodies: &BTreeMap<usize, String>,
    gateway: &dyn BatchGateway,
    observer: &mut dyn FnMut(&str),
) -> BatchReport {
    let mut state = BatchRunState::new();
    for item in plan.items() {
        if matches!(item.verdict(), BatchItemVerdict::Malformed) {
            mark_failed(&mut state.report, &mut state.failed, item, "malformed-item");
        }
    }
    for (position, index) in plan.order().iter().copied().enumerate() {
        if state.failed.contains(&index) {
            continue;
        }
        observer(&format!(
            "▶ /issue: creating item {index}/{} (topo position {})...",
            plan.items().len(),
            position + 1
        ));
        process_item(plan, bodies, gateway, observer, &mut state, index);
    }
    state.report
}

fn process_item(
    plan: &BatchCreatePlan,
    bodies: &BTreeMap<usize, String>,
    gateway: &dyn BatchGateway,
    observer: &mut dyn FnMut(&str),
    state: &mut BatchRunState,
    index: usize,
) {
    let item = plan.item(index).expect("plan order names an item");
    match item.verdict() {
        BatchItemVerdict::Malformed => {}
        BatchItemVerdict::DuplicateExisting { number, url } => {
            duplicate_remote(&mut state.report, item, *number, url);
            let _ = state.targets.insert(
                index,
                ResolvedTarget::Remote {
                    number: *number,
                    url: url.clone(),
                    id: None,
                },
            );
        }
        BatchItemVerdict::DuplicateItem(target) => {
            process_duplicate_item(plan, state, item, *target);
        }
        BatchItemVerdict::Create => {
            process_create_item(plan, bodies, gateway, observer, state, item);
        }
    }
}

fn process_duplicate_item(
    plan: &BatchCreatePlan,
    state: &mut BatchRunState,
    item: &BatchCreateItem,
    target: usize,
) {
    let Some(resolved) = state.targets.get(&target).cloned() else {
        fail_and_propagate(
            &mut state.report,
            &mut state.failed,
            plan,
            item,
            "duplicate target did not resolve",
            "transitive-failure: duplicate target did not resolve",
        );
        return;
    };
    match &resolved {
        ResolvedTarget::Remote { number, url, .. } => {
            duplicate_remote(&mut state.report, item, *number, url);
        }
        ResolvedTarget::DryRunItem(ultimate) => {
            row(&mut state.report, item.index(), "DUPLICATE", "true");
            row(
                &mut state.report,
                item.index(),
                "DUPLICATE_OF_ITEM",
                &ultimate.to_string(),
            );
            row(&mut state.report, item.index(), "TITLE", item.title());
            state.report.deduplicated += 1;
        }
    }
    let _ = state.targets.insert(item.index(), resolved);
}

fn process_create_item(
    plan: &BatchCreatePlan,
    bodies: &BTreeMap<usize, String>,
    gateway: &dyn BatchGateway,
    observer: &mut dyn FnMut(&str),
    state: &mut BatchRunState,
    item: &BatchCreateItem,
) {
    let index = item.index();
    let Some(body) = bodies.get(&index) else {
        fail_and_propagate(
            &mut state.report,
            &mut state.failed,
            plan,
            item,
            "missing preloaded body",
            "transitive-failure: prerequisite body was missing",
        );
        return;
    };
    match gateway.create(item, body) {
        Err(detail) => record_create_failure(plan, observer, state, item, &detail),
        Ok(GatewayCreateOutcome::DryRun { title }) => {
            record_dry_run(plan, state, item, &title);
        }
        Ok(GatewayCreateOutcome::Created {
            issue: created,
            title,
        }) => record_live_create(plan, gateway, observer, state, item, &created, &title),
    }
}

fn record_create_failure(
    plan: &BatchCreatePlan,
    observer: &mut dyn FnMut(&str),
    state: &mut BatchRunState,
    item: &BatchCreateItem,
    detail: &str,
) {
    let index = item.index();
    let detail = flat_error(detail, ERROR_CHARS);
    observer(&format!(
        "**⚠ /issue: create failed for item {index}: {detail}**"
    ));
    fail_and_propagate(
        &mut state.report,
        &mut state.failed,
        plan,
        item,
        &format!("create-failed: {detail}"),
        &format!("transitive-failure: item {index} failed create"),
    );
}

fn record_dry_run(
    plan: &BatchCreatePlan,
    state: &mut BatchRunState,
    item: &BatchCreateItem,
    title: &str,
) {
    let index = item.index();
    row(&mut state.report, index, "DRY_RUN", "true");
    row(&mut state.report, index, "TITLE", title);
    row(
        &mut state.report,
        index,
        "BLOCKED_BY",
        &reference_list(plan.effective_blocked_by(index)),
    );
    row(
        &mut state.report,
        index,
        "BLOCKS",
        &reference_list(item.blocks()),
    );
    row(&mut state.report, index, "DRY_RUN_DEPS", "true");
    state.report.created += 1;
    let _ = state
        .targets
        .insert(index, ResolvedTarget::DryRunItem(index));
}

fn record_live_create(
    plan: &BatchCreatePlan,
    gateway: &dyn BatchGateway,
    observer: &mut dyn FnMut(&str),
    state: &mut BatchRunState,
    item: &BatchCreateItem,
    created: &CreatedIssue,
    title: &str,
) {
    let index = item.index();
    state.report.created += 1;
    row(
        &mut state.report,
        index,
        "NUMBER",
        &created.number.to_string(),
    );
    row(&mut state.report, index, "URL", &created.url);
    row(&mut state.report, index, "ID", &created.id.to_string());
    row(&mut state.report, index, "TITLE", title);
    let _ = state.targets.insert(
        index,
        ResolvedTarget::Remote {
            number: created.number,
            url: created.url.clone(),
            id: Some(created.id),
        },
    );
    match apply_edges(plan, item, created, &state.targets, gateway) {
        Ok(()) => row(
            &mut state.report,
            index,
            "BLOCKER_LINKS_APPLIED",
            &edge_count(plan, item).to_string(),
        ),
        Err((detail, applied)) => {
            record_edge_failure(
                plan,
                gateway,
                observer,
                state,
                item,
                created,
                (&detail, applied),
            );
        }
    }
}

fn record_edge_failure(
    plan: &BatchCreatePlan,
    gateway: &dyn BatchGateway,
    observer: &mut dyn FnMut(&str),
    state: &mut BatchRunState,
    item: &BatchCreateItem,
    created: &CreatedIssue,
    failure: (&str, usize),
) {
    let (detail, applied) = failure;
    let index = item.index();
    if let Err(cleanup) = gateway.cleanup(created.number) {
        observer(&format!(
            "**⚠ /issue: orphan close failed for #{} ({}): {}. Manually close.**",
            created.number,
            created.url,
            flat_error(&cleanup, ERROR_CHARS)
        ));
    }
    row(&mut state.report, index, "FAILED", "true");
    row(&mut state.report, index, "TITLE", item.title());
    row(
        &mut state.report,
        index,
        "ERROR",
        &format!("dep-link-failed: {}", flat_error(detail, ERROR_CHARS)),
    );
    row(
        &mut state.report,
        index,
        "BLOCKER_LINKS_APPLIED",
        &applied.to_string(),
    );
    if state.failed.insert(index) {
        state.report.failed += 1;
    }
    propagate(
        &mut state.report,
        &mut state.failed,
        plan,
        index,
        &format!(
            "transitive-failure: parent #{} (item {index}) failed dep-wiring",
            created.number
        ),
    );
}

fn duplicate_remote(report: &mut BatchReport, item: &BatchCreateItem, number: u64, url: &str) {
    row(report, item.index(), "DUPLICATE", "true");
    row(
        report,
        item.index(),
        "DUPLICATE_OF_NUMBER",
        &number.to_string(),
    );
    row(report, item.index(), "DUPLICATE_OF_URL", url);
    row(report, item.index(), "TITLE", item.title());
    report.deduplicated += 1;
}

fn apply_edges(
    plan: &BatchCreatePlan,
    item: &BatchCreateItem,
    created: &CreatedIssue,
    targets: &BTreeMap<usize, ResolvedTarget>,
    gateway: &dyn BatchGateway,
) -> Result<(), (String, usize)> {
    let mut applied = 0;
    for reference in plan.effective_blocked_by(item.index()) {
        let (number, identifier) = match resolve_reference(plan, *reference, targets) {
            Ok(target) => target,
            Err(detail) => return Err((detail, applied)),
        };
        if let Err(detail) = gateway.add_blocked_by(created.number, number, identifier) {
            return Err((detail, applied));
        }
        applied += 1;
    }
    for reference in item.blocks() {
        let BatchIssueReference::Existing(client) = reference else {
            continue;
        };
        if let Err(detail) = gateway.add_blocked_by(*client, created.number, Some(created.id)) {
            return Err((detail, applied));
        }
        applied += 1;
    }
    Ok(())
}

fn resolve_reference(
    plan: &BatchCreatePlan,
    reference: BatchIssueReference,
    targets: &BTreeMap<usize, ResolvedTarget>,
) -> Result<(u64, Option<u64>), String> {
    match reference {
        BatchIssueReference::Existing(number) => Ok((number, plan.policy_blocker_id(number))),
        BatchIssueReference::Item(index) => match targets.get(&index) {
            Some(ResolvedTarget::Remote { number, id, .. }) => Ok((*number, *id)),
            Some(ResolvedTarget::DryRunItem(_)) => {
                Err(format!("batch item {index} has no live issue id"))
            }
            None => Err(format!(
                "batch item {index} did not resolve before its dependent"
            )),
        },
    }
}

fn edge_count(plan: &BatchCreatePlan, item: &BatchCreateItem) -> usize {
    plan.effective_blocked_by(item.index()).len()
        + item
            .blocks()
            .iter()
            .filter(|reference| matches!(reference, BatchIssueReference::Existing(_)))
            .count()
}

fn fail_and_propagate(
    report: &mut BatchReport,
    failed: &mut BTreeSet<usize>,
    plan: &BatchCreatePlan,
    item: &BatchCreateItem,
    detail: &str,
    descendant_detail: &str,
) {
    mark_failed(report, failed, item, detail);
    propagate(report, failed, plan, item.index(), descendant_detail);
}

fn propagate(
    report: &mut BatchReport,
    failed: &mut BTreeSet<usize>,
    plan: &BatchCreatePlan,
    source: usize,
    detail: &str,
) {
    for descendant in plan.descendants(source) {
        if let Some(item) = plan.item(descendant) {
            mark_failed(report, failed, item, detail);
        }
    }
}

fn mark_failed(
    report: &mut BatchReport,
    failed: &mut BTreeSet<usize>,
    item: &BatchCreateItem,
    detail: &str,
) {
    if !failed.insert(item.index()) {
        return;
    }
    row(report, item.index(), "FAILED", "true");
    row(report, item.index(), "TITLE", item.title());
    row(
        report,
        item.index(),
        "ERROR",
        &flat_error(detail, ERROR_CHARS),
    );
    report.failed += 1;
}

fn row(report: &mut BatchReport, index: usize, suffix: &str, value: &str) {
    report
        .rows
        .push((format!("ISSUE_{index}_{suffix}"), value.to_owned()));
}

fn reference_list(references: &[BatchIssueReference]) -> String {
    references
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>()
        .join(",")
}

#[cfg(test)]
mod tests {
    use std::{cell::RefCell, collections::VecDeque, fs};

    use larch_core::{BatchCreatePlan, CreatedIssue};
    use tempfile::TempDir;

    use super::{
        BatchCreateItem, BatchGateway, BatchOptions, GatewayCreateOutcome, load_batch, run_batch,
    };

    #[derive(Clone, Debug, Eq, PartialEq)]
    enum Call {
        Create(usize),
        Edge(u64, u64, Option<u64>),
        Cleanup(u64),
    }

    #[derive(Default)]
    struct FakeGateway {
        calls: RefCell<Vec<Call>>,
        creates: RefCell<VecDeque<Result<GatewayCreateOutcome, String>>>,
        edges: RefCell<VecDeque<Result<(), String>>>,
        cleanup_error: RefCell<Option<String>>,
    }

    impl FakeGateway {
        fn with_creates(creates: Vec<Result<GatewayCreateOutcome, String>>) -> Self {
            Self {
                creates: RefCell::new(creates.into()),
                ..Self::default()
            }
        }
    }

    impl BatchGateway for FakeGateway {
        fn create(
            &self,
            item: &BatchCreateItem,
            _body: &str,
        ) -> Result<GatewayCreateOutcome, String> {
            self.calls.borrow_mut().push(Call::Create(item.index()));
            self.creates
                .borrow_mut()
                .pop_front()
                .expect("fixture create")
        }

        fn add_blocked_by(
            &self,
            client: u64,
            blocker: u64,
            blocker_id: Option<u64>,
        ) -> Result<(), String> {
            self.calls
                .borrow_mut()
                .push(Call::Edge(client, blocker, blocker_id));
            self.edges.borrow_mut().pop_front().unwrap_or(Ok(()))
        }

        fn cleanup(&self, number: u64) -> Result<(), String> {
            self.calls.borrow_mut().push(Call::Cleanup(number));
            self.cleanup_error.borrow().clone().map_or(Ok(()), Err)
        }
    }

    fn created(index: usize) -> GatewayCreateOutcome {
        GatewayCreateOutcome::Created {
            issue: CreatedIssue {
                number: 100 + u64::try_from(index).expect("index"),
                url: format!("https://example.test/issues/{}", 100 + index),
                id: 9000 + u64::try_from(index).expect("index"),
            },
            title: format!("Item {index}"),
        }
    }

    fn plan(decisions: &str) -> BatchCreatePlan {
        BatchCreatePlan::parse(
            concat!(
                "ITEM_1_TITLE=One\n",
                "ITEM_1_BODY_FILE=/tmp/one\n",
                "ITEM_2_TITLE=Two\n",
                "ITEM_2_BODY_FILE=/tmp/two\n",
                "ITEM_3_TITLE=Three\n",
                "ITEM_3_BODY_FILE=/tmp/three\n",
                "ITEMS_TOTAL=3\n",
            ),
            decisions,
        )
        .expect("plan")
    }

    fn bodies() -> std::collections::BTreeMap<usize, String> {
        [(1, "one"), (2, "two"), (3, "three")]
            .into_iter()
            .map(|(index, body)| (index, body.to_owned()))
            .collect()
    }

    #[test]
    fn dependency_failure_rolls_back_skips_descendants_and_continues_independent_items() {
        let plan = plan(concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_1_BLOCKED_BY=77\n",
            "ITEM_2_VERDICT=CREATE\n",
            "ITEM_2_BLOCKED_BY=ITEM_1\n",
            "ITEM_3_VERDICT=CREATE\n",
        ));
        let gateway = FakeGateway::with_creates(vec![Ok(created(1)), Ok(created(3))]);
        gateway
            .edges
            .borrow_mut()
            .push_back(Err("dependency refused".to_owned()));
        let mut events = Vec::new();
        let report = run_batch(&plan, &bodies(), &gateway, &mut |line| {
            events.push(line.to_owned())
        });
        assert_eq!(report.created, 2, "rolled-back creates still count");
        assert_eq!(report.failed, 2, "source and descendant fail");
        assert_eq!(
            gateway.calls.into_inner(),
            [
                Call::Create(1),
                Call::Edge(101, 77, None),
                Call::Cleanup(101),
                Call::Create(3),
            ]
        );
        assert!(report.rows.contains(&(
            "ISSUE_2_ERROR".to_owned(),
            "transitive-failure: parent #101 (item 1) failed dep-wiring".to_owned()
        )));
    }

    #[test]
    fn create_failure_propagates_transitively_without_aborting_a_sibling() {
        let plan = plan(concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_2_VERDICT=CREATE\n",
            "ITEM_2_BLOCKED_BY=ITEM_1\n",
            "ITEM_3_VERDICT=CREATE\n",
        ));
        let gateway =
            FakeGateway::with_creates(vec![Err("create denied".to_owned()), Ok(created(3))]);
        let report = run_batch(&plan, &bodies(), &gateway, &mut |_| {});
        assert_eq!(report.created, 1);
        assert_eq!(report.failed, 2);
        assert_eq!(
            gateway.calls.into_inner(),
            [Call::Create(1), Call::Create(3)]
        );
    }

    #[test]
    fn dry_run_emits_no_ids_and_makes_no_edge_or_cleanup_calls() {
        let plan = plan(concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_1_BLOCKED_BY=42\n",
            "ITEM_2_VERDICT=DUPLICATE\n",
            "ITEM_2_DUPLICATE_OF_ITEM=1\n",
            "ITEM_3_VERDICT=CREATE\n",
        ));
        let gateway = FakeGateway::with_creates(vec![
            Ok(GatewayCreateOutcome::DryRun {
                title: "One".to_owned(),
            }),
            Ok(GatewayCreateOutcome::DryRun {
                title: "Three".to_owned(),
            }),
        ]);
        let report = run_batch(&plan, &bodies(), &gateway, &mut |_| {});
        assert_eq!(report.created, 2);
        assert_eq!(report.deduplicated, 1);
        assert!(report.rows.iter().all(|(key, _)| !key.ends_with("_ID")));
        assert_eq!(
            gateway.calls.into_inner(),
            [Call::Create(1), Call::Create(3)]
        );
    }

    #[test]
    fn policy_blocker_uses_the_cached_node_id() {
        let plan = plan(concat!(
            "ITEM_1_VERDICT=CREATE\n",
            "ITEM_1_BLOCKED_BY=42\n",
            "ITEM_2_VERDICT=CREATE\n",
            "ITEM_3_VERDICT=CREATE\n",
            "BLOCKED_BY_ISSUE=42\n",
            "BLOCKED_BY_ISSUE_ID=9042\n",
        ));
        let gateway =
            FakeGateway::with_creates(vec![Ok(created(1)), Ok(created(2)), Ok(created(3))]);
        let report = run_batch(&plan, &bodies(), &gateway, &mut |_| {});
        assert_eq!(report.failed, 0);
        assert!(
            gateway
                .calls
                .into_inner()
                .contains(&Call::Edge(101, 42, Some(9042)))
        );
    }

    #[test]
    fn load_preflights_create_bodies_and_confines_every_batch_input() {
        let directory = TempDir::new().expect("temporary directory");
        let root = fs::canonicalize(directory.path()).expect("canonical root");
        let body = root.join("body.txt");
        fs::write(&body, "Create body.").expect("body");
        let parse_output = root.join("parse.env");
        fs::write(
            &parse_output,
            format!(
                "ITEM_1_TITLE=One\nITEM_1_BODY_FILE={}\nITEM_2_TITLE=Two\nITEM_2_BODY_FILE={}\nITEMS_TOTAL=2\n",
                body.display(),
                root.join("duplicate-body-does-not-need-to-exist").display()
            ),
        )
        .expect("parse output");
        let decisions = root.join("edges.env");
        fs::write(
            &decisions,
            "ITEM_1_VERDICT=CREATE\nITEM_2_VERDICT=DUPLICATE\nITEM_2_DUPLICATE_OF=42\nITEM_2_DUPLICATE_OF_URL=https://example.test/issues/42\n",
        )
        .expect("decisions");
        let mut options = BatchOptions {
            parse_output: parse_output.to_string_lossy().into_owned(),
            edges_file: decisions.to_string_lossy().into_owned(),
            repo: "owner/repo".to_owned(),
            operator_invoked: true,
            ..BatchOptions::default()
        };

        let (_, bodies) = load_batch(&options).expect("preloads create body");
        assert_eq!(
            bodies,
            [(1, "Create body.".to_owned())].into_iter().collect()
        );

        let outside = TempDir::new().expect("outside directory");
        let outside_edges = outside.path().join("edges.env");
        fs::write(&outside_edges, "ITEM_1_VERDICT=CREATE\n").expect("outside edges");
        options.edges_file = outside_edges.to_string_lossy().into_owned();
        assert!(
            load_batch(&options)
                .expect_err("outside input refuses")
                .contains("escapes declared root")
        );
    }
}
