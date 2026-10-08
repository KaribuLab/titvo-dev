"""Regression cases for independent execution, security and technical outcomes."""

import pytest

from titvo_cli.outcome import execution_state, outcome_rows, technical_errors


@pytest.mark.parametrize(
    "result,state",
    [
        (
            {"status": "FAILED", "coverage": {"complete": True}, "issues": [{}]},
            "COMPLETED",
        ),
        ({"coverage": {"complete": True}, "issues": []}, "COMPLETED"),
        (
            {
                "coverage": {"complete": False},
                "metrics": {"completed_batches": 3},
                "error": "batch failed",
            },
            "INCOMPLETE",
        ),
        (
            {
                "coverage": {"complete": False},
                "metrics": {"completed_batches": 0},
                "error": "corrupt snapshot",
            },
            "FAILED",
        ),
        ({"coverage": {"complete": True}, "error": "recovered issue"}, "COMPLETED"),
        ({"status": "FAILED"}, "UNKNOWN"),
    ],
)
def test_execution_does_not_depend_on_findings(result, state):
    """Security rejection cannot override measured execution coverage."""
    assert execution_state(result) == state


def test_errors_and_findings_remain_separate():
    """Preserve technical diagnostics even on a completed scan with findings."""
    result = {
        "coverage": {"complete": True, "errors": ["warning"]},
        "error": "warning",
        "issues": [{}],
    }
    assert technical_errors(result) == ["warning"]
    rows = dict(outcome_rows(result))
    assert rows == {
        "Ejecución": "Completado",
        "Seguridad": "Con hallazgos · 1",
        "Errores técnicos": "Sí · 1",
    }
