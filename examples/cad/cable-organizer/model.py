"""Open cable channels and two vertical mounting holes; all dimensions in mm."""

import cadquery as cq


def build(p):
    body = cq.Workplane("XY").box(p["width"], p["depth"], p["height"], centered=(True, True, False))
    body = body.edges("|Z").fillet(p["corner_radius"])
    radius = p["channel_diameter"] / 2
    channel_z = p["floor"] + radius
    for i in range(int(p["channel_count"])):
        x = (i - (p["channel_count"] - 1) / 2) * p["channel_spacing"]
        round_channel = cq.Solid.makeCylinder(
            radius, p["depth"] + 2, cq.Vector(x, -p["depth"] / 2 - 1, channel_z), cq.Vector(0, 1, 0)
        )
        opening = (
            cq.Workplane("XY")
            .box(p["channel_diameter"], p["depth"] + 2, p["height"], centered=(True, True, False))
            .translate((x, 0, channel_z))
        )
        body = body.cut(round_channel).cut(opening)
    for x in (-p["mount_spacing"] / 2, p["mount_spacing"] / 2):
        hole = cq.Solid.makeCylinder(
            p["mount_diameter"] / 2, p["height"] + 2, cq.Vector(x, 0, -1), cq.Vector(0, 0, 1)
        )
        body = body.cut(hole)
    return body
