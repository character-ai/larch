//! Offline design-domain fixtures, snapshots, and GitHub replay helpers.
//!
//! Session fixtures own all state below a private temporary root and never
//! change process-global environment or working directory. GitHub replay reuses
//! [`IssueServiceStub`] so later design leaves can exercise clarify, pause, and
//! mutation-conflict recovery offline.

use std::{
    fmt,
    fs, io,
    path::{Path, PathBuf},
};

use crate::{
    BoundedBytes, ExecutionSnapshot, IssueServiceExchange, IssueServiceStub, ParityDifference,
    TestWorkspace,
    filesystem::validate_relative,
    snapshot_util::{
        file_mode, fnv1a, path_bytes, redact_matching_lines, replace_all, sorted_children,
    },
};

const DESIGN_SESSION_SNAPSHOT_SCHEMA: u32 = 1;
const DESIGN_STDOUT_SNAPSHOT_SCHEMA: u32 = 1;
const ENTRY_LIMIT: usize = 512;
const STDOUT_FIELD_LIMIT: usize = 256;
const DEFAULT_PPID: u32 = 4242;
const DEFAULT_ISSUE: u64 = 7680;
const DEFAULT_RUN_ID: &str = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";
const DEFAULT_REPOSITORY: &str = "character-ai/larch";

const SENSITIVE_LINE_NEEDLES: [&[u8]; 10] = [
    b"authorization",
    b"bearer ",
    b"password",
    b"credential",
    b"api_key",
    b"api-key",
    b"access_token",
    b"secret-token",
    b"token=",
    b"\"token\":",
];

const GITHUB_TOKEN_PREFIXES: [&[u8]; 6] =
    [b"ghp_", b"gho_", b"ghs_", b"ghu_", b"ghr_", b"github_pat_"];

/// Named design-session shape used by design-domain parity tests.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DesignFixture {
    Absent,
    Partial,
    Conflicting,
    Committed,
}

impl DesignFixture {
    /// Return the semantic state represented by this fixture.
    #[must_use]
    pub const fn state(self) -> DesignSessionState {
        match self {
            Self::Absent => DesignSessionState::Absent,
            Self::Partial => DesignSessionState::Partial,
            Self::Conflicting => DesignSessionState::Conflicting,
            Self::Committed => DesignSessionState::Committed,
        }
    }
}

/// Coarse semantic completeness of a design session fixture.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DesignSessionState {
    Absent,
    Partial,
    Conflicting,
    Committed,
}

impl DesignSessionState {
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Absent => "absent",
            Self::Partial => "partial",
            Self::Conflicting => "conflicting",
            Self::Committed => "committed",
        }
    }
}

/// Builder for one isolated design session under an owned temporary root.
#[derive(Clone, Debug)]
pub struct DesignSessionBuilder {
    fixture: DesignFixture,
    ppid: u32,
    issue_number: u64,
    repository_slug: String,
    run_id: String,
}

impl DesignSessionBuilder {
    #[must_use]
    pub fn new(fixture: DesignFixture) -> Self {
        Self {
            fixture,
            ppid: DEFAULT_PPID,
            issue_number: DEFAULT_ISSUE,
            repository_slug: DEFAULT_REPOSITORY.to_owned(),
            run_id: DEFAULT_RUN_ID.to_owned(),
        }
    }

    #[must_use]
    pub const fn ppid(mut self, ppid: u32) -> Self {
        self.ppid = ppid;
        self
    }

    #[must_use]
    pub const fn issue_number(mut self, issue_number: u64) -> Self {
        self.issue_number = issue_number;
        self
    }

    #[must_use]
    pub fn repository_slug(mut self, repository_slug: impl Into<String>) -> Self {
        self.repository_slug = repository_slug.into();
        self
    }

    #[must_use]
    pub fn run_id(mut self, run_id: impl Into<String>) -> Self {
        self.run_id = run_id.into();
        self
    }

    /// Build the fixture without changing the process environment or cwd.
    ///
    /// # Errors
    /// Returns private-workspace setup failures.
    pub fn build(self) -> io::Result<DesignSession> {
        let Self {
            fixture,
            ppid,
            issue_number,
            repository_slug,
            run_id,
        } = self;
        let workspace = TestWorkspace::new()?;
        let session = DesignSession {
            workspace,
            state: fixture.state(),
            ppid,
            issue_number,
            repository_slug,
            run_id,
        };
        session.materialize(fixture)?;
        Ok(session)
    }
}

/// An owned, isolated design session with issue wire, env, and run-log files.
#[derive(Debug)]
pub struct DesignSession {
    workspace: TestWorkspace,
    state: DesignSessionState,
    ppid: u32,
    issue_number: u64,
    repository_slug: String,
    run_id: String,
}

impl DesignSession {
    #[must_use]
    pub fn builder(fixture: DesignFixture) -> DesignSessionBuilder {
        DesignSessionBuilder::new(fixture)
    }

