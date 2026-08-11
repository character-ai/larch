use std::{collections::BTreeMap, env, process::ExitCode, time::Duration};

use crate::{github_repository_resolution, test_shards};
use chrono::Utc;
use clap::{Args, ValueEnum};
use larch_adapters::{
    AddRequest, BranchMutationRequest, CheckoutRequest, CommitMessage, CommitRequest, FetchRequest,
    GitCli, GitCliPolicy, GitPath, GitRef, GitRefspec, GitRemote, GixRepository, PushRequest,
    RepositoryRoot, RestoreRequest, TokioProcessRunner, atomic_write_utf8,
    github::{OctocrabGitHubService, PullRequestSpec},
    read_utf8,
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    CiTimingRunSelection, GitHubActionsService, GitHubMutationOutcome, GitHubRepositoryRef, Head,
    RepositoryRead, Revision, StatusOptions, WorkflowDispatchRequest, WorkflowRunFilters,
    collect_harness_timing, collect_job_timing, collect_pytest_timing, plan_json, verify_json,
};
use serde::Deserialize;
use serde_json::json;
const MAKEFILE: &str = "Makefile";
const ASSIGNMENTS: &str = "python/shard-assignments.json";
const MAIN: &str = "main";
const DEFAULT_WORKFLOW: &str = "ci.yaml";
const WORKFLOW_POLL: Duration = Duration::from_secs(15);
const WORKFLOW_WAIT_LIMIT: Duration = Duration::from_secs(30 * 60);
const WORKFLOW_LIST_LIMIT: usize = 20;
#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
enum RebalanceKind {
    Harness,
    Python,
    All,
}
impl RebalanceKind {
    const fn includes_harness(self) -> bool {
        matches!(self, Self::Harness | Self::All)
    }
    const fn includes_python(self) -> bool {
        matches!(self, Self::Python | Self::All)
    }
    const fn wire(self) -> &'static str {
        match self {
            Self::Harness => "harness",
            Self::Python => "python",
            Self::All => "all",
        }
    }
    const fn commit_label(self) -> &'static str {
        match self {
            Self::Harness => "harness",
            Self::Python => "python",
            Self::All => "harness+python",
        }
    }
}
#[derive(Clone, Debug)]
struct CompileAffinityArgument {
    target: String,
    group: String,
    setup_seconds: f64,
}
#[derive(Args, Clone, Debug)]
pub struct RebalanceRunArguments {
    #[arg(long, value_enum, default_value_t = RebalanceKind::All)]
    kind: RebalanceKind,
    #[arg(long, value_parser = crate::parse_repository)]
    repo: Option<GitHubRepositoryRef>,
    #[arg(long, default_value_t = 5, value_parser = parse_run_count)]
    n_runs: usize,
    #[arg(long, default_value = "rebalance-shards", value_parser = parse_branch_prefix)]
    branch_prefix: String,
    #[arg(long, default_value_t = 3, value_parser = parse_run_count)]
    n_verify_runs: usize,
    #[arg(long, value_parser = parse_positive_u32)]
    n_python_shards: Option<u32>,
    #[arg(long, default_value_t = 15.0, value_parser = parse_positive_f64)]
    balance_threshold: f64,
    #[arg(long, default_value_t = 300.0, value_parser = parse_positive_f64)]
    max_shard_wall_clock: f64,
    #[arg(long, value_parser = parse_experiment_note)]
    experimental_wall_clock_override: Option<String>,
    #[arg(long, value_parser = parse_compile_affinity)]
    compile_affinity: Vec<CompileAffinityArgument>,
    #[arg(long, default_value = DEFAULT_WORKFLOW, value_parser = parse_selector)]
    workflow: String,
    #[arg(long, default_value = MAIN, value_parser = parse_selector)]
    baseline_branch: String,
    #[arg(long)]
    dry_run: bool,
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Artifact {
    Makefile,
    Assignments,
}
impl Artifact {
    const fn path(self) -> &'static str {
        match self {
            Self::Makefile => MAKEFILE,
            Self::Assignments => ASSIGNMENTS,
        }
    }
}
#[derive(Clone, Debug)]
struct HarnessPlan {
    current_shards: BTreeMap<u32, Vec<String>>,
    proposed_shards: BTreeMap<u32, Vec<String>>,
    baseline_slowest_wall_clock: f64,
    baseline_runner_seconds: f64,
    approved_slowest_wall_clock: f64,
    changed: bool,
}
#[derive(Clone, Debug)]
struct PythonPlan {
    assignments: BTreeMap<String, u32>,
    shard_count: u32,
    changed: bool,
}
#[derive(Clone, Debug)]
struct PreparedPlan {
    kind: RebalanceKind,
    repository: GitHubRepositoryRef,
    harness: Option<HarnessPlan>,
    python: Option<PythonPlan>,
    decision: String,
}
impl PreparedPlan {
    fn is_noop(&self) -> bool {
        self.harness.as_ref().is_none_or(|plan| !plan.changed)
            && self.python.as_ref().is_none_or(|plan| !plan.changed)
    }
}
#[derive(Clone, Debug)]
struct PublishedPullRequest {
    number: u64,
    url: String,
    branch: String,
}
trait WorkflowPort {
    fn prepare(&mut self, arguments: &RebalanceRunArguments) -> Result<PreparedPlan, String>;
    fn write_candidates(&mut self, plan: &PreparedPlan) -> Result<Vec<Artifact>, String>;
    fn publish(
        &mut self,
        arguments: &RebalanceRunArguments,
        plan: &PreparedPlan,
        artifacts: &[Artifact],
        branch: &str,
    ) -> Result<PublishedPullRequest, String>;
    fn recover_publish_failure(
        &mut self,
        artifacts: &[Artifact],
        branch: &str,
    ) -> Result<(), String>;
    fn verify(
        &mut self,
        arguments: &RebalanceRunArguments,
        plan: &PreparedPlan,
        pull_request: &PublishedPullRequest,
    ) -> Result<(), String>;
}
pub fn run(arguments: &RebalanceRunArguments) -> Result<ExitCode, String> {
    let mut services = ProductionWorkflow::new()?;
    execute(&mut services, arguments)
}

