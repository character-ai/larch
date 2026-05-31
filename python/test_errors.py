"""Tests for errors.py hierarchy."""

from __future__ import annotations

import errors


def test_subclass_relationships() -> None:
    assert issubclass(errors.TransientNetworkError, errors.ShipError)
    assert issubclass(errors.NeedsUserInput, errors.ShipError)
    assert issubclass(errors.Stalled, errors.ShipError)


def test_messages_preserved() -> None:
    err = errors.TransientNetworkError("network blip")
    assert str(err) == "network blip"
