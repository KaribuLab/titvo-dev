"""Verify menu lifecycle, remote authorization and credential handling."""

import importlib
import io
import os
from pathlib import Path
from unittest.mock import Mock

import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from titvo_cli import interactive as ui


def console():
    """Capture the terminal dashboard without requiring a physical TTY."""
    return Console(file=io.StringIO(), width=100)


def run_menu(monkeypatch, tmp_path, actions, scan):
    """Inject menu input and project selection while exercising real dispatch."""
    monkeypatch.setattr(
        ui,
        "load_session",
        lambda *args: ui.Session(project=tmp_path, scope_ready=True, model_ready=True),
    )
    monkeypatch.setattr(ui, "pause", lambda: None)
    answers = iter(actions)
    monkeypatch.setattr(ui, "choose", lambda *args: next(answers))

    def project(_console, session, _root):
        session.project = tmp_path
        return True

    monkeypatch.setattr(ui, "select_project", project)
    ui.run_session(console(), tmp_path, Mock(), scan, Mock(), Mock())


def test_completed_scan_returns_to_menu(monkeypatch, tmp_path):
    scan = Mock(side_effect=typer.Exit(0))
    run_menu(monkeypatch, tmp_path, ["scan", "scan", None], scan)
    assert scan.call_count == 2
    assert scan.call_args.kwargs["model"] == "mock"
    assert scan.call_args.kwargs["allow_remote_ai"] is False
    assert scan.call_args.kwargs["output"] == Path(".titvo/reports")


@pytest.mark.parametrize("confirm", ["\r", "l"])
def test_real_exit_choice_closes_session(monkeypatch, tmp_path, confirm):
    """Select the actual Questionary exit option and restore the terminal session."""
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    select = ui.questionary.select
    terminal = console()
    scan = Mock()
    with create_pipe_input() as pipe:
        monkeypatch.setattr(
            ui.questionary,
            "select",
            lambda *args, **kwargs: select(
                *args, **kwargs, input=pipe, output=DummyOutput()
            ),
        )
        # Choose MiniStack initially, then traverse the five preceding actions.
        pipe.send_text("\rjjjjj" + confirm)
        ui.run_session(terminal, tmp_path, Mock(), scan, Mock(), Mock())
    scan.assert_not_called()
    assert ui.FRAME.get() is None
    assert "¡Hasta pronto!" in terminal.file.getvalue()
    assert "Sesión cerrada" in terminal.file.getvalue()


@pytest.mark.parametrize("keys", ["j\r", "jl", "h", "\x1b", "\x03"])
def test_real_back_choice_and_cancellation_return_none(monkeypatch, keys):
    """Nested back actions and keyboard cancellation retain the same contract."""
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    select = ui.questionary.select
    with create_pipe_input() as pipe:
        monkeypatch.setattr(
            ui.questionary,
            "select",
            lambda *args, **kwargs: select(
                *args, **kwargs, input=pipe, output=DummyOutput()
            ),
        )
        pipe.send_text(keys)
        assert ui.choose("Ajustes", [("Continuar", "next"), ("Volver", None)]) is None


def test_real_scan_requires_explicit_authorization(monkeypatch, tmp_path):
    module = importlib.import_module("titvo_cli.app")
    monkeypatch.setenv("TITVO_AI_API_KEY", "test-secret")
    monkeypatch.setenv("TITVO_AI_MODEL", "test-model")
    (tmp_path / "app.py").write_text("code")
    confirmation = Mock(ask=lambda: False)
    confirm = Mock(return_value=confirmation)
    monkeypatch.setattr(ui.questionary, "confirm", confirm)
    resources = Mock()
    monkeypatch.setattr(module, "clients", resources)
    import pytest

    with pytest.raises(typer.Exit):
        module.guided_scan(
            tmp_path,
            "http://localhost:4566",
            "real",
            False,
            True,
            tmp_path / "reports",
            None,
        )
    assert confirm.call_count == 1
    assert "autorizar" in confirm.call_args.args[0]
    resources.assert_not_called()


