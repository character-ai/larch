//! Token cost model, pricing tables, and per-run cost aggregation.
//!
//! Library parity for Python `larch.report.report_tokens_cost` and the pricing
//! re-exports of `larch.report.tokens`. No command changes owner here: Python
//! keeps `token cost`, `token render-cost-line`, and `report-tokens analyze`
//! until their cutover leaves move.
//!
//! # Pricing data
//!
//! [`RATE_TABLE`] is the single reviewed source of per-1M-token rates. To
//! update it: change the row, cite the vendor price page beside it, regenerate
//! the recorded Python fixtures under
//! `crates/larch-core/tests/fixtures/token_cost/`, and review the changed
//! numbers as a pricing change rather than a code detail.
//!
//! Every live Rust pricing path reads this table, including the phase-detail
//! cost line in `larch_adapters`. The one deliberate exception is the frozen
//! Cursor correction sweep in `larch-cli`'s run-log migration commands, which
//! keeps its own historical constants because it must reproduce numbers that
//! were already published.
//!
//! # Loud substitution
//!
//! A model with no rate row of its own is never costed as zero: another row
//! prices its tokens, and every such substitution, including a display bucket
//! that folds one model onto another model's rate, is recorded as
//! [`TokenObservationKind::UnpricedModel`] so a caller can surface it.
//!
//! # Command surface
//!
//! This layer parses only the pricing flags. Help output, usage text, exit
//! codes, and the stderr warning belong to the CLI leaf that later takes
//! `token cost` and `token render-cost-line` from Python.
//!
//! # Rounding
//!
//! Every emitted number rounds the way Python's `round(value, digits)` does:
//! correct decimal rounding of the exact binary value with ties to even. See
//! [`python_round`].

use super::token_scan::{
    TOKEN_VENDORS, TokenObservationKind, TokenObservations, TokenRunRecord, TokenVendor,
    VendorTotals, effective_vendor_total, safe_int,
};
use crate::text::unsigned_integer;
use crate::vendor_model::{
    CLAUDE_FABLE_5_MODEL, CLAUDE_GLM_5_2_MODEL, CLAUDE_HAIKU_4_5_MODEL, CLAUDE_OPUS_4_8_MODEL,
    CLAUDE_SONNET_4_6_MODEL, CODEX_DEFAULT_MODEL, CODEX_REVIEW_MODEL_DEFAULT, CURSOR_DEFAULT_MODEL,
    CURSOR_GROK_4_6_HIGH_MODEL, canonicalize_glm_main_model,
};
use serde_json::{Map, Value};
use std::collections::BTreeMap;
use std::{error::Error, fmt};

/// Warning a pricing entrypoint emits when only blended counts were supplied.
pub const BLENDED_FALLBACK_WARNING: &str = "token cost: WARNING: per-bucket counts unavailable; using blended rate (may overstate by ~3-10x)";

/// Teams-plan per-token surcharge applied to pinned-model Cursor requests.
///
/// Source: `cursor.com/docs/account/teams/pricing`, "Cursor Token Rate
/// $0.25/1M tokens". It applies to input, cache-read, and output for
/// `composer-2.5` invocations, and `LARCH_CURSOR_TEAMS_SURCHARGE_PER_M`
/// overrides it.
pub const CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M: f64 = 0.25;

/// Published Cursor `composer-2.5` list rates before the Teams surcharge.
///
/// The table stores the surcharged row; this row exists because the surcharge
/// is environment-overridable, so a caller that resolves rates from the
/// environment has to add its own surcharge to these published numbers.
pub static CURSOR_COMPOSER_BASE_RATES: RateRow = RateRow::external(0.50, 0.20, 2.50);

/// Codex model ids that price at the Codex-mini display rate.
///
/// `gpt-5.4-mini` is the historical id and `gpt-5.6-luna` is the live pin.
/// Every other Codex model, including a model-less legacy row, prices at the
/// default bucket.
pub const CODEX_MINI_MODELS: [&str; 2] = ["gpt-5.4-mini", CODEX_REVIEW_MODEL_DEFAULT];

/// Cursor model ids that price at the grok rate.
///
/// The two explicitly named legacy aliases preserve historical ledger pricing;
/// they are never active routing defaults. Membership is exact: a near-miss id
/// prices at the composer rate.
const LEGACY_CURSOR_GROK_4_5_HIGH_MODEL: &str = "cursor-grok-4.5-high";
const LEGACY_GROK_4_5_MODEL: &str = "grok-4.5";
pub const CURSOR_GROK_MODELS: [&str; 3] = [
    CURSOR_GROK_4_6_HIGH_MODEL,
    LEGACY_CURSOR_GROK_4_5_HIGH_MODEL,
    LEGACY_GROK_4_5_MODEL,
];

/// One per-1M-token rate row.
///
/// A lane with no cache-creation tiers leaves both at zero; only a
/// Claude-shaped lane reads them.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct RateRow {
    /// Uncached input rate per 1M tokens.
    pub input: f64,
    /// Cache-read rate per 1M tokens, spelled cached input for Codex.
    pub cache_read: f64,
    /// Five-minute cache-creation rate per 1M tokens.
    pub cache_create_5m: f64,
    /// One-hour cache-creation rate per 1M tokens.
    pub cache_create_1h: f64,
    /// Output rate per 1M tokens.
    pub output: f64,
}

impl RateRow {
    /// Build a row for a lane with no cache-creation tiers.
    const fn external(input: f64, cache_read: f64, output: f64) -> Self {
        Self {
            input,
            cache_read,
            cache_create_5m: 0.0,
            cache_create_1h: 0.0,
            output,
        }
    }

    /// Build a Claude-shaped row with both cache-creation tiers.
    const fn claude(
        input: f64,
        cache_read: f64,
        five_minute: f64,
        one_hour: f64,
        output: f64,
    ) -> Self {
        Self {
            input,
            cache_read,
            cache_create_5m: five_minute,
            cache_create_1h: one_hour,
            output,
        }
    }
}