fn execute<P: WorkflowPort>(
    services: &mut P,
    arguments: &RebalanceRunArguments,
) -> Result<ExitCode, String> {
    let plan = services.prepare(arguments)?;
    println!(
        "Repo   : {}/{}",
        plan.repository.owner(),
        plan.repository.name()
    );
    println!("Kind   : {}", plan.kind.wire());
    println!("Plan   : {}", plan.decision);
    if plan.is_noop() {
        println!("No shard artifact changes needed; exiting before branch creation.");
        return Ok(ExitCode::SUCCESS);
    }
    if arguments.dry_run {
        println!(
            "Dry run complete; no candidate artifact, branch, push, PR, or workflow was created."
        );
        return Ok(ExitCode::SUCCESS);
    }
    let artifacts = services.write_candidates(&plan)?;
    let branch = branch_name(&arguments.branch_prefix);
    let pull_request = match services.publish(arguments, &plan, &artifacts, &branch) {
        Ok(pull_request) => pull_request,
        Err(error) => {
            let recovery = services.recover_publish_failure(&artifacts, &branch);
            return match recovery {
                Ok(()) => Err(error),
                Err(recovery_error) => Err(format!("{error}; rollback failed: {recovery_error}")),
            };
        }
    };
    if let Err(error) = services.verify(arguments, &plan, &pull_request) {
        return Err(format!(
            "{error}; PR remains available at {}",
            pull_request.url
        ));
    }
    println!(
        "PR #{} is ready for review: {}",
        pull_request.number, pull_request.url
    );
    println!("Merge remains operator-owned.");
    Ok(ExitCode::SUCCESS)
}

struct ProductionWorkflow {
    root: RepositoryRoot,
    repository: GixRepository,
    runtime: LarchRuntime,
    cancellation: Cancellation,
    runner: TokioProcessRunner,
    github: OctocrabGitHubService,
    git_policy: GitCliPolicy,
    created_branch: Option<String>,
    pushed_branch: Option<String>,
}

impl ProductionWorkflow {
    fn new() -> Result<Self, String> {
        let cwd = env::current_dir()
            .map_err(|error| format!("cannot resolve working directory: {error}"))?;
        let root = RepositoryRoot::resolve(Some(&cwd))
            .map_err(|error| format!("cannot resolve repository root: {error}"))?;
        let repository = GixRepository::discover(root.path())
            .map_err(|error| format!("cannot open repository: {error}"))?;
        let runtime = LarchRuntime::new()
            .map_err(|error| format!("cannot initialize larch runtime: {error}"))?;
        let cancellation = Cancellation::new();
        let runner = TokioProcessRunner::default();
        let github = runtime
            .block_on(OctocrabGitHubService::from_gh(
                &runner,
                root.path(),
                &cancellation,
            ))
            .map_err(|error| format!("cannot initialize GitHub service: {error}"))?;
        let git_policy = GitCliPolicy::new(root.path().to_path_buf())
            .map_err(|error| format!("cannot initialize Git owner: {error}"))?;
        Ok(Self {
            root,
            repository,
            runtime,
            cancellation,
            runner,
            github,
            git_policy,
            created_branch: None,
            pushed_branch: None,
        })
    }

