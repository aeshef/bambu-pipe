"""Print job state machine."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from bambu_pipe.models.validation import ValidationReport


class JobStage(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    AWAITING_VALIDATION_APPROVAL = "awaiting_validation_approval"
    SLICING = "slicing"
    AWAITING_SLICE_APPROVAL = "awaiting_slice_approval"
    UPLOADING = "uploading"
    PRINTING = "printing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    GENERATING = "generating"
    AWAITING_MODEL_APPROVAL = "awaiting_model_approval"


PipelineMode = Literal["mesh_only", "text_full"]


_TRANSITIONS: dict[JobStage, list[JobStage]] = {
    JobStage.PENDING: [
        JobStage.VALIDATING,
        JobStage.GENERATING,
        JobStage.SLICING,
        JobStage.CANCELLED,
    ],
    JobStage.GENERATING: [JobStage.AWAITING_MODEL_APPROVAL, JobStage.FAILED],
    JobStage.AWAITING_MODEL_APPROVAL: [
        JobStage.VALIDATING,
        JobStage.GENERATING,
        JobStage.CANCELLED,
    ],
    JobStage.VALIDATING: [JobStage.AWAITING_VALIDATION_APPROVAL, JobStage.FAILED],
    JobStage.AWAITING_VALIDATION_APPROVAL: [
        JobStage.SLICING,
        JobStage.VALIDATING,
        JobStage.CANCELLED,
    ],
    JobStage.SLICING: [JobStage.AWAITING_SLICE_APPROVAL, JobStage.FAILED],
    JobStage.AWAITING_SLICE_APPROVAL: [JobStage.UPLOADING, JobStage.CANCELLED],
    JobStage.UPLOADING: [JobStage.PRINTING, JobStage.FAILED],
    JobStage.PRINTING: [JobStage.DONE, JobStage.FAILED],
}


class StageArtifacts(BaseModel):
    prompt: str | None = None
    enriched_prompt: str | None = None
    model_path: str | None = None
    model_format: str | None = None
    validation: ValidationReport | None = None
    sliced_path: str | None = None
    thumbnail_path: str | None = None
    remote_filename: str | None = None
    estimated_print_time: str | None = None
    estimated_filament_g: float | None = None
    print_progress_pct: float | None = None


class PrintJob(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    mode: PipelineMode = "mesh_only"
    prompt: str = ""
    model_path: str | None = None
    quality: Literal["draft", "standard", "fine"] = "standard"
    material: str = "PLA"
    auto_approve: bool = False

    stage: JobStage = JobStage.PENDING
    error: str | None = None
    artifacts: StageArtifacts = Field(default_factory=StageArtifacts)
    history: list[dict[str, Any]] = Field(default_factory=list)

    def advance(self, new_stage: JobStage, *, error: str | None = None) -> None:
        allowed = _TRANSITIONS.get(self.stage, [])
        if new_stage not in allowed:
            raise ValueError(
                f"Invalid transition: {self.stage.value} → {new_stage.value}. "
                f"Allowed: {[stage.value for stage in allowed]}"
            )
        self.history.append(
            {
                "from": self.stage.value,
                "to": new_stage.value,
                "at": datetime.now(UTC).isoformat(),
                "error": error,
            }
        )
        self.stage = new_stage
        self.error = error
        self.updated_at = datetime.now(UTC)

    @property
    def is_terminal(self) -> bool:
        return self.stage in {JobStage.DONE, JobStage.FAILED, JobStage.CANCELLED}

    @property
    def awaits_approval(self) -> bool:
        return self.stage.value.startswith("awaiting_")

    @property
    def approval_stage(self) -> JobStage | None:
        if not self.awaits_approval:
            return None
        return self.stage
