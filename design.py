"""
Autoaquaponics design file — THE AGENT MODIFIES THIS FILE.
==========================================================
Parametric CadQuery model of a closed-loop RAS tilapia system.
Enclosed in a 25ft x 12ft lean-to roof structure.

Components: 1-3 HDPE fish tanks (configurable via NUM_TANKS),
            1 biofilter (multi-barrel MBBR), 1 sump, 1 water pump,
            1 air pump, aeration system. Shared infrastructure scales
            automatically — pump/biofilter/air are divided per-tank
            for scoring while the CAD shows the full multi-tank layout.

The PARAMS dict at the bottom is read by evaluate.py to score
the design. The CadQuery geometry is rendered to OCP CAD Viewer
locally or exported to STEP in headless mode.

Usage:
    python design.py                  # headless: evaluate + export STEP
    python design.py --render         # local: OCP CAD Viewer on port 3939
"""

import math
import sys
import os

# ---------------------------------------------------------------------------
# DESIGN PARAMETERS — Agent modifies these to optimize tilapia growth
# ---------------------------------------------------------------------------

# Structure (25ft x 12ft lean-to, fixed envelope)
STRUCTURE_LENGTH_MM = 25 * 304.8    # 7620mm (X-axis) — DO NOT EXCEED
STRUCTURE_WIDTH_MM = 12 * 304.8     # 3657.6mm (Y-axis) — DO NOT EXCEED
SOUTH_POST_H = 7 * 304.8           # 2133.6mm
NORTH_POST_H = 9 * 304.8           # 2743.2mm

# Fish Tank — round HDPE cylindrical
FISH_TANK_DIA = 1300.0              # mm (increased from 1200mm for more volume)
FISH_TANK_H = 900.0                 # mm (increased from 762mm for more volume)
FISH_TANK_WALL = 6.0                # mm wall thickness
FISH_TANK_STAND_H = 450.0           # mm steel tube stand height
FISH_TANK_VOLUME_L = round(
    math.pi * (FISH_TANK_DIA / 2000) ** 2 * (FISH_TANK_H / 1000) * 1000 * 0.67, 1
)  # liters (67% practical fill, computed from geometry)
FISH_TANK_CX = 3251.0              # X center position (mm) — used for single-tank
FISH_TANK_CY = 1270.0              # Y center position (mm) — all tanks share this Y

# Multi-Tank Scaling
NUM_TANKS = 2                        # number of fish tanks (1, 2, or 3)
assert NUM_TANKS in (1, 2, 3), "NUM_TANKS must be 1, 2, or 3"

# Stocking
STOCKING_COUNT = 10                 # fingerlings stocked in tank (reduced from 12)
GROW_OUT_DAYS = 165                 # 5.5 months

# Biofilter — MBBR barrels in series
BIO_BARREL_COUNT = 6                # number of 55-gal MBBR barrels (3 per tank for 2-tank setup)
BIO_DIA = 585.0                     # mm barrel outer diameter
BIO_H = 880.0                       # mm barrel height
BIO_WALL = 4.0                      # mm barrel wall thickness
BIO_STAND_H = 170.0                 # mm stand height
BIO_SPACING = 635.0                 # mm center-to-center spacing
BIO_FILL_RATIO = 0.60               # K1 media fill ratio (0-1)
BIO_BARREL_VOLUME_L = 208.2         # liters per barrel (55-gal)
BIO_MEDIA_SURFACE_M2_M3 = 500       # K1 media specific surface area
BIO_NITRIFICATION_RATE = 0.5        # g NH3/m2/day

# Biofilter positions
BIO1_CX = 1200.0
BIO2_CX = 1835.0
BIO3_CX = 2470.0
BIO_CY = 2400.0

# Sump Tank
SUMP_L = 800.0                      # mm length
SUMP_W = 600.0                      # mm width
SUMP_D = 500.0                      # mm depth
SUMP_WALL = 5.0
SUMP_CX = 5200.0
SUMP_CY = 1529.0
SUMP_INLET_Z = 200.0                # mm above grade

# Water Pump
PUMP_FLOW_LPM = 80.0                 # L/min (80/2=40 per tank, 40*60/800=3.0 t/hr optimal)
PUMP_POWER_W = 550                   # watts (LEO ACm75 at operating point, 0.75kW rated)
PUMP_W = 250.0                       # mm body width
PUMP_D = 180.0                       # mm body depth
PUMP_H = 200.0                       # mm body height
PUMP_CX = 5475.0
PUMP_CY = 907.0

