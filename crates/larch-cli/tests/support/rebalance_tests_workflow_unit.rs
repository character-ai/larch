use super::*;
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
        fs::create_dir_all(root.path().join("python")).expect("create assignments directory");
        fs::write(
            root.path().join(MAKEFILE),
            "test-harnesses-1: test-harness-shards-coverage alpha\n\
             test-harnesses-2: beta\n",
        )
        .expect("write fixture Makefile");
        fs::write(root.path().join(ASSIGNMENTS), "{\n  \"test::old\": 1\n}\n")
            .expect("write fixture assignments");
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
            baseline_slowest_wall_clock: 10.0,
            baseline_runner_seconds: 18.0,
            approved_slowest_wall_clock: 12.0,
            changed: true,
        }),
        python: Some(PythonPlan {
            assignments: BTreeMap::from([("test::one".to_owned(), 1), ("test::two".to_owned(), 2)]),
            shard_count: 2,
            changed: true,
        }),
        decision: "approved".to_owned(),
    }
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
            baseline_slowest_wall_clock: 10.0,
            baseline_runner_seconds: 18.0,
            approved_slowest_wall_clock: 12.0,
            is_noop: false,
        }),
        python: Some(PlanPythonResponse {
            assignments: plan
                .python
                .as_ref()
                .expect("python plan")
                .assignments
                .clone(),
            shard_count: 2,
            is_noop: false,
        }),
    }
}

fn timing_reports() -> (
    larch_core::HarnessTimingReport,
    larch_core::JobTimingReport,
    larch_core::PytestTimingReport,
) {
    let harness = serde_json::from_value(json!({
        "schema_version": 1,
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
        "schema_version": 1,
        "kind": "jobs",
        "sampled_run_ids": [11],
        "rows": [],
        "shard_medians": [],
        "skipped_run_ids": [],
    }))
    .expect("fixture job timing report");
    let pytest = serde_json::from_value(json!({
        "schema_version": 1,
        "kind": "pytest",
        "sampled_run_ids": [11],
        "rows": [],
        "nodeid_medians": [],
        "shard_medians": [],
        "observed_shard_count": 2,
        "skipped_run_ids": [],
    }))
    .expect("fixture pytest timing report");
    (harness, jobs, pytest)
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
    let original_assignments = fs::read_to_string(fixture.root.path().join(ASSIGNMENTS))
        .expect("read fixture assignments");

    workflow
        .fetch_and_require_immutable_main()
        .expect("fixture main is immutable and clean");
    let artifacts = workflow
        .write_candidates(&plan)
        .expect("write candidate artifacts");
    assert_eq!(artifacts, [Artifact::Makefile, Artifact::Assignments]);
    assert_ne!(
        fs::read_to_string(fixture.root.path().join(MAKEFILE)).expect("read candidate Makefile"),
        original_makefile
    );
    assert_ne!(
        fs::read_to_string(fixture.root.path().join(ASSIGNMENTS))
            .expect("read candidate assignments"),
        original_assignments
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
    assert_eq!(
        fs::read_to_string(fixture.root.path().join(ASSIGNMENTS))
            .expect("read restored assignments"),
        original_assignments
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
    request_arguments.n_python_shards = Some(2);
    request_arguments.experimental_wall_clock_override = Some("experiment-42".to_owned());
    request_arguments.compile_affinity = vec![CompileAffinityArgument {
        target: "crate-a".to_owned(),
        group: "compile".to_owned(),
        setup_seconds: 2.5,
    }];
    let plan = changed_plan();
    let harness_map = &plan.harness.as_ref().expect("harness plan").current_shards;
    let assignments = &plan.python.as_ref().expect("python plan").assignments;
    let (harness, jobs, pytest) = timing_reports();

    let planned: serde_json::Value = serde_json::from_str(
        &plan_request(
            &request_arguments,
            Some(harness_map),
            Some(&harness),
            Some(&jobs),
            Some(assignments),
            Some(&pytest),
        )
        .expect("render planning request"),
    )
    .expect("parse planning request");
    assert_eq!(planned["kind"], "plan");
    assert_eq!(planned["selection"], "all");
    assert_eq!(planned["harness"]["expected_run_ids"], json!([11]));
    assert_eq!(planned["python"]["expected_run_ids"], json!([11]));
    assert_eq!(
        planned["options"]["compile_affinities"][0]["target"],
        "crate-a"
    );
    assert!(
        plan_request(
            &request_arguments,
            Some(harness_map),
            None,
            Some(&jobs),
            Some(assignments),
            Some(&pytest),
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
            Some(&pytest),
        )
        .expect("render verification request"),
    )
    .expect("parse verification request");
    assert_eq!(verified["kind"], "verify");
    assert_eq!(verified["harness"]["expected_run_ids"], json!([21, 22]));
    assert_eq!(verified["python"]["expected_shard_count"], 2);
    assert!(
        verify_request(
            &request_arguments,
            &plan,
            &[21],
            None,
            Some(&jobs),
            Some(&pytest),
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
        .expect("complete response prepares both legs");
    assert!(!prepared.is_noop());
    let mut noop = prepared;
    noop.harness.as_mut().expect("harness leg").changed = false;
    noop.python.as_mut().expect("python leg").changed = false;
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
        .expect("complete response prepares both legs");
    let mut body_arguments = arguments();
    body_arguments.kind = RebalanceKind::All;
    body_arguments.experimental_wall_clock_override = Some("experiment-42".to_owned());
    let body = pull_request_body(&body_arguments, &prepared);
    assert!(body.contains("- Legs: harness, python"));
    assert!(body.contains("- Files: Makefile, python/shard-assignments.json"));
    assert!(body.contains("- Experimental wall-clock override: experiment-42"));
    assert!(body.ends_with('\n'));
}

#[test]
fn plan_response_rejects_incomplete_selected_legs() {
    let missing = PlanResponse {
        decision: "approved".to_owned(),
        violations: Vec::new(),
        harness: None,
        python: None,
    };
    assert!(
        missing
            .into_prepared(
                RebalanceKind::Python,
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
            baseline_slowest_wall_clock: 0.0,
            baseline_runner_seconds: 0.0,
            approved_slowest_wall_clock: 0.0,
            is_noop: true,
        }),
        python: None,
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
            python: None,
        }),
        "rebalance plan was rejected"
    );
    assert_eq!(
        format_plan_rejection(&PlanResponse {
            decision: "rejected".to_owned(),
            violations: vec!["fresh main required".to_owned()],
            harness: None,
            python: None,
        }),
        "rebalance plan was rejected: fresh main required"
    );
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
    assert_eq!(parse_positive_u32("2"), Ok(2));
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
    assert!(parse_positive_u32("0").is_err());
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