    #[must_use]
    pub fn root(&self) -> &Path {
        self.workspace.root()
    }

    #[must_use]
    pub const fn state(&self) -> DesignSessionState {
        self.state
    }

    #[must_use]
    pub const fn ppid(&self) -> u32 {
        self.ppid
    }

    #[must_use]
    pub const fn issue_number(&self) -> u64 {
        self.issue_number
    }

    #[must_use]
    pub fn repository_slug(&self) -> &str {
        &self.repository_slug
    }

    #[must_use]
    pub fn run_id(&self) -> &str {
        &self.run_id
    }

    /// Absolute path to the design temporary directory when present.
    #[must_use]
    pub fn design_tmpdir(&self) -> PathBuf {
        self.root().join("design-tmpdir")
    }

    /// Absolute path to the PID-keyed current design env file when present.
    #[must_use]
    pub fn current_design_env_path(&self) -> PathBuf {
        self.root().join(format!(
            "cache/larch/sessions/current-design-env-{}.sh",
            self.ppid
        ))
    }

    /// Absolute path to the issue body fixture when present.
    #[must_use]
    pub fn issue_body_path(&self) -> PathBuf {
        self.root().join("issue/body.md")
    }

    /// Absolute path to the design run-log staging tree when present.
    #[must_use]
    pub fn run_log_staging_path(&self) -> PathBuf {
        self.root()
            .join("larch-logs")
            .join("design")
            .join(&self.run_id)
    }

    fn materialize(&self, fixture: DesignFixture) -> io::Result<()> {
        match fixture {
            DesignFixture::Absent => Ok(()),
            DesignFixture::Partial => self.materialize_partial(),
            DesignFixture::Conflicting => self.materialize_conflicting(),
            DesignFixture::Committed => self.materialize_committed(),
        }
    }

    fn materialize_partial(&self) -> io::Result<()> {
        self.write_issue_body(
            "<!-- larch:plan:start -->\n\
             ### NEW: Partial plan heading\n\
             interrupted before end marker\n",
        )?;
        self.write_plan_document(
            "plan.txt",
            "### NEW: Partial plan heading\n\
             interrupted before end marker\n",
        )?;
        self.write_step_result_env(
            "step-2b.result.env",
            "STEP_STATUS=partial\n\
             PLAN_PATH=<DESIGN_TMPDIR>/plan.txt\n",
        )?;
        self.write_design_env(false)?;
        self.write_run_log_staging(
            "manifest.json",
            "{\n  \"schema\": 1,\n  \"skill\": \"design\",\n  \"status\": \"partial\"\n}\n",
        )?;
        Ok(())
    }

    fn materialize_conflicting(&self) -> io::Result<()> {
        self.write_issue_body(
            "## Conflicting design fixture\n\
             <!-- larch:plan:start -->\n\
             ### NEW: First plan\n\
             <!-- larch:plan:end -->\n\
             <!-- larch:plan:start -->\n\
             ### NEW: Second plan\n\
             <!-- larch:plan:end -->\n\
             <!-- larch:design-pause:start -->\n\
             ISSUE_NUMBER=<ISSUE>\n\
             REPO=<REPOSITORY>\n\
             RUN_ID=<RUN_ID>\n\
             STEP=step-3\n\
             SESSION_ID=<RUN_ID>\n\
             BRAINSTORM_DONE=true\n\
             BODY_HASH=deadbeef\n\
             PAUSED_AT=2026-08-01T00:00:00Z\n\
             <!-- larch:design-pause:end -->\n",
        )?;
        self.write_plan_document(
            "plan.txt",
            "### NEW: First plan\n\
             ### NEW: Second plan\n",
        )?;
        self.write_plan_document(
            "plan-grammar.md",
            "### NEW: First plan\n\
             ### UPDATED: Conflicting update\n\
             ### REWRITTEN: Conflicting rewrite\n\
             ### MAY_UPDATE: Optional cleanup\n\
             diff_lines: 12\n",
        )?;
        self.write_step_result_env(
            "step-3.result.env",
            "STEP_STATUS=conflict\n\
             CLARIFY_STATE=ambiguous\n\
             AUTH=Bearer ghp_fixturecredential\n",
        )?;
        self.write_step_result_env(
            "step-5b.result.env",
            "STEP_STATUS=conflict\n\
             ANNOTATION_STATUS=duplicate\n",
        )?;
        self.workspace.create_dir("design-tmpdir/.completed")?;
        self.workspace
            .write("design-tmpdir/.completed/step-3", b"completed\n")?;
        self.write_design_env(true)?;
        self.write_run_log_staging(
            "manifest.json",
            "{\n  \"schema\": 1,\n  \"skill\": \"design\",\n  \"status\": \"conflict\"\n}\n",
        )?;
        self.write_run_log_staging(
            "events.jsonl",
            "{\"event\":\"pause\",\"token\":\"ghp_fixturecredential\"}\n\
             {\"event\":\"clarify\",\"state\":\"ambiguous\"}\n",
        )?;
        Ok(())
    }

