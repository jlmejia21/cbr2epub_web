#!/usr/bin/env python3
"""
CBR to EPUB Converter - Web Application (Flask Backend)
Convert Comic Book RAR/CBZ archives to EPUB format for Kindle/iPad.
"""
import os
import sys
import uuid
import shutil
import threading
from datetime import timedelta

from flask import Flask, render_template, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.extractor import ArchiveExtractor
from lib.image_proc import optimize_image
from lib.epub_builder import EpubBuilder
from lib.utils import sort_pages_filenames, get_file_extension, sanitize_filename

# Configuration
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
UPLOAD_FOLDER = '/tmp/cbr2epub_uploads'
OUTPUT_FOLDER = '/tmp/cbr2epub_outputs'
ALLOWED_EXTENSIONS = {'cbz'}

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload

# Store conversion tasks
tasks = {}


def allowed_file(filename):
    """Check if file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files():
    """Remove files older than 1 hour."""
    import time
    now = time.time()
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        if os.path.exists(folder):
            for item in os.listdir(folder):
                item_path = os.path.join(folder, item)
                if os.path.isfile(item_path) and now - os.path.getmtime(item_path) > 3600:
                    try:
                        os.remove(item_path)
                    except Exception:
                        pass
                elif os.path.isdir(item_path) and now - os.path.getmtime(item_path) > 3600:
                    try:
                        shutil.rmtree(item_path)
                    except Exception:
                        pass


def convert_task(task_id, archive_path, title, author, output_dir):
    """Background conversion task."""
    try:
        tasks[task_id]['status'] = 'extracting'
        tasks[task_id]['progress'] = 5
        tasks[task_id]['message'] = 'Extrayendo imagenes...'

        extractor = ArchiveExtractor(archive_path)
        image_paths = extractor.extract()
        temp_dir = extractor.get_temp_dir()

        total = len(image_paths)
        tasks[task_id]['total_pages'] = total

        tasks[task_id]['status'] = 'sorting'
        tasks[task_id]['progress'] = 10
        tasks[task_id]['message'] = f'Imagenes extraidas: {total}'

        image_paths = sort_pages_filenames(image_paths)
        optimized_paths = []

        for i, img_path in enumerate(image_paths):
            progress = 10 + (80 * i // total)
            tasks[task_id]['progress'] = progress
            tasks[task_id]['message'] = f'Optimizando {i+1}/{total}...'

            try:
                optimized = optimize_image(img_path, MAX_IMAGE_SIZE, force_jpeg=False)
                optimized_paths.append(optimized)
            except Exception:
                optimized_paths.append(img_path)

        tasks[task_id]['status'] = 'generating'
        tasks[task_id]['progress'] = 92
        tasks[task_id]['message'] = 'Generando EPUB...'

        epub = EpubBuilder(title=title, author=author)
        for img_path in optimized_paths:
            epub.add_image(img_path)

        safe_title = sanitize_filename(title) or 'output'
        output_path = os.path.join(output_dir, f'{safe_title}.epub')

        epub.build(output_path)
        extractor.cleanup()

        size_mb = os.path.getsize(output_path) / (1024 * 1024)

        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['message'] = 'Completado!'
        tasks[task_id]['output_path'] = output_path
        tasks[task_id]['size_mb'] = size_mb

    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['message'] = f'Error: {str(e)}'
        tasks[task_id]['error'] = str(e)


@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload():
    """Handle file upload and start conversion."""
    if 'file' not in request.files:
        return jsonify({'error': 'No se encontro archivo'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No se selecciono archivo'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Formato no soportado. Usar solo CBZ.'}), 400

    title = request.form.get('title', '').strip()
    if not title:
        title = os.path.splitext(secure_filename(file.filename))[0]

    author = request.form.get('author', 'Desconocido').strip()

    output_dir = request.form.get('output_dir', OUTPUT_FOLDER)

    task_id = str(uuid.uuid4())

    temp_upload = os.path.join(UPLOAD_FOLDER, f'{task_id}_{secure_filename(file.filename)}')
    file.save(temp_upload)

    tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'message': 'Iniciando...',
        'filename': file.filename,
        'title': title,
        'author': author,
        'output_dir': output_dir,
        'upload_path': temp_upload
    }

    thread = threading.Thread(target=convert_task, args=(task_id, temp_upload, title, author, output_dir))
    thread.daemon = True
    thread.start()

    return jsonify({
        'task_id': task_id,
        'status': 'started',
        'message': 'Conversion iniciada'
    })


@app.route('/api/status/<task_id>')
def status(task_id):
    """Get conversion status."""
    if task_id not in tasks:
        return jsonify({'error': 'Tarea no encontrada'}), 404

    task = tasks[task_id]
    return jsonify({
        'status': task['status'],
        'progress': task['progress'],
        'message': task['message'],
        'total_pages': task.get('total_pages', 0)
    })


@app.route('/api/download/<task_id>')
def download(task_id):
    """Download completed EPUB."""
    if task_id not in tasks:
        abort(404)

    task = tasks[task_id]
    if task['status'] != 'completed':
        return jsonify({'error': 'EPUB no disponible todavia'}), 400

    output_path = task.get('output_path')
    if not output_path or not os.path.exists(output_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404

    safe_title = sanitize_filename(task['title']) or 'output'
    filename = f'{safe_title}.epub'

    return send_file(output_path, as_attachment=True, download_name=filename)


@app.route('/api/cleanup', methods=['POST'])
def cleanup():
    """Clean up old files."""
    cleanup_old_files()
    return jsonify({'message': 'Limpieza completada'})


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({'error': 'Archivo muy grande. Maximo 500MB.'}), 413


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    print("=" * 50)
    print("  CBR/CBZ a EPUB - Web Application")
    print(f"  http://localhost:{port}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)