//! Advisory hook commands with confined, descriptor-relative local state.

use std::{
    env,
    ffi::{OsStr, OsString},
    fs,
    io::{self, Read as _, Write as _},
    path::{Path, PathBuf},
    process::{Command, ExitCode},
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use larch_adapters::bgjob_registry;
use serde_json::{Map, Value};
use sha2::{Digest as _, Sha256};

#[cfg(unix)]
#[allow(deprecated)]
use nix::fcntl::flock;
#[cfg(unix)]
use nix::{
    errno::Errno,
    fcntl::{AtFlags, FlockArg, OFlag, open, openat, renameat},
    sys::stat::{Mode, SFlag, fchmod, fstat, fstatat, mkdirat},
    unistd::{UnlinkatFlags, unlinkat},
};
#[cfg(unix)]
use std::{
    fs::File,
    os::fd::{AsRawFd as _, OwnedFd},
    thread,
    time::Instant,
};
#[cfg(unix)]
use uuid::Uuid;

const WINDOW_SECONDS: u8 = 30;
const THRESHOLD_COUNT: &str = "3";
const STATE_DIR_NAME: &str = "larch-read-poll";
const TMP_FALLBACK: &str = "/private/tmp";
const REMINDER_TEXT: &str = "Read-poll detected: repeated identical Read calls. Use one read after state changes instead of polling.";
const MAX_STDIN_BYTES: usize = 65_536;
const MAX_STATE_BYTES: u64 = 512;
#[cfg(unix)]
const STATE_DIRECTORY_MODE: Mode = Mode::S_IRWXU;
#[cfg(unix)]
const STATE_FILE_MODE: Mode = Mode::from_bits_retain(0o600);
#[cfg(unix)]
const LOCK_WAIT: Duration = Duration::from_millis(100);
#[cfg(unix)]
const TEMP_ATTEMPTS: usize = 8;

#[derive(Clone, Debug, Eq, PartialEq)]
struct ReadEvent {
    cwd: String,
    file_path: String,
    offset: String,
    session_id: String,
    conversation_id: String,
    now: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct StateRow {
    path_hash: String,
    offset: String,
    count: String,
    epoch: String,
}

/// Run the advisory `hook anti-read-poll` command.
///
/// Every failure intentionally returns success without output: Claude hook
/// notifications must never block the tool event that triggered them.
pub fn anti_read_poll(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let Some(event) = parse_stdin_event() else {
        return ExitCode::SUCCESS;
    };

    #[cfg(unix)]
    {
        if process_event(&event).is_ok_and(|count| count == THRESHOLD_COUNT) {
            emit_reminder();
        }
    }
    #[cfg(not(unix))]
    {
        let _ = event;
    }

    ExitCode::SUCCESS
}

fn parse_stdin_event() -> Option<ReadEvent> {
    let mut input = Vec::new();
    io::stdin()
        .lock()
        .take((MAX_STDIN_BYTES + 1) as u64)
        .read_to_end(&mut input)
        .ok()?;
    if input.len() > MAX_STDIN_BYTES {
        return None;
    }
    let payload: Value = serde_json::from_slice(&input).ok()?;
    parse_payload(&payload)
}

fn parse_payload(payload: &Value) -> Option<ReadEvent> {
    let payload = payload.as_object()?;
    if string_field(payload, "tool_name") != "Read" {
        return None;
    }
    let tool_input = payload.get("tool_input")?.as_object()?;
    let file_path = string_field(tool_input, "file_path");
    if file_path.is_empty() {
        return None;
    }
    Some(ReadEvent {
        cwd: nonempty_or_root(string_field(payload, "cwd")),
        file_path,
        offset: offset_value(tool_input.get("offset")),
        session_id: string_field(payload, "session_id"),
        conversation_id: string_field(payload, "conversation_id"),
        now: now_value()?,
    })
}

fn string_field(object: &Map<String, Value>, name: &str) -> String {
    object
        .get(name)
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned()
}

fn nonempty_or_root(value: String) -> String {
    if value.is_empty() {
        "/".to_owned()
    } else {
        value
    }
}

fn offset_value(value: Option<&Value>) -> String {
    let raw = match value {
        Some(Value::String(value)) => value.clone(),
        Some(Value::Number(value)) => value.to_string(),
        _ => "0".to_owned(),
    };
    if is_offset(&raw) { raw } else { "0".to_owned() }
}

fn is_offset(value: &str) -> bool {
    let bytes = value.as_bytes();
    let start = usize::from(bytes.first() == Some(&b'-'));
    bytes.len() > start && bytes[start..].iter().all(u8::is_ascii_digit)
}

fn now_value() -> Option<String> {
    match env::var("HOOK_ANTI_READ_POLL_NOW") {
        Ok(value) if !value.is_empty() => normalize_decimal(&value),
        Ok(_) | Err(env::VarError::NotPresent) => SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .ok()
            .map(|duration| duration.as_secs().to_string()),
        Err(env::VarError::NotUnicode(_)) => None,
    }
}

fn session_key(event: &ReadEvent, discriminator: Option<&str>) -> String {
    if !event.session_id.is_empty() {
        return event.session_id.clone();
    }
    if !event.conversation_id.is_empty() {
        return event.conversation_id.clone();
    }
    discriminator.filter(|value| !value.is_empty()).map_or_else(
        || "nosession".to_owned(),
        |value| format!("nosession-{value}"),
    )
}

fn stable_digest(value: &str) -> String {
    let digest = Sha256::digest(value.as_bytes());
    format!("{digest:x}")[..32].to_owned()
}

fn state_basename(cwd: &str, resolved_session_key: &str) -> String {
    let cwd_hash = stable_digest(if cwd.is_empty() { "/" } else { cwd });
    let session_hash = stable_digest(resolved_session_key);
    format!("read-{cwd_hash}-{session_hash}.state")
}

fn path_hash(file_path: &str) -> String {
    stable_digest(file_path)
}

fn normalize_decimal(value: &str) -> Option<String> {
    if value.is_empty() || !value.bytes().all(|byte| byte.is_ascii_digit()) {
        return None;
    }
    let trimmed = value.trim_start_matches('0');
    Some(if trimmed.is_empty() {
        "0".to_owned()
    } else {
        trimmed.to_owned()
    })
}

fn increment_decimal(value: &str) -> String {
    let mut bytes = value.as_bytes().to_vec();
    for digit in bytes.iter_mut().rev() {
        if *digit == b'9' {
            *digit = b'0';
        } else {
            *digit += 1;
            return String::from_utf8_lossy(&bytes).into_owned();
        }
    }
    let mut incremented = Vec::with_capacity(bytes.len() + 1);
    incremented.push(b'1');
    incremented.extend(bytes);
    String::from_utf8_lossy(&incremented).into_owned()
}

fn decimal_at_least(left: &str, right: &str) -> bool {
    left.len() > right.len() || (left.len() == right.len() && left >= right)
}

fn elapsed_is_in_window(now: &str, prior: &str) -> bool {
    if !decimal_at_least(now, prior) {
        return false;
    }
    let mut borrow = 0_i16;
    let mut difference = Vec::with_capacity(now.len());
    let now_bytes = now.as_bytes();
    let prior_bytes = prior.as_bytes();
    for index in 0..now_bytes.len() {
        let now_index = now_bytes.len() - index - 1;
        let prior_digit = prior_bytes
            .get(prior_bytes.len().wrapping_sub(index + 1))
            .map_or(0_i16, |byte| i16::from(*byte - b'0'));
        let mut digit = i16::from(now_bytes[now_index] - b'0') - borrow - prior_digit;
        if digit < 0 {
            digit += 10;
            borrow = 1;
        } else {
            borrow = 0;
        }
        let encoded_digit = match digit {
            0 => b'0',
            1 => b'1',
            2 => b'2',
            3 => b'3',
            4 => b'4',
            5 => b'5',
            6 => b'6',
            7 => b'7',
            8 => b'8',
            9 => b'9',
            _ => return false,
        };
        difference.push(encoded_digit);
    }
    while difference.len() > 1 && difference.last() == Some(&b'0') {
        difference.pop();
    }
    match difference.len() {
        0 => true,
        1 => difference[0] - b'0' <= WINDOW_SECONDS,
        2 => (difference[1] - b'0') * 10 + (difference[0] - b'0') <= WINDOW_SECONDS,
        _ => false,
    }
}

fn parse_state_row(raw: &str) -> Option<StateRow> {
    let fields: Vec<&str> = raw.trim_end_matches('\n').split('\t').collect();
    if fields.len() != 4 {
        return None;
    }
    Some(StateRow {
        path_hash: fields[0].to_owned(),
        offset: fields[1].to_owned(),
        count: normalize_decimal(fields[2])?,
        epoch: normalize_decimal(fields[3])?,
    })
}

fn count_for(event: &ReadEvent, prior: Option<&StateRow>, event_path_hash: &str) -> String {
    let Some(prior) = prior else {
        return "1".to_owned();
    };
    if prior.path_hash == event_path_hash
        && prior.offset == event.offset
        && elapsed_is_in_window(&event.now, &prior.epoch)
    {
        increment_decimal(&prior.count)
    } else {
        "1".to_owned()
    }
}

fn emit_reminder() {
    let _ = writeln!(
        io::stdout().lock(),
        "{{\"hookSpecificOutput\":{{\"additionalContext\":\"{REMINDER_TEXT}\",\"hookEventName\":\"PostToolUse\"}}}}"
    );
}

#[cfg(unix)]
fn state_parent() -> Option<PathBuf> {
    let path = env::var_os("TMPDIR")
        .filter(|value| !value.is_empty())
        .map_or_else(|| PathBuf::from(TMP_FALLBACK), PathBuf::from);
    path.is_absolute().then_some(path)
}

#[cfg(unix)]
fn process_event(event: &ReadEvent) -> Result<String, ()> {
    let root = state_parent().ok_or(())?;
    let discriminator = env::var("HOOK_ANTI_READ_POLL_DISCRIMINATOR").ok();
    process_event_at(event, &root, discriminator.as_deref())
}

#[cfg(unix)]
fn process_event_at(
    event: &ReadEvent,
    temporary_root: &Path,
    discriminator: Option<&str>,
) -> Result<String, ()> {
    let state = StateDirectory::open(temporary_root)?;
    let name = state_basename(&event.cwd, &session_key(event, discriminator));
    let _lock = state.lock(&name)?;
    state.verify_current()?;
    let previous = read_state_row(&state, &name)?;
    let digest = path_hash(&event.file_path);
    let count = count_for(event, previous.as_ref(), &digest);
    let row = StateRow {
        path_hash: digest,
        offset: event.offset.clone(),
        count: count.clone(),
        epoch: event.now.clone(),
    };
    write_state_row(&state, &name, &row)?;
    Ok(count)
}

#[cfg(unix)]
struct StateDirectory {
    parent: OwnedFd,
    directory: OwnedFd,
}

#[cfg(unix)]
impl StateDirectory {
    fn open(temporary_root: &Path) -> Result<Self, ()> {
        let parent = open(
            temporary_root,
            OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            Mode::empty(),
        )
        .map_err(|_| ())?;
        if entry_kind(&fstat(&parent).map_err(|_| ())?) != SFlag::S_IFDIR {
            return Err(());
        }
        match mkdirat(&parent, STATE_DIR_NAME, STATE_DIRECTORY_MODE) {
            Ok(()) | Err(Errno::EEXIST) => {}
            Err(_) => return Err(()),
        }
        let directory = openat(
            &parent,
            STATE_DIR_NAME,
            OFlag::O_RDONLY | OFlag::O_DIRECTORY | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            Mode::empty(),
        )
        .map_err(|_| ())?;
        let state = Self { parent, directory };
        state.verify_current()?;
        fchmod(&state.directory, STATE_DIRECTORY_MODE).map_err(|_| ())?;
        state.verify_current()?;
        Ok(state)
    }

    fn verify_current(&self) -> Result<(), ()> {
        let opened = fstat(&self.directory).map_err(|_| ())?;
        let visible =
            fstatat(&self.parent, STATE_DIR_NAME, AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
        if entry_kind(&opened) != SFlag::S_IFDIR
            || entry_kind(&visible) != SFlag::S_IFDIR
            || !same_file(&opened, &visible)
        {
            return Err(());
        }
        Ok(())
    }

    fn lock(&self, state_name: &str) -> Result<OwnedFd, ()> {
        self.verify_current()?;
        let lock_name = format!(".{state_name}.lock");
        match fstatat(
            &self.directory,
            lock_name.as_str(),
            AtFlags::AT_SYMLINK_NOFOLLOW,
        ) {
            Ok(stat) if is_single_link_regular(&stat) => {}
            Err(Errno::ENOENT) => {}
            Ok(_) | Err(_) => return Err(()),
        }
        let lock = openat(
            &self.directory,
            lock_name.as_str(),
            OFlag::O_RDWR
                | OFlag::O_CREAT
                | OFlag::O_NOFOLLOW
                | OFlag::O_NONBLOCK
                | OFlag::O_CLOEXEC,
            STATE_FILE_MODE,
        )
        .map_err(|_| ())?;
        let opened = fstat(&lock).map_err(|_| ())?;
        let visible = fstatat(
            &self.directory,
            lock_name.as_str(),
            AtFlags::AT_SYMLINK_NOFOLLOW,
        )
        .map_err(|_| ())?;
        if !is_single_link_regular(&opened)
            || !is_single_link_regular(&visible)
            || !same_file(&opened, &visible)
        {
            return Err(());
        }
        fchmod(&lock, STATE_FILE_MODE).map_err(|_| ())?;
        assert_current_regular_entry(self, lock_name.as_str(), &opened)?;
        let deadline = Instant::now() + LOCK_WAIT;
        loop {
            #[allow(deprecated)] // `flock` is the portable BSD/Linux advisory lock primitive.
            match flock(lock.as_raw_fd(), FlockArg::LockExclusiveNonblock) {
                Ok(()) => {
                    assert_current_regular_entry(self, lock_name.as_str(), &opened)?;
                    self.verify_current()?;
                    return Ok(lock);
                }
                Err(error) if error == Errno::EWOULDBLOCK || error == Errno::EAGAIN => {
                    if Instant::now() >= deadline {
                        return Err(());
                    }
                    thread::yield_now();
                }
                Err(_) => return Err(()),
            }
        }
    }
}

#[cfg(unix)]
const fn entry_kind(stat: &nix::sys::stat::FileStat) -> SFlag {
    let raw_mode = stat.st_mode;
    SFlag::from_bits_truncate(raw_mode)
}

#[cfg(unix)]
fn same_file(left: &nix::sys::stat::FileStat, right: &nix::sys::stat::FileStat) -> bool {
    (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)
}

#[cfg(unix)]
fn is_single_link_regular(stat: &nix::sys::stat::FileStat) -> bool {
    stat.st_nlink == 1 && entry_kind(stat) == SFlag::S_IFREG
}

#[cfg(unix)]
fn assert_current_regular_entry(
    state: &StateDirectory,
    name: &str,
    expected: &nix::sys::stat::FileStat,
) -> Result<(), ()> {
    let current = fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
    if !is_single_link_regular(&current) || !same_file(expected, &current) {
        return Err(());
    }
    Ok(())
}

#[cfg(unix)]
fn read_state_row(state: &StateDirectory, name: &str) -> Result<Option<StateRow>, ()> {
    state.verify_current()?;
    let visible = match fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW) {
        Ok(stat) => stat,
        Err(Errno::ENOENT) => return Ok(None),
        Err(_) => return Err(()),
    };
    if entry_kind(&visible) == SFlag::S_IFLNK {
        unlinkat(&state.directory, name, UnlinkatFlags::NoRemoveDir).map_err(|_| ())?;
        return Ok(None);
    }
    if entry_kind(&visible) != SFlag::S_IFREG {
        return Err(());
    }
    let descriptor = openat(
        &state.directory,
        name,
        OFlag::O_RDONLY | OFlag::O_NOFOLLOW | OFlag::O_NONBLOCK | OFlag::O_CLOEXEC,
        Mode::empty(),
    )
    .map_err(|_| ())?;
    let opened = fstat(&descriptor).map_err(|_| ())?;
    let current = fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW).map_err(|_| ())?;
    if entry_kind(&opened) != SFlag::S_IFREG
        || entry_kind(&current) != SFlag::S_IFREG
        || !same_file(&opened, &current)
    {
        return Err(());
    }
    let mut bytes = Vec::new();
    File::from(descriptor)
        .take(MAX_STATE_BYTES)
        .read_to_end(&mut bytes)
        .map_err(|_| ())?;
    let raw = String::from_utf8(bytes).map_err(|_| ())?;
    Ok(parse_state_row(&raw))
}

#[cfg(unix)]
fn write_state_row(state: &StateDirectory, name: &str, row: &StateRow) -> Result<(), ()> {
    state.verify_current()?;
    let (temporary_name, descriptor) = create_temp_file(state, name)?;
    let result = (|| {
        let opened = fstat(&descriptor).map_err(|_| ())?;
        if !is_single_link_regular(&opened) {
            return Err(());
        }
        let text = format!(
            "{}\t{}\t{}\t{}\n",
            row.path_hash, row.offset, row.count, row.epoch
        );
        let mut temporary = File::from(descriptor);
        temporary.write_all(text.as_bytes()).map_err(|_| ())?;
        temporary.flush().map_err(|_| ())?;
        fchmod(&temporary, STATE_FILE_MODE).map_err(|_| ())?;
        temporary.sync_all().map_err(|_| ())?;
        drop(temporary);

        state.verify_current()?;
        assert_current_regular_entry(state, temporary_name.as_str(), &opened)?;
        assert_or_unlink_replaceable_destination(state, name)?;
        state.verify_current()?;
        assert_current_regular_entry(state, temporary_name.as_str(), &opened)?;
        renameat(
            &state.directory,
            temporary_name.as_str(),
            &state.directory,
            name,
        )
        .map_err(|_| ())?;
        state.verify_current()?;
        assert_current_regular_entry(state, name, &opened)
    })();
    if result.is_err() {
        let _ = unlinkat(
            &state.directory,
            temporary_name.as_str(),
            UnlinkatFlags::NoRemoveDir,
        );
    }
    result
}

#[cfg(unix)]
fn create_temp_file(state: &StateDirectory, name: &str) -> Result<(String, OwnedFd), ()> {
    for _ in 0..TEMP_ATTEMPTS {
        let temporary_name = format!(".{name}.tmp.{}", Uuid::new_v4().simple());
        match openat(
            &state.directory,
            temporary_name.as_str(),
            OFlag::O_WRONLY | OFlag::O_CREAT | OFlag::O_EXCL | OFlag::O_NOFOLLOW | OFlag::O_CLOEXEC,
            STATE_FILE_MODE,
        ) {
            Ok(descriptor) => {
                let opened = fstat(&descriptor).map_err(|_| ())?;
                if !is_single_link_regular(&opened) {
                    return Err(());
                }
                return Ok((temporary_name, descriptor));
            }
            Err(Errno::EEXIST) => {}
            Err(_) => return Err(()),
        }
    }
    Err(())
}

#[cfg(unix)]
fn assert_or_unlink_replaceable_destination(state: &StateDirectory, name: &str) -> Result<(), ()> {
    match fstatat(&state.directory, name, AtFlags::AT_SYMLINK_NOFOLLOW) {
        Err(Errno::ENOENT) => Ok(()),
        Ok(stat) if entry_kind(&stat) == SFlag::S_IFLNK => {
            unlinkat(&state.directory, name, UnlinkatFlags::NoRemoveDir).map_err(|_| ())
        }
        Ok(stat) if is_single_link_regular(&stat) => Ok(()),
        Err(_) | Ok(_) => Err(()),
    }
}

// ===========================================================================
// PreToolUse deny hooks (fail-closed shim fallbacks live in the sibling
// scripts). Each verb reads the hook JSON from stdin, always exits SUCCESS, and
// emits Anthropic's `hookSpecificOutput` deny envelope on stdout to block; an
// allow emits nothing. Ported from scripts/block-submodule-edit.sh,
// scripts/deny-edit-write.sh, and scripts/hook-deny-run-in-background.sh.
// ===========================================================================

/// Bounded symlink-resolution depth that doubles as a cycle detector.
const MAX_SYMLINK_HOPS: usize = 40;

const DENY_EDIT_WRITE_TTL_MINUTES: u64 = 360;
const DENY_EDIT_WRITE_TOKENS: [&str; 7] = [
    "research",
    "audit-umbrella",
    "file-bug",
    "complete-umbrella",
    "debate",
    "triage",
    "umbrella",
];

/// Fixed read-only-repo deny reason shared by the verb and its shim fallback.
const READ_ONLY_REPO_DENY: &str = "The active skill is read-only-repo -- Edit/Write/NotebookEdit outside /tmp or the larch session cache is not permitted.";

const SUBMODULE_PARSE_DENY: &str =
    "submodule edit guard: failed to parse tool input, blocking as precaution";
const SUBMODULE_READ_STDIN_DENY: &str =
    "submodule edit guard: failed to read stdin, blocking as precaution";
const SUBMODULE_NOT_ABSOLUTE_DENY: &str =
    "submodule edit guard: tool_input.file_path is not absolute, blocking as precaution";
const SUBMODULE_CYCLE_DENY: &str = "submodule edit guard: symlink resolution exceeded 40 hops (possible cycle), blocking as precaution";
const SUBMODULE_READLINK_DENY: &str =
    "submodule edit guard: readlink failed, blocking as precaution";
const SUBMODULE_EMPTY_TARGET_DENY: &str =
    "submodule edit guard: readlink returned empty target, blocking as precaution";

const RUN_IN_BACKGROUND_MALFORMED_DENY: &str =
    "run_in_background denied: malformed hook JSON cannot rule out Bash background launch";
const RUN_IN_BACKGROUND_MISSING_CWD_DENY: &str =
    "run_in_background denied: missing canonical cwd for Bash background launch";
const RUN_IN_BACKGROUND_REGISTRY_READ_DENY: &str =
    "run_in_background denied: cannot read active bgjob registry entry";

/// A `PreToolUse` decision: allow silently or deny with a reason.
enum Decision {
    Allow,
    Deny(String),
}

/// Build the `hookSpecificOutput` deny envelope (byte-compatible with the
/// scripts' `jq -cn` output: fixed ASCII field order, `serde_json`-escaped
/// reason). No trailing newline.
fn deny_envelope(reason: &str) -> String {
    let escaped = serde_json::to_string(reason).unwrap_or_else(|_| "\"\"".to_owned());
    format!(
        "{{\"hookSpecificOutput\":{{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":{escaped}}}}}"
    )
}

