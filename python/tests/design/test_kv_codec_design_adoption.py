"""Characterize shared-codec behavior at migrated /design call sites."""
# These tests deliberately pin private migration seams.
# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path

from larch.design import (
    design_core,
    design_log_publish_flow,
    design_step5c,
)


def test_log_scrub_retains_last_row_crlf_and_numeric_fallback() -> None:
    stdout = "SECRET_SCRUB_VIOLATIONS=1\r\ninvalid\nSECRET_SCRUB_VIOLATIONS= 2 \r\n"

    assert design_log_publish_flow._scrub_violations(stdout) == "2"  # pyright: ignore[reportPrivateUsage] - characterize migration seam
    assert (
        design_log_publish_flow._scrub_violations("SECRET_SCRUB_VIOLATIONS=nope\n")
        == "0"
    )  # pyright: ignore[reportPrivateUsage] - characterize migration seam
    assert design_log_publish_flow._scrub_violations("SECRET_SCRUB_VIOLATIONS=1\rSECRET_SCRUB_VIOLATIONS=2") == "2"  # pyright: ignore[reportPrivateUsage] - lone CR was a legacy row boundary


def test_step0_env_readers_keep_allowlist_duplicate_and_empty_value_policy(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache.env"
    _ = cache.write_text("# ignored\r\nKEEP=old\r\nKEEP=\r\nDROP=value\n", newline="")

    assert design_core.load_bash_quoted_env(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        path=cache, allow_keys={"KEEP"}
    ) == {"KEEP": ""}

    source = tmp_path / "source.env"
    _ = source.write_text(" export KEEP=old\r\nexport KEEP=new\nKEEP=\n", newline="")
    assert design_core._load_source_env(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        path=source, allow_keys={"KEEP"}
    ) == {"KEEP": ""}


def test_optional_trailers_preserve_input_order_and_duplicates(tmp_path: Path) -> None:
    values = tmp_path / "values.env"
    _ = values.write_text(
        " diff_deleted=2\r\ndiff_added=1\ndiff_deleted=3\nignored\n", newline=""
    )

    assert design_step5c._optional_trailer_lines_from_values_file(values) == [  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        "diff_deleted: 2\n",
        "diff_added: 1\n",
        "diff_deleted: 3\n",
    ]
