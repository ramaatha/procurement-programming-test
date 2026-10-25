# filepath: procurement/ai/images.py
import base64
import io
import warnings
from PIL import Image,ImageOps,UnidentifiedImageError
from .config import AIError


def prepare_image(upload) -> str:
    if upload.size > 2*1024*1024 or upload.content_type not in ('image/jpeg','image/png'):
        raise AIError('Gunakan gambar JPG/PNG maksimal 2 MB.',400)
    data=upload.read(2*1024*1024+1)
    if len(data)>2*1024*1024:
        raise AIError('Ukuran gambar melebihi 2 MB.',400)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as probe:
                if probe.format not in ('JPEG','PNG') or getattr(probe,'n_frames',1)!=1:
                    raise ValueError
                if probe.width*probe.height>12_000_000 or min(probe.size)<32:
                    raise ValueError
                probe.verify()
            with Image.open(io.BytesIO(data)) as source:
                oriented=ImageOps.exif_transpose(source)
                oriented.thumbnail((1600,1600))
                image=Image.new('RGB',oriented.size,'white')
                rgba=oriented.convert('RGBA')
                image.paste(rgba,mask=rgba.getchannel('A'))
                output=io.BytesIO()
                image.save(output,format='JPEG',quality=85)
    except (OSError,ValueError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise AIError('Gambar tidak dapat dibaca. Gunakan JPG/PNG yang jelas, maksimal 12 megapiksel.',400) from None
    return 'data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode('ascii')