def test_credentials_are_restored_and_never_rendered(monkeypatch, tmp_path):
    monkeypatch.setenv("TITVO_AI_API_KEY", "inherited-secret")
    monkeypatch.delenv("TITVO_AI_MODEL", raising=False)
    answers = iter(["settings", "configure", None])
    monkeypatch.setattr(ui, "choose", lambda *args: next(answers))

    def configure(_console, session):
        os.environ.update(
            TITVO_AI_API_KEY="session-secret", TITVO_AI_MODEL="test-model"
        )
        session.mode = "real"

    monkeypatch.setattr(ui, "configure", configure)
    terminal = console()
    ui.run_session(terminal, tmp_path, Mock(), Mock(), Mock(), Mock())
    assert os.environ["TITVO_AI_API_KEY"] == "inherited-secret"
    assert "TITVO_AI_MODEL" not in os.environ
    assert "inherited-secret" not in terminal.file.getvalue()
    assert "session-secret" not in terminal.file.getvalue()


def test_changing_provider_does_not_reuse_another_provider_key(monkeypatch):
    monkeypatch.setenv("TITVO_AI_PROVIDER", "openai")
    monkeypatch.setenv("TITVO_AI_API_KEY", "openai-secret")
    monkeypatch.setenv("TITVO_AI_MODEL", "original-model")
    answers = iter(["real", "anthropic"])
    monkeypatch.setattr(ui, "choose", lambda *args: next(answers))
    monkeypatch.setattr(
        ui.questionary, "text", lambda *args, **kwargs: Mock(ask=lambda: "test-model")
    )
    password = Mock(ask=lambda: "anthropic-secret")
    monkeypatch.setattr(ui.questionary, "password", lambda *args, **kwargs: password)
    session = ui.Session()
    ui.configure(console(), session)
    assert session.mode == "real"
    assert os.environ["TITVO_AI_API_KEY"] == "anthropic-secret"
    assert os.environ["TITVO_AI_PROVIDER"] == "anthropic"


def test_failed_evaluation_is_explained_as_completed_analysis():
    module = importlib.import_module("titvo_cli.app")
    terminal = console()
    original = module.console
    module.console = terminal
    try:
        module.show_result(
            {
                "status": "FAILED",
                "coverage": {"complete": True},
                "scaned_files": 1,
                "issues": [{"severity": "CRITICAL"}],
            },
            Path(".titvo/reports"),
        )
    finally:
        module.console = original
    text = terminal.file.getvalue()
    assert "Análisis completado · hallazgos detectados" in text
    assert "Ejecución: Completado" in text
    assert "Seguridad: Con hallazgos" in text
    assert "Errores técnicos: Sin errores reportados" in text
    assert "Análisis incompleto" not in text


def test_non_interactive_start_still_prints_help():
    module = importlib.import_module("titvo_cli.app")
    result = CliRunner().invoke(module.app, [])
    assert result.exit_code == 0
    assert "preview" in result.output
    assert "scan" in result.output


def test_preferences_restore_choices_without_serializing_secrets(monkeypatch, tmp_path):
    """Only the allowlisted UI choices survive a process restart."""
    import json

    project = tmp_path / "project"
    project.mkdir()
    (project / "src").mkdir()
    monkeypatch.setenv("TITVO_AI_API_KEY", "secret-never-persist")
    session = ui.Session(
        project=project,
        include=["src"],
        mode="real",
        scope_ready=True,
        model_ready=True,
        provider="openai",
        model="test-model",
    )
    path = tmp_path / "ui.json"
    ui.save_session(console(), path, session)
    restored = ui.load_session(path, tmp_path, tmp_path)
    assert restored.project == project
    assert restored.include == ["src"]
    assert restored.mode == "real"
    assert restored.model_ready
    assert "secret-never-persist" not in path.read_text()
    assert set(json.loads(path.read_text())) == {
        "project",
        "include",
        "mode",
        "scope_ready",
        "model_ready",
        "provider",
        "model",
        "target",
        "api_url",
        "dashboard_url",
        "repository_url",
        "branch",
    }


