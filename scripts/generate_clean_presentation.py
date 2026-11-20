"""
Executive Clean Presentation Generator for Dayleaf
Theme: Dayleaf Obsidian + Electric Violet / JAIN University
Subject: Design and Thinking
Department: B.Tech CSE (Cyber Security)
Faculty: Dr. Harinee S
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# -------------------------------------------------------------
# Color Palette
# -------------------------------------------------------------
BG_COLOR = RGBColor(10, 7, 19)          # Deep Obsidian #0A0713
CARD_BG = RGBColor(20, 15, 36)          # Dark Violet Glass #140F24
CARD_BORDER = RGBColor(60, 48, 96)      # Subtle Border #3C3060
ACCENT_VIOLET = RGBColor(168, 85, 247)  # Electric Violet #A855F7
ACCENT_CYAN = RGBColor(56, 189, 248)    # Neon Cyan #38BDF8
ACCENT_GREEN = RGBColor(52, 211, 153)   # Emerald Mint #34D399
ACCENT_GOLD = RGBColor(251, 191, 36)    # Amber Gold #FBBF24

TEXT_WHITE = RGBColor(255, 255, 255)
TEXT_PURPLE = RGBColor(233, 213, 255)
TEXT_MUTED = RGBColor(156, 163, 175)
TEXT_BODY = RGBColor(229, 231, 235)

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

def set_slide_background(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BG_COLOR

def add_header(slide, tag_text, title_text, subtitle_text=""):
    """Adds a clean, spacious header with top tag, bold title, and subtitle."""
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.73), Inches(1.15))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    p0 = tf.paragraphs[0]
    p0.text = tag_text.upper()
    p0.font.name = FONT_HEADING
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = ACCENT_CYAN
    p0.space_after = Pt(4)
    
    p1 = tf.add_paragraph()
    p1.text = title_text
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(22)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    
    if subtitle_text:
        p1.space_after = Pt(2)
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.name = FONT_BODY
        p2.font.size = Pt(11)
        p2.font.color.rgb = TEXT_MUTED

def add_card(slide, left, top, width, height, border_color=CARD_BORDER, bg_color=CARD_BG):
    """Draws a clean rounded rectangle container."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.2)
    return shape

def add_footer(slide, current_page, total_pages=12):
    """Adds a clean, minimalist footer."""
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.73), Inches(0.35))
    tf = tb.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = f"Dayleaf: AI Timetable Intelligence  •  Design and Thinking  •  B.Tech CSE (Cyber Security)               Slide {current_page} of {total_pages}"
    p.font.name = FONT_BODY
    p.font.size = Pt(8.5)
    p.font.color.rgb = RGBColor(115, 115, 128)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# =============================================================
# SLIDE 1: Front Title Slide
# =============================================================
slide1 = prs.slides.add_slide(blank_layout)
set_slide_background(slide1)

# Top Bar Card with Jain University Logo
logo_card = add_card(slide1, Inches(0.8), Inches(0.4), Inches(11.73), Inches(1.15), border_color=RGBColor(80, 65, 120))
logo_path = r"screenshots\jain_logo_white_text.png"
if os.path.exists(logo_path):
    slide1.shapes.add_picture(logo_path, Inches(1.05), Inches(0.55), height=Inches(0.8))

# Header info inside top bar
tb_top_info = slide1.shapes.add_textbox(Inches(5.5), Inches(0.48), Inches(6.8), Inches(0.95))
tfi = tb_top_info.text_frame
tfi.word_wrap = True
tfi.margin_left = tfi.margin_top = tfi.margin_right = tfi.margin_bottom = 0
p = tfi.paragraphs[0]
p.text = "DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING"
p.font.name = FONT_HEADING
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.alignment = PP_ALIGN.RIGHT

p = tfi.add_paragraph()
p.text = "Specialization: B.Tech CSE (Cyber Security)  •  Academic Year 2026-27"
p.font.name = FONT_BODY
p.font.size = Pt(10)
p.font.color.rgb = ACCENT_PURPLE = RGBColor(216, 180, 254)
p.alignment = PP_ALIGN.RIGHT

p = tfi.add_paragraph()
p.text = "Course: Design and Thinking"
p.font.name = FONT_BODY
p.font.size = Pt(10)
p.font.bold = True
p.font.color.rgb = ACCENT_CYAN
p.alignment = PP_ALIGN.RIGHT

# Project Title Card (Left)
add_card(slide1, Inches(0.8), Inches(1.75), Inches(5.6), Inches(4.9), border_color=ACCENT_VIOLET)
tb_title = slide1.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.4))
tft = tb_title.text_frame
tft.word_wrap = True
tft.margin_left = tft.margin_top = tft.margin_right = tft.margin_bottom = 0

