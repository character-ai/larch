use super::*;
use larch_test_support::{HttpResponseBuilder, IssueServiceExchange, IssueServiceStub};
use std::{
    fs,
    path::Path,
    process::{Command, Output},
};

#[derive(Clone, Copy)]
enum Failure {
    Dirty,
    Stale,
    StaleBeforeWrite,
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
            kind: RebalanceKind::Rust,
            repository: GitHubRepositoryRef::new("owner", "repo").unwrap(),
            harness: None,
            rust: Some(RustPlan {
                current_shard_count: 1,
                shard_count: if self.noop { 1 } else { 2 },
                baseline_slowest_wall_clock: 500.0,
                approved_slowest_wall_clock: 500.0,
                changed: !self.noop,
            }),
            decision: if self.noop { "noop" } else { "change" }.to_owned(),
        })
    }

    fn revalidate_for_write(&mut self) -> Result<(), String> {
        self.events.push("revalidate");
        matches!(self.failure, Some(Failure::StaleBeforeWrite))
            .then_some(Err("stale immutable-main evidence".to_owned()))
            .unwrap_or(Ok(()))
    }

    fn write_candidates(&mut self, _plan: &PreparedPlan) -> Result<Vec<Artifact>, String> {
        self.events.push("write");
        if matches!(self.failure, Some(Failure::Write)) {
            self.events.push("write-rollback");
            return Err("candidate write failed".to_owned());
        }
        Ok(vec![Artifact::CiWorkflow])
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
            head_sha: "a".repeat(40),
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

struct GitFixture {
    root: tempfile::TempDir,
    remote: tempfile::TempDir,
}

impl GitFixture {
    fn new() -> Self {
        let root = tempfile::tempdir().expect("temporary repository root");
        let remote = tempfile::tempdir().expect("temporary origin");
        fs::write(
            root.path().join(MAKEFILE),
            "test-harnesses-1: test-harness-shards-coverage alpha\n\
             test-harnesses-2: beta\n",
        )
        .expect("write fixture Makefile");
        fs::create_dir_all(root.path().join(".github/workflows"))
            .expect("create workflow directory");
        fs::write(
            root.path().join(CI_WORKFLOW),
            r#"jobs:
  rust-full-shards:
    strategy:
      matrix:
        shard: [1]
    env:
      COVERAGE_SHARD_COUNT: "1"
  rust-full-policy:
  rust-partial:
  rust-skip:
  rust-coverage:
    env:
      RUST_COVERAGE_SHARD_COUNT: "1"
  # Manual profile sweeps
"#,
        )
        .expect("write fixture CI workflow");
        git(root.path(), &["init", "--quiet", "--initial-branch=main"]);
        git(
            root.path(),
            &["config", "user.email", "rebalance@example.invalid"],
        );
        git(root.path(), &["config", "user.name", "Rebalance fixture"]);
        git(root.path(), &["add", "--all"]);
        git(root.path(), &["commit", "--quiet", "-m", "base"]);
        git_bare(remote.path(), &["init", "--bare", "--quiet"]);
        git(
            root.path(),
            &[
                "remote",
                "add",
                "origin",
                remote.path().to_str().expect("UTF-8 remote path"),
            ],
        );
        git(
            root.path(),
            &["push", "--quiet", "--set-upstream", "origin", MAIN],
        );
        Self { root, remote }
    }

    fn workflow(&self) -> ProductionWorkflow {
        let root = RepositoryRoot::resolve(Some(self.root.path())).expect("fixture root");
        let repository = GixRepository::discover(root.path()).expect("fixture repository");
        let runtime = LarchRuntime::new().expect("fixture runtime");
        let cancellation = Cancellation::new();
        let runner = TokioProcessRunner::default();
        let git_policy = GitCliPolicy::new(root.path().to_path_buf()).expect("fixture Git policy");
        ProductionWorkflow {
            root,
            repository,
            runtime,
            cancellation,
            runner,
            github: None,
            git_policy,
            created_branch: None,
            pushed_branch: None,
        }
    }

    fn branch(&self) -> String {
        String::from_utf8(git_output(self.root.path(), &["branch", "--show-current"]).stdout)
            .expect("UTF-8 branch name")
            .trim()
            .to_owned()
    }

    fn local_branch_exists(&self, branch: &str) -> bool {
        !git_output(self.root.path(), &["branch", "--list", branch])
            .stdout
            .is_empty()
    }

    fn remote_branch_exists(&self, branch: &str) -> bool {
        Command::new("git") // lint-subprocess-via-runner: ok test-only Git fixture inspects its isolated bare origin
            .arg("--git-dir")
            .arg(self.remote.path())
            .args(["show-ref", "--verify", "--quiet"])
            .arg(format!("refs/heads/{branch}"))
            .status()
            .expect("inspect fixture origin")
            .success()
    }
}

fn workflow_with_github(fixture: &GitFixture, server: &IssueServiceStub) -> ProductionWorkflow {
    let mut workflow = fixture.workflow();
    workflow.github = Some(
        workflow
            .runtime
            .block_on(async { OctocrabGitHubService::with_test_base(server.base_url()) }),
    );
    workflow
}

fn start_github_stub(exchanges: Vec<IssueServiceExchange>) -> IssueServiceStub {
    IssueServiceStub::start(exchanges).expect("start loopback GitHub stub")
}

fn empty_workflow_runs() -> &'static str {
    r#"{"workflow_runs":[]}"#
}

