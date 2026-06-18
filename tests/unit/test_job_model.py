from __future__ import annotations

import pytest
from bambu_pipe.models.job import JobStage, PrintJob


def test_valid_transitions() -> None:
    job = PrintJob()
    job.advance(JobStage.VALIDATING)
    job.advance(JobStage.AWAITING_VALIDATION_APPROVAL)
    job.advance(JobStage.SLICING)
    assert job.stage == JobStage.SLICING


def test_invalid_transition_raises() -> None:
    job = PrintJob()
    with pytest.raises(ValueError, match="Invalid transition"):
        job.advance(JobStage.PRINTING)
