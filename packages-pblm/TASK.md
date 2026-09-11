Concurrent Package Installer

**Intro:** Build the fetch-and-install layer of a package manager.
Packages have dependencies. They're served by several mirrors of varying speed
and reliability. `pkgmgr/registry.py` is given to you — treat it as a
third-party library you've never seen. `pkgmgr/installer.py` is the module you
extend.

**The one hard rule:** all concurrency goes through `concurrent.futures`. No raw
`threading.Thread`, no `asyncio`, no `multiprocessing`. Docs:
https://docs.python.org/3/library/concurrent.futures.html

Run the baseline:

```
python3 run.py
```

It takes about 6.4 seconds. That's the number to beat.

---

## Task 1 — Resolve the graph concurrently

Implement `resolve_graph(root)`. Return metadata for `root` and every
transitive dependency.

`get_metadata` costs ~100ms per call. Eleven packages serially is over a
second; you should land well under half that. The graph has diamonds —
several packages depend on `typeutils` — and each package's metadata must be
fetched exactly once.

The wrinkle: you don't know the full node set until you've resolved part of it.
You're submitting work whose results tell you what else to submit.

## Task 2 — Download concurrently, install in order

Implement `install(root, disk)`. Downloads overlap; commits respect dependency
order. `Disk.commit` raises `InstallOrderError` if you get the order wrong, so
it's self-checking.

Target: under 4 seconds.

## Task 3 — Race the mirrors

Implement `fetch_fastest(name, version, mirrors)`. Ask several mirrors at once
and take whoever answers first.

Complications that are in the data, not hypothetical: `cdn-edge` is fast but
only carries packages under 900kb, so it raises `PackageNotFound` for the big
ones. `eu-west` is fast and fails a quarter of the time. `archive` never fails
but is slow. A mirror failing must not sink the whole fetch; only raise
`PackageNotFound` when every mirror is exhausted.

Think about what you do with the losing futures once you have a winner.

## Task 4 — Install as things become ready

Implement `install_streaming(root, disk)`. Don't wait for all downloads before
committing anything. The moment a package's payload has landed *and* all of its
dependencies are already installed, commit it.

This is the task where the data structure matters. A downloaded package may
unblock several others, and those may unblock more.

## Task 5 — Cancellation and a failure budget

Implement `install_bounded(...)`. Abort if more than `failure_budget` downloads
fail outright, or if `timeout` elapses. Cancel what hasn't started, leave the
disk consistent, raise, and be able to say what made it and what didn't.

---

## Checking yourself

```
python3 check.py 2      # one task
python3 check.py all
```

Run these *after* you think a task is done.