/// Emit the deny envelope to stdout with the scripts' trailing newline.
fn emit_deny(reason: &str) {
    let _ = writeln!(io::stdout().lock(), "{}", deny_envelope(reason));
}

/// Read all of stdin, or `None` when the read itself fails.
fn read_hook_stdin() -> Option<Vec<u8>> {
    let mut input = Vec::new();
    io::stdin().lock().read_to_end(&mut input).ok()?;
    Some(input)
}

fn is_symlink(path: &Path) -> bool {
    fs::symlink_metadata(path).is_ok_and(|meta| meta.file_type().is_symlink())
}

/// Outcome of the bounded symlink-chain walk.
enum SymlinkResolution {
    Resolved(PathBuf),
    Cycle,
    ReadlinkFailed,
    EmptyTarget,
}

/// Resolve a symlink chain by hand, matching the scripts' pure-shell loop:
/// bounded depth (cycle detection), relative targets rebased against the link's
/// own directory, non-symlink inputs returned unchanged.
fn resolve_symlinks(path: &Path) -> SymlinkResolution {
    let mut resolved = path.to_path_buf();
    let mut depth = 0_usize;
    while is_symlink(&resolved) {
        if depth >= MAX_SYMLINK_HOPS {
            return SymlinkResolution::Cycle;
        }
        let Ok(target) = fs::read_link(&resolved) else {
            return SymlinkResolution::ReadlinkFailed;
        };
        if target.as_os_str().is_empty() {
            return SymlinkResolution::EmptyTarget;
        }
        resolved = if target.is_absolute() {
            target
        } else {
            resolved
                .parent()
                .map_or_else(|| target.clone(), |parent| parent.join(&target))
        };
        depth += 1;
    }
    SymlinkResolution::Resolved(resolved)
}