    fn git(&self) -> GitCli<'_, TokioProcessRunner> {
        GitCli::new(&self.runner, self.git_policy.clone())
    }

    fn repository_for(arguments: &RebalanceRunArguments) -> Result<GitHubRepositoryRef, String> {
        if let Some(repository) = &arguments.repo {
            return Ok(repository.clone());
        }
        let slug = github_repository_resolution::remote_slug("origin")
            .ok_or_else(|| "origin repository could not be resolved".to_owned())?;
        github_repository_resolution::repository_ref(&slug)
            .map_err(|()| "origin repository could not be resolved".to_owned())
    }

    fn fetch_and_require_immutable_main(&self) -> Result<(), String> {
        let remote = GitRemote::new("origin").map_err(|error| error.to_string())?;
        let refspec = GitRefspec::new("refs/heads/main:refs/remotes/origin/main")
            .map_err(|error| error.to_string())?;
        self.runtime
            .block_on(self.git().fetch(
                FetchRequest {
                    remote,
                    refspec: Some(refspec),
                    quiet: true,
                    no_tags: true,
                },
                &self.cancellation,
            ))
            .map_err(|error| format!("cannot refresh origin/main: {error}"))?;
        let head = self.repository.head().map_err(|error| error.to_string())?;
        let Head::Symbolic { name, target } = head else {
            return Err("immutable-main evidence requires a symbolic main checkout".to_owned());
        };
        if name.as_bytes() != b"refs/heads/main" {
            return Err("immutable-main evidence requires the local main branch".to_owned());
        }
        let local = self.resolve(MAIN)?;
        let origin = self.resolve("origin/main")?;
        if target != local || local != origin {
            return Err(
                "immutable-main evidence requires HEAD, main, and origin/main to match".to_owned(),
            );
        }
        let status = self
            .repository
            .local_status(&StatusOptions::default())
            .map_err(|error| format!("cannot inspect repository state: {error}"))?;
        if status.is_dirty() {
            return Err("refusing to rebalance from a dirty repository".to_owned());
        }
        let references = self
            .repository
            .references()
            .map_err(|error| error.to_string())?;
        if references
            .iter()
            .any(|reference| reference.name.as_bytes() == b"refs/stash")
        {
            return Err("refusing to rebalance while git stash is nonempty".to_owned());
        }
        Ok(())
    }

    fn resolve(&self, revision: &str) -> Result<larch_core::ObjectId, String> {
        self.repository
            .resolve_revision(&Revision::new(revision.as_bytes()))
            .map_err(|_| format!("immutable-main evidence is missing {revision}"))
    }

    fn makefile(
        &self,
        intent: larch_adapters::PathIntent,
    ) -> Result<larch_adapters::ConfinedPath, String> {
        self.root
            .confine(MAKEFILE, intent)
            .map_err(|error| format!("cannot safely access {MAKEFILE}: {error}"))
    }

    fn collect_plan(
        &self,
        arguments: &RebalanceRunArguments,
        repository: &GitHubRepositoryRef,
    ) -> Result<PreparedPlan, String> {
        let current_harness = arguments
            .kind
            .includes_harness()
            .then(|| {
                self.makefile(larch_adapters::PathIntent::Read)
                    .and_then(|path| test_shards::read_makefile_shard_map(&path))
            })
            .transpose()?;
        let current_assignments = arguments
            .kind
            .includes_python()
            .then(|| self.read_assignments())
            .transpose()?;
        let (harness_pair, pytest_timing) = self.runtime.block_on(async {
            let selection = CiTimingRunSelection::Recent {
                branch: arguments.baseline_branch.clone(),
                workflow: arguments.workflow.clone(),
                limit: arguments.n_runs,
            };
            let harness = if let Some(shards) = &current_harness {
                let targets = shards.values().flatten().cloned().collect::<Vec<_>>();
                let timing = collect_harness_timing(
                    &self.github,
                    repository,
                    &selection,
                    &targets,
                    &self.cancellation,
                )
                .await
                .map_err(|error| error.to_string())?;
                let jobs = collect_job_timing(
                    &self.github,
                    repository,
                    &timing.sampled_run_ids,
                    &self.cancellation,
                )
                .await
                .map_err(|error| error.to_string())?;
                Ok::<_, String>(Some((timing, jobs)))
            } else {
                Ok(None)
            }?;
            let pytest = if current_assignments.is_some() {
                Some(
                    collect_pytest_timing(&self.github, repository, &selection, &self.cancellation)
                        .await
                        .map_err(|error| error.to_string())?,
                )
            } else {
                None
            };
            Ok::<_, String>((harness, pytest))
        })?;
        let (harness_timing, jobs_timing) =
            harness_pair.map_or((None, None), |(harness, jobs)| (Some(harness), Some(jobs)));
        let request = plan_request(
            arguments,
            current_harness.as_ref(),
            harness_timing.as_ref(),
            jobs_timing.as_ref(),
            current_assignments.as_ref(),
            pytest_timing.as_ref(),
        )?;
        let result = plan_json(&request)?;
        let response: PlanResponse = serde_json::from_str(&result.json)
            .map_err(|error| format!("invalid rebalance-tests plan response: {error}"))?;
        if !result.success || response.decision == "rejected" {
            return Err(format_plan_rejection(&response));
        }
        response.into_prepared(arguments.kind, repository.clone(), current_harness)
    }

    fn read_assignments(&self) -> Result<BTreeMap<String, u32>, String> {
        let path = self
            .root
            .confine(ASSIGNMENTS, larch_adapters::PathIntent::Read)
            .map_err(|error| format!("cannot safely read {ASSIGNMENTS}: {error}"))?;
        serde_json::from_str(&read_utf8(&path).map_err(|error| error.to_string())?)
            .map_err(|error| format!("invalid {ASSIGNMENTS}: {error}"))
    }

    fn restore_artifacts(&self, artifacts: &[Artifact]) -> Result<(), String> {
        if artifacts.is_empty() {
            return Ok(());
        }
        let paths = artifact_git_paths(artifacts)?;
        self.runtime
            .block_on(async {
                let git = self.git();
                git.restore(
                    RestoreRequest {
                        staged: true,
                        paths: paths.clone(),
                    },
                    &self.cancellation,
                )
                .await
                .map_err(|error| error.to_string())?;
                git.checkout(
                    CheckoutRequest::Paths {
                        ours: false,
                        theirs: false,
                        paths,
                    },
                    &self.cancellation,
                )
                .await
                .map_err(|error| error.to_string())
            })
            .map(|_| ())
            .map_err(|error| format!("cannot restore candidate artifacts: {error}"))
    }

    fn rollback_write_failure(&self, artifacts: &[Artifact], error: String) -> String {
        match self.restore_artifacts(artifacts) {
            Ok(()) => error,
            Err(rollback) => format!("{error}; rollback failed: {rollback}"),
        }
    }

    fn checkout_main(&self) -> Result<(), String> {
        self.runtime
            .block_on(self.git().checkout(
                CheckoutRequest::Branch {
                    create: false,
                    force: false,
                    name: GitRef::new(MAIN).map_err(|error| error.to_string())?,
                    start_point: None,
                },
                &self.cancellation,
            ))
            .map(|_| ())
            .map_err(|error| format!("cannot restore the main checkout: {error}"))
    }
    fn remove_created_branch(&mut self, branch: &str) -> Result<(), String> {
        if self.created_branch.as_deref() != Some(branch) {
            return Ok(());
        }
        self.runtime
            .block_on(self.git().branch_mutation(
                BranchMutationRequest::Delete {
                    force: true,
                    name: GitRef::new(branch).map_err(|error| error.to_string())?,
                },
                &self.cancellation,
            ))
            .map_err(|error| format!("cannot remove failed local branch {branch}: {error}"))?;
        self.created_branch = None;
        Ok(())
    }
    fn push_branch(&mut self, branch: &str) -> Result<(), String> {
        // A transport error can arrive after the remote accepts this ref.
        self.pushed_branch = Some(branch.to_owned());
        let git = self.git();
        self.runtime
            .block_on(
                git.push(
                    PushRequest {
                        remote: GitRemote::new("origin").map_err(|error| error.to_string())?,
                        refspec: GitRefspec::new(format!(
                            "refs/heads/{branch}:refs/heads/{branch}"
                        ))
                        .map_err(|error| error.to_string())?,
                        force_with_lease: None,
                        set_upstream: true,
                    },
                    &self.cancellation,
                ),
            )
            .map(|_| ())
            .map_err(|error| format!("cannot push rebalance branch: {error}"))
    }
    fn dispatch_and_wait(
        &self,
        repository: &GitHubRepositoryRef,
        workflow: &str,
        branch: &str,
        n_runs: usize,
    ) -> Result<Vec<u64>, String> {
        self.runtime.block_on(async {
            let mut seen = Vec::new();
            let mut completed = Vec::new();
            for _ in 0..n_runs {
                let mut before = list_workflow_ids(
                    &self.github,
                    repository,
                    workflow,
                    branch,
                    &self.cancellation,
                )
                .await?;
                before.extend(&seen);
                before.sort_unstable();
                before.dedup();
                let outcome = self
                    .github
                    .dispatch_workflow(
                        &WorkflowDispatchRequest {
                            repository: repository.clone(),
                            workflow: workflow.to_owned(),
                            git_reference: branch.to_owned(),
                        },
                        &self.cancellation,
                    )
                    .await
                    .map_err(|error| format!("workflow dispatch failed: {error}"))?;
                if outcome == GitHubMutationOutcome::Ambiguous {
                    return Err("workflow dispatch outcome is ambiguous; refusing to guess a verification run".to_owned());
                }
                let run = wait_for_completed_run(
                    &self.github,
                    repository,
                    workflow,
                    branch,
                    &before,
                    &self.cancellation,
                )
                .await?;
                seen.push(run);
                completed.push(run);
            }
            Ok(completed)
        })
    }
}
impl WorkflowPort for ProductionWorkflow {
    fn prepare(&mut self, arguments: &RebalanceRunArguments) -> Result<PreparedPlan, String> {
        self.fetch_and_require_immutable_main()?;
        let repository = Self::repository_for(arguments)?;
        self.collect_plan(arguments, &repository)
    }

