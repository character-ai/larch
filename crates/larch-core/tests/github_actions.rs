//! Public-contract coverage for GitHub Actions log rendering.

use larch_core::{
    CheckRun, GitHubActionsError, GitHubActionsErrorKind, GitHubActionsFuture,
    GitHubActionsService, GitHubCloseReason, GitHubComment, GitHubFuture, GitHubIssue,
    GitHubIssueCreate, GitHubIssueEdit, GitHubIssueList, GitHubIssueSearch, GitHubLabel,
    GitHubLabelCreate, GitHubMutationOutcome, GitHubRepository, GitHubRepositoryRef, GitHubService,
    GitHubTransportPolicy, ProcessCancellation, WorkflowDispatchRequest, WorkflowJob,
    WorkflowLogArchive, WorkflowRun, WorkflowRunFilters, run_logs, run_logs_setup_failure,
    workflow_path,
};
use std::{
    future::Future,
    io::Write,
    pin::Pin,
    task::{Context, Poll, Waker},
};

struct NeverCancelled;

impl ProcessCancellation for NeverCancelled {
    fn is_cancelled(&self) -> bool {
        false
    }

    fn cancelled(&self) -> Pin<Box<dyn Future<Output = ()> + Send + '_>> {
        Box::pin(std::future::pending())
    }
}

#[derive(Clone)]
struct FakeService {
    run: Result<WorkflowRun, GitHubActionsError>,
    archive: Result<WorkflowLogArchive, GitHubActionsError>,
    jobs: Result<Vec<WorkflowJob>, GitHubActionsError>,
}

fn unused_github<T>() -> GitHubFuture<'static, T> {
    Box::pin(async { panic!("unused GitHub service operation") })
}

fn unused_actions<T>() -> GitHubActionsFuture<'static, T> {
    Box::pin(async { panic!("unused GitHub Actions service operation") })
}

impl GitHubService for FakeService {
    fn transport_policy(&self) -> GitHubTransportPolicy {
        GitHubTransportPolicy::github_com()
    }

    fn repository<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubRepository> {
        unused_github()
    }

    fn issue<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _number: u64,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        unused_github()
    }

    fn list_issues<'a>(
        &'a self,
        _request: &'a GitHubIssueList,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubIssue>> {
        unused_github()
    }

    fn search_issues<'a>(
        &'a self,
        _request: &'a GitHubIssueSearch,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubIssue>> {
        unused_github()
    }

    fn create_issue<'a>(
        &'a self,
        _request: &'a GitHubIssueCreate,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        unused_github()
    }

    fn edit_issue<'a>(
        &'a self,
        _request: &'a GitHubIssueEdit,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        unused_github()
    }

    fn close_issue<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _number: u64,
        _reason: GitHubCloseReason,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubIssue> {
        unused_github()
    }

    fn list_comments<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _number: u64,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubComment>> {
        unused_github()
    }

    fn create_comment<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _number: u64,
        _body: &'a str,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubComment> {
        unused_github()
    }

    fn edit_comment<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _comment_id: u64,
        _body: &'a str,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubComment> {
        unused_github()
    }

    fn delete_comment<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _comment_id: u64,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, ()> {
        unused_github()
    }

    fn list_labels<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>> {
        unused_github()
    }

    fn create_label<'a>(
        &'a self,
        _request: &'a GitHubLabelCreate,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, GitHubLabel> {
        unused_github()
    }

    fn add_label<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _number: u64,
        _label: &'a str,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>> {
        unused_github()
    }

    fn remove_label<'a>(
        &'a self,
        _repo: &'a GitHubRepositoryRef,
        _number: u64,
        _label: &'a str,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubFuture<'a, Vec<GitHubLabel>> {
        unused_github()
    }
}

impl GitHubActionsService for FakeService {
    fn list_workflow_runs<'a>(
        &'a self,
        _repository: &'a GitHubRepositoryRef,
        _filters: &'a WorkflowRunFilters,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'a, Vec<WorkflowRun>> {
        unused_actions()
    }

