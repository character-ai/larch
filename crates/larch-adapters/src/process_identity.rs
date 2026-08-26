//! Concrete process-identity host using nix signals and allowlisted `ps`/`pgrep`.

use crate::{
    process::{NoopProcessObserver, TokioProcessRunner},
    runtime::{Cancellation, LarchRuntime},
};
use larch_core::{
    ChildEnvironment, ExternalProcessRunner, ExternalProgram, HostUtilityProgram,
    IdentityProbeOutput, PROCESS_IDENTITY_PS_TIMEOUT, ProcessBirthIdentity,
    ProcessBirthIdentityProbeOutput, ProcessErrorKind, ProcessIdentityHost, ProcessRequest,
    TerminateSignal,
};

const SYSTEM_HOST_UTILITY_PATH: &str = "/usr/bin:/bin";
#[cfg(target_os = "macos")]
use nix::errno::Errno;
use nix::{
    sys::signal::{Signal, kill, killpg},
    unistd::{Pid, getpgid, getppid},
};
use std::{
    env, fs,
    io::{self, Write as _},
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process,
    sync::Arc,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

#[cfg(unix)]
use std::collections::{BTreeMap, BTreeSet};

#[cfg(target_os = "macos")]
use libproc::{
    bsd_info::BSDInfo,
    proc_pid::pidinfo,
    processes::{ProcFilter, pids_by_type},
};

/// Production host for process-identity capture and validated termination.
pub struct SystemProcessIdentityHost {
    runtime: LarchRuntime,
    runner: TokioProcessRunner,
    working_directory: PathBuf,
    started: Instant,
}

impl SystemProcessIdentityHost {
    /// Build a host bound to the current working directory.
    ///
    /// # Panics
    ///
    /// Panics when the Tokio runtime cannot be created.
    #[must_use]
    pub fn new() -> Self {
        Self {
            runtime: LarchRuntime::new().expect("tokio runtime"),
            runner: TokioProcessRunner::new(Arc::new(NoopProcessObserver)),
            working_directory: env::current_dir().unwrap_or_else(|_| PathBuf::from("/")),
            started: Instant::now(),
        }
    }

    fn run_host_utility(
        &self,
        program: HostUtilityProgram,
        arguments: &[&str],
        timeout: Duration,
    ) -> Result<(i32, String), ProcessErrorKind> {
        let request = ProcessRequest::new(
            ExternalProgram::HostUtility(program),
            arguments.iter().map(|argument| (*argument).to_owned()),
            self.working_directory.clone(),
            timeout,
            Duration::from_secs(1),
            NonZeroUsize::new(1024 * 1024).unwrap_or(NonZeroUsize::MIN),
        )
        .map_err(|_| ProcessErrorKind::Input)?;
        // `lstart` is persisted in session-setup markers and must remain
        // parseable when reconciling legacy PID-only markers.
        // Session setup and parity isolation both scrub `PATH`. Process
        // identity is a closed host-utility operation, so resolve `ps` only
        // through the platform system directories rather than weakening
        // PID-reuse protection when the caller supplies a partial path.
        let request = if program == HostUtilityProgram::Ps {
            request
                .with_environment(ChildEnvironment::LcAll, "C")
                .with_environment(ChildEnvironment::Path, SYSTEM_HOST_UTILITY_PATH)
        } else {
            request
        };
        let cancellation = Cancellation::new();
        match self
            .runtime
            .block_on(self.runner.run(request, &cancellation))
        {
            Ok(output) => Ok((
                output.status().code().unwrap_or(1),
                String::from_utf8_lossy(output.stdout()).into_owned(),
            )),
            Err(error) => Err(error.kind()),
        }
    }
}

impl Default for SystemProcessIdentityHost {
    fn default() -> Self {
        Self::new()
    }
}

impl ProcessIdentityHost for SystemProcessIdentityHost {
    fn get_pgid(&self, process_id: i32) -> Option<i32> {
        if process_id <= 0 {
            return None;
        }
        getpgid(Some(Pid::from_raw(process_id)))
            .ok()
            .map(Pid::as_raw)
    }

    fn probe_ps_identity(&self, process_id: i32) -> IdentityProbeOutput {
        let process_id_text = process_id.to_string();
        match self.run_host_utility(
            HostUtilityProgram::Ps,
            &["-p", &process_id_text, "-o", "lstart=", "-o", "command="],
            PROCESS_IDENTITY_PS_TIMEOUT,
        ) {
            Ok((0, stdout)) => IdentityProbeOutput::Stdout(stdout),
            Err(ProcessErrorKind::TimedOut) => IdentityProbeOutput::Timeout,
            // POSIX `ps` uses status 1 when it finds no matching process.
            // Every other process-runner failure is unverifiable rather than
            // proof that the PID is absent.
            Ok((1, _)) => IdentityProbeOutput::Missing,
            Ok(_) | Err(_) => IdentityProbeOutput::Error,
        }
    }

    fn probe_process_birth_identity(&self, process_id: i32) -> ProcessBirthIdentityProbeOutput {
        probe_system_process_birth_identity(process_id)
    }

    fn process_is_zombie(&self, process_id: i32) -> bool {
        #[cfg(target_os = "linux")]
        {
            linux_process_state(process_id).is_some_and(|state| state == 'Z')
        }
        #[cfg(not(target_os = "linux"))]
        {
            let _ = process_id;
            false
        }
    }

    fn pgrep_children(&self, process_id: i32) -> Vec<i32> {
        let process_id_text = process_id.to_string();
        let stdout = self
            .run_host_utility(
                HostUtilityProgram::Pgrep,
                &["-P", &process_id_text],
                Duration::from_secs(5),
            )
            .ok()
            .filter(|(code, _)| *code == 0)
            .map(|(_, stdout)| stdout)
            .unwrap_or_default();
        parse_pid_list(&stdout)
    }

    fn pgrep_group(&self, process_group_id: i32) -> Vec<i32> {
        self.pgrep_group_checked(process_group_id)
            .unwrap_or_default()
    }

    fn pgrep_group_checked(&self, process_group_id: i32) -> Option<Vec<i32>> {
        let process_group_text = process_group_id.to_string();
        match self.run_host_utility(
            HostUtilityProgram::Pgrep,
            &["-g", &process_group_text],
            Duration::from_secs(5),
        ) {
            Ok((0, stdout)) => Some(parse_pid_list(&stdout)),
            // `pgrep` reserves 1 for a successful empty match.
            Ok((1, _)) => Some(Vec::new()),
            Ok(_) | Err(_) => None,
        }
    }

    fn signal_process(&self, process_id: i32, signal: TerminateSignal) -> bool {
        kill(Pid::from_raw(process_id), to_nix_signal(signal)).is_ok()
    }

    fn signal_group(&self, process_group_id: i32, signal: TerminateSignal) -> bool {
        killpg(Pid::from_raw(process_group_id), to_nix_signal(signal)).is_ok()
    }

    fn sleep(&self, duration: Duration) {
        std::thread::sleep(duration);
    }

    fn monotonic_now(&self) -> Duration {
        self.started.elapsed()
    }

    fn wall_time_secs(&self) -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_or(0.0, |duration| duration.as_secs_f64())
    }

    fn current_pid(&self) -> i32 {
        i32::try_from(process::id()).unwrap_or(0)
    }

    fn parent_pid(&self) -> i32 {
        getppid().as_raw()
    }

    fn parent_of(&self, process_id: i32) -> Option<i32> {
        let process_id_text = process_id.to_string();
        let (_, stdout) = self
            .run_host_utility(
                HostUtilityProgram::Ps,
                &["-o", "ppid=", "-p", &process_id_text],
                Duration::from_secs(5),
            )
            .ok()?;
        let parent = stdout.trim();
        if parent.is_empty() || !parent.bytes().all(|byte| byte.is_ascii_digit()) {
            return None;
        }
        parent.parse().ok()
    }

    fn list_processes(&self) -> Vec<(i32, String)> {
        let Ok((_, stdout)) = self.run_host_utility(
            HostUtilityProgram::Ps,
            &["-A", "-o", "pid=", "-o", "args="],
            Duration::from_secs(30),
        ) else {
            return Vec::new();
        };
        let mut rows = Vec::new();
        for line in stdout.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            let mut parts = trimmed.splitn(2, char::is_whitespace);
            let Some(process_id_text) = parts.next() else {
                continue;
            };
            if !process_id_text.bytes().all(|byte| byte.is_ascii_digit()) {
                continue;
            }
            let Ok(process_id) = process_id_text.parse::<i32>() else {
                continue;
            };
            let command = parts.next().unwrap_or("").trim_start().to_owned();
            rows.push((process_id, command));
        }
        rows
    }

    fn resolve_path(&self, path: &str) -> String {
        fs::canonicalize(path).map_or_else(
            |_| path.to_owned(),
            |resolved| resolved.display().to_string(),
        )
    }

    fn append_kill_log_line(&self, path: &Path, line: &str) {
        let Some(parent) = path.parent() else {
            return;
        };
        let _ = fs::create_dir_all(parent);
        let Ok(mut file) = fs::OpenOptions::new().create(true).append(true).open(path) else {
            return;
        };
        let _ = file.write_all(line.as_bytes());
    }

    fn write_identity_file(&self, path: &Path, text: &str) -> Result<(), String> {
        let Some(parent) = path.parent() else {
            return Err("identity path missing parent".to_owned());
        };
        let _ = fs::create_dir_all(parent);
        let name = path
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or("identity.json");
        let temp = parent.join(format!("{name}.tmp.{}", process::id()));
        fs::write(&temp, text).map_err(|error| error.to_string())?;
        fs::rename(&temp, path).map_err(|error| {
            let _ = fs::remove_file(&temp);
            error.to_string()
        })
    }

    fn read_identity_file(&self, path: &Path) -> Option<String> {
        fs::read_to_string(path).ok()
    }

    fn remove_file(&self, path: &Path) {
        let _ = fs::remove_file(path);
    }

    fn is_regular_file(&self, path: &Path) -> bool {
        fs::symlink_metadata(path)
            .is_ok_and(|metadata| metadata.is_file() && !metadata.file_type().is_symlink())
    }

    fn file_mtime_ns(&self, path: &Path) -> Option<u64> {
        let metadata = fs::metadata(path).ok()?;
        let modified = metadata.modified().ok()?;
        let duration = modified.duration_since(UNIX_EPOCH).ok()?;
        Some(u64::try_from(duration.as_nanos()).unwrap_or(u64::MAX))
    }

    fn read_text_lossy(&self, path: &Path) -> Option<String> {
        fs::read(path)
            .ok()
            .map(|bytes| String::from_utf8_lossy(&bytes).into_owned())
    }
}

