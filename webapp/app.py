"""
Flask application entrypoint for the webapp interface.
"""
import sys
from pathlib import Path
# Define parent_dir for use throughout the app
parent_dir = str(Path(__file__).resolve().parent.parent)
sys.path.append(parent_dir)
import os
from flask import Flask, jsonify, redirect, url_for, request, send_file, session
from datetime import datetime
import requests
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from werkzeug.utils import secure_filename
import io

# Load environment variables from .env file
load_dotenv()

# Flask application setup
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
)

# Configure the app
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'meme-generator-secret-key')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Set jinja global variable for footer
@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

# Note: Data file serving is handled by the views blueprint

# Create a proxy route to the meme API
@app.route('/api/generate', methods=['GET', 'POST'])
@csrf.exempt  # Exempt this route from CSRF protection since it's a proxy
def proxy_to_meme_api():
    """Proxy requests to the meme generation API."""
    # Handle GET requests (when page is refreshed)
    if request.method == 'GET':
        return jsonify({'error': 'This endpoint only accepts POST requests with form data'}), 405
    
    try:
        # Configure the API URL (backend runs on port 8001)
        meme_api_port = os.environ.get('MEME_API_PORT', '8001')
        api_url = f"http://localhost:{meme_api_port}/api/generate"
        
        print(f"Forwarding request to: {api_url}")  # Debug log
        
        # Prepare the files dictionary for the request
        files = {}
        if request.files and 'image' in request.files:
            image_file = request.files['image']
            # Read the file content into memory
            file_content = image_file.read()
            # Create a file-like object from the content
            file_obj = io.BytesIO(file_content)
            # Add the file to the files dictionary
            files['image'] = (
                secure_filename(image_file.filename),  # Original filename
                file_obj,                             # File content
                image_file.content_type               # Content type
            )
        
        # Prepare form data
        form_data = {}
        for key in request.form:
            form_data[key] = request.form[key]
        
        print(f"Sending request with files: {bool(files)} and form data: {form_data}")  # Debug log
        
        # Forward the request to the API
        response = requests.post(
            api_url, 
            data=form_data,
            files=files,
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': request.headers.get('Origin', '*')
            },
            timeout=30
        )
        
        print(f"Backend response status: {response.status_code}")  # Debug log
        
        # If JSON response, store info in session
        if response.headers.get('Content-Type', '').startswith('application/json'):
            try:
                data = response.json()
                # Convert boolean to string to avoid session serialization issues
                is_from_template = data.get('from_template', False)
                session['from_template'] = 'true' if is_from_template else 'false'
                session['similarity_score'] = data.get('similarity_score', 0)
                print(f"DEBUG - Session data: from_template={session['from_template']}, similarity_score={session['similarity_score']}")
            except Exception as e:
                print(f"DEBUG - Error parsing JSON in proxy: {e}")
                pass
        
        # Return the API response
        return (
            response.content, 
            response.status_code, 
            {'Content-Type': response.headers.get('Content-Type', 'application/json')}
        )
    except requests.RequestException as e:
        print(f"DEBUG - Proxy error: {str(e)}")  # Debug log
        return jsonify({
            'error': f"Failed to connect to meme API: {str(e)}"
        }), 500
    except Exception as e:
        print(f"DEBUG - Unexpected error: {str(e)}")  # Debug log
        return jsonify({
            'error': f"Error processing request: {str(e)}"
        }), 500

# Import and register routes
from webapp.views import main
app.register_blueprint(main)

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8000))  # Use port 8000 for webapp
    
    print(f"Starting webapp on http://127.0.0.1:{port}")
    print(f"Template folder: {app.template_folder}")
    print(f"Static folder: {app.static_folder}")
    
    # Run the app
    app.run(debug=True, host="0.0.0.0", port=port) 