"""
RoastMe AI Service for MemeZap - Generates savage meme roasts from user photos
"""
import logging
import os
import base64
from pathlib import Path
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
import io
import requests

load_dotenv()

logger = logging.getLogger(__name__)

class RoastMeService:
    """Service for generating AI-powered meme roasts."""
    
    def __init__(self):
        """Initialize the RoastMeService."""
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Roast templates for different scenarios
        self.roast_templates = {
            "appearance": [
                "You look like {} got lost on their way to {}",
                "Someone ordered {} from Wish",
                "If {} had a discount version, it would be you",
                "You're giving off strong {} vibes but make it sad",
                "When {} said 'Be yourself,' they didn't mean this literally"
            ],
            "style": [
                "Your style is {} meets {} in a dark alley",
                "Fashion called - they want their {} back",
                "This outfit is giving {} energy but not in a good way",
                "When {} tries to be trendy",
                "Your vibe is {} but make it awkward"
            ],
            "general": [
                "You're proof that {} can happen to anyone",
                "If {} was a person",
                "When mom says 'We have {} at home'",
                "This is why {} warnings exist",
                "You're like {} but with less confidence"
            ]
        }
        
        # Pop culture references for roasts
        self.pop_culture_refs = [
            "a Marvel character", "a Disney villain", "a Netflix original", 
            "a TikTok trend", "a Walmart brand", "a knockoff version",
            "a discontinued product", "a YouTube video", "a stock photo",
            "a random NPC", "a tutorial gone wrong", "a beta version",
            "a free trial", "a demo character", "a placeholder image"
        ]
    
    def generate_roast(self, image_path: str, roast_intensity: str = "medium") -> Dict:
        """
        Generate a savage meme roast based on a photo.
        
        Args:
            image_path: Path to the image to roast
            roast_intensity: "light", "medium", or "savage"
            
        Returns:
            Dictionary containing roast information
        """
        if not self.openai_client:
            return {
                "roast": "Sorry, I need my AI powers to roast you properly! 🤖",
                "meme_template": "Drake Pointing",
                "meme_caption": "Getting roasted by a human|Getting roasted by AI",
                "intensity": roast_intensity,
                "disclaimer": "All roasts are in good fun! 😄"
            }
        
        try:
            # Analyze the image first
            image_analysis = self.analyze_image_for_roast(image_path)
            
            # Generate the roast
            roast_text = self.generate_roast_text(image_analysis, roast_intensity)
            
            # Create meme suggestions
            meme_suggestions = self.generate_meme_suggestions(roast_text)
            
            return {
                "roast": roast_text,
                "meme_template": meme_suggestions.get("template", "Mocking SpongeBob"),
                "meme_caption": meme_suggestions.get("caption", roast_text),
                "intensity": roast_intensity,
                "image_analysis": image_analysis,
                "disclaimer": "All roasts are in good fun! 😄"
            }
            
        except Exception as e:
            logger.error(f"Error generating roast: {e}")
            return {
                "roast": "I'm too stunned to roast you right now! 😵",
                "meme_template": "Surprised Pikachu",
                "meme_caption": "When the AI is speechless",
                "intensity": roast_intensity,
                "disclaimer": "All roasts are in good fun! 😄"
            }
    
    def analyze_image_for_roast(self, image_path: str) -> Dict:
        """
        Analyze image to find roast-worthy elements.
        
        Args:
            image_path: Path to the image
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Convert image to base64
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Analyze with GPT-4 Vision
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a witty image analyst. Describe what you see in a humorous way, noting style, appearance, setting, and any amusing details. Be clever but not mean-spirited."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analyze this image and describe what you see in a humorous way. Focus on style, appearance, setting, and any amusing details. Be witty but not cruel."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "description": analysis,
                "has_person": "person" in analysis.lower() or "man" in analysis.lower() or "woman" in analysis.lower(),
                "has_style": any(word in analysis.lower() for word in ["outfit", "clothing", "style", "wearing", "shirt", "dress"]),
                "setting": "indoor" if any(word in analysis.lower() for word in ["room", "inside", "indoor"]) else "outdoor"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image for roast: {e}")
            return {
                "description": "A mysterious being that defies description",
                "has_person": True,
                "has_style": True,
                "setting": "unknown"
            }
    
    def generate_roast_text(self, image_analysis: Dict, intensity: str) -> str:
        """
        Generate roast text based on image analysis.
        
        Args:
            image_analysis: Image analysis results
            intensity: Roast intensity level
            
        Returns:
            Roast text
        """
        try:
            # Set intensity parameters
            intensity_prompts = {
                "light": "Create a playful, gentle roast that's more funny than harsh. Keep it wholesome.",
                "medium": "Create a clever roast that's funny and witty. A bit savage but not mean.",
                "savage": "Create a savage roast that's brutally funny. Go hard but keep it creative."
            }
            
            prompt = f"""
            Based on this image description: "{image_analysis['description']}"
            
            {intensity_prompts.get(intensity, intensity_prompts['medium'])}
            
            Create a meme-style roast that:
            1. Is clever and creative
            2. References internet culture
            3. Could work as a meme caption
            4. Is funny, not cruel
            5. Includes modern slang/references
            
            Make it one sentence that would go viral. Think of it as a meme caption.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral meme roaster. Create clever, funny roasts that would trend on social media."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.8
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating roast text: {e}")
            return "You're giving off main character energy... in a side quest."
    
    def generate_meme_suggestions(self, roast_text: str) -> Dict:
        """
        Generate meme template suggestions for the roast.
        
        Args:
            roast_text: The roast text
            
        Returns:
            Dictionary with meme suggestions
        """
        try:
            prompt = f"""
            For this roast: "{roast_text}"
            
            Suggest the best meme template and caption format that would make this roast go viral.
            
            Choose from popular templates like:
            - Drake Pointing (rejecting vs approving)
            - Distracted Boyfriend (choosing between options)
            - Mocking SpongeBob (mocking text)
            - Woman Yelling at Cat (confrontational)
            - Surprised Pikachu (shocked reaction)
            - This Is Fine (accepting disaster)
            
            Return JSON: {"template": "template_name", "caption": "formatted_caption"}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a meme template expert. Match roasts to viral meme formats."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.5
            )
            
            import json
            import re
            
            response_text = response.choices[0].message.content
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                return json.loads(json_match.group())
            
        except Exception as e:
            logger.error(f"Error generating meme suggestions: {e}")
        
        # Fallback suggestions
        return {
            "template": "Mocking SpongeBob",
            "caption": roast_text
        }
    
    def generate_roast_battle(self, image1_path: str, image2_path: str) -> Dict:
        """
        Generate a roast battle between two images.
        
        Args:
            image1_path: Path to first image
            image2_path: Path to second image
            
        Returns:
            Dictionary with roast battle results
        """
        try:
            # Analyze both images
            analysis1 = self.analyze_image_for_roast(image1_path)
            analysis2 = self.analyze_image_for_roast(image2_path)
            
            # Generate roasts for each
            roast1 = self.generate_roast_text(analysis1, "medium")
            roast2 = self.generate_roast_text(analysis2, "medium")
            
            # Determine winner (randomly for now, could be based on analysis)
            import random
            winner = random.choice([1, 2])
            
            return {
                "participant1": {
                    "roast": roast1,
                    "analysis": analysis1
                },
                "participant2": {
                    "roast": roast2,
                    "analysis": analysis2
                },
                "winner": winner,
                "battle_result": f"Participant {winner} wins this roast battle! 🔥",
                "disclaimer": "All roasts are in good fun! 😄"
            }
            
        except Exception as e:
            logger.error(f"Error generating roast battle: {e}")
            return {
                "error": "Roast battle failed - both participants were too powerful! 💥",
                "disclaimer": "All roasts are in good fun! 😄"
            }
    
    def get_roast_stats(self) -> Dict:
        """Get statistics about roast generation."""
        # In a real implementation, you'd track these metrics
        return {
            "total_roasts": 0,
            "intensity_breakdown": {
                "light": 0,
                "medium": 0,
                "savage": 0
            },
            "popular_templates": {
                "Mocking SpongeBob": 0,
                "Drake Pointing": 0,
                "Distracted Boyfriend": 0
            }
        } 