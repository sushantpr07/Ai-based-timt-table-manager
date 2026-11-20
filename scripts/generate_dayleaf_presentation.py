"""
Dayleaf Presentation Generator
Creates a professional 16:9 widescreen PowerPoint presentation (.pptx)
for Design and Thinking course in B.Tech CSE (Cyber Security).
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# -------------------------------------------------------------
# Color Palette (Dayleaf Obsidian + Electric Violet Theme)
# -------------------------------------------------------------
BG_COLOR = RGBColor(11, 8, 19)         # Deep Obsidian #0B0813
CARD_BG = RGBColor(22, 17, 38)         # Glass Card #161126
CARD_BORDER = RGBColor(56, 44, 92)     # Muted Violet Border #382C5C
CARD_ACCENT = RGBColor(168, 85, 247)   # Electric Violet #A855F7
CYAN_ACCENT = RGBColor(56, 189, 248)   # Neon Cyan #38BDF8
GREEN_ACCENT = RGBColor(52, 211, 153)  # Emerald #34D399
ORANGE_ACCENT = RGBColor(251, 146, 60) # Amber #FB923C

TEXT_WHITE = RGBColor(255, 255, 255)
TEXT_PURPLE = RGBColor(233, 213, 255)  # Light lavender #E9D5FF
TEXT_MUTED = RGBColor(161, 161, 170)   # Slate gray #A1A1AA
TEXT_BODY = RGBColor(226, 232, 240)    # Light gray #E2E8F0

FONT_NAME = "Segoe UI"

def set_slide_background(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = BG_COLOR

def add_header(slide, category_text, title_text, subtitle_text=""):
    """Adds a standardized Dayleaf header with category badge, bold title, and subtitle."""
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.2))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    
    # 1. Category Badge
    p0 = tf.paragraphs[0]
    p0.text = "  " + category_text.upper() + "  "
    p0.font.name = FONT_NAME
    p0.font.size = Pt(9.5)
    p0.font.bold = True
    p0.font.color.rgb = CYAN_ACCENT
    p0.space_after = Pt(4)
    
    # 2. Main Title
    p1 = tf.add_paragraph()
    p1.text = title_text
    p1.font.name = FONT_NAME
    p1.font.size = Pt(24)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    
    # 3. Subtitle (if any)
    if subtitle_text:
        p1.space_after = Pt(2)
        p2 = tf.add_paragraph()
        p2.text = subtitle_text
        p2.font.name = FONT_NAME
        p2.font.size = Pt(11.5)
        p2.font.color.rgb = TEXT_MUTED

def add_card(slide, left, top, width, height, border_color=CARD_BORDER, bg_color=CARD_BG):
    """Draws a rounded card container with glass effect background."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.color.rgb = border_color
    shape.line.width = Pt(1.2)
    return shape

def add_footer(slide, current_page, total_pages=15):
    """Adds small Dayleaf footer with slide numbers."""
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.05), Inches(11.7), Inches(0.35))
    tf = footer_box.text_frame
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = f"Dayleaf — AI Campus & Timetable Intelligence  •  Design and Thinking  •  B.Tech CSE (Cyber Security)               Slide {current_page} of {total_pages}"
    p.font.name = FONT_NAME
    p.font.size = Pt(8.5)
    p.font.color.rgb = RGBColor(113, 113, 122)

# =============================================================
# BUILD PRESENTATION
# =============================================================
prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# -------------------------------------------------------------
# SLIDE 1: Title & Team Roster
# -------------------------------------------------------------
slide1 = prs.slides.add_slide(blank_layout)
set_slide_background(slide1)

# Subtle wave accent on right if exists
wave_path = r"screenshots\wave_violet.png"
if os.path.exists(wave_path):
    slide1.shapes.add_picture(wave_path, Inches(9.2), Inches(0.8), width=Inches(3.3))

# Title Card / Banner
title_box = slide1.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(10.0), Inches(2.2))
tf = title_box.text_frame
tf.word_wrap = True
tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

p_badge = tf.paragraphs[0]
p_badge.text = "DESIGN AND THINKING PROJECT  •  B.TECH CSE (CYBER SECURITY)"
p_badge.font.name = FONT_NAME
p_badge.font.size = Pt(11)
p_badge.font.bold = True
p_badge.font.color.rgb = CARD_ACCENT
p_badge.space_after = Pt(8)

p_main = tf.add_paragraph()
p_main.text = "Dayleaf: Next-Gen AI Campus &\nTimetable Intelligence Platform"
p_main.font.name = FONT_NAME
p_main.font.size = Pt(32)
p_main.font.bold = True
p_main.font.color.rgb = TEXT_WHITE
p_main.space_after = Pt(8)

p_desc = tf.add_paragraph()
p_desc.text = "A modern constraint-satisfaction scheduling engine powered by Gemini AI, designed to eliminate university schedule conflicts, optimize classroom utilization, and empower students and faculty."
p_desc.font.name = FONT_NAME
p_desc.font.size = Pt(12)
p_desc.font.color.rgb = TEXT_MUTED

# Team Members Grid (6 members in 2 rows x 3 columns)
team_members = [
    ("Rudraksh Chadha", "25BTRCC045", "Lead Researcher & Problem Framing"),
    ("Sakthivel M", "25BTRCC048", "UI/UX & Design Thinking Lead"),
    ("Sushant Prakash", "25BTRCC053", "Full-Stack System Architect"),
    ("Sudhanshu Kumar", "25BTRCC052", "Constraint Engine & DB Modeler"),
    ("Hrishit Chaudhary", "25BTRCC025", "Cyber Security & Access Control"),
    ("Mohamed Badreldin", "25BTRCC061", "QA, Testing & Verification"),
]