    fn materialize_committed(&self) -> io::Result<()> {
        self.write_issue_body(
            "## Committed design fixture\n\
             Repository: <REPOSITORY>\n\
             <!-- larch:plan:start -->\n\
             ### NEW: Land design fixtures\n\
             Files: crates/larch-test-support/src/design.rs\n\
             ### UPDATED: Document design fixture ownership\n\
             Files: docs/rust-testing.md\n\
             ### REWRITTEN: Keep stdout snapshot contract exact\n\
             ### MAY_UPDATE: Later leaf polish\n\
             diff_lines: 240\n\
             <!-- larch:plan:end -->\n\
             <!-- larch:design-pause:start -->\n\
             ISSUE_NUMBER=<ISSUE>\n\
             REPO=<REPOSITORY>\n\
             RUN_ID=<RUN_ID>\n\
             STEP=step-6\n\
             SESSION_ID=<RUN_ID>\n\
             BRAINSTORM_DONE=true\n\
             BODY_HASH=cafebabe\n\
             PAUSED_AT=2026-08-15T12:00:00Z\n\
             LOG_RECOVERY_BRANCH=larch-log-design-<RUN_ID>\n\
             <!-- larch:design-pause:end -->\n",
        )?;
        self.write_plan_document(
            "plan.txt",
            "### NEW: Land design fixtures\n\
             Files: crates/larch-test-support/src/design.rs\n\
             ### UPDATED: Document design fixture ownership\n\
             Files: docs/rust-testing.md\n\
             ### REWRITTEN: Keep stdout snapshot contract exact\n\
             ### MAY_UPDATE: Later leaf polish\n\
             diff_lines: 240\n",
        )?;
        self.write_plan_document(
            "plan-grammar.md",
            "### NEW: Land design fixtures\n\
             ### UPDATED: Document design fixture ownership\n\
             ### REWRITTEN: Keep stdout snapshot contract exact\n\
             ### MAY_UPDATE: Later leaf polish\n\
             diff_lines: 240\n",
        )?;
        self.write_step_result_env(
            "step-0.result.env",
            "STEP_STATUS=ok\n\
             DESIGN_TMPDIR=<DESIGN_TMPDIR>\n\
             ISSUE_NUMBER=<ISSUE>\n\
             SESSION_ID=<RUN_ID>\n",
        )?;
        self.write_step_result_env(
            "step-6.result.env",
            "STEP_STATUS=ok\n\
             GATE_C=pass\n\
             PUBLICATION=ready\n",
        )?;
        self.workspace
            .create_dir("design-tmpdir/.completed")?;
        self.workspace
            .write("design-tmpdir/.completed/step-0", b"ok\n")?;
        self.workspace
            .write("design-tmpdir/.completed/step-6", b"ok\n")?;
        self.workspace.write(
            "design-tmpdir/clarify-thread.md",
            "<!-- larch:clarify-request id=1 -->\n\
             ## Clarifications needed\n\
             - Q1: Confirm fixture ownership.\n\
             <!-- larch:clarify-response id=1 -->\n\
             ## Resolved\n\
             - Q1: larch-test-support owns design fixtures.\n",
        )?;
        self.write_design_env(true)?;
        self.write_run_log_staging(
            "manifest.json",
            "{\n  \"schema\": 1,\n  \"skill\": \"design\",\n  \"status\": \"committed\",\n  \"run_id\": \"<RUN_ID>\"\n}\n",
        )?;
        self.write_run_log_staging(
            "events.jsonl",
            "{\"event\":\"clarify\",\"id\":1,\"state\":\"settled\"}\n\
             {\"event\":\"pause\",\"action\":\"save\"}\n\
             {\"event\":\"publish\",\"status\":\"ready\"}\n",
        )?;
        self.write_run_log_staging(
            "final-summary.md",
            "Design session committed for issue <ISSUE> in <REPOSITORY>.\n",
        )?;
        Ok(())
    }

    fn write_issue_body(&self, template: &str) -> io::Result<()> {
        let body = self.render(template);
        self.workspace.write("issue/body.md", body.as_bytes())?;
        Ok(())
    }

    fn write_plan_document(&self, name: &str, template: &str) -> io::Result<()> {
        validate_relative(Path::new(name))?;
        let relative = format!("design-tmpdir/{name}");
        self.workspace
            .write(relative, self.render(template).as_bytes())?;
        Ok(())
    }

    fn write_step_result_env(&self, name: &str, template: &str) -> io::Result<()> {
        validate_relative(Path::new(name))?;
        let relative = format!("design-tmpdir/{name}");
        self.workspace
            .write(relative, self.render(template).as_bytes())?;
        Ok(())
    }

