import os
import math
import cadquery as cq
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.pdfgen import canvas

def calculate_m4_holes(length):
    edge_offset = 15.0
    usable_len = length - (2 * edge_offset)
    if usable_len <= 0:
        return [length / 2.0]
    num_spaces = math.ceil(usable_len / 150.0)
    if num_spaces < 2:
        num_spaces = 2
    pitch = usable_len / num_spaces
    return [edge_offset + (i * pitch) for i in range(num_spaces + 1)]

def draw_title_block(c, page_w, page_h, dwg_no, title, sheet_str, thick):
    tb_x, tb_y, tb_w, tb_h = page_w - 260, 15, 245, 85
    c.setLineWidth(1.0)
    c.setStrokeColor(colors.black)
    c.rect(tb_x, tb_y, tb_w, tb_h)
    
    c.line(tb_x, tb_y + 60, tb_x + tb_w, tb_y + 60)
    c.line(tb_x, tb_y + 40, tb_x + tb_w, tb_y + 40)
    c.line(tb_x, tb_y + 20, tb_x + tb_w, tb_y + 20)
    c.line(tb_x + 120, tb_y, tb_x + 120, tb_y + 60)

    c.setFont("Helvetica-Bold", 8)
    c.drawString(tb_x + 5, tb_y + 68, "PROJECT: SHEET METAL PODIUM ASSEMBLY")
    c.drawString(tb_x + 5, tb_y + 48, f"DWG NO: {dwg_no}")
    c.drawString(tb_x + 125, tb_y + 48, f"TITLE: {title}")
    c.drawString(tb_x + 5, tb_y + 28, f"THICKNESS: {thick} mm")
    c.drawString(tb_x + 125, tb_y + 28, f"SHEET: {sheet_str}")
    c.drawString(tb_x + 5, tb_y + 8, "UNITS / SCALE: mm / N.T.S.")

def draw_dimension(c, x1, y1, x2, y2, text, offset=15, is_vert=False):
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.blue)
    c.setFillColor(colors.blue)
    c.setFont("Helvetica", 7)
    if not is_vert:
        c.line(x1, y1, x1, y1 + offset)
        c.line(x2, y2, x2, y2 + offset)
        c.line(x1, y1 + offset - 2, x2, y2 + offset - 2)
        c.drawCentredString((x1 + x2)/2, y1 + offset + 2, text)
    else:
        c.line(x1, y1, x1 + offset, y1)
        c.line(x2, y2, x2 + offset, y2)
        c.line(x1 + offset - 2, y1, x1 + offset - 2, y2)
        c.drawCentredString(x1 + offset + 8, (y1 + y2)/2, text)

