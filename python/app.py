from flask import Flask, request, jsonify, send_file, Response
from flask_cors import CORS
import os
import json
import tempfile
import logging
import time
import shutil
import uuid
import concurrent.futures
from functools import lru_cache
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from correction import correct_subtitles, validate_srt

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['JSON_AS_ASCII'] = False  # For proper UTF-8 encoding in responses

# Ensure directories exist
os.makedirs(os.path.join(os.path.dirname(__file__), 'dictionaries'), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper functions
def allowed_file(filename):
    """Check if a filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@lru_cache(maxsize=8)
def load_dictionary(filename):
    """Load a dictionary from a JSON file, creating it if it doesn't exist.

    This function is cached to improve performance when dictionaries are accessed frequently.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create empty dictionary if file doesn't exist
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {filename}. Creating new dictionary.")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return {}

def save_dictionary(dictionary, filename):
    """Save a dictionary to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving dictionary to {filename}: {str(e)}")
        return False

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

# Routes
@app.route('/api/health', methods=['GET'])
@limiter.exempt  # No rate limit for health checks
def health_check():
    # Run cleanup on health check requests
    cleanup_old_files()
    return jsonify({
        "status": "ok",
        "version": "1.1.0",
        "timestamp": time.time()
    })

@app.route('/api/dictionaries/protection', methods=['GET', 'POST'])
@limiter.limit("30/hour")  # Custom rate limit for dictionary operations
def protection_dictionary():
    if request.method == 'GET':
        protection_dict = load_dictionary(PROTECTION_DICT_FILE)
        return jsonify(protection_dict)
    elif request.method == 'POST':
        try:
            protection_dict = request.json
            if not isinstance(protection_dict, dict):
                return jsonify({"error": "Invalid dictionary format"}), 400

            # Validate dictionary entries
            for key in list(protection_dict.keys()):
                if not isinstance(key, str) or not key.strip():
                    del protection_dict[key]  # Remove invalid keys

            if save_dictionary(protection_dict, PROTECTION_DICT_FILE):
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
@limiter.limit("30/hour")  # Custom rate limit for dictionary operations
def correction_dictionary():
    if request.method == 'GET':
        correction_dict = load_dictionary(CORRECTION_DICT_FILE)
        return jsonify(correction_dict)
    elif request.method == 'POST':
        try:
            correction_dict = request.json
            if not isinstance(correction_dict, dict):
                return jsonify({"error": "Invalid dictionary format"}), 400

            # Validate dictionary entries
            for key in list(correction_dict.keys()):
                if not isinstance(key, str) or not key.strip():
                    del correction_dict[key]  # Remove invalid keys

            if save_dictionary(correction_dict, CORRECTION_DICT_FILE):
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

@app.route('/api/dictionaries/export', methods=['GET'])
@limiter.limit("10/hour")
def export_dictionaries():
    try:
        protection_dict = load_dictionary(PROTECTION_DICT_FILE)
        correction_dict = load_dictionary(CORRECTION_DICT_FILE)

        export_data = {
            "protection": protection_dict,
            "correction": correction_dict,
            "exported_at": time.time(),
            "version": "1.1.0"
        }

        # Create a temporary file for the export
        temp_file = os.path.join(UPLOAD_FOLDER, f"dictionaries_export_{uuid.uuid4().hex[:8]}.json")
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        return send_file(
            temp_file,
            as_attachment=True,
            download_name="srt_correction_dictionaries.json",
            mimetype="application/json"
        )
    except Exception as e:
        logger.error(f"Error exporting dictionaries: {str(e)}")
        return jsonify({"error": "Failed to export dictionaries"}), 500

@app.route('/api/dictionaries/import', methods=['POST'])
@limiter.limit("10/hour")
def import_dictionaries():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.endswith('.json'):
            return jsonify({"error": "Only JSON files are supported"}), 400

        # Save and process the file
        temp_path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(temp_path)

        try:
            with open(temp_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            # Validate the import data
            if not isinstance(import_data, dict) or 'protection' not in import_data or 'correction' not in import_data:
                return jsonify({"error": "Invalid dictionary format"}), 400

            # Update dictionaries
            save_dictionary(import_data['protection'], PROTECTION_DICT_FILE)
            save_dictionary(import_data['correction'], CORRECTION_DICT_FILE)

            return jsonify({
                "status": "success",
                "message": "Dictionaries imported successfully",
                "protection_count": len(import_data['protection']),
                "correction_count": len(import_data['correction'])
            })
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Error importing dictionaries: {str(e)}")
        return jsonify({"error": "Failed to import dictionaries"}), 500

@app.route('/api/process', methods=['POST'])
@limiter.limit("20/hour")
def process_files():
    start_time = time.time()
    logger.info("Starting file processing request")

    try:
        if 'files' not in request.files:
            return jsonify({"error": "No files part"}), 400

        files = request.files.getlist('files')

        if not files or files[0].filename == '':
            return jsonify({"error": "No files selected"}), 400

        # Validate file count
        if len(files) > 10:
            return jsonify({"error": "Too many files. Maximum 10 files allowed per request"}), 400

        results = []
        total_replacements = {}
        processed_count = 0
        skipped_count = 0
        error_count = 0

        # Load dictionaries once for all files
        protection_dict = load_dictionary(PROTECTION_DICT_FILE)
        correction_dict = load_dictionary(CORRECTION_DICT_FILE)

        # Filter valid files
        valid_files = []
        for file in files:
            if not file or not file.filename:
                skipped_count += 1
                continue

            if not allowed_file(file.filename):
                logger.warning(f"Skipping file with unsupported extension: {file.filename}")
                skipped_count += 1
                continue

            valid_files.append(file)

        # Define a function to process a single file
        def process_single_file(file):
            try:
                # Generate unique filenames to prevent collisions
                safe_filename = secure_filename(file.filename)
                unique_filename = generate_unique_filename(safe_filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)

                # Read file content with proper encoding detection
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Try with different encoding if UTF-8 fails
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()

                # Validate SRT format
                if not validate_srt(content):
                    logger.warning(f"Invalid SRT format in file: {file.filename}")
                    return {
                        "original_filename": file.filename,
                        "error": "Invalid SRT format",
                        "status": "error"
                    }, {}, "error"

                # Process the file
                corrected_content, replacements = correct_subtitles(content, correction_dict, protection_dict)

                # Generate output filename and save corrected content
                output_filename = f"{os.path.splitext(unique_filename)[0]}_corrected.srt"
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(corrected_content)

                # Return result
                return {
                    "original_filename": file.filename,
                    "corrected_filename": output_filename,
                    "replacements": replacements,
                    "download_url": f"/api/download/{output_filename}",
                    "status": "success"
                }, replacements, "success"

            except Exception as e:
                logger.error(f"Error processing file {file.filename}: {str(e)}")
                return {
                    "original_filename": file.filename,
                    "error": str(e),
                    "status": "error"
                }, {}, "error"

        # Process files in parallel using ThreadPoolExecutor
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(valid_files))) as executor:
            # Submit all files for processing
            future_to_file = {executor.submit(process_single_file, file): file for file in valid_files}

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    result, file_replacements, status = future.result()
                    results.append(result)

                    # Update counters based on status
                    if status == "success":
                        processed_count += 1
                        # Update total replacements
                        for key, count in file_replacements.items():
                            if key in total_replacements:
                                total_replacements[key] += count
                            else:
                                total_replacements[key] = count
                    else:
                        error_count += 1

                except Exception as e:
                    logger.error(f"Exception processing file {file.filename}: {str(e)}")
                    results.append({
                        "original_filename": file.filename,
                        "error": str(e),
                        "status": "error"
                    })
                    error_count += 1

        elapsed_time = time.time() - start_time
        logger.info(f"Processed {processed_count} files in {elapsed_time:.2f} seconds")

        return jsonify({
            "status": "success",
            "results": results,
            "total_replacements": total_replacements,
            "statistics": {
                "totalCorrections": sum(total_replacements.values()) if total_replacements else 0,
                "protectedTermsCount": len(protection_dict),
                "correctionTermsCount": len(correction_dict),
                "processedCount": processed_count,
                "skippedCount": skipped_count,
                "errorCount": error_count,
                "processingTime": round(elapsed_time, 2)
            }
        })
    except Exception as e:
        logger.error(f"Unexpected error in process_files: {str(e)}")
        return jsonify({"error": "Server error while processing files"}), 500

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    # Initialize dictionaries if they don't exist
    if not os.path.exists(PROTECTION_DICT_FILE):
        initial_protection = {
            "dall-e": "",
            "midjourney": "",
            "ctrl": "",
            "shift": ""
        }
        save_dictionary(initial_protection, PROTECTION_DICT_FILE)

    if not os.path.exists(CORRECTION_DICT_FILE):
        initial_correction = {
            "[Subscription]": "",
            "\"": "",
            "\"": "",
            "\"": "",
            "[Thank you]": ""
        }
        save_dictionary(initial_correction, CORRECTION_DICT_FILE)

    app.run(host='0.0.0.0', port=5001, debug=True)
