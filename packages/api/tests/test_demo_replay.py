from __future__ import annotations

from pathlib import Path

from clusius_api.scripts.demo_replay import _commit_or_mtime


def test_commit_or_mtime_falls_back_to_mtime_outside_git(tmp_path: Path) -> None:
    # Regression test: an earlier version picked the "latest" evidence file via a plain
    # filename sort, which put "...-13.run-detail.json" before "...-8.run-detail.json"
    # (lexicographic: '1' < '8'), silently replaying a stale run. Sorting by real
    # timestamp instead of filename fixes it regardless of naming scheme.
    older = tmp_path / "2026-08-01-real-e2e-validation-8.run-detail.json"
    newer = tmp_path / "2026-08-01-real-e2e-validation-13.run-detail.json"
    older.write_text("{}", encoding="utf-8")
    newer.write_text("{}", encoding="utf-8")

    import os
    import time

    now = time.time()
    os.utime(older, (now - 100, now - 100))
    os.utime(newer, (now, now))

    candidates = [older, newer]
    latest = max(candidates, key=_commit_or_mtime)

    assert latest == newer
