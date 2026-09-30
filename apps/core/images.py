"""Uploaded photos are made smaller before they are stored.

Phone cameras produce 5–12 MB pictures; the archive keeps a copy that is
large enough for a full screen and a printed book, but a fraction of the size.
"""
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_SIDE = 1800
PORTRAIT_SIDE = 1200


def shrink(upload, max_side=MAX_SIDE, quality=84):
    """Return (ContentFile, extension) with the image turned upright and
    scaled down, or None if `upload` is not an image Pillow can read."""
    try:
        upload.seek(0)
        image = Image.open(upload)
        image.load()
    except Exception:  # noqa: BLE001 - any unreadable file is simply not an image
        return None
    image = ImageOps.exif_transpose(image)
    has_alpha = image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    image.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = BytesIO()
    if has_alpha:
        image.convert("RGBA").save(buf, "PNG", optimize=True)
        ext = "png"
    else:
        image.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
        ext = "jpg"
    return ContentFile(buf.getvalue()), ext
