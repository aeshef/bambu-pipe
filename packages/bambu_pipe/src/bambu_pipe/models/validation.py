"""Validation report models and Print Confidence Score."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "warning", "error"]


class ValidationCheck(BaseModel):
    """Single validation check result."""

    name: str
    passed: bool
    message: str
    severity: Severity = "error"
    suggestion: str | None = None


class ValidationReport(BaseModel):
    """Aggregated validation output."""

    checks: list[ValidationCheck] = Field(default_factory=list)
    score: int | None = None

    @property
    def blocking_failures(self) -> list[ValidationCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "error"]

    @property
    def passed(self) -> bool:
        return not self.blocking_failures

    def to_summary(self) -> str:
        lines = []
        for check in self.checks:
            if check.passed:
                icon = "✓"
            elif check.severity == "warning":
                icon = "!"
            else:
                icon = "✗"
            lines.append(f"{icon} {check.name}: {check.message}")
        if self.score is not None:
            lines.insert(0, f"Score: {self.score}%")
        return "\n".join(lines)
