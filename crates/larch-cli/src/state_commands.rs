use crate::argparse_compat::{
    join_arguments, looks_like_option, resolve_option, split_inline_option, write_stdout,
    write_stdout_line,
};
use larch_adapters::{FileIoErrorKind, read_optional_utf8_lossy, read_session_kv_text};
use larch_core::{
    CrStrip, DuplicatePolicy, EmptyKeyPolicy, KvDocument, ParseOptions, select_kv_bytes,
};
use std::{
    collections::BTreeMap,
    ffi::{OsStr, OsString},
    io::{self, Read as _},
    os::unix::ffi::OsStrExt as _,
    path::{Path, PathBuf},
    process::ExitCode,
};

const KV_USAGE: &str = concat!(
    "usage: cli.py kv get [-h] --key KEY [--file FILE]\n",
    "                     [--match {first,last,last-non-empty}] [--default DEFAULT]\n",
    "                     [--cr-strip {none,suffix,rstrip,strip}]\n",
);
const KV_HELP: &str = concat!(
    "usage: cli.py kv get [-h] --key KEY [--file FILE]\n",
    "                     [--match {first,last,last-non-empty}] [--default DEFAULT]\n",
    "                     [--cr-strip {none,suffix,rstrip,strip}]\n",
    "\n",
    "Extract one value from KEY=value input.\n",
    "\n",
    "options:\n",
    "  -h, --help            show this help message and exit\n",
    "  --key KEY\n",
    "  --file FILE\n",
    "  --match {first,last,last-non-empty}\n",
    "  --default DEFAULT\n",
    "  --cr-strip {none,suffix,rstrip,strip}\n",
);
const READ_KEY_USAGE: &str =
    "usage: session read-key [--file FILE] [--key KEY] [--default DEFAULT]\n";
const READ_KEYS_USAGE: &str = "usage: session read-keys [--file FILE] [--key KEY]\n";

#[derive(Default)]
struct ParsedArguments {
    file: Option<OsString>,
    file_present: bool,
    keys: Vec<OsString>,
    default: Option<OsString>,
    match_policy: Option<OsString>,
    cr_strip: Option<OsString>,
    unknown: Vec<OsString>,
}

#[derive(Clone, Copy, Eq, PartialEq)]
enum ParseMode {
    Kv,
    ReadKey,
    ReadKeys,
}

pub fn kv_get(arguments: &[OsString]) -> ExitCode {
    for argument in arguments.iter().take_while(|argument| *argument != "--") {
        let Some(text) = argument.to_str() else {
            continue;
        };
        let (name, explicit) = split_inline_option(text);
        if name == "-h" || name.starts_with("-h") || (name.len() > 2 && "--help".starts_with(name))
        {
            if let Some(value) = explicit {
                return kv_usage_error(&format!(
                    "argument -h/--help: ignored explicit argument '{value}'"
                ));
            }
            print!("{KV_HELP}");
            return ExitCode::SUCCESS;
        }
    }
    let mut parsed = match parse_arguments(arguments, ParseMode::Kv) {
        Ok(parsed) => parsed,
        Err(error) => return kv_usage_error(&error),
    };
    let policy = match parsed.match_policy.as_deref().and_then(OsStr::to_str) {
        None | Some("first") => DuplicatePolicy::First,
        Some("last") => DuplicatePolicy::Last,
        Some("last-non-empty") => DuplicatePolicy::LastNonEmpty,
        Some(value) => {
            return kv_usage_error(&format!(
                "argument --match: invalid choice: '{value}' (choose from 'first', 'last', 'last-non-empty')"
            ));
        }
    };
    let Some(key) = parsed.keys.pop() else {
        return kv_usage_error("the following arguments are required: --key");
    };
    let cr_strip = match parsed.cr_strip.as_deref().and_then(OsStr::to_str) {
        None | Some("none") => CrStrip::None,
        Some("suffix") => CrStrip::Suffix,
        Some("rstrip") => CrStrip::End,
        Some("strip") => CrStrip::Both,
        Some(value) => {
            return kv_usage_error(&format!(
                "argument --cr-strip: invalid choice: '{value}' (choose from 'none', 'suffix', 'rstrip', 'strip')"
            ));
        }
    };
    if !parsed.unknown.is_empty() {
        return kv_usage_error(&format!(
            "unrecognized arguments: {}",
            join_arguments(&parsed.unknown)
        ));
    }
    let default = parsed.default.unwrap_or_default();
    let input = if let Some(file) = parsed.file {
        match read_optional_utf8_lossy(Path::new(&file)) {
            Ok(Some(text)) => text.into_bytes(),
            Ok(None) => Vec::new(),
            Err(error) => {
                eprintln!("{error}");
                return ExitCode::FAILURE;
            }
        }
    } else {
        let mut bytes = Vec::new();
        if let Err(error) = io::stdin().read_to_end(&mut bytes) {
            eprintln!("{error}");
            return ExitCode::FAILURE;
        }
        bytes
    };
    let value = select_kv_bytes(
        &input,
        key.as_os_str().as_bytes(),
        default.as_os_str().as_bytes(),
        policy,
        cr_strip,
    );
    write_stdout_line(&value)
}