    fn write_design_env(&self, include_issue: bool) -> io::Result<()> {
        let design_tmpdir = self.design_tmpdir();
        let mut lines = vec![
            format!(
                "export DESIGN_TMPDIR={}",
                shell_single_quote(&design_tmpdir.to_string_lossy())
            ),
            format!(
                "export CLAUDE_PLUGIN_ROOT={}",
                shell_single_quote(&self.root().join("plugin").to_string_lossy())
            ),
            format!("export SESSION_ID={}", self.run_id),
            format!("export RUN_ID={}", self.run_id),
            format!("export REPO={}", self.repository_slug),
        ];
        if include_issue {
            lines.push(format!("export ISSUE_NUMBER={}", self.issue_number));
        }
        lines.push(String::new());
        let contents = lines.join("\n");
        let relative = format!(
            "cache/larch/sessions/current-design-env-{}.sh",
            self.ppid
        );
        self.workspace.write(&relative, contents.as_bytes())?;
        self.workspace
            .write("design-tmpdir/source-env.sh", contents.as_bytes())?;
        Ok(())
    }

    fn write_run_log_staging(&self, name: &str, template: &str) -> io::Result<()> {
        validate_relative(Path::new(name))?;
        let relative = format!("larch-logs/design/{}/{name}", self.run_id);
        self.workspace
            .write(relative, self.render(template).as_bytes())?;
        Ok(())
    }

    fn render(&self, template: &str) -> String {
        template
            .replace("<DESIGN_TMPDIR>", &self.design_tmpdir().to_string_lossy())
            .replace("<ROOT>", &self.root().to_string_lossy())
            .replace("<REPOSITORY>", &self.repository_slug)
            .replace("<RUN_ID>", &self.run_id)
            .replace("<ISSUE>", &self.issue_number.to_string())
    }
}

/// One normalized file entry in a design session snapshot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DesignEntrySnapshot {
    pub relative_path: String,
    pub mode: u32,
    pub content: BoundedBytes,
}

/// Bounded semantic snapshot of a design session.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DesignSessionSnapshot {
    pub schema: u32,
    pub execution: ExecutionSnapshot,
    pub state: DesignSessionState,
    pub ppid: u32,
    pub issue_number: u64,
    pub repository_slug: BoundedBytes,
    pub run_id: BoundedBytes,
    pub entries: Vec<DesignEntrySnapshot>,
    pub entries_truncated: bool,
}

impl DesignSessionSnapshot {
    /// Capture a stable, redacted view of an isolated design session.
    ///
    /// # Errors
    /// Returns filesystem errors while walking the owned fixture root.
    pub fn capture(session: &DesignSession, execution: ExecutionSnapshot) -> io::Result<Self> {
        let mut entries = Vec::new();
        collect_entries(session.root(), session.root(), &mut entries)?;
        let entries_truncated = entries.len() > ENTRY_LIMIT;
        entries.truncate(ENTRY_LIMIT);
        let entries = entries
            .into_iter()
            .map(|entry| normalize_entry(entry, session))
            .collect();
        Ok(Self {
            schema: DESIGN_SESSION_SNAPSHOT_SCHEMA,
            execution,
            state: session.state(),
            ppid: session.ppid(),
            issue_number: session.issue_number(),
            repository_slug: BoundedBytes::new(&normalize_design_text(
                session.repository_slug().as_bytes(),
                session,
            )),
            run_id: BoundedBytes::new(&normalize_design_text(session.run_id().as_bytes(), session)),
            entries,
            entries_truncated,
        })
    }
}

/// One exact machine field captured from design-domain stdout.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DesignStdoutField {
    pub key: String,
    pub value: BoundedBytes,
}

/// Snapshot of design stdout: ordered exact machine fields and normalized prose.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DesignStdoutSnapshot {
    pub schema: u32,
    pub fields: Vec<DesignStdoutField>,
    pub fields_truncated: bool,
    pub prose: BoundedBytes,
}

impl DesignStdoutSnapshot {
    /// Capture design stdout using the session's owned root for identity redaction.
    #[must_use]
    pub fn capture(stdout: &[u8], session: &DesignSession) -> Self {
        let mut fields = Vec::new();
        let mut prose = Vec::new();
        let mut fields_truncated = false;
        for line in stdout.split_inclusive(|byte| *byte == b'\n') {
            if let Some((key, value)) = stdout_field(line) {
                if fields.len() < STDOUT_FIELD_LIMIT {
                    fields.push(DesignStdoutField {
                        key: String::from_utf8_lossy(key).into_owned(),
                        value: BoundedBytes::new(&normalize_design_text(value, session)),
                    });
                } else {
                    fields_truncated = true;
                }
            } else {
                prose.extend_from_slice(line);
            }
        }
        Self {
            schema: DESIGN_STDOUT_SNAPSHOT_SCHEMA,
            fields,
            fields_truncated,
            prose: BoundedBytes::new(&normalize_prose(&prose, session)),
        }
    }
}

/// Differential parity oracle for design session and stdout snapshots.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct DesignParityOracle;

impl DesignParityOracle {
    #[must_use]
    pub const fn new() -> Self {
        Self
    }

