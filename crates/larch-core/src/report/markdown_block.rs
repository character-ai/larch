//! Marker-delimited Markdown block upsert for report renderers.
//!
//! Ports Python `larch.report.markdown_block`. Recovery matches the Python
//! state machine: a valid begin/end pair is replaced in place; a lone begin
//! truncates from the marker; a lone end drops the head through the marker;
//! absent markers append. Empty or identical markers fail closed.

use std::{
    error::Error,
    fmt,
    fs::{self, File, OpenOptions},
    io::{self, Write},
    path::Path,
};

/// A validated begin/end marker pair for [`replace_markdown_block`].
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct BlockMarkers {
    begin: String,
    end: String,
}

impl BlockMarkers {
    /// Validate and construct a distinct non-empty marker pair.
    ///
    /// # Errors
    ///
    /// Returns [`BlockMarkersError`] when either marker is empty or both are equal.
    pub fn new(
        begin: impl Into<String>,
        end: impl Into<String>,
    ) -> Result<Self, BlockMarkersError> {
        let begin = begin.into();
        let end = end.into();
        if begin.is_empty() || end.is_empty() {
            return Err(BlockMarkersError {
                kind: BlockMarkersErrorKind::Empty,
            });
        }
        if begin == end {
            return Err(BlockMarkersError {
                kind: BlockMarkersErrorKind::NotDistinct,
            });
        }
        Ok(Self { begin, end })
    }

    /// Return the begin marker token (without HTML comment wrappers).
    #[must_use]
    pub fn begin(&self) -> &str {
        &self.begin
    }

    /// Return the end marker token (without HTML comment wrappers).
    #[must_use]
    pub fn end(&self) -> &str {
        &self.end
    }
}

/// Why [`BlockMarkers::new`] rejected a marker pair.
#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub enum BlockMarkersErrorKind {
    /// A marker was empty.
    Empty,
    /// Begin and end were identical.
    NotDistinct,
}

/// Typed marker-pair validation failure.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BlockMarkersError {
    kind: BlockMarkersErrorKind,
}

impl BlockMarkersError {
    /// Return the failure kind.
    #[must_use]
    pub const fn kind(&self) -> BlockMarkersErrorKind {
        self.kind
    }

    /// Return the stable machine reason.
    #[must_use]
    pub const fn reason(&self) -> &'static str {
        match self.kind {
            BlockMarkersErrorKind::Empty => "block-markers-empty",
            BlockMarkersErrorKind::NotDistinct => "block-markers-not-distinct",
        }
    }
}

impl fmt::Display for BlockMarkersError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.kind {
            BlockMarkersErrorKind::Empty => formatter.write_str("block markers must be non-empty"),
            BlockMarkersErrorKind::NotDistinct => {
                formatter.write_str("block markers must be distinct")
            }
        }
    }
}

impl Error for BlockMarkersError {}

/// Replace the marker-delimited block in `target` with `block`.
///
/// Warnings for lone begin/end recovery go to stderr, matching Python's
/// default `warn` callback.
///
/// # Errors
///
/// Returns an [`io::Error`] when the target cannot be read or the atomic write
/// fails. The original file is left intact when the write fails.
pub fn replace_markdown_block(
    target: &Path,
    block: &str,
    markers: &BlockMarkers,
    label: &str,
) -> io::Result<()> {
    replace_markdown_block_with_warn(target, block, markers, label, |message| {
        eprintln!("{message}");
    })
}

/// Replace the marker-delimited block, routing recovery warnings through `warn`.
///
/// # Errors
///
/// Returns an [`io::Error`] when the target cannot be read or the atomic write
/// fails. The original file is left intact when the write fails.
pub fn replace_markdown_block_with_warn<F>(
    target: &Path,
    block: &str,
    markers: &BlockMarkers,
    label: &str,
    mut warn: F,
) -> io::Result<()>
where
    F: FnMut(String),
{
    let existing = read_existing_text(target)?;
    let text = rewrite_block_text(
        &existing,
        block,
        markers,
        label,
        &target.display().to_string(),
        &mut warn,
    );
    let mode = existing_mode(target);
    atomic_write_text(target, &text, mode)
}