#[cfg(unix)]
#[derive(Clone, Debug, Eq, PartialEq)]
struct ProcessGroupAnchor {
    // These identities live only for one owned-child shutdown. Persisted
    // process cleanup remains behind the stricter recorded-identity paths.
    process_id: i32,
    birth_identity: ProcessBirthIdentity,
}

#[cfg(unix)]
#[derive(Clone, Debug, Eq, PartialEq)]
struct DescendantProcessGroup {
    process_group: i32,
    depth: usize,
    anchors: Vec<ProcessGroupAnchor>,
}

#[cfg(unix)]
impl DescendantProcessGroup {
    fn merge(&mut self, other: Self) {
        self.depth = self.depth.max(other.depth);
        for anchor in other.anchors {
            if !self.anchors.contains(&anchor) {
                self.anchors.push(anchor);
            }
        }
    }

    fn has_live_anchor(&self) -> bool {
        self.anchors
            .iter()
            .any(|anchor| anchor_matches_group(anchor, self.process_group))
    }

    fn signal(&self, signal: TerminateSignal) -> io::Result<()> {
        if !self
            .anchors
            .iter()
            .any(|anchor| anchor.process_id == self.process_group)
        {
            return Err(io::Error::other(format!(
                "descendant joined unowned process group {}",
                self.process_group
            )));
        }
        if self.has_live_anchor() {
            return signal_process_group(self.process_group, signal);
        }
        if process_group_exists(self.process_group)? {
            // Never signal a bare PGID after every process that tied it to the
            // owned tree has exited or changed identity.
            return Err(io::Error::other(format!(
                "cannot verify owned descendant process group {}",
                self.process_group
            )));
        }
        Ok(())
    }
}

