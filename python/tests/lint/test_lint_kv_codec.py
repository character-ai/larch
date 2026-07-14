"""Focused detection coverage for the shared KEY=value codec ratchet."""

from __future__ import annotations

from larch.lint import lint_kv_codec
from larch.lint.engine import SourceFile


def _source(*, path: str, text: str) -> SourceFile:
    return SourceFile(path=path, text=text, lines=tuple(text.splitlines()))


def test_detects_python_split_reader_loop() -> None:
    source = _source(
        path="python/larch/example.py",
        text="for line in rows:\n    key, value = line.split('=', 1)\n",
    )

    findings = lint_kv_codec.detect(source)

    assert [(item.line, item.rule_id) for item in findings] == [(2, "kv-codec")]
    assert findings[0].anchor


def test_detects_python_comprehension_reader() -> None:
    source = _source(
        path="python/larch/example.py",
        text="pairs = {key: value for line in rows for key, value in [line.split('=', 1)]}\n",
    )

    assert [item.line for item in lint_kv_codec.detect(source)] == [1]


def test_ignores_non_owner_option_splitting_and_codec_owner() -> None:
    option = _source(
        path="python/larch/example.py",
        text="for token in args:\n    key, value = token.split('=', 1)\n",
    )
    owner = _source(
        path="python/larch/io.py",
        text="for line in rows:\n    key, value = line.split('=', 1)\n",
    )

    assert not lint_kv_codec.detect(option)
    assert not lint_kv_codec.detect(owner)


def test_detects_shell_reader_but_not_unrelated_awk() -> None:
    shell = _source(
        path="scripts/example.sh",
        text="value=$(awk -F= '$1 == key { print $2 }' file)\n",
    )
    unrelated = _source(
        path="scripts/example.sh",
        text="awk -F: '{ print $2 }' file\n",
    )

    assert [item.line for item in lint_kv_codec.detect(shell)] == [1]
    assert not lint_kv_codec.detect(unrelated)


def test_detects_quoted_shell_delimiters_without_option_false_positives() -> None:
    quoted_awk = _source(
        path="scripts/example.sh",
        text="awk -F '=' '$1 == key { print $2 }' file\n",
    )
    quoted_cut = _source(
        path="scripts/example.sh",
        text="cut -d '=' -f 2 \"$env_file\"\n",
    )
    unrelated_cut = _source(
        path="scripts/example.sh",
        text="cut -d '=' -f 2 options.txt\n",
    )
    assert [item.line for item in lint_kv_codec.detect(quoted_awk)] == [1]
    assert [item.line for item in lint_kv_codec.detect(quoted_cut)] == [1]
    assert not lint_kv_codec.detect(unrelated_cut)


def test_ignores_shell_harnesses() -> None:
    source = _source(
        path="scripts/test-example.sh",
        text="awk -F= '$1 == key { print $2 }' file\n",
    )

    assert not lint_kv_codec.detect(source)
