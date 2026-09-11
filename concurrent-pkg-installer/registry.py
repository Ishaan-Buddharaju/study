"""
pkgmgr.registry — the package registry layer.

This module is GIVEN to you. Do not modify it. Read it the way you would read
an unfamiliar third-party library: figure out the contract, then build on top.

Every network-ish call here is slow on purpose. Mirrors are unreliable on
purpose. That is the point of the exercise.
"""

from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

_DATA = Path(__file__).resolve().parent.parent / "data" / "packages.json"


class MirrorError(RuntimeError):
    """Raised when a mirror fails to serve a package."""


class PackageNotFound(KeyError):
    """Raised when no mirror carries the requested package."""


class InstallOrderError(RuntimeError):
    """Raised when a package is installed before its dependencies."""


@dataclass(frozen=True)
class PackageMeta:
    name: str
    version: str
    deps: tuple[str, ...]
    size_kb: int


class Mirror:
    """A single package mirror.

    Mirrors differ in latency and reliability. Some carry only a subset of
    packages. A mirror that does not carry a package raises PackageNotFound;
    a mirror having a bad day raises MirrorError.
    """

    def __init__(self, name: str, *, latency: float, failure_rate: float,
                 carries: set[str] | None = None):
        self.name = name
        self._latency = latency
        self._failure_rate = failure_rate
        self._carries = carries
        self._rng = random.Random(hash(name) & 0xFFFF)
        self._lock = threading.Lock()
        self.request_count = 0

    def carries(self, package: str) -> bool:
        return self._carries is None or package in self._carries

    def fetch(self, package: str, version: str) -> bytes:
        """Download a package payload. Blocking. Slow. Sometimes fails.

        Raises PackageNotFound if this mirror does not carry the package.
        Raises MirrorError on a transient failure — retrying may work.
        """
        with self._lock:
            self.request_count += 1
        meta = _REGISTRY.get(package)
        if meta is None or not self.carries(package):
            time.sleep(self._latency * 0.2)
            raise PackageNotFound(f"{self.name} does not carry {package!r}")
        # Bigger packages take longer.
        time.sleep(self._latency * (1 + meta.size_kb / 4000))
        with self._lock:
            roll = self._rng.random()
        if roll < self._failure_rate:
            raise MirrorError(f"{self.name} failed serving {package}=={version}")
        return f"<payload {package}=={version} from {self.name}>".encode()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Mirror {self.name} latency={self._latency}>"


def _load() -> dict[str, PackageMeta]:
    raw = json.loads(_DATA.read_text())
    return {
        name: PackageMeta(name, spec["version"], tuple(spec["deps"]), spec["size_kb"])
        for name, spec in raw.items()
    }


_REGISTRY: dict[str, PackageMeta] = _load()


def get_metadata(package: str) -> PackageMeta:
    """Look up a package's version and direct dependencies.

    Blocking, and not free — assume roughly 100ms of network time per call.
    """
    time.sleep(0.1)
    meta = _REGISTRY.get(package)
    if meta is None:
        raise PackageNotFound(package)
    return meta


def list_mirrors() -> list[Mirror]:
    """Return the configured mirrors, fastest first (allegedly)."""
    all_pkgs = set(_REGISTRY)
    return [
        Mirror("eu-west", latency=0.30, failure_rate=0.25),
        Mirror("us-east", latency=0.45, failure_rate=0.05),
        # The archive is slow and complete. The CDN is fast and partial.
        Mirror("cdn-edge", latency=0.15, failure_rate=0.10,
               carries={p for p in all_pkgs if _REGISTRY[p].size_kb < 900}),
        Mirror("archive", latency=0.90, failure_rate=0.0),
    ]


class Disk:
    """The install target. Enforces dependency ordering.

    This is the oracle for Task 2 onward: if your install order is wrong,
    commit() raises rather than silently succeeding.
    """

    def __init__(self) -> None:
        self._installed: list[str] = []
        self._lock = threading.Lock()

    def commit(self, package: str, payload: bytes) -> None:
        meta = _REGISTRY[package]
        with self._lock:
            missing = [d for d in meta.deps if d not in self._installed]
            if missing:
                raise InstallOrderError(
                    f"cannot install {package}: missing {', '.join(sorted(missing))}"
                )
            if package in self._installed:
                raise InstallOrderError(f"{package} installed twice")
            self._installed.append(package)

    @property
    def installed(self) -> list[str]:
        with self._lock:
            return list(self._installed)
