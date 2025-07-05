#!/usr/bin/env python3
"""
Web application routes for meme generation.
"""
import logging
from flask import request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import os
import time
import shutil
from pathlib import Path
import yaml
import sys
from tempfile import NamedTemporaryFile
import requests
from bot.twitter_notif import notify_meme_generated

# Add parent directory to sys.path to allow importing from other modules
sys.path.append(str(Path(__file__).parent.parent))
from ai_services.meme_service import MemeService
from ai_services.image_vector_db import ImageVectorDB
from utils import download_image_from_url

logger = logging.getLogger(__name__)

# Global service instances - initialized once at startup
_meme_service = None
_vector_db = None

def get_meme_service():
    """Get the global MemeService instance, initializing if needed."""
    global _meme_service
    if _meme_service is None:
        logger.info("Initializing MemeService (this may take a moment on first load)...")
        _meme_service = MemeService()
        logger.info("MemeService initialized successfully")
    return _meme_service

def get_vector_db():
    """Get the global ImageVectorDB instance, initializing if needed."""
    global _vector_db
    if _vector_db is None:
        logger.info("Initializing ImageVectorDB (this may take a moment on first load)...")
        _vector_db = ImageVectorDB()
        logger.info("ImageVectorDB initialized successfully")
    return _vector_db

def warmup_models():
    """Initialize all models during startup to avoid delays on first request."""
    try:
        logger.info("Starting model warmup...")
        
        # Initialize MemeService (loads OCR models)
        meme_service = get_meme_service()
        logger.info("MemeService initialized")
        
        # Initialize ImageVectorDB (loads CLIP model and vector database)
        vector_db = get_vector_db()
        logger.info("ImageVectorDB initialized")
        
        logger.info("Model warmup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Model warmup failed: {e}")
        return False

def fix_vector_db_path(old_path):
    """Fix old vector database paths to current project paths."""
    project_base = os.getenv('PROJECT_BASE_PATH', '/Users/krishnayadav/Documents/forgex/memezap/memezap-backend')
    
    # Replace old meme-generator paths with current project path
    if '/meme-generator/' in old_path:
        # Extract the relative path after meme-generator
        relative_path = old_path.split('/meme-generator/')[-1]
        new_path = os.path.join(project_base, relative_path)
        return new_path
    
    return old_path

