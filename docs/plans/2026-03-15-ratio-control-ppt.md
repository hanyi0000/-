# Ratio Control PPT Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a competition-ready PowerPoint deck for the ratio-control lesson, with embedded images, charts, speaker notes, and presentation-ready progressive reveal slides.

**Architecture:** Use a single Python build script to generate image assets and the final `.pptx`. The script will define a reusable visual system, slide metadata, and helper functions for cards, diagrams, and notes, then render all slides deterministically into a desktop output file.

**Tech Stack:** Python, `python-pptx`, `Pillow`, `matplotlib`, PowerPoint `.pptx`

---

### Task 1: Prepare the local build environment

**Files:**
- Create: `scripts/build_ratio_control_ppt.py`
- Create: `assets/generated/.gitkeep`

**Step 1: Check whether required Python packages are available**

Run: `python -c "import pptx, PIL, matplotlib; print('ok')"`
Expected: either `ok` or an import error showing the missing dependency.

**Step 2: Install missing package(s) into the workspace environment**

Run: `python -m pip install --target D:\edge\新建文件夹\.vendor python-pptx matplotlib`
Expected: installation completes without errors.

**Step 3: Verify imports from the local dependency path**

Run: `python -c "import sys; sys.path.insert(0, r'D:\edge\新建文件夹\.vendor'); import pptx, PIL, matplotlib; print('ok')"`
Expected: `ok`

### Task 2: Implement the presentation generator

**Files:**
- Create: `scripts/build_ratio_control_ppt.py`

**Step 1: Write the slide metadata and theme constants**

Include:
- slide size, palette, font names
- common title/subtitle/card helpers
- full slide content and notes derived from the approved design

**Step 2: Implement asset rendering helpers**

Generate:
- coffee/factory split cover art
- simple process diagrams
- simulation charts
- icon-like value slides

**Step 3: Implement `.pptx` slide construction**

Include:
- cover, section, content, comparison, chart, summary, and closing slide layouts
- speaker notes for every slide
- progressive reveal slides for key moments

**Step 4: Save the output deck to the desktop**

Write to:
- `C:\Users\hanyi\Desktop\从生椰拿铁到工业安全：比值控制系统的黄金契约.pptx`

### Task 3: Run and verify the generated deck

**Files:**
- Output: `C:\Users\hanyi\Desktop\从生椰拿铁到工业安全：比值控制系统的黄金契约.pptx`

**Step 1: Execute the build script**

Run: `python scripts/build_ratio_control_ppt.py`
Expected: script reports successful asset generation and PPT export.

**Step 2: Verify the output file exists and has non-trivial size**

Run: `Get-Item "C:\Users\hanyi\Desktop\从生椰拿铁到工业安全：比值控制系统的黄金契约.pptx" | Select-Object FullName,Length,LastWriteTime`
Expected: file exists with a size clearly larger than an empty deck.

**Step 3: Smoke-check slide count**

Run: a Python snippet that opens the PPT and prints slide count
Expected: `25` or `26`

### Task 4: Final polish and handoff

**Files:**
- Modify: `scripts/build_ratio_control_ppt.py` if polish is required

**Step 1: Adjust any spacing or text overflow issues discovered during verification**

Run the build again after changes.

**Step 2: Summarize output and remaining manual optional tweaks**

Report:
- output path
- slide count
- whether optional manual animation refinement is still worth doing
