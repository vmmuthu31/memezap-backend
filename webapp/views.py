"""
Views for the web application.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import requests
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for, 
    flash, request, jsonify, current_app, session, send_file, abort
)
import werkzeug.utils
import shutil

from .forms import MemeForm, ChatForm
from utils import upload_image_to_s3
import sys

# Add parent directory to path to import from other modules
sys.path.append(str(Path(__file__).parent.parent))

# Import enhanced AI services
from ai_services.template_service import TemplateService
from ai_services.trend_service import TrendService
from ai_services.persona_service import PersonaService
from ai_services.roast_service import RoastMeService
from ai_services.trendzombie_service import TrendZombieService

logger = logging.getLogger(__name__)

# Create blueprint
main = Blueprint('main', __name__)

# Initialize AI services
template_service = TemplateService()
trend_service = TrendService()
persona_service = PersonaService()
roast_service = RoastMeService()
trendzombie_service = TrendZombieService()

# Default API URL when running locally
DEFAULT_API_URL = "http://localhost:8000/api/generate"

def get_api_url():
    """Get the configured API URL from environment or use the default."""
    meme_api_port = os.environ.get('MEME_API_PORT', '8001')
    return f"http://localhost:{meme_api_port}/api/generate"

def save_image_from_response(response, directory):
    """
    Save image from response to specified directory
    
    Args:
        response: Response object from requests
        directory: Directory to save image to
        
    Returns:
        Path to saved image
    """
    # Create directory if it doesn't exist
    Path(directory).mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}.jpg"
    save_path = os.path.join(directory, filename)
    
    # Save image content
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    logger.info(f"Saved image to {save_path}")
    return save_path

@main.route('/', methods=['GET', 'POST'])
def index():
    """Render the main page with enhanced meme generator."""
    form = MemeForm()
    
    # Get trending suggestions for the homepage
    trending_suggestions = []
    try:
        trending_suggestions = trend_service.generate_meme_suggestions_from_trends(limit=3)
    except Exception as e:
        logger.error(f"Error getting trending suggestions: {e}")
    
    # Get trending templates
    trending_templates = []
    try:
        trending_templates = template_service.get_trending_templates(limit=6)
    except Exception as e:
        logger.error(f"Error getting trending templates: {e}")
    
    if form.validate_on_submit():
        # Process the form data here
        if form.image.data:
            # Get the uploaded file
            uploaded_file = form.image.data
            
            # Create a safe filename
            filename = werkzeug.utils.secure_filename(uploaded_file.filename)
            
            # Create temp directory for uploads if it doesn't exist
            user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
            user_query_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file temporarily with a unique name
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            original_path = user_query_dir / unique_filename
            uploaded_file.save(original_path)
            
            logger.info(f"Saved original image to {original_path}")
            
            # Try template recognition first
            template_info = None
            try:
                template_info = template_service.identify_template(str(original_path))
                if template_info:
                    logger.info(f"Template detected: {template_info['template_name']}")
                    flash(f"🎯 Template detected: {template_info['template_name']}", "info")
            except Exception as e:
                logger.error(f"Error in template recognition: {e}")
            
            # Upload to S3 and get URL
            image_url = upload_image_to_s3(original_path)
            
            if not image_url:
                flash("Failed to upload image. Please try again.", "error")
                return redirect(url_for('main.index'))
            
            # Collect text from the form
            top_text = form.top_text.data or ""
            bottom_text = form.bottom_text.data or ""
            additional_text = form.additional_text.data or ""
            
            # Combine all text parts with pipe separator for API
            caption = "|".join(filter(None, [top_text, bottom_text, additional_text]))
            
            # Generate AI suggestions if no text provided
            if not caption and template_info:
                try:
                    ai_suggestions = template_service.suggest_captions_for_template(template_info)
                    if ai_suggestions:
                        caption = ai_suggestions[0]  # Use first suggestion
                        flash(f"💡 AI suggested: {caption}", "info")
                except Exception as e:
                    logger.error(f"Error generating AI suggestions: {e}")
            
            try:
                # Call the enhanced meme generation API
                api_url = request.host_url.rstrip('/') + get_api_url()
                
                payload = {
                    'image_url': image_url,
                    'caption': caption
                }
                
                # Add template info if available
                if template_info:
                    payload['template_id'] = template_info.get('template_id')
                    payload['template_name'] = template_info.get('template_name')
                
                response = requests.post(api_url, data=payload, timeout=30)
                
                if response.status_code == 200:
                    # Create user_response_meme directory if it doesn't exist
                    user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                    user_response_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Try to parse JSON response to get template info
                    try:
                        content_type = response.headers.get('Content-Type', '')
                        if 'application/json' in content_type:
                            resp_data = response.json()
                            is_from_template = resp_data.get('from_template', False)
                            session['from_template'] = 'true' if is_from_template else 'false'
                            session['similarity_score'] = resp_data.get('similarity_score', 0)
                            logger.info(f"Meme source info: from_template={session['from_template']}, similarity={session['similarity_score']}")
                        else:
                            # Not a JSON response, use default values
                            session['from_template'] = 'false'
                            session['similarity_score'] = 0
                            logger.info("Response is not JSON, setting default values")
                    except Exception as e:
                        # Error parsing JSON
                        session['from_template'] = 'false'
                        session['similarity_score'] = 0
                        logger.warning(f"Error parsing JSON response: {e}")
                    
                    # Save the generated meme
                    result_path = save_image_from_response(
                        response, 
                        str(user_response_dir)
                    )
                    
                    # Instead of using the remote URL, use the local file path for display
                    if result_path:
                        # Convert to relative path for use in templates
                        rel_path = os.path.relpath(result_path, Path(__file__).parent.parent)
                        session['last_meme_url'] = f"/{rel_path.replace(os.sep, '/')}"
                        
                        # Update user persona if session has user info
                        user_id = session.get('user_id', 'anonymous')
                        try:
                            persona_service.analyze_meme_interaction(user_id, {
                                'text': caption,
                                'template': template_info['template_name'] if template_info else 'custom',
                                'id': f"web_{int(datetime.now().timestamp())}"
                            }, 'created')
                        except Exception as e:
                            logger.error(f"Error updating persona: {e}")
                        
                        flash("Meme generated successfully! 🎭✨", "success")
                    else:
                        # Fallback to response URL if local save failed
                        session['last_meme_url'] = response.url
                        flash("Meme generated successfully, but couldn't save locally.", "warning")
                else:
                    flash(f"Error generating meme: {response.text}", "error")
            
            except Exception as e:
                logger.error(f"Error calling meme API: {e}")
                flash(f"Error: {str(e)}", "error")
        else:
            flash("Please upload an image to generate a meme.", "warning")
            
        return redirect(url_for('main.index'))
    
    return render_template('index.html', 
                         form=form, 
                         last_meme_url=session.get('last_meme_url'),
                         trending_suggestions=trending_suggestions,
                         trending_templates=trending_templates)

@main.route('/roast-me', methods=['GET', 'POST'])
def roast_me():
    """RoastMe AI feature page."""
    form = MemeForm()
    roast_result = None
    
    if form.validate_on_submit() and form.image.data:
        # Process the uploaded image
        uploaded_file = form.image.data
        filename = werkzeug.utils.secure_filename(uploaded_file.filename)
        
        # Create temp directory
        temp_dir = Path(__file__).parent.parent / "data" / "temp_roast"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Save temporarily
        unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
        temp_path = temp_dir / unique_filename
        uploaded_file.save(temp_path)
        
        try:
            # Get roast intensity from form or default to medium
            intensity = request.form.get('roast_intensity', 'medium')
            
            # Generate roast
            roast_result = roast_service.generate_roast(str(temp_path), intensity)
            
            # Clean up temp file
            temp_path.unlink()
            
            flash(f"🔥 Roast generated with {intensity} intensity!", "success")
            
        except Exception as e:
            logger.error(f"Error generating roast: {e}")
            flash("Error generating roast. Please try again.", "error")
            if temp_path.exists():
                temp_path.unlink()
    
    return render_template('roast_me.html', form=form, roast_result=roast_result)

@main.route('/trending-memes')
def trending_memes():
    """Trending memes page with AI suggestions."""
    try:
        # Get trending suggestions
        trending_suggestions = trend_service.generate_meme_suggestions_from_trends(limit=10)
        
        # Get trend analytics (if available)
        trend_analytics = {}
        try:
            if hasattr(trend_service, 'get_trend_analytics'):
                trend_analytics = trend_service.get_trend_analytics()
        except Exception as e:
            logger.error(f"Error getting trend analytics: {e}")
        
        return render_template('trending_memes.html',
                             trending_suggestions=trending_suggestions,
                             trend_analytics=trend_analytics)
        
    except Exception as e:
        logger.error(f"Error loading trending memes: {e}")
        flash("Error loading trending content. Please try again.", "error")
        return render_template('trending_memes.html',
                             trending_suggestions=[],
                             trend_analytics={})

@main.route('/persona-analyzer')
def persona_analyzer():
    """Persona analyzer page."""
    user_id = session.get('user_id', 'anonymous')
    
    try:
        # Get user persona
        persona = persona_service.get_user_persona(user_id)
        
        # Generate personalized suggestions
        personalized_suggestions = []
        if persona:
            personalized_suggestions = persona_service.generate_personalized_suggestions(user_id)
        
        return render_template('persona_analyzer.html',
                             persona=persona,
                             personalized_suggestions=personalized_suggestions)
        
    except Exception as e:
        logger.error(f"Error loading persona: {e}")
        return render_template('persona_analyzer.html',
                             persona=None,
                             personalized_suggestions=[])

@main.route('/template-gallery')
def template_gallery():
    """Template gallery page."""
    try:
        # Get trending templates
        trending_templates = template_service.get_trending_templates(limit=20)
        
        # Search templates if query provided
        search_query = request.args.get('search', '')
        search_results = []
        if search_query:
            search_results = template_service.search_templates(search_query, limit=10)
        
        return render_template('template_gallery.html',
                             trending_templates=trending_templates,
                             search_results=search_results,
                             search_query=search_query)
        
    except Exception as e:
        logger.error(f"Error loading template gallery: {e}")
        flash("Error loading templates. Please try again.", "error")
        return render_template('template_gallery.html',
                             trending_templates=[],
                             search_results=[],
                             search_query='')

@main.route('/api/template-suggestions', methods=['POST'])
def api_template_suggestions():
    """API endpoint for getting template suggestions."""
    try:
        data = request.get_json()
        template_name = data.get('template_name', '')
        user_text = data.get('user_text', '')
        
        # Get template info
        templates = template_service.search_templates(template_name, limit=1)
        if not templates:
            return jsonify({'error': 'Template not found'}), 404
        
        template_info = templates[0]
        
        # Generate suggestions
        suggestions = template_service.suggest_captions_for_template(template_info, user_text)
        
        return jsonify({
            'suggestions': suggestions,
            'template_info': template_info
        })
        
    except Exception as e:
        logger.error(f"Error getting template suggestions: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/trending-now')
def api_trending_now():
    """API endpoint for current trending topics."""
    try:
        trends = trend_service.get_trending_topics()
        
        # Filter for high meme potential
        meme_worthy_trends = [t for t in trends if t.get('meme_potential', 0) > 0.5]
        
        return jsonify({
            'trends': meme_worthy_trends[:10],
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting trending topics: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/persona-update', methods=['POST'])
def api_persona_update():
    """API endpoint for updating user persona."""
    try:
        data = request.get_json()
        user_id = session.get('user_id', 'anonymous')
        
        meme_data = data.get('meme_data', {})
        interaction_type = data.get('interaction_type', 'created')
        
        # Update persona
        updated_persona = persona_service.analyze_meme_interaction(user_id, meme_data, interaction_type)
        
        return jsonify({
            'status': 'success',
            'persona': updated_persona
        })
        
    except Exception as e:
        logger.error(f"Error updating persona: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/chat', methods=['GET', 'POST'])
def chat():
    """Render chat interface."""
    form = ChatForm()
    
    # Initialize chat history in session if not present
    if 'chat_history' not in session:
        session['chat_history'] = []
    
    if form.validate_on_submit():
        message = form.message.data
        image_url = None
        original_path = None
        
        # Handle image upload
        if form.image.data:
            # Get the uploaded file
            uploaded_file = form.image.data
            
            # Create a safe filename
            filename = werkzeug.utils.secure_filename(uploaded_file.filename)
            
            # Create user_query_meme directory if it doesn't exist
            user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
            user_query_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the file with a unique name
            unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
            original_path = user_query_dir / unique_filename
            uploaded_file.save(original_path)
            
            logger.info(f"Saved original image to {original_path}")
            
            # Upload to S3 and get URL
            image_url = upload_image_to_s3(original_path)
            
            if not image_url:
                flash("Failed to upload image. Please try again.", "error")
                return redirect(url_for('main.chat'))
        
        # Add message to chat history
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_message = {
            'user': True,
            'text': message,
            'image': image_url,
            'timestamp': timestamp
        }
        
        # Add user message to history
        chat_history = session.get('chat_history', [])
        chat_history.append(chat_message)
        
        # If image is present, call the meme generation API
        if image_url:
            try:
                # Use the API endpoint
                api_url = request.host_url.rstrip('/') + get_api_url()
                
                payload = {
                    'image_url': image_url,
                    'caption': message
                }
                
                response = requests.post(api_url, data=payload, timeout=30)
                
                if response.status_code == 200:
                    # Create user_response_meme directory if it doesn't exist
                    user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                    user_response_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save the generated meme
                    result_path = save_image_from_response(
                        response, 
                        str(user_response_dir)
                    )
                    
                    # Use local file path if available, otherwise use response URL
                    image_path = None
                    if result_path:
                        # Convert to relative path for use in templates
                        rel_path = os.path.relpath(result_path, Path(__file__).parent.parent)
                        image_path = f"/{rel_path.replace(os.sep, '/')}"
                    else:
                        image_path = response.url
                    
                    # Add bot response to chat history
                    meme_response = {
                        'user': False,
                        'text': "Here's your meme!",
                        'image': image_path,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    chat_history.append(meme_response)
                else:
                    # Add error response
                    error_response = {
                        'user': False,
                        'text': f"Sorry, I couldn't generate a meme. Error: {response.text}",
                        'image': None,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    chat_history.append(error_response)
                    
            except Exception as e:
                logger.error(f"Error calling meme API: {e}")
                error_response = {
                    'user': False,
                    'text': "Sorry, something went wrong when generating your meme.",
                    'image': None,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                chat_history.append(error_response)
        else:
            # Simple text response if no image
            text_response = {
                'user': False,
                'text': "Please upload an image to generate a meme!",
                'image': None,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            chat_history.append(text_response)
        
        # Update session
        session['chat_history'] = chat_history
        
        return redirect(url_for('main.chat'))
    
    return render_template('chat.html', form=form, chat_history=session.get('chat_history', []))

@main.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chat messages."""
    data = request.json
    
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400
    
    message = data['message']
    image_url = data.get('image_url')
    
    # Process the message and image here
    # This would typically involve calling your meme generator
    
    response = {
        'success': True,
        'message': 'Received your message!',
        'timestamp': datetime.now().isoformat()
    }
    
    if image_url:
        # Call the meme generation API
        try:
            # Use the API endpoint
            api_url = request.host_url.rstrip('/') + get_api_url()
            
            payload = {
                'image_url': image_url,
                'caption': message
            }
            
            meme_response = requests.post(api_url, data=payload, timeout=30)
            
            if meme_response.status_code == 200:
                # Create user_response_meme directory if it doesn't exist
                user_response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
                user_response_dir.mkdir(parents=True, exist_ok=True)
                
                # Save the generated meme
                result_path = save_image_from_response(
                    meme_response, 
                    str(user_response_dir)
                )
                
                if result_path:
                    # Convert to relative path for use in API response
                    rel_path = os.path.relpath(result_path, Path(__file__).parent.parent)
                    response['meme_url'] = f"/{rel_path.replace(os.sep, '/')}"
                else:
                    response['meme_url'] = meme_response.url
            else:
                response['error'] = f"Failed to generate meme: {meme_response.text}"
                
        except Exception as e:
            logger.error(f"Error calling meme API: {e}")
            response['error'] = str(e)
    
    return jsonify(response)