/// The single reviewed pricing source, verified as of 2026-08-13.
///
/// Sources: `OpenAI` GPT-5.6 family and historical Codex model pricing; the
/// Cursor [Models & Pricing](https://cursor.com/docs/models-and-pricing)
/// `composer-2.5` and Grok 4.6 rows plus the
/// Teams surcharge; Anthropic Claude Opus, Sonnet, Haiku, and Fable list-price buckets; and the
/// Z.ai GLM-5.2 main-agent rates, whose cache-creation tiers are unused.
pub static RATE_TABLE: [(TokenVendor, &str, RateRow); 12] = [
    (
        TokenVendor::Codex,
        CODEX_DEFAULT_MODEL,
        RateRow::external(5.00, 0.50, 30.00),
    ),
    (
        TokenVendor::Codex,
        "gpt-5.6-terra",
        RateRow::external(2.50, 0.25, 15.00),
    ),
    (
        TokenVendor::Codex,
        CODEX_REVIEW_MODEL_DEFAULT,
        RateRow::external(1.00, 0.10, 6.00),
    ),
    (
        TokenVendor::Codex,
        "gpt-5.5",
        RateRow::external(5.00, 0.50, 30.00),
    ),
    (
        TokenVendor::Codex,
        "gpt-5.4-mini",
        RateRow::external(0.75, 0.075, 4.50),
    ),
    (
        TokenVendor::Cursor,
        CURSOR_DEFAULT_MODEL,
        RateRow::external(
            CURSOR_COMPOSER_BASE_RATES.input + CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M,
            CURSOR_COMPOSER_BASE_RATES.cache_read + CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M,
            CURSOR_COMPOSER_BASE_RATES.output + CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M,
        ),
    ),
    (
        TokenVendor::Cursor,
        CURSOR_GROK_4_6_HIGH_MODEL,
        RateRow::external(2.00, 0.50, 6.00),
    ),
    (
        TokenVendor::Claude,
        CLAUDE_OPUS_4_8_MODEL,
        RateRow::claude(5.00, 0.50, 6.25, 10.00, 25.00),
    ),
    (
        TokenVendor::Claude,
        CLAUDE_SONNET_4_6_MODEL,
        RateRow::claude(3.00, 0.30, 3.75, 6.00, 15.00),
    ),
    (
        TokenVendor::Claude,
        CLAUDE_HAIKU_4_5_MODEL,
        RateRow::claude(1.00, 0.10, 1.25, 2.00, 5.00),
    ),
    (
        TokenVendor::Claude,
        CLAUDE_FABLE_5_MODEL,
        RateRow::claude(10.00, 1.00, 12.50, 20.00, 50.00),
    ),
    (
        TokenVendor::Claude,
        CLAUDE_GLM_5_2_MODEL,
        RateRow::claude(1.40, 0.26, 0.00, 0.00, 4.40),
    ),
];

/// Input, cache-read, and output weights that blend a row into one rate.
const BLENDED_FLEET_MIX: (f64, f64, f64) = (0.07, 0.92, 0.01);
/// Blended Claude rate used when only an aggregate token count is known.
const DEFAULT_CLAUDE_BLENDED_PER_M: f64 = 0.80;

/// Return the model a lane falls back to when the recorded id has no row.
const fn default_vendor_model(vendor: TokenVendor) -> &'static str {
    match vendor {
        TokenVendor::Codex => CODEX_DEFAULT_MODEL,
        TokenVendor::Cursor => CURSOR_DEFAULT_MODEL,
        TokenVendor::Claude | TokenVendor::ClaudeSub => CLAUDE_OPUS_4_8_MODEL,
    }
}

/// Look up an exact `(vendor, model)` row, with no fallback.
///
/// A `claude_sub` lane shares the Claude table because it is priced at Claude
/// rates under a distinct report key.
#[must_use]
pub fn exact_rate_row(vendor: TokenVendor, model: &str) -> Option<RateRow> {
    let lane = if matches!(vendor, TokenVendor::ClaudeSub) {
        TokenVendor::Claude
    } else {
        vendor
    };
    RATE_TABLE
        .iter()
        .find(|(row_vendor, row_model, _row)| *row_vendor == lane && *row_model == model)
        .map(|(_vendor, _model, row)| *row)
}

/// Return the row a lane falls back to, which always exists.
fn default_rate_row(vendor: TokenVendor) -> RateRow {
    exact_rate_row(vendor, default_vendor_model(vendor))
        .expect("every lane default model has a rate row")
}

/// Record a model whose tokens priced at another model's row.
///
/// The substituted row still prices those tokens, so no count is lost; the
/// observation exists so the substitution cannot pass unseen. A blank model was
/// never recorded in the first place and reports nothing.
fn note_priced_as(
    vendor: TokenVendor,
    model: &str,
    applied: &str,
    observations: &mut TokenObservations,
) {
    if !model.is_empty() && model != applied {
        observations.record(TokenObservationKind::UnpricedModel, vendor.as_str(), model);
    }
}

/// Resolve the per-1M rate row for `(vendor, model)`.
///
/// An empty or unknown model falls back to the lane's default row, so a
/// model-less legacy ledger row prices at the vendor default instead of zero.
/// An unknown non-empty model is recorded through `observations`.
#[must_use]
pub fn rate_row(vendor: TokenVendor, model: &str, observations: &mut TokenObservations) -> RateRow {
    exact_rate_row(vendor, model).unwrap_or_else(|| {
        note_priced_as(vendor, model, default_vendor_model(vendor), observations);
        default_rate_row(vendor)
    })
}

/// Blend a lane's default row into one aggregate rate.
#[expect(
    clippy::suboptimal_flops,
    reason = "a fused multiply-add would drop the intermediate rounding Python performed"
)]
fn blended_default(vendor: TokenVendor) -> f64 {
    let row = default_rate_row(vendor);
    row.input * BLENDED_FLEET_MIX.0
        + row.cache_read * BLENDED_FLEET_MIX.1
        + row.output * BLENDED_FLEET_MIX.2
}

/// Effective per-1M display rates after environment overrides.
///
/// Ports Python `DisplayRates`. Every field is dollars per million tokens.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct TokenRates {
    /// Main-agent Claude uncached input.
    pub claude_input: f64,
    /// Main-agent Claude cache read.
    pub claude_cache_read: f64,
    /// Main-agent Claude five-minute cache creation.
    pub claude_cache_create_5m: f64,
    /// Main-agent Claude one-hour cache creation.
    pub claude_cache_create_1h: f64,
    /// Main-agent Claude output.
    pub claude_output: f64,
    /// Codex default-bucket uncached input.
    pub codex_input: f64,
    /// Codex default-bucket cached input.
    pub codex_cached_input: f64,
    /// Codex default-bucket output.
    pub codex_output: f64,
    /// Codex mini-bucket uncached input.
    pub codex_mini_input: f64,
    /// Codex mini-bucket cached input.
    pub codex_mini_cached_input: f64,
    /// Codex mini-bucket output.
    pub codex_mini_output: f64,
    /// Cursor composer uncached input.
    pub cursor_input: f64,
    /// Cursor composer cache read.
    pub cursor_cache_read: f64,
    /// Cursor composer output.
    pub cursor_output: f64,
    /// Blended Claude rate for aggregate-only records.
    pub claude_blended: f64,
    /// Blended Codex rate for aggregate-only records.
    pub codex_blended: f64,
    /// Blended Cursor rate for aggregate-only records.
    pub cursor_blended: f64,
    /// Cursor grok uncached input.
    pub cursor_grok_input: f64,
    /// Cursor grok cache read.
    pub cursor_grok_cache_read: f64,
    /// Cursor grok output.
    pub cursor_grok_output: f64,
}

/// Read the first positive float among `names`, or `default`.
///
/// A blank, unparseable, or non-positive value is skipped, matching the Python
/// owner's tolerant precedence chain.
fn env_rate(env: &BTreeMap<String, String>, names: &[&str], default: f64) -> f64 {
    for name in names {
        let Some(raw) = env.get(*name) else { continue };
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            continue;
        }
        let Ok(value) = trimmed.parse::<f64>() else {
            continue;
        };
        if value > 0.0 {
            return value;
        }
    }
    default
}