p = tft.paragraphs[0]
p.text = "DESIGN & THINKING PROJECT"
p.font.name = FONT_HEADING
p.font.size = Pt(10.5)
p.font.bold = True
p.font.color.rgb = ACCENT_CYAN
p.space_after = Pt(8)

p = tft.add_paragraph()
p.text = "Dayleaf"
p.font.name = FONT_HEADING
p.font.size = Pt(36)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(4)

p = tft.add_paragraph()
p.text = "Next-Gen AI Campus & Timetable Intelligence Platform"
p.font.name = FONT_HEADING
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = TEXT_PURPLE
p.space_after = Pt(14)

p = tft.add_paragraph()
p.text = "An autonomous constraint-satisfaction scheduling engine powered by Gemini AI. Eliminates room clashes, prevents faculty fatigue, and delivers clash-free personalized schedules across departments."
p.font.name = FONT_BODY
p.font.size = Pt(11)
p.font.color.rgb = TEXT_BODY
p.space_after = Pt(18)

# Submitted To Card inside Left
p = tft.add_paragraph()
p.text = "PROJECT GUIDANCE / EVALUATION:"
p.font.name = FONT_HEADING
p.font.size = Pt(9.5)
p.font.bold = True
p.font.color.rgb = ACCENT_GOLD
p.space_after = Pt(2)

p = tft.add_paragraph()
p.text = "Submitted to: Dr. Harinee S"
p.font.name = FONT_HEADING
p.font.size = Pt(15)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE

# Right Card: Student Roster Table
add_card(slide1, Inches(6.6), Inches(1.75), Inches(5.93), Inches(4.9), border_color=RGBColor(80, 65, 120))

tb_table_title = slide1.shapes.add_textbox(Inches(6.85), Inches(1.95), Inches(5.4), Inches(0.5))
tftt = tb_table_title.text_frame
tftt.word_wrap = True
tftt.margin_left = tftt.margin_top = tftt.margin_right = tftt.margin_bottom = 0
p = tftt.paragraphs[0]
p.text = "SUBMITTED BY (TEAM MEMBERS)"
p.font.name = FONT_HEADING
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = ACCENT_VIOLET

# Table for Student details
rows = 7
cols = 3
left = Inches(6.85)
top = Inches(2.45)
width = Inches(5.4)
height = Inches(3.9)

table_shape = slide1.shapes.add_table(rows, cols, left, top, width, height)
table = table_shape.table
table.columns[0].width = Inches(0.9)
table.columns[1].width = Inches(2.6)
table.columns[2].width = Inches(1.9)

headers = ["Sl. No.", "Student Name", "USN"]
students = [
    ("1", "Rudraksh Chadha", "25BTRCC045"),
    ("2", "Sakthivel M", "25BTRCC048"),
    ("3", "Sushant Prakash", "25BTRCC053"),
    ("4", "Sudhanshu Kumar", "25BTRCC052"),
    ("5", "Hrishit Chaudhary", "25BTRCC025"),
    ("6", "Mohamed Badreldin", "25BTRCC061"),
]

for col_idx, h_text in enumerate(headers):
    cell = table.cell(0, col_idx)
    cell.fill.solid()
    cell.fill.fore_color.rgb = RGBColor(32, 25, 58)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = cell.text_frame.paragraphs[0]
    p.text = h_text
    p.font.name = FONT_HEADING
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = ACCENT_CYAN
    if col_idx == 0:
        p.alignment = PP_ALIGN.CENTER