    fn write_candidates(&mut self, plan: &PreparedPlan) -> Result<Vec<Artifact>, String> {
        let mut written = Vec::new();
        if let Some(harness) = &plan.harness
            && harness.changed
        {
            test_shards::validate_rebalanced_harness_shards(
                &harness.current_shards,
                &harness.proposed_shards,
            )?;
            let makefile = self.makefile(larch_adapters::PathIntent::Write)?;
            written.push(Artifact::Makefile);
            if let Err(error) =
                test_shards::write_makefile_shard_map(&makefile, &harness.proposed_shards)
            {
                return Err(self.rollback_write_failure(
                    &written,
                    format!("cannot write {MAKEFILE}: {error}"),
                ));
            }
        }
        if let Some(python) = &plan.python
            && python.changed
        {
            let target = self
                .root
                .confine(ASSIGNMENTS, larch_adapters::PathIntent::Write)
                .map_err(|error| {
                    self.rollback_write_failure(
                        &written,
                        format!("cannot safely write {ASSIGNMENTS}: {error}"),
                    )
                })?;
            written.push(Artifact::Assignments);
            if let Err(error) =
                atomic_write_utf8(&target, &assignments_json(&python.assignments), 0o644)
            {
                return Err(self.rollback_write_failure(
                    &written,
                    format!("cannot write {ASSIGNMENTS}: {error}"),
                ));
            }
        }
        Ok(written)
    }
    fn publish(
        &mut self,
        arguments: &RebalanceRunArguments,
        plan: &PreparedPlan,
        artifacts: &[Artifact],
        branch: &str,
    ) -> Result<PublishedPullRequest, String> {
        let branch_ref = GitRef::new(branch).map_err(|error| error.to_string())?;
        let paths = artifact_git_paths(artifacts)?;
        self.runtime.block_on(async {
            let git = self.git();
            git.branch_mutation(
                BranchMutationRequest::Create {
                    force: false,
                    name: branch_ref.clone(),
                    start_point: Some(GitRef::new("HEAD").map_err(|error| error.to_string())?),
                },
                &self.cancellation,
            )
            .await
            .map_err(|error| format!("cannot create rebalance branch: {error}"))
        })?;
        self.created_branch = Some(branch.to_owned());
        self.runtime.block_on(async {
            let git = self.git();
            git.checkout(
                CheckoutRequest::Branch {
                    create: false,
                    force: false,
                    name: branch_ref.clone(),
                    start_point: None,
                },
                &self.cancellation,
            )
            .await
            .map_err(|error| format!("cannot checkout rebalance branch: {error}"))?;
            git.add(
                AddRequest {
                    all: false,
                    force: false,
                    pathspec_from_file: None,
                    pathspec_file_nul: false,
                    paths,
                },
                &self.cancellation,
            )
            .await
            .map_err(|error| format!("cannot stage rebalance artifacts: {error}"))?;
            git.commit(
                CommitRequest {
                    message: Some(CommitMessage::Literal(
                        commit_subject(arguments.kind).into(),
                    )),
                    amend: false,
                    no_edit: false,
                    allow_empty: false,
                    only: false,
                    pathspec_from_file: None,
                    pathspec_file_nul: false,
                    paths: Vec::new(),
                },
                &self.cancellation,
            )
            .await
            .map_err(|error| format!("cannot commit rebalance artifacts: {error}"))
        })?;
        self.push_branch(branch)?;
        self.checkout_main()?;
        let body = pull_request_body(arguments, plan);
        let created = self
            .runtime
            .block_on(self.github.create_pull_request(
                &self.cancellation,
                &PullRequestSpec {
                    owner: plan.repository.owner(),
                    repo: plan.repository.name(),
                    head: branch,
                    base: MAIN,
                    title: &commit_subject(arguments.kind),
                    body: &body,
                    draft: false,
                },
            ))
            .map_err(|error| format!("cannot create rebalance pull request: {error}"))?;
        let number = created.pull_request().number();
        Ok(PublishedPullRequest {
            number,
            url: format!(
                "https://github.com/{}/{}/pull/{number}",
                plan.repository.owner(),
                plan.repository.name()
            ),
            branch: branch.to_owned(),
        })
    }

