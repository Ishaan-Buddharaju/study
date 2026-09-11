"""
Self-check harness. Run `python3 check.py 2` to check Task 2, etc.
`python3 check.py all` runs everything implemented so far.

These tell you whether your answer is correct. They do not tell you how to
write it, and a real interviewer would not hand you them. Use them AFTER you
think you're done, not while you're working.
"""

from __future__ import annotations

import sys
import time

from pkgmgr import installer
from pkgmgr.registry import Disk, InstallOrderError, PackageNotFound, list_mirrors

ROOT = "webapp"
EXPECTED = {
    "webapp", "httpserver", "orm", "templating", "dbdriver", "schema",
    "netcore", "binproto", "parsercore", "typeutils", "logging",
}


def _ok(msg): print(f"  PASS  {msg}")
def _no(msg): print(f"  FAIL  {msg}")


def check1() -> bool:
    t = time.perf_counter()
    graph = installer.resolve_graph(ROOT)
    dt = time.perf_counter() - t
    good = True
    if set(graph) != EXPECTED:
        _no(f"wrong node set; missing {EXPECTED - set(graph)}, extra {set(graph) - EXPECTED}")
        good = False
    else:
        _ok(f"resolved all {len(graph)} packages")
    # 11 packages serially would be ~1.1s. Concurrent should be well under.
    if dt > 0.65:
        _no(f"took {dt:.2f}s — too slow, metadata isn't overlapping (or you're re-fetching diamonds)")
        good = False
    else:
        _ok(f"resolved in {dt:.2f}s")
    return good


def _order_valid(order: list[str], graph) -> bool:
    pos = {n: i for i, n in enumerate(order)}
    for name, meta in graph.items():
        for dep in meta.deps:
            if pos.get(dep, 1 << 30) > pos.get(name, -1):
                _no(f"{name} installed before its dependency {dep}")
                return False
    return True


def _check_install(fn, label: str, budget: float) -> bool:
    disk = Disk()
    t = time.perf_counter()
    order = fn(ROOT, disk)
    dt = time.perf_counter() - t
    good = True
    if set(order) != EXPECTED:
        _no(f"{label}: wrong package set")
        good = False
    if disk.installed != order:
        _no(f"{label}: returned order doesn't match what you committed")
        good = False
    graph = {n: __import__("pkgmgr.registry", fromlist=["x"])._REGISTRY[n] for n in EXPECTED}
    if not _order_valid(order, graph):
        good = False
    else:
        _ok(f"{label}: install order respects dependencies")
    if dt > budget:
        _no(f"{label}: took {dt:.1f}s, target is under {budget:.0f}s (sequential baseline ~6.4s)")
        good = False
    else:
        _ok(f"{label}: completed in {dt:.1f}s")
    return good


def check2() -> bool:
    return _check_install(installer.install, "install", 4.0)


def check3() -> bool:
    mirrors = list_mirrors()
    good = True
    from pkgmgr.registry import _REGISTRY
    # mathcore is 2100kb -> not on cdn-edge. Must still succeed.
    for pkg in ("mathcore", "typeutils", "netcore"):
        try:
            t = time.perf_counter()
            payload = installer.fetch_fastest(pkg, _REGISTRY[pkg].version, mirrors)
            dt = time.perf_counter() - t
            if not payload:
                _no(f"fetch_fastest({pkg}) returned nothing")
                good = False
            else:
                _ok(f"fetched {pkg} in {dt:.2f}s")
        except Exception as exc:
            _no(f"fetch_fastest({pkg}) raised {type(exc).__name__}: {exc}")
            good = False
    try:
        installer.fetch_fastest("nonesuch", "0.0.0", mirrors)
        _no("fetch_fastest should raise PackageNotFound for an unknown package")
        good = False
    except PackageNotFound:
        _ok("raises PackageNotFound when no mirror carries it")
    except Exception as exc:
        _no(f"raised {type(exc).__name__} instead of PackageNotFound")
        good = False
    return good


def check4() -> bool:
    return _check_install(installer.install_streaming, "install_streaming", 3.5)


def check5() -> bool:
    good = True
    disk = Disk()
    try:
        installer.install_bounded(ROOT, disk, timeout=0.5)
        _no("timeout=0.5 should have aborted the install")
        good = False
    except Exception as exc:
        _ok(f"aborted under timeout with {type(exc).__name__}")
    if len(disk.installed) == len(EXPECTED):
        _no("everything installed despite the timeout")
        good = False
    disk2 = Disk()
    try:
        order = installer.install_bounded(ROOT, disk2, timeout=30, failure_budget=99)
        if set(order) == EXPECTED:
            _ok("completes normally when the budget is generous")
        else:
            _no("incomplete install under a generous budget")
            good = False
    except Exception as exc:
        _no(f"raised {type(exc).__name__} under a generous budget: {exc}")
        good = False
    return good


CHECKS = {1: check1, 2: check2, 3: check3, 4: check4, 5: check5}

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    todo = CHECKS.keys() if arg == "all" else [int(arg)]
    for n in todo:
        print(f"\nTask {n}")
        try:
            CHECKS[n]()
        except NotImplementedError:
            print("  SKIP  not implemented yet")
        except Exception as exc:
            print(f"  ERROR {type(exc).__name__}: {exc}")
