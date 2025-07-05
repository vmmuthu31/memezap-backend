"""
Template Service for MemeZap - Handles meme template recognition and suggestions
"""
import logging
import requests
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv
import time
import hashlib

load_dotenv()

logger = logging.getLogger(__name__)

class TemplateService:
    """Service for meme template recognition and management."""
    
    def __init__(self):
        """Initialize the TemplateService."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.templates_dir = self.data_dir / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Template sources
        self.imgflip_api_url = "https://api.imgflip.com/get_memes"
        self.template_cache_file = self.data_dir / "template_cache.json"
        
        # OpenAI client for AI-powered suggestions
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Template database
        self.templates = {}
        self.load_templates()
        
        # Popular meme templates with their characteristics
        self.popular_templates = {
            "drake": {
                "name": "Drake Pointing",
                "description": "Drake rejecting something (top) and approving something (bottom)",
                "template_id": "181913649",
                "text_positions": ["top", "bottom"],
                "categories": ["reaction", "comparison", "choice"]
            },
            "distracted_boyfriend": {
                "name": "Distracted Boyfriend",
                "description": "Man looking at another woman while his girlfriend looks disapproving",
                "template_id": "112126428",
                "text_positions": ["left", "center", "right"],
                "categories": ["relationship", "choice", "temptation"]
            },
            "woman_yelling_at_cat": {
                "name": "Woman Yelling at Cat",
                "description": "Woman pointing and yelling at a white cat sitting at a table",
                "template_id": "188390779",
                "text_positions": ["top", "bottom"],
                "categories": ["argument", "confrontation", "reaction"]
            },
            "expanding_brain": {
                "name": "Expanding Brain",
                "description": "Four panels showing brain getting bigger and more enlightened",
                "template_id": "93895088",
                "text_positions": ["level1", "level2", "level3", "level4"],
                "categories": ["evolution", "intelligence", "progression"]
            },
            "two_buttons": {
                "name": "Two Buttons",
                "description": "Person sweating over choosing between two buttons",
                "template_id": "87743020",
                "text_positions": ["button1", "button2"],
                "categories": ["decision", "difficult_choice", "stress"]
            }
        }
    
    def load_templates(self):
        """Load template database from cache or fetch from APIs."""
        try:
            if self.template_cache_file.exists():
                with open(self.template_cache_file, 'r') as f:
                    cached_data = json.load(f)
                    
                # Check if cache is less than 24 hours old
                cache_age = time.time() - cached_data.get('timestamp', 0)
                if cache_age < 86400:  # 24 hours
                    self.templates = cached_data.get('templates', {})
                    logger.info(f"Loaded {len(self.templates)} templates from cache")
                    return
            
            # Fetch fresh templates
            self.fetch_templates()
            
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
            self.templates = {}
    
    def fetch_templates(self):
        """Fetch templates from ImgFlip API."""
        try:
            logger.info("Fetching templates from ImgFlip API...")
            response = requests.get(self.imgflip_api_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                templates = {}
                for meme in data['data']['memes']:
                    templates[meme['id']] = {
                        'name': meme['name'],
                        'url': meme['url'],
                        'width': meme['width'],
                        'height': meme['height'],
                        'box_count': meme['box_count'],
                        'source': 'imgflip'
                    }
                
                # Save to cache
                cache_data = {
                    'timestamp': time.time(),
                    'templates': templates
                }
                with open(self.template_cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                
                self.templates = templates
                logger.info(f"Fetched and cached {len(templates)} templates from ImgFlip")
            else:
                logger.error(f"ImgFlip API error: {data.get('error_message', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error fetching templates: {e}")
    
    def identify_template(self, image_path: str, confidence_threshold: float = 0.3) -> Optional[Dict]:
        """
        Identify if an image matches a known meme template.
        
        Args:
            image_path: Path to the image to analyze
            confidence_threshold: Minimum confidence score to consider a match
            
        Returns:
            Dictionary with template info if match found, None otherwise
        """
        try:
            # For now, we'll use a simple approach based on image dimensions and characteristics
            # In a production system, you'd use more sophisticated computer vision
            
            image = Image.open(image_path)
            width, height = image.size
            aspect_ratio = width / height
            
            # Check against known template characteristics
            for template_id, template_info in self.templates.items():
                template_aspect_ratio = template_info['width'] / template_info['height']
                
                # Simple matching based on aspect ratio similarity
                ratio_diff = abs(aspect_ratio - template_aspect_ratio)
                if ratio_diff < 0.1:  # Allow 10% difference in aspect ratio
                    confidence = 1.0 - (ratio_diff * 10)  # Convert to confidence score
                    
                    if confidence >= confidence_threshold:
                        return {
                            'template_id': template_id,
                            'template_name': template_info['name'],
                            'template_url': template_info['url'],
                            'confidence': confidence,
                            'box_count': template_info['box_count'],
                            'source': template_info['source']
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error identifying template: {e}")
            return None
    
    def suggest_captions_for_template(self, template_info: Dict, user_text: str = "") -> List[str]:
        """
        Generate AI-powered caption suggestions for a specific template.
        
        Args:
            template_info: Template information dictionary
            user_text: Optional user-provided text for context
            
        Returns:
            List of suggested captions
        """
        if not self.openai_client:
            return self.get_fallback_captions(template_info['template_name'])
        
        try:
            template_name = template_info['template_name']
            
            # Get template context from popular templates
            template_context = ""
            for key, info in self.popular_templates.items():
                if info['name'].lower() in template_name.lower():
                    template_context = info['description']
                    break
            
            prompt = f"""
            Generate 4 witty, viral-worthy captions for the "{template_name}" meme template.
            
            Template context: {template_context}
            User context: {user_text}
            
            Guidelines:
            - Keep it relevant to current trends and culture
            - Make it relatable and funny
            - Use internet slang appropriately
            - Each caption should be different in style (sarcastic, wholesome, dark humor, etc.)
            - Format as pipe-separated text parts if the template has multiple text areas
            
            Return only the 4 captions, one per line, without numbering or formatting.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral meme caption generator. Create funny, relatable captions that would go viral on social media."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.8
            )
            
            captions = response.choices[0].message.content.strip().split('\n')
            captions = [caption.strip() for caption in captions if caption.strip()]
            
            logger.info(f"Generated {len(captions)} AI captions for template {template_name}")
            return captions
            
        except Exception as e:
            logger.error(f"Error generating AI captions: {e}")
            return self.get_fallback_captions(template_info['template_name'])
    
    def get_fallback_captions(self, template_name: str) -> List[str]:
        """
        Get fallback captions when AI generation fails.
        
        Args:
            template_name: Name of the template
            
        Returns:
            List of fallback captions
        """
        fallback_captions = {
            "drake": [
                "Using old methods | Using MemeZap AI",
                "Manual meme creation | AI-powered memes",
                "Spending hours on memes | MemeZap doing it in seconds",
                "Basic memes | Viral content with MemeZap"
            ],
            "distracted_boyfriend": [
                "Me | New AI meme tool | My old meme app",
                "Content creators | MemeZap | Traditional tools",
                "My productivity | MemeZap | Everything else",
                "Old meme formats | MemeZap templates | Boring content"
            ],
            "woman_yelling_at_cat": [
                "When you manually create memes | MemeZap creating them instantly",
                "Traditional meme tools | MemeZap's AI magic",
                "Spending money on designers | Getting memes for free",
                "Complex meme creation | Simple MemeZap interface"
            ]
        }
        
        # Match template name to fallback captions
        for key, captions in fallback_captions.items():
            if key in template_name.lower():
                return captions
        
        # Generic fallback
        return [
            "When life gives you lemons | Make memes with MemeZap",
            "Me trying to be productive | MemeZap distracting me with perfect memes",
            "Old way of doing things | MemeZap's AI revolution",
            "Basic content | Viral memes with MemeZap"
        ]
    
    def get_trending_templates(self, limit: int = 10) -> List[Dict]:
        """
        Get trending meme templates.
        
        Args:
            limit: Number of templates to return
            
        Returns:
            List of trending template dictionaries
        """
        try:
            # Sort templates by popularity metrics (for now, we'll use a simple approach)
            # In production, you'd track actual usage metrics
            popular_template_ids = [
                "181913649",  # Drake
                "112126428",  # Distracted Boyfriend
                "188390779",  # Woman Yelling at Cat
                "93895088",   # Expanding Brain
                "87743020",   # Two Buttons
                "124822590",  # Left Exit 12 Off Ramp
                "102156234",  # Mocking SpongeBob
                "131087935",  # Running Away Balloon
                "129242436",  # Change My Mind
                "217743513"   # UNO Draw 25 Cards
            ]
            
            trending = []
            for template_id in popular_template_ids[:limit]:
                if template_id in self.templates:
                    template_info = self.templates[template_id].copy()
                    template_info['template_id'] = template_id
                    template_info['id'] = template_id  # Add id field for template gallery
                    trending.append(template_info)
            
            return trending
            
        except Exception as e:
            logger.error(f"Error getting trending templates: {e}")
            return []
    
    def generate_template_variations(self, base_text: str, template_info: Dict) -> List[Dict]:
        """
        Generate multiple variations of a meme using the same template.
        
        Args:
            base_text: Base text to create variations from
            template_info: Template information
            
        Returns:
            List of meme variations
        """
        if not self.openai_client:
            return []
        
        try:
            template_name = template_info['template_name']
            
            prompt = f"""
            Create 3 different variations of a meme using the "{template_name}" template.
            Base idea: {base_text}
            
            For each variation, create a different style:
            1. Sarcastic/ironic version
            2. Wholesome/positive version  
            3. Dark humor/edgy version
            
            Format each as: STYLE: caption_text
            Keep captions short and punchy.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a creative meme variation generator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.9
            )
            
            variations = []
            lines = response.choices[0].message.content.strip().split('\n')
            
            for line in lines:
                if ':' in line:
                    style, caption = line.split(':', 1)
                    variations.append({
                        'style': style.strip(),
                        'caption': caption.strip(),
                        'template_id': template_info.get('template_id'),
                        'template_name': template_name
                    })
            
            return variations
            
        except Exception as e:
            logger.error(f"Error generating template variations: {e}")
            return []
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """
        Get template information by ID.
        
        Args:
            template_id: Template ID to look up
            
        Returns:
            Template information dictionary or None
        """
        return self.templates.get(template_id)
    
    def search_templates(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search templates by name or description.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching templates
        """
        try:
            query_lower = query.lower()
            matches = []
            
            # First, try exact and partial matches
            for template_id, template_info in self.templates.items():
                name = template_info['name'].lower()
                if query_lower in name:
                    match_info = template_info.copy()
                    match_info['template_id'] = template_id
                    match_info['id'] = template_id
                    # Calculate relevance score
                    match_info['relevance'] = 1.0 if name == query_lower else 0.8
                    matches.append(match_info)
            
            # If no matches, try semantic matching with popular keywords
            if not matches:
                keyword_mapping = {
                    'love': ['heart', 'couple', 'romance', 'boyfriend', 'girlfriend', 'valentine'],
                    'money': ['rich', 'broke', 'cash', 'dollar', 'stonks', 'investment'],
                    'work': ['job', 'office', 'boss', 'meeting', 'tired', 'monday'],
                    'school': ['student', 'teacher', 'exam', 'homework', 'college'],
                    'food': ['hungry', 'diet', 'eating', 'restaurant', 'cooking'],
                    'technology': ['computer', 'phone', 'internet', 'tech', 'ai', 'robot'],
                    'funny': ['joke', 'comedy', 'laugh', 'hilarious', 'humor'],
                    'sad': ['cry', 'depressed', 'upset', 'emotional', 'tears'],
                    'angry': ['mad', 'rage', 'furious', 'annoyed', 'frustrated'],
                    'happy': ['joy', 'smile', 'excited', 'celebration', 'party']
                }
                
                # Check if query matches any keyword category
                for category, keywords in keyword_mapping.items():
                    if query_lower in keywords or any(keyword in query_lower for keyword in keywords):
                        # Return popular templates that might fit
                        popular_ids = ["181913649", "112126428", "188390779", "93895088", "87743020"]
                        for template_id in popular_ids:
                            if template_id in self.templates and len(matches) < limit:
                                match_info = self.templates[template_id].copy()
                                match_info['template_id'] = template_id
                                match_info['id'] = template_id
                                match_info['relevance'] = 0.6
                                matches.append(match_info)
                        break
            
            # If still no matches, return some popular templates
            if not matches:
                popular_ids = ["181913649", "112126428", "188390779", "93895088", "87743020"]
                for template_id in popular_ids:
                    if template_id in self.templates and len(matches) < limit:
                        match_info = self.templates[template_id].copy()
                        match_info['template_id'] = template_id
                        match_info['id'] = template_id
                        match_info['relevance'] = 0.4
                        matches.append(match_info)
            
            # Sort by relevance
            matches.sort(key=lambda x: x['relevance'], reverse=True)
            
            return matches[:limit]
            
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return [] 