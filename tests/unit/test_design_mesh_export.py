"""Collapsed tessellation faces must not hide real topology defects."""

import numpy as np
import trimesh
from bambu_pipe.design.worker import remove_zero_area_faces


def test_empty_triangles_removed_without_changing_surface() -> None:
    mesh = trimesh.creation.box()
    volume, area, bounds = mesh.volume, mesh.area, mesh.bounds.copy()
    mesh.faces = np.vstack([mesh.faces, [0, 0, 1]])
    assert not mesh.is_watertight
    assert remove_zero_area_faces(mesh) == 1
    assert mesh.is_watertight and mesh.is_volume
    assert mesh.volume == volume and mesh.area == area
    np.testing.assert_array_equal(mesh.bounds, bounds)


def test_real_holes_and_small_positive_faces_are_preserved() -> None:
    mesh = trimesh.creation.box()
    mesh.update_faces(np.arange(len(mesh.faces) - 1))
    mesh.faces = np.vstack([mesh.faces, [0, 0, 1]])
    assert remove_zero_area_faces(mesh) == 1
    assert not mesh.is_watertight
    tiny = trimesh.Trimesh(
        vertices=[[0, 0, 0], [1e-6, 0, 0], [0, 1e-6, 0]],
        faces=[[0, 1, 2]], process=False,
    )
    assert remove_zero_area_faces(tiny) == 0
    assert len(tiny.faces) == 1
