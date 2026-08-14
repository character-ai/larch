//! Pure aggregation and rendering for the repository-size developer report.

const CATEGORY_WIDTH: usize = 45;
const FILES_WIDTH: usize = 5;
const LINES_WIDTH: usize = 6;
const SIZE_LABEL_WIDTH: usize = 29;
const BYTES_PER_MEBIBYTE: f64 = 1024.0 * 1024.0;
const LINE_COUNT_EXCLUDED_PREFIXES: [&[u8]; 2] = [b"larch-logs/", b"node_modules/"];
const LARCH_LOGS_PREFIX: &[u8] = b"larch-logs/";
const IMPLEMENT_LOGS_PREFIX: &[u8] = b"larch-logs/implement/";
const DESIGN_LOGS_PREFIX: &[u8] = b"larch-logs/design/";

/// One fixed source category in the repository-size report.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RepoSizeCategory {
    /// Non-test shell scripts.
    BashScripts,
    /// Shell tests named `test-*.sh`.
    BashTests,
    /// Non-test Python source files.
    PythonCode,
    /// Python tests identified by filename or a `tests/` directory.
    PythonTests,
    /// Production Rust source lines.
    RustCode,
    /// Rust test source lines.
    RustTests,
    /// Markdown files.
    Markdown,
}

impl RepoSizeCategory {
    const ALL: [Self; 7] = [
        Self::BashScripts,
        Self::BashTests,
        Self::PythonCode,
        Self::PythonTests,
        Self::RustCode,
        Self::RustTests,
        Self::Markdown,
    ];

    const fn index(self) -> usize {
        match self {
            Self::BashScripts => 0,
            Self::BashTests => 1,
            Self::PythonCode => 2,
            Self::PythonTests => 3,
            Self::RustCode => 4,
            Self::RustTests => 5,
            Self::Markdown => 6,
        }
    }

    const fn label(self) -> &'static str {
        match self {
            Self::BashScripts => "Bash scripts (runtime, non-test *.sh)",
            Self::BashTests => "Bash tests (test-*.sh)",
            Self::PythonCode => "Python code (non-test *.py)",
            Self::PythonTests => "Python tests (test_*.py + tests/)",
            Self::RustCode => "Rust code (non-test *.rs)",
            Self::RustTests => "Rust tests (#[cfg(test)] + tests/ + benches/)",
            Self::Markdown => "All Markdown (*.md)",
        }
    }
}

/// Identify the fixed line-count category for one Git-relative byte path.
#[must_use]
pub fn line_count_category(path: &[u8]) -> Option<RepoSizeCategory> {
    if line_count_excluded(path) {
        return None;
    }

    let basename = path.rsplit(|byte| *byte == b'/').next().unwrap_or(path);
    let suffix = suffix(basename);
    if suffix == b".sh" {
        return Some(if basename.starts_with(b"test-") {
            RepoSizeCategory::BashTests
        } else {
            RepoSizeCategory::BashScripts
        });
    }
    if suffix == b".py" {
        return Some(
            if basename.starts_with(b"test_")
                || basename == b"conftest.py"
                || has_path_component(path, b"tests")
            {
                RepoSizeCategory::PythonTests
            } else {
                RepoSizeCategory::PythonCode
            },
        );
    }
    (suffix == b".md").then_some(RepoSizeCategory::Markdown)
}

/// Return whether a Git-relative byte path contributes Rust line counts.
#[must_use]
pub fn is_rust_line_count_path(path: &[u8]) -> bool {
    if line_count_excluded(path) {
        return false;
    }
    let basename = path.rsplit(|byte| *byte == b'/').next().unwrap_or(path);
    suffix(basename) == b".rs"
}

fn line_count_excluded(path: &[u8]) -> bool {
    LINE_COUNT_EXCLUDED_PREFIXES
        .iter()
        .any(|prefix| path.starts_with(prefix))
}

fn has_path_component(path: &[u8], expected: &[u8]) -> bool {
    path.split(|byte| *byte == b'/')
        .any(|component| component == expected)
}

fn suffix(basename: &[u8]) -> &[u8] {
    let Some(dot) = basename.iter().rposition(|byte| *byte == b'.') else {
        return b"";
    };
    if (dot == 0 && !basename[1..].contains(&b'.')) || dot + 1 == basename.len() {
        return b"";
    }
    &basename[dot..]
}

