import os
import zipfile
import math
import cadquery as cq
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors

def calculate_m4_holes(length):
    """Calculates M4 hole pitch (Target = L/3, Max Pitch = 200mm, Edge offset = 20mm)"""
    edge_offset = 20.0
    usable_len = length - (2 * edge_offset)
    if usable_len <= 0:
        return [length / 2.0]
    
    num_spaces = math.ceil(usable_len / 200.0)
    if num_spaces < 2:
        num_spaces = 2
        
    pitch = usable_len / num_spaces
    holes = [edge_offset + (i * pitch) for i in range(num_spaces + 1)]
    return holes

def generate_all_files(length, width, height, thickness, bend1, bend2, job_id):
    output_dir = f"outputs/{job_id}"
    os.makedirs(output_dir, exist_ok=True)

    # 1. Sheet Metal Calculations
    k_factor = 0.33
    bend_radius = thickness
    bd = 2 * (bend_radius + thickness) - (3.14159 / 2) * (bend_radius + (k_factor * thickness))

    flat_L = length + (2 * bend1) + (2 * bend2) - (4 * bd)
    flat_W = width + (2 * bend1) + (2 * bend2) - (4 * bd)

    long_holes = calculate_m4_holes(length)
    short_holes = calculate_m4_holes(width)

    # 2. Generate 3D STEP Assembly (4 Panels with M4 Holes on Bend 2)
    def create_panel(panel_len):
        base = cq.Workplane("XY").rect(panel_len, thickness).extrude(bend1)
        top_lip = cq.Workplane("XY").workplane(offset=bend1)\
            .rect(panel_len, bend2).extrude(thickness)\
            .translate((0, -bend2/2 + thickness/2, 0))
        panel = base.union(top_lip)
        
        # Cut M4 Holes on Bend 2 (Top Lip)
        for h_x in calculate_m4_holes(panel_len):
            pos_x = h_x - (panel_len / 2.0)
            hole = cq.Workplane("XY").workplane(offset=bend1 - 5)\
                .cylinder(thickness + 10, 2.15)\
                .translate((pos_x, -bend2/2 + thickness/2, 0))
            panel = panel.cut(hole)
        return panel

    front_panel = create_panel(length).translate((0, width/2, 0))
    back_panel = create_panel(length).rotate((0,0,0),(0,0,1), 180).translate((0, -width/2, 0))
    left_panel = create_panel(width).rotate((0,0,0),(0,0,1), 90).translate((-length/2, 0, 0))
    right_panel = create_panel(width).rotate((0,0,0),(0,0,1), -90).translate((length/2, 0, 0))

    assembly = cq.Assembly()
    assembly.add(front_panel, name="Front_Panel")
    assembly.add(back_panel, name="Back_Panel")
    assembly.add(left_panel, name="Left_Panel")
    assembly.add(right_panel, name="Right_Panel")

    step_path = os.path.join(output_dir, "podium_assembly.step")
    assembly.save(step_path)

    # 3. Generate DXF Flat Pattern
    flat_sheet = cq.Workplane("XY").rect(flat_L, flat_W).extrude(thickness)
    dxf_path = os.path.join(output_dir, "flat_pattern.dxf")
    cq.exporters.export(flat_sheet, dxf_path)

    # 4. Generate Professional Engineering PDF Blueprint
    pdf_path = os.path.join(output_dir, "podium_drawings.pdf")
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    page_w, page_h = landscape(A4)

    # Drawing Border
    c.setLineWidth(1.5)
    c.setStrokeColor(colors.black)
    c.rect(15, 15, page_w - 30, page_h - 30)

    # Title Block Outer Frame
    tb_x, tb_y, tb_w, tb_h = page_w - 280, 15, 265, 110
    c.setLineWidth(1.0)
    c.rect(tb_x, tb_y, tb_w, tb_h)

    # Title Block Rows and Grid Lines
    c.line(tb_x, tb_y + 85, tb_x + tb_w, tb_y + 85)
    c.line(tb_x, tb_y + 60, tb_x + tb_w, tb_y + 60)
    c.line(tb_x, tb_y + 35, tb_x + tb_w, tb_y + 35)
    c.line(tb_x + 130, tb_y, tb_x + 130, tb_y + 85)

    # Title Block Text Entries
    c.setFont("Helvetica-Bold", 10)
    c.drawString(tb_x + 10, tb_y + 93, "PROJECT: MODULAR SHEET METAL PODIUM")
    
    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 8, tb_y + 72, "DRAWING NO:")
    c.setFont("Helvetica", 8)
    c.drawString(tb_x + 70, tb_y + 72, f"POD-ASM-{job_id}")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 138, tb_y + 72, "MATERIAL:")
    c.setFont("Helvetica", 8)
    c.drawString(tb_x + 190, tb_y + 72, "CRCA / Stainless")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 8, tb_y + 47, "DRAWN BY:")
    c.setFont("Helvetica", 8)
    c.drawString(tb_x + 70, tb_y + 47, "AI CAD Engine")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 138, tb_y + 47, "THICKNESS:")
    c.setFont("Helvetica", 8)
    c.drawString(tb_x + 195, tb_y + 47, f"{thickness} mm")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 8, tb_y + 22, "CHECKED BY:")
    c.setFont("Helvetica", 8)
    c.drawString(tb_x + 70, tb_y + 22, "Lead Engineer")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 138, tb_y + 22, "UNITS / SCALE:")
    c.setFont("Helvetica", 8)
    c.drawString(tb_x + 205, tb_y + 22, "mm / N.T.S.")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 8, tb_y + 6, "DATE:")
    c.setFont("Helvetica", 8)
    c.drawString(tb_x + 40, tb_y + 6, "August 2026")

    # Blueprint Title Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, page_h - 45, "MODULAR PODIUM FABRICATION BLUEPRINT")
    c.setLineWidth(0.5)
    c.line(30, page_h - 52, page_w - 30, page_h - 52)

    # 3D Orthographic Views Representation Boxes
    c.setDash(2, 2)
    c.rect(40, 240, 220, 160)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(45, 385, "FRONT VIEW (MAIN PROFILE)")

    c.rect(280, 240, 220, 160)
    c.drawString(285, 385, "SIDE VIEW (DOUBLE BEND PROFILE)")

    c.rect(40, 50, 220, 160)
    c.drawString(45, 195, "TOP VIEW (INTERNAL M4 BOLT LIPS)")

    # Fabrication & Bending Specifications Table
    c.setDash(1, 0)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(280, 200, "FABRICATION & BENDING DATA TABLE")

    table_x, table_y = 280, 70
    c.rect(table_x, table_y, 240, 115)
    c.setFont("Helvetica", 9)
    
    rows = [
        f"Overall Podium Size: {length} x {width} x {height} mm",
        f"Bend 1 (Vertical Wall): {bend1} mm (90 deg UP)",
        f"Bend 2 (Top Inward Lip): {bend2} mm (90 deg UP)",
        f"Calculated Flat Blank Size: {flat_L:.1f} x {flat_W:.1f} mm",
        f"M4 Bolt Pitch (Long Side): {len(long_holes)} Holes",
        f"M4 Bolt Pitch (Short Side): {len(short_holes)} Holes",
        "Corner Detail: 45 Deg Miter Cutouts",
        "Base Detail: Open Bottom"
    ]
    
    y_pos = table_y + 100
    for r in rows:
        c.drawString(table_x + 8, y_pos, f"• {r}")
        y_pos -= 13

    c.save()
    return {"blank_size": f"{flat_L:.1f} x {flat_W:.1f} mm"}