for row_idx, (sl, name, usn) in enumerate(students):
    r = row_idx + 1
    row_data = [sl, name, usn]
    for col_idx, text in enumerate(row_data):
        cell = table.cell(r, col_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor(24, 18, 44) if r % 2 == 1 else RGBColor(18, 14, 34)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = cell.text_frame.paragraphs[0]
        p.text = text
        p.font.name = FONT_BODY
        p.font.size = Pt(10.5)
        p.font.bold = (col_idx == 1 and "Sushant" in text)
        p.font.color.rgb = TEXT_WHITE if col_idx < 2 else ACCENT_PURPLE
        if col_idx == 0:
            p.alignment = PP_ALIGN.CENTER

add_footer(slide1, 1)

# =============================================================
# SLIDE 2: Problem Background & Real-World Need
# =============================================================
slide2 = prs.slides.add_slide(blank_layout)
set_slide_background(slide2)
add_header(slide2, "NEED IN TODAY'S WORLD", "Why University Timetabling is Broken Today", "The silent crisis in campus operations: NP-hard complexity managed by manual spreadsheets.")

cards_s2 = [
    ("Combinatorial NP-Hard Problem", "Massive Variable Explosion",
     "A modern university with 4+ departments, 50+ faculty, 15+ labs, and hundreds of students produces over 100,000 slot permutations. Human coordinators cannot compute globally conflict-free schedules manually.",
     ACCENT_VIOLET),
    ("Costly Resource Waste", "Empty High-Tech Labs vs. Overcrowded Halls",
     "Expensive AI, GPU, and Cloud labs sit idle 35% of the week due to fragmented scheduling, while regular lecture halls face double-booking clashes and capacity overflows.",
     ACCENT_CYAN),
    ("Faculty & Student Burnout", "Chaotic Unstructured Timetables",
     "Teachers suffer from 4-5 consecutive lecture marathons without lunch breaks, while students endure erratic 6-hour gap intervals between morning and evening classes.",
     ACCENT_GOLD)
]

for idx, (title, sub, desc, accent) in enumerate(cards_s2):
    x = Inches(0.8) + idx * Inches(3.95)
    y = Inches(1.8)
    w = Inches(3.75)
    h = Inches(4.8)
    
    add_card(slide2, x, y, w, h, border_color=accent)
    tb = slide2.shapes.add_textbox(x + Inches(0.25), y + Inches(0.3), w - Inches(0.5), h - Inches(0.6))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = f"PAIN POINT 0{idx+1}"
    p.font.name = FONT_HEADING
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = accent
    p.space_after = Pt(8)
    
    p = tf.add_paragraph()
    p.text = title
    p.font.name = FONT_HEADING
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(4)
    
    p = tf.add_paragraph()
    p.text = sub
    p.font.name = FONT_BODY
    p.font.size = Pt(11)
    p.font.italic = True
    p.font.color.rgb = TEXT_PURPLE
    p.space_after = Pt(14)
    
    p = tf.add_paragraph()
    p.text = desc
    p.font.name = FONT_BODY
    p.font.size = Pt(11.5)
    p.font.color.rgb = TEXT_BODY

add_footer(slide2, 2)

# =============================================================
# SLIDE 3: Design Thinking Methodology (5-Stage Framework)
# =============================================================
slide3 = prs.slides.add_slide(blank_layout)
set_slide_background(slide3)
add_header(slide3, "DESIGN THINKING FRAMEWORK", "The 5-Stage Human-Centered Innovation Model", "How Design Thinking guided the entire engineering of Dayleaf from empathy to validation.")

stages = [
    ("1. EMPATHIZE", "Interviewed administrators, department HODs, teachers, and students to discover real scheduling pain points.", ACCENT_CYAN),
    ("2. DEFINE", "Synthesized the core design challenge: How might we automate zero-clash scheduling with full human control?", ACCENT_VIOLET),
    ("3. IDEATE", "Architected a dual-engine model: Mathematical constraint satisfaction coupled with Gemini AI co-pilot.", ACCENT_GREEN),
    ("4. PROTOTYPE", "Built Dayleaf Studio — dark neon Obsidian web app with live interactive timetable visualizer.", ACCENT_GOLD),
    ("5. TEST", "Benchmarked with 66 timetable slots, 4 departments, 15 labs, and 50 automated validation suites.", TEXT_PURPLE)
]

for idx, (st_name, st_desc, accent) in enumerate(stages):
    x = Inches(0.8) + idx * Inches(2.38)
    y = Inches(1.8)
    w = Inches(2.2)
    h = Inches(4.8)
    
    add_card(slide3, x, y, w, h, border_color=accent)
    tb = slide3.shapes.add_textbox(x + Inches(0.18), y + Inches(0.3), w - Inches(0.36), h - Inches(0.6))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = f"PHASE 0{idx+1}"
    p.font.name = FONT_HEADING
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = accent
    p.space_after = Pt(6)
    
    p = tf.add_paragraph()
    p.text = st_name
    p.font.name = FONT_HEADING
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(12)
    
    p = tf.add_paragraph()
    p.text = st_desc
    p.font.name = FONT_BODY
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_BODY

add_footer(slide3, 3)

# =============================================================
# SLIDE 4: Stage 1 & 2: Empathize & Define (User Personas)
# =============================================================
slide4 = prs.slides.add_slide(blank_layout)
set_slide_background(slide4)
add_header(slide4, "STAGE 1 & 2: EMPATHIZE & DEFINE", "Campus Personas & Design Challenge Statement", "Understanding the exact needs and frustrations across all institutional levels.")

personas = [
    ("College Administrator", "Oversees campus-wide resources and accreditation metrics.", "Spends 3 weeks at semester start resolving cross-department scheduling clashes manually.", ACCENT_CYAN),
    ("Department HOD", "Manages departmental teaching load, courses, and lab allocations.", "Lacks real-time visibility into shared labs booked by other engineering departments.", ACCENT_VIOLET),
    ("Faculty Member", "Teaches core subjects, conducts lab practicals, and performs research.", "Faces back-to-back lectures without rest or erratic morning/evening gap hours.", ACCENT_GREEN),
    ("B.Tech Student", "Attends theory lectures, lab sessions, and elective seminars.", "Encountering overlapping elective slots or arriving at labs double-booked by other batches.", ACCENT_GOLD)
]

for idx, (role, need, pain, accent) in enumerate(personas):
    r = idx // 2
    c = idx % 2
    x = Inches(0.8) + c * Inches(5.95)
    y = Inches(1.8) + r * Inches(2.5)
    w = Inches(5.7)
    h = Inches(2.25)
    
    add_card(slide4, x, y, w, h, border_color=accent)
    tb = slide4.shapes.add_textbox(x + Inches(0.25), y + Inches(0.2), w - Inches(0.5), h - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = role
    p.font.name = FONT_HEADING
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(4)
    
    p = tf.add_paragraph()
    p.text = f"• GOAL: {need}"
    p.font.name = FONT_BODY
    p.font.size = Pt(10.5)
    p.font.color.rgb = TEXT_PURPLE
    p.space_after = Pt(3)
    
    p = tf.add_paragraph()
    p.text = f"• CORE PAIN: {pain}"
    p.font.name = FONT_BODY
    p.font.size = Pt(10)
    p.font.color.rgb = TEXT_BODY

add_footer(slide4, 4)

# =============================================================
# SLIDE 5: Stage 3: Ideate — Constraint Satisfaction + Gemini AI
# =============================================================
slide5 = prs.slides.add_slide(blank_layout)
set_slide_background(slide5)
add_header(slide5, "STAGE 3: IDEATE", "The Dual-Core AI Architecture of Dayleaf", "Combining mathematical constraint logic with Google Gemini Generative Intelligence.")

# Left Card: Constraint Engine
add_card(slide5, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.8), border_color=ACCENT_VIOLET)
tb_ce = slide5.shapes.add_textbox(Inches(1.05), Inches(2.05), Inches(5.2), Inches(4.3))
tf = tb_ce.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Mathematical Constraint Engine"
p.font.name = FONT_HEADING
p.font.size = Pt(17)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(8)

p = tf.add_paragraph()
p.text = "HARD CONSTRAINTS (Zero Tolerance — Strictly Enforced):"
p.font.name = FONT_HEADING
p.font.size = Pt(10.5)
p.font.bold = True
p.font.color.rgb = ACCENT_CYAN
p.space_after = Pt(4)

hard_rules = [
    "No Room Double-Booking: Exactly 1 session per venue per time slot.",
    "No Faculty Collision: An instructor cannot be in two locations at once.",
    "Section Cohort Non-Overlap: Section cannot have concurrent classes.",
    "Capacity Compliance: Room capacity must equal or exceed enrollment.",
    "Hardware/Lab Matching: Practical subjects allocated only to smart labs."
]
for r in hard_rules:
    pi = tf.add_paragraph()
    pi.text = f"✔ {r}"
    pi.font.name = FONT_BODY
    pi.font.size = Pt(10)
    pi.font.color.rgb = TEXT_BODY
    pi.space_after = Pt(2)

p = tf.add_paragraph()
p.text = "\nSOFT CONSTRAINTS (Optimization Scoring Penalties):"
p.font.name = FONT_HEADING
p.font.size = Pt(10.5)
p.font.bold = True
p.font.color.rgb = ACCENT_GREEN
p.space_after = Pt(4)

soft_rules = [
    "Even Workload Distribution: Max 3-4 teaching hours/day per faculty.",
    "Minimizing Student Wait Gaps between lectures.",
    "Respecting faculty research and PhD supervision windows."
]
for r in soft_rules:
    pi = tf.add_paragraph()
    pi.text = f"★ {r}"
    pi.font.name = FONT_BODY
    pi.font.size = Pt(10)
    pi.font.color.rgb = TEXT_BODY
    pi.space_after = Pt(2)

# Right Card: Gemini AI Assistant
add_card(slide5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), border_color=ACCENT_CYAN)
tb_ai = slide5.shapes.add_textbox(Inches(7.05), Inches(2.05), Inches(5.2), Inches(4.3))
tf = tb_ai.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Gemini LLM Campus Assistant Co-Pilot"
p.font.name = FONT_HEADING
p.font.size = Pt(17)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(8)