fn successful_workflow_runs(head_sha: &str) -> String {
    format!(
        r#"{{"workflow_runs":[{{"id":17,"status":"completed","conclusion":"success","head_sha":"{head_sha}","event":"workflow_dispatch","run_attempt":1}}]}}"#
    )
}

fn no_content_exchange() -> IssueServiceExchange {
    IssueServiceExchange::any(
        HttpResponseBuilder::new(204)
            .build()
            .expect("valid no-content response"),
    )
}

fn created_pull_request() -> &'static str {
    r#"{"number":42,"state":"open","title":"rebalance","head":{"ref":"rebalance-publish"},"base":{"ref":"main"},"draft":false,"merged":false}"#
}

fn git(root: &Path, arguments: &[&str]) {
    let status = Command::new("git") // lint-subprocess-via-runner: ok test-only Git fixture creates typed repository states
        .arg("-C")
        .arg(root)
        .args(arguments)
        .status()
        .expect("run fixture git");
    assert!(status.success(), "fixture git command failed: {status}");
}

fn git_bare(root: &Path, arguments: &[&str]) {
    let status = Command::new("git") // lint-subprocess-via-runner: ok test-only Git fixture creates its isolated bare origin
        .args(arguments)
        .arg(root)
        .status()
        .expect("run bare fixture git");
    assert!(
        status.success(),
        "bare fixture git command failed: {status}"
    );
}

fn git_output(root: &Path, arguments: &[&str]) -> Output {
    let output = Command::new("git") // lint-subprocess-via-runner: ok test-only Git fixture reads its isolated repository state
        .arg("-C")
        .arg(root)
        .args(arguments)
        .output()
        .expect("read fixture git state");
    assert!(
        output.status.success(),
        "fixture git read failed: {}",
        output.status
    );
    output
}

fn arguments() -> RebalanceRunArguments {
    RebalanceRunArguments {
        kind: RebalanceKind::Rust,
        repo: Some(GitHubRepositoryRef::new("owner", "repo").unwrap()),
        n_runs: 1,
        branch_prefix: "rebalance-shards".to_owned(),
        n_verify_runs: 1,
        n_rust_shards: None,
        max_shard_wall_clock: 300.0,
        max_rust_shard_wall_clock: 600.0,
        experimental_wall_clock_override: None,
        compile_affinity: Vec::new(),
        workflow: "ci.yaml".to_owned(),
        baseline_branch: "main".to_owned(),
        dry_run: false,
    }
}

fn changed_plan() -> PreparedPlan {
    PreparedPlan {
        kind: RebalanceKind::All,
        repository: GitHubRepositoryRef::new("owner", "repo").expect("fixture repository"),
        harness: Some(HarnessPlan {
            current_shards: BTreeMap::from([
                (
                    1,
                    vec![
                        "test-harness-shards-coverage".to_owned(),
                        "alpha".to_owned(),
                    ],
                ),
                (2, vec!["beta".to_owned()]),
            ]),
            proposed_shards: BTreeMap::from([
                (
                    1,
                    vec!["test-harness-shards-coverage".to_owned(), "beta".to_owned()],
                ),
                (2, vec!["alpha".to_owned()]),
            ]),
            predicted_packed_spread: 4.0,
            baseline_slowest_wall_clock: 10.0,
            baseline_runner_seconds: 18.0,
            approved_slowest_wall_clock: 12.0,
            changed: true,
        }),
        rust: Some(RustPlan {
            current_shard_count: 1,
            shard_count: 1,
            baseline_slowest_wall_clock: 500.0,
            approved_slowest_wall_clock: 500.0,
            changed: false,
        }),
        decision: "approved".to_owned(),
    }
}

fn harness_only_plan() -> PreparedPlan {
    let mut plan = changed_plan();
    plan.kind = RebalanceKind::Harness;
    plan.rust = None;
    plan
}

fn rust_only_plan() -> PreparedPlan {
    let mut plan = changed_plan();
    plan.kind = RebalanceKind::Rust;
    plan.harness = None;
    let rust = plan.rust.as_mut().expect("Rust plan");
    rust.shard_count = 4;
    rust.approved_slowest_wall_clock = 480.0;
    rust.changed = true;
    plan
}

fn approved_response(plan: &PreparedPlan) -> PlanResponse {
    PlanResponse {
        decision: "approved".to_owned(),
        violations: Vec::new(),
        harness: Some(PlanHarnessResponse {
            proposed_shards: plan
                .harness
                .as_ref()
                .expect("harness plan")
                .proposed_shards
                .clone(),
            predicted_proposed: BTreeMap::from([(1, 10.0), (2, 6.0)]),
            baseline_slowest_wall_clock: 10.0,
            baseline_runner_seconds: 18.0,
            approved_slowest_wall_clock: 12.0,
            is_noop: false,
        }),
        rust: Some(PlanRustResponse {
            current_shard_count: 1,
            shard_count: 1,
            baseline_slowest_wall_clock: 500.0,
            approved_slowest_wall_clock: 500.0,
            is_noop: true,
        }),
    }
}