/// Count newline bytes without decoding file contents.
#[must_use]
pub fn count_newlines(bytes: &[u8]) -> u64 {
    let mut count = 0;
    for byte in bytes {
        if *byte == b'\n' {
            count += 1;
        }
    }
    count
}

/// Split one Rust source file's newline bytes into production and test lines.
///
/// Files below a Cargo tests or benches directory are entirely test code.
/// Other files use a deterministic byte lexer. Strings and comments are
/// masked without removing newlines, then test attributes are paired with the
/// item that follows them. Doc-test fences remain production lines.
#[must_use]
pub fn rust_line_split(path: &[u8], bytes: &[u8]) -> (u64, u64) {
    let total_lines = count_newlines(bytes);
    if has_path_component(path, b"tests") || has_path_component(path, b"benches") {
        return (0, total_lines);
    }

    let newline_offsets: Vec<usize> = bytes
        .iter()
        .enumerate()
        .filter_map(|(index, byte)| (*byte == b'\n').then_some(index))
        .collect();
    let masked = mask_rust_non_code(bytes);
    let mut test_lines = vec![false; newline_offsets.len()];
    let mut index = 0;
    let mut brace_depth = 0_usize;

    while index < masked.len() {
        if masked[index] == b'#'
            && let Some(attribute) = parse_rust_attribute(&masked, index)
        {
            if attribute.inner && attribute.cfg_test && brace_depth == 0 {
                return (0, total_lines);
            }

            let region_end = if !attribute.inner && attribute.cfg_test {
                Some(rust_item_end(&masked, attribute.end))
            } else if !attribute.inner && attribute.test {
                rust_test_function_end(&masked, attribute.end)
            } else {
                None
            };
            if let Some(end) = region_end {
                mark_test_lines(&mut test_lines, &newline_offsets, attribute.start, end);
                index = end.saturating_add(1);
                continue;
            }

            index = attribute.end;
            continue;
        }

        match masked[index] {
            b'{' => brace_depth = brace_depth.saturating_add(1),
            b'}' => brace_depth = brace_depth.saturating_sub(1),
            _ => {}
        }
        index += 1;
    }

    let mut marked_test_lines = 0_u64;
    for is_test in test_lines {
        if is_test {
            marked_test_lines = marked_test_lines.saturating_add(1);
        }
    }
    (
        total_lines.saturating_sub(marked_test_lines),
        marked_test_lines,
    )
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct RustAttribute {
    start: usize,
    end: usize,
    inner: bool,
    cfg_test: bool,
    test: bool,
}

fn parse_rust_attribute(bytes: &[u8], start: usize) -> Option<RustAttribute> {
    if bytes.get(start) != Some(&b'#') {
        return None;
    }

    let mut cursor = skip_ascii_whitespace(bytes, start + 1);
    let inner = bytes.get(cursor) == Some(&b'!');
    if inner {
        cursor = skip_ascii_whitespace(bytes, cursor + 1);
    }
    if bytes.get(cursor) != Some(&b'[') {
        return None;
    }
    let open = cursor;
    let close = matching_square_bracket(bytes, open)?;
    cursor = skip_ascii_whitespace(bytes, open + 1);

    let first_start = cursor;
    let first_end = rust_identifier_end(bytes, first_start)?;
    let first_segment = &bytes[first_start..first_end];
    let mut final_segment = first_segment;
    let mut segment_count = 1_usize;
    cursor = first_end;

    loop {
        cursor = skip_ascii_whitespace(bytes, cursor);
        if bytes.get(cursor..cursor.saturating_add(2)) != Some(b"::") {
            break;
        }
        cursor = skip_ascii_whitespace(bytes, cursor + 2);
        let segment_end = rust_identifier_end(bytes, cursor)?;
        final_segment = &bytes[cursor..segment_end];
        segment_count = segment_count.saturating_add(1);
        cursor = segment_end;
    }

    cursor = skip_ascii_whitespace(bytes, cursor);
    let cfg_test = segment_count == 1
        && first_segment == b"cfg"
        && bytes.get(cursor) == Some(&b'(')
        && cfg_arguments_mention_test(bytes, cursor, close);

    Some(RustAttribute {
        start,
        end: close + 1,
        inner,
        cfg_test,
        test: final_segment == b"test",
    })
}

fn matching_square_bracket(bytes: &[u8], open: usize) -> Option<usize> {
    let mut depth = 1_usize;
    let mut cursor = open + 1;
    while cursor < bytes.len() {
        match bytes[cursor] {
            b'[' => depth = depth.saturating_add(1),
            b']' => {
                depth = depth.saturating_sub(1);
                if depth == 0 {
                    return Some(cursor);
                }
            }
            _ => {}
        }
        cursor += 1;
    }
    None
}

fn cfg_arguments_mention_test(bytes: &[u8], open: usize, limit: usize) -> bool {
    let mut cursor = open + 1;
    while cursor < limit {
        let Some(identifier_end) = rust_identifier_end(bytes, cursor) else {
            cursor += 1;
            continue;
        };
        if &bytes[cursor..identifier_end] == b"test" {
            let before = bytes.get(cursor.wrapping_sub(1)).copied();
            let after = bytes.get(identifier_end).copied();
            if before.is_some_and(cfg_identifier_delimiter)
                && after.is_some_and(cfg_identifier_delimiter)
            {
                let after_whitespace = skip_ascii_whitespace(bytes, identifier_end);
                if bytes.get(after_whitespace) != Some(&b'=') {
                    return true;
                }
            }
        }
        cursor = identifier_end;
    }
    false
}

const fn cfg_identifier_delimiter(byte: u8) -> bool {
    byte.is_ascii_whitespace() || matches!(byte, b'(' | b',' | b')')
}

fn rust_identifier_end(bytes: &[u8], start: usize) -> Option<usize> {
    let first = *bytes.get(start)?;
    if first != b'_' && !first.is_ascii_alphabetic() {
        return None;
    }
    let mut cursor = start + 1;
    while bytes
        .get(cursor)
        .is_some_and(|byte| *byte == b'_' || byte.is_ascii_alphanumeric())
    {
        cursor += 1;
    }
    Some(cursor)
}

fn skip_ascii_whitespace(bytes: &[u8], mut cursor: usize) -> usize {
    while bytes.get(cursor).is_some_and(u8::is_ascii_whitespace) {
        cursor += 1;
    }
    cursor
}

fn skip_leading_rust_attributes(bytes: &[u8], mut cursor: usize) -> usize {
    loop {
        cursor = skip_ascii_whitespace(bytes, cursor);
        let Some(attribute) = parse_rust_attribute(bytes, cursor) else {
            return cursor;
        };
        cursor = attribute.end;
    }
}

fn rust_item_end(bytes: &[u8], cursor: usize) -> usize {
    let mut cursor = skip_leading_rust_attributes(bytes, cursor);
    while cursor < bytes.len() {
        match bytes[cursor] {
            b'{' => return matching_rust_brace(bytes, cursor),
            b';' => return cursor,
            _ => cursor += 1,
        }
    }
    bytes.len().saturating_sub(1)
}

fn rust_test_function_end(bytes: &[u8], cursor: usize) -> Option<usize> {
    let mut cursor = skip_leading_rust_attributes(bytes, cursor);
    let mut saw_fn = false;
    while cursor < bytes.len() {
        if let Some(identifier_end) = rust_identifier_end(bytes, cursor) {
            saw_fn |= &bytes[cursor..identifier_end] == b"fn";
            cursor = identifier_end;
            continue;
        }
        match bytes[cursor] {
            b'{' if saw_fn => return Some(matching_rust_brace(bytes, cursor)),
            b'{' | b';' => return None,
            _ => cursor += 1,
        }
    }
    saw_fn.then(|| bytes.len().saturating_sub(1))
}

fn matching_rust_brace(bytes: &[u8], open: usize) -> usize {
    let mut depth = 1_usize;
    let mut cursor = open + 1;
    while cursor < bytes.len() {
        match bytes[cursor] {
            b'{' => depth = depth.saturating_add(1),
            b'}' => {
                depth = depth.saturating_sub(1);
                if depth == 0 {
                    return cursor;
                }
            }
            _ => {}
        }
        cursor += 1;
    }
    bytes.len().saturating_sub(1)
}

fn mark_test_lines(test_lines: &mut [bool], newline_offsets: &[usize], start: usize, end: usize) {
    if test_lines.is_empty() {
        return;
    }
    let first_line = newline_offsets.partition_point(|newline| *newline < start);
    if first_line >= test_lines.len() {
        return;
    }
    let last_line = newline_offsets
        .partition_point(|newline| *newline < end)
        .min(test_lines.len() - 1);
    for line in &mut test_lines[first_line..=last_line] {
        *line = true;
    }
}

fn mask_rust_non_code(bytes: &[u8]) -> Vec<u8> {
    let mut masked = bytes.to_vec();
    let mut cursor = 0;
    while cursor < bytes.len() {
        let end = match bytes.get(cursor..cursor.saturating_add(2)) {
            Some(b"//") => Some(
                cursor
                    + bytes[cursor..]
                        .iter()
                        .take_while(|byte| **byte != b'\n')
                        .count(),
            ),
            Some(b"/*") => Some(rust_block_comment_end(bytes, cursor)),
            _ => rust_raw_string_end(bytes, cursor)
                .or_else(|| {
                    (bytes[cursor] == b'\'')
                        .then(|| rust_char_literal_end(bytes, cursor))
                        .flatten()
                })
                .or_else(|| (bytes[cursor] == b'"').then(|| rust_quoted_string_end(bytes, cursor))),
        };
        let Some(end) = end else {
            cursor += 1;
            continue;
        };
        mask_non_newlines(&mut masked, cursor, end);
        cursor = end;
    }
    masked
}

fn rust_block_comment_end(bytes: &[u8], start: usize) -> usize {
    let mut depth = 1_usize;
    let mut cursor = start + 2;
    while cursor + 1 < bytes.len() {
        match &bytes[cursor..cursor + 2] {
            b"/*" => {
                depth = depth.saturating_add(1);
                cursor += 2;
            }
            b"*/" => {
                depth = depth.saturating_sub(1);
                cursor += 2;
                if depth == 0 {
                    return cursor;
                }
            }
            _ => cursor += 1,
        }
    }
    bytes.len()
}

fn rust_quoted_string_end(bytes: &[u8], quote: usize) -> usize {
    let mut cursor = quote + 1;
    while cursor < bytes.len() {
        if bytes[cursor] == b'\\' {
            cursor = cursor.saturating_add(2).min(bytes.len());
        } else if bytes[cursor] == b'"' {
            return cursor + 1;
        } else {
            cursor += 1;
        }
    }
    bytes.len()
}

fn rust_raw_string_end(bytes: &[u8], start: usize) -> Option<usize> {
    let hash_start = if bytes.get(start) == Some(&b'r') {
        start + 1
    } else if bytes.get(start..start.saturating_add(2)) == Some(b"br") {
        start + 2
    } else {
        return None;
    };
    let hashes = bytes[hash_start..]
        .iter()
        .take_while(|byte| **byte == b'#')
        .count();
    let quote = hash_start + hashes;
    if bytes.get(quote) != Some(&b'"') {
        return None;
    }

    let mut cursor = quote + 1;
    while cursor < bytes.len() {
        if bytes[cursor] == b'"'
            && bytes.get(cursor + 1..cursor + 1 + hashes)
                == Some(&bytes[hash_start..hash_start + hashes])
        {
            return Some(cursor + 1 + hashes);
        }
        cursor += 1;
    }
    Some(bytes.len())
}

fn rust_char_literal_end(bytes: &[u8], start: usize) -> Option<usize> {
    if bytes.get(start + 1) == Some(&b'\\') {
        let mut cursor = start.saturating_add(3);
        while cursor < bytes.len() {
            if bytes[cursor] == b'\'' {
                return Some(cursor + 1);
            }
            cursor += 1;
        }
        return Some(bytes.len());
    }
    (bytes.get(start + 2) == Some(&b'\'')).then_some(start + 3)
}

fn mask_non_newlines(bytes: &mut [u8], start: usize, end: usize) {
    for byte in &mut bytes[start..end] {
        if *byte != b'\n' {
            *byte = b' ';
        }
    }
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct CategoryCounts {
    files: u64,
    lines: u64,
}

/// Aggregated values for the fixed repository-size report.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepoSizeReport {
    categories: [CategoryCounts; 7],
    repo_total: u64,
    larch_logs_total: u64,
    implement: u64,
    design: u64,
}

impl RepoSizeReport {
    /// Record one classified file's newline-byte total.
    pub const fn add_line_count(&mut self, category: RepoSizeCategory, lines: u64) {
        let counts = &mut self.categories[category.index()];
        counts.files = counts.files.saturating_add(1);
        counts.lines = counts.lines.saturating_add(lines);
    }

    /// Record one Rust file's production and test newline totals.
    ///
    /// A mixed file contributes one file to each non-empty category. A file
    /// with no newline bytes contributes to neither category.
    pub const fn add_rust_line_split(&mut self, code_lines: u64, test_lines: u64) {
        if code_lines > 0 {
            self.add_line_count(RepoSizeCategory::RustCode, code_lines);
        }
        if test_lines > 0 {
            self.add_line_count(RepoSizeCategory::RustTests, test_lines);
        }
    }

    /// Record one tracked file's logical byte size.
    pub fn add_size(&mut self, path: &[u8], bytes: u64) {
        self.repo_total = self.repo_total.saturating_add(bytes);
        if !path.starts_with(LARCH_LOGS_PREFIX) {
            return;
        }
        self.larch_logs_total = self.larch_logs_total.saturating_add(bytes);
        if path.starts_with(IMPLEMENT_LOGS_PREFIX) {
            self.implement = self.implement.saturating_add(bytes);
        } else if path.starts_with(DESIGN_LOGS_PREFIX) {
            self.design = self.design.saturating_add(bytes);
        }
    }

    /// Render the report with its fixed text layout.
    #[must_use]
    pub fn render(&self) -> String {
        let mut rows = vec![
            format!(
                "┌{}┬{}┬{}┐",
                "─".repeat(CATEGORY_WIDTH + 2),
                "─".repeat(FILES_WIDTH + 2),
                "─".repeat(LINES_WIDTH + 2),
            ),
            format!(
                "│ {:^CATEGORY_WIDTH$} │ {:^FILES_WIDTH$} │ {:^LINES_WIDTH$} │",
                "Category", "Files", "Lines",
            ),
            table_middle(),
        ];
        for (index, category) in RepoSizeCategory::ALL.iter().enumerate() {
            let counts = self.categories[category.index()];
            rows.push(format!(
                "│ {:<CATEGORY_WIDTH$} │ {:>FILES_WIDTH$} │ {:>LINES_WIDTH$} │",
                category.label(),
                grouped(counts.files),
                grouped(counts.lines),
            ));
            if index + 1 != RepoSizeCategory::ALL.len() {
                rows.push(table_middle());
            }
        }
        rows.push(format!(
            "└{}┴{}┴{}┘",
            "─".repeat(CATEGORY_WIDTH + 2),
            "─".repeat(FILES_WIDTH + 2),
            "─".repeat(LINES_WIDTH + 2),
        ));
        rows.push(String::new());

        let rest = self
            .larch_logs_total
            .saturating_sub(self.implement)
            .saturating_sub(self.design);
        let repo_minus_logs = self.repo_total.saturating_sub(self.larch_logs_total);
        rows.extend([
            render_size_line("Repo (tracked content):", self.repo_total, ""),
            render_size_line(
                "larch-logs/ total:",
                self.larch_logs_total,
                &format!(
                    "   ({:>4.1}% of repo)",
                    percentage(self.larch_logs_total, self.repo_total),
                ),
            ),
            render_size_line(
                "  ├─ implement:",
                self.implement,
                &format!(
                    "   ({:>4.1}% of run-logs)",
                    percentage(self.implement, self.larch_logs_total),
                ),
            ),
            render_size_line(
                "  ├─ design:",
                self.design,
                &format!(
                    "   ({:>4.1}% of run-logs)",
                    percentage(self.design, self.larch_logs_total),
                ),
            ),
            render_size_line(
                "  └─ rest (shared, etc.):",
                rest,
                &format!(
                    "   ({:>4.1}% of run-logs)",
                    percentage(rest, self.larch_logs_total),
                ),
            ),
            render_size_line(
                "Repo minus larch-logs:",
                repo_minus_logs,
                &format!(
                    "   ({:>4.1}% of repo)",
                    percentage(repo_minus_logs, self.repo_total),
                ),
            ),
        ]);
        rows.join("\n")
    }
}

fn table_middle() -> String {
    format!(
        "├{}┼{}┼{}┤",
        "─".repeat(CATEGORY_WIDTH + 2),
        "─".repeat(FILES_WIDTH + 2),
        "─".repeat(LINES_WIDTH + 2),
    )
}

fn grouped(value: u64) -> String {
    let digits = value.to_string();
    let mut output = String::with_capacity(digits.len() + digits.len() / 3);
    for (index, byte) in digits.bytes().enumerate() {
        if index > 0 && (digits.len() - index).is_multiple_of(3) {
            output.push(',');
        }
        output.push(char::from(byte));
    }
    output
}

#[allow(clippy::cast_precision_loss)] // Preserve the legacy Python float percentage formatter.
fn percentage(numerator: u64, denominator: u64) -> f64 {
    if denominator == 0 {
        return 0.0;
    }
    numerator as f64 * 100.0 / denominator as f64
}

#[allow(clippy::cast_precision_loss)] // Preserve the legacy Python float size formatter.
fn render_size_line(label: &str, bytes: u64, suffix: &str) -> String {
    format!(
        "{label:<SIZE_LABEL_WIDTH$}{:>8.2} MB{suffix}",
        bytes as f64 / BYTES_PER_MEBIBYTE,
    )
}

#[cfg(test)]
mod tests {
    use proptest::prelude::*;

    use super::{
        RepoSizeCategory, RepoSizeReport, count_newlines, is_rust_line_count_path,
        line_count_category, rust_line_split,
    };

    fn assert_rust_split(path: &[u8], source: &[u8], expected: (u64, u64)) {
        let actual = rust_line_split(path, source);
        assert_eq!(actual, expected);
        assert_eq!(actual.0 + actual.1, count_newlines(source));
    }

    #[test]
    fn classifies_only_the_fixed_source_categories() {
        assert_eq!(
            line_count_category(b"scripts/larch.sh"),
            Some(RepoSizeCategory::BashScripts)
        );
        assert_eq!(
            line_count_category(b"scripts/test-larch.sh"),
            Some(RepoSizeCategory::BashTests)
        );
        assert_eq!(
            line_count_category(b"python/tool.py"),
            Some(RepoSizeCategory::PythonCode)
        );
        assert_eq!(
            line_count_category(b"python/test_tool.py"),
            Some(RepoSizeCategory::PythonTests)
        );
        assert_eq!(
            line_count_category(b"python/tests/helper.py"),
            Some(RepoSizeCategory::PythonTests)
        );
        assert_eq!(
            line_count_category(b"python/conftest.py"),
            Some(RepoSizeCategory::PythonTests)
        );
        assert_eq!(
            line_count_category(b"docs/guide.md"),
            Some(RepoSizeCategory::Markdown)
        );
        assert_eq!(line_count_category(b"crates/larch-core/src/lib.rs"), None);
        assert!(is_rust_line_count_path(b"crates/larch-core/src/lib.rs"));
        assert!(!is_rust_line_count_path(b"larch-logs/generated.rs"));
        assert!(!is_rust_line_count_path(b"node_modules/pkg/generated.rs"));
        assert_eq!(line_count_category(b"larch-logs/run.md"), None);
        assert_eq!(line_count_category(b"node_modules/pkg/readme.md"), None);
        assert_eq!(line_count_category(b"docs/.md"), None);
    }

    #[test]
    fn splits_cfg_test_module_lines() {
        assert_rust_split(
            b"crates/example/src/lib.rs",
            b"fn production() {}\n\
              #[cfg(test)]\n\
              mod tests {\n\
                  #[test]\n\
                  fn works() {}\n\
              }\n",
            (1, 5),
        );
    }

    #[test]
    fn splits_compound_cfg_test_and_blockless_items() {
        assert_rust_split(
            b"crates/example/src/lib.rs",
            b"#[cfg(all(test, feature = \"x\"))]\n\
              fn helper() {\n\
                  assert!(true);\n\
              }\n\
              fn production() {}\n",
            (1, 4),
        );
        assert_rust_split(
            b"crates/example/src/lib.rs",
            b"#[cfg(test)]\n\
              use crate::helper;\n\
              fn production() {}\n",
            (1, 2),
        );
    }

    #[test]
    fn masks_raw_strings_comments_and_non_test_cfg_values() {
        let raw_string = br####"const TEXT: &str = r###"
#[cfg(test)]
}
"###;
fn production() {}
"####;
        assert_rust_split(b"crates/example/src/lib.rs", raw_string, (5, 0));

        let comments = b"/* outer\n\
             /* #[cfg(test)] mod hidden { */\n\
             }\n\
             */\n\
             // #[test]\n\
             fn production() {}\n";
        assert_rust_split(b"crates/example/src/lib.rs", comments, (6, 0));

        let named_cfg_values = b"#[cfg(feature = \"test\")]\n\
            fn feature_named_test() {}\n\
            #[cfg(test = \"value\")]\n\
            fn keyed_test() {}\n";
        assert_rust_split(b"crates/example/src/lib.rs", named_cfg_values, (4, 0));
    }

    #[test]
    fn malformed_literals_remain_bounded() {
        assert_rust_split(
            b"crates/example/src/lib.rs",
            b"let text = \"unterminated\\",
            (0, 0),
        );
    }

    #[test]
    fn distinguishes_char_literals_from_lifetimes() {
        assert_rust_split(
            b"crates/example/src/lib.rs",
            b"#[cfg(test)]\n\
              fn helper<'a>(value: &'a str) {\n\
                  let brace = '{';\n\
                  let _ = value;\n\
              }\n\
              fn production() {}\n",
            (1, 5),
        );
    }

    #[test]
    fn treats_cargo_test_directories_as_whole_file_tests() {
        assert_rust_split(
            b"crates/example/tests/integration.rs",
            b"fn first() {}\nfn second() {}\n",
            (0, 2),
        );
        assert_rust_split(
            b"crates/example/benches/throughput.rs",
            b"fn benchmark() {}\n",
            (0, 1),
        );
    }

    #[test]
    fn splits_inner_and_function_test_attributes() {
        assert_rust_split(
            b"crates/example/src/test_only.rs",
            b"#![cfg(test)]\nfn helper() {}\n",
            (0, 2),
        );
        assert_rust_split(
            b"crates/example/src/lib.rs",
            b"fn production() {}\n\
              #[test]\n\
              fn standalone() {\n\
              }\n",
            (1, 3),
        );
        assert_rust_split(
            b"crates/example/src/lib.rs",
            b"#[tokio::test]\n\
              async fn asynchronous() {}\n\
              fn production() {}\n",
            (1, 2),
        );
    }

    proptest! {
        #[test]
        fn arbitrary_bytes_preserve_every_newline(bytes in prop::collection::vec(any::<u8>(), 0..512)) {
            let (code, tests) = rust_line_split(b"crates/example/src/lib.rs", &bytes);
            prop_assert_eq!(code + tests, count_newlines(&bytes));
        }
    }

    #[test]
    fn renders_zero_totals() {
        let report = RepoSizeReport::default();
        assert_eq!(count_newlines(b"one\ntwo\n"), 2);
        assert!(report.render().contains("( 0.0% of repo)"));
        assert!(report.render().contains("( 0.0% of run-logs)"));
    }

    #[test]
    fn rust_file_counts_include_only_non_empty_contributions() {
        let mut report = RepoSizeReport::default();
        report.add_rust_line_split(3, 2);
        report.add_rust_line_split(1, 0);
        report.add_rust_line_split(0, 4);
        report.add_rust_line_split(0, 0);
        let rendered = report.render();

        assert!(
            rendered.contains("Rust code (non-test *.rs)                     │     2 │      4")
        );
        assert!(
            rendered.contains("Rust tests (#[cfg(test)] + tests/ + benches/) │     2 │      6")
        );
    }

    #[test]
    fn renders_logical_mebibyte_totals_and_splits() {
        let mut report = RepoSizeReport::default();
        report.add_size(b"assets/data.bin", 1024 * 1024);
        report.add_size(b"larch-logs/implement/run.bin", 1024 * 1024);
        let rendered = report.render();

        assert!(rendered.contains("Repo (tracked content):          2.00 MB"));
        assert!(rendered.contains("larch-logs/ total:               1.00 MB   (50.0% of repo)"));
        assert!(
            rendered.contains("  ├─ implement:                  1.00 MB   (100.0% of run-logs)")
        );
        assert!(rendered.contains("Repo minus larch-logs:           1.00 MB   (50.0% of repo)"));
    }
}