def generate_all_files(length, width, height, thickness, bend1, bend2, job_id):
    output_dir = f"outputs/{job_id}"
    os.makedirs(output_dir, exist_ok=True)

    # Automatic Inside Bend Radius and K-Factor calculation
    bend_radius = thickness
    k_factor = 0.33
    bd = 2 * (bend_radius + thickness) - (math.pi / 2) * (bend_radius + (k_factor * thickness))

    # Flat dimensions
    flat_L = length + (2 * bend1) + (2 * bend2) - (4 * bd)
    flat_W = width + (2 * bend1) + (2 * bend2) - (4 * bd)

    long_holes = calculate_m4_holes(length)
    short_holes = calculate_m4_holes(width)

    # 1. STEP Multi-Body CAD Model Generation
    def create_panel(p_len):
        base = cq.Workplane("XY").rect(p_len, thickness).extrude(bend1)
        top_lip = cq.Workplane("XY").workplane(offset=bend1)\
            .rect(p_len, bend2).extrude(thickness)\
            .translate((0, -bend2/2 + thickness/2, 0))
        panel = base.union(top_lip)
        
        for h_x in calculate_m4_holes(p_len):
            pos_x = h_x - (p_len / 2.0)
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

    # 2. DXF Flat Pattern Export
    flat_sheet = cq.Workplane("XY").rect(flat_L, flat_W).extrude(thickness)
    dxf_path = os.path.join(output_dir, "flat_pattern.dxf")
    cq.exporters.export(flat_sheet, dxf_path)

    # 3. Multi-Page Technical Drawing PDF Export
    pdf_path = os.path.join(output_dir, "podium_drawings.pdf")
    c = canvas.Canvas(pdf_path, pagesize=landscape(A4))
    page_w, page_h = landscape(A4)

    # PAGE 1: ASSEMBLY & SECTION VIEWS
    c.setLineWidth(1.5)
    c.rect(15, 15, page_w - 30, page_h - 30)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, page_h - 40, "MAIN PODIUM ASSEMBLY BLUEPRINT")
    c.line(30, page_h - 46, page_w - 30, page_h - 46)

    # Front View with Double Line Sheet Thickness
    fx, fy, fw, fh = 40, 310, 150, 100
    c.setLineWidth(1.0)
    c.rect(fx, fy, fw, fh)
    c.rect(fx + 2, fy + 2, fw - 4, fh - 4)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.black)
    c.drawString(fx + 35, fy - 12, "FRONT ELEVATION")
    draw_dimension(c, fx, fy + fh, fx + fw, fy + fh, f"L = {length} mm", 10)
    draw_dimension(c, fx + fw, fy, fx + fw, fy + fh, f"H = {height} mm", 10, is_vert=True)

    # Section A-A Line
    c.setDash(4, 2)
    c.setStrokeColor(colors.black)
    c.line(fx + fw/2, fy - 10, fx + fw/2, fy + fh + 10)
    c.drawString(fx + fw/2 - 3, fy + fh + 14, "A")
    c.drawString(fx + fw/2 - 3, fy - 22, "A")
    c.setDash(1, 0)

    # Side View
    sx, sy, sw, sh = 240, 310, 100, 100
    c.rect(sx, sy, sw, sh)
    c.rect(sx + 2, sy + 2, sw - 4, sh - 4)
    c.drawString(sx + 25, sy - 12, "SIDE VIEW")
    draw_dimension(c, sx, sy + sh, sx + sw, sy + sh, f"W = {width} mm", 10)

    # Section A-A Profile View
    sec_x, sec_y = 380, 310
    c.drawString(sec_x + 10, sec_y - 12, "SECTION A-A")
    c.rect(sec_x, sec_y + sh - 6, sw, 6)
    c.rect(sec_x, sec_y, 6, sh - 6)
    c.rect(sec_x + sw - 6, sec_y, 6, sh - 6)

    # Top View with Miter Lines
    tx, ty, tw, th = 40, 140, 150, 100
    c.rect(tx, ty, tw, th)
    c.rect(tx + 8, ty + 8, tw - 16, th - 16)
    c.line(tx, ty, tx + 8, ty + 8)
    c.line(tx + tw, ty, tx + tw - 8, ty + 8)
    c.line(tx, ty + th, tx + 8, ty + th - 8)
    c.line(tx + tw, ty + th, tx + tw - 8, ty + th - 8)
    c.drawString(tx + 45, ty - 12, "TOP VIEW (LIP MITERS)")

    # Isometric View Diagram
    iso_x, iso_y = 240, 140
    c.rect(iso_x, iso_y, 110, 100)
    c.drawString(iso_x + 15, iso_y - 12, "ISOMETRIC VIEW")
    c.line(iso_x + 20, iso_y + 20, iso_x + 80, iso_y + 20)
    c.line(iso_x + 80, iso_y + 20, iso_x + 80, iso_y + 70)
    c.line(iso_x + 80, iso_y + 70, iso_x + 20, iso_y + 70)
    c.line(iso_x + 20, iso_y + 70, iso_x + 20, iso_y + 20)
    c.line(iso_x + 20, iso_y + 70, iso_x + 40, iso_y + 90)
    c.line(iso_x + 80, iso_y + 70, iso_x + 100, iso_y + 90)
    c.line(iso_x + 40, iso_y + 90, iso_x + 100, iso_y + 90)
    c.line(iso_x + 100, iso_y + 90, iso_x + 100, iso_y + 40)
    c.line(iso_x + 80, iso_y + 20, iso_x + 100, iso_y + 40)

    draw_title_block(c, page_w, page_h, f"POD-ASM-{job_id}", "MAIN ASSEMBLY", "1 OF 2", thickness)
    c.showPage()

    # PAGE 2: INDIVIDUAL PART FLAT PATTERN
    c.setLineWidth(1.5)
    c.rect(15, 15, page_w - 30, page_h - 30)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(30, page_h - 40, "PART DETAIL: FRONT & BACK PANEL")
    c.line(30, page_h - 46, page_w - 30, page_h - 46)

    # Formed 2D Profile View
    px, py, pw, ph = 40, 250, 160, 120
    c.setLineWidth(1.0)
    c.rect(px, py, pw, ph)
    c.rect(px + 3, py + 3, pw - 6, ph - 6)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(px + 35, py - 12, "FORMED PANEL ELEVATION")
    draw_dimension(c, px, py + ph, px + pw, py + ph, f"{length} mm", 10)
    draw_dimension(c, px + pw, py, px + pw, py + ph, f"{height} mm", 10, is_vert=True)

    # Side Profile (Double Bend Channels)
    spx, spy = 240, 250
    c.rect(spx, spy, 15, ph)
    c.rect(spx + 15, spy + ph - 20, 15, 20)
    c.drawString(spx - 5, spy - 12, "DOUBLE BEND PROFILE")
    draw_dimension(c, spx, spy, spx + 15, spy, f"F1: {bend1}mm", -15)
    draw_dimension(c, spx + 15, spy + ph - 20, spx + 30, spy + ph - 20, f"F2: {bend2}mm", 10)

    # Flat Pattern Layout with 45-deg Miters & M4 Holes
    flx, fly, flw, flh = 40, 55, 220, 140
    c.drawString(flx, fly + flh + 8, f"UNBENT FLAT PATTERN (SIZE: {flat_L:.1f} x {flat_W:.1f} mm)")
    
    p = c.beginPath()
    m = 12
    p.moveTo(flx + m, fly)
    p.lineTo(flx + flw - m, fly)
    p.lineTo(flx + flw, fly + m)
    p.lineTo(flx + flw, fly + flh - m)
    p.lineTo(flx + flw - m, fly + flh)
    p.lineTo(flx + m, fly + flh)
    p.lineTo(flx, fly + flh - m)
    p.lineTo(flx, fly + m)
    p.close()
    c.drawPath(p, fill=0, stroke=1)

    c.setDash(2, 2)
    c.line(flx + 20, fly, flx + 20, fly + flh)
    c.line(flx + flw - 20, fly, flx + flw - 20, fly + flh)
    c.line(flx, fly + 20, flx + flw, fly + 20)
    c.line(flx, fly + flh - 20, flx + flw, fly + flh - 20)
    c.setDash(1, 0)

    # M4 Holes on Flat Layout
    for hx in long_holes:
        scaled_hx = flx + 20 + (hx / length) * (flw - 40)
        c.circle(scaled_hx, fly + 10, 2, fill=0, stroke=1)
        c.circle(scaled_hx, fly + flh - 10, 2, fill=0, stroke=1)

    draw_title_block(c, page_w, page_h, f"POD-PRT-{job_id}", "FRONT/BACK PANEL", "2 OF 2", thickness)
    c.save()

    return {"blank_size": f"{flat_L:.1f} x {flat_W:.1f} mm"}