/// Ephemeral ownership state for one directly spawned Unix process tree.
///
/// Unlike persisted recovery identities, this state never crosses a process
/// or session boundary. It still captures kernel birth identities and refuses
/// a descendant group whose leader was not observed inside the owned tree.
#[cfg(unix)]
pub struct OwnedProcessTree {
    root_process: i32,
    root_group: i32,
    descendant_groups: Vec<DescendantProcessGroup>,
}

#[cfg(unix)]
impl OwnedProcessTree {
    /// Bind a child that was spawned as the leader of its own process group.
    #[must_use]
    pub const fn new(root_process: i32) -> Self {
        Self {
            root_process,
            root_group: root_process,
            descendant_groups: Vec::new(),
        }
    }

    /// Signal every verified descendant group, then the directly owned group.
    ///
    /// # Errors
    ///
    /// Returns the first discovery, identity, or signal error after attempting
    /// every safely identified group and the root group.
    pub fn signal(&mut self, signal: TerminateSignal) -> io::Result<()> {
        let mut first_error = self.refresh_descendant_groups().err();
        for group in &self.descendant_groups {
            if let Err(error) = group.signal(signal)
                && first_error.is_none()
            {
                first_error = Some(error);
            }
        }
        if let Err(error) = signal_process_group(self.root_group, signal)
            && first_error.is_none()
        {
            first_error = Some(error);
        }
        first_error.map_or(Ok(()), Err)
    }

