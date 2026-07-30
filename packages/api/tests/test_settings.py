from clusius_api.settings import ApiSettings


def test_ssh_targets_configured_false_by_default() -> None:
    settings = ApiSettings(_env_file=None)

    assert settings.ssh_targets_configured is False


def test_ssh_targets_configured_true_when_both_hosts_set(monkeypatch) -> None:
    monkeypatch.setenv("CLUSIUS_TARGET_ARM_HOST", "1.2.3.4")
    monkeypatch.setenv("CLUSIUS_TARGET_X86_HOST", "5.6.7.8")

    settings = ApiSettings(_env_file=None)

    assert settings.ssh_targets_configured is True
    assert settings.target_arm_host == "1.2.3.4"
    assert settings.target_x86_host == "5.6.7.8"


def test_ssh_targets_configured_false_when_only_one_host_set(monkeypatch) -> None:
    monkeypatch.setenv("CLUSIUS_TARGET_ARM_HOST", "1.2.3.4")
    monkeypatch.delenv("CLUSIUS_TARGET_X86_HOST", raising=False)

    settings = ApiSettings(_env_file=None)

    assert settings.ssh_targets_configured is False


def test_default_instance_types() -> None:
    settings = ApiSettings(_env_file=None)

    assert settings.target_arm_instance_type == "c4a-standard-2"
    assert settings.target_x86_instance_type == "c4-standard-2"