fn timing_reports() -> (
    larch_core::HarnessTimingReport,
    larch_core::JobTimingReport,
    larch_core::JobTimingReport,
) {
    let harness = serde_json::from_value(json!({
        "schema_version": 2,
        "kind": "harness",
        "sampled_run_ids": [11],
        "rows": [],
        "bootstrap_rows": [],
        "target_medians": [],
        "shard_medians": [],
        "untimed_targets": [],
        "skipped_run_ids": [],
    }))
    .expect("fixture harness timing report");
    let jobs = serde_json::from_value(json!({
        "schema_version": 2,
        "kind": "jobs",
        "sampled_run_ids": [11],
        "rows": [],
        "shard_medians": [],
        "skipped_run_ids": [],
    }))
    .expect("fixture job timing report");
    let rust = serde_json::from_value(json!({
        "schema_version": 2,
        "kind": "rust-jobs",
        "sampled_run_ids": [11],
        "rows": [{"run_id": 11, "shard": 1, "seconds": 500.0}],
        "shard_medians": [{"shard": 1, "seconds": 500.0}],
        "skipped_run_ids": [],
    }))
    .expect("fixture Rust job timing report");
    (harness, jobs, rust)
}

#[test]
fn rust_workflow_shard_count_rewrite_updates_the_three_lockstep_fields() {
    let fixture = GitFixture::new();
    let source =
        fs::read_to_string(fixture.root.path().join(CI_WORKFLOW)).expect("read fixture workflow");

    assert_eq!(rust_workflow_shard_count(&source), Ok(1));
    let rewritten = rewrite_rust_workflow_shard_count(&source, 4).expect("rewrite workflow");
    assert_eq!(rust_workflow_shard_count(&rewritten), Ok(4));
    assert!(rewritten.contains("shard: [1, 2, 3, 4]"));
    assert!(rewritten.contains("COVERAGE_SHARD_COUNT: \"4\""));
    assert!(rewritten.contains("RUST_COVERAGE_SHARD_COUNT: \"4\""));
}

#[test]
fn rust_workflow_shard_count_refuses_inconsistent_or_ambiguous_fields() {
    let fixture = GitFixture::new();
    let source =
        fs::read_to_string(fixture.root.path().join(CI_WORKFLOW)).expect("read fixture workflow");
    let inconsistent = source.replace(
        "RUST_COVERAGE_SHARD_COUNT: \"1\"",
        "RUST_COVERAGE_SHARD_COUNT: \"2\"",
    );
    assert!(
        rust_workflow_shard_count(&inconsistent)
            .expect_err("inconsistent workflow must fail closed")
            .contains("inconsistent")
    );
    let ambiguous = source.replacen(
        "      COVERAGE_SHARD_COUNT: \"1\"",
        "      COVERAGE_SHARD_COUNT: \"1\"\n      COVERAGE_SHARD_COUNT: \"1\"",
        1,
    );
    assert!(
        rust_workflow_shard_count(&ambiguous)
            .expect_err("ambiguous workflow must fail closed")
            .contains("multiple")
    );
}

#[test]
fn production_workflow_writes_a_rust_matrix_resize_as_one_artifact() {
    let fixture = GitFixture::new();
    let mut workflow = fixture.workflow();
    let plan = rust_only_plan();

    let artifacts = workflow
        .write_candidates(&plan)
        .expect("write Rust coverage rebalance artifact");

    assert_eq!(artifacts, [Artifact::CiWorkflow]);
    let workflow_text =
        fs::read_to_string(fixture.root.path().join(CI_WORKFLOW)).expect("read rewritten workflow");
    assert_eq!(rust_workflow_shard_count(&workflow_text), Ok(4));
    workflow
        .restore_artifacts(&artifacts)
        .expect("restore Rust coverage rebalance artifact");
    let restored =
        fs::read_to_string(fixture.root.path().join(CI_WORKFLOW)).expect("read restored workflow");
    assert_eq!(rust_workflow_shard_count(&restored), Ok(1));
}

#[test]
fn production_workflow_writes_pushes_and_recovers_with_an_isolated_origin() {
    let fixture = GitFixture::new();
    let mut workflow = fixture.workflow();
    let plan = changed_plan();
    let mut publish_arguments = arguments();
    publish_arguments.kind = RebalanceKind::All;
    let original_makefile =
        fs::read_to_string(fixture.root.path().join(MAKEFILE)).expect("read fixture Makefile");

    workflow
        .fetch_and_require_immutable_main()
        .expect("fixture main is immutable and clean");
    let artifacts = workflow
        .write_candidates(&plan)
        .expect("write candidate artifacts");
    assert_eq!(artifacts, [Artifact::Makefile]);
    assert_ne!(
        fs::read_to_string(fixture.root.path().join(MAKEFILE)).expect("read candidate Makefile"),
        original_makefile
    );

    let branch = "rebalance-fixture";
    let error = workflow
        .publish(&publish_arguments, &plan, &artifacts, branch)
        .expect_err("test workflow intentionally has no GitHub client");
    assert!(error.contains("GitHub service was not initialized"));
    assert_eq!(fixture.branch(), MAIN);
    assert!(fixture.local_branch_exists(branch));
    assert!(fixture.remote_branch_exists(branch));

    let recovery = workflow
        .recover_publish_failure(&artifacts, branch)
        .expect_err("a possibly-pushed remote branch is deliberately retained");
    assert!(recovery.contains("remote branch rebalance-fixture may exist"));
    assert!(!fixture.local_branch_exists(branch));
    assert_eq!(
        fs::read_to_string(fixture.root.path().join(MAKEFILE)).expect("read restored Makefile"),
        original_makefile
    );
}