/// Apply the Claude bucket overrides to one table row.
fn claude_env_row(env: &BTreeMap<String, String>, row: RateRow) -> RateRow {
    RateRow::claude(
        env_rate(
            env,
            &["LARCH_CLAUDE_INPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_INPUT"],
            row.input,
        ),
        env_rate(
            env,
            &[
                "LARCH_CLAUDE_CACHE_READ_RATE_PER_M",
                "LARCH_RATE_CLAUDE_CACHE_READ",
            ],
            row.cache_read,
        ),
        env_rate(
            env,
            &[
                "LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M",
                "LARCH_RATE_CLAUDE_CACHE_CREATE",
                "LARCH_RATE_CLAUDE_CACHE_CREATE_5M",
            ],
            row.cache_create_5m,
        ),
        env_rate(
            env,
            &[
                "LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M",
                "LARCH_RATE_CLAUDE_CACHE_CREATE_1H",
            ],
            row.cache_create_1h,
        ),
        env_rate(
            env,
            &["LARCH_CLAUDE_OUTPUT_RATE_PER_M", "LARCH_RATE_CLAUDE_OUTPUT"],
            row.output,
        ),
    )
}

/// Apply the Codex default or mini bucket overrides to one table row.
fn codex_env_row(env: &BTreeMap<String, String>, row: RateRow, mini: bool) -> RateRow {
    let (input, cached_input, output): (&[&str], &[&str], &[&str]) = if mini {
        (
            &[
                "LARCH_CODEX_MINI_INPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_MINI_INPUT",
            ],
            &[
                "LARCH_CODEX_MINI_CACHED_INPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_MINI_CACHE_READ",
                "LARCH_RATE_CODEX_MINI_CACHED_INPUT",
            ],
            &[
                "LARCH_CODEX_MINI_OUTPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_MINI_OUTPUT",
            ],
        )
    } else {
        (
            &["LARCH_CODEX_INPUT_RATE_PER_M", "LARCH_RATE_CODEX_INPUT"],
            &[
                "LARCH_CODEX_CACHED_INPUT_RATE_PER_M",
                "LARCH_RATE_CODEX_CACHE_READ",
                "LARCH_RATE_CODEX_CACHED_INPUT",
            ],
            &["LARCH_CODEX_OUTPUT_RATE_PER_M", "LARCH_RATE_CODEX_OUTPUT"],
        )
    };
    RateRow::external(
        env_rate(env, input, row.input),
        env_rate(env, cached_input, row.cache_read),
        env_rate(env, output, row.output),
    )
}

/// Apply the Cursor composer overrides to the surcharged base rates.
fn cursor_env_row(env: &BTreeMap<String, String>) -> RateRow {
    let surcharge = env_rate(
        env,
        &["LARCH_CURSOR_TEAMS_SURCHARGE_PER_M"],
        CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M,
    );
    RateRow::external(
        env_rate(
            env,
            &["LARCH_CURSOR_INPUT_RATE_PER_M", "LARCH_RATE_CURSOR_INPUT"],
            CURSOR_COMPOSER_BASE_RATES.input + surcharge,
        ),
        env_rate(
            env,
            &[
                "LARCH_CURSOR_CACHE_READ_RATE_PER_M",
                "LARCH_RATE_CURSOR_CACHE_READ",
            ],
            CURSOR_COMPOSER_BASE_RATES.cache_read + surcharge,
        ),
        env_rate(
            env,
            &["LARCH_CURSOR_OUTPUT_RATE_PER_M", "LARCH_RATE_CURSOR_OUTPUT"],
            CURSOR_COMPOSER_BASE_RATES.output + surcharge,
        ),
    )
}

/// Apply the Cursor grok overrides to one table row.
fn cursor_grok_env_row(env: &BTreeMap<String, String>, row: RateRow) -> RateRow {
    RateRow::external(
        env_rate(env, &["LARCH_CURSOR_GROK_INPUT_RATE_PER_M"], row.input),
        env_rate(
            env,
            &["LARCH_CURSOR_GROK_CACHE_READ_RATE_PER_M"],
            row.cache_read,
        ),
        env_rate(env, &["LARCH_CURSOR_GROK_OUTPUT_RATE_PER_M"], row.output),
    )
}

/// Resolve effective display rates for one main-agent model.
///
/// Only the GLM main-agent `[1m]` alias is canonicalized before lookup; a
/// subprocess lane prices through [`exact_rate_row`] directly. An unknown
/// `claude_model` falls back to the Opus row and is recorded through
/// `observations`.
#[must_use]
pub fn display_rates(
    env: &BTreeMap<String, String>,
    claude_model: &str,
    observations: &mut TokenObservations,
) -> TokenRates {
    let claude = claude_env_row(
        env,
        rate_row(
            TokenVendor::Claude,
            canonicalize_glm_main_model(claude_model),
            observations,
        ),
    );
    let codex = codex_env_row(env, default_rate_row(TokenVendor::Codex), false);
    let codex_mini = codex_env_row(
        env,
        rate_row(TokenVendor::Codex, CODEX_REVIEW_MODEL_DEFAULT, observations),
        true,
    );
    let cursor = cursor_env_row(env);
    let cursor_grok = cursor_grok_env_row(
        env,
        rate_row(
            TokenVendor::Cursor,
            CURSOR_GROK_4_6_HIGH_MODEL,
            observations,
        ),
    );
    TokenRates {
        claude_input: claude.input,
        claude_cache_read: claude.cache_read,
        claude_cache_create_5m: claude.cache_create_5m,
        claude_cache_create_1h: claude.cache_create_1h,
        claude_output: claude.output,
        codex_input: codex.input,
        codex_cached_input: codex.cache_read,
        codex_output: codex.output,
        codex_mini_input: codex_mini.input,
        codex_mini_cached_input: codex_mini.cache_read,
        codex_mini_output: codex_mini.output,
        cursor_input: cursor.input,
        cursor_cache_read: cursor.cache_read,
        cursor_output: cursor.output,
        claude_blended: env_rate(
            env,
            &[
                "LARCH_CLAUDE_RATE_PER_M",
                "LARCH_TOKEN_RATE_PER_M",
                "LARCH_RATE_CLAUDE_AGGREGATE",
            ],
            DEFAULT_CLAUDE_BLENDED_PER_M,
        ),
        codex_blended: env_rate(
            env,
            &["LARCH_CODEX_RATE_PER_M", "LARCH_RATE_CODEX_AGGREGATE"],
            blended_default(TokenVendor::Codex),
        ),
        cursor_blended: env_rate(
            env,
            &["LARCH_CURSOR_RATE_PER_M", "LARCH_RATE_CURSOR_AGGREGATE"],
            blended_default(TokenVendor::Cursor),
        ),
        cursor_grok_input: cursor_grok.input,
        cursor_grok_cache_read: cursor_grok.cache_read,
        cursor_grok_output: cursor_grok.output,
    }
}

/// Round the way Python's `round(value, digits)` does.
///
/// Python rounds the exact binary value to `digits` decimals with ties to even,
/// then returns the nearest double. Rust's fixed-precision formatting performs
/// the same exact-value rounding, so formatting and reparsing reproduces it.
#[must_use]
pub fn python_round(value: f64, digits: usize) -> f64 {
    format!("{value:.digits$}").parse::<f64>().unwrap_or(value)
}

/// Cost of one bucket, rounded to six decimals like the Python owner.
fn cost_bucket(tokens: i64, rate: f64) -> f64 {
    if tokens <= 0 {
        return 0.0;
    }
    python_round(tokens_in_millions(tokens) * rate, 6)
}

