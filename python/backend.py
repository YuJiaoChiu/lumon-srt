from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import os
import json
import tempfile
import logging
import time
import shutil
import uuid
import threading
import zipfile
from pathlib import Path
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from correction_engine import CorrectionEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)  # For proper IP behind proxy
CORS(app)  # Enable CORS for all routes

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Configuration
UPLOAD_FOLDER = os.path.join(tempfile.gettempdir(), 'srt_correction')
ALLOWED_EXTENSIONS = {'srt'}
PROTECTION_DICT_FILE = os.path.join(os.path.dirname(__file__), '保护terms.json')
CORRECTION_DICT_FILE = os.path.join(os.path.dirname(__file__), 'correction_dictionary.json')
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max upload size
FILE_CLEANUP_THRESHOLD = 3600  # Clean up files older than 1 hour

# Security settings
DICTIONARY_PIN = "1324"  # Default PIN for dictionary modifications

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['JSON_AS_ASCII'] = False  # For proper UTF-8 encoding in responses

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the correction engine
correction_engine = CorrectionEngine(
    correction_dict_file=CORRECTION_DICT_FILE,
    protection_dict_file=PROTECTION_DICT_FILE
)

# Store processing tasks
processing_tasks = {}

# Helper functions
def allowed_file(filename):
    """Check if a filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """Clean up old temporary files."""
    now = time.time()
    count = 0
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                # If file is older than threshold, delete it
                if now - os.path.getmtime(file_path) > FILE_CLEANUP_THRESHOLD:
                    os.remove(file_path)
                    count += 1
        logger.info(f"Cleaned up {count} old files")
    except Exception as e:
        logger.error(f"Error during file cleanup: {str(e)}")

def generate_unique_filename(original_filename):
    """Generate a unique filename to prevent collisions."""
    base, ext = os.path.splitext(original_filename)
    return f"{base}_{uuid.uuid4().hex[:8]}{ext}"

# Task processing
def process_file_task(task_id, file_path, output_path):
    """Background task to process a single file."""
    try:
        # Update task status
        processing_tasks[task_id]['status'] = 'processing'

        # Define progress callback
        def progress_callback(percent):
            processing_tasks[task_id]['progress'] = percent
            # Log progress every 10%
            if int(percent) % 10 == 0:
                logger.info(f"Task {task_id} progress: {percent:.2f}%")

        # Process the file
        logger.info(f"Starting processing for task {task_id}, file: {file_path}")
        start_time = time.time()
        result = correction_engine.process_file(file_path, output_path, progress_callback)
        elapsed_time = time.time() - start_time

        # Update task with results
        processing_tasks[task_id]['status'] = 'completed'
        processing_tasks[task_id]['progress'] = 100
        processing_tasks[task_id]['result'] = result
        processing_tasks[task_id]['completed_at'] = time.time()
        processing_tasks[task_id]['processing_time'] = elapsed_time

        logger.info(f"Task {task_id} completed in {elapsed_time:.2f} seconds")
        logger.info(f"Processed {result.get('total_replacements', 0)} replacements")

    except Exception as e:
        logger.error(f"Error in task {task_id}: {str(e)}")
        processing_tasks[task_id]['status'] = 'error'
        processing_tasks[task_id]['error'] = str(e)
        processing_tasks[task_id]['completed_at'] = time.time()

def process_multiple_files_task(task_id):
    """Background task to process multiple files."""
    try:
        # Update task status
        task = processing_tasks[task_id]
        task['status'] = 'processing'
        task['results'] = []
        task['total_replacements'] = 0

        file_info_list = task['file_info']
        total_files = len(file_info_list)

        logger.info(f"Starting processing for task {task_id} with {total_files} files")
        start_time = time.time()

        # Process each file
        for i, file_info in enumerate(file_info_list):
            file_path = file_info['file_path']
            output_path = file_info['output_path']
            original_filename = file_info['original_filename']

            # Update progress for overall task
            base_progress = (i / total_files) * 100

            # Define progress callback for this file
            def file_progress_callback(percent):
                # Calculate overall progress: base progress + (file progress / total files)
                overall_progress = base_progress + (percent / total_files)
                task['progress'] = overall_progress
                # Log progress every 5%
                if int(overall_progress) % 5 == 0 and int(overall_progress) > int(task.get('last_logged_progress', 0)):
                    task['last_logged_progress'] = overall_progress
                    logger.info(f"Task {task_id} overall progress: {overall_progress:.2f}% (File {i+1}/{total_files})")

            # Process the file
            logger.info(f"Processing file {i+1}/{total_files}: {original_filename}")
            try:
                result = correction_engine.process_file(file_path, output_path, file_progress_callback)

                # Add download URL to result
                output_filename = os.path.basename(output_path)
                result['download_url'] = f"/api/download/{output_filename}"

                # Add to results
                task['results'].append(result)
                task['total_replacements'] += result.get('total_replacements', 0)
                task['files_processed'] += 1

                logger.info(f"Processed file {i+1}/{total_files}: {original_filename} with {result.get('total_replacements', 0)} replacements")
            except Exception as e:
                logger.error(f"Error processing file {original_filename}: {str(e)}")
                # Add error result
                task['results'].append({
                    'original_filename': original_filename,
                    'error': str(e),
                    'status': 'error'
                })

        # Update task with final results
        elapsed_time = time.time() - start_time
        task['status'] = 'completed'
        task['progress'] = 100
        task['completed_at'] = time.time()
        task['processing_time'] = elapsed_time

        # Add statistics
        task['statistics'] = {
            'totalFiles': total_files,
            'filesProcessed': task['files_processed'],
            'totalCorrections': task['total_replacements'],
            'processingTime': elapsed_time
        }

        logger.info(f"Task {task_id} completed in {elapsed_time:.2f} seconds")
        logger.info(f"Processed {total_files} files with {task['total_replacements']} total replacements")

    except Exception as e:
        logger.error(f"Error in multi-file task {task_id}: {str(e)}")
        processing_tasks[task_id]['status'] = 'error'
        processing_tasks[task_id]['error'] = str(e)
        processing_tasks[task_id]['completed_at'] = time.time()

# Routes
@app.route('/api/health', methods=['GET'])
@limiter.exempt  # No rate limit for health checks
def health_check():
    # Run cleanup on health check requests
    cleanup_old_files()
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "timestamp": time.time()
    })

@app.route('/api/dictionaries/protection', methods=['GET', 'POST'])
@limiter.exempt  # Remove rate limit for testing
def protection_dictionary():
    if request.method == 'GET':
        return jsonify(correction_engine.protection_dict)
    elif request.method == 'POST':
        try:
            # Verify PIN code
            pin = request.json.get('pin')
            if pin != DICTIONARY_PIN:
                return jsonify({"error": "Invalid PIN code"}), 403

            protection_dict = request.json.get('dictionary', {})
            if not isinstance(protection_dict, dict):
                return jsonify({"error": "Invalid dictionary format"}), 400

            # Validate dictionary entries
            for key in list(protection_dict.keys()):
                if not isinstance(key, str) or not key.strip():
                    del protection_dict[key]  # Remove invalid keys

            if correction_engine.update_protection_dict(protection_dict):
                return jsonify({
                    "status": "success",
                    "message": "Protection dictionary updated",
                    "count": len(protection_dict)
                })
            else:
                return jsonify({"error": "Failed to save dictionary"}), 500
        except Exception as e:
            logger.error(f"Error updating protection dictionary: {str(e)}")
            return jsonify({"error": "Invalid request"}), 400

@app.route('/api/dictionaries/correction', methods=['GET', 'POST'])
@limiter.exempt  # Remove rate limit for testing
def correction_dictionary():
    if request.method == 'GET':
        return jsonify(correction_engine.correction_dict)
    elif request.method == 'POST':
        try:
            # Verify PIN code
            pin = request.json.get('pin')
            if pin != DICTIONARY_PIN:
                return jsonify({"error": "Invalid PIN code"}), 403

            correction_dict = request.json.get('dictionary', {})
            if not isinstance(correction_dict, dict):
                return jsonify({"error": "Invalid dictionary format"}), 400

            # Validate dictionary entries
            for key in list(correction_dict.keys()):
                if not isinstance(key, str) or not key.strip():
                    del correction_dict[key]  # Remove invalid keys

            if correction_engine.update_correction_dict(correction_dict):
                return jsonify({
                    "status": "success",
                    "message": "Correction dictionary updated",
                    "count": len(correction_dict)
                })
            else:
                return jsonify({"error": "Failed to save dictionary"}), 500
        except Exception as e:
            logger.error(f"Error updating correction dictionary: {str(e)}")
            return jsonify({"error": "Invalid request"}), 400

@app.route('/api/process', methods=['POST'])
@limiter.exempt  # Remove rate limit for testing
def process_files():
    try:
        if 'files' not in request.files and 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        # Get files from request (support both 'file' and 'files')
        files = []
        if 'files' in request.files:
            files = request.files.getlist('files')
        elif 'file' in request.files:
            files = [request.files['file']]

        if not files or all(file.filename == '' for file in files):
            return jsonify({"error": "No file selected"}), 400

        # Filter out invalid files
        valid_files = []
        for file in files:
            if file.filename == '':
                continue
            if not allowed_file(file.filename):
                logger.warning(f"Skipping invalid file type: {file.filename}")
                continue
            valid_files.append(file)

        if not valid_files:
            return jsonify({"error": "No valid SRT files found. Only SRT files are allowed."}), 400

        # Create a task ID
        task_id = str(uuid.uuid4())

        # Save files and prepare for processing
        file_info = []
        for file in valid_files:
            # Save the uploaded file
            safe_filename = secure_filename(file.filename)
            unique_filename = generate_unique_filename(safe_filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)

            # Generate output filename
            output_filename = f"{os.path.splitext(unique_filename)[0]}_corrected.srt"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

            file_info.append({
                'original_filename': file.filename,
                'file_path': file_path,
                'output_path': output_path
            })

        # Initialize task status
        processing_tasks[task_id] = {
            'status': 'queued',
            'progress': 0,
            'created_at': time.time(),
            'file_count': len(file_info),
            'files_processed': 0,
            'file_info': file_info,
            'results': []
        }

        # Start processing in a background thread
        thread = threading.Thread(
            target=process_multiple_files_task,
            args=(task_id,)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "success",
            "message": f"Processing started for {len(file_info)} files",
            "task_id": task_id
        })

    except Exception as e:
        logger.error(f"Error in process_files: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
@limiter.exempt  # Remove rate limit for testing
def get_task_status(task_id):
    if task_id not in processing_tasks:
        return jsonify({"error": "Task not found"}), 404

    task = processing_tasks[task_id]
    response = {
        "status": task['status'],
        "progress": task['progress'],
        "created_at": task['created_at']
    }

    # Add file name for backward compatibility
    if 'file_name' in task:
        response['file_name'] = task['file_name']
    elif 'file_info' in task and task['file_info']:
        response['file_name'] = task['file_info'][0]['original_filename']

    # Include results if task is completed
    if task['status'] == 'completed':
        # Multi-file results
        if 'results' in task and task['results']:
            # Convert tuple keys to strings in replacements dictionary for each result
            for result in task['results']:
                if 'replacements' in result:
                    string_replacements = {}
                    for key, value in result['replacements'].items():
                        if isinstance(key, tuple):
                            # Convert tuple key to string
                            wrong, correct = key
                            string_key = f"{wrong} -> {correct}"
                            string_replacements[string_key] = value
                        else:
                            string_replacements[str(key)] = value
                    result['replacements'] = string_replacements

            response['results'] = task['results']

            # Add statistics if available
            if 'statistics' in task:
                response['statistics'] = task['statistics']

        # Single file result (backward compatibility)
        elif 'result' in task:
            # Convert tuple keys to strings in replacements dictionary
            if 'replacements' in task['result']:
                string_replacements = {}
                for key, value in task['result']['replacements'].items():
                    if isinstance(key, tuple):
                        # Convert tuple key to string
                        wrong, correct = key
                        string_key = f"{wrong} -> {correct}"
                        string_replacements[string_key] = value
                    else:
                        string_replacements[str(key)] = value
                task['result']['replacements'] = string_replacements

            response['result'] = task['result']
            response['download_url'] = f"/api/download/{os.path.basename(task['output_path'])}"

    # Include error if task failed
    if task['status'] == 'error' and 'error' in task:
        response['error'] = task['error']

    return jsonify(response)

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_file(file_path, as_attachment=True, download_name=filename)

@app.route('/api/dictionaries/update-term', methods=['POST'])
@limiter.exempt
def update_dictionary_term():
    """Add, update or delete a single term in the dictionary."""
    try:
        # Verify PIN code
        pin = request.json.get('pin')
        if pin != DICTIONARY_PIN:
            return jsonify({"error": "Invalid PIN code"}), 403

        # Get parameters
        dict_type = request.json.get('type')  # 'correction' or 'protection'
        term = request.json.get('term')
        value = request.json.get('value', '')
        action = request.json.get('action')  # 'add', 'update', or 'delete'

        if not dict_type or not term or not action:
            return jsonify({"error": "Missing required parameters"}), 400

        if dict_type not in ['correction', 'protection']:
            return jsonify({"error": "Invalid dictionary type"}), 400

        if action not in ['add', 'update', 'delete']:
            return jsonify({"error": "Invalid action"}), 400

        # Get the appropriate dictionary
        if dict_type == 'correction':
            dictionary = correction_engine.correction_dict.copy()
        else:  # protection
            dictionary = correction_engine.protection_dict.copy()

        # Perform the requested action
        if action in ['add', 'update']:
            dictionary[term] = value
        elif action == 'delete':
            if term in dictionary:
                del dictionary[term]
            else:
                return jsonify({"error": "Term not found"}), 404

        # Save the updated dictionary
        if dict_type == 'correction':
            success = correction_engine.update_correction_dict(dictionary)
        else:  # protection
            success = correction_engine.update_protection_dict(dictionary)

        if success:
            return jsonify({
                "status": "success",
                "message": f"Term '{term}' {action}ed in {dict_type} dictionary",
                "count": len(dictionary)
            })
        else:
            return jsonify({"error": "Failed to save dictionary"}), 500
    except Exception as e:
        logger.error(f"Error updating dictionary term: {str(e)}")
        return jsonify({"error": "Invalid request"}), 400

@app.route('/api/dictionaries/search', methods=['GET'])
@limiter.exempt
def search_dictionary():
    """Search for terms in the dictionaries."""
    try:
        # Get parameters
        query = request.args.get('q', '')
        dict_type = request.args.get('type')  # 'correction', 'protection', or 'all'

        if not query:
            return jsonify({"error": "Missing search query"}), 400

        if dict_type not in ['correction', 'protection', 'all']:
            return jsonify({"error": "Invalid dictionary type"}), 400

        results = {}

        # Search in correction dictionary
        if dict_type in ['correction', 'all']:
            correction_results = {}
            for term, value in correction_engine.correction_dict.items():
                if query.lower() in term.lower():
                    correction_results[term] = value
            results['correction'] = correction_results

        # Search in protection dictionary
        if dict_type in ['protection', 'all']:
            protection_results = {}
            for term in correction_engine.protection_dict.keys():
                if query.lower() in term.lower():
                    protection_results[term] = ''
            results['protection'] = protection_results

        return jsonify({
            "status": "success",
            "query": query,
            "results": results
        })
    except Exception as e:
        logger.error(f"Error searching dictionaries: {str(e)}")
        return jsonify({"error": "Invalid request"}), 400

@app.route('/api/download-multiple', methods=['POST'])
@limiter.exempt
def download_multiple_files():
    """Download multiple files as a zip archive."""
    try:
        # Get list of filenames from request
        filenames = request.json.get('filenames', [])
        if not filenames:
            return jsonify({"error": "No files specified"}), 400

        # Create a temporary zip file
        zip_filename = f"corrected_files_{uuid.uuid4().hex[:8]}.zip"
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

        # Create zip file with all requested files
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for filename in filenames:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
                if os.path.exists(file_path):
                    # Add file to zip with just the filename (not the full path)
                    zipf.write(file_path, os.path.basename(file_path))

        # Return the zip file
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    except Exception as e:
        logger.error(f"Error creating zip file: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Create initial dictionaries if they don't exist
    if not os.path.exists(PROTECTION_DICT_FILE):
        initial_protection = {
            "dall-e": "",
            "midjourney": "",
            "ctrl": "",
            "shift": ""
        }
        correction_engine.update_protection_dict(initial_protection)

    if not os.path.exists(CORRECTION_DICT_FILE):
        initial_correction = {
            "[Subscription]": "",
            "\"": "",
            "\"": "",
            "\"": "",
            "[Thank you]": ""
        }
        correction_engine.update_correction_dict(initial_correction)

    app.run(host='0.0.0.0', port=5002, debug=True)