/// Outcome of the nearest-existing-ancestor probe plus canonicalization.
enum ProbeDir {
    /// Walked to `/` without finding any existing ancestor.
    Root,
    /// The probe directory could not be canonicalized.
    NotCanonical,
    /// Canonical existing probe directory.
    Dir(PathBuf),
}

/// Find the nearest existing ancestor of `file_path`, then canonicalize the
/// directory to inspect (its own dir when it landed on a file).
fn nearest_canonical_probe_dir(file_path: &Path) -> ProbeDir {
    let root = Path::new("/");
    let mut probe = file_path.to_path_buf();
    while !probe.exists() && probe != root {
        match probe.parent() {
            Some(parent) => probe = parent.to_path_buf(),
            None => break,
        }
    }
    if probe == root {
        return ProbeDir::Root;
    }
    let probe_dir = if probe.is_file() {
        probe
            .parent()
            .map_or_else(|| PathBuf::from("/"), Path::to_path_buf)
    } else {
        probe
    };
    fs::canonicalize(&probe_dir).map_or(ProbeDir::NotCanonical, ProbeDir::Dir)
}

/// Run a `git -C <dir> <args...>` query, returning its trimmed single-line
/// stdout when the command succeeds with non-empty output.
fn git_query(dir: &Path, args: &[&str]) -> Option<PathBuf> {
    let output = Command::new("git")
        .arg("-C")
        .arg(dir)
        .args(args)
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }
    let text = String::from_utf8(output.stdout).ok()?;
    let trimmed = text.trim_end_matches(['\n', '\r']);
    (!trimmed.is_empty()).then(|| PathBuf::from(trimmed))
}