#[test]
fn production_workflow_publishes_through_the_typed_github_service() {
    let fixture = GitFixture::new();
    let server = start_github_stub(vec![
        IssueServiceExchange::any_json(200, "[]").expect("valid pull request list"),
        IssueServiceExchange::any_json(201, created_pull_request())
            .expect("valid created pull request"),
    ]);
    let mut workflow = workflow_with_github(&fixture, &server);
    let plan = changed_plan();
    let mut publish_arguments = arguments();
    publish_arguments.kind = RebalanceKind::All;
    let artifacts = workflow
        .write_candidates(&plan)
        .expect("write candidate artifacts");

    let published = workflow
        .publish(&publish_arguments, &plan, &artifacts, "rebalance-publish")
        .expect("create pull request through loopback service");

    assert_eq!(published.number, 42);
    assert_eq!(published.branch, "rebalance-publish");
    assert_eq!(fixture.branch(), MAIN);
    assert!(fixture.remote_branch_exists("rebalance-publish"));
    workflow
        .restore_artifacts(&artifacts)
        .expect("restore fixture artifacts");
    workflow
        .remove_created_branch("rebalance-publish")
        .expect("remove fixture branch");
    assert_eq!(
        server
            .finish()
            .expect("all typed GitHub requests are consumed")
            .len(),
        2
    );
}

#[test]
fn production_workflow_dispatches_and_selects_a_fresh_verification_run() {
    let fixture = GitFixture::new();
    let head_sha = "a".repeat(40);
    let server = start_github_stub(vec![
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid initial workflow list"),
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid dispatch workflow list"),
        no_content_exchange(),
        IssueServiceExchange::any_json(200, successful_workflow_runs(&head_sha))
            .expect("valid completed workflow list"),
    ]);
    let workflow = workflow_with_github(&fixture, &server);
    let repository = GitHubRepositoryRef::new("owner", "repo").expect("fixture repository");

    assert_eq!(
        workflow.dispatch_and_wait(&repository, "ci.yaml", "rebalance-dispatch", &head_sha, 1,),
        Ok(vec![17])
    );
    assert_eq!(
        server
            .finish()
            .expect("all typed Actions requests are consumed")
            .len(),
        4
    );
}

#[test]
fn production_workflow_verification_rejects_an_incomplete_plan_after_dispatch() {
    let fixture = GitFixture::new();
    let head_sha = "b".repeat(40);
    let server = start_github_stub(vec![
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid initial workflow list"),
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid dispatch workflow list"),
        no_content_exchange(),
        IssueServiceExchange::any_json(200, successful_workflow_runs(&head_sha))
            .expect("valid completed workflow list"),
    ]);
    let mut workflow = workflow_with_github(&fixture, &server);
    let repository = GitHubRepositoryRef::new("owner", "repo").expect("fixture repository");
    let plan = PreparedPlan {
        kind: RebalanceKind::All,
        repository,
        harness: None,
        rust: None,
        decision: "approved".to_owned(),
    };
    let pull_request = PublishedPullRequest {
        number: 17,
        url: "https://example.invalid/pull/17".to_owned(),
        branch: "rebalance-dispatch".to_owned(),
        head_sha,
    };
    let mut verify_arguments = arguments();
    verify_arguments.kind = RebalanceKind::All;

    let error = workflow
        .verify(&verify_arguments, &plan, &pull_request)
        .expect_err("a selected verification leg requires matching evidence");
    assert!(
        error.contains("rebalance verification rejected")
            || error.contains("selected leg")
            || error.contains("selection does not match supplied legs"),
        "unexpected verification error: {error}"
    );
    assert_eq!(
        server
            .finish()
            .expect("all typed Actions requests are consumed")
            .len(),
        4
    );
}

#[test]
fn production_workflow_collects_each_selected_planning_leg_before_rejecting_empty_evidence() {
    let fixture = GitFixture::new();
    let server = start_github_stub(vec![
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid empty harness selection"),
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid empty Rust coverage selection"),
    ]);
    let workflow = workflow_with_github(&fixture, &server);
    let repository = GitHubRepositoryRef::new("owner", "repo").expect("fixture repository");
    let mut planning_arguments = arguments();
    planning_arguments.kind = RebalanceKind::All;

    let error = workflow
        .collect_plan(&planning_arguments, &repository)
        .expect_err("empty selected timing cohorts must be rejected by the Rust plan core");
    assert!(error.contains("harness.expected_run_ids"), "{error}");
    assert_eq!(
        server
            .finish()
            .expect("all typed planning selections are consumed")
            .len(),
        2
    );
}

#[test]
fn production_workflow_collects_each_selected_verification_leg_before_failing_closed() {
    let fixture = GitFixture::new();
    let head_sha = "c".repeat(40);
    let server = start_github_stub(vec![
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid initial workflow list"),
        IssueServiceExchange::any_json(200, empty_workflow_runs())
            .expect("valid dispatch workflow list"),
        no_content_exchange(),
        IssueServiceExchange::any_json(200, successful_workflow_runs(&head_sha))
            .expect("valid completed workflow list"),
        IssueServiceExchange::any_json(404, "{}").expect("valid harness log failure"),
        IssueServiceExchange::any_json(404, "{}").expect("valid jobs failure"),
        IssueServiceExchange::any_json(404, "{}").expect("valid Rust jobs failure"),
    ]);
    let mut workflow = workflow_with_github(&fixture, &server);
    let mut verify_arguments = arguments();
    verify_arguments.kind = RebalanceKind::All;
    let mut plan = changed_plan();
    plan.harness
        .as_mut()
        .expect("harness plan")
        .approved_slowest_wall_clock = 10.0;
    let pull_request = PublishedPullRequest {
        number: 17,
        url: "https://example.invalid/pull/17".to_owned(),
        branch: "rebalance-dispatch".to_owned(),
        head_sha,
    };

    let error = workflow
        .verify(&verify_arguments, &plan, &pull_request)
        .expect_err("missing typed verification evidence must fail closed");
    assert!(error.contains("harness timing cohort"), "{error}");
    assert_eq!(
        server
            .finish()
            .expect("all typed verification requests are consumed")
            .len(),
        7
    );
}

