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
    io::Write as _,
    num::NonZeroUsize,
    path::{Path, PathBuf},
    process,
    sync::Arc,
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
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
