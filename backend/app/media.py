"""Picture uploads: validate, shrink and store in the database."""
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from .models import MediaFile, db

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_SIDE = 1800          # longest edge in pixels; bigger uploads are shrunk
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class UploadError(Exception):
    pass


def save_upload(file_storage):
    """Turn an uploaded file into a MediaFile row (not yet committed). Raises UploadError."""
    if not file_storage or not file_storage.filename:
        raise UploadError("Choose a picture first.")
    raw = file_storage.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadError("That picture is larger than 8 MB.")
    try:
        img = Image.open(io.BytesIO(raw))
        if img.format not in ALLOWED_FORMATS:
            raise UploadError("Use a JPG, PNG or WebP picture.")
        img = ImageOps.exif_transpose(img)  # respect phone-camera rotation
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    except UnidentifiedImageError:
        raise UploadError("That file is not a picture.")
    except (OSError, Image.DecompressionBombError):
        raise UploadError("That picture could not be read.")

    out = io.BytesIO()
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        img.save(out, "PNG", optimize=True)   # keep transparency (logos)
        mime = "image/png"
    else:
        img.convert("RGB").save(out, "JPEG", quality=85, optimize=True, progressive=True)
        mime = "image/jpeg"
    media = MediaFile(data=out.getvalue(), mime=mime, width=img.width, height=img.height)
    db.session.add(media)
    db.session.flush()
    return media


def delete_media(media_id):
    """Remove a picture nothing uses any more."""
    if media_id:
        row = db.session.get(MediaFile, media_id)
        if row:
            db.session.delete(row)