# Air Pump + Aeration
AIR_PUMP_FLOW_LPM = 200              # L/min output (dual diaphragm pump for 2 tanks)
AIR_PUMP_POWER_W = 140               # watts (200 LPM diaphragm pump)
AIR_PUMP_W = 200.0
AIR_PUMP_D = 150.0
AIR_PUMP_H = 150.0
AIR_PUMP_CX = 2177.0
AIR_PUMP_CY = 300.0
AIR_PUMP_Z = 200.0                   # mm mounted height

# Temperature management
AMBIENT_TEMP_C = 23.0                # Barbosa average air temp at 1300m ASL
GREENHOUSE_BOOST_C = 4.0             # greenhouse effect on WATER temp
INSULATION_BOOST_C = 1.0             # tank insulation (increased from 0.5 for better temp)
DARK_TANK_BOOST_C = 0.3              # black HDPE solar absorption (minimal baseline)

# Pipe dimensions (OD in mm, for CAD rendering)
SUPPLY_OD = 48.3                     # 1.5" Sch40 PVC
DRAIN_OD = 60.3                      # 2" Sch40 PVC
BARREL_OD = 48.3                     # 1.5" inter-barrel
OVERFLOW_OD = 60.3                   # 2" emergency
AIRLINE_OD = 6.0                     # 6mm silicone

# Lumber (actual dimensions)
POST_W = 3.5 * 25.4                  # 89mm (4x4)
PLATE_W = 1.5 * 25.4                 # 38mm (2x6)
PLATE_D = 5.5 * 25.4                 # 140mm (2x6)
RAFTER_W = 1.5 * 25.4
RAFTER_D = 5.5 * 25.4
PURLIN_W = 1.5 * 25.4
PURLIN_D = 3.5 * 25.4
ROOF_OVERHANG = 100                  # mm
POLY_THICK = 6                       # mm polycarbonate

# Colors for OCP CAD Viewer
COLORS = {
    "wood": "#C4A35A", "steel": "#333333", "polycarbonate": "#B8D4E3",
    "fish_tank": "#1E5C99", "biofilter": "#4A4A4A", "sump": "#757575",
    "pump": "#FFD700", "pvc_white": "#FFFFFF", "pvc_emergency": "#FF6600",
    "air_line": "#00BFFF", "slab": "#808080", "dimension": "#FF0000",
    "gutter": "#A0A0A0",
}

# ---------------------------------------------------------------------------
# Multi-Tank Layout Computation
# ---------------------------------------------------------------------------

_TANK_SPACING = 1600.0               # mm center-to-center (≥300mm walkway gap)
if NUM_TANKS == 1:
    TANK_CXS = [FISH_TANK_CX]
elif NUM_TANKS == 2:
    _mid_x = 3000.0
    TANK_CXS = [_mid_x - _TANK_SPACING / 2, _mid_x + _TANK_SPACING / 2]
else:  # 3
    _mid_x = 3000.0
    TANK_CXS = [_mid_x - _TANK_SPACING, _mid_x, _mid_x + _TANK_SPACING]

# Adjust sump/pump east if rightmost tank encroaches
_right_clearance = max(TANK_CXS) + FISH_TANK_DIA / 2 + 400
if _right_clearance + SUMP_L / 2 > SUMP_CX:
    SUMP_CX = _right_clearance + SUMP_L / 2
    PUMP_CX = SUMP_CX + 275

# ---------------------------------------------------------------------------
# PARAMS dict — exported for evaluate.py scoring (DO NOT RENAME)
# Shared resources are divided by NUM_TANKS so evaluate.py sees per-tank values.
# ---------------------------------------------------------------------------

