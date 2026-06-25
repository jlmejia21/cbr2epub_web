
"""Image processing for maximum quality Kindle/iPad optimization."""
from PIL import Image
import os


MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5MB max per image
TARGET_QUALITY = 80  # Good balance quality/size


def get_image_size_mb(filepath):
    """Get image file size in MB."""
    return os.path.getsize(filepath) / (1024 * 1024)


def resize_image_if_needed(image_path, max_bytes=MAX_IMAGE_SIZE_BYTES):
    """Resize image only if it exceeds max size while preserving maximum quality."""
    current_size = os.path.getsize(image_path)

    if current_size <= max_bytes:
        return image_path

    img = Image.open(image_path)
    original_width, original_height = img.size

    width, height = original_width, original_height
    scale = 1.0

    while True:
        new_width = int(width * scale)
        new_height = int(height * scale)

        if new_width < 100 or new_height < 100:
            break

        img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        temp_path = image_path + '.tmp'
        img_resized.save(temp_path, quality=TARGET_QUALITY, optimize=True)

        if os.path.getsize(temp_path) <= max_bytes:
            os.replace(temp_path, image_path)
            img.close()
            return image_path

        scale *= 0.95
        img_resized.close()
        if os.path.exists(temp_path):
            os.remove(temp_path)

    img.close()
    return image_path


def convert_to_jpeg_max_quality(image_path, quality=TARGET_QUALITY):
    """Convert non-JPEG images to JPEG with maximum quality保留."""
    ext = os.path.splitext(image_path)[1].lower()

    if ext in ['.jpg', '.jpeg']:
        return image_path

    try:
        img = Image.open(image_path)

        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                background.paste(img, mask=img.split()[3])
            else:
                background.paste(img, mask=img.split()[1] if len(img.split()) > 1 else None)
            img = background
        elif img.mode == 'P':
            if 'transparency' in img.info:
                img = img.convert('RGBA')
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        base_name = os.path.splitext(image_path)[0]
        jpeg_path = base_name + '.jpg'

        img.save(jpeg_path, quality=quality, optimize=True)
        img.close()

        if image_path != jpeg_path:
            os.remove(image_path)
            return jpeg_path

        return image_path
    except Exception as e:
        raise ValueError(f"Error convirtiendo imagen {image_path}: {e}")


def optimize_image(image_path, max_bytes=MAX_IMAGE_SIZE_BYTES, force_jpeg=False):
    """Full optimization pipeline preserving maximum quality.

    Args:
        image_path: Path to image file
        max_bytes: Maximum file size in bytes
        force_jpeg: If True, convert all images to JPEG. If False, keep original format if possible.
    """
    if force_jpeg:
        image_path = convert_to_jpeg_max_quality(image_path, TARGET_QUALITY)
    else:
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in ['.jpg', '.jpeg']:
            try:
                image_path = convert_to_jpeg_max_quality(image_path, TARGET_QUALITY)
            except Exception:
                pass

    image_path = resize_image_if_needed(image_path, max_bytes)

    return image_path


def get_image_dimensions(image_path):
    """Get image dimensions (width, height)."""
    with Image.open(image_path) as img:
        return img.size


def validate_image(image_path):
    """Check if image is valid and can be opened."""
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False