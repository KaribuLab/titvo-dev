"""Separate execution completeness, technical errors and security findings."""


def execution_state(result: dict) -> str:
    """Use measured coverage; a rejected security evaluation is not a crash."""
    complete = result.get("coverage", {}).get("complete")
    if complete is True:
        return "COMPLETED"
    if complete is False:
        completed = result.get("metrics", {}).get("completed_batches")
        if completed == 0 and result.get("error"):
            return "FAILED"
        return "INCOMPLETE"
    return "UNKNOWN"


def technical_errors(result: dict) -> list[str]:
    """Deduplicate explicit errors without counting findings as execution errors."""
    errors = []
    if result.get("error"):
        errors.append(str(result["error"]))
    errors.extend(str(error) for error in result.get("coverage", {}).get("errors", []))
    return list(dict.fromkeys(errors))


def finding_count(result: dict) -> int | None:
    """Use inline findings or the AWS count; missing detail never means zero."""
    issues = result.get("issues")
    if isinstance(issues, list):
        return len(issues)
    count = result.get("issues_count")
    return count if type(count) is int and count >= 0 else None


def outcome_rows(result: dict) -> list[tuple[str, str]]:
    """Give terminal views the same independent execution/result/error facts."""
    labels = {
        "COMPLETED": "Completado",
        "INCOMPLETE": "Incompleto",
        "FAILED": "Fallido",
        "UNKNOWN": "No registrado",
    }
    errors = technical_errors(result)
    count = finding_count(result)
    return [
        ("Ejecución", labels[execution_state(result)]),
        (
            "Seguridad",
            "No registrado"
            if count is None
            else f"Con hallazgos · {count}"
            if count
            else "Sin hallazgos reportados",
        ),
        (
            "Errores técnicos",
            f"Sí · {len(errors)}" if errors else "Sin errores reportados",
        ),
    ]
