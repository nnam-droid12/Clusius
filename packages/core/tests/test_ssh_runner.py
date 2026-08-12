from dataclasses import dataclass
from typing import Any

import pytest
from clusius_core.migrate.ssh_runner import CommandResult, TargetHost, TargetRunner


@dataclass
class _FakeRunResult:
    exited: int
    stdout: str
    stderr: str


class _FakeConnection:
    def __init__(
        self, script: dict[str, _FakeRunResult], calls: list[Any], **kwargs: Any
    ) -> None:
        self.kwargs = kwargs
        self._script = script
        self._calls = calls

    def run(self, command: str, hide: bool, warn: bool) -> _FakeRunResult:
        self._calls.append(("run", command, self.kwargs))
        return self._script.get(command, _FakeRunResult(exited=0, stdout="", stderr=""))

    def put(self, local: str, remote: str) -> None:
        self._calls.append(("put", local, remote))

    def get(self, remote: str, local: str) -> None:
        self._calls.append(("get", remote, local))


def _make_target() -> TargetHost:
    return TargetHost(
        host="10.0.0.5", user="clusius", ssh_key_path="/keys/id_ed25519", price_per_hour=0.5
    )


def _make_runner(
    script: dict[str, _FakeRunResult] | None = None, calls: list[Any] | None = None
) -> tuple[TargetRunner, list[Any]]:
    calls = calls if calls is not None else []
    script = script or {}
    factory = lambda **kw: _FakeConnection(script, calls, **kw)  # noqa: E731
    return TargetRunner(_make_target(), connection_factory=factory), calls


def test_run_returns_command_result_on_success() -> None:
    script = {"echo hi": _FakeRunResult(exited=0, stdout="hi\n", stderr="")}
    runner, _ = _make_runner(script)

    result = runner.run("echo hi")

    assert isinstance(result, CommandResult)
    assert result.ok
    assert result.stdout == "hi\n"


def test_connection_factory_receives_target_details() -> None:
    runner, calls = _make_runner()

    runner.run("true")

    _, _, kwargs = calls[0]
    assert kwargs["host"] == "10.0.0.5"
    assert kwargs["user"] == "clusius"
    assert kwargs["connect_kwargs"]["key_filename"] == "/keys/id_ed25519"


def test_run_raises_on_failure_by_default() -> None:
    script = {"false": _FakeRunResult(exited=1, stdout="", stderr="command not found")}
    runner, _ = _make_runner(script)

    with pytest.raises(RuntimeError, match="command not found"):
        runner.run("false")


def test_run_does_not_raise_when_raise_on_failure_false() -> None:
    script = {"false": _FakeRunResult(exited=1, stdout="", stderr="boom")}
    runner, _ = _make_runner(script)

    result = runner.run("false", raise_on_failure=False)

    assert not result.ok
    assert result.exit_code == 1


def test_run_many_executes_in_order() -> None:
    runner, calls = _make_runner()

    results = runner.run_many(["cmd1", "cmd2", "cmd3"])

    assert [r.command for r in results] == ["cmd1", "cmd2", "cmd3"]
    assert [c[1] for c in calls] == ["cmd1", "cmd2", "cmd3"]


def test_put_and_get_delegate_to_connection() -> None:
    runner, calls = _make_runner()

    runner.put("local.gguf", "/remote/model.gguf")
    runner.get("/remote/result.json", "local-result.json")

    assert ("put", "local.gguf", "/remote/model.gguf") in calls
    assert ("get", "/remote/result.json", "local-result.json") in calls
