//! The `/report-tokens` cost-over-time chart.
//!
//! This replaces the retired `plot-cost-over-time.py` matplotlib child. The
//! series is a per-day total cost, so the chart is a line with round markers
//! over a light grid, and it is rendered here rather than in a spawned
//! interpreter: larch's process policy has no arbitrary-script class, and the
//! program principle is to spawn only true external products.
//!
//! Two details of the retired child changed deliberately. The title separates
//! its label with a colon instead of an em dash, because larch's readability
//! style bans em dashes from user-facing output. And the x tick labels stay
//! horizontal, thinned to whatever fits, instead of matplotlib's rotated every
//! label.

use super::raster::{Canvas, Color, text_height, text_width};

/// Canvas width, matching matplotlib's 10-inch figure at 100 dots per inch.
const WIDTH: usize = 1000;
/// Canvas height, matching matplotlib's 4-inch figure at 100 dots per inch.
const HEIGHT: usize = 400;
/// Leftmost column of the plotting area, leaving room for the tick labels.
const PLOT_LEFT: i32 = 80;
/// Rightmost column of the plotting area.
const PLOT_RIGHT: i32 = 970;
/// Topmost row of the plotting area, leaving room for the title.
const PLOT_TOP: i32 = 56;
/// Bottom row of the plotting area, leaving room for the date labels.
const PLOT_BOTTOM: i32 = 336;
/// Scale of the title text.
const TITLE_SCALE: i32 = 2;
/// Scale of the axis and tick text.
const LABEL_SCALE: i32 = 1;
/// Radius of one plotted point's marker.
const MARKER_RADIUS: i32 = 3;
/// How many horizontal rules the value axis aims for.
const TICK_TARGET: f64 = 5.0;
/// Blank columns kept between two neighboring date labels.
const LABEL_GAP: i32 = 18;

/// Near-black used for the title, the labels, and the axis spines.
const INK: Color = [0x22, 0x22, 0x22];
/// The light rule color, matching matplotlib's grid at quarter alpha.
const GRID: Color = [0xDD, 0xDD, 0xDD];
/// Matplotlib's first line color, kept so the charts still look like larch's.
const SERIES: Color = [0x1F, 0x77, 0xB4];

/// One rendered chart: the file it should be written as, and its PNG bytes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CostPlot {
    /// Basename the caller writes the chart to.
    pub file_name: String,
    /// Encoded PNG bytes.
    pub png: Vec<u8>,
}

/// Round one plotted coordinate to the nearest device pixel.
#[allow(clippy::cast_possible_truncation)] // Plot coordinates are bounded by the canvas size.
const fn device(value: f64) -> i32 {
    value.round() as i32
}

/// Widen one count for the coordinate arithmetic.
#[allow(clippy::cast_precision_loss)] // A series holds far fewer points than f64 counts exactly.
const fn widen(value: usize) -> f64 {
    value as f64
}

/// Render one series as a cost-over-time PNG.
///
/// `points` are `(date, cost)` pairs in ascending date order. An empty series
/// still renders its frame, the way an empty matplotlib axes did.
#[must_use]
pub fn render_cost_plot(skill: &str, label: &str, points: &[(String, f64)]) -> CostPlot {
    let mut canvas = Canvas::new(WIDTH, HEIGHT);
    let title = format!("{skill} token cost over time: {label}");
    let (top, step) = value_axis(points);
    draw_frame(&mut canvas, &title);
    draw_value_axis(&mut canvas, top, step);
    draw_date_axis(&mut canvas, points);
    draw_series(&mut canvas, points, top);
    CostPlot {
        file_name: format!("larch-report-tokens-{}.png", file_slug(label)),
        png: canvas.into_png(),
    }
}

/// The lowercase hyphenated form of one series label.
fn file_slug(label: &str) -> String {
    let slug: String = label
        .chars()
        .map(|character| match character.to_ascii_lowercase() {
            safe @ ('a'..='z' | '0'..='9' | '.' | '_' | '-') => safe,
            _unsafe_character => '-',
        })
        .collect();
    if slug.is_empty() {
        "series".to_owned()
    } else {
        slug
    }
}

/// Draw the title, the value-axis caption, and the two axis spines.
fn draw_frame(canvas: &mut Canvas, title: &str) {
    let title_left =
        (i32::try_from(WIDTH).unwrap_or(i32::MAX) - text_width(title, TITLE_SCALE)) / 2;
    canvas.text((title_left.max(0), 16), title, TITLE_SCALE, INK);
    canvas.text((10, PLOT_TOP - 18), "USD", LABEL_SCALE, INK);
    canvas.line((PLOT_LEFT, PLOT_TOP), (PLOT_LEFT, PLOT_BOTTOM), INK);
    canvas.line((PLOT_LEFT, PLOT_BOTTOM), (PLOT_RIGHT, PLOT_BOTTOM), INK);
}