col_w = Inches(3.75)
row_h = Inches(1.5)
left_base = Inches(0.8)
top_base = Inches(3.3)

for idx, (name, usn, role) in enumerate(team_members):
    r = idx // 3
    c = idx % 3
    x = left_base + c * (col_w + Inches(0.25))
    y = top_base + r * (row_h + Inches(0.2))
    
    add_card(slide1, x, y, col_w, row_h, border_color=RGBColor(67, 56, 102) if "Sushant" in name else CARD_BORDER)
    
    tb = slide1.shapes.add_textbox(x + Inches(0.2), y + Inches(0.15), col_w - Inches(0.4), row_h - Inches(0.3))
    tff = tb.text_frame
    tff.word_wrap = True
    tff.margin_left = tff.margin_top = tff.margin_right = tff.margin_bottom = 0
    
    p_num = tff.paragraphs[0]
    p_num.text = f"MEMBER 0{idx+1}  •  {usn}"
    p_num.font.name = FONT_NAME
    p_num.font.size = Pt(9)
    p_num.font.bold = True
    p_num.font.color.rgb = CYAN_ACCENT
    p_num.space_after = Pt(2)
    
    p_name = tff.add_paragraph()
    p_name.text = name
    p_name.font.name = FONT_NAME
    p_name.font.size = Pt(14)
    p_name.font.bold = True
    p_name.font.color.rgb = TEXT_WHITE
    p_name.space_after = Pt(2)
    
    p_role = tff.add_paragraph()
    p_role.text = role
    p_role.font.name = FONT_NAME
    p_role.font.size = Pt(10)
    p_role.font.color.rgb = TEXT_PURPLE

add_footer(slide1, 1)

# -------------------------------------------------------------
# SLIDE 2: The Problem in Today's Universities
# -------------------------------------------------------------
slide2 = prs.slides.add_slide(blank_layout)
set_slide_background(slide2)
add_header(slide2, "PROBLEM BACKGROUND", "Why University Timetabling is Broken Today", "The silent crisis in campus scheduling: NP-hard complexity managed by manual spreadsheets.")

