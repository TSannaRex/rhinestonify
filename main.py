from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import math

app = FastAPI()

@app.post("/api/generate")
async def generate_rhinestone_api(
    image: UploadFile = File(...),
    stone_size_mm: float = Form(...),
    target_width_mm: float = Form(...),
    spacing_mm: float = Form(...)
):
    try:
        # ── Read image ────────────────────────────────────────────────────────
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        # Read with alpha channel support (handles transparent PNGs)
        img_raw = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

        if img_raw is None:
            return {"status": "error", "error": "Could not decode image."}

        # ── Flatten to greyscale, handling transparency correctly ─────────────
        if img_raw.ndim == 2:
            # Already greyscale
            img = img_raw
        elif img_raw.shape[2] == 4:
            # RGBA: composite onto white background first, then greyscale
            alpha = img_raw[:, :, 3:4].astype(np.float32) / 255.0
            rgb   = img_raw[:, :, :3].astype(np.float32)
            white = np.ones_like(rgb) * 255.0
            composited = (rgb * alpha + white * (1 - alpha)).astype(np.uint8)
            img = cv2.cvtColor(composited, cv2.COLOR_BGR2GRAY)
        else:
            # BGR: just convert to greyscale
            img = cv2.cvtColor(img_raw, cv2.COLOR_BGR2GRAY)

        # ── Pre-process: mild blur to remove noise before thresholding ────────
        blurred = cv2.GaussianBlur(img, (5, 5), 0)

        # Dark pixels → white (active), light background → black
        _, thresh = cv2.threshold(blurred, 127, 255, cv2.THRESH_BINARY_INV)

        # ── Remove tiny isolated blobs (stray dots from noise) ────────────────
        kernel = np.ones((3, 3), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=2)

        # ── Physical scaling ──────────────────────────────────────────────────
        h_pixels, w_pixels = thresh.shape
        print(f"Image: {w_pixels}x{h_pixels}px | {target_width_mm}mm wide | {w_pixels/target_width_mm:.2f}px/mm")
        pixels_per_mm = w_pixels / target_width_mm
        target_height_mm = h_pixels / pixels_per_mm

        # ── Hexagonal grid math ───────────────────────────────────────────────
        step = stone_size_mm + spacing_mm          # centre-to-centre distance
        row_height = step * math.sin(math.radians(60))  # ~0.866 * step

        # Stone radius in the SVG: slightly smaller than half the stone diameter
        # so there is always a visible gap between stones in the preview.
        # The actual cut radius IS exactly stone_size_mm/2 — that is what the
        # cutter uses. We just render slightly smaller so they don't visually merge.
        svg_radius = (stone_size_mm / 2) * 0.92

        # Pad the grid by one radius so edge stones aren't clipped
        radius_mm = stone_size_mm / 2
        x_start = radius_mm
        y_start = radius_mm
        x_end   = target_width_mm  - radius_mm
        y_end   = target_height_mm - radius_mm

        rows = int((y_end - y_start) / row_height) + 1
        cols = int((x_end - x_start) / step) + 1

        circles = []

        for r in range(rows):
            for c in range(cols):
                x = x_start + c * step
                # Offset every other row for the honeycomb effect
                if r % 2 == 1:
                    x += step / 2

                y = y_start + r * row_height

                # Skip stones that would extend beyond the canvas
                if x > x_end or y > y_end:
                    continue

                # Convert physical coords to pixel coords for mask lookup
                px = int(round(x * pixels_per_mm))
                py = int(round(y * pixels_per_mm))

                # Clamp to valid pixel range
                px = max(0, min(px, w_pixels - 1))
                py = max(0, min(py, h_pixels - 1))

                # Place a stone only if the centre pixel is inside the design
                if thresh[py, px] == 255:
                    circles.append((x, y))

        # ── Build SVG ─────────────────────────────────────────────────────────
        svg_lines = [
            f'<svg width="{target_width_mm}mm" height="{target_height_mm:.2f}mm" '
            f'viewBox="0 0 {target_width_mm} {target_height_mm:.2f}" '
            f'xmlns="http://www.w3.org/2000/svg">'
        ]

        for cx, cy in circles:
            svg_lines.append(
                f'  <circle cx="{cx:.3f}" cy="{cy:.3f}" r="{svg_radius:.3f}" fill="#7c5cbf" />'
            )

        svg_lines.append('</svg>')
        svg_content = '\n'.join(svg_lines)

        return {
            "status": "success",
            "stone_count": len(circles),
            "svg_data": svg_content
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# Serve frontend — must be last so /api routes are registered first
app.mount("/", StaticFiles(directory="public", html=True), name="public")