/// Canonicalize a path that must resolve to an existing directory.
fn canonical_dir(path: &Path) -> Option<PathBuf> {
    if path.as_os_str().is_empty() {
        return None;
    }
    let canonical = fs::canonicalize(path).ok()?;
    canonical.is_dir().then_some(canonical)
}

/// Whether `candidate` equals `root` or sits underneath it (component-wise).
fn path_is_within(candidate: &Path, root: &Path) -> bool {
    candidate.starts_with(root)
}

/// Block edits to files inside a checked-out submodule of the current repo.
///
/// Fails CLOSED on stdin/parse/readlink/cycle; fails OPEN for non-git and
/// canonicalization failures. Always returns `ExitCode::SUCCESS`.
pub fn block_submodule_edit(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    let decision = read_hook_stdin().map_or_else(
        || Decision::Deny(SUBMODULE_READ_STDIN_DENY.to_owned()),
        |input| {
            let project_dir = env::var_os("CLAUDE_PROJECT_DIR").filter(|value| !value.is_empty());
            let pwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("/"));
            submodule_decision(&input, project_dir.as_deref(), &pwd)
        },
    );
    if let Decision::Deny(reason) = decision {
        emit_deny(&reason);
    }
    ExitCode::SUCCESS
}

fn submodule_decision(input: &[u8], project_dir: Option<&OsStr>, pwd: &Path) -> Decision {
    let Ok(payload) = serde_json::from_slice::<Value>(input) else {
        return Decision::Deny(SUBMODULE_PARSE_DENY.to_owned());
    };
    let file_path = payload
        .get("tool_input")
        .and_then(Value::as_object)
        .map(|input| string_field(input, "file_path"))
        .unwrap_or_default();
    if file_path.is_empty() {
        return Decision::Allow;
    }
    let file_path = PathBuf::from(file_path);
    if !file_path.is_absolute() {
        return Decision::Deny(SUBMODULE_NOT_ABSOLUTE_DENY.to_owned());
    }
    let repo_root = project_dir
        .and_then(|dir| git_query(Path::new(dir), &["rev-parse", "--show-toplevel"]))
        .or_else(|| git_query(pwd, &["rev-parse", "--show-toplevel"]));
    let Some(repo_root) = repo_root else {
        return Decision::Allow;
    };
    let Ok(repo_root) = fs::canonicalize(&repo_root) else {
        eprintln!("submodule edit guard: warning: could not canonicalize repo root");
        return Decision::Allow;
    };
    let resolved = match resolve_symlinks(&file_path) {
        SymlinkResolution::Resolved(path) => path,
        SymlinkResolution::Cycle => return Decision::Deny(SUBMODULE_CYCLE_DENY.to_owned()),
        SymlinkResolution::ReadlinkFailed => {
            return Decision::Deny(SUBMODULE_READLINK_DENY.to_owned());
        }
        SymlinkResolution::EmptyTarget => {
            return Decision::Deny(SUBMODULE_EMPTY_TARGET_DENY.to_owned());
        }
    };
    let probe_dir = match nearest_canonical_probe_dir(&resolved) {
        ProbeDir::Root => return Decision::Allow,
        ProbeDir::NotCanonical => {
            eprintln!("submodule edit guard: warning: could not canonicalize probe dir");
            return Decision::Allow;
        }
        ProbeDir::Dir(dir) => dir,
    };
    let Some(file_repo_root) = git_query(&probe_dir, &["rev-parse", "--show-toplevel"]) else {
        return Decision::Allow;
    };
    let Ok(file_repo_root) = fs::canonicalize(&file_repo_root) else {
        eprintln!("submodule edit guard: warning: could not canonicalize file repo root");
        return Decision::Allow;
    };
    if file_repo_root == repo_root {
        return Decision::Allow;
    }
    let Some(superproject) = git_query(
        &file_repo_root,
        &["rev-parse", "--show-superproject-working-tree"],
    ) else {
        return Decision::Allow;
    };
    let Ok(superproject) = fs::canonicalize(&superproject) else {
        eprintln!("submodule edit guard: warning: could not canonicalize superproject path");
        return Decision::Allow;
    };
    if superproject != repo_root {
        return Decision::Allow;
    }
    let submodule_path = file_repo_root.strip_prefix(&repo_root).map_or_else(
        |_| file_repo_root.to_string_lossy().into_owned(),
        |relative| relative.to_string_lossy().into_owned(),
    );
    Decision::Deny(format!(
        "This file is inside the '{submodule_path}' submodule. Never edit submodules directly here; file PRs in the submodule's own repo instead."
    ))
}

/// Token-scoped read-only-repo guard: while a recognized skill token has a fresh
/// activation sentinel, permit Edit/Write/NotebookEdit only for canonical paths
/// under `/tmp` or the larch cache sessions root. Always returns
/// `ExitCode::SUCCESS`.
pub fn deny_edit_write(arguments: &[OsString]) -> ExitCode {
    let token = arguments
        .first()
        .and_then(|arg| arg.to_str())
        .unwrap_or_default();
    let Some(activation_dir) = deny_edit_write_activation_dir() else {
        // No HOME/XDG root to resolve the sentinel: fail open (leaked, tokenless
        // registrations stay disarmed).
        return ExitCode::SUCCESS;
    };
    let ttl = Duration::from_secs(DENY_EDIT_WRITE_TTL_MINUTES * 60);
    if !activation_is_live(token, &activation_dir, SystemTime::now(), ttl) {
        return ExitCode::SUCCESS;
    }
    let input = read_hook_stdin().unwrap_or_default();
    let Ok(tmp_root) = fs::canonicalize("/tmp") else {
        emit_deny(READ_ONLY_REPO_DENY);
        return ExitCode::SUCCESS;
    };
    let sessions_root =
        deny_edit_write_sessions_root().and_then(|root| fs::canonicalize(root).ok());
    if let Decision::Deny(reason) =
        deny_edit_write_path_decision(&input, &tmp_root, sessions_root.as_deref())
    {
        emit_deny(&reason);
    }
    ExitCode::SUCCESS
}

fn deny_edit_write_cache_child(suffix: &str) -> Option<PathBuf> {
    env::var_os("XDG_CACHE_HOME")
        .filter(|value| !value.is_empty())
        .map(|xdg| PathBuf::from(xdg).join(format!("larch/{suffix}")))
        .or_else(|| {
            env::var_os("HOME")
                .filter(|value| !value.is_empty())
                .map(|home| PathBuf::from(home).join(format!(".cache/larch/{suffix}")))
        })
}

fn deny_edit_write_activation_dir() -> Option<PathBuf> {
    deny_edit_write_cache_child("deny-edit-write-active")
}

fn deny_edit_write_sessions_root() -> Option<PathBuf> {
    deny_edit_write_cache_child("sessions")
}

fn activation_is_live(token: &str, activation_dir: &Path, now: SystemTime, ttl: Duration) -> bool {
    if !DENY_EDIT_WRITE_TOKENS.contains(&token) {
        return false;
    }
    let Ok(entries) = fs::read_dir(activation_dir) else {
        return false;
    };
    let prefix = format!("{token}-");
    for entry in entries.flatten() {
        let Some(name) = entry.file_name().to_str().map(str::to_owned) else {
            continue;
        };
        if !name.starts_with(&prefix) {
            continue;
        }
        let Ok(meta) = fs::symlink_metadata(entry.path()) else {
            continue;
        };
        if !meta.file_type().is_file() {
            continue;
        }
        let Ok(modified) = meta.modified() else {
            continue;
        };
        // `find -mmin -TTL`: modified less than TTL minutes ago (a future mtime
        // also matches the "within window" predicate).
        match now.duration_since(modified) {
            Ok(age) if age < ttl => return true,
            Err(_) => return true,
            Ok(_) => {}
        }
    }
    false
}

fn deny_edit_write_extract_path(payload: &Value) -> Option<String> {
    let input = payload.get("tool_input")?.as_object()?;
    for key in ["file_path", "notebook_path"] {
        let value = input.get(key).and_then(Value::as_str).unwrap_or_default();
        if !value.is_empty() {
            return Some(value.to_owned());
        }
    }
    None
}