PARAMS = {
    "structure_length_mm": STRUCTURE_LENGTH_MM,
    "structure_width_mm": STRUCTURE_WIDTH_MM,
    "fish_tank_dia_mm": FISH_TANK_DIA,
    "fish_tank_h_mm": FISH_TANK_H,
    "fish_tank_stand_h_mm": FISH_TANK_STAND_H,
    "tank_volume_l": FISH_TANK_VOLUME_L,
    "stocking_count": STOCKING_COUNT,
    "grow_out_days": GROW_OUT_DAYS,
    "num_tanks": NUM_TANKS,
    "bio_barrel_count": BIO_BARREL_COUNT / NUM_TANKS,    # per-tank share (float OK)
    "bio_barrel_volume_l": BIO_BARREL_VOLUME_L,
    "bio_fill_ratio": BIO_FILL_RATIO,
    "bio_media_surface_m2_per_m3": BIO_MEDIA_SURFACE_M2_M3,
    "bio_nitrification_rate": BIO_NITRIFICATION_RATE,
    "bio_stand_h_mm": BIO_STAND_H,
    "bio_h_mm": BIO_H,
    "sump_inlet_z_mm": SUMP_INLET_Z,
    "pump_flow_lpm": PUMP_FLOW_LPM / NUM_TANKS,          # per-tank share
    "air_pump_flow_lpm": AIR_PUMP_FLOW_LPM / NUM_TANKS,   # per-tank share
    "ambient_temp_c": AMBIENT_TEMP_C,
    "greenhouse_boost_c": GREENHOUSE_BOOST_C,       # baseline: 1.5
    "insulation_boost_c": INSULATION_BOOST_C,       # baseline: 0.0
    "dark_tank_boost_c": DARK_TANK_BOOST_C,         # baseline: 0.3
}

# ---------------------------------------------------------------------------
# Exit early if just being imported for PARAMS (headless scoring)
# ---------------------------------------------------------------------------

if os.environ.get("AUTOAQUAPONICS_PARAMS_ONLY") == "1":
    sys.exit(0)

# ---------------------------------------------------------------------------
# CadQuery model generation
# ---------------------------------------------------------------------------

try:
    import cadquery as cq
except ImportError:
    print("CadQuery not installed. Install with: pip install cadquery")
    print("Scoring only (no CAD)...")
    # Still run evaluation
    from evaluate import score_design
    result = score_design(PARAMS, verbose=True)
    print(f"\n--- DESIGN SCORE ---")
    print(f"predicted_weight_g:     {result['predicted_weight_g']:.2f}")
    print(f"constraints_pass:       {result['constraints_pass']}")
    sys.exit(0)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_box_at(cx, cy, cz, sx, sy, sz):
    return cq.Workplane("XY").transformed(offset=(cx, cy, cz + sz/2)).box(sx, sy, sz)


def make_cylinder_at(cx, cy, z_bottom, dia, height):
    return cq.Workplane("XY").transformed(offset=(cx, cy, z_bottom)).circle(dia/2).extrude(height)


def make_hollow_cylinder(cx, cy, z_bottom, od, height, wall):
    outer = make_cylinder_at(cx, cy, z_bottom, od, height)
    inner = make_cylinder_at(cx, cy, z_bottom + wall, od - 2*wall, height - 2*wall)
    return outer.cut(inner)


def make_pipe_segment(start, end, od):
    sx, sy, sz = start
    ex, ey, ez = end
    dx, dy, dz = ex - sx, ey - sy, ez - sz
    length = math.sqrt(dx**2 + dy**2 + dz**2)
    if length < 1:
        return None
    pnt = cq.Vector(sx, sy, sz)
    direction = cq.Vector(dx/length, dy/length, dz/length)
    cyl = cq.Solid.makeCylinder(od/2, length, pnt, direction)
    return cq.Workplane("XY").newObject([cyl])


def make_pipe_run(points, od):
    segments = []
    for i in range(len(points) - 1):
        seg = make_pipe_segment(points[i], points[i+1], od)
        if seg is not None:
            segments.append(seg)
    for i in range(1, len(points) - 1):
        x, y, z = points[i]
        elbow = cq.Workplane("XY").transformed(offset=(x, y, z)).sphere(od * 0.7)
        segments.append(elbow)
    if not segments:
        return cq.Workplane("XY").box(1, 1, 1)
    result = segments[0]
    for s in segments[1:]:
        result = result.union(s)
    return result


# ═══════════════════════════════════════════════════
# BUILD MODEL
# ═══════════════════════════════════════════════════

print("=" * 60)
print("  AUTOAQUAPONICS — Building parametric model...")
print("=" * 60)

LENGTH = STRUCTURE_LENGTH_MM
WIDTH = STRUCTURE_WIDTH_MM
SLAB_THICKNESS = 4 * 25.4  # 101.6mm