/// Cost of an aggregate-only count, rounded to two decimals.
fn cost_blend(tokens: i64, rate: f64) -> f64 {
    if tokens <= 0 {
        return 0.0;
    }
    python_round(tokens_in_millions(tokens) * rate, 2)
}

#[expect(
    clippy::cast_precision_loss,
    reason = "Python divided the same integer by 1e6 as a float"
)]
fn tokens_in_millions(tokens: i64) -> f64 {
    tokens as f64 / 1_000_000.0
}

/// Format a dollar amount with two decimals.
#[must_use]
pub fn format_money(value: f64) -> String {
    format!("{value:.2}")
}

/// Claude-shaped per-bucket counts for one lane.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ClaudeCounts {
    /// Uncached input tokens.
    pub input: i64,
    /// Cache-read tokens.
    pub cache_read: i64,
    /// Five-minute cache-creation tokens.
    pub cache_create_5m: i64,
    /// One-hour cache-creation tokens.
    pub cache_create_1h: i64,
    /// Output tokens.
    pub output: i64,
}

impl ClaudeCounts {
    /// Sum every component.
    #[must_use]
    pub const fn total(&self) -> i64 {
        self.input + self.cache_read + self.cache_create_5m + self.cache_create_1h + self.output
    }

    const fn is_present(&self) -> bool {
        self.input > 0
            || self.cache_read > 0
            || self.cache_create_5m > 0
            || self.cache_create_1h > 0
            || self.output > 0
    }

    const fn is_zero(&self) -> bool {
        self.input == 0
            && self.cache_read == 0
            && self.cache_create_5m == 0
            && self.cache_create_1h == 0
            && self.output == 0
    }

    const fn has_negative(&self) -> bool {
        self.input < 0
            || self.cache_read < 0
            || self.cache_create_5m < 0
            || self.cache_create_1h < 0
            || self.output < 0
    }

    fn cost(&self, row: RateRow) -> f64 {
        python_round(
            cost_bucket(self.input, row.input)
                + cost_bucket(self.cache_read, row.cache_read)
                + cost_bucket(self.cache_create_5m, row.cache_create_5m)
                + cost_bucket(self.cache_create_1h, row.cache_create_1h)
                + cost_bucket(self.output, row.output),
            2,
        )
    }

    /// Read one Claude-shaped bucket, folding legacy cache creation into 5m.
    pub(super) fn from_bucket(bucket: &Map<String, Value>) -> Self {
        let legacy = safe_int(bucket.get("cache_create"), 0);
        let mut five_minute = safe_int(bucket.get("cache_create_5m"), 0);
        let one_hour = safe_int(bucket.get("cache_create_1h"), 0);
        if legacy > 0 && five_minute == 0 && one_hour == 0 {
            five_minute = legacy;
        }
        Self {
            input: safe_int(bucket.get("input"), 0),
            cache_read: safe_int(bucket.get("cache_read"), 0),
            cache_create_5m: five_minute,
            cache_create_1h: one_hour,
            output: safe_int(bucket.get("output"), 0),
        }
    }

    pub(super) const fn add(&mut self, other: Self) {
        self.input += other.input;
        self.cache_read += other.cache_read;
        self.cache_create_5m += other.cache_create_5m;
        self.cache_create_1h += other.cache_create_1h;
        self.output += other.output;
    }

    const fn slot(&mut self, field: &str) -> Option<&mut i64> {
        match field.as_bytes() {
            b"input" => Some(&mut self.input),
            b"cache-read" => Some(&mut self.cache_read),
            b"cache-write-5m" => Some(&mut self.cache_create_5m),
            b"cache-write-1h" => Some(&mut self.cache_create_1h),
            b"output" => Some(&mut self.output),
            _unknown => None,
        }
    }
}

/// Codex-shaped per-bucket counts for one display bucket.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct CodexCounts {
    /// Uncached input tokens.
    pub input: i64,
    /// Cached input tokens.
    pub cached_input: i64,
    /// Output tokens.
    pub output: i64,
}

impl CodexCounts {
    /// Read one Codex-shaped report bucket.
    pub(super) fn from_bucket(bucket: &Map<String, Value>) -> Self {
        Self {
            input: safe_int(bucket.get("input"), 0),
            cached_input: safe_int(bucket.get("cached_input"), 0),
            output: safe_int(bucket.get("output"), 0),
        }
    }

    /// Accumulate one per-model bucket into this display bucket.
    pub(super) const fn add(&mut self, other: Self) {
        self.input += other.input;
        self.cached_input += other.cached_input;
        self.output += other.output;
    }

    /// Sum every component.
    #[must_use]
    pub const fn total(&self) -> i64 {
        self.input + self.cached_input + self.output
    }

    const fn is_present(&self) -> bool {
        self.input > 0 || self.cached_input > 0 || self.output > 0
    }

    const fn is_zero(&self) -> bool {
        self.input == 0 && self.cached_input == 0 && self.output == 0
    }

    const fn has_negative(&self) -> bool {
        self.input < 0 || self.cached_input < 0 || self.output < 0
    }

    fn cost(&self, input: f64, cached_input: f64, output: f64) -> f64 {
        python_round(
            cost_bucket(self.input, input)
                + cost_bucket(self.cached_input, cached_input)
                + cost_bucket(self.output, output),
            2,
        )
    }

    const fn slot(&mut self, field: &str) -> Option<&mut i64> {
        match field.as_bytes() {
            b"input" => Some(&mut self.input),
            b"cached-input" => Some(&mut self.cached_input),
            b"output" => Some(&mut self.output),
            _unknown => None,
        }
    }
}

/// Cursor-shaped per-bucket counts for one display bucket.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct CursorCounts {
    /// Uncached input tokens.
    pub input: i64,
    /// Cache-read tokens.
    pub cache_read: i64,
    /// Output tokens.
    pub output: i64,
}

impl CursorCounts {
    /// Sum every component.
    #[must_use]
    pub const fn total(&self) -> i64 {
        self.input + self.cache_read + self.output
    }

    const fn is_zero(&self) -> bool {
        self.input == 0 && self.cache_read == 0 && self.output == 0
    }

    const fn has_negative(&self) -> bool {
        self.input < 0 || self.cache_read < 0 || self.output < 0
    }

    fn cost(&self, input: f64, cache_read: f64, output: f64) -> f64 {
        python_round(
            cost_bucket(self.input, input)
                + cost_bucket(self.cache_read, cache_read)
                + cost_bucket(self.output, output),
            2,
        )
    }

    const fn slot(&mut self, field: &str) -> Option<&mut i64> {
        match field.as_bytes() {
            b"input" => Some(&mut self.input),
            b"cache-read" => Some(&mut self.cache_read),
            b"output" => Some(&mut self.output),
            _unknown => None,
        }
    }
}