fn rewrite_block_text<F>(
    existing: &str,
    block: &str,
    markers: &BlockMarkers,
    label: &str,
    target_display: &str,
    warn: &mut F,
) -> String
where
    F: FnMut(String),
{
    let lines = split_keep_ends(existing);
    let (begin_idx, end_idx, has_begin, has_end) = locate_markers(&lines, markers);

    if has_begin && has_end {
        let Some(begin) = begin_idx else {
            return append_block(existing, block);
        };
        let Some(end) = end_idx else {
            return append_block(existing, block);
        };
        let mut text = String::new();
        for line in &lines[..begin] {
            text.push_str(line);
        }
        text.push_str(block);
        for line in &lines[end + 1..] {
            text.push_str(line);
        }
        return text;
    }

    if has_begin && !has_end {
        warn(format!(
            "{label}: warning: {target_display} has lone <!-- {} --> marker; \
             truncating from marker and rewriting block",
            markers.begin()
        ));
        let mut kept = String::new();
        for line in &lines {
            if is_marker_line(line, markers.begin()) {
                break;
            }
            kept.push_str(line);
        }
        return finish_recovered_prefix(&kept, block);
    }

    if has_end && !has_begin {
        warn(format!(
            "{label}: warning: {target_display} has lone <!-- {} --> marker; \
             dropping head through marker and rewriting block",
            markers.end()
        ));
        let mut kept_tail = String::new();
        let mut past = false;
        for line in &lines {
            if is_marker_line(line, markers.end()) {
                past = true;
                continue;
            }
            if past {
                kept_tail.push_str(line);
            }
        }
        return finish_recovered_prefix(&kept_tail, block);
    }

    append_block(existing, block)
}

fn finish_recovered_prefix(kept: &str, block: &str) -> String {
    let mut text = kept.to_owned();
    if !text.is_empty() && !text.ends_with('\n') {
        text.push('\n');
    }
    text.push_str(block);
    text
}

fn append_block(existing: &str, block: &str) -> String {
    let mut text = existing.to_owned();
    if !existing.is_empty() {
        text.push('\n');
    }
    text.push_str(block);
    text
}

fn locate_markers(
    lines: &[String],
    markers: &BlockMarkers,
) -> (Option<usize>, Option<usize>, bool, bool) {
    let mut begin_idx = None;
    let mut end_idx = None;
    let mut has_begin = false;
    let mut has_end = false;
    for (idx, line) in lines.iter().enumerate() {
        if is_marker_line(line, markers.begin()) {
            has_begin = true;
            if begin_idx.is_none() {
                begin_idx = Some(idx);
            }
        }
        if is_marker_line(line, markers.end()) {
            has_end = true;
            if begin_idx.is_some() && end_idx.is_none() {
                end_idx = Some(idx);
            }
        }
    }
    (begin_idx, end_idx, has_begin, has_end)
}

/// Match Python `^\s*<!-- {marker} -->\s*$` against a keepends line.
fn is_marker_line(line: &str, marker: &str) -> bool {
    let stripped = line.trim_end_matches(['\r', '\n']);
    let trimmed = stripped.trim();
    let prefix = "<!-- ";
    let suffix = " -->";
    trimmed
        .strip_prefix(prefix)
        .and_then(|rest| rest.strip_suffix(suffix))
        .is_some_and(|inner| inner == marker)
}

/// Split like Python `str.splitlines(keepends=True)` after universal-newline read.
fn split_keep_ends(text: &str) -> Vec<String> {
    let mut lines = Vec::new();
    let mut start = 0;
    let bytes = text.as_bytes();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index] == b'\n' {
            lines.push(text[start..=index].to_owned());
            index += 1;
            start = index;
            continue;
        }
        index += 1;
    }
    if start < text.len() {
        lines.push(text[start..].to_owned());
    }
    lines
}