# --- Post registry ---
POST_REGISTRY = {
    "S1": {"x": 44.5,   "y": 44.5,   "h": SOUTH_POST_H},
    "S2": {"x": 1524.0, "y": 44.5,   "h": SOUTH_POST_H},
    "S3": {"x": 3048.0, "y": 44.5,   "h": SOUTH_POST_H},
    "S4": {"x": 4572.0, "y": 44.5,   "h": SOUTH_POST_H},
    "S5": {"x": 6096.0, "y": 44.5,   "h": SOUTH_POST_H},
    "S6": {"x": 7575.5, "y": 44.5,   "h": SOUTH_POST_H},
    "N1": {"x": 44.5,   "y": 3613.1, "h": NORTH_POST_H},
    "N2": {"x": 1524.0, "y": 3613.1, "h": NORTH_POST_H},
    "N3": {"x": 3048.0, "y": 3613.1, "h": NORTH_POST_H},
    "N4": {"x": 4572.0, "y": 3613.1, "h": NORTH_POST_H},
    "N5": {"x": 6096.0, "y": 3613.1, "h": NORTH_POST_H},
    "N6": {"x": 7575.5, "y": 3613.1, "h": NORTH_POST_H},
}

# --- Ground Slab ---
slab = cq.Workplane("XY").transformed(offset=(LENGTH/2, WIDTH/2, -SLAB_THICKNESS/2)).box(LENGTH, WIDTH, SLAB_THICKNESS)

# --- Posts (12x 4x4) ---
post_parts = []
for pid, info in POST_REGISTRY.items():
    post_parts.append(make_box_at(info["x"], info["y"], 0, POST_W, POST_W, info["h"]))
posts_asm = post_parts[0]
for p in post_parts[1:]:
    posts_asm = posts_asm.union(p)

# --- Top Plates + Rafters ---
south_plate = make_box_at(LENGTH/2, 44.5, SOUTH_POST_H, LENGTH, PLATE_W, PLATE_D)
north_plate = make_box_at(LENGTH/2, 3613.1, NORTH_POST_H, LENGTH, PLATE_W, PLATE_D)
plates_asm = south_plate.union(north_plate)

RAFTER_Z_SOUTH = SOUTH_POST_H + PLATE_D
RAFTER_Z_NORTH = NORTH_POST_H + PLATE_D
rafter_run = 3613.1 - 44.5
rafter_rise = RAFTER_Z_NORTH - RAFTER_Z_SOUTH
rafter_slope_len = math.sqrt(rafter_run**2 + rafter_rise**2)
rafter_angle = math.degrees(math.atan2(rafter_rise, rafter_run))
overhang_along_slope = ROOF_OVERHANG / math.cos(math.atan2(rafter_rise, rafter_run))
rafter_total_len = rafter_slope_len + 2 * overhang_along_slope

rafter_x_positions = [44.5, 1524.0, 3048.0, 4572.0, 6096.0, 7575.5]
rafter_parts = []
for rx in rafter_x_positions:
    start_y = 44.5 - ROOF_OVERHANG
    start_z = RAFTER_Z_SOUTH - ROOF_OVERHANG * (rafter_rise / rafter_run)
    rafter = (cq.Workplane("XY")
              .transformed(offset=(rx, start_y, start_z))
              .transformed(rotate=(rafter_angle, 0, 0))
              .box(RAFTER_W, rafter_total_len, RAFTER_D, centered=(True, False, False)))
    rafter_parts.append(rafter)
rafters_asm = rafter_parts[0]
for r in rafter_parts[1:]:
    rafters_asm = rafters_asm.union(r)
framing_asm = plates_asm.union(rafters_asm)

# --- Purlins ---
purlin_parts = []
purlin_spacing = 24 * 25.4  # 609.6mm OC
n_purlins = int(rafter_total_len / purlin_spacing) + 1
for i in range(n_purlins):
    dist = i * purlin_spacing
    if dist > rafter_total_len:
        break
    frac = dist / rafter_total_len
    py = (44.5 - ROOF_OVERHANG) + frac * (rafter_run + 2 * ROOF_OVERHANG)
    pz = (RAFTER_Z_SOUTH - ROOF_OVERHANG * rafter_rise / rafter_run
          + frac * (rafter_rise + 2 * ROOF_OVERHANG * rafter_rise / rafter_run) + RAFTER_D)
    purlin_parts.append(make_box_at(LENGTH/2, py, pz, LENGTH, PURLIN_W, PURLIN_D))
