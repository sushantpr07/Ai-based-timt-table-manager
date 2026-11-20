"""Captures real screenshots of every Dayleaf section using installed Chrome."""
import os, time
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3010"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")
os.makedirs(OUT, exist_ok=True)

def shot(page, name, full=False):
    time.sleep(1.2)
    page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=full)
    print("saved", name)

def nav(page, label):
    page.locator(f"nav.side-nav button[aria-label='{label}']").first.click()
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)

def login(page, email, password="Dayleaf@2026"):
    page.goto(f"{BASE}/sign-in"); page.wait_for_load_state("networkidle")
    page.fill("input[name=email]", email); page.fill("input[name=password]", password)
    page.click("button.auth-submit")
    page.wait_for_url(f"{BASE}/", timeout=20000); page.wait_for_load_state("networkidle"); time.sleep(2)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1.5)
    page = ctx.new_page()

    # Public pages
    page.goto(BASE); page.wait_for_load_state("networkidle")
    shot(page, "01_landing")
    shot(page, "01b_landing_full", full=True)
    page.goto(f"{BASE}/sign-in"); page.wait_for_load_state("networkidle")
    shot(page, "02_signin")

    # Admin
    login(page, "sushantprakash2003@gmail.com")
    shot(page, "03_dashboard")
    nav(page, "Timetable")
    selects = page.locator("select")
    try:
        selects.nth(0).select_option(index=1)
        time.sleep(0.8)
        selects.nth(1).select_option(index=1)
        page.wait_for_load_state("networkidle"); time.sleep(2.5)
    except Exception as e:
        print("select err", e)
    shot(page, "04_timetable")
    shot(page, "04b_timetable_full", full=True)
    # scroll to schedule grid
    grid = page.locator(".timetable-grid, .schedule-grid, table").first
    try:
        grid.scroll_into_view_if_needed(); shot(page, "04c_timetable_grid")
    except Exception as e:
        print("grid err", e)

    nav(page, "AI planner"); shot(page, "05_ai_planner")
    nav(page, "Academics"); shot(page, "06_academics")
    tabs = page.locator(".resource-tabs button")
    for i in range(min(tabs.count(), 6)):
        t = tabs.nth(i); label = t.inner_text().strip().lower().replace(" ", "_")[:20]
        t.click(); page.wait_for_load_state("networkidle"); shot(page, f"06_{i}_{label}")
    nav(page, "Classrooms"); shot(page, "07_classrooms")
    nav(page, "People"); shot(page, "08_people")
    tabs = page.locator(".resource-tabs button")
    for i in range(min(tabs.count(), 4)):
        t = tabs.nth(i); label = t.inner_text().strip().lower().replace(" ", "_")[:20]
        t.click(); page.wait_for_load_state("networkidle"); shot(page, f"08_{i}_{label}")
    nav(page, "Analytics"); shot(page, "09_analytics")
    nav(page, "Audit log"); shot(page, "10_audit")
    nav(page, "Settings"); shot(page, "11_settings")

    # Student view
    ctx2 = browser.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1.5)
    sp = ctx2.new_page()
    try:
        login(sp, "aarav.sharma@dayleaf.edu"); shot(sp, "12_student_overview")
        nav(sp, "My timetable"); shot(sp, "13_student_timetable")
    except Exception as e:
        print("student err", e)
    # Faculty view
    ctx3 = browser.new_context(viewport={"width": 1600, "height": 900}, device_scale_factor=1.5)
    fp = ctx3.new_page()
    try:
        login(fp, "arjun.menon@dayleaf.edu"); shot(fp, "14_faculty_overview")
        nav(fp, "My timetable"); shot(fp, "15_faculty_timetable")
    except Exception as e:
        print("faculty err", e)
    browser.close()