#[test]
fn immutable_main_validation_rejects_other_branches_and_dirty_files() {
    let fixture = GitFixture::new();
    fixture
        .workflow()
        .fetch_and_require_immutable_main()
        .expect("fixture main is accepted");
    git(
        fixture.root.path(),
        &["switch", "--quiet", "--create", "topic"],
    );
    let error = fixture
        .workflow()
        .fetch_and_require_immutable_main()
        .expect_err("non-main checkout is rejected");
    assert!(error.contains("local main branch"), "{error}");
    git(fixture.root.path(), &["switch", "--quiet", MAIN]);
    fs::write(fixture.root.path().join("untracked"), "dirty\n").expect("dirty fixture");
    assert!(
        fixture
            .workflow()
            .fetch_and_require_immutable_main()
            .expect_err("dirty checkout is rejected")
            .contains("dirty repository")
    );
}

#[test]
fn push_branch_refuses_a_remote_branch_that_already_exists() {
    let fixture = GitFixture::new();
    let branch = "existing-rebalance";
    git(
        fixture.root.path(),
        &["switch", "--quiet", "--create", branch],
    );
    git(
        fixture.root.path(),
        &[
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "existing branch",
        ],
    );
    git(fixture.root.path(), &["push", "--quiet", "origin", branch]);
    git(
        fixture.root.path(),
        &["commit", "--quiet", "--allow-empty", "-m", "local advance"],
    );
    git(fixture.root.path(), &["switch", "--quiet", MAIN]);

    let mut workflow = fixture.workflow();
    assert!(
        workflow
            .push_branch(branch)
            .expect_err("force-with-lease must refuse an existing remote branch")
            .contains("cannot push rebalance branch")
    );
    assert_eq!(workflow.pushed_branch.as_deref(), Some(branch));
}

#[test]
fn plan_and_verify_requests_preserve_complete_evidence() {
    let mut request_arguments = arguments();
    request_arguments.kind = RebalanceKind::All;
    request_arguments.experimental_wall_clock_override = Some("experiment-42".to_owned());
    request_arguments.compile_affinity = vec![CompileAffinityArgument {
        target: "crate-a".to_owned(),
        group: "compile".to_owned(),
        setup_seconds: 2.5,
    }];
    let plan = changed_plan();
    let harness_map = &plan.harness.as_ref().expect("harness plan").current_shards;
    let (harness, jobs, rust_jobs) = timing_reports();

    let planned: serde_json::Value = serde_json::from_str(
        &plan_request(
            &request_arguments,
            &PlanRequestEvidence {
                current_harness: Some(harness_map),
                harness_timing: Some(&harness),
                jobs_timing: Some(&jobs),
                current_rust_shard_count: Some(1),
                rust_timing: Some(&rust_jobs),
            },
        )
        .expect("render planning request"),
    )
    .expect("parse planning request");
    assert_eq!(planned["kind"], "plan");
    assert_eq!(planned["schema_version"], 2);
    assert_eq!(planned["selection"], "all");
    assert_eq!(planned["harness"]["expected_run_ids"], json!([11]));
    assert_eq!(planned["rust"]["expected_run_ids"], json!([11]));
    assert!(planned.get("python").is_none());
    assert_eq!(
        planned["options"]["compile_affinities"][0]["target"],
        "crate-a"
    );
    assert!(
        plan_request(
            &request_arguments,
            &PlanRequestEvidence {
                current_harness: Some(harness_map),
                harness_timing: None,
                jobs_timing: Some(&jobs),
                current_rust_shard_count: Some(1),
                rust_timing: Some(&rust_jobs),
            },
        )
        .is_err()
    );

    let verified: serde_json::Value = serde_json::from_str(
        &verify_request(
            &request_arguments,
            &plan,
            &[21, 22],
            Some(&harness),
            Some(&jobs),
            Some(&rust_jobs),
        )
        .expect("render verification request"),
    )
    .expect("parse verification request");
    assert_eq!(verified["kind"], "verify");
    assert_eq!(verified["schema_version"], 2);
    assert_eq!(verified["harness"]["expected_run_ids"], json!([21, 22]));
    assert_eq!(verified["rust"]["expected_shard_count"], 1);
    assert!(verified.get("python").is_none());
    assert!(
        verify_request(
            &request_arguments,
            &plan,
            &[21],
            None,
            Some(&jobs),
            Some(&rust_jobs),
        )
        .is_err()
    );
}

#[test]
fn plan_response_prepares_selected_legs() {
    let plan = changed_plan();
    let current_shards = plan
        .harness
        .as_ref()
        .expect("harness plan")
        .current_shards
        .clone();
    let prepared = approved_response(&plan)
        .into_prepared(
            RebalanceKind::All,
            GitHubRepositoryRef::new("owner", "repo").expect("fixture repository"),
            Some(current_shards),
        )
        .expect("complete response prepares all legs");
    assert!(!prepared.is_noop());
    let mut noop = prepared;
    noop.harness.as_mut().expect("harness leg").changed = false;
    assert!(noop.is_noop());
}