purlins_asm = purlin_parts[0]
for p in purlin_parts[1:]:
    purlins_asm = purlins_asm.union(p)

# --- Roof Panel ---
panel_start_y = 44.5 - ROOF_OVERHANG
panel_start_z = RAFTER_Z_SOUTH - ROOF_OVERHANG * rafter_rise / rafter_run + RAFTER_D + PURLIN_D
roof_panel = (cq.Workplane("XY")
              .transformed(offset=(LENGTH/2, panel_start_y, panel_start_z))
              .transformed(rotate=(rafter_angle, 0, 0))
              .box(LENGTH + 2*ROOF_OVERHANG, rafter_total_len, POLY_THICK,
                   centered=(True, False, False)))

# --- Fish Tank(s) + Stand(s) ---
FISH_TANK_RIM_Z = FISH_TANK_STAND_H + FISH_TANK_H
stand_size = 1200.0
tube_sec = 40.0
fish_tank_asm = None

for tcx in TANK_CXS:
    stand_parts = []
    for ox, oy in [(-stand_size/2+tube_sec/2, -stand_size/2+tube_sec/2),
                   (stand_size/2-tube_sec/2, -stand_size/2+tube_sec/2),
                   (stand_size/2-tube_sec/2, stand_size/2-tube_sec/2),
                   (-stand_size/2+tube_sec/2, stand_size/2-tube_sec/2)]:
        stand_parts.append(make_box_at(tcx+ox, FISH_TANK_CY+oy, 0, tube_sec, tube_sec, FISH_TANK_STAND_H))
    for i in range(4):
        corners = [(-stand_size/2,-stand_size/2),(stand_size/2,-stand_size/2),
                   (stand_size/2,stand_size/2),(-stand_size/2,stand_size/2)]
        c1, c2 = corners[i], corners[(i+1)%4]
        mx = tcx + (c1[0]+c2[0])/2
        my = FISH_TANK_CY + (c1[1]+c2[1])/2
        sx = abs(c2[0]-c1[0]) if abs(c2[0]-c1[0]) > 1 else tube_sec
        sy = abs(c2[1]-c1[1]) if abs(c2[1]-c1[1]) > 1 else tube_sec
        stand_parts.append(make_box_at(mx, my, FISH_TANK_STAND_H-tube_sec, sx, sy, tube_sec))
    stand_parts.append(make_box_at(tcx, FISH_TANK_CY, FISH_TANK_STAND_H-tube_sec, stand_size, tube_sec, tube_sec))
    stand_parts.append(make_box_at(tcx, FISH_TANK_CY, FISH_TANK_STAND_H-tube_sec, tube_sec, stand_size, tube_sec))
    tank_stand = stand_parts[0]
    for s in stand_parts[1:]:
        tank_stand = tank_stand.union(s)
    tank_body = make_hollow_cylinder(tcx, FISH_TANK_CY, FISH_TANK_STAND_H,
                                     FISH_TANK_DIA, FISH_TANK_H, FISH_TANK_WALL)
    single_tank = tank_stand.union(tank_body)
    fish_tank_asm = single_tank if fish_tank_asm is None else fish_tank_asm.union(single_tank)

# --- Biofilter (MBBR barrels + stand) ---
bio_cxs = [BIO1_CX + i * BIO_SPACING for i in range(BIO_BARREL_COUNT)]
# Adjust if more than 3 barrels
if BIO_BARREL_COUNT <= 3:
    bio_cxs = [BIO1_CX, BIO2_CX, BIO3_CX][:BIO_BARREL_COUNT]
elif BIO_BARREL_COUNT == 4:
    bio_cxs = [BIO1_CX, BIO2_CX, BIO3_CX, BIO3_CX + BIO_SPACING]
bio_platform_l = (bio_cxs[-1] - bio_cxs[0] + BIO_DIA + 200) if len(bio_cxs) > 1 else BIO_DIA + 200
bio_platform_cx = (bio_cxs[0] + bio_cxs[-1]) / 2 if len(bio_cxs) > 1 else bio_cxs[0]

