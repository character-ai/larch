//! Differential parity tests for filtered session-transcript rendering.
//!
//! The `*-expected.jsonl` fixtures are recorded, byte-exact output of the Python
//! owner (`larch.rendering.render_session_transcript.render`) over the
//! `*.jsonl` inputs beside them. `raw-session.jsonl` carries a `%REPO_ROOT%`
//! token so the recorded pair stays free of any operator path.
//!
//! `hostile.jsonl` is the one deliberate divergence. Python's
//! `json.dumps(..., ensure_ascii=False)` leaves `U+0085`, `U+2028`, and
//! `U+2029` bare, so transcript content carrying them forges document lines for
//! any reader that splits the way Python's `str.splitlines` does. The Rust owner
//! escapes those three. Both halves are asserted here: parity once the escape is
//! undone, and the structural property the escape buys.

use std::{
    fs::{self, File},
    io::Write as _,
    path::Path,
};

use larch_core::{
    MAX_TRANSCRIPT_INPUT_BYTES, MAX_TRANSCRIPT_RECORD_BYTES, TRANSCRIPT_POLICY,
    TRANSCRIPT_SCHEMA_VERSION, TranscriptError, render_session_transcript,
};
use serde_json::Value;
use tempfile::TempDir;

const RAW_SESSION: &str = include_str!("fixtures/session_transcript/raw-session.jsonl");
const RAW_SESSION_EXPECTED: &str =
    include_str!("fixtures/session_transcript/raw-session-expected.jsonl");
const HOSTILE: &str = include_str!("fixtures/session_transcript/hostile.jsonl");
const HOSTILE_EXPECTED: &str = include_str!("fixtures/session_transcript/hostile-expected.jsonl");

/// Stand-in clone root substituted for the fixture's `%REPO_ROOT%` token.
const FIXTURE_REPO_ROOT: &str = "/larch-parity-clone";

fn seed(directory: &TempDir, name: &str, body: &str) -> std::path::PathBuf {
    let path = directory.path().join(name);
    fs::write(&path, body).expect("seed raw session fixture");
    path
}

/// Split the way Python's `str.splitlines` does, which is what forged lines target.
fn python_splitlines(text: &str) -> Vec<&str> {
    let mut lines = Vec::new();
    let mut start = 0;
    let mut index = 0;
    let bytes = text.as_bytes();
    while index < text.len() {
        let Some(character) = text[index..].chars().next() else {
            break;
        };
        let width = character.len_utf8();
        let terminator = matches!(
            character,
            '\n' | '\r'
                | '\u{b}'
                | '\u{c}'
                | '\u{1c}'
                | '\u{1d}'
                | '\u{1e}'
                | '\u{85}'
                | '\u{2028}'
                | '\u{2029}'
        );
        if terminator {
            lines.push(&text[start..index]);
            index += if character == '\r' && bytes.get(index + 1) == Some(&b'\n') {
                2
            } else {
                width
            };
            start = index;
        } else {
            index += width;
        }
    }
    if start < text.len() {
        lines.push(&text[start..]);
    }
    lines
}

/// Assert the document is exactly one header plus the turn count it declares.
fn assert_one_object_per_line(document: &str) -> usize {
    let lines = python_splitlines(document);
    let header: Value = serde_json::from_str(lines[0]).expect("header line parses");
    let turns = header["turns"].as_u64().expect("header declares turns");
    assert_eq!(header["v"].as_u64(), Some(TRANSCRIPT_SCHEMA_VERSION));
    assert_eq!(header["policy"].as_str(), Some(TRANSCRIPT_POLICY));
    assert_eq!(
        lines.len() as u64,
        turns + 1,
        "document carries a line the header does not declare"
    );
    for line in &lines[1..] {
        let record: Value = serde_json::from_str(line).expect("turn line parses");
        assert!(record.get("turn").is_some(), "turn record lacks a turn");
        assert!(record.get("blocks").is_some(), "turn record lacks blocks");
    }
    usize::try_from(turns).expect("turn count fits")
}

#[test]
fn rendered_transcript_matches_the_python_owner_byte_for_byte() {
    let directory = TempDir::new().expect("parity temp directory");
    let body = RAW_SESSION.replace("%REPO_ROOT%", FIXTURE_REPO_ROOT);
    let input = seed(&directory, "raw-session.jsonl", &body);
    let rendered = render_session_transcript(&input, Some(Path::new(FIXTURE_REPO_ROOT)))
        .expect("fixture renders");
    assert_eq!(rendered.text, RAW_SESSION_EXPECTED);
    assert_eq!(rendered.turns, 10);
    assert!(rendered.warnings.is_empty());
    assert_eq!(assert_one_object_per_line(&rendered.text), 10);
}

#[test]
fn hostile_content_cannot_forge_a_document_line() {
    let directory = TempDir::new().expect("hostile temp directory");
    let input = seed(&directory, "hostile.jsonl", HOSTILE);
    let rendered =
        render_session_transcript(&input, Some(Path::new(FIXTURE_REPO_ROOT))).expect("renders");

    // Parity with the recorded Python owner, once the three added escapes are undone.
    let unescaped = rendered
        .text
        .replace("\\u0085", "\u{85}")
        .replace("\\u2028", "\u{2028}")
        .replace("\\u2029", "\u{2029}");
    assert_eq!(unescaped, HOSTILE_EXPECTED);

    // The property the escape buys, and the proof the Python owner lacked it.
    assert_eq!(assert_one_object_per_line(&rendered.text), rendered.turns);
    assert!(
        python_splitlines(HOSTILE_EXPECTED).len() > rendered.turns + 1,
        "recorded Python output was expected to split into forged lines"
    );
}