#[test]
fn pull_request_text_preserves_selected_legs() {
    let plan = changed_plan();
    let current_shards = plan
        .harness
        .as_ref()
        .expect("harness plan")
        .current_shards
        .clone();
    let prepared = approved_response(&plan)
        .into_prepared(
            RebalanceKind::All,
            GitHubRepositoryRef::new("owner", "repo").expect("fixture repository"),
            Some(current_shards),
        )
        .expect("complete response prepares all legs");
    let mut body_arguments = arguments();
    body_arguments.kind = RebalanceKind::All;
    body_arguments.experimental_wall_clock_override = Some("experiment-42".to_owned());
    let body = pull_request_body(&body_arguments, &prepared);
    assert!(body.contains("- Legs: harness, rust"));
    assert!(body.contains("- Files: Makefile"));
    assert!(body.contains("- Harness predicted packed spread: 4.0s"));
    assert!(body.contains("- Rust coverage shards: 1 to 1"));
    assert!(body.contains("- Experimental wall-clock override: experiment-42"));
    assert!(body.ends_with('\n'));

    let mut rust_only = prepared;
    rust_only.harness = None;
    rust_only.kind = RebalanceKind::Rust;
    let mut rust_arguments = body_arguments;
    rust_arguments.kind = RebalanceKind::Rust;
    let body = pull_request_body(&rust_arguments, &rust_only);
    assert!(!body.contains("- Experimental wall-clock override:"));
}

#[test]
fn plan_response_rejects_incomplete_selected_legs() {
    let missing = PlanResponse {
        decision: "approved".to_owned(),
        violations: Vec::new(),
        harness: None,
        rust: None,
    };
    assert!(
        missing
            .into_prepared(
                RebalanceKind::All,
                GitHubRepositoryRef::new("owner", "repo").expect("fixture repository"),
                None,
            )
            .is_err()
    );
    let unexpected_harness = PlanResponse {
        decision: "approved".to_owned(),
        violations: Vec::new(),
        harness: Some(PlanHarnessResponse {
            proposed_shards: BTreeMap::new(),
            predicted_proposed: BTreeMap::new(),
            baseline_slowest_wall_clock: 0.0,
            baseline_runner_seconds: 0.0,
            approved_slowest_wall_clock: 0.0,
            is_noop: true,
        }),
        rust: None,
    };
    assert!(
        unexpected_harness
            .into_prepared(
                RebalanceKind::Harness,
                GitHubRepositoryRef::new("owner", "repo").expect("fixture repository"),
                None,
            )
            .is_err()
    );
    assert_eq!(
        format_plan_rejection(&PlanResponse {
            decision: "rejected".to_owned(),
            violations: Vec::new(),
            harness: None,
            rust: None,
        }),
        "rebalance plan was rejected"
    );
    assert_eq!(
        format_plan_rejection(&PlanResponse {
            decision: "rejected".to_owned(),
            violations: vec!["fresh main required".to_owned()],
            harness: None,
            rust: None,
        }),
        "rebalance plan was rejected: fresh main required"
    );
}

#[test]
fn selected_leg_responses_and_pull_request_text_remain_specific() {
    let repository = GitHubRepositoryRef::new("owner", "repo").expect("fixture repository");
    let harness_plan = harness_only_plan();
    let harness_shards = harness_plan
        .harness
        .as_ref()
        .expect("harness plan")
        .current_shards
        .clone();
    let mut harness_response = approved_response(&changed_plan());
    harness_response.rust = None;
    let harness = harness_response
        .into_prepared(
            RebalanceKind::Harness,
            repository.clone(),
            Some(harness_shards),
        )
        .expect("harness response prepares only its selected leg");
    let harness_body = pull_request_body(&arguments(), &harness);
    assert!(harness_body.contains("- Legs: harness"));
    assert!(harness_body.contains("- Files: Makefile"));

    let mut rust_response = approved_response(&changed_plan());
    rust_response.harness = None;
    let rust = rust_response.rust.as_mut().expect("Rust response");
    rust.shard_count = 4;
    rust.approved_slowest_wall_clock = 480.0;
    rust.is_noop = false;
    let rust = rust_response
        .into_prepared(
            RebalanceKind::Rust,
            GitHubRepositoryRef::new("owner", "repo").expect("fixture repository"),
            None,
        )
        .expect("Rust response prepares only its selected leg");
    let rust_body = pull_request_body(&arguments(), &rust);
    assert!(rust_body.contains("- Legs: rust"));
    assert!(rust_body.contains("- Files: .github/workflows/ci.yaml"));
    assert!(rust_body.contains("- Rust coverage shards: 1 to 4"));
    assert!(!rust_body.contains("Harness baseline"));
}

