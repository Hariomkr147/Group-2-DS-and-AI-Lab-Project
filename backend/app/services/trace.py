"""Progress events for one tutoring turn.

Each layer calls `emit` to say what it did. Nothing happens unless a streaming request is listening
(`collect`), so the JSON path is unchanged. Events are shown to the student: never put the stored
answer, a hidden result or a prompt in them.
"""
from contextlib import contextmanager
from contextvars import ContextVar
import logging
from typing import Callable

log = logging.getLogger(__name__)

_sink: ContextVar[Callable[[dict], None] | None] = ContextVar("trace_sink", default=None)


def emit(stage: str, title: str, detail: str = "") -> None:
    sink = _sink.get()
    if sink is None:
        return
    try:
        sink({"stage": stage, "title": title, "detail": detail})
    except Exception as error:                     # a broken listener must never break the turn
        log.warning("Trace event dropped (%s)", type(error).__name__)


@contextmanager
def collect(sink: Callable[[dict], None]):
    token = _sink.set(sink)
    try:
        yield
    finally:
        _sink.reset(token)