#[test]
fn missing_input_is_refused_before_any_read() {
    let directory = TempDir::new().expect("missing temp directory");
    let absent = directory.path().join("absent.jsonl");
    assert_eq!(
        render_session_transcript(&absent, None),
        Err(TranscriptError::Missing(absent.clone()))
    );
    assert_eq!(
        render_session_transcript(directory.path(), None),
        Err(TranscriptError::Missing(directory.path().to_path_buf()))
    );
}

#[test]
fn a_file_without_parseable_records_is_refused() {
    let directory = TempDir::new().expect("empty temp directory");
    let input = seed(&directory, "empty.jsonl", "\n{not json\n[1,2]\n\"text\"\n");
    assert_eq!(
        render_session_transcript(&input, None),
        Err(TranscriptError::NoRecords(input.clone()))
    );
}

#[test]
fn an_oversized_file_is_refused_rather_than_rendered_in_part() {
    let directory = TempDir::new().expect("oversized temp directory");
    let input = directory.path().join("huge.jsonl");
    let file = File::create(&input).expect("create sparse oversized input");
    file.set_len(MAX_TRANSCRIPT_INPUT_BYTES + 1)
        .expect("extend sparse oversized input");
    drop(file);
    assert_eq!(
        render_session_transcript(&input, None),
        Err(TranscriptError::Oversized {
            path: input,
            bytes: MAX_TRANSCRIPT_INPUT_BYTES + 1,
        })
    );
}

#[test]
fn an_oversized_record_is_skipped_and_counted() {
    let directory = TempDir::new().expect("record bound temp directory");
    let input = directory.path().join("long-record.jsonl");
    let mut file = File::create(&input).expect("create long-record input");
    file.write_all(br#"{"type":"user","message":{"role":"user","content":"kept"}}"#)
        .expect("write kept record");
    file.write_all(b"\n{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"")
        .expect("write oversized prefix");
    let filler = vec![b'x'; 64 * 1024];
    let mut written = 0usize;
    while written <= MAX_TRANSCRIPT_RECORD_BYTES {
        file.write_all(&filler).expect("write oversized body");
        written += filler.len();
    }
    file.write_all(b"\"}}\n").expect("write oversized suffix");
    drop(file);

    let rendered = render_session_transcript(&input, None).expect("renders around the long record");
    assert_eq!(rendered.turns, 1);
    assert_eq!(rendered.warnings.oversized_records, 1);
    assert_eq!(rendered.warnings.replaced_records, 0);
    assert_eq!(
        rendered.warnings.lines(),
        vec![format!(
            "skipped 1 record(s) over the {MAX_TRANSCRIPT_RECORD_BYTES}-byte record bound"
        )]
    );
    assert!(!rendered.text.contains("xxxx"));
}

#[test]
fn invalid_utf8_is_replaced_and_reported() {
    let directory = TempDir::new().expect("utf8 temp directory");
    let input = directory.path().join("invalid.jsonl");
    let mut body = br#"{"type":"user","message":{"role":"user","content":"bad "#.to_vec();
    body.extend_from_slice(&[0xff, 0xfe]);
    body.extend_from_slice(br#" byte"}}"#);
    body.push(b'\n');
    body.extend_from_slice(br#"{"type":"user","message":{"role":"user","content":"clean"}}"#);
    body.push(b'\n');
    fs::write(&input, &body).expect("write invalid utf-8 input");

    let rendered = render_session_transcript(&input, None).expect("renders replaced records");
    assert_eq!(rendered.turns, 2);
    assert_eq!(rendered.warnings.replaced_records, 1);
    assert!(!rendered.warnings.is_empty());
    assert_eq!(
        rendered.warnings.lines(),
        vec!["replaced invalid UTF-8 bytes in 1 record(s)".to_owned()]
    );
    assert!(rendered.text.contains("bad \u{fffd}\u{fffd} byte"));
}

#[test]
fn carriage_returns_separate_records_the_way_python_did() {
    let directory = TempDir::new().expect("newline temp directory");
    let input = seed(
        &directory,
        "newlines.jsonl",
        "{\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"one\"}}\r\n\
         {\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"two\"}}\r\
         {\"type\":\"user\",\"message\":{\"role\":\"user\",\"content\":\"three\"}}",
    );
    let rendered = render_session_transcript(&input, None).expect("renders every record");
    assert_eq!(rendered.turns, 3);
    assert_eq!(assert_one_object_per_line(&rendered.text), 3);
}

#[test]
fn the_repository_prefix_is_only_stripped_when_a_root_is_known() {
    let directory = TempDir::new().expect("root temp directory");
    let body = format!(
        "{{\"type\":\"assistant\",\"message\":{{\"role\":\"assistant\",\"content\":[\
         {{\"type\":\"tool_use\",\"id\":\"toolu_1\",\"name\":\"Read\",\"input\":\
         {{\"file_path\":\"{FIXTURE_REPO_ROOT}/skills/shared/topology.md\"}}}}]}}}}\n"
    );
    let input = seed(&directory, "root.jsonl", &body);
    let with_root = render_session_transcript(&input, Some(Path::new(FIXTURE_REPO_ROOT)))
        .expect("renders with a root");
    assert!(with_root.text.contains("skills/shared/topology.md"));
    assert_eq!(with_root.turns, 1);
    let without_root = render_session_transcript(&input, None).expect("renders without a root");
    assert_eq!(without_root.turns, 0);
    assert!(!without_root.text.contains("tool_use"));
    assert_eq!(assert_one_object_per_line(&without_root.text), 0);
}
