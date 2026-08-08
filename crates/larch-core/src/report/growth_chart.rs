//! Compact ASCII cumulative-growth chart over bucketed issue counts.
//!
//! Ports `larch.rendering.render_chart`. A row's key is arbitrary text, not one
//! character, so canvas cells hold strings: a two-character key widens its row
//! exactly as the Python owner's `"".join(cells)` did.

use crate::{
    report::token_cost::python_round,
    text::{python_int, split_text_lines, trim_python_whitespace},
};

/// Body the renderer returns when there is nothing to plot.
pub const EMPTY_CHART: &str = "No growth data available.";
/// Smallest column count the TSV grammar accepts on a data row.
const MIN_ROW_COLUMNS: usize = 3;

/// One plotted series: its canvas key, its legend label, and its bucket values.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GrowthRow {
    /// Glyph text painted into the canvas.
    pub key: String,
    /// Legend text.
    pub label: String,
    /// Cumulative value per bucket, in header order.
    pub values: Vec<i64>,
}

/// One non-integer bucket value, reported with the text that failed to parse.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GrowthValueError(pub String);

impl std::fmt::Display for GrowthValueError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            formatter,
            "invalid literal for int() with base 10: '{}'",
            self.0
        )
    }
}

/// Parse the header bucket labels and the data rows from TSV text.
///
/// Blank and whitespace-only lines are dropped before the header is taken, and
/// a data row with fewer than three columns is skipped, matching the Python
/// owner. An empty bucket cell reads as `0`.
///
/// # Errors
///
/// Returns the offending text when a bucket value is not an integer. The Python
/// owner raised `ValueError` here and exited on the traceback.
pub fn parse_tsv(text: &str) -> Result<(Vec<String>, Vec<GrowthRow>), GrowthValueError> {
    let lines: Vec<&str> = split_text_lines(text)
        .into_iter()
        .filter(|line| !trim_python_whitespace(line).is_empty())
        .map(|line| line.trim_end_matches('\n'))
        .collect();
    let Some((header, body)) = lines.split_first() else {
        return Ok((Vec::new(), Vec::new()));
    };
    let buckets: Vec<String> = header
        .split('\t')
        .skip(2)
        .map(std::borrow::ToOwned::to_owned)
        .collect();
    let mut rows = Vec::new();
    for line in body {
        let parts: Vec<&str> = line.split('\t').collect();
        if parts.len() < MIN_ROW_COLUMNS {
            continue;
        }
        let mut values = Vec::with_capacity(parts.len() - 2);
        for value in &parts[2..] {
            let parsed = if value.is_empty() {
                Some(0)
            } else {
                python_int(value)
            };
            values.push(parsed.ok_or_else(|| GrowthValueError((*value).to_owned()))?);
        }
        rows.push(GrowthRow {
            key: parts[0].to_owned(),
            label: parts[1].to_owned(),
            values,
        });
    }
    Ok((buckets, rows))
}

/// Render the cumulative-growth chart body without a trailing newline.
#[must_use]
pub fn render_chart(buckets: &[String], rows: &[GrowthRow]) -> String {
    if rows.is_empty() || buckets.is_empty() {
        return EMPTY_CHART.to_owned();
    }
    let width = buckets.len();
    let height = rows.len();
    let max_final = rows
        .iter()
        .map(|row| row.values.last().copied().unwrap_or(0))
        .max()
        .unwrap_or(0)
        .max(1);
    let mut canvas: Vec<Vec<&str>> = vec![vec!["."; width]; height];
    for row in rows {
        for (column, value) in row.values.iter().take(width).enumerate() {
            if *value <= 0 {
                continue;
            }
            let target = height - 1 - scaled_row(*value, max_final, height);
            let existing = canvas[target][column];
            canvas[target][column] = if existing == "." || existing == row.key {
                row.key.as_str()
            } else {
                "*"
            };
        }
    }

    let mut output = vec![
        "Cumulative growth chart".to_owned(),
        format!(
            "Buckets: {} -> {} ({} buckets)",
            buckets[0],
            buckets[width - 1],
            width
        ),
    ];
    output.extend(canvas.into_iter().map(|line| line.concat()));
    output.push("Legend:".to_owned());
    for row in rows {
        let final_value = row.values.last().copied().unwrap_or(0);
        output.push(format!("  {}: {} ({final_value})", row.key, row.label));
    }
    output.join("\n")
}