fn deny_edit_write_path_decision(
    input: &[u8],
    tmp_root: &Path,
    sessions_root: Option<&Path>,
) -> Decision {
    let Ok(payload) = serde_json::from_slice::<Value>(input) else {
        return Decision::Deny(READ_ONLY_REPO_DENY.to_owned());
    };
    let Some(path) = deny_edit_write_extract_path(&payload) else {
        return Decision::Deny(READ_ONLY_REPO_DENY.to_owned());
    };
    let path = PathBuf::from(path);
    if !path.is_absolute() {
        return Decision::Deny(READ_ONLY_REPO_DENY.to_owned());
    }
    let SymlinkResolution::Resolved(resolved) = resolve_symlinks(&path) else {
        return Decision::Deny(READ_ONLY_REPO_DENY.to_owned());
    };
    let ProbeDir::Dir(probe_dir) = nearest_canonical_probe_dir(&resolved) else {
        return Decision::Deny(READ_ONLY_REPO_DENY.to_owned());
    };
    if path_is_within(&probe_dir, tmp_root) {
        return Decision::Allow;
    }
    if sessions_root.is_some_and(|sessions| path_is_within(&probe_dir, sessions)) {
        return Decision::Allow;
    }
    Decision::Deny(READ_ONLY_REPO_DENY.to_owned())
}

/// Deny Bash `run_in_background` launches while a larch bgjob is registered for
/// this clone. Malformed JSON denies (a background launch cannot be ruled out);
/// a combinator-free documented `bgjob wait` is the one carve-out. Always
/// returns `ExitCode::SUCCESS`.
pub fn deny_run_in_background(arguments: &[OsString]) -> ExitCode {
    if !arguments.is_empty() {
        return ExitCode::SUCCESS;
    }
    if env_flag("LARCH_HOOK_DENY_RUN_IN_BACKGROUND_DISABLE")
        || env_flag("LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT")
    {
        return ExitCode::SUCCESS;
    }
    let input = read_hook_stdin().unwrap_or_default();
    let registry_root = env::var_os("LARCH_BGJOB_REGISTRY_ROOT")
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .or_else(|| {
            env::var_os("HOME")
                .filter(|value| !value.is_empty())
                .map(|home| PathBuf::from(home).join(".cache/larch/daemons"))
        });
    if let Decision::Deny(reason) = run_in_background_decision(&input, registry_root.as_deref()) {
        emit_deny(&reason);
    }
    ExitCode::SUCCESS
}

fn env_flag(name: &str) -> bool {
    env::var(name).as_deref() == Ok("1")
}

/// Render a JSON value the way `jq -r '<expr> // false'` would for the
/// `run_in_background` field: missing/null → `"false"`, otherwise the scalar.
fn render_run_in_background(value: Option<&Value>) -> String {
    match value {
        None | Some(Value::Null) => "false".to_owned(),
        Some(Value::Bool(flag)) => flag.to_string(),
        Some(Value::String(text)) => text.clone(),
        Some(Value::Number(number)) => number.to_string(),
        Some(other) => other.to_string(),
    }
}

fn background_launch_intended(run_bg: &str, command_text: &str) -> bool {
    if run_bg == "true" {
        return true;
    }
    // Heuristic mirror of `*run_in_background*true*`: the command embeds the
    // flag set to true even though the parsed field did not read as `true`.
    command_text
        .find("run_in_background")
        .is_some_and(|index| command_text[index..].contains("true"))
}

fn is_documented_bgjob_wait(command: &str) -> bool {
    const COMBINATORS: [&str; 8] = ["&&", "||", ";", "|", "`", "$(", ">", "<"];
    let mut normalized: String = command
        .chars()
        .map(|character| match character {
            '\n' | '\r' | '\t' => ' ',
            other => other,
        })
        .collect();
    while normalized.contains("  ") {
        normalized = normalized.replace("  ", " ");
    }
    if COMBINATORS.iter().any(|token| normalized.contains(token)) {
        return false;
    }
    let Some(index) = normalized.find("/scripts/larch.sh") else {
        return false;
    };
    let rest = &normalized[index..];
    rest.contains(" bgjob wait ") || rest.ends_with(" bgjob wait")
}

fn clone_paths_same(marker: &Path, current: &Path) -> bool {
    marker == current || current.starts_with(marker) || marker.starts_with(current)
}

fn run_in_background_decision(input: &[u8], registry_root: Option<&Path>) -> Decision {
    let Ok(payload) = serde_json::from_slice::<Value>(input) else {
        return Decision::Deny(RUN_IN_BACKGROUND_MALFORMED_DENY.to_owned());
    };
    if payload
        .get("tool_name")
        .and_then(Value::as_str)
        .unwrap_or_default()
        != "Bash"
    {
        return Decision::Allow;
    }
    let tool_input = payload.get("tool_input").and_then(Value::as_object);
    let run_bg =
        render_run_in_background(tool_input.and_then(|input| input.get("run_in_background")));
    let command_text = tool_input
        .map(|input| string_field(input, "command"))
        .unwrap_or_default();
    if !background_launch_intended(&run_bg, &command_text) {
        return Decision::Allow;
    }
    if is_documented_bgjob_wait(&command_text) {
        return Decision::Allow;
    }
    let cwd = payload
        .get("cwd")
        .and_then(Value::as_str)
        .unwrap_or_default();
    let Some(cwd_canon) = canonical_dir(Path::new(cwd)) else {
        return Decision::Deny(RUN_IN_BACKGROUND_MISSING_CWD_DENY.to_owned());
    };
    let Some(registry_root) = registry_root.filter(|root| root.is_dir()) else {
        return Decision::Allow;
    };
    let Ok(entries) = fs::read_dir(registry_root) else {
        return Decision::Allow;
    };
    let mut paths: Vec<PathBuf> = entries
        .flatten()
        .map(|entry| entry.path())
        .filter(|path| path.extension().is_some_and(|value| value == "env"))
        .collect();
    paths.sort();
    for entry in paths {
        let Ok(meta) = fs::symlink_metadata(&entry) else {
            continue;
        };
        if !meta.file_type().is_file() {
            continue;
        }
        match bgjob_registry::entry_clone_path(&entry) {
            Err(_) => return Decision::Deny(RUN_IN_BACKGROUND_REGISTRY_READ_DENY.to_owned()),
            Ok(None) => {}
            Ok(Some(clone_path)) => {
                if let Some(clone_canon) = canonical_dir(&clone_path)
                    && clone_paths_same(&clone_canon, &cwd_canon)
                {
                    return Decision::Deny(format!(
                        "run_in_background denied: active larch bgjob registry exists for this clone ({})",
                        entry.display()
                    ));
                }
            }
        }
    }
    Decision::Allow
}

#[cfg(test)]
mod tests {
    use super::{
        REMINDER_TEXT, ReadEvent, STATE_DIR_NAME, StateDirectory, StateRow, count_for,
        elapsed_is_in_window, increment_decimal, normalize_decimal, parse_payload, parse_state_row,
        path_hash, process_event_at, state_basename, write_state_row,
    };
    #[cfg(unix)]
    use nix::{sys::stat::Mode, unistd::mkfifo};
    use serde_json::json;
    #[cfg(unix)]
    use std::os::unix::fs::PermissionsExt as _;
    use std::{
        fs,
        sync::{Arc, Barrier},
        thread,
    };
    use tempfile::TempDir;

    fn event(now: &str) -> ReadEvent {
        ReadEvent {
            cwd: "/project".to_owned(),
            file_path: "/project/private name.md".to_owned(),
            offset: "7".to_owned(),
            session_id: "session".to_owned(),
            conversation_id: String::new(),
            now: now.to_owned(),
        }
    }

    #[test]
    fn parses_only_complete_read_events() {
        let valid = json!({
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/example", "offset": -3},
            "cwd": "",
            "session_id": "session",
        });
        let parsed = parse_payload(&valid).expect("valid event");
        assert_eq!(parsed.cwd, "/");
        assert_eq!(parsed.offset, "-3");
        assert!(parse_payload(&json!({"tool_name": "Bash"})).is_none());
        assert!(parse_payload(&json!({"tool_name": "Read", "tool_input": {}})).is_none());
        let decimal_offset = json!({
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/example", "offset": 1.5},
        });
        assert_eq!(parse_payload(&decimal_offset).expect("event").offset, "0");
    }

    #[test]
    fn decimal_helpers_keep_large_python_compatible_values() {
        assert_eq!(increment_decimal("999"), "1000");
        assert!(normalize_decimal("not-a-time").is_none());
        assert!(elapsed_is_in_window("100", "70"));
        assert!(!elapsed_is_in_window("101", "70"));
        assert!(elapsed_is_in_window(
            "100000000000000000000",
            "99999999999999999999"
        ));
        assert!(!elapsed_is_in_window("9", "10"));
        let prior = parse_state_row("digest\t7\t0002\t00070\n").expect("row");
        let current = event("100");
        assert_eq!(count_for(&current, Some(&prior), "digest"), "3");
    }