@main.route('/clear-chat', methods=['POST'])
def clear_chat():
    """Clear the chat history."""
    session.pop('chat_history', None)
    return redirect(url_for('main.chat'))

@main.route('/clear-meme-session', methods=['POST'])
def clear_meme_session():
    """Clear meme-related session data"""
    session.pop('last_meme_url', None)
    session.pop('from_template', None)
    session.pop('similarity_score', None)
    session.pop('selected_template_id', None)
    session.pop('selected_template_name', None)
    session.pop('selected_template_url', None)
    return jsonify({'status': 'success'})

@main.route('/meme-generator', methods=['GET', 'POST'])
def meme_generator():
    """Meme generator page"""
    form = MemeForm()
    last_meme_url = session.get('last_meme_url')  # Get last meme URL from session
    
    # Handle template parameters from URL
    template_id = request.args.get('template_id')
    template_name = request.args.get('template_name')
    template_url = None
    
    # If template parameters are provided, get the template URL
    if template_id and template_name and template_id.strip():
        try:
            # Get template info from template service
            template_info = template_service.get_template_by_id(template_id)
            if template_info:
                template_url = template_info.get('url')
                # Store template info in session for form processing
                session['selected_template_id'] = template_id
                session['selected_template_name'] = template_name
                session['selected_template_url'] = template_url
                logger.info(f"Template selected: {template_name} (ID: {template_id})")
        except Exception as e:
            logger.error(f"Error loading template {template_id}: {e}")
    elif template_name and template_name.strip():
        # If we have template name but no ID, try to find it by name
        try:
            # Search for template by name
            search_results = template_service.search_templates(template_name, limit=1)
            if search_results:
                template_info = search_results[0]
                template_id = template_info.get('id') or template_info.get('template_id')
                template_url = template_info.get('url')
                if template_id and template_url:
                    session['selected_template_id'] = template_id
                    session['selected_template_name'] = template_name
                    session['selected_template_url'] = template_url
                    logger.info(f"Template found by name: {template_name} (ID: {template_id})")
        except Exception as e:
            logger.error(f"Error searching template by name {template_name}: {e}")
    
    if request.method == 'POST':
        # Manual validation and form handling
        if not form.csrf_token.validate(form):
            flash('Security validation failed. Please try again.', 'error')
            return redirect(url_for('main.meme_generator'))
        
        # Check if we have either a template or uploaded file
        has_template = session.get('selected_template_id') and session.get('selected_template_url')
        has_file = form.image.data and form.image.data.filename
        
        if not has_template and not has_file:
            flash('Please upload an image or select a template from the gallery.', 'error')
            return redirect(url_for('main.meme_generator'))
        
        # Validate file if uploaded
        if has_file:
            if not form.image.validate(form):
                flash('Invalid image file. Please upload JPG, PNG, GIF, or WebP files only.', 'error')
                return redirect(url_for('main.meme_generator'))
        
        # Handle form submission
        try:
            # Prepare form data
            top_text = form.top_text.data or ''
            bottom_text = form.bottom_text.data or ''
            additional_text = form.additional_text.data or ''
            
            # Combine all text parts with pipe separator for API
            caption = "|".join(filter(None, [top_text, bottom_text, additional_text]))
            
            # Check if we have a template selected
            has_template = session.get('selected_template_id') and session.get('selected_template_url')
            
            if has_template and not form.image.data:
                # Template-only generation (no uploaded file)
                api_url = f"http://localhost:{os.environ.get('MEME_API_PORT', '8001')}/api/smart_generate"
                
                form_data = {
                    'image_url': session.get('selected_template_url'),
                    'caption': caption,
                    'template_id': session.get('selected_template_id'),
                    'template_name': session.get('selected_template_name')
                }
                
                logger.info(f"Generating meme from template: {session.get('selected_template_name')}")
                response = requests.post(api_url, data=form_data, headers={'X-Requested-With': 'XMLHttpRequest'}, timeout=30)
                
            elif form.image.data:
                # File upload generation (with or without template)
                uploaded_file = form.image.data
                filename = werkzeug.utils.secure_filename(uploaded_file.filename)
                
                # Create temp directory for uploads if it doesn't exist
                user_query_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
                user_query_dir.mkdir(parents=True, exist_ok=True)
                
                # Save the file temporarily with a unique name
                unique_filename = f"{int(datetime.now().timestamp())}_{filename}"
                original_path = user_query_dir / unique_filename
                uploaded_file.save(original_path)
                
                logger.info(f"Saved uploaded image to {original_path}")
                
                # Upload to S3 and get URL
                image_url = upload_image_to_s3(original_path)
                
                if not image_url:
                    flash("Failed to upload image. Please try again.", "error")
                    return redirect(url_for('main.meme_generator'))
                
                # Use smart generation API for better results
                api_url = f"http://localhost:{os.environ.get('MEME_API_PORT', '8001')}/api/smart_generate"
                
                form_data = {
                    'image_url': image_url,
                    'caption': caption
                }
                
                # Add template info if available (for comparison)
                if has_template:
                    form_data['template_id'] = session.get('selected_template_id')
                    form_data['template_name'] = session.get('selected_template_name')
                
                logger.info(f"Generating meme from uploaded file with caption: {caption}")
                response = requests.post(api_url, data=form_data, headers={'X-Requested-With': 'XMLHttpRequest'}, timeout=30)
                
            else:
                flash("Please upload an image or select a template.", "error")
                return redirect(url_for('main.meme_generator'))
            
            if response.status_code == 200:
                # Handle the response based on content type
                content_type = response.headers.get('Content-Type', '')
                
                if 'application/json' in content_type:
                    # JSON response with meme URL
                    data = response.json()
                    meme_url = data.get('meme_url')
                    
                    if meme_url:
                        # Convert relative URL to absolute path for local serving
                        if meme_url.startswith('/'):
                            # Remove any leading /data prefix since serve_data_file will handle it
                            last_meme_url = meme_url.replace('/data/', '/')
                        else:
                            last_meme_url = f"/{meme_url}"
                        
                        # Store session data
                        is_from_template = data.get('from_template', False)
                        session['from_template'] = 'true' if is_from_template else 'false'
                        session['similarity_score'] = data.get('similarity_score', 0)
                        session['last_meme_url'] = last_meme_url  # Store the URL in session
                        
                        flash('Meme generated successfully!', 'success')
                        logger.info(f"Meme generated successfully: {last_meme_url}")
                        
                        # Clear template selection after successful generation
                        session.pop('selected_template_id', None)
                        session.pop('selected_template_name', None)
                        session.pop('selected_template_url', None)
                        
                        # Redirect with generated parameter
                        return redirect(url_for('main.meme_generator', generated=True))
                    else:
                        flash('Failed to generate meme - no URL returned', 'error')
                        
                elif 'image/' in content_type:
                    # Direct image response - save and serve
                    user_response_dir = Path(__file__).parent.parent / 'data' / 'user_response_meme'
                    user_response_dir.mkdir(parents=True, exist_ok=True)
                    saved_image_path = save_image_from_response(response, str(user_response_dir))
                    
                    if saved_image_path:
                        # Convert to relative path for serving
                        rel_path = os.path.relpath(saved_image_path, Path(__file__).parent.parent)
                        last_meme_url = f"/{rel_path.replace(os.sep, '/')}"
                        
                        # Store the URL in session
                        session['last_meme_url'] = last_meme_url
                        
                        flash('Meme generated successfully!', 'success')
                        logger.info(f"Meme saved locally: {last_meme_url}")
                        
                        # Clear template selection after successful generation
                        session.pop('selected_template_id', None)
                        session.pop('selected_template_name', None)
                        session.pop('selected_template_url', None)
                        
                        # Redirect with generated parameter
                        return redirect(url_for('main.meme_generator', generated=True))
                    else:
                        flash('Failed to save generated meme', 'error')
                else:
                    flash('Unexpected response format from meme service', 'error')
            else:
                error_msg = f'Error generating meme: {response.status_code}'
                if response.text:
                    try:
                        error_data = response.json()
                        error_msg += f' - {error_data.get("error", response.text)}'
                    except:
                        error_msg += f' - {response.text}'
                flash(error_msg, 'error')
                logger.error(f"Meme generation failed: {error_msg}")
                
        except requests.RequestException as e:
            flash(f'Error connecting to meme service: {str(e)}', 'error')
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'error')
    
    # Get last meme URL from session
    last_meme_url = session.get('last_meme_url')
    logger.info(f"Rendering template with last_meme_url: {last_meme_url}")
    logger.info(f"Session data: {dict(session)}")
    
    return render_template('meme_generator.html', 
                         form=form, 
                         last_meme_url=last_meme_url,
                         template_id=template_id,
                         template_name=template_name,
                         template_url=template_url)

