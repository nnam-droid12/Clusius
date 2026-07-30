from __future__ import annotations

from clusius_core.migrate.model_prep import ensure_git_lfs_installed, prepare_gguf_models
from clusius_core.migrate.ssh_runner import CommandResult


class FakeRunner:
    def __init__(self, scripted: dict[str, CommandResult] | None = None) -> None:
        self.commands: list[str] = []
        self._scripted = scripted or {}

    def run(self, command: str, raise_on_failure: bool = True) -> CommandResult:
        self.commands.append(command)
        for substring, result in self._scripted.items():
            if substring in command:
                return result
        return CommandResult(command=command, exit_code=0, stdout="", stderr="")


def test_ensure_git_lfs_installed_skips_when_present() -> None:
    runner = FakeRunner(
        scripted={"command -v git-lfs": CommandResult("", 0, "/usr/bin/git-lfs", "")}
    )

    ensure_git_lfs_installed(runner)  # type: ignore[arg-type]

    assert not any("apt-get install" in c for c in runner.commands)


def test_ensure_git_lfs_installed_installs_when_missing() -> None:
    runner = FakeRunner(scripted={"command -v git-lfs": CommandResult("", 1, "", "not found")})

    ensure_git_lfs_installed(runner)  # type: ignore[arg-type]

    assert any("apt-get install" in c and "git-lfs" in c for c in runner.commands)


def test_prepare_gguf_models_clones_converts_and_quantizes() -> None:
    runner = FakeRunner()

    result = prepare_gguf_models(
        runner,  # type: ignore[arg-type]
        image_tag="clusius-llamacpp:latest",
        hf_model_id="Qwen/Qwen2.5-0.5B-Instruct",
        quant_types=["Q4_K_M", "Q8_0"],
        workdir="/opt/clusius/models",
    )

    assert result == {
        "Q4_K_M": "/opt/clusius/models/model-Q4_K_M.gguf",
        "Q8_0": "/opt/clusius/models/model-Q8_0.gguf",
    }

    clone_cmd = next(c for c in runner.commands if "git clone" in c)
    assert "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct" in clone_cmd

    convert_cmd = next(c for c in runner.commands if "convert_hf_to_gguf.py" in c)
    assert "--outfile /opt/clusius/models/model-f16.gguf" in convert_cmd
    assert "--outtype f16" in convert_cmd

    quantize_cmds = [c for c in runner.commands if "llama-quantize" in c]
    assert len(quantize_cmds) == 2
    assert any(
        "model-f16.gguf /opt/clusius/models/model-Q4_K_M.gguf Q4_K_M" in c for c in quantize_cmds
    )
    assert any(
        "model-f16.gguf /opt/clusius/models/model-Q8_0.gguf Q8_0" in c for c in quantize_cmds
    )


def test_prepare_gguf_models_returns_empty_dict_for_no_quants() -> None:
    runner = FakeRunner()

    result = prepare_gguf_models(
        runner,  # type: ignore[arg-type]
        image_tag="clusius-llamacpp:latest",
        hf_model_id="Qwen/Qwen2.5-0.5B-Instruct",
        quant_types=[],
    )

    assert result == {}