def test_deleted_scope_requires_selection_again(tmp_path):
    """A remembered folder cannot silently become a valid empty analysis scope."""
    session = ui.Session(project=tmp_path, include=["deleted"], scope_ready=True)
    path = tmp_path / "ui.json"
    ui.save_session(console(), path, session)
    assert not ui.load_session(path, tmp_path, tmp_path).scope_ready


def test_explicit_current_directory_overrides_another_remembered_project(tmp_path):
    """Opening Titvo inside a new repository targets that repository."""
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    path = tmp_path / "ui.json"
    ui.save_session(console(), path, ui.Session(project=first))
    assert ui.load_session(path, second, tmp_path).project == second


def test_review_guides_missing_steps_and_cancellation(monkeypatch, tmp_path):
    """A first review advances automatically and stops at a canceled step."""
    sequence = []
    session = ui.Session()

    def project(*args):
        sequence.append("project")
        session.project = tmp_path
        return True

    def scope(*args):
        sequence.append("scope")
        session.scope_ready = True
        return True

    monkeypatch.setattr(ui, "select_project", project)
    monkeypatch.setattr(ui, "select_scope", scope)
    monkeypatch.setattr(
        ui, "configure", lambda *args: sequence.append("model") or False
    )
    assert not ui.prepare_review(console(), session, tmp_path)
    assert sequence == ["project", "scope", "model"]
    assert session.scope_ready
    assert not session.model_ready


def test_findings_explorer_renders_evidence_and_recommendation(monkeypatch, tmp_path):
    """Source evidence is displayed literally and never interpreted as Rich markup."""
    answers = iter([0, None])
    monkeypatch.setattr(ui, "choose", lambda *args: next(answers))
    monkeypatch.setattr(ui, "pause", lambda: None)
    terminal = console()
    ui.explore_report(
        terminal,
        {
            "issues": [
                {
                    "severity": "HIGH",
                    "title": "[red]literal title[/red]",
                    "path": "src/app.py",
                    "line": 6,
                    "description": "Unsafe input",
                    "code": "eval(user_input)",
                    "recommendation": "Remove eval",
                }
            ]
        },
        tmp_path / "report.json",
    )
    text = terminal.file.getvalue()
    assert "[red]literal title[/red]" in text
    assert "src/app.py:6" in text
    assert "eval(user_input)" in text
    assert "Remove eval" in text


def test_robot_and_worker_counter_render_on_narrow_terminal():
    """Compact identity and real worker counters remain readable without percentage guesses."""
    from titvo_cli.presentation import WorkerProgress

    terminal = Console(file=io.StringIO(), width=60)
    progress = WorkerProgress()
    progress.update({"expert": "owasp_api", "batch": "2/12"})
    terminal.print(progress)
    text = terminal.file.getvalue()
    assert "▄▟██▙▄" in text
    assert "OWASP API" in text
    assert "2/12" in text
    assert "%" not in text


