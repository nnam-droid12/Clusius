"""Scans a workload's Dockerfile(s) and Python dependency manifests for x86-only
assumptions that would break (or silently under-perform) on Arm64: CUDA calls,
AVX-specific compiler flags, unpinned/x86-only base images, and x86-only wheel
constraints. This is the "Analyze" stage of the Clusius pipeline (see ARCHITECTURE.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Severity = Literal["blocker", "warning", "info"]

_CUDA_PATTERNS = [
    re.compile(r"\bnvidia/cuda\b"),
    re.compile(r"\btorch\.cuda\b"),
    re.compile(r"\bCUDA_VISIBLE_DEVICES\b"),
    re.compile(r"\bnvcc\b"),
    re.compile(r"\bnvidia-smi\b"),
]

_AVX_FLAG_PATTERN = re.compile(r"-m(avx512\w*|avx2|avx|sse4(\.\d)?|fma)\b")

_X86_WHEEL_PATTERNS = [
    re.compile(r"manylinux(?:1|2010|2014|_2_\d+)_x86_64"),
    re.compile(r"cp3\d+-cp3\d+-(?:manylinux\w*_)?x86_64\.whl"),
]

_FROM_LINE = re.compile(r"^\s*FROM\s+(?P<image>\S+)", re.IGNORECASE | re.MULTILINE)


@dataclass
class Finding:
    severity: Severity
    category: str
    file: str
    line: int
    message: str


@dataclass
class AnalysisReport:
    findings: list[Finding]

    @property
    def blockers(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "blocker"]

    @property
    def is_migration_blocked(self) -> bool:
        return len(self.blockers) > 0


def _scan_dockerfile(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        for pattern in _CUDA_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        severity="blocker",
                        category="cuda",
                        file=str(path),
                        line=lineno,
                        message=f"CUDA-specific reference {pattern.pattern!r} has no Arm64 CPU "
                        "equivalent; route this workload through an Arm CPU-optimized backend "
                        "(llama.cpp/KleidiAI or vLLM/ACL) instead.",
                    )
                )
        if _AVX_FLAG_PATTERN.search(line):
            findings.append(
                Finding(
                    severity="blocker",
                    category="avx-flags",
                    file=str(path),
                    line=lineno,
                    message="x86-only AVX/SSE compiler flag has no Arm equivalent; drop it for "
                    "the Arm64 build and rely on GGML_NATIVE / ACL's own architecture "
                    "detection instead.",
                )
            )

    for match in _FROM_LINE.finditer(text):
        image = match.group("image")
        lineno = text.count("\n", 0, match.start()) + 1
        if "nvidia/cuda" in image:
            findings.append(
                Finding(
                    severity="blocker",
                    category="base-image",
                    file=str(path),
                    line=lineno,
                    message=f"base image {image!r} is a CUDA image with no Arm64 build; swap for "
                    "an Arm-optimized CPU base (see infra/docker/llamacpp-kleidi.Dockerfile or "
                    "infra/docker/vllm-acl.Dockerfile).",
                )
            )
        elif ":" not in image or image.endswith(":latest"):
            findings.append(
                Finding(
                    severity="warning",
                    category="base-image",
                    file=str(path),
                    line=lineno,
                    message=f"base image {image!r} is unpinned; pin an explicit tag (and ideally "
                    "a digest) so the Arm64 rebuild resolves the same upstream image the x86 "
                    "baseline used.",
                )
            )

    return findings


def _scan_python_manifest(path: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in _X86_WHEEL_PATTERNS:
            if pattern.search(line):
                findings.append(
                    Finding(
                        severity="blocker",
                        category="x86-wheel",
                        file=str(path),
                        line=lineno,
                        message=f"pinned wheel/platform tag {pattern.pattern!r} is x86_64-only; "
                        "re-resolve against aarch64 wheels (or build from source) for the "
                        "Arm64 image.",
                    )
                )
    return findings


_DOCKERFILE_GLOBS = ("Dockerfile", "*.Dockerfile", "Dockerfile.*")
_PYTHON_MANIFEST_GLOBS = ("requirements*.txt", "pyproject.toml")


def scan_workload(workload_dir: Path) -> AnalysisReport:
    findings: list[Finding] = []

    seen: set[Path] = set()
    for glob in _DOCKERFILE_GLOBS:
        for path in workload_dir.rglob(glob):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            findings.extend(
                _scan_dockerfile(path, path.read_text(encoding="utf-8", errors="ignore"))
            )

    seen.clear()
    for glob in _PYTHON_MANIFEST_GLOBS:
        for path in workload_dir.rglob(glob):
            if path in seen or not path.is_file():
                continue
            seen.add(path)
            findings.extend(
                _scan_python_manifest(path, path.read_text(encoding="utf-8", errors="ignore"))
            )

    return AnalysisReport(findings=findings)
