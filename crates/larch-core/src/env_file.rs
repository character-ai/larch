//! Exact `KEY=value` parsing, selection, validation, and rendering.

use std::{
    collections::{BTreeMap, BTreeSet},
    error::Error,
    fmt,
};

/// How a scalar selection resolves duplicate keys.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DuplicatePolicy {
    /// Keep the first value.
    First,
    /// Keep the last value, including an empty value.
    Last,
    /// Keep the last non-empty value.
    LastNonEmpty,
}

/// How carriage returns inside a value are normalized.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CrStrip {
    /// Preserve carriage returns that are not CRLF framing.
    None,
    /// Remove one carriage return from the end.
    Suffix,
    /// Remove every carriage return from the end.
    End,
    /// Remove carriage returns from both ends.
    Both,
}

/// How a parser treats a non-empty line without `=`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MalformedLinePolicy {
    /// Ignore the line for compatibility with legacy machine-output readers.
    Skip,
    /// Reject the complete document.
    Reject,
}

/// How empty keys are handled while reading.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EmptyKeyPolicy {
    /// Preserve an empty key for legacy compatibility.
    Keep,
    /// Ignore rows with an empty key.
    Skip,
}

/// How comment-looking lines are handled while reading.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CommentPolicy {
    /// Treat a line beginning with `#` as an ordinary record.
    Keep,
    /// Ignore a line beginning with `#`.
    Skip,
}

/// How surrounding whitespace is handled.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum WhitespacePolicy {
    /// Preserve whitespace exactly.
    Preserve,
    /// Remove surrounding Unicode whitespace.
    Trim,
}

/// Whether duplicate input records are accepted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DuplicateInputPolicy {
    /// Preserve duplicate rows for later selection.
    Allow,
    /// Reject the complete document on the first duplicate.
    Reject,
}

/// Accepted key grammar.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum KeyPolicy {
    /// Stable larch wire keys: ASCII letters, digits, dot, underscore, and dash.
    Wire,
    /// Shell environment keys: uppercase ASCII letters, digits, and underscore.
    Environment,
}

/// Explicit parsing policy for a `KEY=value` document.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ParseOptions {
    /// Handling for non-empty records without `=`.
    pub malformed_lines: MalformedLinePolicy,
    /// Key grammar, or `None` for legacy read compatibility.
    pub key_policy: Option<KeyPolicy>,
    /// Whether an empty key is ignored instead of retained.
    pub empty_keys: EmptyKeyPolicy,
    /// Whether lines beginning with `#` are ignored.
    pub comments: CommentPolicy,
    /// Whether surrounding key whitespace is removed.
    pub key_whitespace: WhitespacePolicy,
    /// Whether surrounding value whitespace is removed.
    pub value_whitespace: WhitespacePolicy,
    /// Carriage-return normalization after CRLF framing is removed.
    pub cr_strip: CrStrip,
    /// Whether a repeated key rejects the complete document.
    pub duplicates: DuplicateInputPolicy,
}

impl ParseOptions {
    /// Match the broad live Python reader grammar.
    #[must_use]
    pub const fn legacy() -> Self {
        Self {
            malformed_lines: MalformedLinePolicy::Skip,
            key_policy: None,
            empty_keys: EmptyKeyPolicy::Keep,
            comments: CommentPolicy::Keep,
            key_whitespace: WhitespacePolicy::Preserve,
            value_whitespace: WhitespacePolicy::Preserve,
            cr_strip: CrStrip::None,
            duplicates: DuplicateInputPolicy::Allow,
        }
    }

    /// Strict grammar for state-bearing environment files.
    #[must_use]
    pub const fn environment() -> Self {
        Self {
            malformed_lines: MalformedLinePolicy::Reject,
            key_policy: Some(KeyPolicy::Environment),
            empty_keys: EmptyKeyPolicy::Keep,
            comments: CommentPolicy::Skip,
            key_whitespace: WhitespacePolicy::Preserve,
            value_whitespace: WhitespacePolicy::Preserve,
            cr_strip: CrStrip::None,
            duplicates: DuplicateInputPolicy::Reject,
        }
    }
}

/// Rendering policy for exact `KEY=value\n` bytes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RenderOptions {
    /// Key grammar enforced before any bytes are returned.
    pub key_policy: KeyPolicy,
    /// Whether rows are sorted by key while preserving equal-key order.
    pub sort_keys: bool,
}