    /// Compare session snapshots and name only the semantic channels that differ.
    #[must_use]
    pub fn compare_sessions(
        &self,
        left: &DesignSessionSnapshot,
        right: &DesignSessionSnapshot,
    ) -> Vec<ParityDifference> {
        let mut differences = Vec::new();
        push_difference(
            &mut differences,
            "schema",
            &left.schema.to_string(),
            &right.schema.to_string(),
        );
        push_difference(
            &mut differences,
            "state",
            left.state.as_str(),
            right.state.as_str(),
        );
        push_difference(
            &mut differences,
            "ppid",
            &left.ppid.to_string(),
            &right.ppid.to_string(),
        );
        push_difference(
            &mut differences,
            "issue_number",
            &left.issue_number.to_string(),
            &right.issue_number.to_string(),
        );
        push_difference(
            &mut differences,
            "repository_slug",
            &bounded_summary(&left.repository_slug),
            &bounded_summary(&right.repository_slug),
        );
        push_difference(
            &mut differences,
            "run_id",
            &bounded_summary(&left.run_id),
            &bounded_summary(&right.run_id),
        );
        compare_execution(&mut differences, &left.execution, &right.execution);
        compare_channel(
            &mut differences,
            "entries",
            &left.entries,
            left.entries_truncated,
            &right.entries,
            right.entries_truncated,
        );
        differences
    }

    /// Compare design stdout snapshots without treating prose as machine fields.
    #[must_use]
    pub fn compare_stdout(
        &self,
        left: &DesignStdoutSnapshot,
        right: &DesignStdoutSnapshot,
    ) -> Vec<ParityDifference> {
        let mut differences = Vec::new();
        push_difference(
            &mut differences,
            "schema",
            &left.schema.to_string(),
            &right.schema.to_string(),
        );
        compare_channel(
            &mut differences,
            "stdout.fields",
            &left.fields,
            left.fields_truncated,
            &right.fields,
            right.fields_truncated,
        );
        push_difference(
            &mut differences,
            "stdout.prose",
            &bounded_summary(&left.prose),
            &bounded_summary(&right.prose),
        );
        differences
    }
}

/// Recorded GitHub exchanges for design clarify, pause, and mutation conflicts.
#[derive(Clone, Debug, Default)]
pub struct DesignGithubScenario;

impl DesignGithubScenario {
    /// Clarify round-trip: issue read, comment thread, then label remove.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn clarify_round_trip(
        owner: &str,
        repo: &str,
        issue: u64,
    ) -> Result<Vec<IssueServiceExchange>, crate::HttpResponseError> {
        let issue_path = format!("/repos/{owner}/{repo}/issues/{issue}");
        let comments_path = format!("/repos/{owner}/{repo}/issues/{issue}/comments");
        let labels_path = format!("/repos/{owner}/{repo}/issues/{issue}/labels");
        Ok(vec![
            IssueServiceExchange::json(
                "GET",
                &issue_path,
                200,
                format!(
                    "{{\"number\":{issue},\"title\":\"[DESIGNING] Fixture\",\"body\":\"plan\",\"state\":\"open\",\"labels\":[{{\"name\":\"needs-design-clarification\"}}]}}"
                ),
            )?,
            IssueServiceExchange::json(
                "GET",
                &comments_path,
                200,
                "[\
{\"id\":1,\"body\":\"<!-- larch:clarify-request id=1 -->\\n## Clarifications needed\\n- Q1: Confirm ownership.\\n\"},\
{\"id\":2,\"body\":\"<!-- larch:clarify-response id=1 -->\\n## Resolved\\n- Q1: Fixtures own this.\\n\"}\
]",
            )?,
            IssueServiceExchange::json("DELETE", &labels_path, 200, "[]")?,
        ])
    }

    /// Pause save/load path: issue read with pause pointer, then successful edit.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn pause_round_trip(
        owner: &str,
        repo: &str,
        issue: u64,
        run_id: &str,
    ) -> Result<Vec<IssueServiceExchange>, crate::HttpResponseError> {
        let issue_path = format!("/repos/{owner}/{repo}/issues/{issue}");
        let body = format!(
            "<!-- larch:design-pause:start -->\\n\
ISSUE_NUMBER={issue}\\n\
REPO={owner}/{repo}\\n\
RUN_ID={run_id}\\n\
STEP=step-3\\n\
SESSION_ID={run_id}\\n\
BRAINSTORM_DONE=true\\n\
BODY_HASH=cafebabe\\n\
PAUSED_AT=2026-08-15T12:00:00Z\\n\
<!-- larch:design-pause:end -->"
        );
        Ok(vec![
            IssueServiceExchange::json(
                "GET",
                &issue_path,
                200,
                format!(
                    "{{\"number\":{issue},\"title\":\"[DESIGNING] Paused\",\"body\":\"{body}\",\"state\":\"open\",\"labels\":[]}}"
                ),
            )?,
            IssueServiceExchange::json(
                "PATCH",
                &issue_path,
                200,
                format!(
                    "{{\"number\":{issue},\"title\":\"[DESIGNING] Paused\",\"body\":\"{body}\",\"state\":\"open\",\"labels\":[]}}"
                ),
            )?,
        ])
    }

    /// Mutation conflict: label flip races a 409, then a successful retry.
    ///
    /// # Errors
    /// Returns invalid HTTP fixture response configuration.
    pub fn mutation_conflict(
        owner: &str,
        repo: &str,
        issue: u64,
    ) -> Result<Vec<IssueServiceExchange>, crate::HttpResponseError> {
        let labels_path = format!("/repos/{owner}/{repo}/issues/{issue}/labels");
        Ok(vec![
            IssueServiceExchange::conflict(
                "POST",
                &labels_path,
                "{\"message\":\"Issue modified concurrently\"}",
            )?,
            IssueServiceExchange::json(
                "POST",
                &labels_path,
                200,
                "[{\"name\":\"needs-design-clarification\"}]",
            )?,
        ])
    }

    /// Start a loopback stub for one of the design GitHub scenarios.
    ///
    /// # Errors
    /// Returns loopback bind failures or invalid exchange configuration.
    pub fn start(
        exchanges: impl IntoIterator<Item = IssueServiceExchange>,
    ) -> io::Result<IssueServiceStub> {
        IssueServiceStub::start(exchanges)
    }
}