    fn refresh_descendant_groups(&mut self) -> io::Result<()> {
        let (groups, capture_error) =
            capture_descendant_process_groups(self.root_process, self.root_group);
        for group in groups {
            if let Some(existing) = self
                .descendant_groups
                .iter_mut()
                .find(|existing| existing.process_group == group.process_group)
            {
                if existing.has_live_anchor() {
                    existing.merge(group);
                } else {
                    // A numeric PGID can be reused only after the old group is
                    // empty. Do not let an old leader anchor authorize a new
                    // snapshot whose live members belong to another group.
                    *existing = group;
                }
            } else {
                self.descendant_groups.push(group);
            }
        }
        self.descendant_groups
            .sort_by_key(|group| std::cmp::Reverse(group.depth));
        capture_error.map_or(Ok(()), Err)
    }
}

#[cfg(unix)]
fn anchor_matches_group(anchor: &ProcessGroupAnchor, process_group: i32) -> bool {
    if probe_system_process_birth_identity(anchor.process_id)
        != ProcessBirthIdentityProbeOutput::Identity(anchor.birth_identity.clone())
    {
        return false;
    }
    if getpgid(Some(Pid::from_raw(anchor.process_id))).map(Pid::as_raw) != Ok(process_group) {
        return false;
    }
    probe_system_process_birth_identity(anchor.process_id)
        == ProcessBirthIdentityProbeOutput::Identity(anchor.birth_identity.clone())
}

#[cfg(unix)]
fn signal_process_group(process_group: i32, signal: TerminateSignal) -> io::Result<()> {
    match killpg(Pid::from_raw(process_group), to_nix_signal(signal)) {
        Ok(()) | Err(nix::errno::Errno::ESRCH) => Ok(()),
        Err(error) => Err(io::Error::from_raw_os_error(error as i32)),
    }
}

#[cfg(unix)]
fn process_group_exists(process_group: i32) -> io::Result<bool> {
    match kill(Pid::from_raw(-process_group), None) {
        Ok(()) | Err(nix::errno::Errno::EPERM) => Ok(true),
        Err(nix::errno::Errno::ESRCH) => Ok(false),
        Err(error) => Err(io::Error::from_raw_os_error(error as i32)),
    }
}