fn read_existing_text(target: &Path) -> io::Result<String> {
    if !target.is_file() {
        return Ok(String::new());
    }
    // Match Python `Path.read_text` universal-newline mode.
    let raw = fs::read_to_string(target)?;
    Ok(raw.replace("\r\n", "\n").replace('\r', "\n"))
}

fn existing_mode(path: &Path) -> Option<u32> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        fs::metadata(path)
            .ok()
            .filter(std::fs::Metadata::is_file)
            .map(|meta| meta.permissions().mode() & 0o777)
    }
    #[cfg(not(unix))]
    {
        let _ = path;
        None
    }
}

fn atomic_write_text(path: &Path, text: &str, mode: Option<u32>) -> io::Result<()> {
    if let Some(parent) = path.parent()
        && !parent.as_os_str().is_empty()
    {
        fs::create_dir_all(parent)?;
    }
    let temporary = path.with_file_name(format!(
        "{}{}",
        path.file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("markdown-block"),
        ".tmp"
    ));
    let write_result = (|| {
        let mut file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&temporary)?;
        file.write_all(text.as_bytes())?;
        file.sync_all()?;
        drop(file);
        if let Some(mode_bits) = mode {
            set_mode(&temporary, mode_bits)?;
        }
        fs::rename(&temporary, path)?;
        Ok(())
    })();
    if write_result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    write_result
}

