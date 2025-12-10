import sys
import base64
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile

def generate_lqip(image_field):
    """
    Generates a Low-Quality Image Placeholder (Base64 String).
    Returns: "data:image/webp;base64,..."
    """
    if not image_field:
        return None
    
    try:
        if hasattr(image_field, 'open'):
            image_field.open()
        
        img = Image.open(image_field)
        
        # 1. Ultra-Resize (to 20px width)
        aspect = img.height / img.width
        new_height = int(20 * aspect)
        img_small = img.resize((20, new_height), Image.Resampling.LANCZOS)
        
        # 2. Convert to WebP
        buffer = BytesIO()
        img_small.save(buffer, format="WEBP", quality=40)
        
        # 3. Encode to Base64
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/webp;base64,{img_str}"
        
    except Exception as e:
        print(f"LQIP Error: {e}")
        return None

def optimize_image(image_field, max_width=1200, quality=80):
    """
    Overwrites the original image with an optimized WebP version.
    """
    if not image_field:
        return None

    try:
        if hasattr(image_field, 'open'):
            image_field.open()
            
        img = Image.open(image_field)
        
        # Skip if already optimized (small WebP)
        if img.format == 'WEBP' and img.width <= max_width:
            return image_field

        # 1. Resize
        if img.width > max_width:
            output_size = (max_width, int(img.height * (max_width / img.width)))
            img = img.resize(output_size, Image.Resampling.LANCZOS)

        # 2. Save as WebP
        output_io = BytesIO()
        img.save(output_io, format='WEBP', quality=quality, optimize=True)
        output_io.seek(0)

        # 3. Create New File Object
        new_name = image_field.name.rsplit('.', 1)[0] + ".webp"
        
        return InMemoryUploadedFile(
            output_io, 'ImageField', new_name, 'image/webp',
            sys.getsizeof(output_io), None
        )
    except Exception as e:
        print(f"Optimization Error: {e}")
        return image_field # Return original on failure