ai_pts = [
    ("Multi-Model Resilient Pipeline", "Automated fallback circuit: Gemini-1.5-Flash → Gemini-2.0-Flash → Gemini-Flash-Latest with 8s timeouts to guarantee 100% uptime."),
    ("Natural Language Understanding", "Staff and students interact conversationally: 'Find a free lab on Wednesday afternoon' or 'Which professors have heavy loads?'"),
    ("Integrity Enforcement Layer", "LLM recommendations never bypass database constraints; drafts must clear solver validation before publishing."),
    ("Context-Aware Intelligence", "Understands academic terms (Fall 2026-27), department codes (CSE, CYS, DS, ECE), and live room capacity limits.")
]

for title, desc in ai_pts:
    pt = tf.add_paragraph()
    pt.text = f"▶ {title}"
    pt.font.name = FONT_HEADING
    pt.font.size = Pt(11)
    pt.font.bold = True
    pt.font.color.rgb = ACCENT_VIOLET
    pt.space_after = Pt(2)
    
    pd = tf.add_paragraph()
    pd.text = desc
    pd.font.name = FONT_BODY
    pd.font.size = Pt(10)
    pd.font.color.rgb = TEXT_BODY
    pd.space_after = Pt(6)

add_footer(slide5, 5)

# =============================================================
# SLIDE 6: Stage 4: Prototype — Dayleaf Studio Workspace
# =============================================================
slide6 = prs.slides.add_slide(blank_layout)
set_slide_background(slide6)
add_header(slide6, "STAGE 4: PROTOTYPE (ACTUAL UI)", "Dayleaf Studio: Obsidian & Violet Interface", "The live platform dashboard providing unified campus oversight and role-based access.")