#[test]
fn single_leg_requests_require_only_the_matching_evidence() {
    let (harness_timing, jobs_timing, rust_timing) = timing_reports();
    let harness_plan = harness_only_plan();
    let mut harness_arguments = arguments();
    harness_arguments.kind = RebalanceKind::Harness;
    let harness_shards = &harness_plan
        .harness
        .as_ref()
        .expect("harness plan")
        .current_shards;

    let requested: serde_json::Value = serde_json::from_str(
        &plan_request(
            &harness_arguments,
            &PlanRequestEvidence {
                current_harness: Some(harness_shards),
                harness_timing: Some(&harness_timing),
                jobs_timing: Some(&jobs_timing),
                current_rust_shard_count: None,
                rust_timing: None,
            },
        )
        .expect("render harness planning request"),
    )
    .expect("parse harness planning request");
    assert_eq!(requested["selection"], "harness");
    assert!(requested.get("python").is_none());
    assert!(
        plan_request(
            &harness_arguments,
            &PlanRequestEvidence {
                current_harness: Some(harness_shards),
                harness_timing: None,
                jobs_timing: Some(&jobs_timing),
                current_rust_shard_count: None,
                rust_timing: None,
            },
        )
        .is_err()
    );
    assert!(
        verify_request(
            &harness_arguments,
            &harness_plan,
            &[17],
            Some(&harness_timing),
            None,
            None,
        )
        .is_err()
    );

    let rust_plan = rust_only_plan();
    let mut rust_arguments = arguments();
    rust_arguments.kind = RebalanceKind::Rust;
    let verified: serde_json::Value = serde_json::from_str(
        &verify_request(
            &rust_arguments,
            &rust_plan,
            &[18],
            None,
            None,
            Some(&rust_timing),
        )
        .expect("render Rust verification request"),
    )
    .expect("parse Rust verification request");
    assert_eq!(verified["selection"], "rust");
    assert!(verified["harness"].is_null());
    assert!(
        plan_request(
            &rust_arguments,
            &PlanRequestEvidence {
                current_harness: None,
                harness_timing: None,
                jobs_timing: None,
                current_rust_shard_count: Some(4),
                rust_timing: None,
            },
        )
        .is_err()
    );
}

#[test]
fn workflow_helpers_cover_every_rebalance_kind_and_noop_recovery() {
    assert!(RebalanceKind::Harness.includes_harness());
    assert!(RebalanceKind::Rust.includes_rust());
    assert!(RebalanceKind::All.includes_rust());
    assert_eq!(RebalanceKind::Harness.wire(), "harness");
    assert_eq!(RebalanceKind::Rust.wire(), "rust");
    assert_eq!(RebalanceKind::Harness.commit_label(), "harness");
    assert_eq!(RebalanceKind::Rust.commit_label(), "rust");
    assert_eq!(RebalanceKind::All.commit_label(), "harness+rust");
    assert_eq!(Artifact::Makefile.path(), MAKEFILE);
    assert_eq!(Artifact::CiWorkflow.path(), CI_WORKFLOW);
    assert_eq!(
        predicted_packed_spread(&BTreeMap::from([(1, 10.0), (2, 6.0)])).to_bits(),
        4.0_f64.to_bits()
    );
    assert_eq!(
        predicted_packed_spread(&BTreeMap::new()).to_bits(),
        0.0_f64.to_bits()
    );

    let fixture = GitFixture::new();
    let mut workflow = fixture.workflow();
    let mut unchanged = changed_plan();
    unchanged.harness.as_mut().expect("harness plan").changed = false;
    unchanged.rust.as_mut().expect("Rust plan").changed = false;
    assert_eq!(
        workflow
            .write_candidates(&unchanged)
            .expect("unchanged plan writes nothing"),
        Vec::<Artifact>::new()
    );
    assert_eq!(workflow.recover_publish_failure(&[], "unused"), Ok(()));
}

#[test]
fn workflow_run_helpers_require_a_single_completed_success() {
    let head_sha = "a".repeat(40);
    let successful = WorkflowRun {
        database_id: 7,
        status: "completed".to_owned(),
        conclusion: Some("success".to_owned()),
        head_sha: head_sha.clone(),
        event: WORKFLOW_EVENT.to_owned(),
        workflow_name: "CI".to_owned(),
        attempt: 1,
    };
    let filters = verification_run_filters("ci.yaml", "rebalance-fixture", &head_sha);
    assert_eq!(filters.workflow.as_deref(), Some("ci.yaml"));
    assert_eq!(filters.branch.as_deref(), Some("rebalance-fixture"));
    assert_eq!(filters.event.as_deref(), Some(WORKFLOW_EVENT));
    assert_eq!(filters.commit.as_deref(), Some(head_sha.as_str()));
    assert_eq!(
        workflow_ids_from_runs(vec![successful.clone()], &head_sha),
        Ok(vec![7])
    );
    let runtime = LarchRuntime::new().expect("test runtime");
    assert_eq!(
        runtime.block_on(wait_for_completed_run_from(
            || std::future::ready(Ok(vec![successful.clone()])),
            &head_sha,
            &[],
        )),
        Ok(7)
    );
    assert_eq!(
        select_verification_run(std::slice::from_ref(&successful), &[7], &head_sha),
        Ok(None)
    );
    let mut pending = successful.clone();
    pending.status = "queued".to_owned();
    assert_eq!(
        select_verification_run(&[pending], &[], &head_sha),
        Ok(None)
    );
    let mut failed = successful.clone();
    failed.conclusion = Some("failure".to_owned());
    assert!(select_verification_run(&[failed], &[], &head_sha).is_err());
    let mut wrong_head = successful;
    wrong_head.head_sha = "b".repeat(40);
    assert!(workflow_ids_from_runs(vec![wrong_head], &head_sha).is_err());
}

#[test]
fn offline_success_fixture_writes_publishes_and_verifies() {
    let mut fixture = FixtureWorkflow::new(None, false);
    assert_eq!(execute(&mut fixture, &arguments()), Ok(ExitCode::SUCCESS));
    assert_eq!(
        fixture.events,
        ["prepare", "revalidate", "write", "publish", "verify"]
    );
}