impl RenderOptions {
    /// Render stable larch wire keys in caller order.
    #[must_use]
    pub const fn wire() -> Self {
        Self {
            key_policy: KeyPolicy::Wire,
            sort_keys: false,
        }
    }

    /// Render deterministic environment-file bytes.
    #[must_use]
    pub const fn environment() -> Self {
        Self {
            key_policy: KeyPolicy::Environment,
            sort_keys: true,
        }
    }
}

/// One decoded row. Values may contain `=` and lone carriage returns.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct KvRow {
    key: String,
    value: String,
}

impl KvRow {
    /// Construct a row that is safe to render under `key_policy`.
    ///
    /// # Errors
    ///
    /// Returns [`KvError`] for an unsafe key or a line-forging value.
    pub fn new(
        key: impl Into<String>,
        value: impl Into<String>,
        key_policy: KeyPolicy,
    ) -> Result<Self, KvError> {
        let row = Self {
            key: key.into(),
            value: value.into(),
        };
        validate_row(&row, key_policy, 0)?;
        Ok(row)
    }

    /// Return the decoded key.
    #[must_use]
    pub fn key(&self) -> &str {
        &self.key
    }

    /// Return the decoded value.
    #[must_use]
    pub fn value(&self) -> &str {
        &self.value
    }
}

/// An ordered, duplicate-preserving `KEY=value` document.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct KvDocument {
    rows: Vec<KvRow>,
}

impl KvDocument {
    /// Decode LF or CRLF records according to an explicit policy.
    ///
    /// A lone carriage return is value data and never creates a record.
    ///
    /// # Errors
    ///
    /// Returns [`KvError`] when the selected policy rejects a record.
    pub fn parse(text: &str, options: ParseOptions) -> Result<Self, KvError> {
        let mut rows = Vec::new();
        let mut seen = BTreeSet::new();
        let line_count = text.split('\n').count();
        for (index, raw_line) in text.split('\n').enumerate() {
            let line_number = index + 1;
            let raw = if index + 1 < line_count {
                raw_line.strip_suffix('\r').unwrap_or(raw_line)
            } else {
                raw_line
            };
            if raw.is_empty() || (options.comments == CommentPolicy::Skip && raw.starts_with('#')) {
                continue;
            }
            let Some((raw_key, raw_value)) = raw.split_once('=') else {
                if options.malformed_lines == MalformedLinePolicy::Reject {
                    return Err(KvError::new(KvErrorKind::MalformedRecord, line_number));
                }
                continue;
            };
            let key = if options.key_whitespace == WhitespacePolicy::Trim {
                raw_key.trim()
            } else {
                raw_key
            };
            if options.empty_keys == EmptyKeyPolicy::Skip && key.is_empty() {
                continue;
            }
            if let Some(policy) = options.key_policy {
                validate_key(key, policy, line_number)?;
            }
            if options.duplicates == DuplicateInputPolicy::Reject && !seen.insert(key.to_owned()) {
                return Err(KvError::new(KvErrorKind::DuplicateKey, line_number));
            }
            let value = strip_cr(raw_value, options.cr_strip);
            let value = if options.value_whitespace == WhitespacePolicy::Trim {
                value.trim()
            } else {
                value
            };
            rows.push(KvRow {
                key: key.to_owned(),
                value: value.to_owned(),
            });
        }
        Ok(Self { rows })
    }

    /// Construct a document from already validated rows.
    #[must_use]
    pub const fn from_rows(rows: Vec<KvRow>) -> Self {
        Self { rows }
    }

    /// Return rows in source order, including duplicates.
    #[must_use]
    pub fn rows(&self) -> &[KvRow] {
        &self.rows
    }

    /// Select one value per key with deterministic duplicate handling.
    #[must_use]
    pub fn select(&self, policy: DuplicatePolicy) -> BTreeMap<String, String> {
        let mut selected = BTreeMap::new();
        for row in &self.rows {
            match policy {
                DuplicatePolicy::First => {
                    let _ = selected
                        .entry(row.key.clone())
                        .or_insert_with(|| row.value.clone());
                }
                DuplicatePolicy::Last => {
                    let _ = selected.insert(row.key.clone(), row.value.clone());
                }
                DuplicatePolicy::LastNonEmpty if !row.value.is_empty() => {
                    let _ = selected.insert(row.key.clone(), row.value.clone());
                }
                DuplicatePolicy::LastNonEmpty => {}
            }
        }
        selected
    }