# High-Res Screenshot Frame
ws_ss = r"project-report\img\03_dashboard.png"
if os.path.exists(ws_ss):
    add_card(slide6, Inches(0.8), Inches(1.8), Inches(7.5), Inches(4.8), border_color=ACCENT_VIOLET)
    slide6.shapes.add_picture(ws_ss, Inches(0.85), Inches(1.85), width=Inches(7.4))

# Side Explanations
add_card(slide6, Inches(8.5), Inches(1.8), Inches(4.03), Inches(4.8), border_color=CARD_BORDER)
tb = slide6.shapes.add_textbox(Inches(8.75), Inches(2.05), Inches(3.55), Inches(4.3))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Key UI Innovations"
p.font.name = FONT_HEADING
p.font.size = Pt(17)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(10)

ui_cards = [
    ("Obsidian Dark Palette", "Deep #0A0713 background minimizes visual fatigue during scheduling tasks."),
    ("Multi-Role Workspaces", "Contextually switches for Admin, HOD, Faculty, and Students upon login."),
    ("Real-Time Campus Badge", "Displays active term (Fall Semester 2026-27) and live operational status."),
    ("Unified Navigation", "Instant one-click access to Timetable, Academics, Classrooms, People & AI.")
]

for title, desc in ui_cards:
    p_t = tf.add_paragraph()
    p_t.text = f"✦ {title}"
    p_t.font.name = FONT_HEADING
    p_t.font.size = Pt(11)
    p_t.font.bold = True
    p_t.font.color.rgb = ACCENT_CYAN
    p_t.space_after = Pt(2)
    
    p_d = tf.add_paragraph()
    p_d.text = desc
    p_d.font.name = FONT_BODY
    p_d.font.size = Pt(10)
    p_d.font.color.rgb = TEXT_BODY
    p_d.space_after = Pt(8)

add_footer(slide6, 6)

# =============================================================
# SLIDE 7: Prototype Deep Dive: Timetable Optimizer & Visualizer
# =============================================================
slide7 = prs.slides.add_slide(blank_layout)
set_slide_background(slide7)
add_header(slide7, "CORE MODULE 01 (ACTUAL UI)", "Constraint Optimizer & Live Timetable Visualizer", "Sub-second schedule solver, conflict scoring metric, and publication workflow.")

tt_ss = r"project-report\img\04_timetable.png"
if os.path.exists(tt_ss):
    add_card(slide7, Inches(0.8), Inches(1.8), Inches(7.5), Inches(4.8), border_color=ACCENT_VIOLET)
    slide7.shapes.add_picture(tt_ss, Inches(0.85), Inches(1.85), width=Inches(7.4))