/// Every token count one pricing pass consumes.
///
/// A lane carries either per-bucket counts or one blended count; the blended
/// count prices the lane only when that lane has no bucket detail.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct TokenCounts {
    /// Main-agent Claude per-bucket counts.
    pub claude: ClaudeCounts,
    /// Codex default-bucket counts.
    pub codex: CodexCounts,
    /// Codex mini-bucket counts.
    pub codex_mini: CodexCounts,
    /// Cursor composer-bucket counts.
    pub cursor: CursorCounts,
    /// Cursor grok-bucket counts.
    pub cursor_grok: CursorCounts,
    /// Whether any Cursor per-bucket count was supplied at all.
    pub cursor_detail_present: bool,
    /// Spawned-Claude counts priced at the Opus row.
    pub claude_sub: ClaudeCounts,
    /// Spawned-Claude counts priced at the Sonnet row.
    pub claude_sub_sonnet: ClaudeCounts,
    /// Spawned-Claude counts priced at the Haiku row.
    pub claude_sub_haiku: ClaudeCounts,
    /// Spawned-Claude counts priced at the Fable row.
    pub claude_sub_fable: ClaudeCounts,
    /// Aggregate main-agent Claude tokens when no bucket detail exists.
    pub claude_blended: i64,
    /// Aggregate Codex tokens when no bucket detail exists.
    pub codex_blended: i64,
    /// Aggregate Cursor tokens when no bucket detail exists.
    pub cursor_blended: i64,
    /// Aggregate spawned-Claude tokens when no bucket detail exists.
    pub claude_sub_blended: i64,
}

/// A refusal from the cost model.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TokenCostError {
    /// A pricing flag was unknown or carried no value.
    UnknownFlag(String),
    /// A token count was not a non-negative integer.
    InvalidCount(String),
    /// A report bucket held a negative token count.
    NegativeCount(&'static str),
}

impl fmt::Display for TokenCostError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::UnknownFlag(flag) => write!(formatter, "unknown or incomplete flag: {flag}"),
            Self::InvalidCount(raw) => write!(formatter, "invalid non-integer token count: {raw}"),
            Self::NegativeCount(lane) => {
                write!(formatter, "invalid non-integer token count in lane: {lane}")
            }
        }
    }
}

impl Error for TokenCostError {}

/// Read one count argument the way Python's `_uint` did.
fn parse_count(raw: &str) -> Result<i64, TokenCostError> {
    if raw.is_empty() {
        return Ok(0);
    }
    unsigned_integer(raw)
        .and_then(|value| i64::try_from(value).ok())
        .ok_or_else(|| TokenCostError::InvalidCount(raw.to_owned()))
}

/// Spawned-Claude flag prefixes, longest first so a prefix never shadows one.
const CLAUDE_LANE_PREFIXES: [&str; 5] = [
    "claude-sub-sonnet",
    "claude-sub-haiku",
    "claude-sub-fable",
    "claude-sub",
    "claude",
];

impl TokenCounts {
    /// Resolve one `--<lane>-<field>-tokens` flag to the count it sets.
    ///
    /// The second element reports whether the flag is a Cursor per-bucket flag,
    /// which is what marks a Cursor split as detailed even when it reads zero.
    fn slot(&mut self, flag: &str) -> Option<(&mut i64, bool)> {
        let body = flag
            .strip_prefix("--")
            .and_then(|name| name.strip_suffix("-tokens"))?;
        match body {
            "claude" => return Some((&mut self.claude_blended, false)),
            "codex" => return Some((&mut self.codex_blended, false)),
            "cursor" => return Some((&mut self.cursor_blended, false)),
            "claude-sub" => return Some((&mut self.claude_sub_blended, false)),
            _bucketed => {}
        }
        for prefix in CLAUDE_LANE_PREFIXES {
            let Some(field) = lane_field(body, prefix) else {
                continue;
            };
            let lane = match prefix {
                "claude-sub-sonnet" => &mut self.claude_sub_sonnet,
                "claude-sub-haiku" => &mut self.claude_sub_haiku,
                "claude-sub-fable" => &mut self.claude_sub_fable,
                "claude-sub" => &mut self.claude_sub,
                _claude => &mut self.claude,
            };
            return lane.slot(field).map(|slot| (slot, false));
        }
        for prefix in ["codex-mini", "codex"] {
            let Some(field) = lane_field(body, prefix) else {
                continue;
            };
            let lane = if prefix == "codex-mini" {
                &mut self.codex_mini
            } else {
                &mut self.codex
            };
            return lane.slot(field).map(|slot| (slot, false));
        }
        for prefix in ["cursor-grok", "cursor"] {
            let Some(field) = lane_field(body, prefix) else {
                continue;
            };
            let lane = if prefix == "cursor-grok" {
                &mut self.cursor_grok
            } else {
                &mut self.cursor
            };
            return lane.slot(field).map(|slot| (slot, true));
        }
        None
    }

    /// Parse `token cost` pricing flags into counts plus the main-agent model.
    ///
    /// A repeated flag replaces the earlier value, matching the Python owner.
    ///
    /// # Errors
    ///
    /// Returns [`TokenCostError`] for an unknown flag, a flag with no value, or
    /// a count that is not a non-negative integer.
    pub fn from_cost_argv(argv: &[String]) -> Result<(Self, String), TokenCostError> {
        let mut counts = Self::default();
        let mut claude_model = String::new();
        let mut index = 0;
        while index < argv.len() {
            let argument = argv[index].as_str();
            let value = argv
                .get(index + 1)
                .ok_or_else(|| TokenCostError::UnknownFlag(argument.to_owned()))?;
            if argument == "--claude-model" {
                claude_model.clone_from(value);
            } else {
                let cursor_detail = {
                    let (slot, cursor_detail) = counts
                        .slot(argument)
                        .ok_or_else(|| TokenCostError::UnknownFlag(argument.to_owned()))?;
                    *slot = parse_count(value)?;
                    cursor_detail
                };
                counts.cursor_detail_present = counts.cursor_detail_present || cursor_detail;
            }
            index += 2;
        }
        Ok((counts, claude_model))
    }

    /// Build counts from one scanned run record.
    ///
    /// A lane with a nonzero report bucket prices per bucket; every other lane
    /// falls back to its effective aggregate total. A recorded model id with no
    /// rate row of its own is reported through `observations`.
    ///
    /// # Errors
    ///
    /// Returns [`TokenCostError::NegativeCount`] when a bucket held a negative
    /// count. The Python owner reached the same state by rejecting a negative
    /// count argument, which drove its caller onto blended fallback pricing.
    pub fn from_run_record(
        record: &TokenRunRecord,
        observations: &mut TokenObservations,
    ) -> Result<Self, TokenCostError> {
        let mut counts = Self::default();
        for vendor in TOKEN_VENDORS {
            if let Some(bucket) = bucket_for(record, vendor) {
                match vendor {
                    TokenVendor::Claude => counts.claude = ClaudeCounts::from_bucket(bucket),
                    TokenVendor::Codex => counts.read_codex(record, bucket, observations),
                    TokenVendor::Cursor => counts.read_cursor(record, bucket, observations),
                    TokenVendor::ClaudeSub => counts.read_claude_sub(record, bucket, observations),
                }
            } else {
                let total = effective_vendor_total(&lane_totals(record, vendor), vendor);
                match vendor {
                    TokenVendor::Claude => counts.claude_blended = total,
                    TokenVendor::Codex => counts.codex_blended = total,
                    TokenVendor::Cursor => counts.cursor_blended = total,
                    TokenVendor::ClaudeSub => counts.claude_sub_blended = total,
                }
            }
        }
        counts.reject_negative()?;
        Ok(counts)
    }