    /// Select every value per key in source order.
    #[must_use]
    pub fn select_all(&self) -> BTreeMap<String, Vec<String>> {
        let mut selected: BTreeMap<String, Vec<String>> = BTreeMap::new();
        for row in &self.rows {
            selected
                .entry(row.key.clone())
                .or_default()
                .push(row.value.clone());
        }
        selected
    }

    /// Render exact UTF-8 `KEY=value\n` bytes after validating every row.
    ///
    /// # Errors
    ///
    /// Returns [`KvError`] before rendering if any row can forge a line.
    pub fn render(&self, options: RenderOptions) -> Result<String, KvError> {
        for (index, row) in self.rows.iter().enumerate() {
            validate_row(row, options.key_policy, index + 1)?;
        }
        let mut rows: Vec<&KvRow> = self.rows.iter().collect();
        if options.sort_keys {
            rows.sort_by(|left, right| left.key.cmp(&right.key));
        }
        let mut rendered = String::new();
        for row in rows {
            rendered.push_str(&row.key);
            rendered.push('=');
            rendered.push_str(&row.value);
            rendered.push('\n');
        }
        Ok(rendered)
    }
}

/// Select one exact byte value from legacy `KEY=value` input.
///
/// Unlike [`KvDocument`], this helper does not require UTF-8. It preserves the
/// legacy stdin contract while still treating one carriage return before LF as
/// record framing.
#[must_use]
pub fn select_kv_bytes(
    text: &[u8],
    key: &[u8],
    default: &[u8],
    duplicate_policy: DuplicatePolicy,
    cr_strip: CrStrip,
) -> Vec<u8> {
    let mut selected = None;
    let mut lines = text.split(|byte| *byte == b'\n').peekable();
    while let Some(raw_line) = lines.next() {
        let line = if lines.peek().is_some() {
            raw_line.strip_suffix(b"\r").unwrap_or(raw_line)
        } else {
            raw_line
        };
        let Some(value) = line
            .strip_prefix(key)
            .and_then(|remaining| remaining.strip_prefix(b"="))
        else {
            continue;
        };
        let value = strip_cr_bytes(value, cr_strip);
        match duplicate_policy {
            DuplicatePolicy::First => return value.to_vec(),
            DuplicatePolicy::Last => selected = Some(value),
            DuplicatePolicy::LastNonEmpty if !value.is_empty() => selected = Some(value),
            DuplicatePolicy::LastNonEmpty => {}
        }
    }
    selected.unwrap_or(default).to_vec()
}

/// Return the first matching value from caller-ordered `KEY=value` rows.
#[must_use]
pub fn kv_row_value<'a>(rows: &'a [(String, String)], key: &str) -> Option<&'a str> {
    rows.iter()
        .find(|(candidate, _)| candidate == key)
        .map(|(_, value)| value.as_str())
}

/// Render caller-ordered `KEY=value\n` rows after rejecting line forgery.
///
/// # Errors
///
/// Returns [`KvError`] when a key or value cannot safely occupy one row.
pub fn kv_text(rows: &[(&str, &str)]) -> Result<String, KvError> {
    let rows = rows
        .iter()
        .map(|(key, value)| KvRow::new(*key, *value, KeyPolicy::Wire))
        .collect::<Result<Vec<_>, _>>()?;
    KvDocument::from_rows(rows).render(RenderOptions::wire())
}

/// Parse exactly one CR-free `KEY=value` row with an explicit codec policy.
///
/// A caller that reads one terminal line must not quietly accept a second row
/// or CR framing as value data. The returned row retains the parser's key and
/// value semantics for `options`.
#[must_use]
pub fn parse_single_kv_row(text: &str, options: ParseOptions) -> Option<KvRow> {
    if text.contains(['\n', '\r']) {
        return None;
    }
    let document = KvDocument::parse(text, options).ok()?;
    let [row] = document.rows() else {
        return None;
    };
    Some(row.clone())
}

