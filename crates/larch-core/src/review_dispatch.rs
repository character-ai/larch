use std::{collections::BTreeSet, path::Path, sync::LazyLock, time::Duration};

use regex::Regex;

/// Default timeout for reviewer completion sentinels.
pub const WAIT_DEFAULT_TIMEOUT_SECONDS: u64 = 1_860;
/// Default polling interval for reviewer completion sentinels.
pub const WAIT_DEFAULT_POLL_INTERVAL_SECONDS: f64 = 5.0;
/// A slow iteration is considered a suspended-process interval.
pub const SUSPEND_REFUND_SECONDS: u64 = 60;
/// Required number of columns in `scripts/generators.tsv`.
pub const GENERATORS_TSV_COLUMNS: usize = 2;

static SCRIPT_TEST: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\Ascripts/test-.*\.(?:sh|py)\z").expect("static regex"));
static SKILL_TEST: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\Askills/[^/]+/scripts/test-.*\.sh\z").expect("static regex"));
static PACKAGE_TEST: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\A[^/]+/(?:tests|test)/[^/]+\.(?:sh|py|go|bats)\z").expect("static regex")
});
static TEST_BASENAME: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\A(?:test_.*|.*_test|.*\.test)\.(?:sh|py|go)\z").expect("static regex")
});
static DOC_PATH: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"\A(?:docs/[^/]+\.(?:md|txt|rst|adoc)|scripts/[^/]+\.md)\z").expect("static regex")
});

/// The review routing mode inferred from a patch.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DiffMode {
    /// The patch needs the ordinary code-review prompt.
    Generic,
    /// Every changed path is documentation.
    DocsOnly,
    /// Every changed path is test-only.
    TestOnly,
    /// Every changed path is generated output.
    GeneratedOnly,
}

impl DiffMode {
    /// Return the exact wire token emitted by `agent classify-diff`.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Generic => "generic",
            Self::DocsOnly => "docs-only",
            Self::TestOnly => "test-only",
            Self::GeneratedOnly => "generated-only",
        }
    }
}

/// Why `scripts/generators.tsv` cannot safely drive generated-path routing.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum GeneratorsTsvError {
    /// A non-comment row did not have the required number of columns.
    WrongColumnCount { line: usize },
    /// A required generator or output field was empty.
    EmptyColumn { line: usize },
}

impl std::fmt::Display for GeneratorsTsvError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::WrongColumnCount { line } => {
                write!(
                    formatter,
                    "generators.tsv line {line} must contain {GENERATORS_TSV_COLUMNS} tab-separated columns"
                )
            }
            Self::EmptyColumn { line } => {
                write!(
                    formatter,
                    "generators.tsv line {line} contains an empty required column"
                )
            }
        }
    }
}

impl std::error::Error for GeneratorsTsvError {}

/// Parse the fixed two-column generated-artifact manifest.
///
/// An unreadable or malformed manifest must stop classification rather than
/// silently routing all changes through the generic reviewer.
///
/// # Errors
/// Returns [`GeneratorsTsvError`] for a malformed non-comment manifest row.
pub fn parse_generated_paths(input: &str) -> Result<BTreeSet<String>, GeneratorsTsvError> {
    let mut paths = BTreeSet::new();
    for (index, line) in input.lines().enumerate() {
        let line_number = index + 1;
        let stripped = line.trim();
        if stripped.is_empty() || stripped.starts_with('#') {
            continue;
        }
        let columns: Vec<&str> = line.split('\t').collect();
        if columns.len() != GENERATORS_TSV_COLUMNS {
            return Err(GeneratorsTsvError::WrongColumnCount { line: line_number });
        }
        if columns.iter().any(|column| column.trim().is_empty()) {
            return Err(GeneratorsTsvError::EmptyColumn { line: line_number });
        }
        paths.insert(columns[1].to_owned());
    }
    Ok(paths)
}

/// Classify one complete diff body without emitting diagnostics.
#[must_use]
pub fn classify_diff(diff: &str, generated_paths: &BTreeSet<String>) -> DiffMode {
    let mut mode = None;
    let mut seen = false;
    for line in diff.split('\n') {
        if !line.starts_with("diff --git ") {
            continue;
        }
        seen = true;
        let Some((old_path, new_path)) = parse_diff_header(line) else {
            return DiffMode::Generic;
        };
        let old_mode = classify_path(old_path, generated_paths);
        let new_mode = classify_path(new_path, generated_paths);
        if old_mode != new_mode || old_mode == DiffMode::Generic {
            return DiffMode::Generic;
        }
        if let Some(previous) = mode {
            if previous != old_mode {
                return DiffMode::Generic;
            }
        } else {
            mode = Some(old_mode);
        }
    }
    if seen {
        mode.unwrap_or(DiffMode::Generic)
    } else {
        DiffMode::Generic
    }
}

