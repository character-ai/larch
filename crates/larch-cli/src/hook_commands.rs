//! Advisory hook commands with confined, descriptor-relative local state.

use std::{
    env,
    ffi::OsString,
    io::{self, Read as _, Write as _},
    process::ExitCode,
    time::{SystemTime, UNIX_EPOCH},
};

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
    path::{Path, PathBuf},
    thread,
    time::{Duration, Instant},
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
