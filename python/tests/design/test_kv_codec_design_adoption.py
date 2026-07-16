"""Characterize shared-codec behavior at migrated /design call sites."""

from __future__ import annotations

from pathlib import Path

from larch.design import (
    design_log_publish_flow,
    design_step0,
    design_step0_env,
    design_step1,
    design_step5c,
    plan_scout,
)


def test_log_scrub_retains_last_row_crlf_and_numeric_fallback() -> None:
    stdout = "SECRET_SCRUB_VIOLATIONS=1\r\ninvalid\nSECRET_SCRUB_VIOLATIONS= 2 \r\n"

    assert design_log_publish_flow._scrub_violations(stdout) == "2"  # pyright: ignore[reportPrivateUsage] - characterize migration seam
    assert (
        design_log_publish_flow._scrub_violations("SECRET_SCRUB_VIOLATIONS=nope\n")
        == "0"
    )  # pyright: ignore[reportPrivateUsage] - characterize migration seam
    assert design_log_publish_flow._scrub_violations("SECRET_SCRUB_VIOLATIONS=1\rSECRET_SCRUB_VIOLATIONS=2") == "2"  # pyright: ignore[reportPrivateUsage] - lone CR was a legacy row boundary


def test_step0_relay_retains_last_value_for_duplicate_status_rows(
    tmp_path: Path,
) -> None:
    state = design_step0.relay_degraded_tools_gate_stdout(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        stdout="DEGRADED=false\r\nDEGRADED=true\nBOTH_DOWN=false\n",
        design_tmpdir=tmp_path,
    )

    assert state["DEGRADED"] == "true"
    assert state["BOTH_DOWN"] == "false"


def test_step0_env_readers_keep_allowlist_duplicate_and_empty_value_policy(
    tmp_path: Path,
) -> None:
    cache = tmp_path / "cache.env"
    cache.write_text("# ignored\r\nKEEP=old\r\nKEEP=\r\nDROP=value\n", newline="")

    assert design_step0_env.load_bash_quoted_env(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        path=cache, allow_keys={"KEEP"}
    ) == {"KEEP": ""}

    source = tmp_path / "source.env"
    source.write_text(" export KEEP=old\r\nexport KEEP=new\nKEEP=\n", newline="")
    assert design_step0_env._load_source_env(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        path=source, allow_keys={"KEEP"}
    ) == {"KEEP": ""}


def test_step1_stderr_sink_uses_first_matching_value_and_preserves_empty_fallback(
    tmp_path: Path,
) -> None:
    output = tmp_path / "custom-output.txt"
    output.with_name("custom-output.txt.meta").write_text(
        "STDERR_SINK=first.log\nSTDERR_SINK=second.log\n", encoding="utf-8"
    )

    assert design_step1.brainstorm_stderr_sink_for_output(  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        output_path=output, design_tmpdir=tmp_path
    ) == Path("first.log")


def test_optional_trailers_preserve_input_order_and_duplicates(tmp_path: Path) -> None:
    values = tmp_path / "values.env"
    values.write_text(
        " diff_deleted=2\r\ndiff_added=1\ndiff_deleted=3\nignored\n", newline=""
    )

    assert design_step5c._optional_trailer_lines_from_values_file(values) == [  # pyright: ignore[reportPrivateUsage] - characterize migration seam
        "diff_deleted: 2\n",
        "diff_added: 1\n",
        "diff_deleted: 3\n",
    ]


def test_plan_scout_single_key_readers_use_first_value_and_reject_malformed(
    tmp_path: Path,
) -> None:
    launch = tmp_path / "launch.env"
    launch.write_text(
        "ELAPSED=4\r\nELAPSED=9\nSTATUS=first\nSTATUS=second\n", newline=""
    )

    assert plan_scout._launch_latency_ms(launch) == 4000  # pyright: ignore[reportPrivateUsage] - characterize migration seam
    assert plan_scout._parse_launch_status(launch) == "first"  # pyright: ignore[reportPrivateUsage] - characterize migration seam

    malformed = tmp_path / "malformed.env"
    malformed.write_text("ELAPSED=not-a-number\n", encoding="utf-8")
    assert plan_scout._launch_latency_ms(malformed) == 0  # pyright: ignore[reportPrivateUsage] - characterize migration seam
