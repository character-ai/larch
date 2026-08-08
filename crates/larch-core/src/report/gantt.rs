//! Generic ASCII Gantt renderer.
//!
//! Ports `larch.rendering.gantt`. The renderer carries no reviewer-domain
//! knowledge: labels pass through unchanged, row times and window times share
//! one absolute base, and rows with no positive overlap after clamping are
//! dropped. `larch_adapters::phase_detail` keeps its own inlined copy of the
//! default-width path because that report predates this owner; both agree on
//! the glyphs, the box, and the axis.

use crate::text::{python_int, split_text_lines};

/// Track width the CLI uses when `--width` is absent.
pub const DEFAULT_WIDTH: i64 = 56;
/// Largest track width the CLI accepts.
///
/// The Python owner had no bound and died with `MemoryError` on an absurd
/// width. A bounded refusal keeps the acceptance promise that oversized input
/// never panics, and no real chart approaches this width.
pub const MAX_WIDTH: i64 = 10_000;
/// Seconds in one minute, for the `m:ss` axis labels.
const SECONDS_PER_MINUTE: i64 = 60;
/// Tab-delimited column count every rows-TSV record must carry.
const TSV_COLUMN_COUNT: usize = 3;

/// One labelled bar in the same absolute time base as the window.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GanttRow {
    /// Opaque caller text, never sanitized or truncated.
    pub label: String,
    /// Absolute start second.
    pub start_s: i64,
    /// Absolute end second.
    pub end_s: i64,
}

impl GanttRow {
    /// Build one row from its label and absolute bounds.
    #[must_use]
    pub fn new(label: impl Into<String>, start_s: i64, end_s: i64) -> Self {
        Self {
            label: label.into(),
            start_s,
            end_s,
        }
    }
}

/// Format non-negative seconds as `m:ss` for chart axes and titles.
///
/// This is the axis formatter, not the table duration formatter.
#[must_use]
pub fn format_mss(seconds: i64) -> String {
    let value = seconds.max(0);
    format!(
        "{}:{:02}",
        value / SECONDS_PER_MINUTE,
        value % SECONDS_PER_MINUTE
    )
}

/// Render `rows` as a plain ASCII Gantt chart, or the empty string when no row
/// overlaps the window.
///
/// `width` absent selects [`DEFAULT_WIDTH`] and enables the label-aware
/// narrowing the Python owner applies only to the default.
#[must_use]
pub fn render_gantt(
    window_start_s: i64,
    window_end_s: i64,
    rows: &[GanttRow],
    width: Option<i64>,
) -> String {
    let use_default_width = width.is_none();
    let requested = width.unwrap_or(DEFAULT_WIDTH).max(1);
    let span = window_end_s.saturating_sub(window_start_s).max(1);
    let filtered: Vec<(&GanttRow, i64, i64, i64)> = rows
        .iter()
        .filter_map(|row| {
            let start = row.start_s.max(window_start_s);
            let end = row.end_s.min(window_end_s);
            (end > start).then(|| (row, start, end, end - start))
        })
        .collect();
    if filtered.is_empty() {
        return String::new();
    }

    let label_width = filtered
        .iter()
        .map(|(row, _, _, _)| row.label.chars().count())
        .max()
        .unwrap_or(0);
    let duration_width = filtered
        .iter()
        .map(|(_, _, _, duration)| format!("{duration}s").chars().count())
        .max()
        .unwrap_or(0);
    let width = if use_default_width {
        let budget = 90_i64
            .saturating_sub(i64::try_from(label_width).unwrap_or(i64::MAX))
            .saturating_sub(i64::try_from(duration_width).unwrap_or(i64::MAX))
            .saturating_sub(4)
            .max(10);
        requested.min(budget)
    } else {
        requested
    };
    let width = usize::try_from(width).unwrap_or(usize::MAX);

    let prefix = " ".repeat(label_width + 1);
    let mut lines = vec![axis(label_width, width, &format_mss(span))];
    lines.push(format!("{prefix}┌{}┐", "─".repeat(width)));
    for (row, start, end, duration) in filtered {
        let track = bar(start, end, window_start_s, span, width);
        let duration = format!("{duration}s");
        lines.push(format!(
            "{} │{track}│ {}",
            pad_right(&row.label, label_width),
            pad_left(&duration, duration_width)
        ));
    }
    lines.push(format!("{prefix}└{}┘", "─".repeat(width)));
    lines.join("\n")
}

/// One rows-TSV parse failure, rendered as the Python owner rendered it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RowsTsvError(pub String);

impl std::fmt::Display for RowsTsvError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.write_str(&self.0)
    }
}

/// Parse the three-column rows TSV the CLI accepts.
///
/// Columns are `label`, `start_s`, `end_s`. Empty lines are skipped, matching
/// the Python reader, which also skips them before counting columns.
///
/// # Errors
///
/// Returns the exact malformed-row message the Python owner raised.
pub fn parse_rows_tsv(text: &str) -> Result<Vec<GanttRow>, RowsTsvError> {
    let mut rows = Vec::new();
    for (index, line) in split_text_lines(text).into_iter().enumerate() {
        let lineno = index + 1;
        if line.is_empty() {
            continue;
        }
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() != TSV_COLUMN_COUNT {
            return Err(RowsTsvError(format!(
                "malformed row {lineno}: expected 3 tab-delimited columns"
            )));
        }
        let (Some(start_s), Some(end_s)) = (python_int(parts[1]), python_int(parts[2])) else {
            return Err(RowsTsvError(format!(
                "malformed row {lineno}: start_s and end_s must be integers"
            )));
        };
        rows.push(GanttRow::new(parts[0], start_s, end_s));
    }
    Ok(rows)
}