struct RawEntry {
    relative_path: String,
    mode: u32,
    bytes: Vec<u8>,
}

fn collect_entries(root: &Path, current: &Path, entries: &mut Vec<RawEntry>) -> io::Result<()> {
    if current == root {
        for child in sorted_children(current)? {
            collect_entries(root, &child, entries)?;
        }
        return Ok(());
    }
    let metadata = fs::symlink_metadata(current)?;
    let relative = current
        .strip_prefix(root)
        .map_err(|error| io::Error::other(error.to_string()))?;
    let relative_path = relative.to_string_lossy().replace('\\', "/");
    if metadata.is_dir() {
        entries.push(RawEntry {
            relative_path: format!("{relative_path}/"),
            mode: file_mode(&metadata),
            bytes: Vec::new(),
        });
        for child in sorted_children(current)? {
            collect_entries(root, &child, entries)?;
        }
    } else if metadata.is_file() {
        entries.push(RawEntry {
            relative_path,
            mode: file_mode(&metadata),
            bytes: fs::read(current)?,
        });
    }
    Ok(())
}

fn normalize_entry(entry: RawEntry, session: &DesignSession) -> DesignEntrySnapshot {
    DesignEntrySnapshot {
        relative_path: entry.relative_path,
        mode: entry.mode,
        content: BoundedBytes::new(&normalize_design_text(&entry.bytes, session)),
    }
}

fn normalize_design_text(input: &[u8], session: &DesignSession) -> Vec<u8> {
    let design_tmpdir = session.design_tmpdir();
    let mut normalized = replace_all(input, &path_bytes(&design_tmpdir), b"<DESIGN_TMPDIR>");
    normalized = replace_all(&normalized, &path_bytes(session.root()), b"<ROOT>");
    if !session.repository_slug().is_empty() {
        normalized = replace_all(
            &normalized,
            session.repository_slug().as_bytes(),
            b"<REPOSITORY>",
        );
    }
    if !session.run_id().is_empty() {
        normalized = replace_all(&normalized, session.run_id().as_bytes(), b"<RUN_ID>");
    }
    let issue = session.issue_number().to_string();
    normalized = replace_all(&normalized, issue.as_bytes(), b"<ISSUE>");
    redact_design_credentials(&normalized)
}

fn normalize_prose(input: &[u8], session: &DesignSession) -> Vec<u8> {
    let normalized = normalize_design_text(input, session);
    replace_all(&normalized, b"\r\n", b"\n")
}

fn redact_design_credentials(input: &[u8]) -> Vec<u8> {
    let redacted_lines = redact_matching_lines(input, &SENSITIVE_LINE_NEEDLES);
    redact_github_tokens(&redacted_lines)
}

fn redact_github_tokens(input: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    let mut index = 0;
    while index < input.len() {
        if let Some(prefix) = GITHUB_TOKEN_PREFIXES
            .iter()
            .find(|prefix| input[index..].starts_with(prefix))
        {
            output.extend_from_slice(b"<REDACTED>");
            index += prefix.len();
            while index < input.len() && github_token_byte(input[index]) {
                index += 1;
            }
        } else {
            output.push(input[index]);
            index += 1;
        }
    }
    output
}

const fn github_token_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-')
}

fn stdout_field(line: &[u8]) -> Option<(&[u8], &[u8])> {
    let line = strip_line_ending(line);
    let equals = line.iter().position(|byte| *byte == b'=')?;
    let key = &line[..equals];
    valid_stdout_key(key).then_some((key, &line[equals + 1..]))
}

