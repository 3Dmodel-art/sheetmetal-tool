import cadquery as cq
import ezdxf
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import math
import os

def calculate_flat_dim(base_dim, flange_dim, thk, k_factor=0.44, inner_radius=1.0):
    """Calculates flat length for a 90-degree bend."""
    ba = (math.pi / 2) * (inner_radius + k_factor * thk)
    ossb = inner_radius + thk
    return base_dim + (2 * flange_dim) - (2 * ossb) + (2 * ba)

def generate_all_files(length, width, height, thk, job_id):
    out_dir = f"outputs/{job_id}"
    os.makedirs(out_dir, exist_ok=True)

    # 1. GENERATE 3D STEP MODEL
    # Create main hollow 4-side cabinet
    box = cq.Workplane("XY").box(length, width, height)
    cabinet_3d = box.faces("+Z").shell(-thk)
    
    step_path = os.path.join(out_dir, "cabinet_3d.step")
    cq.exporters.export(cabinet_3d, step_path)

    # 2. GENERATE FLAT PATTERN DXF FOR LASER CUTTING
    flat_l = calculate_flat_dim(length, height, thk)
    flat_w = calculate_flat_dim(width, height, thk)

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    
    # Layers: Red for Laser Cut, Blue for Press Brake Bend Lines
    doc.layers.add("CUT_OUTER", color=1)
    doc.layers.add("BEND_LINES", color=5)

    # Flat outer boundary
    half_l, half_w = flat_l / 2.0, flat_w / 2.0
    msp.add_lwpolyline([
        (-half_l, -half_w),
        (half_l, -half_w),
        (half_l, half_w),
        (-half_l, half_w),
        (-half_l, -half_w)
    ], dxfattribs={"layer": "CUT_OUTER"})

    # Bend lines
    bend_x = length / 2.0
    bend_y = width / 2.0
    msp.add_line((-bend_x, -half_w), (-bend_x, half_w), dxfattribs={"layer": "BEND_LINES"})
    msp.add_line((bend_x, -half_w), (bend_x, half_w), dxfattribs={"layer": "BEND_LINES"})
    msp.add_line((-half_l, -bend_y), (half_l, -bend_y), dxfattribs={"layer": "BEND_LINES"})
    msp.add_line((-half_l, bend_y), (half_l, bend_y), dxfattribs={"layer": "BEND_LINES"})

    dxf_path = os.path.join(out_dir, "flat_pattern.dxf")
    doc.saveas(dxf_path)

    # 3. GENERATE BENDING PDF DRAWING
    pdf_path = os.path.join(out_dir, "bending_drawing.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "SHEET METAL BENDING DRAWING")
    c.setFont("Helvetica", 11)
    c.drawString(50, 720, f"Finished Dimensions: {length} x {width} x {height} mm")
    c.drawString(50, 705, f"Sheet Thickness: {thk} mm | K-Factor: 0.44")
    c.drawString(50, 690, f"Required Blank Size: {flat_l:.2f} x {flat_w:.2f} mm")
    
    # Simple schematic drawing on PDF
    c.rect(100, 420, 300, 200)
    c.setDash(2, 2)
    c.line(170, 420, 170, 620)
    c.line(330, 420, 330, 620)
    c.drawString(110, 400, "Bend 90° Up")
    c.drawString(340, 400, "Bend 90° Up")
    c.save()

    return {
        "step": step_path,
        "dxf": dxf_path,
        "pdf": pdf_path,
        "blank_size": f"{flat_l:.2f} mm x {flat_w:.2f} mm"
    }