    /// Split the Codex bucket by model, routing mini-class rows to their bucket.
    fn read_codex(
        &mut self,
        record: &TokenRunRecord,
        bucket: &Map<String, Value>,
        observations: &mut TokenObservations,
    ) {
        let Some(by_model) = model_split(record, TokenVendor::Codex) else {
            self.codex = CodexCounts {
                input: safe_int(bucket.get("input"), 0),
                cached_input: safe_int(bucket.get("cached_input"), 0),
                output: safe_int(bucket.get("output"), 0),
            };
            return;
        };
        for (model, raw) in by_model {
            let fields = raw.as_object();
            let read = |key: &str| fields.map_or(0, |fields| safe_int(fields.get(key), 0));
            let mini = CODEX_MINI_MODELS.contains(&model.as_str());
            let applied = if mini {
                CODEX_REVIEW_MODEL_DEFAULT
            } else {
                CODEX_DEFAULT_MODEL
            };
            note_priced_as(TokenVendor::Codex, model, applied, observations);
            let target = if mini {
                &mut self.codex_mini
            } else {
                &mut self.codex
            };
            target.input += read("input");
            target.cached_input += read("cached_input");
            target.output += read("output");
        }
    }

    /// Split the Cursor bucket by model when every per-model bucket is exact.
    fn read_cursor(
        &mut self,
        record: &TokenRunRecord,
        bucket: &Map<String, Value>,
        observations: &mut TokenObservations,
    ) {
        let by_model = record.raw_report.get("BUCKETS_cursor_by_model");
        let Some(detailed) = by_model
            .and_then(Value::as_object)
            .filter(|split| cursor_split_is_detailed(split))
        else {
            self.cursor_blended = ["input", "cache_read", "output"]
                .iter()
                .map(|key| safe_int(bucket.get(*key), 0))
                .sum();
            return;
        };
        self.cursor_detail_present = true;
        for (model, raw) in detailed {
            let counts =
                cursor_bucket_counts(raw).expect("a validated Cursor bucket stays validated");
            let grok = CURSOR_GROK_MODELS.contains(&model.as_str());
            let applied = if grok {
                CURSOR_GROK_4_6_HIGH_MODEL
            } else {
                CURSOR_DEFAULT_MODEL
            };
            note_priced_as(TokenVendor::Cursor, model, applied, observations);
            let target = if grok {
                &mut self.cursor_grok
            } else {
                &mut self.cursor
            };
            target.input += counts[0];
            target.cache_read += counts[1];
            target.output += counts[2];
        }
    }

    /// Split the spawned-Claude bucket into the three separately priced families.
    ///
    /// Every other model, including Opus and any unrecognized id, folds into
    /// the aggregate bucket priced at the Opus row.
    fn read_claude_sub(
        &mut self,
        record: &TokenRunRecord,
        bucket: &Map<String, Value>,
        observations: &mut TokenObservations,
    ) {
        let Some(by_model) = model_split(record, TokenVendor::ClaudeSub) else {
            self.claude_sub = ClaudeCounts::from_bucket(bucket);
            return;
        };
        let empty = Map::new();
        for (model, raw) in by_model {
            let counts = ClaudeCounts::from_bucket(raw.as_object().unwrap_or(&empty));
            let (target, applied) = match model.as_str() {
                CLAUDE_SONNET_4_6_MODEL => (&mut self.claude_sub_sonnet, CLAUDE_SONNET_4_6_MODEL),
                CLAUDE_HAIKU_4_5_MODEL => (&mut self.claude_sub_haiku, CLAUDE_HAIKU_4_5_MODEL),
                CLAUDE_FABLE_5_MODEL => (&mut self.claude_sub_fable, CLAUDE_FABLE_5_MODEL),
                _opus_or_other => (&mut self.claude_sub, CLAUDE_OPUS_4_8_MODEL),
            };
            note_priced_as(TokenVendor::ClaudeSub, model, applied, observations);
            target.add(counts);
        }
    }

    fn reject_negative(&self) -> Result<(), TokenCostError> {
        let lanes: [(&'static str, bool); 13] = [
            ("claude", self.claude.has_negative()),
            ("codex", self.codex.has_negative()),
            ("codex_mini", self.codex_mini.has_negative()),
            ("cursor", self.cursor.has_negative()),
            ("cursor_grok", self.cursor_grok.has_negative()),
            ("claude_sub", self.claude_sub.has_negative()),
            ("claude_sub_sonnet", self.claude_sub_sonnet.has_negative()),
            ("claude_sub_haiku", self.claude_sub_haiku.has_negative()),
            ("claude_sub_fable", self.claude_sub_fable.has_negative()),
            ("claude", self.claude_blended < 0),
            ("codex", self.codex_blended < 0),
            ("cursor", self.cursor_blended < 0),
            ("claude_sub", self.claude_sub_blended < 0),
        ];
        lanes
            .into_iter()
            .find_map(|(lane, negative)| negative.then_some(TokenCostError::NegativeCount(lane)))
            .map_or(Ok(()), Err)
    }

    /// Return whether every count is zero.
    ///
    /// The Cursor detail marker is not a count and does not affect this.
    #[must_use]
    pub const fn is_zero(&self) -> bool {
        self.claude.is_zero()
            && self.codex.is_zero()
            && self.codex_mini.is_zero()
            && self.cursor.is_zero()
            && self.cursor_grok.is_zero()
            && self.claude_sub.is_zero()
            && self.claude_sub_sonnet.is_zero()
            && self.claude_sub_haiku.is_zero()
            && self.claude_sub_fable.is_zero()
            && self.claude_blended == 0
            && self.codex_blended == 0
            && self.cursor_blended == 0
            && self.claude_sub_blended == 0
    }
}

/// Split `body` into the field that follows `prefix`, or `None`.
fn lane_field<'a>(body: &'a str, prefix: &str) -> Option<&'a str> {
    body.strip_prefix(prefix)
        .and_then(|rest| rest.strip_prefix('-'))
}

/// Return a lane's report bucket when it holds a positive component sum.
fn bucket_for(record: &TokenRunRecord, vendor: TokenVendor) -> Option<&Map<String, Value>> {
    record
        .raw_report
        .get(&format!("BUCKETS_{}", vendor.as_str()))
        .and_then(Value::as_object)
        .filter(|bucket| {
            !bucket.is_empty()
                && vendor
                    .components()
                    .iter()
                    .map(|key| safe_int(bucket.get(*key), 0))
                    .sum::<i64>()
                    > 0
        })
}

/// Return the per-model split for one lane, or `None` when absent or empty.
fn model_split(record: &TokenRunRecord, vendor: TokenVendor) -> Option<&Map<String, Value>> {
    record
        .raw_report
        .get(&format!("BUCKETS_{}_by_model", vendor.as_str()))
        .and_then(Value::as_object)
        .filter(|split| !split.is_empty())
}

const fn lane_totals(record: &TokenRunRecord, vendor: TokenVendor) -> VendorTotals {
    match vendor {
        TokenVendor::Claude => record.claude,
        TokenVendor::Codex => record.codex,
        TokenVendor::Cursor => record.cursor,
        TokenVendor::ClaudeSub => record.claude_sub,
    }
}