/// Parse one allowlisted `KEY=value` or `export KEY=value` shell assignment.
///
/// The right-hand side must decode to at most one POSIX shell token. Comments
/// are disabled, matching Python's `shlex.split(..., comments=False)` behavior.
#[must_use]
pub fn parse_allowlisted_env_line(
    raw: &str,
    allowed_keys: &[&str],
    key_policy: Option<KeyPolicy>,
    reject_newline_rhs: bool,
) -> Option<(String, String)> {
    let mut line = raw.trim();
    if line.is_empty() || line.starts_with('#') {
        return None;
    }
    line = line.strip_prefix("export ").unwrap_or(line);
    let (raw_key, rhs) = line.split_once('=')?;
    let key = raw_key.trim();
    if !allowed_keys.contains(&key)
        || key_policy.is_some_and(|policy| validate_key(key, policy, 0).is_err())
        || (reject_newline_rhs && rhs.contains(['\n', '\r']))
    {
        return None;
    }
    let value = split_one_shell_token(rhs)?;
    if value.contains(['\n', '\r']) {
        return None;
    }
    Some((key.to_owned(), value))
}

/// A strict, deterministic environment file ready for guarded updates.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EnvFile {
    values: BTreeMap<String, String>,
}

impl EnvFile {
    /// Return an empty environment file.
    #[must_use]
    pub const fn empty() -> Self {
        Self {
            values: BTreeMap::new(),
        }
    }

    /// Parse a strict environment file, rejecting malformed and duplicate rows.
    ///
    /// # Errors
    ///
    /// Returns [`KvError`] for unsafe keys, duplicates, malformed rows, or CRs.
    pub fn parse(text: &str) -> Result<Self, KvError> {
        if text.contains('\r') {
            return Err(KvError::new(KvErrorKind::UnsafeValue, 0));
        }
        let document = KvDocument::parse(text, ParseOptions::environment())?;
        Ok(Self {
            values: document.select(DuplicatePolicy::Last),
        })
    }

    /// Return the validated values.
    #[must_use]
    pub const fn values(&self) -> &BTreeMap<String, String> {
        &self.values
    }

    /// Apply an allowlisted update as one transaction in memory.
    ///
    /// # Errors
    ///
    /// Returns [`KvError`] without changing this value if any update is unsafe,
    /// repeated, or outside `allowed_keys`.
    pub fn apply_guarded(
        &mut self,
        updates: &[(&str, &str)],
        allowed_keys: &[&str],
    ) -> Result<(), KvError> {
        let mut next = self.values.clone();
        let mut seen = BTreeSet::new();
        for (key, value) in updates {
            validate_key(key, KeyPolicy::Environment, 0)?;
            if !allowed_keys.contains(key) {
                return Err(KvError::new(KvErrorKind::KeyNotAllowed, 0));
            }
            if !seen.insert(*key) {
                return Err(KvError::new(KvErrorKind::DuplicateKey, 0));
            }
            if value.contains(['\n', '\r']) {
                return Err(KvError::new(KvErrorKind::UnsafeValue, 0));
            }
            let _ = next.insert((*key).to_owned(), (*value).to_owned());
        }
        self.values = next;
        Ok(())
    }

    /// Render sorted, newline-terminated environment-file bytes.
    ///
    /// # Errors
    ///
    /// Returns [`KvError`] if internal data cannot be represented safely.
    pub fn render(&self) -> Result<String, KvError> {
        let rows = self
            .values
            .iter()
            .map(|(key, value)| KvRow {
                key: key.clone(),
                value: value.clone(),
            })
            .collect();
        KvDocument::from_rows(rows).render(RenderOptions::environment())
    }
}

/// Stable failure classes for wire parsing and rendering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum KvErrorKind {
    /// A non-empty record lacked `=`.
    MalformedRecord,
    /// A key did not match the selected grammar.
    InvalidKey,
    /// A key was valid but outside the update allowlist.
    KeyNotAllowed,
    /// A value could forge an additional line.
    UnsafeValue,
    /// A strict document or update repeated a key.
    DuplicateKey,
}

/// A typed wire-format failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct KvError {
    kind: KvErrorKind,
    line: usize,
}

impl KvError {
    const fn new(kind: KvErrorKind, line: usize) -> Self {
        Self { kind, line }
    }

    /// Return the stable failure class.
    #[must_use]
    pub const fn kind(&self) -> KvErrorKind {
        self.kind
    }

    /// Return the one-based input line, or zero for an in-memory update.
    #[must_use]
    pub const fn line(&self) -> usize {
        self.line
    }
}