fn parse_diff_header(line: &str) -> Option<(&str, &str)> {
    let remainder = line.strip_prefix("diff --git a/")?;
    let (old_path, new_path) = remainder.split_once(" b/")?;
    (!old_path.is_empty()
        && !new_path.is_empty()
        && !old_path.chars().any(char::is_whitespace)
        && !new_path.chars().any(char::is_whitespace))
    .then_some((old_path, new_path))
}

fn classify_path(path: &str, generated_paths: &BTreeSet<String>) -> DiffMode {
    if path.is_empty() || path.starts_with('/') || path.contains("..") {
        return DiffMode::Generic;
    }
    if generated_paths.contains(path) {
        return DiffMode::GeneratedOnly;
    }
    let basename = path.rsplit('/').next().unwrap_or_default();
    if SCRIPT_TEST.is_match(path)
        || SKILL_TEST.is_match(path)
        || PACKAGE_TEST.is_match(path)
        || TEST_BASENAME.is_match(basename)
        || basename
            .rsplit_once('.')
            .is_some_and(|(_, extension)| extension == "bats")
    {
        return DiffMode::TestOnly;
    }
    if DOC_PATH.is_match(path)
        || matches!(
            path,
            "README.md" | "SECURITY.md" | "AGENTS.md" | "CLAUDE.md" | "KARPATHY_CLAUDE.md"
        )
    {
        return DiffMode::DocsOnly;
    }
    DiffMode::Generic
}

/// One effect port required by the reviewer wait-loop policy.
pub trait ReviewerWaitHost {
    /// Return elapsed monotonic time since a host-selected origin.
    fn now(&mut self) -> Duration;
    /// Sleep for one polling interval.
    fn sleep(&mut self, duration: Duration);
    /// Read an existing sentinel. `None` means the sentinel is not a regular file.
    fn read_sentinel(&mut self, path: &Path) -> Option<String>;
    /// Emit one human-facing diagnostic fragment.
    fn diagnostic(&mut self, text: &str);
}

/// Inputs controlling reviewer wait behavior after command-line validation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ReviewerWaitConfig {
    timeout_seconds: u64,
    poll_interval: Duration,
}

impl ReviewerWaitConfig {
    /// Build a validated wait configuration.
    #[must_use]
    pub const fn new(timeout_seconds: u64, poll_interval: Duration) -> Self {
        Self {
            timeout_seconds,
            poll_interval,
        }
    }

    /// Return the requested timeout in whole seconds.
    #[must_use]
    pub const fn timeout_seconds(self) -> u64 {
        self.timeout_seconds
    }
}

/// One machine-readable completion row produced by the wait loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ReviewerWaitRow {
    /// A sentinel appeared and supplied an exit code.
    Done {
        index: usize,
        name: String,
        exit_code: String,
    },
    /// A sentinel was still absent after the polling budget elapsed.
    Timeout { index: usize, name: String },
}

/// Complete result of waiting for reviewer sentinels.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReviewerWaitResult {
    rows: Vec<ReviewerWaitRow>,
    timed_out: usize,
}

impl ReviewerWaitResult {
    /// Return the machine-readable rows in input order.
    #[must_use]
    pub fn rows(&self) -> &[ReviewerWaitRow] {
        &self.rows
    }

    /// Return the number of missing sentinels at timeout.
    #[must_use]
    pub const fn timed_out(&self) -> usize {
        self.timed_out
    }
}

/// Preserve the legacy poll-budget calculation exactly.
#[must_use]
#[allow(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss
)] // preserves the legacy floating-point poll budget
pub fn wait_max_polls(timeout_seconds: u64, poll_interval_seconds: f64) -> usize {
    let maximum =
        ((timeout_seconds as f64 + poll_interval_seconds - 0.001) / poll_interval_seconds) as usize;
    maximum.max(1)
}

