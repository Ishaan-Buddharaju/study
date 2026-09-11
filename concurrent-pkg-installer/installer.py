"""
pkgmgr.installer — THIS is the module you extend.

Task 0 below is already written for you. It works, and it is slow and naive.
Read it to learn the registry contract, then work the tasks in TASKS.md.

Rule for the whole exercise: all concurrency must go through
concurrent.futures. No raw threading.Thread, no asyncio, no multiprocessing.
"""

from __future__ import annotations

from .registry import (
    Disk,
    Mirror,
    MirrorError,
    PackageMeta,
    PackageNotFound,
    get_metadata,
    list_mirrors,
)


# ---------------------------------------------------------------------------
# Task 0 — GIVEN. A working, fully sequential installer.
# ---------------------------------------------------------------------------

def install_sequential(root: str, disk: Disk) -> list[str]:
    """Install `root` and everything it depends on, one at a time.

    Correct but slow: metadata lookups and downloads all happen serially,
    and it only ever talks to the first mirror.
    """
    mirror = list_mirrors()[0]
    order: list[str] = []
    seen: set[str] = set()

    def visit(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        meta = get_metadata(name)
        for dep in meta.deps:
            visit(dep)
        order.append(name)

    visit(root)

    for name in order:
        meta = get_metadata(name)
        payload = _fetch_with_retries(mirror, name, meta.version)
        disk.commit(name, payload)
    return order


def _fetch_with_retries(mirror: Mirror, name: str, version: str,
                        attempts: int = 5) -> bytes:
    last: Exception | None = None
    for _ in range(attempts):
        try:
            return mirror.fetch(name, version)
        except MirrorError as exc:
            last = exc
    raise last  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Task 1 — Concurrent metadata resolution.
# ---------------------------------------------------------------------------

def resolve_graph(root: str) -> dict[str, PackageMeta]:
    """Return metadata for `root` and every transitive dependency.

    Resolve concurrently. Each package's metadata must be fetched at most once,
    even though the graph has diamonds.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Task 2 — Concurrent download, ordered install.
# ---------------------------------------------------------------------------

def install(root: str, disk: Disk, *, max_workers: int = 8) -> list[str]:
    """Install `root` and its dependencies.

    Downloads should overlap. Installs must respect dependency order —
    Disk.commit will raise InstallOrderError if you get it wrong.
    Returns the install order.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Task 3 — Race the mirrors.
# ---------------------------------------------------------------------------

def fetch_fastest(name: str, version: str, mirrors: list[Mirror]) -> bytes:
    """Fetch a package from whichever mirror returns it first.

    Mirrors that do not carry the package, or that fail, must not sink the
    fetch — as long as one mirror eventually succeeds, this returns.
    Raise PackageNotFound only if every mirror is exhausted.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Task 4 — Install as dependencies become ready.
# ---------------------------------------------------------------------------

def install_streaming(root: str, disk: Disk, *, max_workers: int = 8) -> list[str]:
    """Install each package the moment its payload is downloaded AND all of
    its dependencies are already installed — not in one batch at the end.

    A leaf package that downloads early should be committed early.
    """
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Task 5 — Cancellation and a failure budget.
# ---------------------------------------------------------------------------

def install_bounded(root: str, disk: Disk, *, max_workers: int = 8,
                    failure_budget: int = 3, timeout: float | None = None) -> list[str]:
    """Like install_streaming, but:

      * if more than `failure_budget` downloads fail outright, abandon the
        install and cancel whatever work has not started;
      * if `timeout` elapses, do the same;
      * either way, leave the disk in a consistent state and raise.

    Report which packages made it and which were cancelled.
    """
    raise NotImplementedError
