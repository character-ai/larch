//! Pure aggregation and rendering for the repository-size developer report.

const CATEGORY_WIDTH: usize = 37;
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
    /// Python tests named `test_*.py`.
    PythonTests,
    /// Markdown files.
    Markdown,
}

impl RepoSizeCategory {
    const ALL: [Self; 5] = [
        Self::BashScripts,
        Self::BashTests,
        Self::PythonCode,
        Self::PythonTests,
        Self::Markdown,
    ];

    const fn index(self) -> usize {
        match self {
            Self::BashScripts => 0,
            Self::BashTests => 1,
            Self::PythonCode => 2,
            Self::PythonTests => 3,
            Self::Markdown => 4,
        }
    }

    const fn label(self) -> &'static str {
        match self {
            Self::BashScripts => "Bash scripts (runtime, non-test *.sh)",
            Self::BashTests => "Bash tests (test-*.sh)",
            Self::PythonCode => "Python code (non-test *.py)",
            Self::PythonTests => "Python tests (test_*.py)",
            Self::Markdown => "All Markdown (*.md)",
        }
    }
}

/// Identify the fixed line-count category for one Git-relative byte path.
#[must_use]
pub fn line_count_category(path: &[u8]) -> Option<RepoSizeCategory> {
    if LINE_COUNT_EXCLUDED_PREFIXES
        .iter()
        .any(|prefix| path.starts_with(prefix))
    {
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
        return Some(if basename.starts_with(b"test_") {
            RepoSizeCategory::PythonTests
        } else {
            RepoSizeCategory::PythonCode
        });
    }
    (suffix == b".md").then_some(RepoSizeCategory::Markdown)
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

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
struct CategoryCounts {
    files: u64,
    lines: u64,
}

/// Aggregated values for the fixed repository-size report.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepoSizeReport {
    categories: [CategoryCounts; 5],
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

    /// Render the report with the Python owner's fixed text layout.
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
    use super::{RepoSizeCategory, RepoSizeReport, count_newlines, line_count_category};

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
            line_count_category(b"docs/guide.md"),
            Some(RepoSizeCategory::Markdown)
        );
        assert_eq!(line_count_category(b"larch-logs/run.md"), None);
        assert_eq!(line_count_category(b"node_modules/pkg/readme.md"), None);
        assert_eq!(line_count_category(b"docs/.md"), None);
    }

    #[test]
    fn renders_zero_totals_like_the_python_owner() {
        let report = RepoSizeReport::default();
        assert_eq!(count_newlines(b"one\ntwo\n"), 2);
        assert!(report.render().contains("( 0.0% of repo)"));
        assert!(report.render().contains("( 0.0% of run-logs)"));
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