@main.route('/trendzombie')
def trendzombie():
    """TrendZombie - AI Meme Resurrector page."""
    try:
        # Get current trends
        trends = trend_service.get_trending_topics(refresh=False)
        
        # Get resurrected memes based on trends
        resurrected_memes = trendzombie_service.resurrect_memes_for_trends(trends, limit=6)
        
        # Get hall of fame
        hall_of_fame = trendzombie_service.get_zombie_hall_of_fame(limit=5)
        
        # Get resurrection stats
        stats = trendzombie_service.get_resurrection_stats()
        
        # Get available classic memes for custom resurrection
        classic_memes = trendzombie_service.classic_memes
        
        logger.info(f"TrendZombie: Found {len(resurrected_memes)} resurrected memes")
        
        return render_template('trendzombie.html', 
                             resurrected_memes=resurrected_memes,
                             hall_of_fame=hall_of_fame,
                             stats=stats,
                             classic_memes=classic_memes)
        
    except Exception as e:
        logger.error(f"Error in TrendZombie page: {e}")
        return render_template('trendzombie.html', 
                             resurrected_memes=[],
                             hall_of_fame=[],
                             stats={},
                             classic_memes=[])

@main.route('/api/resurrect-meme', methods=['POST'])
def api_resurrect_meme():
    """API endpoint to resurrect a specific meme with context."""
    try:
        data = request.get_json()
        meme_name = data.get('meme_name')
        context = data.get('context')
        
        if not meme_name or not context:
            return jsonify({'error': 'Both meme_name and context are required'}), 400
        
        # Create a mock trend for the context
        trend = {
            'id': f'custom_{context.replace(" ", "_")}',
            'name': context,
            'source': 'custom',
            'volume': 1000,
            'url': '',
            'timestamp': datetime.now().isoformat(),
            'meme_potential': 0.8,
            'description': f'Custom context: {context}'
        }
        
        # Find the classic meme
        classic_meme = None
        for meme in trendzombie_service.classic_memes:
            if meme['name'].lower() == meme_name.lower():
                classic_meme = meme
                break
        
        if not classic_meme:
            return jsonify({'error': f'Classic meme "{meme_name}" not found'}), 404
        
        # Resurrect the meme
        resurrection = trendzombie_service.resurrect_meme_for_trend(trend)
        
        if not resurrection:
            return jsonify({'error': 'Failed to resurrect meme'}), 500
        
        return jsonify({
            'success': True,
            'resurrection': resurrection
        })
        
    except Exception as e:
        logger.error(f"Error in resurrect meme API: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/trending-resurrections')
def api_trending_resurrections():
    """API endpoint to get trending meme resurrections."""
    try:
        # Get current trends
        trends = trend_service.get_trending_topics(refresh=False)
        
        # Get resurrected memes
        resurrected_memes = trendzombie_service.resurrect_memes_for_trends(trends, limit=10)
        
        return jsonify({
            'success': True,
            'resurrected_memes': resurrected_memes,
            'total_count': len(resurrected_memes)
        })
        
    except Exception as e:
        logger.error(f"Error getting trending resurrections: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/zombie-stats')
def api_zombie_stats():
    """API endpoint to get TrendZombie statistics."""
    try:
        stats = trendzombie_service.get_resurrection_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting zombie stats: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/analyze-persona', methods=['POST'])
def api_analyze_persona():
    """API endpoint to analyze user persona."""
    try:
        data = request.get_json()
        user_id = data.get('user_id', session.get('user_id', 'anonymous'))
        meme_data = data.get('meme_data', {})
        interaction_type = data.get('interaction_type', 'created')
        
        # Analyze the persona
        persona = persona_service.analyze_meme_interaction(user_id, meme_data, interaction_type)
        
        return jsonify({
            'success': True,
            'persona': persona
        })
        
    except Exception as e:
        logger.error(f"Error analyzing persona: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/get-persona/<user_id>')
def api_get_persona(user_id):
    """API endpoint to get user persona."""
    try:
        persona = persona_service.get_user_persona(user_id)
        
        if not persona:
            # Create a new persona
            persona = persona_service.create_user_persona(user_id)
        
        return jsonify({
            'success': True,
            'persona': persona
        })
        
    except Exception as e:
        logger.error(f"Error getting persona: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/api/persona-suggestions', methods=['POST'])
def api_persona_suggestions():
    """Get persona-based meme suggestions."""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'anonymous')
        
        # Get user's persona
        persona = persona_service.get_user_persona(user_id)
        
        if not persona:
            return jsonify({'error': 'No persona found for user'}), 404
        
        # Generate suggestions based on persona
        suggestions = persona_service.generate_persona_suggestions(persona)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'persona': persona
        })
        
    except Exception as e:
        logger.error(f"Error getting persona suggestions: {e}")
        return jsonify({'error': str(e)}), 500

@main.route('/data/<path:filename>')
def serve_data_file(filename):
    """Serve files from the data directory."""
    try:
        # Get absolute path to data directory
        data_dir = Path(__file__).parent.parent / 'data'
        
        # Clean the filename path to remove any double slashes or data prefixes
        clean_filename = filename.replace('/data/', '/').lstrip('/')
        file_path = data_dir / clean_filename
        
        # Security check - make sure file is within data directory
        if not str(file_path.resolve()).startswith(str(data_dir.resolve())):
            logger.error(f"Security violation - attempted to access file outside data directory: {filename}")
            abort(403)
        
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            abort(404)
        
        logger.info(f"Serving file: {file_path}")
        return send_file(file_path)
        
    except Exception as e:
        logger.error(f"Error serving data file {filename}: {e}")
        abort(500)