    fn recover_publish_failure(
        &mut self,
        artifacts: &[Artifact],
        branch: &str,
    ) -> Result<(), String> {
        self.checkout_main()?;
        self.restore_artifacts(artifacts)?;
        self.remove_created_branch(branch)?;
        if self.pushed_branch.as_deref() == Some(branch) {
            return Err(format!(
                "remote branch {branch} may exist after a failed publish; it was retained because the typed Git owner cannot safely prove a remote deletion"
            ));
        }
        Ok(())
    }

    fn verify(
        &mut self,
        arguments: &RebalanceRunArguments,
        plan: &PreparedPlan,
        pull_request: &PublishedPullRequest,
    ) -> Result<(), String> {
        let run_ids = self.dispatch_and_wait(
            &plan.repository,
            &arguments.workflow,
            &pull_request.branch,
            arguments.n_verify_runs,
        )?;
        let (harness_pair, pytest) = self.runtime.block_on(async {
            let harness = if let Some(harness_plan) = &plan.harness {
                let targets = harness_plan
                    .proposed_shards
                    .values()
                    .flatten()
                    .cloned()
                    .collect::<Vec<_>>();
                let selection = CiTimingRunSelection::Explicit(run_ids.clone());
                let timing = collect_harness_timing(
                    &self.github,
                    &plan.repository,
                    &selection,
                    &targets,
                    &self.cancellation,
                )
                .await
                .map_err(|error| error.to_string())?;
                let jobs = collect_job_timing(
                    &self.github,
                    &plan.repository,
                    &run_ids,
                    &self.cancellation,
                )
                .await
                .map_err(|error| error.to_string())?;
                Ok::<_, String>(Some((timing, jobs)))
            } else {
                Ok(None)
            }?;
            let pytest = if plan.python.is_some() {
                let selection = CiTimingRunSelection::Explicit(run_ids.clone());
                Some(
                    collect_pytest_timing(
                        &self.github,
                        &plan.repository,
                        &selection,
                        &self.cancellation,
                    )
                    .await
                    .map_err(|error| error.to_string())?,
                )
            } else {
                None
            };
            Ok::<_, String>((harness, pytest))
        })?;
        let (harness, jobs) =
            harness_pair.map_or((None, None), |(harness, jobs)| (Some(harness), Some(jobs)));
        let request = verify_request(
            arguments,
            plan,
            &run_ids,
            harness.as_ref(),
            jobs.as_ref(),
            pytest.as_ref(),
        )?;
        let result = verify_json(&request)?;
        if !result.success {
            return Err(
                "rebalance verification rejected the measured workflow evidence".to_owned(),
            );
        }
        Ok(())
    }
}

#[derive(Deserialize)]
struct PlanResponse {
    decision: String,
    violations: Vec<String>,
    harness: Option<PlanHarnessResponse>,
    python: Option<PlanPythonResponse>,
}

#[derive(Deserialize)]
struct PlanHarnessResponse {
    proposed_shards: BTreeMap<u32, Vec<String>>,
    baseline_slowest_wall_clock: f64,
    baseline_runner_seconds: f64,
    approved_slowest_wall_clock: f64,
    is_noop: bool,
}

#[derive(Deserialize)]
struct PlanPythonResponse {
    assignments: BTreeMap<String, u32>,
    shard_count: u32,
    is_noop: bool,
}

impl PlanResponse {
    fn into_prepared(
        self,
        kind: RebalanceKind,
        repository: GitHubRepositoryRef,
        current_harness: Option<BTreeMap<u32, Vec<String>>>,
    ) -> Result<PreparedPlan, String> {
        let harness = match self.harness {
            Some(response) => Some(HarnessPlan {
                current_shards: current_harness.ok_or_else(|| {
                    "plan response contained an unexpected harness leg".to_owned()
                })?,
                proposed_shards: response.proposed_shards,
                baseline_slowest_wall_clock: response.baseline_slowest_wall_clock,
                baseline_runner_seconds: response.baseline_runner_seconds,
                approved_slowest_wall_clock: response.approved_slowest_wall_clock,
                changed: !response.is_noop,
            }),
            None => None,
        };
        let python = self.python.map(|response| PythonPlan {
            assignments: response.assignments,
            shard_count: response.shard_count,
            changed: !response.is_noop,
        });
        if kind.includes_harness() != harness.is_some()
            || kind.includes_python() != python.is_some()
        {
            return Err("rebalance-tests plan response omitted a selected leg".to_owned());
        }
        Ok(PreparedPlan {
            kind,
            repository,
            harness,
            python,
            decision: self.decision,
        })
    }
}

