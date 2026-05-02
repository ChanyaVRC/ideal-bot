"""Unit tests for the _tail_lines helper in admin_router."""
from __future__ import annotations

import pytest

from src.api.routers.admin_router import _tail_lines


def _write_lines(path, lines: list[str]) -> None:
    content = "\n".join(lines)
    if lines:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def test_empty_file_returns_empty(tmp_path):
    f = tmp_path / "empty.log"
    f.write_bytes(b"")
    assert _tail_lines(str(f), 10) == []


def test_fewer_lines_than_requested(tmp_path):
    f = tmp_path / "small.log"
    _write_lines(f, ["line1", "line2", "line3"])
    result = _tail_lines(str(f), 10)
    assert result == ["line1", "line2", "line3"]


def test_more_lines_than_requested(tmp_path):
    f = tmp_path / "big.log"
    lines = [f"line{i}" for i in range(100)]
    _write_lines(f, lines)
    result = _tail_lines(str(f), 10)
    assert len(result) == 10
    assert result[0] == "line90"
    assert result[-1] == "line99"


def test_exactly_n_lines(tmp_path):
    f = tmp_path / "exact.log"
    lines = [f"L{i}" for i in range(5)]
    _write_lines(f, lines)
    result = _tail_lines(str(f), 5)
    assert result == lines


def test_request_one_line_returns_last(tmp_path):
    f = tmp_path / "one.log"
    _write_lines(f, ["a", "b", "c", "d"])
    result = _tail_lines(str(f), 1)
    assert result == ["d"]


def test_invalid_utf8_is_replaced_not_raised(tmp_path):
    f = tmp_path / "binary.log"
    f.write_bytes(b"good line\n\xff\xfe bad bytes\ngood again\n")
    result = _tail_lines(str(f), 10)
    assert any("good again" in line for line in result)
    assert any("good line" in line for line in result)


def test_no_trailing_newline(tmp_path):
    f = tmp_path / "no_newline.log"
    f.write_text("alpha\nbeta\ngamma", encoding="utf-8")
    result = _tail_lines(str(f), 5)
    assert result == ["alpha", "beta", "gamma"]


def test_single_line_file(tmp_path):
    f = tmp_path / "single.log"
    f.write_text("only line\n", encoding="utf-8")
    result = _tail_lines(str(f), 5)
    assert result == ["only line"]