cards_s2 = [
    ("Combinatorial Nightmare", "NP-Hard Complexity",
     "A mid-sized college with 50+ faculty, 4 departments, 15+ labs, and 40+ sections results in over 100,000 slot combinations. Human schedulers simply cannot compute clash-free global optima.",
     ORANGE_ACCENT),
    ("Resource Under-Utilization", "Empty Labs vs. Overcrowded Halls",
     "Expensive AI/Cloud labs sit empty 35% of the week while standard lecture halls face double-booking conflicts and capacity overflows, wasting millions in institutional infrastructure.",
     CYAN_ACCENT),
    ("Faculty & Student Burnout", "Unpredictable Workloads",
     "Faculty members frequently suffer from 5 consecutive lecture marathons without lunch breaks, while students endure chaotic gap hours or overlapping elective courses.",
     CARD_ACCENT),
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
    
    p0 = tf.paragraphs[0]
    p0.text = f"CRITICAL ISSUE 0{idx+1}"
    p0.font.name = FONT_NAME
    p0.font.size = Pt(10)
    p0.font.bold = True
    p0.font.color.rgb = accent
    p0.space_after = Pt(8)
    
    p1 = tf.add_paragraph()
    p1.text = title
    p1.font.name = FONT_NAME
    p1.font.size = Pt(18)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(4)
    
    p2 = tf.add_paragraph()
    p2.text = sub
    p2.font.name = FONT_NAME
    p2.font.size = Pt(12)
    p2.font.italic = True
    p2.font.color.rgb = TEXT_PURPLE
    p2.space_after = Pt(14)
    
    p3 = tf.add_paragraph()
    p3.text = desc
    p3.font.name = FONT_NAME
    p3.font.size = Pt(11)
    p3.font.color.rgb = TEXT_BODY

add_footer(slide2, 2)

# -------------------------------------------------------------
# SLIDE 3: The Design Thinking Framework Applied to Dayleaf
# -------------------------------------------------------------
slide3 = prs.slides.add_slide(blank_layout)
set_slide_background(slide3)
add_header(slide3, "DESIGN THINKING METHODOLOGY", "How the 5 Stages of Design Thinking Built Dayleaf", "A human-centric engineering journey from raw user frustration to autonomous AI scheduling.")

stages = [
    ("1. EMPATHIZE", "Interviewed administrators, teachers & students about daily timetable headaches.", CYAN_ACCENT),
    ("2. DEFINE", "Formulated the core challenge: Zero-clash automation with human oversight & transparency.", CARD_ACCENT),
    ("3. IDEATE", "Engineered a dual constraint satisfaction engine combined with Gemini Generative AI.", GREEN_ACCENT),
    ("4. PROTOTYPE", "Built Dayleaf Studio — dark neon Obsidian UI with live timetable visualizer & studio.", ORANGE_ACCENT),
    ("5. TEST", "Validated with 66 timetable slots, 4 departments, 15 labs & 50 automated tests.", TEXT_PURPLE),
]

for idx, (stage_name, stage_desc, accent) in enumerate(stages):
    x = Inches(0.8) + idx * Inches(2.38)
    y = Inches(2.0)
    w = Inches(2.2)
    h = Inches(4.5)
    
    add_card(slide3, x, y, w, h, border_color=accent)
    
    tb = slide3.shapes.add_textbox(x + Inches(0.18), y + Inches(0.3), w - Inches(0.36), h - Inches(0.6))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = f"STAGE 0{idx+1}"
    p0.font.name = FONT_NAME
    p0.font.size = Pt(9.5)
    p0.font.bold = True
    p0.font.color.rgb = accent
    p0.space_after = Pt(6)
    
    p1 = tf.add_paragraph()
    p1.text = stage_name
    p1.font.name = FONT_NAME
    p1.font.size = Pt(15)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(12)
    
    p2 = tf.add_paragraph()
    p2.text = stage_desc
    p2.font.name = FONT_NAME
    p2.font.size = Pt(10.5)
    p2.font.color.rgb = TEXT_BODY

add_footer(slide3, 3)

# -------------------------------------------------------------
# SLIDE 4: Stage 1 & 2: Empathize & Define (User Personas)
# -------------------------------------------------------------
slide4 = prs.slides.add_slide(blank_layout)
set_slide_background(slide4)
add_header(slide4, "STAGE 1 & 2: EMPATHIZE & DEFINE", "Stakeholder Personas & Problem Framing", "Mapping needs and frustrations across the 4 key roles on campus.")

personas = [
    ("College Admin / Dean", "Needs campus-wide oversight, accreditation compliance, and instant conflict alerts.", "Pain: Spends 3 weeks every semester manually fixing clash reports on Excel.", CYAN_ACCENT),
    ("Department HOD", "Needs department-specific scheduling, faculty workload balance, and lab allocations.", "Pain: Inability to coordinate with other departments sharing common computer labs.", CARD_ACCENT),
    ("Faculty Member", "Needs continuous teaching blocks, research time, and advance notice of venue changes.", "Pain: 8:00 AM class followed by 4:00 PM class with 7 unproductive gap hours.", GREEN_ACCENT),
    ("B.Tech Student", "Needs clear clash-free weekly schedule, lab allocations, and mobile access to updates.", "Pain: Arrives at class only to find lab locked or double-booked with seniors.", ORANGE_ACCENT),
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
    
    p0 = tf.paragraphs[0]
    p0.text = role
    p0.font.name = FONT_NAME
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = TEXT_WHITE
    p0.space_after = Pt(4)
    
    p1 = tf.add_paragraph()
    p1.text = f"• NEED: {need}"
    p1.font.name = FONT_NAME
    p1.font.size = Pt(10.5)
    p1.font.color.rgb = TEXT_PURPLE
    p1.space_after = Pt(4)
    
    p2 = tf.add_paragraph()
    p2.text = f"• FRUSTRATION: {pain}"
    p2.font.name = FONT_NAME
    p2.font.size = Pt(10)
    p2.font.color.rgb = TEXT_BODY

add_footer(slide4, 4)

# -------------------------------------------------------------
# SLIDE 5: Stage 3: Ideate & Architecture (Constraint Engine + Gemini AI)
# -------------------------------------------------------------
slide5 = prs.slides.add_slide(blank_layout)
set_slide_background(slide5)
add_header(slide5, "STAGE 3: IDEATE", "The Dayleaf Solution: Dual-Core Intelligence Architecture", "Combining mathematical constraint satisfaction algorithms with Google Gemini Large Language Models.")

# Left Card: Hard Constraints vs Soft Constraints
add_card(slide5, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.8), border_color=CARD_ACCENT)
tb_left = slide5.shapes.add_textbox(Inches(1.05), Inches(2.05), Inches(5.2), Inches(4.3))
tfl = tb_left.text_frame
tfl.word_wrap = True

p = tfl.paragraphs[0]
p.text = "Mathematical Constraint Engine"
p.font.name = FONT_NAME
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(8)

p = tfl.add_paragraph()
p.text = "HARD CONSTRAINTS (Zero Tolerance — Mandatory):"
p.font.name = FONT_NAME
p.font.size = Pt(11)
p.font.bold = True
p.font.color.rgb = CYAN_ACCENT
p.space_after = Pt(4)

hard_items = [
    "No Room Double-Booking: One room can host exactly 1 class per time slot.",
    "No Faculty Collision: A professor cannot be assigned to two places at once.",
    "Section Non-Overlap: Students in a section cannot have simultaneous classes.",
    "Capacity Match: Room capacity must be >= section enrollment size.",
    "Lab Equipment Match: Hands-on subjects only scheduled in designated labs."
]
for item in hard_items:
    pi = tfl.add_paragraph()
    pi.text = f"✔ {item}"
    pi.font.name = FONT_NAME
    pi.font.size = Pt(10)
    pi.font.color.rgb = TEXT_BODY
    pi.space_after = Pt(2)

p_soft = tfl.add_paragraph()
p_soft.text = "\nSOFT CONSTRAINTS (Optimized via Scoring Penalties):"
p_soft.font.name = FONT_NAME
p_soft.font.size = Pt(11)
p_soft.font.bold = True
p_soft.font.color.rgb = GREEN_ACCENT
p_soft.space_after = Pt(4)

soft_items = [
    "Even Daily Workload Distribution (Max 4 lectures/day per faculty).",
    "Minimizing Student Idle Gaps between lectures.",
    "Preferred Faculty Availability windows respected."
]
for item in soft_items:
    pi = tfl.add_paragraph()
    pi.text = f"★ {item}"
    pi.font.name = FONT_NAME
    pi.font.size = Pt(10)
    pi.font.color.rgb = TEXT_BODY
    pi.space_after = Pt(2)

# Right Card: Gemini AI Integration
add_card(slide5, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), border_color=CYAN_ACCENT)
tb_right = slide5.shapes.add_textbox(Inches(7.05), Inches(2.05), Inches(5.2), Inches(4.3))
tfr = tb_right.text_frame
tfr.word_wrap = True