    #[cfg(unix)]
    #[test]
    fn counts_reads_and_persists_only_hashed_paths() {
        let temporary = TempDir::new().expect("temporary root");
        for now in ["100", "101", "102", "103"] {
            let count = process_event_at(&event(now), temporary.path(), None).expect("event");
            assert_eq!(count, (now.parse::<u8>().expect("time") - 99).to_string());
        }
        let name = state_basename("/project", "session");
        assert!(!name.contains("/project"));
        assert!(!name.contains("session"));
        let row = fs::read_to_string(temporary.path().join(STATE_DIR_NAME).join(&name))
            .expect("state row");
        assert_eq!(
            row,
            format!("{}\t7\t4\t103\n", path_hash("/project/private name.md"))
        );
        assert!(!row.contains("/project/private name.md"));
        let state_directory = temporary.path().join(STATE_DIR_NAME);
        assert_eq!(
            fs::metadata(&state_directory)
                .expect("state directory metadata")
                .permissions()
                .mode()
                & 0o777,
            0o700
        );
        assert_eq!(
            fs::metadata(state_directory.join(name))
                .expect("state file metadata")
                .permissions()
                .mode()
                & 0o777,
            0o600
        );
    }

    #[cfg(unix)]
    #[test]
    fn separates_sessions_and_resets_stale_or_malformed_rows() {
        let temporary = TempDir::new().expect("temporary root");
        let first = event("100");
        let second_session = ReadEvent {
            session_id: "other".to_owned(),
            now: "101".to_owned(),
            ..first.clone()
        };
        assert_eq!(
            process_event_at(&first, temporary.path(), None),
            Ok("1".to_owned())
        );
        assert_eq!(
            process_event_at(&second_session, temporary.path(), None),
            Ok("1".to_owned())
        );
        let stale = ReadEvent {
            now: "131".to_owned(),
            ..first.clone()
        };
        assert_eq!(
            process_event_at(&stale, temporary.path(), None),
            Ok("1".to_owned())
        );
        let name = state_basename("/project", "session");
        fs::write(
            temporary.path().join(STATE_DIR_NAME).join(name),
            "malformed\n",
        )
        .expect("write malformed state");
        let current = ReadEvent {
            now: "132".to_owned(),
            ..first
        };
        assert_eq!(
            process_event_at(&current, temporary.path(), None),
            Ok("1".to_owned())
        );
    }

    #[cfg(unix)]
    #[test]
    fn state_directory_and_leaf_attacks_fail_open_or_replace_only_the_leaf() {
        let temporary = TempDir::new().expect("temporary root");
        let redirect = temporary.path().join("redirect");
        fs::create_dir(&redirect).expect("redirect");
        std::os::unix::fs::symlink(&redirect, temporary.path().join(STATE_DIR_NAME))
            .expect("state symlink");
        assert!(process_event_at(&event("100"), temporary.path(), None).is_err());
        assert!(
            fs::read_dir(&redirect)
                .expect("redirect entries")
                .next()
                .is_none()
        );

        fs::remove_file(temporary.path().join(STATE_DIR_NAME)).expect("remove state symlink");
        let state = temporary.path().join(STATE_DIR_NAME);
        fs::create_dir(&state).expect("state directory");
        let name = state_basename("/project", "session");
        let poison = temporary.path().join("poison");
        fs::write(&poison, "unchanged\n").expect("poison");
        std::os::unix::fs::symlink(&poison, state.join(&name)).expect("leaf symlink");
        assert_eq!(
            process_event_at(&event("101"), temporary.path(), None),
            Ok("1".to_owned())
        );
        assert_eq!(
            fs::read_to_string(&poison).expect("poison read"),
            "unchanged\n"
        );
        assert!(state.join(name).is_file());
    }

    #[cfg(unix)]
    #[test]
    fn rejects_non_regular_leaf_and_detects_directory_replacement() {
        let temporary = TempDir::new().expect("temporary root");
        let state = temporary.path().join(STATE_DIR_NAME);
        fs::create_dir(&state).expect("state directory");
        let name = state_basename("/project", "session");
        fs::create_dir(state.join(&name)).expect("nonregular leaf");
        assert!(process_event_at(&event("100"), temporary.path(), None).is_err());

        fs::remove_dir_all(state.join(&name)).expect("remove nonregular leaf");
        mkfifo(state.join(&name).as_path(), Mode::S_IRUSR).expect("fifo leaf");
        assert!(process_event_at(&event("100"), temporary.path(), None).is_err());
        fs::remove_file(state.join(&name)).expect("remove fifo leaf");
        let open_state = StateDirectory::open(temporary.path()).expect("open state");
        let moved = temporary.path().join("moved-state");
        fs::rename(&state, &moved).expect("move state");
        fs::create_dir(&state).expect("replacement state");
        assert!(open_state.verify_current().is_err());
        assert!(
            write_state_row(
                &open_state,
                &name,
                &StateRow {
                    path_hash: path_hash("/project/private name.md"),
                    offset: "7".to_owned(),
                    count: "1".to_owned(),
                    epoch: "101".to_owned(),
                },
            )
            .is_err()
        );
        assert!(
            fs::read_dir(&state)
                .expect("replacement entries")
                .next()
                .is_none()
        );
    }

    #[cfg(unix)]
    #[test]
    fn concurrent_updates_leave_one_complete_regular_row() {
        let temporary = Arc::new(TempDir::new().expect("temporary root"));
        let barrier = Arc::new(Barrier::new(9));
        let mut workers = Vec::new();
        for _ in 0..8 {
            let temporary = Arc::clone(&temporary);
            let barrier = Arc::clone(&barrier);
            workers.push(thread::spawn(move || {
                barrier.wait();
                process_event_at(&event("100"), temporary.path(), None)
            }));
        }
        barrier.wait();
        let results: Vec<_> = workers
            .into_iter()
            .map(|worker| worker.join().expect("worker did not panic"))
            .collect();
        // The hook may deliberately skip a contended advisory update rather
        // than block a Read event. Successful concurrent writers must still
        // leave one complete, parseable state row.
        assert!(results.iter().any(Result::is_ok));
        let name = state_basename("/project", "session");
        let row = fs::read_to_string(temporary.path().join(STATE_DIR_NAME).join(name))
            .expect("state row");
        let parsed = parse_state_row(&row).expect("complete row");
        assert_eq!(parsed.path_hash, path_hash("/project/private name.md"));
        assert_eq!(parsed.offset, "7");
        assert_eq!(parsed.epoch, "100");
        assert!(
            parsed
                .count
                .parse::<u8>()
                .is_ok_and(|count| (1..=8).contains(&count))
        );
    }

    #[test]
    fn reminder_text_is_path_free_and_stable() {
        assert_eq!(
            REMINDER_TEXT,
            "Read-poll detected: repeated identical Read calls. Use one read after state changes instead of polling."
        );
        assert!(!REMINDER_TEXT.contains('/'));
    }
}

#[cfg(test)]
mod deny_hook_tests {
    use super::{
        Decision, READ_ONLY_REPO_DENY, RUN_IN_BACKGROUND_MALFORMED_DENY, activation_is_live,
        deny_edit_write_path_decision, deny_envelope, is_documented_bgjob_wait,
        run_in_background_decision, submodule_decision,
    };
    use serde_json::json;
    use std::{
        fs,
        path::Path,
        time::{Duration, SystemTime},
    };
    use tempfile::TempDir;

    fn is_deny(decision: &Decision) -> bool {
        matches!(decision, Decision::Deny(_))
    }

    fn deny_reason(decision: &Decision) -> String {
        match decision {
            Decision::Deny(reason) => reason.clone(),
            Decision::Allow => panic!("expected deny, got allow"),
        }
    }

    // ---- deny-run-in-background -------------------------------------------

    fn bash_bytes(cwd: &str, command: &str, run_bg: bool) -> Vec<u8> {
        json!({
            "tool_name": "Bash",
            "cwd": cwd,
            "tool_input": {"command": command, "run_in_background": run_bg},
        })
        .to_string()
        .into_bytes()
    }