impl fmt::Display for KvError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        let message = match self.kind {
            KvErrorKind::MalformedRecord => "malformed KEY=value record",
            KvErrorKind::InvalidKey => "unsafe KEY=value key",
            KvErrorKind::KeyNotAllowed => "environment key is not allowlisted",
            KvErrorKind::UnsafeValue => "KEY=value value contains a line break",
            KvErrorKind::DuplicateKey => "duplicate KEY=value key",
        };
        if self.line == 0 {
            formatter.write_str(message)
        } else {
            write!(formatter, "{message} at line {}", self.line)
        }
    }
}

impl Error for KvError {}

fn strip_cr(value: &str, policy: CrStrip) -> &str {
    match policy {
        CrStrip::None => value,
        CrStrip::Suffix => value.strip_suffix('\r').unwrap_or(value),
        CrStrip::End => value.trim_end_matches('\r'),
        CrStrip::Both => value.trim_matches('\r'),
    }
}

fn strip_cr_bytes(value: &[u8], policy: CrStrip) -> &[u8] {
    match policy {
        CrStrip::None => value,
        CrStrip::Suffix => value.strip_suffix(b"\r").unwrap_or(value),
        CrStrip::End => {
            &value[..value
                .iter()
                .rposition(|byte| *byte != b'\r')
                .map_or(0, |index| index + 1)]
        }
        CrStrip::Both => {
            let start = value
                .iter()
                .position(|byte| *byte != b'\r')
                .unwrap_or(value.len());
            let end = value
                .iter()
                .rposition(|byte| *byte != b'\r')
                .map_or(start, |index| index + 1);
            &value[start..end]
        }
    }
}

/// Decode a right-hand side that is exactly one POSIX shell token.
///
/// Returns `None` when the input decodes to zero or more than one token, which
/// is the boundary `shlex.split(value)` length check draws in the Python owner.
#[must_use]
pub fn split_one_shell_token(input: &str) -> Option<String> {
    #[derive(Clone, Copy, Eq, PartialEq)]
    enum Quote {
        None,
        Single,
        Double,
    }

    let mut quote = Quote::None;
    let mut escaped = false;
    let mut token_started = false;
    let mut complete_token = false;
    let mut value = String::new();
    for character in input.chars() {
        if escaped {
            if character == '\n' {
                return None;
            }
            if quote == Quote::Double && !matches!(character, '$' | '`' | '"' | '\\') {
                value.push('\\');
            }
            value.push(character);
            escaped = false;
            token_started = true;
            continue;
        }
        match quote {
            Quote::Single if character == '\'' => quote = Quote::None,
            Quote::Double if character == '"' => quote = Quote::None,
            Quote::Double if character == '\\' => escaped = true,
            Quote::Single | Quote::Double => value.push(character),
            Quote::None if character == '\'' => {
                if complete_token {
                    return None;
                }
                token_started = true;
                quote = Quote::Single;
            }
            Quote::None if character == '"' => {
                if complete_token {
                    return None;
                }
                token_started = true;
                quote = Quote::Double;
            }
            Quote::None if character == '\\' => {
                if complete_token {
                    return None;
                }
                escaped = true;
                token_started = true;
            }
            Quote::None if matches!(character, ' ' | '\t' | '\r' | '\n') => {
                if token_started {
                    complete_token = true;
                }
            }
            Quote::None => {
                if complete_token {
                    return None;
                }
                token_started = true;
                value.push(character);
            }
        }
    }
    if escaped || quote != Quote::None {
        None
    } else {
        Some(value)
    }
}

fn validate_row(row: &KvRow, policy: KeyPolicy, line: usize) -> Result<(), KvError> {
    validate_key(&row.key, policy, line)?;
    if row.value.contains(['\n', '\r']) {
        return Err(KvError::new(KvErrorKind::UnsafeValue, line));
    }
    Ok(())
}

fn validate_key(key: &str, policy: KeyPolicy, line: usize) -> Result<(), KvError> {
    let valid = match policy {
        KeyPolicy::Wire => {
            !key.is_empty()
                && key
                    .bytes()
                    .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
        }
        KeyPolicy::Environment => {
            let mut bytes = key.bytes();
            bytes
                .next()
                .is_some_and(|byte| byte == b'_' || byte.is_ascii_uppercase())
                && bytes
                    .all(|byte| byte == b'_' || byte.is_ascii_uppercase() || byte.is_ascii_digit())
        }
    };
    if valid {
        Ok(())
    } else {
        Err(KvError::new(KvErrorKind::InvalidKey, line))
    }
}