p = tfr.paragraphs[0]
p.text = "Gemini LLM Natural Language Co-Pilot"
p.font.name = FONT_NAME
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(8)

gemini_points = [
    ("Multi-Model Fallback Pipeline", "Engineered resilient failover: Gemini-1.5-Flash → Gemini-2.0-Flash → Gemini-Flash-Latest with strict 8-second circuit breakers."),
    ("Natural Language Scheduling Queries", "Administrators ask: 'Find a free lab on Wednesday afternoon' or 'Which teachers have heavy workload?' and get instant structured answers."),
    ("Hard Constraint Enforcement Layer", "LLM suggestions never bypass database integrity; AI drafts must pass the exact same constraint validator before publication."),
    ("Context-Aware Campus Intelligence", "Assistant understands department codes (CSE, CYS, DS, ECE), academic terms, and room capacity limits in real time.")
]

for title, desc in gemini_points:
    pt = tfr.add_paragraph()
    pt.text = f"▶ {title}"
    pt.font.name = FONT_NAME
    pt.font.size = Pt(11.5)
    pt.font.bold = True
    pt.font.color.rgb = CARD_ACCENT
    pt.space_after = Pt(2)
    
    pd = tfr.add_paragraph()
    pd.text = desc
    pd.font.name = FONT_NAME
    pd.font.size = Pt(10)
    pd.font.color.rgb = TEXT_BODY
    pd.space_after = Pt(6)

add_footer(slide5, 5)

# -------------------------------------------------------------
# SLIDE 6: Stage 4: Prototype — Live Studio UI (Screenshot 1)
# -------------------------------------------------------------
slide6 = prs.slides.add_slide(blank_layout)
set_slide_background(slide6)
add_header(slide6, "STAGE 4: PROTOTYPE & IMPLEMENTATION", "Dayleaf Studio: Premium Obsidian & Violet UI", "Dark mode aesthetic engineered for high contrast, focus, and modern campus intelligence.")

# Left Screenshot
ws_ss = r"screenshots\workspace_full.png"
if os.path.exists(ws_ss):
    add_card(slide6, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.8), border_color=CARD_ACCENT)
    slide6.shapes.add_picture(ws_ss, Inches(0.85), Inches(1.85), width=Inches(6.7))

# Right explanation card
add_card(slide6, Inches(7.8), Inches(1.8), Inches(4.7), Inches(4.8), border_color=CARD_BORDER)
tb_expl = slide6.shapes.add_textbox(Inches(8.05), Inches(2.05), Inches(4.2), Inches(4.3))
tfe = tb_expl.text_frame
tfe.word_wrap = True

pe0 = tfe.paragraphs[0]
pe0.text = "Design System Highlights"
pe0.font.name = FONT_NAME
pe0.font.size = Pt(18)
pe0.font.bold = True
pe0.font.color.rgb = TEXT_WHITE
pe0.space_after = Pt(10)

ui_features = [
    ("Obsidian & Violet Palette", "Deep #0B0813 background prevents eye strain during long timetable scheduling sessions."),
    ("Glassmorphism Components", "Subtle semi-transparent cards with neon borders provide clear visual hierarchy."),
    ("Multi-Role Navigation", "Customized workspaces for College Admin, HOD, Faculty, and Students based on active session."),
    ("Live Campus Status Badge", "Displays active term (Fall 2026-27) and real-time operational status dots.")
]

for h_txt, b_txt in ui_features:
    p_h = tfe.add_paragraph()
    p_h.text = f"✦ {h_txt}"
    p_h.font.name = FONT_NAME
    p_h.font.size = Pt(11)
    p_h.font.bold = True
    p_h.font.color.rgb = CYAN_ACCENT
    p_h.space_after = Pt(2)
    
    p_b = tfe.add_paragraph()
    p_b.text = b_txt
    p_b.font.name = FONT_NAME
    p_b.font.size = Pt(10)
    p_b.font.color.rgb = TEXT_BODY
    p_b.space_after = Pt(8)

add_footer(slide6, 6)

# -------------------------------------------------------------
# SLIDE 7: Module 1: Timetable Planner & Constraint Optimizer (Screenshot 2)
# -------------------------------------------------------------
slide7 = prs.slides.add_slide(blank_layout)
set_slide_background(slide7)
add_header(slide7, "CORE WORKSPACE 01", "Automated Timetable Optimizer & Visualizer", "Instant draft generation, conflict scoring, and published schedule management.")

tt_ss = r"screenshots\timetable_full.png"
if os.path.exists(tt_ss):
    add_card(slide7, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.8), border_color=CARD_ACCENT)
    slide7.shapes.add_picture(tt_ss, Inches(0.85), Inches(1.85), width=Inches(6.7))

add_card(slide7, Inches(7.8), Inches(1.8), Inches(4.7), Inches(4.8), border_color=CARD_BORDER)
tb_tt = slide7.shapes.add_textbox(Inches(8.05), Inches(2.05), Inches(4.2), Inches(4.3))
tft = tb_tt.text_frame
tft.word_wrap = True