bio_stand_parts = []
for lx, ly in [(bio_cxs[0]-BIO_DIA/2-30, BIO_CY-BIO_DIA/2-30),
               (bio_cxs[0]-BIO_DIA/2-30, BIO_CY+BIO_DIA/2+30),
               (bio_platform_cx, BIO_CY-BIO_DIA/2-30),
               (bio_platform_cx, BIO_CY+BIO_DIA/2+30),
               (bio_cxs[-1]+BIO_DIA/2+30, BIO_CY-BIO_DIA/2-30),
               (bio_cxs[-1]+BIO_DIA/2+30, BIO_CY+BIO_DIA/2+30)]:
    bio_stand_parts.append(make_box_at(lx, ly, 0, 40, 40, BIO_STAND_H))
bio_stand_parts.append(make_box_at(bio_platform_cx, BIO_CY, BIO_STAND_H-6,
                                   bio_platform_l, BIO_DIA+200, 6))
bio_stand = bio_stand_parts[0]
for bs in bio_stand_parts[1:]:
    bio_stand = bio_stand.union(bs)

barrel_parts = []
for bcx in bio_cxs:
    barrel_parts.append(make_hollow_cylinder(bcx, BIO_CY, BIO_STAND_H, BIO_DIA, BIO_H, BIO_WALL))
biofilter_asm = bio_stand
for bp in barrel_parts:
    biofilter_asm = biofilter_asm.union(bp)

BIO_INLET_Z = BIO_STAND_H + BIO_H
BIO_OUTLET_Z = BIO_STAND_H + 100

# --- Sump Tank ---
sump_outer = make_box_at(SUMP_CX, SUMP_CY, 0, SUMP_L, SUMP_W, SUMP_D)
sump_inner = make_box_at(SUMP_CX, SUMP_CY, SUMP_WALL, SUMP_L-2*SUMP_WALL, SUMP_W-2*SUMP_WALL, SUMP_D)
sump_tank = sump_outer.cut(sump_inner)

# --- Water Pump ---
pump_body = make_box_at(PUMP_CX, PUMP_CY, 0, PUMP_W, PUMP_D, PUMP_H)

# --- Supply Plumbing (Pump -> Fish Tank(s) via manifold) ---
_manifold_z = FISH_TANK_RIM_Z + 100
_manifold_y = FISH_TANK_CY
supply_parts = []
# Vertical riser from pump to manifold height
riser_pts = [
    (PUMP_CX, PUMP_CY, PUMP_H),
    (PUMP_CX, PUMP_CY, _manifold_z),
    (PUMP_CX, _manifold_y, _manifold_z),
]
supply_parts.append(make_pipe_run(riser_pts, SUPPLY_OD))
# Branch from manifold to each tank
for tcx in TANK_CXS:
    branch_pts = [
        (PUMP_CX, _manifold_y, _manifold_z),
        (tcx + FISH_TANK_DIA/3, _manifold_y, _manifold_z),
        (tcx + FISH_TANK_DIA/3, _manifold_y, FISH_TANK_RIM_Z),
    ]
    supply_parts.append(make_pipe_run(branch_pts, SUPPLY_OD))
supply_pipe = supply_parts[0]
for sp in supply_parts[1:]:
    supply_pipe = supply_pipe.union(sp)

# --- Drain Plumbing (Fish Tank(s) -> Biofilter) ---
drain_parts = []
for tcx in TANK_CXS:
    drain_pts = [
        (tcx - FISH_TANK_DIA/2 - 30, FISH_TANK_CY, FISH_TANK_STAND_H + 100),
        (tcx - FISH_TANK_DIA/2 - 200, FISH_TANK_CY, FISH_TANK_STAND_H + 100),
        (bio_cxs[0], BIO_CY, BIO_INLET_Z),
    ]
    drain_parts.append(make_pipe_run(drain_pts, DRAIN_OD))
drain_pipe = drain_parts[0]
for dp in drain_parts[1:]:
    drain_pipe = drain_pipe.union(dp)

# --- Inter-barrel Plumbing ---
barrel_pipe_parts = []
for i in range(len(bio_cxs) - 1):
    pts = [(bio_cxs[i]+BIO_DIA/2, BIO_CY, BIO_OUTLET_Z+50),
           (bio_cxs[i+1]-BIO_DIA/2, BIO_CY, BIO_INLET_Z-50)]
    barrel_pipe_parts.append(make_pipe_run(pts, BARREL_OD))
