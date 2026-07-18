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
#[derive(Clone, Debug, Eq, PartialEq)]
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
        KvErrorKind, KvRow, MalformedLinePolicy, ParseOptions, RenderOptions,
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
}