pt0 = tft.paragraphs[0]
pt0.text = "Planner Engine Features"
pt0.font.name = FONT_NAME
pt0.font.size = Pt(18)
pt0.font.bold = True
pt0.font.color.rgb = TEXT_WHITE
pt0.space_after = Pt(10)

planner_points = [
    ("One-Click Draft Optimizer", "Analyzes all weekly teaching assignments and generates conflict-free schedules in sub-seconds."),
    ("Granular Filtering", "Instant filter by Academic Term, Department (CSE/CYS/DS/ECE), and Semester Sections."),
    ("Conflict Soft-Score Gauge", "Calculates soft penalty score (workload balance, gaps) where lower score indicates superior timetable."),
    ("Review & Publish Workflow", "Drafts are reviewed by HODs before publishing live to faculty and student portals.")
]

for h_txt, b_txt in planner_points:
    p_h = tft.add_paragraph()
    p_h.text = f"✔ {h_txt}"
    p_h.font.name = FONT_NAME
    p_h.font.size = Pt(11)
    p_h.font.bold = True
    p_h.font.color.rgb = GREEN_ACCENT
    p_h.space_after = Pt(2)
    
    p_b = tft.add_paragraph()
    p_b.text = b_txt
    p_b.font.name = FONT_NAME
    p_b.font.size = Pt(10)
    p_b.font.color.rgb = TEXT_BODY
    p_b.space_after = Pt(8)

add_footer(slide7, 7)

# -------------------------------------------------------------
# SLIDE 8: Module 2: Academic Hierarchy & Structure
# -------------------------------------------------------------
slide8 = prs.slides.add_slide(blank_layout)
set_slide_background(slide8)
add_header(slide8, "CORE WORKSPACE 02", "Academic Structure & Department Hierarchy", "Structured entity relationships ensuring seamless multi-department coordination.")

cards_s8 = [
    ("4 Core Departments", "CSE, Cybersecurity, Data Science & AI, and ECE. Each department manages its own subjects, course codes, and semester syllabus requirements.", CYAN_ACCENT),
    ("2 Active Terms", "Fall Semester 2026-27 (Current active term) and Spring Semester 2026-27. Enables semester rollover and historical schedule archiving.", CARD_ACCENT),
    ("10 Sections Across Semesters", "Semesters 3 & 5 broken into Section A, B, and C batches, enabling parallel lab scheduling without conflict.", GREEN_ACCENT),
    ("18 Accredited Subjects", "Theory courses (3-4 credits) and Intensive Lab sessions (2 hours) with pre-requisite venue requirements.", ORANGE_ACCENT)
]

for idx, (title, desc, accent) in enumerate(cards_s8):
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
    
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = FONT_NAME
    p0.font.size = Pt(16)
    p0.font.bold = True
    p0.font.color.rgb = TEXT_WHITE
    p0.space_after = Pt(6)
    
    p1 = tf.add_paragraph()
    p1.text = desc
    p1.font.name = FONT_NAME
    p1.font.size = Pt(11)
    p1.font.color.rgb = TEXT_BODY

add_footer(slide8, 8)

# -------------------------------------------------------------
# SLIDE 9: Module 3: Classrooms & Smart Labs
# -------------------------------------------------------------
slide9 = prs.slides.add_slide(blank_layout)
set_slide_background(slide9)
add_header(slide9, "CORE WORKSPACE 03", "Smart Classrooms & Specialized Labs", "15 venues cataloged with precision capacity limits and hardware capabilities.")

rooms_categories = [
    ("High-Tech Specialized Labs (Capacity: 75)", 
     ["• AI & Deep Learning Lab (Equipped with GPU clusters)",
      "• Big Data Analytics Lab (High RAM distributed setups)",
      "• Cloud & Networks Lab (Cisco packet tracer / virtualization)",
      "• Cybersecurity & Forensics Lab (Air-gapped penetration testing)",
      "• Electronics & IoT Hardware Lab (Embedded systems & oscilloscopes)"],
     CARD_ACCENT),
    ("Smart Lecture Theatres & Auditoriums (Capacity: 70 - 250)", 
     ["• Audi-1 (Main Campus Auditorium — 250 seats)",
      "• Audi-2 (Seminar Hall A — 120 seats)",
      "• LH-101, LH-102, LH-103 (Multimedia Lecture Halls — 70 seats)",
      "• LH-201, LH-202, LH-203, LH-204 (Interactive Audio-Visual Halls — 70 seats)",
      "• Seminar Hall B (Interactive Workshop Room — 60 seats)"],
     CYAN_ACCENT)
]

for idx, (title, items, accent) in enumerate(rooms_categories):
    x = Inches(0.8) + idx * Inches(5.95)
    y = Inches(1.8)
    w = Inches(5.7)
    h = Inches(4.8)
    
    add_card(slide9, x, y, w, h, border_color=accent)
    
    tb = slide9.shapes.add_textbox(x + Inches(0.25), y + Inches(0.25), w - Inches(0.5), h - Inches(0.5))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = FONT_NAME
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = TEXT_WHITE
    p0.space_after = Pt(12)
    
    for item in items:
        pi = tf.add_paragraph()
        pi.text = item
        pi.font.name = FONT_NAME
        pi.font.size = Pt(11)
        pi.font.color.rgb = TEXT_BODY
        pi.space_after = Pt(8)

