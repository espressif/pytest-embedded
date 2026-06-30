"""Multi-DUT synchronization helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_expect_patterns(*patterns: Any, **kwargs: Any) -> tuple[tuple[Any, ...], dict[str, Any]]:
    """Match :meth:`~pytest_embedded.dut.Dut.expect` / ``expect_exact``: allow ``pattern=`` keyword."""
    out_kw = dict(kwargs)
    if 'pattern' in out_kw:
        if patterns:
            raise TypeError('multiple values for argument pattern')
        patterns = (out_kw.pop('pattern'),)
    return patterns, out_kw


class DutGroupMemberError(Exception):
    """Raised when a parallel :class:`DutGroup` operation fails on one member.

    The original exception (e.g. :exc:`pexpect.TIMEOUT`) is chained as :attr:`__cause__`.
    Use :attr:`member_name`, :attr:`member_index`, and :attr:`group_name` for filtering
    or reporting.
    """

    def __init__(
        self,
        message: str,
        *,
        member_index: int,
        member_name: str,
        group_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.member_index = member_index
        self.member_name = member_name
        self.group_name = group_name


# ---------------------------------------------------------------------------
# DutGroup class
# ---------------------------------------------------------------------------


class DutGroup:
    """Transparent proxy that forwards method calls to every wrapped
    :class:`~pytest_embedded.dut.Dut` **in parallel**.

    Create one from any number of DUTs::

        group = DutGroup(dut[0], dut[1])
        # or
        group = DutGroup(*dut)

    Any :class:`~pytest_embedded.dut.Dut` method can be called on the group.
    It runs on **every** member concurrently and returns a list of per-DUT
    results::

        group.expect_exact('[READY]', timeout=120)
        group.write(ssid)

    :meth:`expect` and :meth:`expect_exact` additionally support **per-DUT
    patterns** -- pass N patterns for N DUTs::

        group.expect_exact('[AP] ready', '[CLIENT] ready', timeout=120)

    Keyword Args:
        names: Optional label per DUT (same length as *duts*), used in logs and in
            :exc:`DutGroupMemberError`. If omitted, defaults to ``dut-0``, ``dut-1``, ...
        group_name: Optional label for this group in logs and exception messages.
    """

    def __init__(
        self,
        *duts: Any,
        names: Sequence[str] | None = None,
        group_name: str | None = None,
    ) -> None:
        if not duts:
            raise ValueError('DutGroup requires at least one DUT')
        self._duts: tuple[Any, ...] = duts
        n = len(duts)
        if names is not None:
            if len(names) != n:
                raise ValueError(f'names must have length {n} (same as number of DUTs), got {len(names)}')
            self._names: tuple[str, ...] = tuple(str(x) for x in names)
        else:
            self._names = tuple(f'dut-{i}' for i in range(n))
        self._group_name = group_name

    # -- container protocol --------------------------------------------------

    @property
    def duts(self) -> tuple[Any, ...]:
        """The underlying DUT objects (read-only)."""
        return self._duts

    @property
    def names(self) -> tuple[str, ...]:
        """Human-readable member labels (same order as :attr:`duts`)."""
        return self._names

    @property
    def group_name(self) -> str | None:
        """Optional label for this group, if set in the constructor."""
        return self._group_name

    def __len__(self) -> int:
        return len(self._duts)

    def __getitem__(self, index: int | slice) -> Any:
        return self._duts[index]

    def __iter__(self) -> Iterator[Any]:
        return iter(self._duts)

    def __repr__(self) -> str:
        parts = [repr(d) for d in self._duts]
        if self._group_name is not None:
            parts.insert(0, f'group_name={self._group_name!r}')
        parts.insert(0, f'names={self._names!r}')
        return f'DutGroup({", ".join(parts)})'

    def _format_member_head(self, member_index: int) -> str:
        gn = self._group_name
        name = self._names[member_index]
        if gn:
            return f'DutGroup {gn!r} member {name!r} (index {member_index})'
        return f'DutGroup member {name!r} (index {member_index})'

    def _wrap_member_failure(
        self,
        member_index: int,
        cause: BaseException,
        *,
        operation: str | None,
    ) -> DutGroupMemberError:
        head = self._format_member_head(member_index)
        op = f' during {operation}' if operation else ''
        logger.error('%s failed%s: %s', head, op, cause, exc_info=cause)
        msg_body = f'{head} failed{op}.\n\n{cause}'
        return DutGroupMemberError(
            msg_body,
            member_index=member_index,
            member_name=self._names[member_index],
            group_name=self._group_name,
        )

    def _run_parallel(
        self,
        callables: list[Any],
        args_per_call: list[tuple],
        kwargs_per_call: list[dict],
        *,
        operation: str | None = None,
    ) -> list[Any]:
        """Run *callables* concurrently, one per DUT, and return ordered results."""
        n = len(callables)
        if n == 1:
            try:
                return [callables[0](*args_per_call[0], **kwargs_per_call[0])]
            except BaseException as e:
                raise self._wrap_member_failure(0, e, operation=operation) from e

        results: list[Any] = [None] * n
        executor = ThreadPoolExecutor(max_workers=n)
        future_to_idx = {executor.submit(callables[i], *args_per_call[i], **kwargs_per_call[i]): i for i in range(n)}
        failed_early = False
        try:
            for fut in as_completed(future_to_idx):
                try:
                    results[future_to_idx[fut]] = fut.result()
                except BaseException as e:
                    failed_early = True
                    idx = future_to_idx[fut]
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise self._wrap_member_failure(idx, e, operation=operation) from e
        finally:
            if not failed_early:
                executor.shutdown(wait=True, cancel_futures=False)
        return results

    # -- expect / expect_exact with per-DUT pattern support ------------------

    def _expect_impl(self, method_name: str, *patterns: Any, **kwargs: Any) -> list[Any]:
        """Shared implementation for :meth:`expect` and :meth:`expect_exact`.

        * 1 pattern  -> broadcast to every DUT.
        * N patterns -> one per DUT (positional, same order as constructor).

        Callers must pass patterns already normalized via :func:`_normalize_expect_patterns`.
        """
        n = len(self._duts)
        methods = [getattr(dut, method_name) for dut in self._duts]

        if len(patterns) == 1:
            args_list = [(patterns[0],)] * n
        elif len(patterns) == n:
            args_list = [(p,) for p in patterns]
        else:
            raise ValueError(f'Expected 1 (broadcast) or {n} (per-DUT) patterns, got {len(patterns)}')

        kwargs_list = [dict(kwargs) for _ in range(n)]
        return self._run_parallel(methods, args_list, kwargs_list, operation=method_name)

    def expect(self, *patterns: Any, **kwargs: Any) -> list[Any]:
        """Parallel :meth:`~pytest_embedded.dut.Dut.expect` (regex) across all DUTs.

        Args:
            *patterns: One pattern broadcast to all DUTs, **or** one per DUT
                (positional, same order as constructor). Same as :class:`~pytest_embedded.dut.Dut`,
                you may pass a single pattern as ``pattern=...`` instead of positionally.
            **kwargs: Forwarded to each DUT's ``expect`` call (e.g. ``timeout``).

        Returns:
            Per-DUT match results in the same order as DUTs.
        """
        patterns, kwargs = _normalize_expect_patterns(*patterns, **kwargs)
        return self._expect_impl('expect', *patterns, **kwargs)

    def expect_exact(self, *patterns: Any, **kwargs: Any) -> list[Any]:
        """Parallel :meth:`~pytest_embedded.dut.Dut.expect_exact` (literal) across all DUTs.

        Args:
            *patterns: One pattern broadcast to all DUTs, **or** one per DUT
                (positional, same order as constructor). Same as :class:`~pytest_embedded.dut.Dut`,
                you may pass a single pattern as ``pattern=...`` instead of positionally.
            **kwargs: Forwarded to each DUT's ``expect_exact`` call (e.g. ``timeout``).

        Returns:
            Per-DUT match results in the same order as DUTs.
        """
        patterns, kwargs = _normalize_expect_patterns(*patterns, **kwargs)
        return self._expect_impl('expect_exact', *patterns, **kwargs)

    # -- transparent proxy for everything else -------------------------------

    def __getattr__(self, name: str) -> Any:
        attrs = []
        for dut in self._duts:
            try:
                attrs.append(getattr(dut, name))
            except AttributeError:
                raise AttributeError(f"'{type(dut).__name__}' object has no attribute '{name}'") from None

        if not all(callable(a) for a in attrs):
            return attrs

        def _proxy(*args: Any, **kwargs: Any) -> list[Any]:
            n = len(attrs)
            args_list = [args] * n
            kwargs_list = [dict(kwargs) for _ in range(n)]
            return self._run_parallel(attrs, args_list, kwargs_list, operation=name)

        return _proxy