fn strip_line_ending(line: &[u8]) -> &[u8] {
    let line = line.strip_suffix(b"\n").unwrap_or(line);
    line.strip_suffix(b"\r").unwrap_or(line)
}

fn valid_stdout_key(key: &[u8]) -> bool {
    !key.is_empty()
        && key[0].is_ascii_uppercase()
        && key
            .iter()
            .all(|byte| byte.is_ascii_uppercase() || byte.is_ascii_digit() || *byte == b'_')
}

fn compare_execution(
    differences: &mut Vec<ParityDifference>,
    left: &ExecutionSnapshot,
    right: &ExecutionSnapshot,
) {
    push_difference(
        differences,
        "execution.exit_class",
        &format!("{:?}", left.exit_class),
        &format!("{:?}", right.exit_class),
    );
    push_difference(
        differences,
        "execution.stdout",
        &bounded_summary(&left.stdout),
        &bounded_summary(&right.stdout),
    );
    push_difference(
        differences,
        "execution.stderr",
        &bounded_summary(&left.stderr),
        &bounded_summary(&right.stderr),
    );
}

fn compare_channel<T: fmt::Debug + PartialEq>(
    differences: &mut Vec<ParityDifference>,
    channel: &str,
    left: &[T],
    left_truncated: bool,
    right: &[T],
    right_truncated: bool,
) {
    if left == right && left_truncated == right_truncated {
        return;
    }
    differences.push(ParityDifference {
        channel: channel.to_owned(),
        left: format!(
            "count={} truncated={} digest={:016x}",
            left.len(),
            left_truncated,
            fnv1a(format!("{left:?}").as_bytes())
        ),
        right: format!(
            "count={} truncated={} digest={:016x}",
            right.len(),
            right_truncated,
            fnv1a(format!("{right:?}").as_bytes())
        ),
    });
}

fn bounded_summary(bytes: &BoundedBytes) -> String {
    format!(
        "len={} checksum={:016x} truncated={}",
        bytes.total_len, bytes.checksum, bytes.truncated
    )
}

fn push_difference(
    differences: &mut Vec<ParityDifference>,
    channel: &str,
    left: &str,
    right: &str,
) {
    if left != right {
        differences.push(ParityDifference {
            channel: channel.to_owned(),
            left: truncate_diagnostic(left),
            right: truncate_diagnostic(right),
        });
    }
}

fn truncate_diagnostic(value: &str) -> String {
    const LIMIT: usize = 512;
    if value.len() <= LIMIT {
        value.to_owned()
    } else {
        format!("{}...({} bytes)", &value[..LIMIT], value.len())
    }
}

fn shell_single_quote(value: &str) -> String {
    format!("'{}'", value.replace('\'', "'\\''"))
}

#[cfg(test)]
mod tests {
    use std::{
        io::{Read as _, Write as _},
        net::TcpStream,
    };

    use crate::{ExecutionSnapshot, IssueServiceStub, snapshot_util::find_bytes};

    use super::{
        DesignFixture, DesignGithubScenario, DesignParityOracle, DesignSession,
        DesignSessionSnapshot, DesignSessionState, DesignStdoutSnapshot,
    };

    #[test]
    fn named_fixtures_build_isolated_sessions_without_process_globals() {
        for (fixture, state) in [
            (DesignFixture::Absent, DesignSessionState::Absent),
            (DesignFixture::Partial, DesignSessionState::Partial),
            (DesignFixture::Conflicting, DesignSessionState::Conflicting),
            (DesignFixture::Committed, DesignSessionState::Committed),
        ] {
            let session = DesignSession::builder(fixture)
                .build()
                .expect("build design session");
            assert_eq!(session.state(), state);
            assert!(session.root().exists());
            match fixture {
                DesignFixture::Absent => {
                    assert!(!session.issue_body_path().exists());
                    assert!(!session.current_design_env_path().exists());
                }
                DesignFixture::Partial
                | DesignFixture::Conflicting
                | DesignFixture::Committed => {
                    assert!(session.issue_body_path().exists());
                    assert!(session.current_design_env_path().exists());
                    assert!(session.design_tmpdir().exists());
                }
            }
        }
    }

    #[test]
    fn snapshots_distinguish_named_states_and_redact_credentials() {
        let oracle = DesignParityOracle::new();
        let mut snapshots = Vec::new();
        for fixture in [
            DesignFixture::Absent,
            DesignFixture::Partial,
            DesignFixture::Conflicting,
            DesignFixture::Committed,
        ] {
            let session = DesignSession::builder(fixture)
                .build()
                .expect("build design session");
            let snapshot = DesignSessionSnapshot::capture(&session, ExecutionSnapshot::success())
                .expect("capture session");
            assert_eq!(snapshot.state, fixture.state());
            snapshots.push((fixture, snapshot));
        }
        let absent = &snapshots[0].1;
        let partial = &snapshots[1].1;
        let conflicting = &snapshots[2].1;
        assert!(
            oracle
                .compare_sessions(absent, partial)
                .iter()
                .any(|difference| difference.channel == "state")
        );
        let entry = conflicting
            .entries
            .iter()
            .find(|entry| entry.relative_path == "design-tmpdir/step-3.result.env")
            .expect("step env entry");
        let content = String::from_utf8_lossy(&entry.content.bytes);
        assert!(!content.contains("ghp_fixturecredential"));
        assert!(content.contains("<REDACTED>"));
    }