/// Render the axis line: `0:00` under the first cell, the span under the last.
fn axis(label_width: usize, width: usize, span_label: &str) -> String {
    let track_start = label_width + 2;
    let track_end = track_start + width.saturating_sub(1);
    let mut characters = vec![' '; track_end + 1];
    place(&mut characters, track_start, "0:00");
    let right_start = track_start.max(
        track_end
            .saturating_sub(span_label.chars().count())
            .saturating_add(1),
    );
    place(&mut characters, right_start, span_label);
    characters
        .into_iter()
        .collect::<String>()
        .trim_end()
        .to_owned()
}

fn place(characters: &mut [char], start: usize, text: &str) {
    for (offset, character) in text.chars().enumerate() {
        let Some(position) = start.checked_add(offset) else {
            return;
        };
        let Some(slot) = characters.get_mut(position) else {
            return;
        };
        *slot = character;
    }
}

/// Place one whole-cell bar inside the track.
fn bar(start_s: i64, end_s: i64, window_start_s: i64, span: i64, width: usize) -> String {
    let rounded_start = scaled_column(start_s.saturating_sub(window_start_s).max(0), span, width);
    let rounded_end = scaled_column(end_s.saturating_sub(window_start_s).max(0), span, width);
    let start_column = rounded_start.min(width.saturating_sub(1));
    let end_column = rounded_end.max(start_column + 1).min(width);
    format!(
        "{}{}{}",
        " ".repeat(start_column),
        "█".repeat(end_column - start_column),
        " ".repeat(width - end_column)
    )
}

#[expect(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    reason = "the Python owner uses this IEEE-754 formula and clamps its integer result"
)]
fn scaled_column(value: i64, span: i64, width: usize) -> usize {
    let scaled = value as f64 * width as f64 / span as f64;
    let rounded = (scaled + 0.5) as i64;
    usize::try_from(rounded).unwrap_or(0).min(width)
}

fn pad_right(value: &str, width: usize) -> String {
    let padding = width.saturating_sub(value.chars().count());
    format!("{value}{}", " ".repeat(padding))
}

fn pad_left(value: &str, width: usize) -> String {
    let padding = width.saturating_sub(value.chars().count());
    format!("{}{value}", " ".repeat(padding))
}

#[cfg(test)]
mod tests {
    use super::{DEFAULT_WIDTH, GanttRow, format_mss, parse_rows_tsv, render_gantt};

    #[test]
    fn formats_axis_labels_as_minutes_and_seconds() {
        assert_eq!(format_mss(0), "0:00");
        assert_eq!(format_mss(61), "1:01");
        assert_eq!(format_mss(-5), "0:00");
    }

    #[test]
    fn drops_rows_that_do_not_overlap_the_window() {
        let rows = vec![GanttRow::new("late", 200, 300)];
        assert_eq!(render_gantt(0, 100, &rows, None), "");
    }

    #[test]
    fn renders_aligned_edges_and_only_track_glyphs() {
        let rows = vec![GanttRow::new("a", 0, 50), GanttRow::new("bb", 50, 100)];
        let chart = render_gantt(0, 100, &rows, Some(10));
        let lines: Vec<&str> = chart.lines().collect();
        assert_eq!(lines.len(), 5);
        assert_eq!(lines[1], "   ┌──────────┐");
        assert_eq!(lines[2], "a  │█████     │ 50s");
        assert_eq!(lines[3], "bb │     █████│ 50s");
        assert_eq!(lines[4], "   └──────────┘");
    }

    #[test]
    fn a_single_row_still_paints_one_cell() {
        let rows = vec![GanttRow::new("x", 0, 1)];
        let chart = render_gantt(0, 1000, &rows, Some(4));
        assert!(chart.contains("x │█   │ 1s"), "{chart}");
    }

    #[test]
    fn a_long_label_narrows_only_the_default_width() {
        let label = "l".repeat(100);
        let rows = vec![GanttRow::new(label.clone(), 0, 10)];
        let default = render_gantt(0, 10, &rows, None);
        let explicit = render_gantt(0, 10, &rows, Some(DEFAULT_WIDTH));
        assert!(default.contains(&"█".repeat(10)), "{default}");
        assert!(explicit.contains(&"█".repeat(56)), "{explicit}");
    }

    #[test]
    fn reads_three_column_rows_and_refuses_other_shapes() {
        let parsed = parse_rows_tsv("a\t0\t5\n\nb\t5\t9\n").expect("rows");
        assert_eq!(
            parsed,
            vec![GanttRow::new("a", 0, 5), GanttRow::new("b", 5, 9)]
        );
        assert_eq!(
            parse_rows_tsv("a\t0\n").unwrap_err().to_string(),
            "malformed row 1: expected 3 tab-delimited columns"
        );
        assert_eq!(
            parse_rows_tsv("a\tx\t5\n").unwrap_err().to_string(),
            "malformed row 1: start_s and end_s must be integers"
        );
    }
}