fn plan_request(
    arguments: &RebalanceRunArguments,
    current_harness: Option<&BTreeMap<u32, Vec<String>>>,
    harness_timing: Option<&larch_core::HarnessTimingReport>,
    jobs_timing: Option<&larch_core::JobTimingReport>,
    current_assignments: Option<&BTreeMap<String, u32>>,
    pytest_timing: Option<&larch_core::PytestTimingReport>,
) -> Result<String, String> {
    let harness = match (current_harness, harness_timing, jobs_timing) {
        (Some(shards), Some(timing), Some(jobs)) => Some(json!({
            "expected_run_ids": timing.sampled_run_ids,
            "current_shards": shards,
            "timing": timing,
            "jobs": jobs,
        })),
        (None, None, None) => None,
        _ => return Err("incomplete harness planning evidence".to_owned()),
    };
    let python = match (current_assignments, pytest_timing) {
        (Some(assignments), Some(timing)) => Some(json!({
            "expected_run_ids": timing.sampled_run_ids,
            "current_assignments": assignments,
            "timing": timing,
        })),
        (None, None) => None,
        _ => return Err("incomplete python planning evidence".to_owned()),
    };
    serde_json::to_string(&json!({
        "schema_version": 1,
        "kind": "plan",
        "selection": arguments.kind.wire(),
        "options": {
            "max_shard_wall_clock": arguments.max_shard_wall_clock,
            "balance_threshold": arguments.balance_threshold,
            "n_python_shards": arguments.n_python_shards,
            "experimental_wall_clock_override": arguments.experimental_wall_clock_override,
            "compile_affinities": arguments.compile_affinity.iter().map(|affinity| json!({
                "target": affinity.target,
                "group": affinity.group,
                "setup_seconds": affinity.setup_seconds,
            })).collect::<Vec<_>>(),
        },
        "harness": harness,
        "python": python,
    }))
    .map_err(|error| format!("cannot render rebalance plan request: {error}"))
}

fn verify_request(
    arguments: &RebalanceRunArguments,
    plan: &PreparedPlan,
    run_ids: &[u64],
    harness_timing: Option<&larch_core::HarnessTimingReport>,
    jobs_timing: Option<&larch_core::JobTimingReport>,
    pytest_timing: Option<&larch_core::PytestTimingReport>,
) -> Result<String, String> {
    let harness = match (&plan.harness, harness_timing, jobs_timing) {
        (Some(plan), Some(timing), Some(jobs)) => Some(json!({
            "expected_run_ids": run_ids,
            "expected_shards": plan.proposed_shards,
            "baseline_slowest_wall_clock": plan.baseline_slowest_wall_clock,
            "baseline_runner_seconds": plan.baseline_runner_seconds,
            "approved_slowest_wall_clock": plan.approved_slowest_wall_clock,
            "timing": timing,
            "jobs": jobs,
        })),
        (None, None, None) => None,
        _ => return Err("incomplete harness verification evidence".to_owned()),
    };
    let python = match (&plan.python, pytest_timing) {
        (Some(plan), Some(timing)) => Some(json!({
            "expected_run_ids": run_ids,
            "expected_shard_count": plan.shard_count,
            "timing": timing,
        })),
        (None, None) => None,
        _ => return Err("incomplete python verification evidence".to_owned()),
    };
    serde_json::to_string(&json!({
        "schema_version": 1,
        "kind": "verify",
        "selection": arguments.kind.wire(),
        "options": {
            "max_shard_wall_clock": arguments.max_shard_wall_clock,
            "balance_threshold": arguments.balance_threshold,
            "experimental_wall_clock_override": arguments.experimental_wall_clock_override,
        },
        "harness": harness,
        "python": python,
    }))
    .map_err(|error| format!("cannot render rebalance verification request: {error}"))
}

fn artifact_git_paths(artifacts: &[Artifact]) -> Result<Vec<GitPath>, String> {
    artifacts
        .iter()
        .map(|artifact| GitPath::new(artifact.path()).map_err(|error| error.to_string()))
        .collect()
}

fn assignments_json(assignments: &BTreeMap<String, u32>) -> String {
    let mut rendered = serde_json::to_string_pretty(assignments)
        .expect("BTreeMap<String, u32> always serializes to JSON");
    rendered.push('\n');
    rendered
}

fn branch_name(prefix: &str) -> String {
    format!("{}-{}", prefix, Utc::now().format("%Y%m%d-%H%M%S"))
}

fn commit_subject(kind: RebalanceKind) -> String {
    format!("chore: rebalance test shards ({})", kind.commit_label())
}

fn pull_request_body(arguments: &RebalanceRunArguments, plan: &PreparedPlan) -> String {
    let mut legs = Vec::new();
    let mut files = Vec::new();
    if plan.harness.is_some() {
        legs.push("harness");
        files.push(MAKEFILE);
    }
    if plan.python.is_some() {
        legs.push("python");
        files.push(ASSIGNMENTS);
    }
    let mut body = vec![
        "Automatically generated by `/rebalance-tests`.".to_owned(),
        String::new(),
        format!("- Legs: {}", legs.join(", ")),
        format!("- Files: {}", files.join(", ")),
        format!(
            "- Baseline: {} successful runs on `{}`",
            arguments.n_runs, arguments.baseline_branch
        ),
        "- Merge remains operator-owned.".to_owned(),
    ];
    if let Some(harness) = &plan.harness {
        body.push(format!(
            "- Harness baseline observed slowest shard: {:.1}s",
            harness.baseline_slowest_wall_clock
        ));
        body.push(format!(
            "- Harness baseline summed runner time: {:.1}s",
            harness.baseline_runner_seconds
        ));
        body.push(format!(
            "- Harness approved slowest-shard threshold: {:.1}s",
            harness.approved_slowest_wall_clock
        ));
    }
    if let Some(python) = &plan.python {
        body.push(format!(
            "- Python nodeids assigned: {} across {} shards",
            python.assignments.len(),
            python.shard_count
        ));
    }
    if let Some(note) = &arguments.experimental_wall_clock_override {
        body.push(format!("- Experimental wall-clock override: {note}"));
    }
    body.join("\n") + "\n"
}

fn format_plan_rejection(response: &PlanResponse) -> String {
    if response.violations.is_empty() {
        "rebalance plan was rejected".to_owned()
    } else {
        format!(
            "rebalance plan was rejected: {}",
            response.violations.join("; ")
        )
    }
}