    #[test]
    fn stdout_snapshot_keeps_exact_fields_and_normalized_prose() {
        let session = DesignSession::builder(DesignFixture::Committed)
            .build()
            .expect("build design session");
        let stdout = format!(
            "SESSION_STATUS=ok\n\
             DESIGN_TMPDIR={}\n\
             ISSUE_NUMBER={}\n\
             prose line about {}\n",
            session.design_tmpdir().display(),
            session.issue_number(),
            session.repository_slug()
        );
        let snapshot = DesignStdoutSnapshot::capture(stdout.as_bytes(), &session);
        assert_eq!(snapshot.fields.len(), 3);
        assert_eq!(snapshot.fields[0].key, "SESSION_STATUS");
        assert_eq!(snapshot.fields[0].value.bytes, b"ok");
        assert_eq!(snapshot.fields[1].value.bytes, b"<DESIGN_TMPDIR>");
        assert_eq!(snapshot.fields[2].value.bytes, b"<ISSUE>");
        assert!(
            String::from_utf8_lossy(&snapshot.prose.bytes).contains("<REPOSITORY>")
                || snapshot.prose.bytes == b"prose line about <REPOSITORY>\n"
        );
    }

    #[test]
    fn github_scenarios_cover_clarify_pause_and_mutation_conflict() {
        let clarify = DesignGithubScenario::clarify_round_trip("character-ai", "larch", 7680)
            .expect("clarify exchanges");
        let stub = DesignGithubScenario::start(clarify).expect("start clarify stub");
        assert_eq!(
            request_status(&stub, "GET", "/repos/character-ai/larch/issues/7680", b""),
            200
        );
        assert_eq!(
            request_status(
                &stub,
                "GET",
                "/repos/character-ai/larch/issues/7680/comments",
                b""
            ),
            200
        );
        assert_eq!(
            request_status(
                &stub,
                "DELETE",
                "/repos/character-ai/larch/issues/7680/labels",
                b""
            ),
            200
        );
        stub.finish().expect("clarify consumed");

        let pause = DesignGithubScenario::pause_round_trip(
            "character-ai",
            "larch",
            7680,
            "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        )
        .expect("pause exchanges");
        let stub = DesignGithubScenario::start(pause).expect("start pause stub");
        assert_eq!(
            request_status(&stub, "GET", "/repos/character-ai/larch/issues/7680", b""),
            200
        );
        assert_eq!(
            request_status(&stub, "PATCH", "/repos/character-ai/larch/issues/7680", b"{}"),
            200
        );
        stub.finish().expect("pause consumed");

        let conflict = DesignGithubScenario::mutation_conflict("character-ai", "larch", 7680)
            .expect("conflict exchanges");
        let stub = DesignGithubScenario::start(conflict).expect("start conflict stub");
        assert_eq!(
            request_status(
                &stub,
                "POST",
                "/repos/character-ai/larch/issues/7680/labels",
                b"[]"
            ),
            409
        );
        assert_eq!(
            request_status(
                &stub,
                "POST",
                "/repos/character-ai/larch/issues/7680/labels",
                b"[]"
            ),
            200
        );
        stub.finish().expect("conflict consumed");
    }

    fn request_status(stub: &IssueServiceStub, method: &str, path: &str, body: &[u8]) -> u16 {
        let bytes = raw_response_bytes(stub, method, path, body);
        let header_end = find_bytes(&bytes, b"\r\n\r\n").expect("response headers");
        let header = std::str::from_utf8(&bytes[..header_end]).expect("response UTF-8");
        header
            .split("\r\n")
            .next()
            .expect("status")
            .split_ascii_whitespace()
            .nth(1)
            .expect("status code")
            .parse()
            .expect("numeric status")
    }

    fn raw_response_bytes(
        stub: &IssueServiceStub,
        method: &str,
        path: &str,
        body: &[u8],
    ) -> Vec<u8> {
        let address = stub
            .base_url()
            .strip_prefix("http://")
            .expect("loopback URL")
            .trim_end_matches('/');
        let mut socket = TcpStream::connect(address).expect("connect loopback stub");
        write!(
            socket,
            "{method} {path} HTTP/1.1\r\nHost: larch.test\r\nAuthorization: Bearer ghp_fixturecredential\r\nContent-Length: {}\r\nConnection: close\r\n\r\n",
            body.len()
        )
        .expect("request headers");
        socket.write_all(body).expect("request body");
        let mut response = Vec::new();
        socket.read_to_end(&mut response).expect("response body");
        response
    }
}
