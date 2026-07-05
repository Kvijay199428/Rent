import os
from PIL import Image, ImageOps
import io
import shutil

from app.core.paths import UPLOADS_DIR as SIGNATURE_DIR

def flatten_signature(input_path, output_path):
    """
    Removes white background, converts to transparent PNG, 
    and crops excess whitespace.
    """
    try:
        # Open image and ensure it has an alpha channel
        img = Image.open(input_path).convert("RGBA")
        
        # Get data
        data = img.getdata()
        
        new_data = []
        for item in data:
            # Change all white (also shades of white)
            # to transparent. 
            # A simple heuristic: if R, G, B are all > 220, it's white-ish.
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                new_data.append((255, 255, 255, 0)) # transparent
            else:
                new_data.append(item)
                
        img.putdata(new_data)
        
        # Crop to bounding box of non-transparent pixels
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
            
        # Save as PNG
        img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error processing signature: {e}")
        return False

def save_signature(file_bytes: bytes, filename: str) -> str:
    """
    Saves the uploaded signature and processes it.
    Returns the path to the flattened signature.
    """
    temp_path = os.path.join(SIGNATURE_DIR, "temp_" + filename)
    flattened_path = os.path.join(SIGNATURE_DIR, "landlord_signature_flattened.png")
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
        
    success = flatten_signature(temp_path, flattened_path)
    
    # Remove temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    if success:
        return flattened_path
    return ""

def delete_signature():
    """
    Deletes the saved signature.
    """
    flattened_path = os.path.join(SIGNATURE_DIR, "landlord_signature_flattened.png")
    if os.path.exists(flattened_path):
        try:
            os.remove(flattened_path)
        except Exception:
            pass