pub fn read_key(arguments: &[OsString]) -> ExitCode {
    let mut parsed = match parse_arguments(arguments, ParseMode::ReadKey) {
        Ok(parsed) => parsed,
        Err(error) => return session_usage_error(READ_KEY_USAGE, "session read-key", &error),
    };
    if !parsed.unknown.is_empty() {
        return session_usage_error(
            READ_KEY_USAGE,
            "session read-key",
            &format!(
                "unrecognized arguments: {}",
                join_arguments(&parsed.unknown)
            ),
        );
    }
    let key = parsed.keys.pop().unwrap_or_default();
    if key.is_empty() {
        eprintln!("read-session-env-key.sh: --key is required");
        return ExitCode::FAILURE;
    }
    let Some(file) = parsed.file.filter(|value| !value.is_empty()) else {
        if parsed.file_present
            && let Some(default) = parsed.default
        {
            return write_stdout_line(default.as_os_str().as_bytes());
        }
        eprintln!("read-session-env-key.sh: --file is required");
        return ExitCode::FAILURE;
    };
    let path = PathBuf::from(&file);
    let text = match read_session_kv_text(&path) {
        Ok(Some(text)) => text,
        Err(error) if error.kind() == FileIoErrorKind::InvalidWireFormat => {
            eprintln!(
                "session env file contains carriage return: {}",
                path.display()
            );
            return ExitCode::FAILURE;
        }
        Ok(None) | Err(_) if parsed.default.is_some() => {
            return write_stdout_line(parsed.default.as_deref().unwrap_or_default().as_bytes());
        }
        Ok(None) | Err(_) => {
            eprintln!("read-session-env-key.sh: cannot read {}", path.display());
            return ExitCode::FAILURE;
        }
    };
    let prefix = format!("{}=", key.to_string_lossy());
    let value = python_splitlines(&text)
        .find_map(|line| line.strip_prefix(&prefix))
        .filter(|value| !value.is_empty())
        .map_or_else(
            || {
                parsed
                    .default
                    .as_deref()
                    .map_or_else(Vec::new, |value| value.as_bytes().to_vec())
            },
            |value| value.as_bytes().to_vec(),
        );
    write_stdout_line(&value)
}

pub fn read_keys(arguments: &[OsString]) -> ExitCode {
    let parsed = match parse_arguments(arguments, ParseMode::ReadKeys) {
        Ok(parsed) => parsed,
        Err(error) => return session_usage_error(READ_KEYS_USAGE, "session read-keys", &error),
    };
    if !parsed.unknown.is_empty() {
        return session_usage_error(
            READ_KEYS_USAGE,
            "session read-keys",
            &format!(
                "unrecognized arguments: {}",
                join_arguments(&parsed.unknown)
            ),
        );
    }
    if parsed.keys.is_empty() {
        eprintln!("read-session-env-keys.sh: at least one --key is required");
        return ExitCode::FAILURE;
    }
    if !parsed.file_present {
        eprintln!("read-session-env-keys.sh: --file is required");
        return ExitCode::FAILURE;
    }
    let specs = parsed
        .keys
        .iter()
        .map(|raw| parse_key_spec(&raw.to_string_lossy()))
        .collect::<Vec<_>>();
    if specs.iter().any(|(name, _default)| name.is_empty()) {
        eprintln!("read-session-env-keys.sh: empty --key name");
        return ExitCode::FAILURE;
    }
    let mut found = BTreeMap::default();
    if let Some(file) = parsed.file.filter(|value| !value.is_empty()) {
        let path = PathBuf::from(file);
        match read_session_kv_text(&path) {
            Ok(Some(text)) => {
                let mut options = ParseOptions::legacy();
                options.empty_keys = EmptyKeyPolicy::Skip;
                found = KvDocument::parse(&text, options)
                    .expect("legacy parser is non-rejecting")
                    .select(DuplicatePolicy::First);
            }
            Err(error) if error.kind() == FileIoErrorKind::InvalidWireFormat => {
                eprintln!(
                    "session env file contains carriage return: {}",
                    path.display()
                );
                return ExitCode::FAILURE;
            }
            Ok(None) | Err(_) => {}
        }
    }
    let mut output = String::new();
    for (name, default) in specs {
        let value = found
            .get(&name)
            .filter(|value| !value.is_empty())
            .map_or_else(|| default.as_deref().unwrap_or(""), String::as_str);
        output.push_str(&name);
        output.push('=');
        output.push_str(value);
        output.push('\n');
    }
    write_stdout(&output)
}

