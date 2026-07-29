from pathlib import Path

from clusius_core.analyze.scanner import scan_workload


def test_detects_cuda_base_image(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04\nRUN pip install torch\n", encoding="utf-8"
    )

    report = scan_workload(tmp_path)

    assert report.is_migration_blocked
    categories = {f.category for f in report.blockers}
    assert "base-image" in categories


def test_detects_cuda_python_call(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM python:3.11-slim\nRUN python -c 'import torch; torch.cuda.is_available()'\n",
        encoding="utf-8",
    )

    report = scan_workload(tmp_path)

    assert any(f.category == "cuda" for f in report.findings)


def test_detects_avx_compiler_flags(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM ubuntu:24.04\nRUN gcc -mavx2 -mfma -O3 main.c -o main\n", encoding="utf-8"
    )

    report = scan_workload(tmp_path)

    assert any(f.category == "avx-flags" for f in report.findings)


def test_warns_on_unpinned_base_image(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text("FROM ubuntu\nRUN echo hi\n", encoding="utf-8")

    report = scan_workload(tmp_path)

    assert any(f.severity == "warning" and f.category == "base-image" for f in report.findings)
    assert not report.is_migration_blocked


def test_detects_x86_only_wheel_pin(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "torch @ https://download.pytorch.org/whl/cpu/torch-2.4.0-cp311-cp311-manylinux2014_x86_64.whl\n",
        encoding="utf-8",
    )

    report = scan_workload(tmp_path)

    assert report.is_migration_blocked
    assert any(f.category == "x86-wheel" for f in report.blockers)


def test_clean_workload_has_no_findings(tmp_path: Path) -> None:
    (tmp_path / "Dockerfile").write_text(
        "FROM ubuntu:24.04\nRUN apt-get update\n", encoding="utf-8"
    )
    (tmp_path / "requirements.txt").write_text("httpx==0.27.0\npydantic==2.7.0\n", encoding="utf-8")

    report = scan_workload(tmp_path)

    assert report.findings == []