add_footer(slide9, 9)

# -------------------------------------------------------------
# SLIDE 10: Module 4: People & Faculty Workload Management
# -------------------------------------------------------------
slide10 = prs.slides.add_slide(blank_layout)
set_slide_background(slide10)
add_header(slide10, "CORE WORKSPACE 04", "Faculty Workload Balancing & Student Access", "Preventing academic burnout while providing personalized schedules.")

add_card(slide10, Inches(0.8), Inches(1.8), Inches(5.7), Inches(4.8), border_color=CARD_ACCENT)
tb10_left = slide10.shapes.add_textbox(Inches(1.05), Inches(2.05), Inches(5.2), Inches(4.3))
tfl10 = tb10_left.text_frame
tfl10.word_wrap = True

p = tfl10.paragraphs[0]
p.text = "Faculty Workload & Availability"
p.font.name = FONT_NAME
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(8)

fac_items = [
    ("Weekly Teaching Load Caps", "Strict limits on teaching hours (e.g. max 16 hours/week) prevent educator fatigue."),
    ("Availability Matrix", "Faculty can configure unavailable time blocks for research, meetings, or PhD supervision."),
    ("Consecutive Lecture Limits", "No professor is assigned more than 2 back-to-back lectures without a break."),
    ("HOD Department Delegation", "HODs oversee their faculty roster: Dr. Kavya Iyer, Prof. Arjun Menon, Dr. Rohan Shah.")
]

for title, desc in fac_items:
    pt = tfl10.add_paragraph()
    pt.text = f"▶ {title}"
    pt.font.name = FONT_NAME
    pt.font.size = Pt(11.5)
    pt.font.bold = True
    pt.font.color.rgb = CYAN_ACCENT
    pt.space_after = Pt(2)
    
    pd = tfl10.add_paragraph()
    pd.text = desc
    pd.font.name = FONT_NAME
    pd.font.size = Pt(10)
    pd.font.color.rgb = TEXT_BODY
    pd.space_after = Pt(6)

add_card(slide10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(4.8), border_color=GREEN_ACCENT)
tb10_right = slide10.shapes.add_textbox(Inches(7.05), Inches(2.05), Inches(5.2), Inches(4.3))
tfr10 = tb10_right.text_frame
tfr10.word_wrap = True

p = tfr10.paragraphs[0]
p.text = "Student Portal & Personalized Timetables"
p.font.name = FONT_NAME
p.font.size = Pt(18)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(8)

stu_items = [
    ("Individualized Student Views", "Students log in to see their specific section schedule without having to parse master sheets."),
    ("Elective Class Alignment", "Cross-departmental electives automatically scheduled in non-clashing time slots."),
    ("Real-Time Change Alerts", "Immediate notifications whenever an instructor reschedules a class or swaps a venue."),
    ("Active Student Roster", "Seeded with verified student profiles (Aarav Sharma, Diya Patel, Kabir Singh, etc.).")
]

for title, desc in stu_items:
    pt = tfr10.add_paragraph()
    pt.text = f"★ {title}"
    pt.font.name = FONT_NAME
    pt.font.size = Pt(11.5)
    pt.font.bold = True
    pt.font.color.rgb = GREEN_ACCENT
    pt.space_after = Pt(2)
    
    pd = tfr10.add_paragraph()
    pd.text = desc
    pd.font.name = FONT_NAME
    pd.font.size = Pt(10)
    pd.font.color.rgb = TEXT_BODY
    pd.space_after = Pt(6)

add_footer(slide10, 10)

# -------------------------------------------------------------
# SLIDE 11: Cyber Security & Access Control (Department Focus)
# -------------------------------------------------------------
slide11 = prs.slides.add_slide(blank_layout)
set_slide_background(slide11)
add_header(slide11, "CYBER SECURITY ARCHITECTURE", "Enterprise Security & Threat Mitigation", "Engineered with defensive security controls tailored for university integrity.")

sec_cards = [
    ("Role-Based Access Control (RBAC)", 
     "Hierarchical 5-tier permission model:\n• Super Admin (System maintenance)\n• College Admin (Full campus config)\n• HOD (Department records & approval)\n• Faculty (View schedule, set availability)\n• Student (Read-only personal timetable)\nStrict route-level dependency guards.", 
     CARD_ACCENT),
    ("Session & Cookie Hardening", 
     "• HTTP-only session cookies mitigate XSS token theft.\n• SameSite=Lax protection against CSRF.\n• Dynamic Origin Validation allowing only authorized campus hosts.\n• Automatic token rotation & revocation family trees.", 
     CYAN_ACCENT),
    ("CSRF Double-Submit HMAC Protection", 
     "All state-mutating requests (POST, PUT, DELETE) require a cryptographically signed X-CSRF-Token header matching the cookie hash with constant-time HMAC comparison.", 
     GREEN_ACCENT),
    ("Tamper-Proof Audit Logging", 
     "Every single timetable modification, venue swap, and faculty reassignment is permanently logged with Actor ID, IP origin, previous value, new value, and ISO timestamp.", 
     ORANGE_ACCENT)
]