async fn list_workflow_ids(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    workflow: &str,
    branch: &str,
    cancellation: &Cancellation,
) -> Result<Vec<u64>, String> {
    let runs = service
        .list_workflow_runs(
            repository,
            &WorkflowRunFilters {
                branch: Some(branch.to_owned()),
                workflow: Some(workflow.to_owned()),
                limit: WORKFLOW_LIST_LIMIT,
                ..WorkflowRunFilters::default()
            },
            cancellation,
        )
        .await
        .map_err(|error| format!("cannot list verification workflow runs: {error}"))?;
    Ok(runs.into_iter().map(|run| run.database_id).collect())
}

async fn wait_for_completed_run(
    service: &dyn GitHubActionsService,
    repository: &GitHubRepositoryRef,
    workflow: &str,
    branch: &str,
    excluded: &[u64],
    cancellation: &Cancellation,
) -> Result<u64, String> {
    let started = tokio::time::Instant::now();
    loop {
        let runs = service
            .list_workflow_runs(
                repository,
                &WorkflowRunFilters {
                    branch: Some(branch.to_owned()),
                    workflow: Some(workflow.to_owned()),
                    limit: WORKFLOW_LIST_LIMIT,
                    ..WorkflowRunFilters::default()
                },
                cancellation,
            )
            .await
            .map_err(|error| format!("cannot wait for verification workflow: {error}"))?;
        if let Some(run) = runs
            .into_iter()
            .filter(|run| !excluded.contains(&run.database_id))
            .max_by_key(|run| run.database_id)
            && run.status == "completed"
        {
            if run.conclusion.as_deref() == Some("success") {
                return Ok(run.database_id);
            }
            return Err(format!(
                "verification workflow {} completed with {:?}",
                run.database_id, run.conclusion
            ));
        }
        if started.elapsed() >= WORKFLOW_WAIT_LIMIT {
            return Err("verification workflow did not complete before its deadline".to_owned());
        }
        tokio::time::sleep(WORKFLOW_POLL).await;
    }
}

