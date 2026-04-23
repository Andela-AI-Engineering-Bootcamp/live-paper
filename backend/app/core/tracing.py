"""LangFuse observability — centralised tracing for all 5 agents.

Every agent call gets a root trace with child spans per step so the
LangFuse dashboard shows full end-to-end latency, token usage, and
confidence scores without any manual instrumentation per agent.
"""

import functools
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Generator, Optional

logger = logging.getLogger(__name__)

_langfuse = None


def _client():
    global _langfuse
    if _langfuse is not None:
        return _langfuse

    import os
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        return None

    from langfuse import Langfuse
    _langfuse = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    return _langfuse


def new_trace_id() -> str:
    return str(uuid.uuid4())


def start_trace(name: str, input: dict, trace_id: Optional[str] = None):
    """Open a root trace. Returns (trace_obj | None, trace_id)."""
    tid = trace_id or new_trace_id()
    lf = _client()
    if not lf:
        return None, tid
    trace = lf.trace(name=name, id=tid, input=input)
    return trace, tid


@contextmanager
def span(
    trace_obj,
    name: str,
    input: Optional[dict] = None,
) -> Generator[dict, None, None]:
    """Context manager that records a child span on *trace_obj*.

    Yields a mutable dict you can write output/metadata into:
        with span(trace, "embed-text", {"text": t}) as s:
            s["output"] = {"dim": 384}
    """
    if trace_obj is None:
        yield {}
        return

    t0 = time.perf_counter()
    span_obj = trace_obj.span(name=name, input=input or {})
    ctx: dict[str, Any] = {}
    try:
        yield ctx
        span_obj.end(output=ctx.get("output"), level="DEFAULT")
    except Exception as exc:
        span_obj.end(
            output={"error": str(exc)},
            level="ERROR",
            status_message=str(exc),
        )
        raise
    finally:
        elapsed = time.perf_counter() - t0
        logger.debug("span %s finished in %.3fs", name, elapsed)


def observe(agent_name: str):
    """Decorator that wraps an async agent `run()` with a root LangFuse trace.

    The decorated function must accept **kwargs and may receive an optional
    `trace_id: str` kwarg — the same ID is returned so callers can link spans.

    Usage:
        @observe("retrieval-agent")
        async def run(question: str, **kwargs) -> RetrievalResult:
            ...
    """
    def decorator(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, trace_id: Optional[str] = None, **kwargs):
            tid = trace_id or new_trace_id()
            trace_obj, tid = start_trace(
                name=agent_name,
                input={"args": str(args)[:200], **{k: str(v)[:200] for k, v in kwargs.items()}},
                trace_id=tid,
            )
            try:
                result = await fn(*args, trace_id=tid, _trace=trace_obj, **kwargs)
                lf = _client()
                if trace_obj and lf:
                    output = result.model_dump() if hasattr(result, "model_dump") else str(result)[:500]
                    trace_obj.update(output=output, status="success")
                    lf.flush()
                return result
            except Exception as exc:
                if trace_obj:
                    trace_obj.update(status="error", status_message=str(exc))
                raise
        return wrapper
    return decorator


def record_metric(trace_obj, key: str, value: float) -> None:
    """Attach a scalar metric (confidence, latency, token count) to a trace."""
    if trace_obj is None:
        return
    try:
        trace_obj.score(name=key, value=value)
    except Exception:
        pass


def flush() -> None:
    """Force-flush pending events to LangFuse (call at shutdown)."""
    lf = _client()
    if lf:
        lf.flush()
