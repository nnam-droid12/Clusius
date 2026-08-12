"""The bounded MVP search space (see ARCHITECTURE.md / build brief §5) and the
per-trial config Optuna samples from it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import optuna

from clusius_core.models import Backend, KVCachePrecision


@dataclass
class SearchSpace:
    threads: list[int]
    batch_sizes: list[int]
    context_lengths: list[int]
    backends: list[Backend] = field(default_factory=lambda: ["llamacpp", "vllm"])
    llamacpp_quants: list[str] = field(default_factory=lambda: ["Q8_0", "Q4_K_M", "Q4_0"])
    vllm_quants: list[str] = field(default_factory=lambda: ["int8", "int4"])
    kv_cache_precisions: list[KVCachePrecision] = field(default_factory=lambda: ["fp16", "int8"])
    core_pinning_options: list[bool] = field(default_factory=lambda: [True, False])


@dataclass
class TrialConfig:
    backend: Backend
    quant: str
    threads: int
    core_pinning: bool
    batch_size: int
    kv_cache_precision: KVCachePrecision
    context_length: int


def quants_for_backend(space: SearchSpace, backend: Backend) -> list[str]:
    return space.llamacpp_quants if backend == "llamacpp" else space.vllm_quants


def suggest_trial(trial: optuna.Trial, space: SearchSpace) -> TrialConfig:
    # Optuna's own stubs type suggest_categorical's return as the broad union of
    # possible choice types, not the specific Literal we sample from — a cast, not a
    # real type hole, since `space.backends`/`space.kv_cache_precisions` are themselves
    # typed to only ever contain valid Backend/KVCachePrecision values.
    backend = cast(Backend, trial.suggest_categorical("backend", space.backends))
    # Quant choices are backend-conditional, so they get a per-backend param name —
    # Optuna's standard idiom for a conditional search space.
    quant = trial.suggest_categorical(f"quant_{backend}", quants_for_backend(space, backend))
    threads = trial.suggest_categorical("threads", space.threads)
    core_pinning = trial.suggest_categorical("core_pinning", space.core_pinning_options)
    batch_size = trial.suggest_categorical("batch_size", space.batch_sizes)
    kv_cache_precision = cast(
        KVCachePrecision,
        trial.suggest_categorical("kv_cache_precision", space.kv_cache_precisions),
    )
    context_length = trial.suggest_categorical("context_length", space.context_lengths)

    return TrialConfig(
        backend=backend,
        quant=quant,
        threads=threads,
        core_pinning=core_pinning,
        batch_size=batch_size,
        kv_cache_precision=kv_cache_precision,
        context_length=context_length,
    )