def configure_routes(app):
    """Configure Flask routes."""
    # Use global service instance instead of creating new one
    meme_engine = get_meme_service()
    
    @app.route('/')
    def index():
        """Serve the main page."""
        return app.send_static_file('index.html')
    
    @app.route('/api/generate', methods=['POST'])
    def generate_meme():
        """Generate a meme from uploaded image."""
        try:
            # Check if request contains an image file or URL
            image_path = None
            
            if 'image' in request.files:
                # Handle file upload
                file = request.files['image']
                if file.filename == '':
                    return jsonify({'error': 'No selected file'}), 400
                
                # Create user_query_meme directory if it doesn't exist
                save_dir = Path(__file__).parent.parent / "data" / "user_query_meme"
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate timestamp filename with proper extension
                timestamp = str(int(time.time()))
                filename = secure_filename(file.filename)
                # Ensure proper extension
                ext = os.path.splitext(filename)[1].lower()
                if not ext:
                    ext = '.jpg'  # Default to jpg if no extension
                elif ext not in ['.jpg', '.jpeg', '.png']:
                    ext = '.jpg'  # Convert unsupported formats to jpg
                
                save_path = save_dir / f"{timestamp}{ext}"
                
                # Save the uploaded file
                file.save(save_path)
                image_path = str(save_path)
                
            elif 'image_url' in request.form:
                # Handle image URL
                image_url = request.form['image_url']
                if not image_url:
                    return jsonify({'error': 'No image URL provided'}), 400
                
                # Download image from URL to user_query_meme directory
                image_path = download_image_from_url(image_url)
            
            else:
                return jsonify({'error': 'No image or image URL provided'}), 400
            
            # Get caption from request or generate one
            caption = request.form.get('caption')
            caption_list = caption.split('|') if caption else []
            
            # First generate meme to a temporary path
            temp_output = meme_engine.generate_meme(image_path, caption_list)
            
            # Create user_response_meme directory if it doesn't exist
            response_dir = Path(__file__).parent.parent / "data" / "user_response_meme"
            response_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy the generated meme to user_response_meme directory with proper extension
            output_filename = f"response_{os.path.basename(image_path)}"
            if not output_filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                output_filename += '.jpg'
            output_path = str(response_dir / output_filename)
            
            # Copy the file
            shutil.copy2(temp_output, output_path)
            
            logger.info(f"Saved meme response to {output_path}")
            
            # Post Twitter notification asynchronously (non-blocking)
            try:
                import threading
                original_caption = caption if caption else "custom meme"
                
                def post_twitter_async():
                    try:
                        twitter_success = notify_meme_generated(
                            input_text=original_caption,
                            meme_image_path=output_path,
                            from_template=False,
                            similarity_score=0
                        )
                        if twitter_success:
                            logger.info("✅ Successfully posted promotional tweet about generated meme")
                        else:
                            logger.info("ℹ️ Twitter notification was not posted (disabled or failed)")
                    except Exception as twitter_error:
                        logger.error(f"Error posting Twitter notification: {twitter_error}")
                
                # Start Twitter posting in background thread
                twitter_thread = threading.Thread(target=post_twitter_async, daemon=True)
                twitter_thread.start()
                logger.info("🚀 Started Twitter notification in background")
                
            except Exception as e:
                logger.error(f"Error starting Twitter notification thread: {e}")
            
            # Return the generated meme
            return send_file(
                output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f"meme_{os.path.basename(image_path)}"
            )
            
        except Exception as e:
            logger.error(f"Error generating meme: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/smart_generate', methods=['POST'])
    def smart_generate_meme():
        """API endpoint for meme generation with similarity search and white box logic."""
        try:
            image_url = request.form.get('image_url')
            caption = request.form.get('caption', '')
            
            # Process the caption text carefully
            if caption:
                # Split by pipe character for top/bottom/middle text
                text_parts = [part.strip() for part in caption.split('|')]
                # Remove any empty strings from the list
                text_parts = [part for part in text_parts if part]
                
                # For template-based memes, we'll use just top and bottom texts
                top_text = text_parts[0] if text_parts else ""
                bottom_text = text_parts[1] if len(text_parts) > 1 else ""
                
                # Log what we received
                logger.info(f"Caption received: '{caption}'")
                logger.info(f"Parsed into {len(text_parts)} text parts")
            else:
                text_parts = []
                top_text = ""
                bottom_text = ""
                logger.info("No caption text provided")
            
            # Setup necessary directories
            project_root = Path(__file__).parent.parent
            user_query_dir = project_root / "data" / "user_query_meme"
            cleaned_image_dir = project_root / "data" / "cleaned_images"
            meme_templates_dir = project_root / "data" / "meme_templates"
            response_dir = project_root / "data" / "user_response_meme"
            
            # Ensure all directories exist
            for directory in [user_query_dir, cleaned_image_dir, meme_templates_dir, response_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamp for unique filenames
            timestamp = str(int(time.time()))
            
            # Download image locally if needed
            if image_url:
                # Download the image from S3 or remote URL
                resp = requests.get(image_url, stream=True)
                if resp.status_code == 200:
                    # Save to user_query_meme with timestamp
                    filename = f"{timestamp}_url_image.jpg"
                    local_image_path = str(user_query_dir / filename)
                    with open(local_image_path, 'wb') as f:
                        for chunk in resp.iter_content(1024):
                            f.write(chunk)
                else:
                    return jsonify({'error': 'Failed to download image from URL'}), 400
            elif 'image' in request.files:
                # Handle direct file upload
                file = request.files['image']
                filename = secure_filename(file.filename)
                local_image_path = str(user_query_dir / f"{timestamp}_{filename}")
                file.save(local_image_path)
            else:
                return jsonify({'error': 'No image provided'}), 400
            
            # Use global service instances (already loaded at startup)
            meme_service = get_meme_service()
            vector_db = get_vector_db()
            
            # First, clean any text from the image with confidence > 0.5
            logger.info(f"Cleaning text from image: {local_image_path}")
            original_filename = os.path.basename(local_image_path)
            cleaned_filename = f"cleaned_{original_filename}"
            cleaned_image_path = str(cleaned_image_dir / cleaned_filename)
            
            # Remove text and save to cleaned_images folder
            meme_service.remove_text_and_inpaint(
                local_image_path, 
                min_confidence=0.5,
                output_path=cleaned_image_path
            )
            logger.info(f"Text cleaned, saved to: {cleaned_image_path}")
            
            # Log the top 5 most similar images
            try:
                # Get top 5 similar images with scores using cleaned image
                top_results = vector_db.search_top_k(cleaned_image_path, k=5)
                print(top_results)
                logger.info("Top 5 similar images:")
                for i, (path, score) in enumerate(top_results):
                    logger.info(f"  Simailr image {i+1}. {path}: {score*100:.2f}%")
                
                # Use the top result if available and score is high enough
                if top_results and top_results[0][1] >= 0.8:
                    similar_path, similarity = top_results[0]
                    
                    # Fix path if it contains old project directory
                    if '/meme-generator/' in similar_path:
                        similar_path = fix_vector_db_path(similar_path)
                    
                    logger.info(f"Using top similar image: {similar_path} with score: {similarity*100:.2f}%")
                else:
                    similar_path = None
                    similarity = 0
                    logger.info(f"No template found with similarity >= 80%")
            except Exception as e:
                logger.warning(f"Error getting top 5 similar images: {e}")
                similar_path = None
                similarity = 0
            
            # Check if template was found
            if not similar_path or not os.path.exists(similar_path):
                logger.info(f"No template found in database.")
                
                # No template found - detect text in original image first
                logger.info(f"Detecting text bounding boxes from original image: {local_image_path}")
                text_results, _ = meme_service.detect_text(local_image_path)
                logger.info("Detected text regions:")
                for i, (bbox, text, confidence) in enumerate(text_results):
                    logger.info(f"Region {i+1}: '{text}', Confidence: {confidence:.2f}")
                    logger.info(f"Bounding box coordinates: {bbox}")
                
                if text_results:
                    # Text detected - use existing bounding boxes on cleaned image
                    logger.info(f"Found {len(text_results)} text regions in original image")
                    logger.info(f"Applying caption to cleaned image using detected bounding boxes")
                    
                    meme_path = meme_service.apply_text_to_template_with_bboxes(
                        template_path=cleaned_image_path,  # Use cleaned image as template
                        text_list=text_parts,             # Caption parts
                        bounding_boxes=text_results,      # Detected bounding boxes from original
                        source_image_path=local_image_path # Original image for reference
                    )
                    from_template = False
                    similarity = 0
                    logger.info(f"Applied {len(text_parts)} caption parts using detected bounding boxes")
                    
                else:
                    # No text detected - try OpenAI-generated bounding boxes
                    logger.info("No text detected in original image. Trying OpenAI-generated bounding boxes.")
                    
                    try:
                        logger.info("Attempting to generate bounding boxes using OpenAI")
                        
                        # Check if we have a similar template from the search (even if below 80% threshold)
                        if top_results and len(top_results) > 0:
                            # Use the most similar template found for OpenAI bounding box generation
                            template_for_ai = top_results[0][0]  # Best match template path
                            template_similarity = top_results[0][1]
                            
                            # Fix path if it contains old project directory
                            if '/meme-generator/' in template_for_ai:
                                template_for_ai = fix_vector_db_path(template_for_ai)
                            
                            logger.info(f"Using template from similarity search for OpenAI: {template_for_ai} (similarity: {template_similarity*100:.2f}%)")
                            
                            # Parsed text parts passed to OpenAI Vision API
                            ai_bounding_boxes = meme_service.generate_bounding_boxes_with_openai(
                                template_for_ai, text_parts  # Clean list of text parts
                            )
                            
                            if ai_bounding_boxes:
                                logger.info(f"Generated {len(ai_bounding_boxes)} bounding boxes using OpenAI Vision API with template")
                                
                                # Use the template directly with AI-generated bounding boxes (no rescaling)
                                meme_path = meme_service.apply_text_to_template_with_bboxes(
                                    template_path=template_for_ai,     # Use template found from similarity
                                    text_list=text_parts,             # Caption parts
                                    bounding_boxes=ai_bounding_boxes,  # AI-generated bounding boxes
                                    source_image_path=None            # No rescaling needed - boxes are for template
                                )
                                from_template = True  # We are using a template
                                similarity = template_similarity
                                logger.info(f"Applied {len(text_parts)} caption parts using AI-generated bounding boxes on template (no rescaling)")
                            else:
                                logger.warning("OpenAI Vision API failed to generate bounding boxes with template, using template with traditional method")
                                # Use template with traditional top/bottom text
                                meme_path = meme_service.generate_white_box_meme(
                                    template_for_ai, top_text, bottom_text
                                )
                                from_template = True
                                similarity = template_similarity
                                logger.info("Generated meme using traditional top/bottom text placement on template")
                        else:
                            # No template available, use cleaned image
                            logger.info("No template available from similarity search, using cleaned image")
                            ai_bounding_boxes = meme_service.generate_bounding_boxes_with_openai(
                                local_image_path, text_parts
                            )
                            
                            if ai_bounding_boxes:
                                logger.info(f"Generated {len(ai_bounding_boxes)} bounding boxes using OpenAI")
                                
                                # Use the cleaned image as template and apply AI-generated bounding boxes
                                meme_path = meme_service.apply_text_to_template_with_bboxes(
                                    template_path=cleaned_image_path,  # Use cleaned image as template
                                    text_list=text_parts,             # Caption parts
                                    bounding_boxes=ai_bounding_boxes,  # AI-generated bounding boxes
                                    source_image_path=local_image_path # Original image for reference
                                )
                                from_template = False
                                similarity = 0
                                logger.info(f"Applied {len(text_parts)} caption parts using AI-generated bounding boxes")
                            else:
                                logger.warning("OpenAI failed to generate bounding boxes, falling back to traditional method")
                                # Fallback to traditional method
                                meme_path = meme_service.generate_meme_from_clean(
                                    cleaned_image_path, text_parts
                                )
                                from_template = False
                                similarity = 0
                                logger.info("Generated meme using traditional top/bottom text placement")
                            
                    except Exception as e:
                        logger.warning(f"OpenAI bounding box generation failed: {e}")
                        # Fallback to traditional method
                        meme_path = meme_service.generate_meme_from_clean(
                            cleaned_image_path, text_parts
                        )
                        from_template = False
                        similarity = 0
                        logger.info("Generated meme using traditional top/bottom text placement")
            
            else:
                # Template found - proceed with existing logic
                logger.info(f"Found template: {similar_path}")
                
                # Detect text bounding boxes from original image I1
                logger.info(f"Detecting text bounding boxes from original image: {local_image_path}")
                text_results, _ = meme_service.detect_text(local_image_path)
                logger.info("Detected text regions:")
                for i, (bbox, text, confidence) in enumerate(text_results):
                    logger.info(f"Region {i+1}: '{text}', Confidence: {confidence:.2f}")
                    logger.info(f"Bounding box coordinates: {bbox}")
                
                if text_results:
                    # Case 1: Text detected in I1 - use bounding boxes B1 on template I2
                    logger.info(f"Found {len(text_results)} text regions in original image")
                    logger.info(f"Applying caption to template using detected bounding boxes")
                    
                    # Use custom method to apply text to template using bounding boxes from I1
                    meme_path = meme_service.apply_text_to_template_with_bboxes(
                        template_path=similar_path,  # I2 (template)
                        text_list=text_parts,       # Caption parts
                        bounding_boxes=text_results, # B1 (from I1)
                        source_image_path=local_image_path  # I1 (source image for scaling)
                    )
                    from_template = True
                    logger.info(f"Applied {len(text_parts)} caption parts to template using bounding boxes")
                    
                else:
                    # Case 2: No text detected in I1 - try OpenAI for template placement
                    logger.info("No text detected in original image. Trying OpenAI-generated bounding boxes for template.")
                    
                    try:
                        logger.info("Attempting to generate bounding boxes using OpenAI for template")
                        ai_bounding_boxes = meme_service.generate_bounding_boxes_with_openai(
                            similar_path, text_parts  # Use parsed text parts instead of raw caption
                        )
                        
                        if ai_bounding_boxes:
                            logger.info(f"Generated {len(ai_bounding_boxes)} bounding boxes using OpenAI for template")
                            
                            # Use template with AI-generated bounding boxes (no rescaling)
                            meme_path = meme_service.apply_text_to_template_with_bboxes(
                                template_path=similar_path,       # Template image
                                text_list=text_parts,             # Caption parts
                                bounding_boxes=ai_bounding_boxes, # AI-generated bounding boxes
                                source_image_path=None            # No rescaling needed - boxes are for template
                            )
                            from_template = True
                            logger.info(f"Applied {len(text_parts)} caption parts to template using AI-generated bounding boxes (no rescaling)")
                            
                        else:
                            logger.warning("OpenAI failed to generate bounding boxes for template, using traditional top/bottom")
                            # Fallback to traditional top/bottom on template
                            meme_path = meme_service.generate_white_box_meme(
                                similar_path, top_text, bottom_text
                            )
                            from_template = True
                            logger.info(f"Applied top/bottom text to template")
                            
                    except Exception as e:
                        logger.warning(f"OpenAI bounding box generation failed for template: {e}")
                        # Fallback to traditional top/bottom on template
                        meme_path = meme_service.generate_white_box_meme(
                            similar_path, top_text, bottom_text
                        )
                        from_template = True
                        logger.info(f"Applied top/bottom text to template")
            
            # Get the similarity score
            similarity_score = float(similarity * 100) if from_template else 0  # Convert to percentage
            
            # Copy the generated meme to user_response_meme directory
            output_filename = f"response_{os.path.basename(local_image_path)}"
            output_path = str(response_dir / output_filename)
            
            # Copy the file
            shutil.copy2(meme_path, output_path)
            
            logger.info(f"Saved meme response to {output_path}")
            
            # Return response with template info if requested via AJAX/JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                # Get relative path for web display
                rel_path = os.path.relpath(output_path, project_root)
                meme_url = f"/{rel_path.replace(os.sep, '/')}"
                
                # Print debug info
                print(f"DEBUG - Returning template info in JSON response: from_template={from_template}, similarity_score={similarity_score}")
                
                # Post Twitter notification asynchronously (non-blocking)
                try:
                    import threading
                    original_caption = caption if caption else "custom meme"
                    
                    def post_twitter_async():
                        try:
                            twitter_success = notify_meme_generated(
                                input_text=original_caption,
                                meme_image_path=output_path,
                                from_template=from_template,
                                similarity_score=similarity_score
                            )
                            if twitter_success:
                                logger.info("✅ Successfully posted promotional tweet about generated meme")
                            else:
                                logger.info("ℹ️ Twitter notification was not posted (disabled or failed)")
                        except Exception as twitter_error:
                            logger.error(f"Error posting Twitter notification: {twitter_error}")
                    
                    # Start Twitter posting in background thread
                    twitter_thread = threading.Thread(target=post_twitter_async, daemon=True)
                    twitter_thread.start()
                    logger.info("🚀 Started Twitter notification in background")
                    
                except Exception as e:
                    logger.error(f"Error starting Twitter notification thread: {e}")
                
                return jsonify({
                    'meme_url': meme_url, 
                    'from_template': from_template,
                    'similarity_score': similarity_score
                })
            
            # For file download requests, also post Twitter notification asynchronously
            try:
                import threading
                original_caption = caption if caption else "custom meme"
                
                def post_twitter_async():
                    try:
                        twitter_success = notify_meme_generated(
                            input_text=original_caption,
                            meme_image_path=output_path,
                            from_template=from_template,
                            similarity_score=similarity_score
                        )
                        if twitter_success:
                            logger.info("✅ Successfully posted promotional tweet about generated meme")
                        else:
                            logger.info("ℹ️ Twitter notification was not posted (disabled or failed)")
                    except Exception as twitter_error:
                        logger.error(f"Error posting Twitter notification: {twitter_error}")
                
                # Start Twitter posting in background thread
                twitter_thread = threading.Thread(target=post_twitter_async, daemon=True)
                twitter_thread.start()
                logger.info("🚀 Started Twitter notification in background")
                
            except Exception as e:
                logger.error(f"Error starting Twitter notification thread: {e}")
            
            # Otherwise return the file directly
            return send_file(
                output_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name=f"meme_{os.path.basename(local_image_path)}"
            )
        except Exception as e:
            logger.error(f"Error generating smart meme: {e}", exc_info=True)
            return jsonify({'error': f'Error generating meme: {str(e)}'}), 500
   