fn set_mode(path: &Path, mode: u32) -> io::Result<()> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut permissions = File::open(path)?.metadata()?.permissions();
        permissions.set_mode(mode);
        fs::set_permissions(path, permissions)
    }
    #[cfg(not(unix))]
    {
        let _ = (path, mode);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::{
        BlockMarkers, BlockMarkersErrorKind, is_marker_line, replace_markdown_block,
        replace_markdown_block_with_warn, rewrite_block_text,
    };
    use std::{fs, path::Path};
    use tempfile::tempdir;

    #[test]
    fn block_markers_reject_empty_and_equal() {
        assert_eq!(
            BlockMarkers::new("", "end").unwrap_err().kind(),
            BlockMarkersErrorKind::Empty
        );
        assert_eq!(
            BlockMarkers::new("begin", "").unwrap_err().kind(),
            BlockMarkersErrorKind::Empty
        );
        assert_eq!(
            BlockMarkers::new("same", "same").unwrap_err().kind(),
            BlockMarkersErrorKind::NotDistinct
        );
        assert_eq!(
            BlockMarkers::new("", "end").unwrap_err().reason(),
            "block-markers-empty"
        );
    }

    #[test]
    fn marker_line_requires_full_line_boundary() {
        assert!(is_marker_line("<!-- token-report-end -->\n", "token-report-end"));
        assert!(is_marker_line("  <!-- token-report-end -->  \n", "token-report-end"));
        // Mid-line marker-like text cannot break the block boundary.
        assert!(!is_marker_line(
            "see <!-- token-report-end --> inside\n",
            "token-report-end"
        ));
        assert!(!is_marker_line(
            "<!-- token-report-end --> trailing\n",
            "token-report-end"
        ));
    }

    #[test]
    fn replace_table_matches_python_recovery() {
        let markers = BlockMarkers::new("token-report-begin", "token-report-end").unwrap();
        let cases = [
            (
                "header\n<!-- token-report-begin -->\nold\n<!-- token-report-end -->\nfooter\n",
                "NEW\n",
                "header\nNEW\nfooter\n",
                false,
            ),
            (
                "just prose\nhere\n",
                "NEW\n",
                "just prose\nhere\n\nNEW\n",
                false,
            ),
            (
                "header\n<!-- token-report-begin -->\nold\nfooter\n",
                "NEW\n",
                "header\nNEW\n",
                true,
            ),
            (
                "header\nold\n<!-- token-report-end -->\nfooter\n",
                "NEW\n",
                "footer\nNEW\n",
                true,
            ),
            (
                "header\n<!-- token-report-end -->\nmiddle\n<!-- token-report-begin -->\nfooter\n",
                "NEW\n",
                "header\n<!-- token-report-end -->\nmiddle\n<!-- token-report-begin -->\nfooter\n\nNEW\n",
                false,
            ),
            (
                "header\n<!-- token-report-begin -->\nold1\n<!-- token-report-end -->\nmid\n<!-- token-report-begin -->\nold2\n<!-- token-report-end -->\nfooter\n",
                "NEW\n",
                "header\nNEW\nmid\n<!-- token-report-begin -->\nold2\n<!-- token-report-end -->\nfooter\n",
                false,
            ),
            ("", "NEW\n", "NEW\n", false),
            (
                "header\n<!-- token-report-begin -->\nold\n<!-- token-report-end -->\nfooter",
                "NEW\n",
                "header\nNEW\nfooter",
                false,
            ),
        ];
        for (before, block, expected, expect_warn) in cases {
            let mut warnings = Vec::new();
            let got = rewrite_block_text(
                before,
                block,
                &markers,
                "token report",
                "body.md",
                &mut |msg| warnings.push(msg),
            );
            assert_eq!(got, expected, "before={before:?}");
            assert_eq!(!warnings.is_empty(), expect_warn, "before={before:?}");
        }
    }

    #[test]
    fn untrusted_mid_line_marker_cannot_break_out_of_block() {
        let markers = BlockMarkers::new("report-begin", "report-end").unwrap();
        let hostile = "header\n<!-- report-begin -->\n\
            hostile see <!-- report-end --> mid-line\n\
            still-inside\n\
            <!-- report-end -->\nfooter\n";
        // Mid-line marker-like text is not a boundary; the full-line end closes.
        let mut warnings = Vec::new();
        let got = rewrite_block_text(
            hostile,
            "SAFE\n",
            &markers,
            "report",
            "body.md",
            &mut |msg| warnings.push(msg),
        );
        assert_eq!(got, "header\nSAFE\nfooter\n");
        assert!(warnings.is_empty());
        assert!(!got.contains("still-inside"));
        assert!(!got.contains("<!-- report-end --> mid-line"));
    }

    #[test]
    fn replace_preserves_mode_and_is_idempotent_when_block_includes_markers() {
        let dir = tempdir().unwrap();
        let target = dir.path().join("body.md");
        fs::write(
            &target,
            "<!-- timing-report-begin -->\nold\n<!-- timing-report-end -->\n",
        )
        .unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mut permissions = fs::metadata(&target).unwrap().permissions();
            permissions.set_mode(0o600);
            fs::set_permissions(&target, permissions).unwrap();
        }
        let markers = BlockMarkers::new("timing-report-begin", "timing-report-end").unwrap();
        let block = "<!-- timing-report-begin -->\nNEW\n<!-- timing-report-end -->\n";
        replace_markdown_block(&target, block, &markers, "timing report").unwrap();
        assert_eq!(fs::read_to_string(&target).unwrap(), block);
        replace_markdown_block(&target, block, &markers, "timing report").unwrap();
        assert_eq!(fs::read_to_string(&target).unwrap(), block);
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            assert_eq!(
                fs::metadata(&target).unwrap().permissions().mode() & 0o777,
                0o600
            );
        }
        let _ = Path::new(".");
    }

    #[test]
    fn warn_callback_receives_lone_begin_message() {
        let dir = tempdir().unwrap();
        let target = dir.path().join("body.md");
        fs::write(&target, "<!-- a-begin -->\nold\n").unwrap();
        let markers = BlockMarkers::new("a-begin", "a-end").unwrap();
        let mut warnings = Vec::new();
        replace_markdown_block_with_warn(&target, "NEW\n", &markers, "label", |msg| {
            warnings.push(msg);
        })
        .unwrap();
        assert_eq!(warnings.len(), 1);
        assert!(warnings[0].contains("lone <!-- a-begin -->"));
        assert_eq!(fs::read_to_string(&target).unwrap(), "NEW\n");
    }
}