#[test]
fn offline_noop_and_dry_run_fixtures_never_mutate() {
    for (noop, dry_run) in [(true, false), (false, true)] {
        let mut arguments = arguments();
        arguments.dry_run = dry_run;
        let mut fixture = FixtureWorkflow::new(None, noop);
        assert_eq!(execute(&mut fixture, &arguments), Ok(ExitCode::SUCCESS));
        assert_eq!(fixture.events, ["prepare"]);
    }
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
fn offline_post_plan_staleness_refuses_before_writes() {
    let mut fixture = FixtureWorkflow::new(Some(Failure::StaleBeforeWrite), false);
    assert!(execute(&mut fixture, &arguments()).is_err());
    assert_eq!(fixture.events, ["prepare", "revalidate"]);
}

#[test]
fn offline_candidate_write_fixture_rolls_back_before_publish() {
    let mut fixture = FixtureWorkflow::new(Some(Failure::Write), false);
    assert!(execute(&mut fixture, &arguments()).is_err());
    assert_eq!(
        fixture.events,
        ["prepare", "revalidate", "write", "write-rollback"]
    );
}

#[test]
fn offline_push_or_pr_failure_fixture_restores_candidates_and_branch() {
    let mut fixture = FixtureWorkflow::new(Some(Failure::Publish), false);
    assert!(execute(&mut fixture, &arguments()).is_err());
    assert_eq!(
        fixture.events,
        [
            "prepare",
            "revalidate",
            "write",
            "publish",
            "publish-rollback"
        ]
    );
}

#[test]
fn offline_verification_failure_fixture_keeps_the_created_pr() {
    let mut fixture = FixtureWorkflow::new(Some(Failure::Verify), false);
    assert!(execute(&mut fixture, &arguments()).is_err());
    assert_eq!(
        fixture.events,
        ["prepare", "revalidate", "write", "publish", "verify"]
    );
}

#[test]
fn parsers_accept_safe_rebalance_inputs() {
    assert_eq!(parse_run_count("1"), Ok(1));
    assert_eq!(
        parse_run_count(&larch_core::MAX_CI_TIMING_RUNS.to_string()),
        Ok(larch_core::MAX_CI_TIMING_RUNS)
    );
    assert_eq!(parse_rust_shard_count("4"), Ok(4));
    assert_eq!(parse_positive_f64("1.5"), Ok(1.5));
    assert_eq!(
        parse_experiment_note(" experiment-42 "),
        Ok("experiment-42".to_owned())
    );
    assert_eq!(
        parse_branch_prefix("rebalance-123"),
        Ok("rebalance-123".to_owned())
    );
    assert_eq!(parse_selector("ci.yaml"), Ok("ci.yaml".to_owned()));
    let affinity = parse_compile_affinity("target=group:0.5").expect("valid affinity");
    assert_eq!(affinity.target, "target");
    assert_eq!(affinity.group, "group");
    assert!((affinity.setup_seconds - 0.5).abs() < f64::EPSILON);
}

#[test]
fn parsers_reject_unsafe_rebalance_inputs() {
    assert!(parse_run_count("0").is_err());
    assert!(parse_run_count("not-a-number").is_err());
    assert!(parse_rust_shard_count("0").is_err());
    assert!(parse_rust_shard_count("33").is_err());
    assert!(parse_positive_f64("NaN").is_err());
    assert!(parse_experiment_note(" \t ").is_err());
    assert!(parse_branch_prefix("branch;rm").is_err());
    assert!(parse_branch_prefix("Uppercase").is_err());
    assert!(parse_selector("main branch").is_err());
    assert!(parse_selector("-branch").is_err());
    assert!(parse_compile_affinity("target=group:0\n").is_err());
    assert!(parse_compile_affinity("target=group:-1").is_err());
}

#[test]
fn explicit_repository_must_match_origin() {
    let origin = GitHubRepositoryRef::new("owner", "repo").unwrap();
    assert_eq!(
        selected_repository(None, origin.clone()),
        Ok(origin.clone())
    );
    assert_eq!(
        selected_repository(Some(&origin), origin.clone()),
        Ok(origin.clone())
    );
    assert!(
        selected_repository(
            Some(&GitHubRepositoryRef::new("other", "repo").unwrap()),
            origin
        )
        .is_err()
    );
}

#[test]
fn verification_run_selection_requires_one_matching_dispatch() {
    let run = |id: u64, event: &str, head_sha: &str, status: &str| WorkflowRun {
        database_id: id,
        status: status.to_owned(),
        conclusion: Some("success".to_owned()),
        head_sha: head_sha.to_owned(),
        event: event.to_owned(),
        workflow_name: "CI".to_owned(),
        attempt: 1,
    };
    let expected = "a";
    assert_eq!(
        select_verification_run(
            &[run(2, WORKFLOW_EVENT, expected, "completed")],
            &[],
            expected
        ),
        Ok(Some(2))
    );
    assert!(
        select_verification_run(&[run(3, "push", expected, "completed")], &[], expected).is_err()
    );
    assert!(
        select_verification_run(
            &[
                run(4, WORKFLOW_EVENT, expected, "completed"),
                run(5, WORKFLOW_EVENT, expected, "completed")
            ],
            &[],
            expected
        )
        .is_err()
    );
}

#[test]
fn subject_matches_the_active_contract() {
    assert_eq!(
        commit_subject(RebalanceKind::All),
        "chore: rebalance test shards (harness+rust)"
    );
}