# Last barrel to sump
last_barrel_pts = [
    (bio_cxs[-1]+BIO_DIA/2, BIO_CY, BIO_OUTLET_Z),
    (bio_cxs[-1]+BIO_DIA/2+200, BIO_CY, BIO_OUTLET_Z),
    (SUMP_CX, SUMP_CY+SUMP_W/2, SUMP_INLET_Z),
]
barrel_pipe_parts.append(make_pipe_run(last_barrel_pts, BARREL_OD))
barrel_pipe_asm = barrel_pipe_parts[0]
for bp in barrel_pipe_parts[1:]:
    barrel_pipe_asm = barrel_pipe_asm.union(bp)

# --- Overflow (Emergency) — one per tank ---
overflow_parts = []
for tcx in TANK_CXS:
    overflow_pts = [
        (tcx+FISH_TANK_DIA/2+30, FISH_TANK_CY, FISH_TANK_RIM_Z-50),
        (tcx+FISH_TANK_DIA/2+200, FISH_TANK_CY, FISH_TANK_RIM_Z-50),
        (SUMP_CX, SUMP_CY, SUMP_D-50),
    ]
    overflow_parts.append(make_pipe_run(overflow_pts, OVERFLOW_OD))
overflow_pipe = overflow_parts[0]
for op in overflow_parts[1:]:
    overflow_pipe = overflow_pipe.union(op)

# --- Aeration ---
air_pump = make_box_at(AIR_PUMP_CX, AIR_PUMP_CY, AIR_PUMP_Z, AIR_PUMP_W, AIR_PUMP_D, AIR_PUMP_H)
airstone_positions = [(bcx, BIO_CY, BIO_STAND_H+20) for bcx in bio_cxs]
for tcx in TANK_CXS:
    airstone_positions.append((tcx, FISH_TANK_CY, FISH_TANK_STAND_H+20))
airstone_parts = [make_cylinder_at(x, y, z, 25, 20) for x, y, z in airstone_positions]

airline_targets = [(bcx, BIO_CY, BIO_STAND_H+BIO_H+20) for bcx in bio_cxs]
for tcx in TANK_CXS:
    airline_targets.append((tcx, FISH_TANK_CY, FISH_TANK_RIM_Z+20))
air_top = AIR_PUMP_Z + AIR_PUMP_H
manifold_z = air_top + 50
airline_parts = []
for tx, ty, tz in airline_targets:
    pts = [(AIR_PUMP_CX, AIR_PUMP_CY, air_top),
           (AIR_PUMP_CX, AIR_PUMP_CY, manifold_z),
           (tx, ty, manifold_z), (tx, ty, tz)]
    airline_parts.append(make_pipe_run(pts, AIRLINE_OD))

aeration_asm = air_pump
for stone in airstone_parts:
    aeration_asm = aeration_asm.union(stone)
for line in airline_parts:
    aeration_asm = aeration_asm.union(line)

# ═══════════════════════════════════════════════════
# EVALUATE DESIGN
# ═══════════════════════════════════════════════════

from evaluate import score_design
result = score_design(PARAMS, verbose=("--verbose" in sys.argv))

print(f"\n--- PER-TANK METRICS (1 of {NUM_TANKS} tank{'s' if NUM_TANKS > 1 else ''}) ---")
print(f"predicted_weight_g:     {result['predicted_weight_g']:.2f}")
print(f"total_harvest_kg:       {result['total_harvest_kg']:.2f}")
print(f"surviving_fish:         {result['surviving_fish']}")
print(f"final_density_kg_m3:    {result['final_density_kg_m3']:.1f}")
print(f"effective_temp_c:       {result['effective_temp_c']:.1f}")
print(f"effective_do_mg_l:      {result['effective_do_mg_l']:.1f}")
print(f"biofilter_cap_g_day:    {result['biofilter_capacity_g_day']:.1f}")
print(f"turnovers_per_hour:     {result['turnovers_per_hour']:.1f}")
print(f"constraints_pass:       {result['constraints_pass']}")
if result["constraint_issues"]:
    for issue in result["constraint_issues"]:
        print(f"  CONSTRAINT FAIL: {issue}")