    #[test]
    fn run_in_background_registry_and_carveouts() {
        let sandbox = TempDir::new().expect("sandbox");
        let clone = sandbox.path().join("clone");
        fs::create_dir_all(&clone).expect("clone");
        let clone_str = clone.to_str().expect("clone utf8");
        let registry = sandbox.path().join("registry");
        fs::create_dir_all(&registry).expect("registry");

        // No registry rows for this clone: allow.
        assert!(!is_deny(&run_in_background_decision(
            &bash_bytes(clone_str, "sleep 1", true),
            Some(&registry),
        )));

        // A registry row naming this clone denies a background launch.
        fs::write(
            registry.join("run-demo.env"),
            format!("CLONE_PATH={clone_str}\n"),
        )
        .expect("registry row");
        assert!(
            deny_reason(&run_in_background_decision(
                &bash_bytes(clone_str, "sleep 1", true),
                Some(&registry),
            ))
            .contains("active larch bgjob")
        );

        // Foreground Bash is allowed even with a live registry row.
        assert!(!is_deny(&run_in_background_decision(
            &bash_bytes(clone_str, "sleep 1", false),
            Some(&registry),
        )));

        // Non-Bash tools are out of scope.
        let read = json!({"tool_name": "Read", "tool_input": {}})
            .to_string()
            .into_bytes();
        assert!(!is_deny(&run_in_background_decision(
            &read,
            Some(&registry)
        )));

        // Malformed JSON denies (a background launch cannot be ruled out).
        assert_eq!(
            deny_reason(&run_in_background_decision(b"not json", Some(&registry))),
            RUN_IN_BACKGROUND_MALFORMED_DENY
        );

        // The documented combinator-free bgjob wait is the one carve-out.
        let wait =
            "${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh bgjob wait --step leaf-1 --max-wait-s 7200";
        assert!(!is_deny(&run_in_background_decision(
            &bash_bytes(clone_str, wait, true),
            Some(&registry),
        )));

        // A same-named decoy path is not the carve-out; the live registry denies.
        let decoy = "/tmp/decoy/larch.sh bgjob wait --step x --max-wait-s 7200";
        assert!(is_deny(&run_in_background_decision(
            &bash_bytes(clone_str, decoy, true),
            Some(&registry),
        )));

        // A combinator before the wait disqualifies the carve-out.
        let wrapped = "sleep 1 && ${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh bgjob wait --step x --max-wait-s 7200";
        assert!(is_deny(&run_in_background_decision(
            &bash_bytes(clone_str, wrapped, true),
            Some(&registry),
        )));

        // Missing cwd denies a confirmed background Bash launch.
        let no_cwd = json!({
            "tool_name": "Bash",
            "tool_input": {"command": "sleep 1", "run_in_background": true},
        })
        .to_string()
        .into_bytes();
        assert!(is_deny(&run_in_background_decision(
            &no_cwd,
            Some(&registry)
        )));
    }

    #[test]
    fn documented_bgjob_wait_recognition() {
        assert!(is_documented_bgjob_wait(
            "\"${X}/scripts/larch.sh\" bgjob wait --step a --max-wait-s 7200"
        ));
        assert!(is_documented_bgjob_wait("${X}/scripts/larch.sh bgjob wait"));
        // Whitespace (newlines/tabs) collapses before matching.
        assert!(is_documented_bgjob_wait(
            "${X}/scripts/larch.sh \n  bgjob wait \\\n  --step a"
        ));
        // Combinators, redirections, and command substitution disqualify.
        assert!(!is_documented_bgjob_wait(
            "sleep 1 && ${X}/scripts/larch.sh bgjob wait --step a"
        ));
        assert!(!is_documented_bgjob_wait(
            "cat x > y /scripts/larch.sh bgjob wait"
        ));
        // A decoy path without /scripts/larch.sh is not the carve-out.
        assert!(!is_documented_bgjob_wait(
            "/tmp/decoy/larch.sh bgjob wait --step a"
        ));
    }

    // ---- deny-edit-write --------------------------------------------------

    fn tool_path_bytes(key: &str, value: &str) -> Vec<u8> {
        json!({"tool_input": {key: value}}).to_string().into_bytes()
    }

    #[test]
    fn activation_liveness_gate() {
        let ttl = Duration::from_secs(super::DENY_EDIT_WRITE_TTL_MINUTES * 60);
        let now = SystemTime::now();

        let dir = TempDir::new().expect("activation dir");
        // An unrecognized token never activates, even with a sentinel present.
        fs::write(dir.path().join("unknown-1"), "").expect("unknown sentinel");
        assert!(!activation_is_live("unknown", dir.path(), now, ttl));
        // A recognized token with a fresh sentinel is live.
        fs::write(dir.path().join("research-123"), "").expect("research sentinel");
        assert!(activation_is_live("research", dir.path(), now, ttl));

        // Token scoping keeps consumers independent.
        let scoped = TempDir::new().expect("scoped dir");
        fs::write(scoped.path().join("file-bug-1"), "").expect("file-bug sentinel");
        assert!(activation_is_live("file-bug", scoped.path(), now, ttl));
        assert!(!activation_is_live("research", scoped.path(), now, ttl));

        // A missing activation directory is inactive.
        assert!(!activation_is_live(
            "research",
            &dir.path().join("absent"),
            now,
            ttl
        ));

        // A stale sentinel does not activate (evaluate as if 7 hours later).
        let stale = TempDir::new().expect("stale dir");
        fs::write(stale.path().join("research-old"), "").expect("stale sentinel");
        let later = now + Duration::from_secs(7 * 60 * 60);
        assert!(!activation_is_live("research", stale.path(), later, ttl));
    }

    #[test]
    fn active_tmp_policy() {
        let tmp_root = fs::canonicalize("/tmp").expect("canonical /tmp");

        // Allow a not-yet-existing file under canonical /tmp (ancestor walk).
        assert!(!is_deny(&deny_edit_write_path_decision(
            &tool_path_bytes("file_path", "/tmp/larch-deny-edit-write-test/new.txt"),
            &tmp_root,
            None,
        )));
        // NotebookEdit uses notebook_path.
        assert!(!is_deny(&deny_edit_write_path_decision(
            &tool_path_bytes("notebook_path", "/tmp/larch-deny-edit-write-test/x.ipynb"),
            &tmp_root,
            None,
        )));
        // Empty file_path must fall back to a valid notebook_path.
        let both = json!({"tool_input": {"file_path": "", "notebook_path": "/tmp/x.ipynb"}})
            .to_string()
            .into_bytes();
        assert!(!is_deny(&deny_edit_write_path_decision(
            &both, &tmp_root, None
        )));

        // A repo-tree path denies.
        let repo = TempDir::new().expect("repo");
        let repo_file = repo.path().join("foo.txt");
        assert!(is_deny(&deny_edit_write_path_decision(
            &tool_path_bytes("file_path", repo_file.to_str().expect("repo utf8")),
            &tmp_root,
            None,
        )));
        // Relative, missing, malformed, and /tmp traversal all deny.
        assert!(is_deny(&deny_edit_write_path_decision(
            &tool_path_bytes("file_path", "foo.txt"),
            &tmp_root,
            None,
        )));
        assert!(is_deny(&deny_edit_write_path_decision(
            b"{\"tool_input\":{}}",
            &tmp_root,
            None
        )));
        assert!(is_deny(&deny_edit_write_path_decision(
            b"not json",
            &tmp_root,
            None
        )));
        let deny = deny_edit_write_path_decision(
            &tool_path_bytes("file_path", "/tmp/../etc/passwd"),
            &tmp_root,
            None,
        );
        assert_eq!(deny_reason(&deny), READ_ONLY_REPO_DENY);

        // Two denies are byte-identical.
        let a = deny_edit_write_path_decision(
            &tool_path_bytes("file_path", "foo.txt"),
            &tmp_root,
            None,
        );
        let b = deny_edit_write_path_decision(
            &tool_path_bytes("file_path", "bar.txt"),
            &tmp_root,
            None,
        );
        assert_eq!(deny_reason(&a), deny_reason(&b));
    }

    #[test]
    fn sessions_root_allow_tier() {
        // An isolated stand-in for the /tmp tier so the sessions tier is tested
        // in isolation even when TempDir itself lives under /tmp.
        let tmp_holder = TempDir::new().expect("tmp holder");
        let tmp_root = fs::canonicalize(tmp_holder.path()).expect("canonical tmp holder");

        let holder = TempDir::new().expect("sessions holder");
        let sessions = holder.path().join("larch/sessions");
        fs::create_dir_all(sessions.join("claude-issue-abc")).expect("sessions tree");
        let sessions_root = fs::canonicalize(&sessions).expect("canonical sessions");

        // Allow a new file under the sessions root.
        let allow = tool_path_bytes(
            "file_path",
            sessions
                .join("claude-issue-abc/body.txt")
                .to_str()
                .expect("sessions utf8"),
        );
        assert!(!is_deny(&deny_edit_write_path_decision(
            &allow,
            &tmp_root,
            Some(&sessions_root)
        )));

        // A sibling under the larch cache but outside sessions/ denies.
        fs::create_dir_all(holder.path().join("larch")).expect("larch cache");
        let sibling = holder.path().join("larch/evil.txt");
        assert!(is_deny(&deny_edit_write_path_decision(
            &tool_path_bytes("file_path", sibling.to_str().expect("sibling utf8")),
            &tmp_root,
            Some(&sessions_root),
        )));

        // Traversal escaping the sessions root denies.
        let escape = format!("{}/../evil.txt", sessions.display());
        assert!(is_deny(&deny_edit_write_path_decision(
            &tool_path_bytes("file_path", &escape),
            &tmp_root,
            Some(&sessions_root),
        )));
    }

