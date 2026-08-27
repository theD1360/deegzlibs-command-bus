"""Tests for command_bus interfaces and base types."""

import pytest
from command_bus import CommandMessage, CommandHandler, Handler, TransmissibleBaseModel


def test_transmissible_base_model_str():
    """str() of a message yields module-qualified repr."""

    class M(TransmissibleBaseModel):
        x: int

    m = M(x=1)
    s = str(m)
    assert "M" in s
    assert "x=1" in s or "1" in s
    assert m.__module__ in s


def test_command_message_is_pydantic_model():
    """CommandMessage subclasses can define fields."""

    class E(CommandMessage):
        id: str

    e = E(id="abc")
    assert e.id == "abc"


def test_event_message_is_pydantic_model():
    from command_bus import EventMessage

    class E(EventMessage):
        id: str

    e = E(id="abc")
    assert e.id == "abc"
    assert not hasattr(e, "correlation_id") or "correlation_id" not in E.model_fields


def test_command_handler_abstract():
    """CommandHandler cannot be instantiated without process()."""
    with pytest.raises(TypeError):
        CommandHandler()


def test_handler_abstract():
    """Handler cannot be instantiated without process()."""
    with pytest.raises(TypeError):
        Handler()