fn parse_arguments(arguments: &[OsString], mode: ParseMode) -> Result<ParsedArguments, String> {
    let mut parsed = ParsedArguments::default();
    let mut index = 0;
    while index < arguments.len() {
        let argument = &arguments[index];
        let text = argument.to_string_lossy();
        if text == "--" {
            parsed.unknown.extend_from_slice(&arguments[index..]);
            break;
        }
        let (name, inline) = split_inline_option(&text);
        let option = scalar_option(name, mode == ParseMode::Kv)
            .filter(|option| mode != ParseMode::ReadKeys || matches!(*option, "--file" | "--key"));
        let Some(option) = option else {
            parsed.unknown.push(argument.clone());
            index += 1;
            continue;
        };
        parsed.file_present |= option == "--file" && argument.as_os_str() == OsStr::new("--file");
        let value = if let Some(value) = inline {
            validate_choice(option, value)?;
            OsString::from(value)
        } else {
            index += 1;
            let Some(value) = arguments.get(index) else {
                return Err(format!("argument {option}: expected one argument"));
            };
            if looks_like_option(value) {
                return Err(format!("argument {option}: expected one argument"));
            }
            validate_choice(option, &value.to_string_lossy())?;
            value.clone()
        };
        match option {
            "--file" => parsed.file = Some(value),
            "--key" if mode == ParseMode::ReadKeys => parsed.keys.push(value),
            "--key" => {
                parsed.keys.clear();
                parsed.keys.push(value);
            }
            "--default" => parsed.default = Some(value),
            "--match" => parsed.match_policy = Some(value),
            "--cr-strip" => parsed.cr_strip = Some(value),
            _ => unreachable!("option names come from scalar_option"),
        }
        index += 1;
    }
    Ok(parsed)
}

fn scalar_option(name: &str, kv_options: bool) -> Option<&'static str> {
    let options: Vec<&'static str> = ["--file", "--key", "--default", "--match", "--cr-strip"]
        .into_iter()
        .filter(|option| kv_options || !matches!(*option, "--match" | "--cr-strip"))
        .collect();
    resolve_option(name, &options)
}

fn validate_choice(option: &str, value: &str) -> Result<(), String> {
    let choices: &[&str] = match option {
        "--match" => &["first", "last", "last-non-empty"],
        "--cr-strip" => &["none", "suffix", "rstrip", "strip"],
        _ => return Ok(()),
    };
    if choices.contains(&value) {
        Ok(())
    } else {
        let rendered = choices
            .iter()
            .map(|choice| format!("'{choice}'"))
            .collect::<Vec<_>>()
            .join(", ");
        Err(format!(
            "argument {option}: invalid choice: '{value}' (choose from {rendered})"
        ))
    }
}

fn python_splitlines(text: &str) -> impl Iterator<Item = &str> {
    text.split(|character| {
        matches!(
            character,
            '\n' | '\u{b}' | '\u{c}' | '\u{1c}'..='\u{1e}' | '\u{85}' | '\u{2028}' | '\u{2029}'
        )
    })
}

fn parse_key_spec(raw: &str) -> (String, Option<String>) {
    let document =
        KvDocument::parse(raw, ParseOptions::legacy()).expect("legacy parser is non-rejecting");
    document.rows().first().map_or_else(
        || (raw.to_owned(), None),
        |row| (row.key().to_owned(), Some(row.value().to_owned())),
    )
}

fn kv_usage_error(error: &str) -> ExitCode {
    eprintln!("{KV_USAGE}cli.py kv get: error: {error}");
    ExitCode::from(2)
}

fn session_usage_error(usage: &str, program: &str, error: &str) -> ExitCode {
    eprintln!("{usage}{program}: error: {error}");
    ExitCode::FAILURE
}
