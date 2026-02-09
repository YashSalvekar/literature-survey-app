import io
import zipfile


def create_zip(files_dict):
    """
    files_dict = {filename: bytes}
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fname, fbytes in files_dict.items():
            zipf.writestr(fname, fbytes)
    buffer.seek(0)
    return buffer