#[cfg(unix)]
fn capture_descendant_process_groups(
    root_process: i32,
    root_group: i32,
) -> (Vec<DescendantProcessGroup>, Option<io::Error>) {
    let mut pending = vec![(root_process, 0_usize)];
    let mut seen = BTreeSet::from([root_process]);
    let mut groups = BTreeMap::<i32, DescendantProcessGroup>::new();
    let mut first_error = None;

    // Snapshot before signaling the root. Once a wrapper exits, its children
    // are reparented and can no longer be discovered from the direct child.
    while let Some((parent, depth)) = pending.pop() {
        let children = match direct_child_process_ids(parent) {
            Ok(children) => children,
            Err(error) => {
                if first_error.is_none() {
                    first_error = Some(error);
                }
                continue;
            }
        };
        for child in children {
            if child <= 0 || !seen.insert(child) {
                continue;
            }
            let child_depth = depth.saturating_add(1);
            pending.push((child, child_depth));
            let (process_group, anchor) = match capture_process_group_anchor(child) {
                Ok(Some(captured)) => captured,
                Ok(None) => continue,
                Err(error) => {
                    if first_error.is_none() {
                        first_error = Some(error);
                    }
                    continue;
                }
            };
            if process_group == root_group {
                continue;
            }
            let group = DescendantProcessGroup {
                process_group,
                depth: child_depth,
                anchors: vec![anchor],
            };
            groups
                .entry(process_group)
                .and_modify(|existing| existing.merge(group.clone()))
                .or_insert(group);
        }
    }

    let mut groups = groups.into_values().collect::<Vec<_>>();
    groups.sort_by_key(|group| std::cmp::Reverse(group.depth));
    (groups, first_error)
}

#[cfg(unix)]
fn capture_process_group_anchor(process_id: i32) -> io::Result<Option<(i32, ProcessGroupAnchor)>> {
    let process_group = match getpgid(Some(Pid::from_raw(process_id))) {
        Ok(process_group) => process_group.as_raw(),
        Err(nix::errno::Errno::ESRCH) => return Ok(None),
        Err(error) => return Err(io::Error::from_raw_os_error(error as i32)),
    };
    let birth_identity = match probe_system_process_birth_identity(process_id) {
        ProcessBirthIdentityProbeOutput::Identity(identity) => identity,
        ProcessBirthIdentityProbeOutput::Missing => return Ok(None),
        ProcessBirthIdentityProbeOutput::Unsupported => {
            return Err(io::Error::new(
                io::ErrorKind::Unsupported,
                "cannot capture descendant process birth identity on this platform",
            ));
        }
        ProcessBirthIdentityProbeOutput::Error => {
            return Err(io::Error::other(
                "cannot capture descendant process birth identity",
            ));
        }
    };
    match getpgid(Some(Pid::from_raw(process_id))) {
        Ok(current_group) if current_group.as_raw() == process_group => Ok(Some((
            process_group,
            ProcessGroupAnchor {
                process_id,
                birth_identity,
            },
        ))),
        Ok(_) => Err(io::Error::other(
            "descendant process group changed during ownership capture",
        )),
        Err(nix::errno::Errno::ESRCH) => Ok(None),
        Err(error) => Err(io::Error::from_raw_os_error(error as i32)),
    }
}

#[cfg(target_os = "macos")]
fn direct_child_process_ids(parent: i32) -> io::Result<Vec<i32>> {
    let parent = u32::try_from(parent)
        .map_err(|_| io::Error::other("parent process id is outside the Darwin pid range"))?;
    let process_ids = pids_by_type(ProcFilter::All)?;
    Ok(process_ids
        .into_iter()
        .filter_map(|process_id| {
            let process_id = i32::try_from(process_id).ok()?;
            let info = pidinfo::<BSDInfo>(process_id, 0).ok()?;
            (info.pbi_ppid == parent).then_some(process_id)
        })
        .collect())
}

#[cfg(target_os = "linux")]
fn direct_child_process_ids(parent: i32) -> io::Result<Vec<i32>> {
    let processes = std::fs::read_dir("/proc")?;
    let mut children = BTreeSet::new();
    for process in processes {
        let process = match process {
            Ok(process) => process,
            Err(error) if error.kind() == io::ErrorKind::NotFound => continue,
            Err(error) => return Err(error),
        };
        let Some(process_id) = process
            .file_name()
            .to_str()
            .and_then(|value| value.parse::<i32>().ok())
        else {
            continue;
        };
        let Ok(stat) = std::fs::read_to_string(process.path().join("stat")) else {
            continue;
        };
        let Some((_command, fields)) = stat.rsplit_once(") ") else {
            continue;
        };
        let process_parent = fields
            .split_whitespace()
            .nth(1)
            .and_then(|value| value.parse::<i32>().ok());
        if process_parent == Some(parent) {
            children.insert(process_id);
        }
    }
    Ok(children.into_iter().collect())
}

#[cfg(all(unix, not(any(target_os = "macos", target_os = "linux"))))]
fn direct_child_process_ids(_parent: i32) -> io::Result<Vec<i32>> {
    Ok(Vec::new())
}

