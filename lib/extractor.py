"""Image extraction from CBZ (ZIP) files."""
import os
import zipfile
from PIL import Image
import tempfile
import shutil

from .utils import get_file_extension, file_exists


class ArchiveExtractor:
    """Extract images from CBZ (ZIP) archives."""

    SUPPORTED_EXTENSIONS = {'.cbz'}

    def __init__(self, archive_path):
        if not file_exists(archive_path):
            raise FileNotFoundError(f"Archivo no encontrado: {archive_path}")

        ext = get_file_extension(archive_path)
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato no soportado: {ext}. Usar solo CBZ.")

        self.archive_path = archive_path
        self.ext = ext
        self.temp_dir = None

    def _get_image_extensions(self):
        """Return set of supported image extensions."""
        return {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

    def _is_image(self, filename):
        """Check if file is a supported image."""
        ext = os.path.splitext(filename)[1].lower()
        return ext in self._get_image_extensions()

    def _extract_zip(self, temp_dir):
        """Extract ZIP archive."""
        with zipfile.ZipFile(self.archive_path, 'r') as zf:
            zf.extractall(temp_dir)
        return self._get_extracted_files(temp_dir)

    def _get_extracted_files(self, directory):
        """Get list of image files from extracted directory."""
        images = []
        for root, _, files in os.walk(directory):
            for filename in sorted(files):
                if self._is_image(filename):
                    full_path = os.path.join(root, filename)
                    images.append(full_path)
        return images

    def extract(self):
        """Extract all images from archive to temporary directory."""
        self.temp_dir = tempfile.mkdtemp(prefix='cbr2epub_')
        try:
            files = self._extract_zip(self.temp_dir)

            if not files:
                raise ValueError("No se encontraron imagenes en el archivo.")

            return files
        except Exception as e:
            self.cleanup()
            raise e

    def cleanup(self):
        """Remove temporary extraction directory."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def get_temp_dir(self):
        """Return temp directory path for external use."""
        return self.temp_dir

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


def extract_archive(archive_path):
    """Convenience function to extract archive and return image paths."""
    with ArchiveExtractor(archive_path) as extractor:
        images = extractor.extract()
        return images