    fn workflow_run<'a>(
        &'a self,
        _repository: &'a GitHubRepositoryRef,
        _run_id: u64,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'a, WorkflowRun> {
        Box::pin(async move { self.run.clone() })
    }

    fn workflow_jobs<'a>(
        &'a self,
        _repository: &'a GitHubRepositoryRef,
        _run_id: u64,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'a, Vec<WorkflowJob>> {
        Box::pin(async move { self.jobs.clone() })
    }

    fn check_runs<'a>(
        &'a self,
        _repository: &'a GitHubRepositoryRef,
        _git_reference: &'a str,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'a, Vec<CheckRun>> {
        unused_actions()
    }

    fn rerun_workflow<'a>(
        &'a self,
        _repository: &'a GitHubRepositoryRef,
        _run_id: u64,
        _failed_only: bool,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'a, GitHubMutationOutcome> {
        unused_actions()
    }

    fn dispatch_workflow<'a>(
        &'a self,
        _request: &'a WorkflowDispatchRequest,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'a, GitHubMutationOutcome> {
        unused_actions()
    }

    fn download_workflow_logs<'a>(
        &'a self,
        _repository: &'a GitHubRepositoryRef,
        _run_id: u64,
        _cancellation: &'a dyn ProcessCancellation,
    ) -> GitHubActionsFuture<'a, WorkflowLogArchive> {
        Box::pin(async move { self.archive.clone() })
    }
}

fn block_on<F: Future>(future: F) -> F::Output {
    let waker = Waker::noop();
    let mut context = Context::from_waker(waker);
    let mut future = std::pin::pin!(future);
    match future.as_mut().poll(&mut context) {
        Poll::Ready(value) => value,
        Poll::Pending => panic!("test future unexpectedly yielded"),
    }
}

fn repository() -> GitHubRepositoryRef {
    GitHubRepositoryRef::new("character-ai", "larch").expect("repository")
}

fn completed_run() -> WorkflowRun {
    WorkflowRun {
        database_id: 42,
        status: "completed".to_owned(),
        conclusion: Some("failure".to_owned()),
        head_sha: "a".repeat(40),
        event: "push".to_owned(),
        attempt: 1,
    }
}

fn archive(entries: &[(&str, &[u8])]) -> WorkflowLogArchive {
    let mut writer = zip::ZipWriter::new(std::io::Cursor::new(Vec::new()));
    let options = zip::write::SimpleFileOptions::default();
    for (name, contents) in entries {
        writer
            .start_file(name, options)
            .expect("start archive entry");
        writer.write_all(contents).expect("write archive entry");
    }
    WorkflowLogArchive::new(writer.finish().expect("finish archive").into_inner())
}

const fn fake(
    run: Result<WorkflowRun, GitHubActionsError>,
    archive: Result<WorkflowLogArchive, GitHubActionsError>,
    jobs: Result<Vec<WorkflowJob>, GitHubActionsError>,
) -> FakeService {
    FakeService { run, archive, jobs }
}

#[test]
fn workflow_path_keeps_its_legacy_contract() {
    assert_eq!(workflow_path(), "unknown\n");
}

#[test]
fn run_logs_renders_only_failed_jobs_with_the_legacy_pointer() {
    let service = fake(
        Ok(completed_run()),
        Ok(archive(&[
            ("failed/output.txt", b"failure details"),
            ("passed/output.txt", b"ok"),
        ])),
        Ok(vec![
            WorkflowJob {
                name: "failed".to_owned(),
                status: "completed".to_owned(),
                conclusion: Some("failure".to_owned()),
                wall_clock_seconds: Some(3.0),
            },
            WorkflowJob {
                name: "passed".to_owned(),
                status: "completed".to_owned(),
                conclusion: Some("success".to_owned()),
                wall_clock_seconds: Some(2.0),
            },
        ]),
    );
    let cancellation = NeverCancelled;

    let output = block_on(run_logs(&service, &repository(), 42, &cancellation));

    assert_eq!(output.exit_code(), 0);
    assert_eq!(
        output.stdout(),
        b"--- CI log (run 42, repo character-ai/larch): failed-job log shown. Full log: https://github.com/character-ai/larch/actions/runs/42 ---\nfailure details\n"
    );
}

