"""Lazy singleton construction.

Module-level `x = Thing()` runs at import time. When `Thing.__init__` validates
credentials or opens sockets, every module that transitively imports it becomes
unimportable without production secrets — so nothing can be tested or run in
isolation. `lazy(Thing)` returns a stand-in with the same attribute surface that
builds the single real instance on first attribute access instead.
"""

from typing import TypeVar

T = TypeVar("T")


def lazy(factory: type[T]) -> T:
    """Return a proxy that constructs `factory()` once, on first attribute access."""

    class _Lazy:
        _real: T | None = None

        def __getattr__(self, name: str):
            if _Lazy._real is None:
                _Lazy._real = factory()
            return getattr(_Lazy._real, name)

    return _Lazy()  # type: ignore[return-value]
