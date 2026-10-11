"""Desk-edge headphone hook, printed on its side; dimensions in millimeters."""

import math

import cadquery as cq


def build(p):
    gap = p["desk_thickness"] + p["clearance"]
    top = p["slot_floor"] + gap + p["wall"]

    def block(xmin, xmax, zmin, zmax):
        return (
            cq.Workplane("XY")
            .box(xmax - xmin, p["width"], zmax - zmin, centered=(True, True, False))
            .translate(((xmin + xmax) / 2, 0, zmin))
        )

    body = block(-p["wall"], 0, 0, top)
    body = body.union(
        block(-p["wall"], p["desk_reach"], p["slot_floor"] - p["wall"], p["slot_floor"])
    )
    body = body.union(block(-p["wall"], p["desk_reach"], top - p["wall"], top))
    body = body.union(block(-p["hook_reach"], 0, 0, p["wall"]))
    body = body.union(block(-p["hook_reach"], -p["hook_reach"] + p["wall"], 0, p["tip_height"]))
    body = body.edges("|Y").fillet(p["corner_radius"])

    # A clearance hole and an underside nut pocket allow an optional M4 set screw.
    screw = cq.Solid.makeCylinder(
        p["screw_diameter"] / 2,
        p["wall"] + 2,
        cq.Vector(p["screw_x"], 0, p["slot_floor"] - p["wall"] - 1),
        cq.Vector(0, 0, 1),
    )
    body = body.cut(screw)
    nut_radius = p["nut_across_flats"] / (2 * math.cos(math.pi / 6))
    nut = (
        cq.Workplane("XY")
        .polygon(6, 2 * nut_radius)
        .extrude(p["nut_depth"] + 0.1)
        .translate((p["screw_x"], 0, p["slot_floor"] - p["wall"] - 0.1))
    )
    body = body.cut(nut)

    # Side printing puts the profile on the bed; inspect hole bridging in the slicer.
    return body.rotate((0, 0, 0), (1, 0, 0), 90).translate((0, 0, p["width"] / 2))