#[cfg(test)]
mod tests {
    use super::{
        CommentPolicy, CrStrip, DuplicatePolicy, EmptyKeyPolicy, EnvFile, KeyPolicy, KvDocument,
        KvErrorKind, KvRow, MalformedLinePolicy, ParseOptions, RenderOptions, kv_row_value,
        kv_text, parse_allowlisted_env_line, parse_single_kv_row, select_kv_bytes,
    };

    #[test]
    fn legacy_parser_preserves_live_duplicate_crlf_and_equals_contracts() {
        let input = include_str!("../../../fixtures/rust-io/kv-input.env");
        let parsed =
            KvDocument::parse(input, ParseOptions::legacy()).expect("fixture should parse");

        assert_eq!(parsed.select(DuplicatePolicy::First)["KEEP"], "one=two");
        assert_eq!(parsed.select(DuplicatePolicy::Last)["KEEP"], "last");
        assert_eq!(
            parsed.select(DuplicatePolicy::LastNonEmpty)["EMPTY"],
            "before"
        );
        assert_eq!(parsed.select_all()["KEEP"], ["one=two", "last"]);
        assert_eq!(parsed.select(DuplicatePolicy::Last)["LONE"], "one\rTWO=two");
        assert_eq!(
            KvDocument::parse("A=one\r\nB=two\r\n", ParseOptions::legacy())
                .expect("CRLF input should parse")
                .select(DuplicatePolicy::Last),
            [
                ("A".to_owned(), "one".to_owned()),
                ("B".to_owned(), "two".to_owned())
            ]
            .into_iter()
            .collect()
        );
    }

    #[test]
    fn parser_policies_cover_cr_empty_comment_and_malformed_records() {
        let mut options = ParseOptions::legacy();
        options.cr_strip = CrStrip::Both;
        options.empty_keys = EmptyKeyPolicy::Skip;
        options.comments = CommentPolicy::Skip;
        options.malformed_lines = MalformedLinePolicy::Reject;

        let error = KvDocument::parse("# note\n=value\nA=\rvalue\r\nmalformed\n", options)
            .expect_err("strict malformed policy should reject");
        assert_eq!(error.kind(), KvErrorKind::MalformedRecord);
        assert_eq!(error.line(), 4);

        options.malformed_lines = MalformedLinePolicy::Skip;
        let parsed = KvDocument::parse("# note\n=value\nA=\rvalue\r\n", options)
            .expect("lenient malformed policy should parse");
        assert_eq!(parsed.select(DuplicatePolicy::Last)["A"], "value");
    }

    #[test]
    fn single_row_parser_preserves_policy_and_rejects_line_forgery() {
        let row = parse_single_kv_row("KEY=value=with-equals", ParseOptions::environment())
            .expect("one environment row should parse");
        assert_eq!(row.key(), "KEY");
        assert_eq!(row.value(), "value=with-equals");
        assert!(
            parse_single_kv_row("KEY=value\nOTHER=forged", ParseOptions::environment()).is_none()
        );
        assert!(parse_single_kv_row("KEY=value\r", ParseOptions::environment()).is_none());
        assert!(parse_single_kv_row("lower=value", ParseOptions::environment()).is_none());
        assert_eq!(
            parse_single_kv_row("lower=value", ParseOptions::legacy())
                .expect("legacy policy retains its key grammar")
                .key(),
            "lower"
        );
    }

    #[test]
    fn golden_renderer_pins_exact_bytes_and_rejects_line_forgery() {
        let rows = vec![
            KvRow::new("B", "two=2", KeyPolicy::Wire).expect("valid row"),
            KvRow::new("A", "one", KeyPolicy::Wire).expect("valid row"),
        ];
        let rendered = KvDocument::from_rows(rows)
            .render(RenderOptions {
                key_policy: KeyPolicy::Wire,
                sort_keys: true,
            })
            .expect("valid rows should render");

        assert_eq!(
            rendered.as_bytes(),
            include_bytes!("../../../fixtures/rust-io/kv-render.golden")
        );
        assert_eq!(
            KvRow::new("BAD=KEY", "value", KeyPolicy::Wire)
                .expect_err("separator in key should fail")
                .kind(),
            KvErrorKind::InvalidKey
        );
        assert_eq!(
            KvRow::new("GOOD", "value\nFORGED=yes", KeyPolicy::Wire)
                .expect_err("newline should fail")
                .kind(),
            KvErrorKind::UnsafeValue
        );
    }