/// Wait for all sentinel files, refunding a polling slot after a long suspend.
#[must_use]
pub fn wait_for_reviewers(
    host: &mut impl ReviewerWaitHost,
    sentinels: &[std::path::PathBuf],
    config: ReviewerWaitConfig,
) -> ReviewerWaitResult {
    let poll_seconds = config.poll_interval.as_secs_f64();
    let max_polls = wait_max_polls(config.timeout_seconds, poll_seconds);
    let total = sentinels.len();
    let mut found: Vec<Option<String>> = vec![None; total];
    let mut found_count = 0_usize;
    let mut checks = 0_usize;
    let mut suspend_refunds = 0_usize;
    let mut last_progress_minute = 0_u64;
    let start = host.now();

    check_sentinels(host, sentinels, &mut found, &mut found_count);
    while found_count < total && checks < max_polls {
        let iteration_start = host.now();
        host.diagnostic(".");
        checks += 1;
        let elapsed_minute = host.now().saturating_sub(start).as_secs() / 60;
        if elapsed_minute >= 1 && elapsed_minute != last_progress_minute {
            host.diagnostic(&format!(
                "\n⏳ Waiting: {elapsed_minute}m elapsed, {checks} checks, {found_count}/{total} done"
            ));
            last_progress_minute = elapsed_minute;
        }
        host.sleep(config.poll_interval);
        check_sentinels(host, sentinels, &mut found, &mut found_count);
        let iteration_seconds = host.now().saturating_sub(iteration_start).as_secs();
        if iteration_seconds > SUSPEND_REFUND_SECONDS {
            host.diagnostic(&format!(
                "\n⚠ suspend detected — iteration took {iteration_seconds}s, not counting toward poll budget"
            ));
            if suspend_refunds < max_polls {
                checks = checks.saturating_sub(1);
                suspend_refunds += 1;
            }
        }
    }

    let elapsed = host.now().saturating_sub(start).as_secs();
    host.diagnostic("\n");
    let mut rows = Vec::with_capacity(total);
    let mut timed_out = 0_usize;
    for (offset, sentinel) in sentinels.iter().enumerate() {
        let index = offset + 1;
        let name = sentinel_name(sentinel);
        if let Some(exit_code) = &found[offset] {
            rows.push(ReviewerWaitRow::Done {
                index,
                name,
                exit_code: exit_code.clone(),
            });
        } else {
            rows.push(ReviewerWaitRow::Timeout { index, name });
            timed_out += 1;
        }
    }
    if timed_out > 0 {
        host.diagnostic(&format!(
            "⚠ {timed_out}/{total} reviewer(s) timed out after {} seconds",
            config.timeout_seconds
        ));
    } else {
        host.diagnostic(&format!(
            "✓ All {total} reviewer(s) completed in {elapsed}s"
        ));
    }
    ReviewerWaitResult { rows, timed_out }
}

fn check_sentinels(
    host: &mut impl ReviewerWaitHost,
    sentinels: &[std::path::PathBuf],
    found: &mut [Option<String>],
    found_count: &mut usize,
) {
    for (offset, sentinel) in sentinels.iter().enumerate() {
        if found[offset].is_some() {
            continue;
        }
        if let Some(text) = host.read_sentinel(sentinel) {
            let exit_code = sentinel_exit_code(&text);
            found[offset] = Some(exit_code.clone());
            *found_count += 1;
            host.diagnostic(&format!(
                "\n✓ {}: exit={exit_code}",
                sentinel_name(sentinel)
            ));
        }
    }
}

fn sentinel_name(path: &Path) -> String {
    let name = path
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or_default();
    name.strip_suffix(".done").unwrap_or(name).to_owned()
}

fn sentinel_exit_code(text: &str) -> String {
    let compact: String = text.split_whitespace().collect();
    if !compact.is_empty() && compact.bytes().all(|byte| byte.is_ascii_digit()) {
        compact
    } else {
        "unknown".to_owned()
    }
}

#[cfg(test)]
mod tests {
    use std::{path::PathBuf, time::Duration};

    use super::{ReviewerWaitConfig, ReviewerWaitHost, wait_for_reviewers, wait_max_polls};

    #[derive(Default)]
    struct FakeHost {
        seconds: u64,
        sleeps: usize,
    }

    impl ReviewerWaitHost for FakeHost {
        fn now(&mut self) -> Duration {
            Duration::from_secs(self.seconds)
        }

        fn sleep(&mut self, _duration: std::time::Duration) {
            self.sleeps += 1;
            self.seconds += if self.sleeps == 1 { 61 } else { 1 };
        }

        fn read_sentinel(&mut self, _: &std::path::Path) -> Option<String> {
            None
        }

        fn diagnostic(&mut self, _: &str) {}
    }

    #[test]
    fn suspended_iteration_refunds_one_poll_slot() {
        assert_eq!(wait_max_polls(1, 2.0), 1);
        let mut host = FakeHost::default();
        let result = wait_for_reviewers(
            &mut host,
            &[PathBuf::from("missing.done")],
            ReviewerWaitConfig::new(1, Duration::from_secs(1)),
        );
        assert_eq!(host.sleeps, 2);
        assert_eq!(result.timed_out(), 1);
    }
}