for idx, (title, desc, accent) in enumerate(sec_cards):
    r = idx // 2
    c = idx % 2
    x = Inches(0.8) + c * Inches(5.95)
    y = Inches(1.8) + r * Inches(2.5)
    w = Inches(5.7)
    h = Inches(2.25)
    
    add_card(slide11, x, y, w, h, border_color=accent)
    
    tb = slide11.shapes.add_textbox(x + Inches(0.25), y + Inches(0.2), w - Inches(0.5), h - Inches(0.4))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = FONT_NAME
    p0.font.size = Pt(14)
    p0.font.bold = True
    p0.font.color.rgb = TEXT_WHITE
    p0.space_after = Pt(4)
    
    p1 = tf.add_paragraph()
    p1.text = desc
    p1.font.name = FONT_NAME
    p1.font.size = Pt(9.5)
    p1.font.color.rgb = TEXT_BODY

add_footer(slide11, 11)

# -------------------------------------------------------------
# SLIDE 12: Dayleaf AI Assistant (Conversational Co-Pilot)
# -------------------------------------------------------------
slide12 = prs.slides.add_slide(blank_layout)
set_slide_background(slide12)
add_header(slide12, "AI CAPABILITIES", "Dayleaf AI: Natural Language Campus Intelligence", "Empowering users to chat with their campus database in plain English.")

add_card(slide12, Inches(0.8), Inches(1.8), Inches(11.7), Inches(4.8), border_color=CARD_ACCENT)
tb12 = slide12.shapes.add_textbox(Inches(1.1), Inches(2.05), Inches(11.1), Inches(4.3))
tf12 = tb12.text_frame
tf12.word_wrap = True

p = tf12.paragraphs[0]
p.text = "Interactive Campus Intelligence Dialogues"
p.font.name = FONT_NAME
p.font.size = Pt(20)
p.font.bold = True
p.font.color.rgb = TEXT_WHITE
p.space_after = Pt(10)

ai_examples = [
    ("Query: 'Find a free lab on Wednesday afternoon for CSE-3A'",
     "Dayleaf AI queries room allocation records, cross-references timetable entries, and responds: 'Cloud & Networks Lab is available Wednesday 2:00 PM - 4:00 PM with 75 seats capacity.'"),
    ("Query: 'Which faculty members have more than 14 teaching hours this week?'",
     "The assistant analyzes weekly teaching assignments across all 4 departments and provides a clean breakdown with recommended load reallocations."),
    ("Query: 'Propose a conflict-free draft for Cybersecurity Semester 5'",
     "The assistant invokes the backend constraint satisfaction solver and generates a new draft timetable ready for HOD review.")
]

for q, a in ai_examples:
    p_q = tf12.add_paragraph()
    p_q.text = f"💬 USER {q}"
    p_q.font.name = FONT_NAME
    p_q.font.size = Pt(12)
    p_q.font.bold = True
    p_q.font.color.rgb = CYAN_ACCENT
    p_q.space_after = Pt(2)
    
    p_a = tf12.add_paragraph()
    p_a.text = f"🤖 DAYLEAF AI: {a}"
    p_a.font.name = FONT_NAME
    p_a.font.size = Pt(10.5)
    p_a.font.color.rgb = TEXT_BODY
    p_a.space_after = Pt(10)

add_footer(slide12, 12)

# -------------------------------------------------------------
# SLIDE 13: Stage 5: Testing & Real-World Validation
# -------------------------------------------------------------
slide13 = prs.slides.add_slide(blank_layout)
set_slide_background(slide13)
add_header(slide13, "STAGE 5: TESTING & METRICS", "Rigorous Verification & Benchmark Results", "Validated with a production-scale simulated campus and 100% automated test coverage.")

test_metrics = [
    ("50 / 50 Tests Passing", "100% backend test suite verification covering authentication, RBAC, timetable solver, and CORS.", GREEN_ACCENT),
    ("Sub-Second Scheduling", "Constraint optimizer solves 66 weekly slots across 4 departments in under 850 milliseconds.", CYAN_ACCENT),
    ("Zero Room Clashes", "Formally verified that no classroom or specialized lab had dual bookings across all active terms.", CARD_ACCENT),
    ("Production-Ready Data", "4 Departments, 15 Classrooms/Labs, 11 Faculty, 10 Students, 18 Subjects, and 23 Assignments.", ORANGE_ACCENT)
]

for idx, (title, desc, accent) in enumerate(test_metrics):
    x = Inches(0.8) + idx * Inches(2.95)
    y = Inches(1.8)
    w = Inches(2.75)
    h = Inches(4.8)
    
    add_card(slide13, x, y, w, h, border_color=accent)
    
    tb = slide13.shapes.add_textbox(x + Inches(0.2), y + Inches(0.3), w - Inches(0.4), h - Inches(0.6))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = f"METRIC 0{idx+1}"
    p0.font.name = FONT_NAME
    p0.font.size = Pt(9.5)
    p0.font.bold = True
    p0.font.color.rgb = accent
    p0.space_after = Pt(8)
    
    p1 = tf.add_paragraph()
    p1.text = title
    p1.font.name = FONT_NAME
    p1.font.size = Pt(17)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.space_after = Pt(10)
    
    p2 = tf.add_paragraph()
    p2.text = desc
    p2.font.name = FONT_NAME
    p2.font.size = Pt(11)
    p2.font.color.rgb = TEXT_BODY

add_footer(slide13, 13)

# -------------------------------------------------------------
# SLIDE 14: Future Roadmap & Scalability
# -------------------------------------------------------------
slide14 = prs.slides.add_slide(blank_layout)
set_slide_background(slide14)
add_header(slide14, "FUTURE ROADMAP", "Next-Phase Innovations & Scalability", "Expanding Dayleaf from single-campus intelligence to an autonomous university ecosystem.")