/// Read one per-model Cursor bucket, rejecting every inexact spelling.
///
/// Only a plain non-negative integer or its exact digit string counts. A float,
/// a boolean, a null, or a signed or separated string makes the whole split
/// unusable, which is what drives the aggregate Composer fallback.
fn cursor_bucket_counts(value: &Value) -> Option<[i64; 3]> {
    let fields = value.as_object()?;
    let mut counts = [0_i64; 3];
    for (index, key) in ["input", "cache_read", "output"].iter().enumerate() {
        let text = match fields.get(*key) {
            None => "0".to_owned(),
            Some(Value::Number(number)) if number.is_f64() => return None,
            Some(Value::Number(number)) => number.to_string(),
            Some(Value::String(raw)) => raw.trim().to_owned(),
            Some(_other) => return None,
        };
        if text.is_empty() || !text.bytes().all(|byte| byte.is_ascii_digit()) {
            return None;
        }
        counts[index] = text.parse().ok()?;
    }
    Some(counts)
}

fn cursor_split_is_detailed(split: &Map<String, Value>) -> bool {
    !split.is_empty()
        && split
            .values()
            .all(|value| cursor_bucket_counts(value).is_some())
}

/// Return whether a Cursor per-model split can drive model-aware pricing.
#[must_use]
pub fn cursor_buckets_are_detailed(by_model: Option<&Value>) -> bool {
    by_model
        .and_then(Value::as_object)
        .is_some_and(cursor_split_is_detailed)
}

/// Every priced value one pricing pass produces.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct TokenCostValues {
    /// Main-agent Claude cost.
    pub claude_cost: f64,
    /// Total Codex cost across both display buckets.
    pub codex_cost: f64,
    /// Codex default-bucket cost.
    pub codex_default_cost: f64,
    /// Codex mini-bucket cost.
    pub codex_mini_cost: f64,
    /// Total Cursor cost.
    pub cursor_cost: f64,
    /// Cursor composer-bucket cost, absent without per-bucket detail.
    pub cursor_composer_cost: Option<f64>,
    /// Cursor grok-bucket cost, absent without per-bucket detail.
    pub cursor_grok_cost: Option<f64>,
    /// Spawned-Claude cost.
    pub claude_sub_cost: f64,
    /// Sum of every lane cost.
    pub total_cost: f64,
    /// Main-agent Claude tokens.
    pub claude_tokens: i64,
    /// Codex tokens.
    pub codex_tokens: i64,
    /// Cursor tokens.
    pub cursor_tokens: i64,
    /// Spawned-Claude tokens.
    pub claude_sub_tokens: i64,
    /// Sum of every lane's tokens.
    pub total_tokens: i64,
    /// Whether any lane priced from a blended aggregate instead of buckets.
    pub blended_fallback: bool,
}

/// One lane's priced tokens and cost, plus whether it used a blended rate.
struct LaneCost {
    tokens: i64,
    cost: f64,
    blended: bool,
}

fn price_claude(counts: &TokenCounts, rates: &TokenRates) -> LaneCost {
    if counts.claude.is_present() {
        return LaneCost {
            tokens: counts.claude.total(),
            cost: counts.claude.cost(RateRow::claude(
                rates.claude_input,
                rates.claude_cache_read,
                rates.claude_cache_create_5m,
                rates.claude_cache_create_1h,
                rates.claude_output,
            )),
            blended: false,
        };
    }
    LaneCost {
        tokens: counts.claude_blended,
        cost: cost_blend(counts.claude_blended, rates.claude_blended),
        blended: counts.claude_blended > 0,
    }
}

/// Codex default-bucket cost, mini-bucket cost, and the lane total.
fn price_codex(counts: &TokenCounts, rates: &TokenRates) -> (f64, f64, LaneCost) {
    if counts.codex.is_present() || counts.codex_mini.is_present() {
        // Both display buckets price at their own model rates and sum, because
        // one round can mix a default-class and a mini-class Codex model.
        let default_cost = counts.codex.cost(
            rates.codex_input,
            rates.codex_cached_input,
            rates.codex_output,
        );
        let mini_cost = counts.codex_mini.cost(
            rates.codex_mini_input,
            rates.codex_mini_cached_input,
            rates.codex_mini_output,
        );
        return (
            default_cost,
            mini_cost,
            LaneCost {
                tokens: counts.codex.total() + counts.codex_mini.total(),
                cost: python_round(default_cost + mini_cost, 2),
                blended: false,
            },
        );
    }
    // A blended fallback has no model breakdown, so the default bucket carries it.
    let cost = cost_blend(counts.codex_blended, rates.codex_blended);
    (
        cost,
        0.0,
        LaneCost {
            tokens: counts.codex_blended,
            cost,
            blended: counts.codex_blended > 0,
        },
    )
}

/// Cursor composer cost, grok cost, and the lane total.
fn price_cursor(counts: &TokenCounts, rates: &TokenRates) -> (Option<f64>, Option<f64>, LaneCost) {
    if counts.cursor_detail_present {
        let composer = counts.cursor.cost(
            rates.cursor_input,
            rates.cursor_cache_read,
            rates.cursor_output,
        );
        let grok = counts.cursor_grok.cost(
            rates.cursor_grok_input,
            rates.cursor_grok_cache_read,
            rates.cursor_grok_output,
        );
        return (
            Some(composer),
            Some(grok),
            LaneCost {
                tokens: counts.cursor.total() + counts.cursor_grok.total(),
                cost: python_round(composer + grok, 2),
                blended: false,
            },
        );
    }
    (
        None,
        None,
        LaneCost {
            tokens: counts.cursor_blended,
            cost: cost_blend(counts.cursor_blended, rates.cursor_blended),
            blended: counts.cursor_blended > 0,
        },
    )
}

/// Spawned-Claude cost, priced from the rate table rather than display rates.
fn price_claude_sub(counts: &TokenCounts, rates: &TokenRates) -> LaneCost {
    let families = [
        (counts.claude_sub_sonnet, CLAUDE_SONNET_4_6_MODEL),
        (counts.claude_sub_haiku, CLAUDE_HAIKU_4_5_MODEL),
        (counts.claude_sub_fable, CLAUDE_FABLE_5_MODEL),
    ];
    let priced: Vec<_> = families
        .into_iter()
        .filter(|(family, _model)| family.is_present())
        .collect();
    if !counts.claude_sub.is_present() && priced.is_empty() {
        return LaneCost {
            tokens: counts.claude_sub_blended,
            cost: cost_blend(counts.claude_sub_blended, rates.claude_blended),
            blended: counts.claude_sub_blended > 0,
        };
    }
    let mut tokens = counts.claude_sub.total();
    let mut cost = counts.claude_sub.cost(sub_rate_row(CLAUDE_OPUS_4_8_MODEL));
    for (family, model) in priced {
        tokens += family.total();
        cost = python_round(cost + family.cost(sub_rate_row(model)), 2);
    }
    LaneCost {
        tokens,
        cost,
        blended: false,
    }
}

/// Return the table row a spawned-Claude family prices at.
fn sub_rate_row(model: &str) -> RateRow {
    exact_rate_row(TokenVendor::ClaudeSub, model)
        .expect("every spawned-Claude family model has a rate row")
}