    #[test]
    fn environment_updates_are_transactional_allowlisted_and_deterministic() {
        let mut env = EnvFile::parse("B=old\nA=keep\n").expect("fixture should parse");
        env.apply_guarded(&[("B", "new"), ("C", "three")], &["B", "C"])
            .expect("allowlisted update should pass");
        assert_eq!(
            env.render().expect("updated env should render").as_bytes(),
            include_bytes!("../../../fixtures/rust-io/env-update.golden")
        );

        let before = env.clone();
        let error = env
            .apply_guarded(&[("B", "changed"), ("NOPE", "x")], &["B"])
            .expect_err("non-allowlisted key should reject the transaction");
        assert_eq!(error.kind(), KvErrorKind::KeyNotAllowed);
        assert_eq!(env, before);
    }

    #[test]
    fn strict_environment_parser_rejects_duplicates_malformed_keys_and_cr() {
        assert_eq!(
            EnvFile::parse("A=1\nA=2\n")
                .expect_err("duplicate should fail")
                .kind(),
            KvErrorKind::DuplicateKey
        );
        assert_eq!(
            EnvFile::parse("bad=1\n")
                .expect_err("unsafe key should fail")
                .kind(),
            KvErrorKind::InvalidKey
        );
        assert_eq!(
            EnvFile::parse("A=1\r\n")
                .expect_err("CR should fail")
                .kind(),
            KvErrorKind::UnsafeValue
        );
    }

    #[test]
    fn byte_selection_preserves_invalid_utf8_and_duplicate_policies() {
        let input = b"KEY=first\r\nKEY=\xff\r\r\nKEY=\n";

        assert_eq!(
            select_kv_bytes(
                input,
                b"KEY",
                b"fallback",
                DuplicatePolicy::First,
                CrStrip::None
            ),
            b"first"
        );
        assert_eq!(
            select_kv_bytes(
                input,
                b"KEY",
                b"fallback",
                DuplicatePolicy::Last,
                CrStrip::None
            ),
            b""
        );
        assert_eq!(
            select_kv_bytes(
                input,
                b"KEY",
                b"fallback",
                DuplicatePolicy::LastNonEmpty,
                CrStrip::Both,
            ),
            b"\xff"
        );
    }

    #[test]
    fn allowlisted_shell_assignments_match_legacy_token_rules() {
        let allowed = ["SAFE", "OTHER"];

        assert_eq!(
            parse_allowlisted_env_line(
                " export SAFE='two words' ",
                &allowed,
                Some(KeyPolicy::Environment),
                true,
            ),
            Some(("SAFE".to_owned(), "two words".to_owned()))
        );
        assert_eq!(
            parse_allowlisted_env_line("SAFE=#literal", &allowed, None, false),
            Some(("SAFE".to_owned(), "#literal".to_owned()))
        );
        assert!(parse_allowlisted_env_line("SAFE=two words", &allowed, None, false).is_none());
        assert!(parse_allowlisted_env_line("SAFE='unterminated", &allowed, None, false).is_none());
        assert!(parse_allowlisted_env_line("SAFE=a\\\nb", &allowed, None, false).is_none());
        assert!(parse_allowlisted_env_line("NOPE=value", &allowed, None, false).is_none());
        assert!(parse_allowlisted_env_line("SAFE='line\nbreak'", &allowed, None, false).is_none());
    }

    #[test]
    fn kv_row_value_returns_the_first_matching_row() {
        let rows = vec![
            ("A".to_owned(), "one".to_owned()),
            ("B".to_owned(), "two".to_owned()),
            ("A".to_owned(), "later".to_owned()),
        ];
        assert_eq!(kv_row_value(&rows, "A"), Some("one"));
        assert_eq!(kv_row_value(&rows, "B"), Some("two"));
        assert_eq!(kv_row_value(&rows, "missing"), None);
    }

    #[test]
    fn kv_text_preserves_order_and_rejects_newlines() {
        assert_eq!(
            kv_text(&[("B", "two"), ("A", "one=1")]).expect("safe rows should render"),
            "B=two\nA=one=1\n"
        );
        assert_eq!(
            kv_text(&[("A", "one\nFORGED=yes")])
                .expect_err("line forging should fail")
                .kind(),
            KvErrorKind::UnsafeValue
        );
    }
}