if NUM_TANKS > 1:
    _sys_fish = result['surviving_fish'] * NUM_TANKS
    _sys_harvest = result['total_harvest_kg'] * NUM_TANKS
    _sys_stocked = STOCKING_COUNT * NUM_TANKS
    print(f"\n--- SYSTEM TOTALS ({NUM_TANKS} tanks) ---")
    print(f"num_tanks:              {NUM_TANKS}")
    print(f"total_fish_stocked:     {_sys_stocked}")
    print(f"total_surviving_fish:   {_sys_fish}")
    print(f"total_system_harvest_kg:{_sys_harvest:.2f}")
    print(f"total_water_volume_l:   {FISH_TANK_VOLUME_L * NUM_TANKS:.0f}")
    print(f"pump_flow_total_lpm:    {PUMP_FLOW_LPM}")
    print(f"bio_barrels_total:      {BIO_BARREL_COUNT}")
    print(f"air_flow_total_lpm:     {AIR_PUMP_FLOW_LPM}")

# ═══════════════════════════════════════════════════
# RENDER (OCP CAD Viewer or STEP export)
# ═══════════════════════════════════════════════════

if "--render" in sys.argv:
    from ocp_vscode import show_object, set_port
    set_port(3939)
    show_object(posts_asm, name="1a-POSTS (4x4 x12)", options={"color": hex_to_rgb(COLORS["wood"])})
    show_object(framing_asm, name="1b-FRAMING (plates+rafters)", options={"color": hex_to_rgb(COLORS["wood"])})
    show_object(purlins_asm, name="1c-PURLINS (2x4 @24in OC)", options={"color": hex_to_rgb(COLORS["wood"]), "alpha": 0.9})
    show_object(roof_panel, name="1d-ROOF (polycarbonate)", options={"color": hex_to_rgb(COLORS["polycarbonate"]), "alpha": 0.35})
    show_object(fish_tank_asm, name=f"2-FISH TANK x{NUM_TANKS} (HDPE+stand)", options={"color": hex_to_rgb(COLORS["fish_tank"]), "alpha": 0.9})
    show_object(biofilter_asm, name="3-BIOFILTER (MBBR barrels)", options={"color": hex_to_rgb(COLORS["biofilter"]), "alpha": 0.9})
    show_object(sump_tank, name="4-SUMP TANK", options={"color": hex_to_rgb(COLORS["sump"]), "alpha": 0.9})
    show_object(pump_body, name="5-PUMP", options={"color": hex_to_rgb(COLORS["pump"])})
    show_object(supply_pipe, name="6a-SUPPLY (1.5in PVC)", options={"color": hex_to_rgb(COLORS["pvc_white"]), "alpha": 0.8})
    show_object(drain_pipe, name="6b-DRAIN (2in PVC)", options={"color": hex_to_rgb(COLORS["pvc_white"]), "alpha": 0.8})
    show_object(overflow_pipe, name="6c-OVERFLOW (emergency)", options={"color": hex_to_rgb(COLORS["pvc_emergency"]), "alpha": 0.8})
    show_object(barrel_pipe_asm, name="6d-INTER-BARREL (1.5in)", options={"color": hex_to_rgb(COLORS["pvc_white"]), "alpha": 0.8})
    show_object(aeration_asm, name="7-AERATION", options={"color": hex_to_rgb(COLORS["air_line"]), "alpha": 0.8})
    show_object(slab, name="9-GROUND SLAB", options={"color": hex_to_rgb(COLORS["slab"]), "alpha": 0.3})
    print("\n  Model rendered to OCP CAD Viewer (port 3939)")
else:
    # Headless: export STEP file
    assembly = posts_asm
    for part in [framing_asm, purlins_asm, fish_tank_asm, biofilter_asm,
                 sump_tank, pump_body, supply_pipe, drain_pipe,
                 barrel_pipe_asm, aeration_asm, slab]:
        assembly = assembly.union(part)
    step_path = os.path.join(os.path.dirname(__file__), "output.step")
    cq.exporters.export(assembly, step_path)
    print(f"\n  STEP exported: {step_path}")

print("\n" + "=" * 60)
print("  AUTOAQUAPONICS — Build complete")
print(f"  Predicted harvest weight: {result['predicted_weight_g']:.1f}g (target: 450g)")
print(f"  Constraints: {'PASS' if result['constraints_pass'] else 'FAIL'}")
print("=" * 60)