fn probe_system_process_birth_identity(process_id: i32) -> ProcessBirthIdentityProbeOutput {
    if process_id <= 0 {
        return ProcessBirthIdentityProbeOutput::Missing;
    }
    #[cfg(target_os = "macos")]
    {
        darwin_process_birth_identity(process_id)
    }
    #[cfg(target_os = "linux")]
    {
        linux_process_birth_identity(process_id)
    }
    #[cfg(not(any(target_os = "macos", target_os = "linux")))]
    {
        ProcessBirthIdentityProbeOutput::Unsupported
    }
}

const fn to_nix_signal(signal: TerminateSignal) -> Signal {
    match signal {
        TerminateSignal::Term => Signal::SIGTERM,
        TerminateSignal::Kill => Signal::SIGKILL,
    }
}

fn parse_pid_list(stdout: &str) -> Vec<i32> {
    let mut process_ids = Vec::new();
    for line in stdout.lines() {
        let raw = line.trim();
        if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
            continue;
        }
        if let Ok(process_id) = raw.parse::<i32>() {
            process_ids.push(process_id);
        }
    }
    process_ids
}

#[cfg(target_os = "macos")]
fn darwin_process_birth_identity(process_id: i32) -> ProcessBirthIdentityProbeOutput {
    let info = match libproc::proc_pid::pidinfo::<libproc::bsd_info::BSDInfo>(process_id, 0) {
        Ok(info) => info,
        // `libproc` exposes an error string rather than errno. Confirm an
        // absent PID through `getpgid` so a process that died between probes
        // remains distinct from an unreadable live process and does not turn
        // normal post-SIGTERM confirmation into a probe failure.
        Err(_) if matches!(getpgid(Some(Pid::from_raw(process_id))), Err(Errno::ESRCH)) => {
            return ProcessBirthIdentityProbeOutput::Missing;
        }
        Err(_) => return ProcessBirthIdentityProbeOutput::Error,
    };
    if info.pbi_pid != u32::try_from(process_id).unwrap_or_default() {
        return ProcessBirthIdentityProbeOutput::Error;
    }
    ProcessBirthIdentityProbeOutput::Identity(ProcessBirthIdentity::Darwin {
        seconds: info.pbi_start_tvsec,
        microseconds: info.pbi_start_tvusec,
    })
}

#[cfg(target_os = "linux")]
fn linux_process_birth_identity(process_id: i32) -> ProcessBirthIdentityProbeOutput {
    let stat_path = format!("/proc/{process_id}/stat");
    let stat = match fs::read_to_string(stat_path) {
        Ok(value) => value,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return ProcessBirthIdentityProbeOutput::Missing;
        }
        Err(_) => return ProcessBirthIdentityProbeOutput::Error,
    };
    // `comm` is parenthesized and may itself contain whitespace or `)`, so
    // split from the final delimiter before indexing fields 3 through 22.
    let Some((_comm, fields)) = stat.rsplit_once(") ") else {
        return ProcessBirthIdentityProbeOutput::Error;
    };
    let Some(start_ticks) = fields
        .split_whitespace()
        .nth(19)
        .and_then(|value| value.parse::<u64>().ok())
    else {
        return ProcessBirthIdentityProbeOutput::Error;
    };
    let boot_id = match fs::read_to_string("/proc/sys/kernel/random/boot_id") {
        Ok(value) => value.trim().to_owned(),
        Err(_) => return ProcessBirthIdentityProbeOutput::Error,
    };
    let identity = ProcessBirthIdentity::Linux {
        boot_id,
        start_ticks,
    };
    if ProcessBirthIdentity::parse_wire_value(&identity.wire_value()).is_none() {
        return ProcessBirthIdentityProbeOutput::Error;
    }
    ProcessBirthIdentityProbeOutput::Identity(identity)
}

/// Read Linux `/proc/<pid>/stat` state after its final `) ` delimiter.
#[cfg(target_os = "linux")]
fn linux_process_state(process_id: i32) -> Option<char> {
    if process_id <= 0 {
        return None;
    }
    let stat = fs::read_to_string(format!("/proc/{process_id}/stat")).ok()?;
    let (_, fields) = stat.rsplit_once(") ")?;
    fields.chars().next()
}
