from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
import math

app = FastAPI()

# 1. The API Endpoint (Catches the request from app.js)
@app.post("/api/generate")
async def generate_rhinestone_api(
    image: UploadFile = File(...),
    stone_size_mm: float = Form(...),
    target_width_mm: float = Form(...),
    spacing_mm: float = Form(...)
):
    try:
        # Read the uploaded image into memory
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        
        # Convert image to grayscale
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        
        # Create a binary mask (dark pixels become white/active, background becomes black)
        _, thresh = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Calculate physical scaling (Pixels to Millimeters)
        h_pixels, w_pixels = thresh.shape
        pixels_per_mm = w_pixels / target_width_mm
        target_height_mm = h_pixels / pixels_per_mm
        
        # Hexagonal Grid Math
        step = stone_size_mm + spacing_mm
        row_height = step * math.sin(math.radians(60))
        
        circles = []
        rows = int(target_height_mm / row_height)
        cols = int(target_width_mm / step)
        
        # Generate the grid points and check against the image
        for r in range(rows):
            for c in range(cols):
                x = c * step
                # Offset every other row for the honeycomb effect
                if r % 2 == 1:
                    x += step / 2 
                y = r * row_height
                
                # Convert physical coordinates back to pixels to check the mask
                px = int(x * pixels_per_mm)
                py = int(y * pixels_per_mm)
                
                # If point is inside bounds AND lands on the design, place a stone
                if px < w_pixels and py < h_pixels:
                    if thresh[py, px] == 255: 
                        circles.append((x, y))
                        
        # Construct the SVG string (Using the Amethyst color from your CSS)
        svg_content = f'<svg width="{target_width_mm}mm" height="{target_height_mm}mm" viewBox="0 0 {target_width_mm} {target_height_mm}" xmlns="http://www.w3.org/2000/svg">\n'
        for cx, cy in circles:
            svg_content += f'  <circle cx="{cx:.2f}" cy="{cy:.2f}" r="{stone_size_mm/2:.2f}" fill="#7c5cbf" />\n'
        svg_content += '</svg>'
        
        # Return the exact JSON structure app.js is expecting
        return {
            "status": "success",
            "stone_count": len(circles),
            "svg_data": svg_content
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# 2. Serve the Frontend UI
# We put this at the bottom so it doesn't overwrite the /api route
app.mount("/", StaticFiles(directory="public", html=True), name="public")
