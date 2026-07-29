"""Target-mode remote execution: runs build/serve/benchmark commands on an existing
C4A (or x86 baseline) instance over SSH, using Fabric. This is the default mode —
Clusius never needs to hold cloud credentials, it just needs an SSH endpoint.

The Fabric `Connection` factory is injectable so this module's orchestration logic
(command construction, result handling, error surfacing) can be unit-tested without a
real SSH server.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from fabric import Connection


@dataclass
class TargetHost:
    host: str
    user: str
    ssh_key_path: str | None = None
    price_per_hour: float | None = None
    port: int = 22


@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class _RunResult(Protocol):
    exited: int
    stdout: str
    stderr: str


class _ConnectionLike(Protocol):
    def run(self, command: str, hide: bool, warn: bool) -> _RunResult: ...
    def put(self, local: str, remote: str) -> Any: ...
    def get(self, remote: str, local: str) -> Any: ...


ConnectionFactory = Callable[..., _ConnectionLike]


class TargetRunner:
    """Executes commands on a single target host over SSH."""

    def __init__(
        self, target: TargetHost, connection_factory: ConnectionFactory = Connection
    ) -> None:
        self.target = target
        self._connection_factory = connection_factory

    def _connect(self) -> _ConnectionLike:
        connect_kwargs: dict[str, Any] = {}
        if self.target.ssh_key_path:
            connect_kwargs["key_filename"] = self.target.ssh_key_path
        return self._connection_factory(
            host=self.target.host,
            user=self.target.user,
            port=self.target.port,
            connect_kwargs=connect_kwargs,
        )

    def run(self, command: str, raise_on_failure: bool = True) -> CommandResult:
        connection = self._connect()
        raw = connection.run(command, hide=True, warn=True)
        result = CommandResult(
            command=command, exit_code=raw.exited, stdout=raw.stdout, stderr=raw.stderr
        )
        if raise_on_failure and not result.ok:
            raise RuntimeError(
                f"remote command failed on {self.target.host} (exit {result.exit_code}): "
                f"{command!r}\nstderr: {result.stderr}"
            )
        return result

    def put(self, local_path: str, remote_path: str) -> None:
        self._connect().put(local_path, remote_path)

    def get(self, remote_path: str, local_path: str) -> None:
        self._connect().get(remote_path, local_path)

    def run_many(self, commands: list[str], raise_on_failure: bool = True) -> list[CommandResult]:
        return [self.run(cmd, raise_on_failure=raise_on_failure) for cmd in commands]
