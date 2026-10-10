"""Independent acceptance criteria, expressed in millimeters."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Coordinate = Annotated[float, Field(allow_inf_nan=False)]


class PointProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    point_mm: tuple[Coordinate, Coordinate, Coordinate]
    expect: Literal["solid", "void"]


class DesignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    brief: str = Field(min_length=1)
    units: Literal["mm"] = "mm"
    parameters: dict[str, Coordinate] = Field(default_factory=dict)
    dimensions_mm: tuple[Positive, Positive, Positive]
    dimension_tolerance_mm: Positive = 0.2
    bed_mm: tuple[Positive, Positive, Positive] = (256, 256, 256)
    solid_count: int = Field(default=1, ge=1)
    min_volume_mm3: Positive = 1
    probes: list[PointProbe] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
