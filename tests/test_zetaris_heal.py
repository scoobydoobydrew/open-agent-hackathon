"""The Zetaris recovery logic, with Docker and the gateway simulated (no containers are touched)."""
import subprocess

import pytest

from agent import zetaris_heal as zh


class Fake:
    def __init__(self, driver_state="exited", health="healthy", docker_up=True):
        self.calls, self.driver_state, self.health, self.docker_up = [], driver_state, health, docker_up

    def __call__(self, args, cwd, timeout=300):
        self.calls.append(" ".join(args))
        out = ""
        rc = 0
        if args[:2] == ["docker", "info"]:
            rc = 0 if self.docker_up else 1
        elif args[:3] == ["docker", "compose", "ps"]:
            out = "abc123\n"
        elif args[:2] == ["docker", "inspect"]:
            out = (self.driver_state if "State.Status" in args[3] else self.health) + "\n"
        elif "--force-recreate" in args:
            self.driver_state = "running"
        return subprocess.CompletedProcess(args, rc, out, "")


@pytest.fixture
def stack(tmp_path, monkeypatch):
    (tmp_path / "docker-compose.yml").write_text("services: {}")
    monkeypatch.setenv("ZETARIS_DIR", str(tmp_path))
    monkeypatch.setattr(zh.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(zh.time, "sleep", lambda s: None)
    return monkeypatch


def test_nothing_to_do_when_the_gateway_answers(stack):
    stack.setattr(zh, "gateway_up", lambda: True)
    assert zh.heal() == "already-up"


def test_stopped_driver_is_recreated_and_the_stack_comes_back(stack):
    fake = Fake(driver_state="exited")
    answers = iter([False, True])
    stack.setattr(zh, "gateway_up", lambda: next(answers))
    stack.setattr(zh, "_run", fake)
    assert zh.heal() == "recovered"
    assert any("--force-recreate --no-deps driver" in c for c in fake.calls)
    assert fake.calls[1] == "docker compose up -d"


def test_a_running_driver_is_left_alone(stack):
    fake = Fake(driver_state="running")
    answers = iter([False, True])
    stack.setattr(zh, "gateway_up", lambda: next(answers))
    stack.setattr(zh, "_run", fake)
    assert zh.heal() == "recovered" and not any("--force-recreate" in c for c in fake.calls)


def test_clear_messages_when_docker_is_the_problem(stack, tmp_path):
    stack.setattr(zh, "gateway_up", lambda: False)
    stack.setattr(zh, "_run", Fake(docker_up=False))
    assert zh.heal() == "docker-not-running"
    stack.setattr(zh.shutil, "which", lambda name: None)
    assert zh.heal() == "docker-missing"
    stack.setenv("ZETARIS_DIR", str(tmp_path / "missing"))
    stack.setattr(zh.shutil, "which", lambda name: "/usr/bin/docker")
    assert zh.heal() == "no-compose-dir"


def test_gives_up_instead_of_hanging(stack):
    stack.setattr(zh, "gateway_up", lambda: False)
    stack.setattr(zh, "_run", Fake(driver_state="running", health="starting"))
    assert zh.heal(wait=0) == "timeout"