/// Price one set of counts.
///
/// A lane with per-bucket counts prices at its bucket rates; a lane with only
/// an aggregate count prices at its blended rate and sets `blended_fallback`.
/// Spawned-Claude families price from [`RATE_TABLE`] directly, so a rate
/// environment override never moves them.
#[must_use]
pub fn price_counts(counts: &TokenCounts, rates: &TokenRates) -> TokenCostValues {
    let claude = price_claude(counts, rates);
    let (codex_default_cost, codex_mini_cost, codex) = price_codex(counts, rates);
    let (cursor_composer_cost, cursor_grok_cost, cursor) = price_cursor(counts, rates);
    let claude_sub = price_claude_sub(counts, rates);
    TokenCostValues {
        claude_cost: claude.cost,
        codex_cost: codex.cost,
        codex_default_cost,
        codex_mini_cost,
        cursor_cost: cursor.cost,
        cursor_composer_cost,
        cursor_grok_cost,
        claude_sub_cost: claude_sub.cost,
        total_cost: python_round(claude.cost + codex.cost + cursor.cost + claude_sub.cost, 2),
        claude_tokens: claude.tokens,
        codex_tokens: codex.tokens,
        cursor_tokens: cursor.tokens,
        claude_sub_tokens: claude_sub.tokens,
        total_tokens: claude.tokens + codex.tokens + cursor.tokens + claude_sub.tokens,
        blended_fallback: claude.blended || codex.blended || cursor.blended || claude_sub.blended,
    }
}

/// Render the `token cost` `KEY=value` block, including its trailing newline.
///
/// The two Cursor component rows appear only when per-bucket Cursor detail was
/// available, which is what tells a reader the split is real.
#[must_use]
pub fn render_cost_kv(values: &TokenCostValues) -> String {
    let mut rows = vec![
        ("CLAUDE_COST", format_money(values.claude_cost)),
        ("CODEX_COST", format_money(values.codex_cost)),
        (
            "CODEX_GPT_5_5_COST",
            format_money(values.codex_default_cost),
        ),
        (
            "CODEX_GPT_5_4_MINI_COST",
            format_money(values.codex_mini_cost),
        ),
    ];
    if let (Some(composer), Some(grok)) = (values.cursor_composer_cost, values.cursor_grok_cost) {
        rows.push(("CURSOR_COMPOSER_COST", format_money(composer)));
        rows.push(("CURSOR_GROK_COST", format_money(grok)));
    }
    rows.extend([
        ("CURSOR_COST", format_money(values.cursor_cost)),
        ("CLAUDE_SUB_COST", format_money(values.claude_sub_cost)),
        ("TOTAL_COST", format_money(values.total_cost)),
        ("CLAUDE_TOKENS", values.claude_tokens.to_string()),
        ("CODEX_TOKENS", values.codex_tokens.to_string()),
        ("CURSOR_TOKENS", values.cursor_tokens.to_string()),
        ("CLAUDE_SUB_TOKENS", values.claude_sub_tokens.to_string()),
        ("TOTAL_TOKENS", values.total_tokens.to_string()),
    ]);
    let mut rendered = String::new();
    for (key, value) in rows {
        rendered.push_str(key);
        rendered.push('=');
        rendered.push_str(&value);
        rendered.push('\n');
    }
    rendered
}

/// Render the one-line cost summary, including its trailing newline.
#[must_use]
pub fn render_cost_line(values: &TokenCostValues) -> String {
    let cursor_segment = match (values.cursor_composer_cost, values.cursor_grok_cost) {
        (Some(composer), Some(grok)) => format!(
            "Cursor ${} (Composer ${}, Grok ${})",
            format_money(values.cursor_cost),
            format_money(composer),
            format_money(grok),
        ),
        _absent => format!("Cursor ${}", format_money(values.cursor_cost)),
    };
    format!(
        "\u{1f4b0} Cost: TOTAL ~${}: Claude ${}, Codex-5.6 ${}, Codex-mini ${}, {}, \
Claude (subprocess) ${}  |  Tokens: {}k\n",
        format_money(values.total_cost),
        format_money(values.claude_cost),
        format_money(values.codex_default_cost),
        format_money(values.codex_mini_cost),
        cursor_segment,
        format_money(values.claude_sub_cost),
        (values.total_tokens + 500) / 1000,
    )
}

/// The priced cost of one run.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct RunCost {
    /// Main-agent Claude cost.
    pub claude_cost: f64,
    /// Codex cost.
    pub codex_cost: f64,
    /// Cursor cost.
    pub cursor_cost: f64,
    /// Cursor composer-bucket cost, absent without a detailed Cursor split.
    pub cursor_composer_cost: Option<f64>,
    /// Cursor grok-bucket cost, absent without a detailed Cursor split.
    pub cursor_grok_cost: Option<f64>,
    /// Spawned-Claude cost.
    pub claude_sub_cost: f64,
    /// Sum of every lane cost.
    pub total_cost: f64,
    /// Whether the per-bucket cost model priced this run.
    pub priced_by_token_cost: bool,
}

/// Price one scanned run.
///
/// A run whose buckets cannot produce valid counts falls back to blended
/// per-lane pricing and reports `priced_by_token_cost = false`, so a renderer
/// can mark that row as an estimate.
#[must_use]
pub fn price_run(
    record: &TokenRunRecord,
    env: &BTreeMap<String, String>,
    observations: &mut TokenObservations,
) -> RunCost {
    let rates = display_rates(env, &record.main_model, observations);
    let Ok(counts) = TokenCounts::from_run_record(record, observations) else {
        return fallback_cost(record, &rates);
    };
    let values = price_counts(&counts, &rates);
    RunCost {
        claude_cost: values.claude_cost,
        codex_cost: values.codex_cost,
        cursor_cost: values.cursor_cost,
        cursor_composer_cost: values.cursor_composer_cost,
        cursor_grok_cost: values.cursor_grok_cost,
        claude_sub_cost: values.claude_sub_cost,
        total_cost: values.total_cost,
        priced_by_token_cost: true,
    }
}

/// Price one run from blended per-lane rates alone.
#[must_use]
pub fn fallback_cost(record: &TokenRunRecord, rates: &TokenRates) -> RunCost {
    let lane = |vendor: TokenVendor, rate: f64| {
        tokens_in_millions(aggregate_vendor_tokens(record, vendor)) * rate
    };
    let claude_cost = lane(TokenVendor::Claude, rates.claude_blended);
    let codex_cost = lane(TokenVendor::Codex, rates.codex_blended);
    let cursor_cost = lane(TokenVendor::Cursor, rates.cursor_blended);
    let claude_sub_cost = lane(TokenVendor::ClaudeSub, rates.claude_blended);
    RunCost {
        claude_cost: python_round(claude_cost, 2),
        codex_cost: python_round(codex_cost, 2),
        cursor_cost: python_round(cursor_cost, 2),
        cursor_composer_cost: None,
        cursor_grok_cost: None,
        claude_sub_cost: python_round(claude_sub_cost, 2),
        total_cost: python_round(claude_cost + codex_cost + cursor_cost + claude_sub_cost, 2),
        priced_by_token_cost: false,
    }
}

/// Return the canonical token total one lane of a run contributes.
#[must_use]
pub const fn aggregate_vendor_tokens(record: &TokenRunRecord, vendor: TokenVendor) -> i64 {
    effective_vendor_total(&lane_totals(record, vendor), vendor)
}