fn parse_run_count(value: &str) -> Result<usize, String> {
    value
        .parse::<usize>()
        .ok()
        .filter(|count| (1..=larch_core::MAX_CI_TIMING_RUNS).contains(count))
        .ok_or_else(|| {
            format!(
                "expected an integer from 1 through {}, got {value:?}",
                larch_core::MAX_CI_TIMING_RUNS
            )
        })
}
fn parse_positive_u32(value: &str) -> Result<u32, String> {
    value
        .parse::<u32>()
        .ok()
        .filter(|value| *value > 0)
        .ok_or_else(|| format!("expected a positive integer, got {value:?}"))
}
fn parse_positive_f64(value: &str) -> Result<f64, String> {
    value
        .parse::<f64>()
        .ok()
        .filter(|value| value.is_finite() && *value > 0.0)
        .ok_or_else(|| format!("expected a positive finite number, got {value:?}"))
}
fn parse_experiment_note(value: &str) -> Result<String, String> {
    let value = value.trim();
    (!value.is_empty())
        .then(|| value.to_owned())
        .ok_or_else(|| {
            "experimental wall-clock override must name the documented experiment".to_owned()
        })
}
fn parse_branch_prefix(value: &str) -> Result<String, String> {
    let valid = !value.is_empty()
        && value.len() <= 100
        && value
            .bytes()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-');
    valid
        .then(|| value.to_owned())
        .ok_or_else(|| "branch prefix must use lowercase letters, digits, and hyphens".to_owned())
}
fn parse_selector(value: &str) -> Result<String, String> {
    let valid = !value.is_empty()
        && value.len() <= 255
        && !value.chars().any(char::is_whitespace)
        && !value.starts_with('-');
    valid.then(|| value.to_owned()).ok_or_else(|| {
        "workflow and branch selectors must be nonempty and contain no whitespace".to_owned()
    })
}
fn parse_compile_affinity(value: &str) -> Result<CompileAffinityArgument, String> {
    let invalid = || "compile affinity must use TARGET=GROUP:SECONDS".to_owned();
    if value.contains(['\n', '\r']) {
        return Err(invalid());
    }
    let mut options = larch_core::ParseOptions::legacy();
    options.malformed_lines = larch_core::MalformedLinePolicy::Reject;
    let document = larch_core::KvDocument::parse(value, options).map_err(|_| invalid())?;
    let [row] = document.rows() else {
        return Err(invalid());
    };
    let (target, remainder) = (row.key(), row.value());
    let (group, seconds) = remainder
        .rsplit_once(':')
        .ok_or_else(|| "compile affinity must use TARGET=GROUP:SECONDS".to_owned())?;
    if target.is_empty()
        || group.is_empty()
        || target.chars().chain(group.chars()).any(char::is_whitespace)
    {
        return Err(
            "compile affinity target and group must be nonempty without whitespace".to_owned(),
        );
    }
    let setup_seconds = seconds
        .parse::<f64>()
        .ok()
        .filter(|seconds| seconds.is_finite() && *seconds >= 0.0)
        .ok_or_else(|| {
            "compile affinity setup seconds must be non-negative and finite".to_owned()
        })?;
    Ok(CompileAffinityArgument {
        target: target.to_owned(),
        group: group.to_owned(),
        setup_seconds,
    })
}
#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Clone, Copy)]
    enum Failure {
        Dirty,
        Stale,
        Write,
        Publish,
        Verify,
    }

    struct FixtureWorkflow {
        failure: Option<Failure>,
        noop: bool,
        events: Vec<&'static str>,
    }

    impl FixtureWorkflow {
        fn new(failure: Option<Failure>, noop: bool) -> Self {
            Self {
                failure,
                noop,
                events: Vec::new(),
            }
        }
    }

    impl WorkflowPort for FixtureWorkflow {
        fn prepare(&mut self, _arguments: &RebalanceRunArguments) -> Result<PreparedPlan, String> {
            self.events.push("prepare");
            match self.failure {
                Some(Failure::Dirty) => return Err("dirty repository".to_owned()),
                Some(Failure::Stale) => return Err("stale immutable-main evidence".to_owned()),
                _ => {}
            }
            Ok(PreparedPlan {
                kind: RebalanceKind::Python,
                repository: GitHubRepositoryRef::new("owner", "repo").unwrap(),
                harness: None,
                python: Some(PythonPlan {
                    assignments: BTreeMap::from([("test::one".to_owned(), 1)]),
                    shard_count: 1,
                    changed: !self.noop,
                }),
                decision: if self.noop { "noop" } else { "change" }.to_owned(),
            })
        }

        fn write_candidates(&mut self, _plan: &PreparedPlan) -> Result<Vec<Artifact>, String> {
            self.events.push("write");
            if matches!(self.failure, Some(Failure::Write)) {
                self.events.push("write-rollback");
                return Err("candidate write failed".to_owned());
            }
            Ok(vec![Artifact::Assignments])
        }

        fn publish(
            &mut self,
            _arguments: &RebalanceRunArguments,
            _plan: &PreparedPlan,
            _artifacts: &[Artifact],
            branch: &str,
        ) -> Result<PublishedPullRequest, String> {
            self.events.push("publish");
            if matches!(self.failure, Some(Failure::Publish)) {
                return Err("push failed".to_owned());
            }
            Ok(PublishedPullRequest {
                number: 1,
                url: "https://example.invalid/pull/1".to_owned(),
                branch: branch.to_owned(),
            })
        }

        fn recover_publish_failure(
            &mut self,
            _artifacts: &[Artifact],
            _branch: &str,
        ) -> Result<(), String> {
            self.events.push("publish-rollback");
            Ok(())
        }

        fn verify(
            &mut self,
            _arguments: &RebalanceRunArguments,
            _plan: &PreparedPlan,
            _pull_request: &PublishedPullRequest,
        ) -> Result<(), String> {
            self.events.push("verify");
            matches!(self.failure, Some(Failure::Verify))
                .then_some(Err("verification failed".to_owned()))
                .unwrap_or(Ok(()))
        }
    }

    fn arguments() -> RebalanceRunArguments {
        RebalanceRunArguments {
            kind: RebalanceKind::Python,
            repo: Some(GitHubRepositoryRef::new("owner", "repo").unwrap()),
            n_runs: 1,
            branch_prefix: "rebalance-shards".to_owned(),
            n_verify_runs: 1,
            n_python_shards: None,
            balance_threshold: 15.0,
            max_shard_wall_clock: 300.0,
            experimental_wall_clock_override: None,
            compile_affinity: Vec::new(),
            workflow: "ci.yaml".to_owned(),
            baseline_branch: "main".to_owned(),
            dry_run: false,
        }
    }

    #[test]
    fn offline_success_fixture_writes_publishes_verifies_and_cleans_up() {
        let mut fixture = FixtureWorkflow::new(None, false);
        assert_eq!(execute(&mut fixture, &arguments()), Ok(ExitCode::SUCCESS));
        assert_eq!(fixture.events, ["prepare", "write", "publish", "verify"]);
    }

    #[test]
    fn offline_noop_fixture_never_mutates() {
        let mut fixture = FixtureWorkflow::new(None, true);
        assert_eq!(execute(&mut fixture, &arguments()), Ok(ExitCode::SUCCESS));
        assert_eq!(fixture.events, ["prepare"]);
    }

    #[test]
    fn offline_dirty_and_stale_fixtures_refuse_before_writes() {
        for failure in [Failure::Dirty, Failure::Stale] {
            let mut fixture = FixtureWorkflow::new(Some(failure), false);
            assert!(execute(&mut fixture, &arguments()).is_err());
            assert_eq!(fixture.events, ["prepare"]);
        }
    }

    #[test]
    fn offline_candidate_write_fixture_rolls_back_before_publish() {
        let mut fixture = FixtureWorkflow::new(Some(Failure::Write), false);
        assert!(execute(&mut fixture, &arguments()).is_err());
        assert_eq!(fixture.events, ["prepare", "write", "write-rollback"]);
    }

    #[test]
    fn offline_push_or_pr_failure_fixture_restores_candidates_and_branch() {
        let mut fixture = FixtureWorkflow::new(Some(Failure::Publish), false);
        assert!(execute(&mut fixture, &arguments()).is_err());
        assert_eq!(
            fixture.events,
            ["prepare", "write", "publish", "publish-rollback"]
        );
    }

    #[test]
    fn offline_verification_failure_fixture_keeps_the_created_pr() {
        let mut fixture = FixtureWorkflow::new(Some(Failure::Verify), false);
        assert!(execute(&mut fixture, &arguments()).is_err());
        assert_eq!(fixture.events, ["prepare", "write", "publish", "verify"]);
    }

    #[test]
    fn parsers_reject_unsafe_workflow_inputs() {
        assert!(parse_branch_prefix("branch;rm").is_err());
        assert!(parse_selector("main branch").is_err());
        assert!(parse_compile_affinity("target=group:0\n").is_err());
        assert!(parse_compile_affinity("target=group:0").is_ok());
    }

    #[test]
    fn assignment_format_and_subject_match_the_existing_contract() {
        assert_eq!(
            assignments_json(&BTreeMap::from([("b".to_owned(), 2), ("a".to_owned(), 1)])),
            "{\n  \"a\": 1,\n  \"b\": 2\n}\n"
        );
        assert_eq!(
            commit_subject(RebalanceKind::All),
            "chore: rebalance test shards (harness+python)"
        );
    }
}