/// The value the top of the plotting area represents, and its tick step.
///
/// The axis always starts at zero, because these are costs, and it ends on a
/// round multiple of the step so every rule carries a short label.
fn value_axis(points: &[(String, f64)]) -> (f64, f64) {
    let highest = points
        .iter()
        .map(|(_date, cost)| *cost)
        .fold(0.0_f64, f64::max);
    if highest <= 0.0 {
        return (1.0, tick_step(1.0));
    }
    let step = tick_step(highest);
    ((highest / step).ceil() * step, step)
}

/// A round tick step near one fifth of the plotted range.
fn tick_step(highest: f64) -> f64 {
    let target = highest / TICK_TARGET;
    let base = 10.0_f64.powf(target.log10().floor());
    for multiple in [1.0, 2.0, 2.5, 5.0] {
        if target <= multiple * base {
            return multiple * base;
        }
    }
    base * 10.0
}

/// Draw the horizontal rules and their value labels.
fn draw_value_axis(canvas: &mut Canvas, top: f64, step: f64) {
    let count = device(top / step).max(1);
    for index in 0..=count {
        let value = step * f64::from(index);
        let y = value_row(value, top);
        canvas.line((PLOT_LEFT, y), (PLOT_RIGHT, y), GRID);
        canvas.line((PLOT_LEFT - 4, y), (PLOT_LEFT, y), INK);
        let text = format_value(value, step);
        let left = PLOT_LEFT - 8 - text_width(&text, LABEL_SCALE);
        canvas.text(
            (left, y - text_height(LABEL_SCALE) / 2),
            &text,
            LABEL_SCALE,
            INK,
        );
    }
}

/// Format one axis value with just enough decimals for its step.
fn format_value(value: f64, step: f64) -> String {
    let decimals = if step >= 1.0 {
        0
    } else if step >= 0.1 {
        1
    } else if step >= 0.01 {
        2
    } else {
        3
    };
    format!("{value:.decimals$}")
}

/// The device row one value sits on.
fn value_row(value: f64, top: f64) -> i32 {
    let span = f64::from(PLOT_BOTTOM - PLOT_TOP);
    device((value / top).mul_add(-span, f64::from(PLOT_BOTTOM)))
}

/// The device column one point index sits on.
fn point_column(index: usize, count: usize) -> i32 {
    let span = f64::from(PLOT_RIGHT - PLOT_LEFT);
    if count <= 1 {
        return device(f64::from(PLOT_LEFT) + span / 2.0);
    }
    device(f64::from(PLOT_LEFT) + span * widen(index) / widen(count - 1))
}

/// Draw the date ticks, thinned so neighboring labels never collide.
fn draw_date_axis(canvas: &mut Canvas, points: &[(String, f64)]) {
    let Some(widest) = points
        .iter()
        .map(|(date, _cost)| text_width(date, LABEL_SCALE))
        .max()
    else {
        return;
    };
    let per_label = (widest + LABEL_GAP).max(1);
    let fits = usize::try_from((PLOT_RIGHT - PLOT_LEFT) / per_label)
        .unwrap_or(1)
        .max(1);
    let stride = points.len().div_ceil(fits).max(1);
    for (index, (date, _cost)) in points.iter().enumerate().step_by(stride) {
        let x = point_column(index, points.len());
        canvas.line((x, PLOT_TOP), (x, PLOT_BOTTOM), GRID);
        canvas.line((x, PLOT_BOTTOM), (x, PLOT_BOTTOM + 4), INK);
        let label_width = text_width(date, LABEL_SCALE);
        let rightmost = (i32::try_from(WIDTH).unwrap_or(i32::MAX) - label_width).max(0);
        let left = (x - label_width / 2).clamp(0, rightmost);
        canvas.text((left, PLOT_BOTTOM + 10), date, LABEL_SCALE, INK);
    }
}

/// Draw the series line and its markers.
fn draw_series(canvas: &mut Canvas, points: &[(String, f64)], top: f64) {
    let mut previous: Option<(i32, i32)> = None;
    for (index, (_date, cost)) in points.iter().enumerate() {
        let current = (point_column(index, points.len()), value_row(*cost, top));
        if let Some(start) = previous {
            canvas.line(start, current, SERIES);
        }
        canvas.disc(current, MARKER_RADIUS, SERIES);
        previous = Some(current);
    }
}