/// Scale one value onto the canvas rows, clamped to the plotted range.
#[expect(
    clippy::cast_precision_loss,
    clippy::cast_possible_truncation,
    clippy::cast_sign_loss,
    reason = "the Python owner divides the same integers as floats and rounds half to even"
)]
fn scaled_row(value: i64, max_final: i64, height: usize) -> usize {
    let span = (height - 1) as f64;
    let rounded = python_round(value as f64 / max_final as f64 * span, 0);
    if rounded <= 0.0 {
        return 0;
    }
    (rounded as usize).min(height - 1)
}

#[cfg(test)]
mod tests {
    use super::{EMPTY_CHART, GrowthRow, parse_tsv, render_chart};

    fn buckets(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| (*value).to_owned()).collect()
    }

    #[test]
    fn an_empty_input_reports_no_data() {
        assert_eq!(parse_tsv("").expect("parse"), (Vec::new(), Vec::new()));
        assert_eq!(render_chart(&[], &[]), EMPTY_CHART);
        assert_eq!(render_chart(&buckets(&["2026-01"]), &[]), EMPTY_CHART);
    }

    #[test]
    fn parses_header_buckets_and_skips_short_rows() {
        let (found, rows) =
            parse_tsv("key\tlabel\t2026-01\t2026-02\nA\tBug\t1\t3\nshort\trow\n").expect("parse");
        assert_eq!(found, buckets(&["2026-01", "2026-02"]));
        assert_eq!(
            rows,
            vec![GrowthRow {
                key: "A".to_owned(),
                label: "Bug".to_owned(),
                values: vec![1, 3],
            }]
        );
    }

    #[test]
    fn an_empty_bucket_cell_reads_as_zero_and_a_word_refuses() {
        let (_buckets, rows) = parse_tsv("k\tl\tb\nA\tBug\t\n").expect("parse");
        assert_eq!(rows[0].values, vec![0]);
        assert_eq!(
            parse_tsv("k\tl\tb\nA\tBug\tx\n").unwrap_err().to_string(),
            "invalid literal for int() with base 10: 'x'"
        );
    }

    #[test]
    fn a_single_series_plots_its_own_key() {
        let rows = vec![GrowthRow {
            key: "A".to_owned(),
            label: "Bug".to_owned(),
            values: vec![1],
        }];
        assert_eq!(
            render_chart(&buckets(&["2026-01"]), &rows),
            "Cumulative growth chart\nBuckets: 2026-01 -> 2026-01 (1 buckets)\nA\nLegend:\n  A: Bug (1)"
        );
    }

    #[test]
    fn two_series_sharing_a_cell_collapse_to_a_star() {
        let rows = vec![
            GrowthRow {
                key: "A".to_owned(),
                label: "Bug".to_owned(),
                values: vec![4],
            },
            GrowthRow {
                key: "B".to_owned(),
                label: "Task".to_owned(),
                values: vec![4],
            },
        ];
        let chart = render_chart(&buckets(&["2026-01"]), &rows);
        assert!(chart.contains("\n*\n."), "{chart}");
    }

    #[test]
    fn a_multi_character_key_widens_its_own_row() {
        let rows = vec![GrowthRow {
            key: "AB".to_owned(),
            label: "Bug".to_owned(),
            values: vec![1, 0],
        }];
        let chart = render_chart(&buckets(&["a", "b"]), &rows);
        assert!(chart.contains("\nAB.\n"), "{chart}");
    }
}