add_card(slide7, Inches(8.5), Inches(1.8), Inches(4.03), Inches(4.8), border_color=CARD_BORDER)
tb = slide7.shapes.add_textbox(Inches(8.75), Inches(2.05), Inches(3.55), Inches(4.3))
tf = tb.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Solver Capabilities"
p.font.name = FONT_HEADING
p.font.size = Pt(17)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(10)

solver_cards = [
    ("One-Click Auto Generation", "Evaluates all teaching assignments and builds clash-free drafts in <850ms."),
    ("Multi-Dimensional Filtering", "Filter by Term (Fall 2026-27), Department (CSE/CYS/DS/ECE), or Section."),
    ("Conflict Soft-Score Gauge", "Calculates penalty index where a lower score indicates a more balanced schedule."),
    ("Review & Publish Gate", "Drafts are reviewed by Department HODs before publishing live to student portals.")
]

for title, desc in solver_cards:
    p_t = tf.add_paragraph()
    p_t.text = f"✔ {title}"
    p_t.font.name = FONT_HEADING
    p_t.font.size = Pt(11)
    p_t.font.bold = True
    p_t.font.color.rgb = ACCENT_GREEN
    p_t.space_after = Pt(2)
    
    p_d = tf.add_paragraph()
    p_d.text = desc
    p_d.font.name = FONT_BODY
    p_d.font.size = Pt(10)
    p_d.font.color.rgb = TEXT_BODY
    p_d.space_after = Pt(8)

add_footer(slide7, 7)

# =============================================================
# SLIDE 8: Academic Structure & Smart Resource Allocation
# =============================================================
slide8 = prs.slides.add_slide(blank_layout)
set_slide_background(slide8)
add_header(slide8, "CORE MODULE 02", "Academic Structure & Smart Resource Allocation", "Structured relationships across departments, sections, subjects, and specialized venues.")

acad_cards = [
    ("4 Core Departments", "Computer Science & Eng (CSE), Cybersecurity (CYS), Data Science & AI (DS), and Electronics & Comm (ECE). Each independently manages curriculum requirements.", ACCENT_CYAN),
    ("2 Active Terms & 10 Sections", "Fall Semester 2026-27 (Active) and Spring Semester 2026-27. Semesters 3 & 5 divided into Section cohorts (A, B, C) for parallel lab practicals.", ACCENT_VIOLET),
    ("15 Classrooms & Smart Labs", "Includes 5 specialized labs (AI/Deep Learning, Cloud, Cyber Forensics) with 75 capacity, plus 10 lecture halls & auditoriums (Audi-1: 250 seats).", ACCENT_GREEN),
    ("18 Accredited Subjects", "Theory courses (3-4 credit lectures) and Intensive Lab sessions (2 hours) with mandatory lab equipment matching constraints.", ACCENT_GOLD)
]

for idx, (title, desc, accent) in enumerate(acad_cards):
    r = idx // 2
    c = idx % 2
    x = Inches(0.8) + c * Inches(5.95)
    y = Inches(1.8) + r * Inches(2.5)
    w = Inches(5.7)
    h = Inches(2.25)
    
    add_card(slide8, x, y, w, h, border_color=accent)
    tb = slide8.shapes.add_textbox(x + Inches(0.25), y + Inches(0.25), w - Inches(0.5), h - Inches(0.5))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = FONT_HEADING
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(6)
    
    p = tf.add_paragraph()
    p.text = desc
    p.font.name = FONT_BODY
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_BODY

add_footer(slide8, 8)

# =============================================================
# SLIDE 9: Cyber Security Architecture & Access Control
# =============================================================
slide9 = prs.slides.add_slide(blank_layout)
set_slide_background(slide9)
add_header(slide9, "CYBER SECURITY ARCHITECTURE", "Enterprise Defensive Security & Access Controls", "Tailored security mechanisms reflecting B.Tech Cyber Security engineering principles.")

