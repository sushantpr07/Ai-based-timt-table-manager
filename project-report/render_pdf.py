import os, shutil
from playwright.sync_api import sync_playwright
from pptx import Presentation
from pptx.util import Inches

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
url = "file:///" + os.path.join(HERE, "index.html").replace("\\", "/")
preview_dir = os.path.join(HERE, "preview")
os.makedirs(preview_dir, exist_ok=True)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    ctx = b.new_context(viewport={"width": 1123, "height": 794}, device_scale_factor=2)
    pg = ctx.new_page()
    pg.goto(url)
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(1500)

    pdf_path = os.path.join(HERE, "Dayleaf_Project_Report.pdf")
    pg.pdf(
        path=pdf_path,
        landscape=True,
        format="A4",
        print_background=True,
        prefer_css_page_size=True,
    )
    shutil.copy2(pdf_path, os.path.join(ROOT, "Dayleaf_Project_Report.pdf"))

    pg.emulate_media(media="print")
    pages = pg.locator("section.page")
    n = pages.count()
    slide_imgs = []
    for i in range(n):
        img_path = os.path.join(preview_dir, f"p{i+1:02d}.png")
        pages.nth(i).screenshot(path=img_path)
        slide_imgs.append(img_path)

    over = pg.evaluate(
        """() => [...document.querySelectorAll('section.page')].map((s,i)=>{
        const c = s.querySelector('.content') || s;
        return {i:i+1, over: c.scrollHeight - c.clientHeight}
    }).filter(x=>x.over>2)"""
    )
    print("Pages:", n, "Overflow:", over)
    b.close()

# Build 18-slide A4-landscape PPTX from the high-res rendered pages
prs = Presentation()
prs.slide_width = Inches(11.693)   # A4 landscape width (297mm)
prs.slide_height = Inches(8.268)   # A4 landscape height (210mm)
blank = prs.slide_layouts[6]

for img_path in slide_imgs:
    sl = prs.slides.add_slide(blank)
    sl.shapes.add_picture(img_path, Inches(0), Inches(0), width=prs.slide_width, height=prs.slide_height)

pptx_out = os.path.join(ROOT, "Dayleaf_Presentation_18Slides.pptx")
prs.save(pptx_out)
print("Saved PPTX:", pptx_out)

# Also copy into apps/web/public/report so it's live on http://localhost:3010/report/index.html
pub_report = os.path.join(ROOT, "apps", "web", "public", "report")
os.makedirs(os.path.join(pub_report, "img"), exist_ok=True)
shutil.copy2(os.path.join(HERE, "index.html"), os.path.join(pub_report, "index.html"))
shutil.copy2(pdf_path, os.path.join(pub_report, "Dayleaf_Project_Report.pdf"))
for fname in os.listdir(os.path.join(HERE, "img")):
    src = os.path.join(HERE, "img", fname)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(pub_report, "img", fname))
print("Published live to http://localhost:3010/report/index.html")
