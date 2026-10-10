from __future__ import annotations

import json

import pytest
from bambu_pipe.cli.main import app
from bambu_pipe.design.schema import DesignSpec
from bambu_pipe.design.workspace import DesignError, init_design, install_skill
from pydantic import ValidationError
from typer.testing import CliRunner


def test_spec_rejects_invalid_units_nonfinite_and_unknown_fields() -> None:
    valid = {"brief": "plate", "dimensions_mm": [80, 40, 4]}
    for update in (
        {"units": "cm"},
        {"dimensions_mm": [80, 40, 0]},
        {"parameters": {"width": float("nan")}},
        {"typo": 1},
    ):
        with pytest.raises(ValidationError):
            DesignSpec.model_validate({**valid, **update})


def test_init_does_not_overwrite_existing_design(tmp_path) -> None:  # noqa: ANN001
    workspace = init_design(tmp_path / "plate")
    original = (workspace / "model.py").read_bytes()
    with pytest.raises(DesignError, match="empty"):
        init_design(workspace)
    assert (workspace / "model.py").read_bytes() == original


def test_cli_init_outputs_parseable_json_and_missing_review_fails(tmp_path) -> None:  # noqa: ANN001
    workspace = tmp_path / "plate"
    result = CliRunner().invoke(app, ["design", "init", str(workspace)])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["workspace"] == str(workspace)
    verify = CliRunner().invoke(app, ["design", "verify", str(workspace)])
    assert verify.exit_code == 2


def test_packaged_skill_installs_without_overwriting(tmp_path) -> None:  # noqa: ANN001
    path = install_skill(tmp_path / "skills")
    assert (path / "SKILL.md").is_file()
    assert (path / "references" / "contract.md").is_file()
    with pytest.raises(DesignError, match="already exists"):
        install_skill(tmp_path / "skills")