sec_items = [
    ("5-Tier Role-Based Access Control (RBAC)", 
     "Strict route-level authorization guards for:\n• Super Admin (System ops)\n• College Admin (Campus setup)\n• HOD (Dept approvals)\n• Faculty (View & availability)\n• Student (Personal timetable)\nGuarantees horizontal & vertical privilege separation.", 
     ACCENT_VIOLET),
    ("Hardened Cookie Session Management", 
     "• HTTP-only cookie flags prevent XSS session hijacking.\n• SameSite=Lax safeguards against cross-site exploitation.\n• Strict dynamic host matching.\n• Refresh token family hashing with immediate revocation on compromise.", 
     ACCENT_CYAN),
    ("CSRF Double-Submit HMAC Protection", 
     "All state-mutating requests (POST, PUT, PATCH, DELETE) require a cryptographically signed X-CSRF-Token header validated via constant-time HMAC comparison to block cross-site forgery.", 
     ACCENT_GREEN),
    ("Tamper-Proof Audit Trail Logging", 
     "Every single timetable modification, venue swap, or grade change is permanently recorded with user ID, IP address, previous value, new value, and ISO 8601 UTC timestamp.", 
     ACCENT_GOLD)
]

for idx, (title, desc, accent) in enumerate(sec_items):
    r = idx // 2
    c = idx % 2
    x = Inches(0.8) + c * Inches(5.95)
    y = Inches(1.8) + r * Inches(2.5)
    w = Inches(5.7)
    h = Inches(2.25)
    
    add_card(slide9, x, y, w, h, border_color=accent)
    tb = slide9.shapes.add_textbox(x + Inches(0.25), y + Inches(0.2), w - Inches(0.5), h - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = FONT_HEADING
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(4)
    
    p = tf.add_paragraph()
    p.text = desc
    p.font.name = FONT_BODY
    p.font.size = Pt(9.5)
    p.font.color.rgb = TEXT_BODY

add_footer(slide9, 9)

# =============================================================
# SLIDE 10: Dayleaf AI Assistant (Conversational Campus Co-Pilot)
# =============================================================
slide10 = prs.slides.add_slide(blank_layout)
set_slide_background(slide10)
add_header(slide10, "CAMPUS AI CO-PILOT", "Dayleaf AI: Natural Language Scheduling Dialogues", "Empowering staff and faculty to query and update campus records in plain English.")

add_card(slide10, Inches(0.8), Inches(1.8), Inches(11.73), Inches(4.8), border_color=ACCENT_VIOLET)
tb10 = slide10.shapes.add_textbox(Inches(1.1), Inches(2.05), Inches(11.13), Inches(4.3))
tf = tb10.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "Natural Language Dialogues with Campus Database"
p.font.name = FONT_HEADING
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(10)

dialogues = [
    ("USER QUERY: 'Find a free lab on Wednesday afternoon for CSE-3A'",
     "DAYLEAF AI: 'Cloud & Networks Lab is completely free on Wednesday from 2:00 PM to 4:00 PM with 75 workstations available.'"),
    ("USER QUERY: 'Which faculty members have more than 14 teaching hours this week?'",
     "DAYLEAF AI: 'Prof. Arjun Menon (16 hrs) and Dr. Kavya Iyer (15 hrs) exceed target workload. Recommended: Reassign 1 elective practical to Prof. Kunal Deshmukh.'"),
    ("USER QUERY: 'Generate a clash-free timetable draft for Cybersecurity Semester 5'",
     "DAYLEAF AI: 'Triggering constraint optimization solver... Draft #4 generated with 0 hard clashes and soft penalty score of 12. Ready for HOD review.'")
]

for q, a in dialogues:
    pq = tf.add_paragraph()
    pq.text = f"💬 {q}"
    pq.font.name = FONT_HEADING
    pq.font.size = Pt(11.5)
    pq.font.bold = True
    pq.font.color.rgb = ACCENT_CYAN
    pq.space_after = Pt(2)
    
    pa = tf.add_paragraph()
    pa.text = f"🤖 {a}"
    pa.font.name = FONT_BODY
    pa.font.size = Pt(10.5)
    pa.font.color.rgb = TEXT_BODY
    pa.space_after = Pt(10)

add_footer(slide10, 10)

# =============================================================
# SLIDE 11: Stage 5: Testing & Benchmark Metrics
# =============================================================
slide11 = prs.slides.add_slide(blank_layout)
set_slide_background(slide11)
add_header(slide11, "STAGE 5: TESTING & VALIDATION", "Empirical Benchmarks & System Verification", "Formally verified with production-scale data and 100% automated test coverage.")

benchmarks = [
    ("50 / 50 Tests Passing", "100% backend test suite validation covering auth, RBAC, solver logic, and CORS security.", ACCENT_GREEN),
    ("<850ms Solver Speed", "Constraint satisfaction engine generates 66 weekly timetable slots across 4 departments in sub-seconds.", ACCENT_CYAN),
    ("Zero Room Clashes", "Formally verified: 0 venue double-bookings and 0 faculty collision across all academic terms.", ACCENT_VIOLET),
    ("Complete Campus Data", "Seeded with 4 departments, 15 classrooms/labs, 11 faculty, 10 students, and 18 accredited courses.", ACCENT_GOLD)
]

for idx, (title, desc, accent) in enumerate(benchmarks):
    x = Inches(0.8) + idx * Inches(2.95)
    y = Inches(1.8)
    w = Inches(2.75)
    h = Inches(4.8)
    
    add_card(slide11, x, y, w, h, border_color=accent)
    tb = slide11.shapes.add_textbox(x + Inches(0.2), y + Inches(0.3), w - Inches(0.4), h - Inches(0.6))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = f"METRIC 0{idx+1}"
    p.font.name = FONT_HEADING
    p.font.size = Pt(9.5)
    p.font.bold = True
    p.font.color.rgb = accent
    p.space_after = Pt(8)
    
    p = tf.add_paragraph()
    p.text = title
    p.font.name = FONT_HEADING
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(10)
    
    p = tf.add_paragraph()
    p.text = desc
    p.font.name = FONT_BODY
    p.font.size = Pt(11)
    p.font.color.rgb = TEXT_BODY

add_footer(slide11, 11)

# =============================================================
# SLIDE 12: Future Roadmap & Project Conclusion
# =============================================================
slide12 = prs.slides.add_slide(blank_layout)
set_slide_background(slide12)

# Big Centered Card
add_card(slide12, Inches(1.2), Inches(0.8), Inches(10.93), Inches(5.9), border_color=ACCENT_VIOLET)
tb12 = slide12.shapes.add_textbox(Inches(1.5), Inches(1.1), Inches(10.33), Inches(5.3))
tf = tb12.text_frame
tf.word_wrap = True

p = tf.paragraphs[0]
p.text = "DESIGN AND THINKING  •  PROJECT CONCLUSION"
p.font.name = FONT_HEADING
p.font.size = Pt(11.5)
p.font.bold = True
p.font.color.rgb = ACCENT_CYAN
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(6)

p = tf.add_paragraph()
p.text = "Dayleaf: Transforming University Timetabling"
p.font.name = FONT_HEADING
p.font.size = Pt(28)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(10)

p = tf.add_paragraph()
p.text = "Through human-centered Design Thinking, Dayleaf replaces weeks of painful manual timetable scheduling with an autonomous, conflict-free, and intelligent platform. By bridging mathematical constraint satisfaction with Gemini AI, university operations become faster, fairer, and future-ready."
p.font.name = FONT_BODY
p.font.size = Pt(11.5)
p.font.color.rgb = TEXT_BODY
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(16)

# Future Roadmap 3 bullets
p = tf.add_paragraph()
p.text = "FUTURE ROADMAP: Mobile Push Notifications  •  Biometric IoT Attendance Sync  •  Autonomous Substitute Allocation"
p.font.name = FONT_HEADING
p.font.size = Pt(10)
p.font.bold = True
p.font.color.rgb = ACCENT_GOLD
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(16)

# Submitted To Card inside conclusion
p = tf.add_paragraph()
p.text = "PROJECT GUIDED AND EVALUATED BY:"
p.font.name = FONT_HEADING
p.font.size = Pt(10)
p.font.bold = True
p.font.color.rgb = ACCENT_PURPLE
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(2)

p = tf.add_paragraph()
p.text = "Submitted to: Dr. Harinee S"
p.font.name = FONT_HEADING
p.font.size = Pt(16)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(14)

# Team acknowledgments
p = tf.add_paragraph()
p.text = "Rudraksh Chadha (25BTRCC045)  •  Sakthivel M (25BTRCC048)  •  Sushant Prakash (25BTRCC053)\nSudhanshu Kumar (25BTRCC052)  •  Hrishit Chaudhary (25BTRCC025)  •  Mohamed Badreldin (25BTRCC061)"
p.font.name = FONT_BODY
p.font.size = Pt(10.5)
p.font.color.rgb = TEXT_MUTED
p.alignment = PP_ALIGN.CENTER
p.space_after = Pt(10)

p = tf.add_paragraph()
p.text = "Thank You! Questions & Discussion Welcome."
p.font.name = FONT_HEADING
p.font.size = Pt(14)
p.font.bold = True
p.font.color.rgb = ACCENT_GREEN
p.alignment = PP_ALIGN.CENTER

add_footer(slide12, 12)

# Save
output_path = "Dayleaf_AI_Campus_Timetable_Final.pptx"
prs.save(output_path)
print(f"Clean Executive Presentation saved successfully to: {os.path.abspath(output_path)}")