    #[test]
    fn deny_envelope_matches_jq_shape() {
        assert_eq!(
            deny_envelope(READ_ONLY_REPO_DENY),
            format!(
                "{{\"hookSpecificOutput\":{{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"{READ_ONLY_REPO_DENY}\"}}}}"
            )
        );
        // Interpolated reasons are JSON-escaped.
        assert!(deny_envelope("a \"quote\"").contains("a \\\"quote\\\""));
    }

    // ---- block-submodule-edit (git fixtures) ------------------------------

    #[cfg(unix)]
    fn git(dir: &Path, args: &[&str]) {
        let output = std::process::Command::new("git")
            .arg("-C")
            .arg(dir)
            .args(args)
            .env("GIT_CONFIG_GLOBAL", "/dev/null")
            .env("GIT_CONFIG_SYSTEM", "/dev/null")
            .env("GIT_AUTHOR_NAME", "test")
            .env("GIT_AUTHOR_EMAIL", "test@example.invalid")
            .env("GIT_COMMITTER_NAME", "test")
            .env("GIT_COMMITTER_EMAIL", "test@example.invalid")
            .output()
            .expect("git spawn");
        assert!(
            output.status.success(),
            "git {args:?} failed: {}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    #[cfg(unix)]
    struct SuperFixture {
        _root: TempDir,
        super_dir: std::path::PathBuf,
        sub: std::path::PathBuf,
        nested: std::path::PathBuf,
        nonrepo: std::path::PathBuf,
    }

    #[cfg(unix)]
    fn build_super_fixture() -> SuperFixture {
        let root = TempDir::new().expect("fixture root");
        let bare = root.path().join("bare.git");
        let seed = root.path().join("seed");
        let super_dir = root.path().join("super");
        let nonrepo = root.path().join("nonrepo");
        fs::create_dir_all(&nonrepo).expect("nonrepo");
        let file_url = |path: &std::path::Path| format!("file://{}", path.display());

        git(
            root.path(),
            &["init", "--bare", "-b", "main", bare.to_str().expect("bare")],
        );
        git(
            root.path(),
            &[
                "-c",
                "init.defaultBranch=main",
                "init",
                seed.to_str().expect("seed"),
            ],
        );
        fs::write(seed.join("seed.txt"), "seed\n").expect("seed file");
        git(&seed, &["add", "seed.txt"]);
        git(&seed, &["commit", "-m", "seed"]);
        git(&seed, &["push", &file_url(&bare), "main"]);

        git(
            root.path(),
            &[
                "-c",
                "init.defaultBranch=main",
                "init",
                super_dir.to_str().expect("super"),
            ],
        );
        fs::write(super_dir.join("README.md"), "# super\n").expect("readme");
        git(&super_dir, &["add", "README.md"]);
        git(&super_dir, &["commit", "-m", "initial"]);
        git(
            &super_dir,
            &[
                "-c",
                "protocol.file.allow=always",
                "submodule",
                "add",
                &file_url(&bare),
                "sub",
            ],
        );
        git(&super_dir, &["commit", "-m", "add submodule sub"]);
        let sub = super_dir.join("sub");

        let nested = super_dir.join("nested");
        fs::create_dir_all(&nested).expect("nested");
        git(
            root.path(),
            &[
                "-c",
                "init.defaultBranch=main",
                "init",
                nested.to_str().expect("nested"),
            ],
        );
        fs::write(nested.join("file.txt"), "n\n").expect("nested file");
        git(&nested, &["add", "file.txt"]);
        git(&nested, &["commit", "-m", "nested"]);

        std::os::unix::fs::symlink(super_dir.join("README.md"), super_dir.join("symlink-file"))
            .expect("symlink-file");
        std::os::unix::fs::symlink(sub.join("any.txt"), super_dir.join("outside-link"))
            .expect("outside-link");
        std::os::unix::fs::symlink(super_dir.join("cycle-link"), super_dir.join("cycle-link"))
            .expect("cycle-link");
        std::os::unix::fs::symlink("sub/any.txt", super_dir.join("relative-link"))
            .expect("relative-link");

        SuperFixture {
            _root: root,
            super_dir,
            sub,
            nested,
            nonrepo,
        }
    }

    #[cfg(unix)]
    fn submodule_input(file_path: &Path) -> Vec<u8> {
        json!({"tool_input": {"file_path": file_path.to_str().expect("path utf8")}})
            .to_string()
            .into_bytes()
    }

    #[cfg(unix)]
    fn assert_submodule_deny(decision: &Decision, needle: &str) {
        assert!(
            matches!(decision, Decision::Deny(reason) if reason.contains(needle)),
            "expected deny containing {needle:?}"
        );
    }

    #[cfg(unix)]
    #[test]
    fn block_submodule_allows_and_denies() {
        let fixture = build_super_fixture();
        let super_dir = fixture.super_dir.as_path();
        let sub = fixture.sub.as_path();

        // Superproject file: allow.
        assert!(!is_deny(&submodule_decision(
            &submodule_input(&super_dir.join("README.md")),
            None,
            super_dir,
        )));
        // Submodule file: deny, naming the submodule path.
        assert_submodule_deny(
            &submodule_decision(&submodule_input(&sub.join("any.txt")), None, super_dir),
            "sub",
        );
        // New file under a new subdir inside the submodule (ancestor walk).
        assert_submodule_deny(
            &submodule_decision(
                &submodule_input(&sub.join("does/not/exist/x.txt")),
                None,
                super_dir,
            ),
            "submodule",
        );
        // Nested non-submodule repo: allow.
        assert!(!is_deny(&submodule_decision(
            &submodule_input(&fixture.nested.join("file.txt")),
            None,
            super_dir,
        )));
        // Symlink resolving into the superproject: allow.
        assert!(!is_deny(&submodule_decision(
            &submodule_input(&super_dir.join("symlink-file")),
            None,
            super_dir,
        )));
    }

    #[cfg(unix)]
    #[test]
    fn block_submodule_anchor_symlink_and_fail_closed_cases() {
        let fixture = build_super_fixture();
        let super_dir = fixture.super_dir.as_path();
        let sub = fixture.sub.as_path();

        // cwd inside the submodule but CLAUDE_PROJECT_DIR anchored to super: deny.
        assert_submodule_deny(
            &submodule_decision(
                &submodule_input(&sub.join("any.txt")),
                Some(super_dir.as_os_str()),
                sub,
            ),
            "submodule",
        );
        // A broken CLAUDE_PROJECT_DIR falls back to a healthy $PWD.
        assert_submodule_deny(
            &submodule_decision(
                &submodule_input(&sub.join("any.txt")),
                Some(fixture.nonrepo.as_os_str()),
                super_dir,
            ),
            "submodule",
        );
        // Absolute symlink into the submodule: deny.
        assert_submodule_deny(
            &submodule_decision(
                &submodule_input(&super_dir.join("outside-link")),
                None,
                super_dir,
            ),
            "submodule",
        );
        // Relative symlink into the submodule: deny.
        assert_submodule_deny(
            &submodule_decision(
                &submodule_input(&super_dir.join("relative-link")),
                None,
                super_dir,
            ),
            "submodule",
        );
        // Self-referential symlink cycle: fail-closed via the depth cap.
        assert_submodule_deny(
            &submodule_decision(
                &submodule_input(&super_dir.join("cycle-link")),
                None,
                super_dir,
            ),
            "symlink",
        );
        // Bad JSON: fail-closed.
        assert_submodule_deny(
            &submodule_decision(b"not json", None, super_dir),
            "blocking",
        );
        // Non-absolute file_path: fail-closed.
        assert_submodule_deny(
            &submodule_decision(
                &json!({"tool_input": {"file_path": "relative/path.txt"}})
                    .to_string()
                    .into_bytes(),
                None,
                super_dir,
            ),
            "absolute",
        );
        // cwd outside any repo: allow.
        assert!(!is_deny(&submodule_decision(
            &submodule_input(&fixture.nonrepo.join("x.txt")),
            None,
            fixture.nonrepo.as_path(),
        )));
        // Caller in repo but file_path outside any repo: allow.
        assert!(!is_deny(&submodule_decision(
            &submodule_input(&fixture.nonrepo.join("x.txt")),
            None,
            super_dir,
        )));
    }
}
