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

        def __setattr__(self, name: str, value) -> None:
            # Assignment must reach the real instance too. Without this it
            # landed on the proxy, while the real object's own methods kept
            # reading the old value: rotating GHOST_API_KEY from the cockpit
            # left the old key working and rejected the new one.
            if _Lazy._real is None:
                _Lazy._real = factory()
            setattr(_Lazy._real, name, value)

        def __delattr__(self, name: str) -> None:
            # The counterpart, so unittest.mock.patch can undo what it set.
            if _Lazy._real is None:
                raise AttributeError(name)
            delattr(_Lazy._real, name)

    return _Lazy()  # type: ignore[return-value]