#[test]
fn run_logs_handles_empty_failed_output_and_rejects_entry_floods() {
    let cancellation = NeverCancelled;
    let mut writer = zip::ZipWriter::new(std::io::Cursor::new(Vec::new()));
    let options = zip::write::SimpleFileOptions::default();
    writer
        .add_directory("failed/", options)
        .expect("directory entry");
    writer
        .start_file("passed/output.txt", options)
        .expect("passed entry");
    writer.write_all(b"ignored").expect("passed output");
    let empty_failed_output = fake(
        Ok(completed_run()),
        Ok(WorkflowLogArchive::new(
            writer.finish().expect("finish archive").into_inner(),
        )),
        Ok(vec![WorkflowJob {
            name: "failed".to_owned(),
            status: "completed".to_owned(),
            conclusion: Some("failure".to_owned()),
            wall_clock_seconds: None,
        }]),
    );
    let output = block_on(run_logs(
        &empty_failed_output,
        &repository(),
        42,
        &cancellation,
    ));
    assert_eq!(output.exit_code(), 0);
    assert_eq!(
        output.stdout(),
        b"--- CI log (run 42, repo character-ai/larch): failed-job log shown. Full log: https://github.com/character-ai/larch/actions/runs/42 ---\n"
    );

    let mut writer = zip::ZipWriter::new(std::io::Cursor::new(Vec::new()));
    for index in 0..1_025 {
        writer
            .start_file(
                format!("failed/{index}.txt"),
                zip::write::SimpleFileOptions::default(),
            )
            .expect("flood entry");
    }
    let flood = fake(
        Ok(completed_run()),
        Ok(WorkflowLogArchive::new(
            writer.finish().expect("finish flood").into_inner(),
        )),
        Ok(Vec::new()),
    );
    let output = block_on(run_logs(&flood, &repository(), 42, &cancellation));
    assert_eq!(output.exit_code(), 1);
    assert!(
        std::str::from_utf8(output.stdout())
            .expect("UTF-8 output")
            .contains("archive is invalid or exceeds its limit")
    );
}

#[test]
fn run_logs_preserves_incomplete_invalid_and_service_failure_contracts() {
    let cancellation = NeverCancelled;
    let incomplete = fake(
        Ok(WorkflowRun {
            status: "in_progress".to_owned(),
            ..completed_run()
        }),
        Ok(WorkflowLogArchive::new(Vec::new())),
        Ok(Vec::new()),
    );
    let output = block_on(run_logs(&incomplete, &repository(), 42, &cancellation));
    assert_eq!(output.exit_code(), 3);
    assert!(
        std::str::from_utf8(output.stdout())
            .expect("UTF-8 output")
            .contains("run is still in progress")
    );

    let transport = GitHubActionsError::new(GitHubActionsErrorKind::Transport, "offline");
    let run_failure = fake(
        Err(transport.clone()),
        Ok(WorkflowLogArchive::new(Vec::new())),
        Ok(Vec::new()),
    );
    let output = block_on(run_logs(&run_failure, &repository(), 42, &cancellation));
    assert_eq!(output.exit_code(), 1);
    assert!(output.stdout().ends_with(b"offline\n"));

    let download_failure = fake(Ok(completed_run()), Err(transport.clone()), Ok(Vec::new()));
    let output = block_on(run_logs(
        &download_failure,
        &repository(),
        42,
        &cancellation,
    ));
    assert_eq!(output.exit_code(), 1);
    assert!(output.stdout().ends_with(b"offline\n"));

    let jobs_failure = fake(
        Ok(completed_run()),
        Ok(WorkflowLogArchive::new(Vec::new())),
        Err(transport.clone()),
    );
    let output = block_on(run_logs(&jobs_failure, &repository(), 42, &cancellation));
    assert_eq!(output.exit_code(), 1);
    assert!(output.stdout().ends_with(b"offline\n"));

    let invalid_archive = fake(
        Ok(completed_run()),
        Ok(WorkflowLogArchive::new(b"not a zip".to_vec())),
        Ok(Vec::new()),
    );
    let output = block_on(run_logs(&invalid_archive, &repository(), 42, &cancellation));
    assert_eq!(output.exit_code(), 1);
    assert!(
        std::str::from_utf8(output.stdout())
            .expect("UTF-8 output")
            .contains("archive is invalid")
    );

    let output = run_logs_setup_failure(&repository(), 42, transport);
    assert_eq!(output.exit_code(), 1);
    assert!(output.stdout().ends_with(b"offline\n"));
}
