"""Generate a parametric STEP model of the IC-225 8 mm metal LED signal lamp.

Dimensions from common IC-225 datasheets:
  mounting hole / thread : M8 x 0.75
  head (bezel) diameter  : ~10 mm
  lens diameter          : 5 mm
  panel protrusion       : ~1.5 mm
  total mounting depth   : ~30 mm
  hex nut                : SW10
  wire leads             : ~150 mm, 2 pcs

Coordinate system: Z = 0 is the panel front face, +Z points out of the panel.
Thread is modelled as a simplified cylindrical envelope (no helical thread).
"""
import cadquery as cq

# ---- parameters (mm) -------------------------------------------------------
THREAD_D = 8.0          # M8
BEZEL_D = 10.0          # outer bezel diameter
BEZEL_H = 1.5           # protrusion in front of panel
LENS_D = 5.0
LENS_DOME = 1.1         # dome height above bezel
BODY_LEN = 28.0         # threaded barrel length behind panel
NUT_AF = 10.0           # across flats (SW10) -> circumradius
NUT_H = 3.0
WASHER_D = 11.5
WASHER_H = 0.8
REAR_D = 7.2
REAR_LEN = 3.0          # plastic tail after thread
WIRE_D = 1.0
WIRE_LEN = 150.0

# ---- front bezel -----------------------------------------------------------
bezel = (
    cq.Workplane("XY")
    .circle(BEZEL_D / 2)
    .extrude(BEZEL_H)
    .edges(">Z")
    .chamfer(0.35)
    .edges("<Z")
    .chamfer(0.2)
)

# ---- 5 mm dome lens --------------------------------------------------------
r_lens = (LENS_D ** 2 / 4 + LENS_DOME ** 2) / (2 * LENS_DOME)  # spherical cap radius
z_center = BEZEL_H + LENS_DOME - r_lens
lens = (
    cq.Workplane("XY")
    .workplane(offset=BEZEL_H - 0.6)
    .circle(LENS_D / 2)
    .extrude(0.62)
    .union(cq.Workplane("XY").workplane(offset=z_center).sphere(r_lens))
)

# ---- M8 barrel (simplified thread envelope) --------------------------------
barrel = (
    cq.Workplane("XY")
    .workplane(offset=-BODY_LEN)
    .circle(THREAD_D / 2)
    .extrude(BODY_LEN + 0.01)
)
# small lead-in chamfers at both ends
barrel = barrel.edges(cq.selectors.NearestToPointSelector((0, 0, -BODY_LEN))).chamfer(0.3)
barrel = barrel.edges(cq.selectors.NearestToPointSelector((0, 0, 0.0))).chamfer(0.2)

# ---- rear plastic tail + wire exits ---------------------------------------
rear = (
    cq.Workplane("XY")
    .workplane(offset=-(BODY_LEN + REAR_LEN))
    .circle(REAR_D / 2)
    .extrude(REAR_LEN + 0.01)
    .edges("<Z")
    .chamfer(0.6)
)

# ---- washer ----------------------------------------------------------------
washer = (
    cq.Workplane("XY")
    .workplane(offset=-WASHER_H)
    .circle(WASHER_D / 2)
    .extrude(WASHER_H + 0.01)
    .faces("<Z")
    .workplane()
    .hole(THREAD_D + 0.3)
)

# ---- hex nut (SW10) --------------------------------------------------------
nut = (
    cq.Workplane("XY")
    .workplane(offset=-(WASHER_H + NUT_H))
    .polygon(6, NUT_AF * 2 / 3 ** 0.5)   # circumscribed circle for SW10
    .extrude(NUT_H + 0.01)
    .faces("<Z")
    .workplane()
    .hole(THREAD_D + 0.25)
)

# ---- two 150 mm wire leads -------------------------------------------------
z_wire_start = -(BODY_LEN + REAR_LEN) + 0.1
wires = []
for x in (-2.0, 2.0):
    w = (
        cq.Workplane("XY")
        .workplane(offset=z_wire_start - WIRE_LEN)
        .center(x, 0)
        .circle(WIRE_D / 2)
        .extrude(WIRE_LEN)
    )
    wires.append(w)

body = bezel.union(lens).union(barrel).union(rear)
hardware = washer.union(nut)
assembly = body.union(hardware)
for w in wires:
    assembly = assembly.union(w)

assembly = assembly.clean()

cq.exporters.export(assembly, "/tmp/opencode/IC-225_LED_signal_lamp.step")
cq.exporters.export(assembly, "/tmp/opencode/IC-225_LED_signal_lamp.stl")

bb = assembly.val().BoundingBox()
print("STEP written.")
print(f"bbox: X {bb.xlen:.2f}  Y {bb.ylen:.2f}  Z {bb.zlen:.2f} mm")
print(f"solid valid: {assembly.val().isValid()}")
print(f"volume: {assembly.val().Volume():.1f} mm^3")
