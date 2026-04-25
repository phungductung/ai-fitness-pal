import base64
from io import BytesIO
from PIL import Image
from pdf2image import convert_from_path

def pdf_to_base64_images(pdf_path: str):
    """Convert each page of a PDF into a base64 encoded string for GPT-4o Vision."""
    images = convert_from_path(pdf_path)
    base64_images = []
    
    for img in images:
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        base64_images.append(base64.b64encode(buffered.getvalue()).decode('utf-8'))
    
    return base64_images

def encode_image(image_path: str):
    """Encode a single image file to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