roadmap_phases = [
    ("Phase 2: Mobile Apps & Push Alerts", "Dedicated iOS and Android apps with instantaneous schedule push notifications, cancellation alerts, and room change directions.", CYAN_ACCENT),
    ("Phase 3: Biometric & IoT Sync", "Integrating with RFID / Biometric smart attendance systems to dynamically detect empty classrooms and release unused reservations.", CARD_ACCENT),
    ("Phase 4: Autonomous Substitution", "When a professor marks unexpected leave, AI automatically locates available substitute faculty with matching subject domain expertise.", GREEN_ACCENT),
    ("Phase 5: Multi-Campus Cloud Federation", "Multi-tenant architecture allowing university networks with 10+ campuses to share inter-branch guest lecturers and online hubs.", ORANGE_ACCENT)
]

for idx, (title, desc, accent) in enumerate(roadmap_phases):
    r = idx // 2
    c = idx % 2
    x = Inches(0.8) + c * Inches(5.95)
    y = Inches(1.8) + r * Inches(2.5)
    w = Inches(5.7)
    h = Inches(2.25)
    
    add_card(slide14, x, y, w, h, border_color=accent)
    
    tb = slide14.shapes.add_textbox(x + Inches(0.25), y + Inches(0.25), w - Inches(0.5), h - Inches(0.5))
    tf = tb.text_frame
    tf.word_wrap = True
    
    p0 = tf.paragraphs[0]
    p0.text = title
    p0.font.name = FONT_NAME
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = TEXT_WHITE
    p0.space_after = Pt(6)
    
    p1 = tf.add_paragraph()
    p1.text = desc
    p1.font.name = FONT_NAME
    p1.font.size = Pt(10.5)
    p1.font.color.rgb = TEXT_BODY

add_footer(slide14, 14)

# -------------------------------------------------------------
# SLIDE 15: Conclusion & Acknowledgments
# -------------------------------------------------------------
slide15 = prs.slides.add_slide(blank_layout)
set_slide_background(slide15)

# Big Centered Card
add_card(slide15, Inches(1.5), Inches(1.2), Inches(10.33), Inches(5.1), border_color=CARD_ACCENT)
if os.path.exists(r"screenshots\wave_violet.png"):
    slide15.shapes.add_picture(r"screenshots\wave_violet.png", Inches(5.2), Inches(1.4), width=Inches(2.9))
tb15 = slide15.shapes.add_textbox(Inches(1.8), Inches(2.2), Inches(9.7), Inches(3.9))
tf15 = tb15.text_frame
tf15.word_wrap = True

p_badge = tf15.paragraphs[0]
p_badge.text = "DESIGN AND THINKING  •  PROJECT CONCLUSION"
p_badge.font.name = FONT_NAME
p_badge.font.size = Pt(12)
p_badge.font.bold = True
p_badge.font.color.rgb = CYAN_ACCENT
p_badge.alignment = PP_ALIGN.CENTER
p_badge.space_after = Pt(10)

p_main = tf15.add_paragraph()
p_main.text = "Dayleaf: Transforming University Timetabling"
p_main.font.name = FONT_NAME
p_main.font.size = Pt(30)
p_main.font.bold = True
p_main.font.color.rgb = TEXT_WHITE
p_main.alignment = PP_ALIGN.CENTER
p_main.space_after = Pt(14)

p_summary = tf15.add_paragraph()
p_summary.text = "Through human-centered Design Thinking, Dayleaf replaces weeks of painful manual timetable scheduling with an automated, conflict-free, and intelligent platform. By bridging mathematical constraint satisfaction with Gemini AI, university operations become faster, fairer, and future-ready."
p_summary.font.name = FONT_NAME
p_summary.font.size = Pt(12)
p_summary.font.color.rgb = TEXT_BODY
p_summary.alignment = PP_ALIGN.CENTER
p_summary.space_after = Pt(20)

p_team = tf15.add_paragraph()
p_team.text = "Presented by B.Tech CSE (Cyber Security) Team:"
p_team.font.name = FONT_NAME
p_team.font.size = Pt(11.5)
p_team.font.bold = True
p_team.font.color.rgb = CARD_ACCENT
p_team.alignment = PP_ALIGN.CENTER
p_team.space_after = Pt(6)

p_names = tf15.add_paragraph()
p_names.text = "Rudraksh Chadha (25BTRCC045)  •  Sakthivel M (25BTRCC048)  •  Sushant Prakash (25BTRCC053)\nSudhanshu Kumar (25BTRCC052)  •  Hrishit Chaudhary (25BTRCC025)  •  Mohamed Badreldin (25BTRCC061)"
p_names.font.name = FONT_NAME
p_names.font.size = Pt(11)
p_names.font.color.rgb = TEXT_PURPLE
p_names.alignment = PP_ALIGN.CENTER
p_names.space_after = Pt(14)

p_qa = tf15.add_paragraph()
p_qa.text = "Thank You! Questions & Discussion Welcome."
p_qa.font.name = FONT_NAME
p_qa.font.size = Pt(15)
p_qa.font.bold = True
p_qa.font.color.rgb = GREEN_ACCENT
p_qa.alignment = PP_ALIGN.CENTER

add_footer(slide15, 15)

# Save
output_path = "Dayleaf_AI_Campus_Timetable_Presentation.pptx"
prs.save(output_path)
print(f"Presentation successfully saved to: {os.path.abspath(output_path)}")
