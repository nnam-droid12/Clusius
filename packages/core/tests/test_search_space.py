import optuna
from clusius_core.tune.search_space import (
    SearchSpace,
    TrialConfig,
    quants_for_backend,
    suggest_trial,
)


def _space() -> SearchSpace:
    return SearchSpace(threads=[4, 8, 16], batch_sizes=[1, 8, 32], context_lengths=[2048, 4096])


def test_quants_for_backend_llamacpp() -> None:
    space = _space()

    assert quants_for_backend(space, "llamacpp") == space.llamacpp_quants


def test_quants_for_backend_vllm() -> None:
    space = _space()

    assert quants_for_backend(space, "vllm") == space.vllm_quants


def test_suggest_trial_produces_valid_config() -> None:
    space = _space()
    study = optuna.create_study(directions=["maximize", "minimize"])

    def objective(trial: optuna.Trial) -> tuple[float, float]:
        config = suggest_trial(trial, space)
        assert isinstance(config, TrialConfig)
        assert config.backend in space.backends
        assert config.quant in quants_for_backend(space, config.backend)
        assert config.threads in space.threads
        assert config.batch_size in space.batch_sizes
        assert config.context_length in space.context_lengths
        assert config.kv_cache_precision in space.kv_cache_precisions
        assert config.core_pinning in space.core_pinning_options
        return 1.0, 1.0

    study.optimize(objective, n_trials=20)

    assert len(study.trials) == 20


def test_suggest_trial_uses_backend_conditional_quant_param() -> None:
    space = _space()
    study = optuna.create_study(directions=["maximize", "minimize"])
    seen_backends = set()

    def objective(trial: optuna.Trial) -> tuple[float, float]:
        config = suggest_trial(trial, space)
        seen_backends.add(config.backend)
        return 1.0, 1.0

    study.optimize(objective, n_trials=30)

    # with 30 trials over 2 backends, both should appear at least once
    assert seen_backends == {"llamacpp", "vllm"}