def test_guided_result_is_returned_and_technical_logs_redact_key(monkeypatch, tmp_path):
    """One accepted prompt returns its own task and saves sanitized worker diagnostics."""
    module = importlib.import_module("titvo_cli.app")
    (tmp_path / "app.py").write_text("code")
    monkeypatch.setenv("TITVO_AI_API_KEY", "secret-only-for-test")
    monkeypatch.setenv("TITVO_AI_MODEL", "test-model")
    confirm = Mock(return_value=Mock(ask=lambda: True))
    monkeypatch.setattr(ui.questionary, "confirm", confirm)
    monkeypatch.setattr(module, "clients", lambda endpoint: (Mock(), Mock()))
    monkeypatch.setattr(module, "bootstrap", Mock())
    monkeypatch.setattr(module, "upload", lambda *args: "own-task")
    snapshot = module.collect(tmp_path, None)
    monkeypatch.setattr(module, "collect", lambda *args: snapshot)
    process = Mock()
    process.stdout = iter(
        [
            'TITVO_EVENT {"expert": "owasp_web", "batch": "1/2"}\n',
            "diagnostic secret-only-for-test\n",
        ]
    )
    process.wait.return_value = 0
    monkeypatch.setattr(module.subprocess, "Popen", lambda *args, **kwargs: process)
    expected = {
        "task_id": "own-task",
        "status": "COMPLETED",
        "coverage": {"complete": True},
        "issues": [],
    }
    monkeypatch.setattr(module, "download_report", lambda *args: expected)
    monkeypatch.setattr(module, "show_result", Mock())
    result = module.guided_scan(
        tmp_path,
        "http://localhost:4566",
        "real",
        False,
        True,
        tmp_path / "reports",
        None,
    )
    assert result is expected
    assert confirm.call_count == 1
    log = (tmp_path / "reports/own-task.log").read_text()
    assert "secret-only-for-test" not in log
    assert "[API KEY OCULTA]" in log


@pytest.mark.parametrize(
    "keys, expected",
    [("jjkl", "second"), ("\x1b[B\r", "second"), ("h", None), ("\x1b", None)],
)
def test_actual_vim_arrow_and_back_keys(monkeypatch, keys, expected):
    """Exercise the actual prompt key bindings, rather than mocking selection."""
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    factory = ui.questionary.select
    with create_pipe_input() as pipe:
        monkeypatch.setattr(
            ui.questionary,
            "select",
            lambda *args, **kwargs: factory(
                *args, **kwargs, input=pipe, output=DummyOutput()
            ),
        )
        pipe.send_text(keys)
        assert (
            ui.choose(
                "Choose", [("First", "first"), ("Second", "second"), ("Third", "third")]
            )
            == expected
        )


def test_folder_selection_uses_vim_keys_and_space(monkeypatch, tmp_path):
    """Checkbox selection supports navigation and preserves the chosen scope."""
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    factory = ui.questionary.checkbox
    session = ui.Session(project=tmp_path)
    monkeypatch.setattr(ui, "choose", lambda *args: "folders")
    with create_pipe_input() as pipe:
        monkeypatch.setattr(
            ui.questionary,
            "checkbox",
            lambda *args, **kwargs: factory(
                *args, **kwargs, input=pipe, output=DummyOutput()
            ),
        )
        pipe.send_text("j l")
        assert ui.select_scope(session)
    assert session.include == ["b"]


def test_mascot_animation_is_bounded_and_can_be_disabled(monkeypatch):
    """Blink during work, retain batch counters, and honor reduced-motion flags."""
    from titvo_cli import presentation

    clock = {"value": 0.0}
    monkeypatch.setattr(presentation, "monotonic", lambda: clock["value"])
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("TITVO_NO_ANIMATION", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    progress = presentation.WorkerProgress()
    progress.update({"expert": "owasp_api", "batch": "2/12"})
    clock["value"] = 1.0
    terminal = console()
    terminal.print(progress)
    assert "▐ ── ▌" in terminal.file.getvalue()
    assert "2/12" in terminal.file.getvalue()
    monkeypatch.setenv("TITVO_NO_ANIMATION", "1")
    still = presentation.WorkerProgress()
    clock["value"] = 2.0
    terminal = console()
    terminal.print(still)
    assert "▪▪" in terminal.file.getvalue()
    assert "▐ ── ▌" not in terminal.file.getvalue()


def test_vim_letters_remain_literal_in_password_fields():
    """Typing model keys does not accidentally navigate or expose credentials."""
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    with create_pipe_input() as pipe:
        pipe.send_text("jklh\r")
        assert (
            ui.ask(ui.questionary.password, "API key", input=pipe, output=DummyOutput())
            == "jklh"
        )
