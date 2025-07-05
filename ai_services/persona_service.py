"""
Persona Service for MemeZap - Handles user persona analysis and memetic digital twin creation
"""
import logging
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import hashlib
from openai import OpenAI
from dotenv import load_dotenv
import re

load_dotenv()

logger = logging.getLogger(__name__)

class PersonaService:
    """Service for analyzing user personas and creating memetic digital twins."""
    
    def __init__(self):
        """Initialize the PersonaService."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.personas_dir = self.data_dir / "personas"
        self.personas_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAI client for AI-powered analysis
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Humor categories and meme types
        self.humor_categories = {
            "sarcastic": ["sarcasm", "irony", "deadpan", "dry humor"],
            "wholesome": ["wholesome", "positive", "uplifting", "heartwarming"],
            "dark": ["dark humor", "edgy", "controversial", "morbid"],
            "absurd": ["absurd", "surreal", "random", "wtf"],
            "relatable": ["relatable", "everyday", "mundane", "common"],
            "political": ["political", "current events", "social commentary"],
            "pop_culture": ["celebrities", "movies", "tv shows", "music"],
            "self_deprecating": ["self-roast", "self-aware", "humble", "modest"],
            "intellectual": ["smart", "clever", "witty", "sophisticated"],
            "cringe": ["cringe", "awkward", "uncomfortable", "secondhand embarrassment"]
        }
    
    def create_user_persona(self, user_id: str, initial_data: Dict = None) -> Dict:
        """Create a new user persona profile."""
        persona = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "humor_profile": {
                "primary_style": "unknown",
                "humor_scores": {category: 0.0 for category in self.humor_categories.keys()},
                "confidence": 0.0
            },
            "meme_preferences": {
                "preferred_formats": [],
                "topics_of_interest": [],
                "engagement_patterns": {}
            },
            "interaction_history": {
                "total_memes_created": 0,
                "recent_activity": [],
                "engagement_score": 0.0
            },
            "digital_twin": {
                "personality_traits": [],
                "communication_style": "",
                "prediction_accuracy": 0.0
            }
        }
        
        if initial_data:
            persona.update(initial_data)
        
        self.save_persona(persona)
        logger.info(f"Created persona for user {user_id}")
        return persona
    
    def analyze_meme_interaction(self, user_id: str, meme_data: Dict, interaction_type: str) -> Dict:
        """Analyze a user's meme interaction and update their persona."""
        persona = self.get_user_persona(user_id)
        if not persona:
            persona = self.create_user_persona(user_id)
        
        # Analyze the meme content
        meme_analysis = self.analyze_meme_content(meme_data)
        
        # Update interaction history
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "type": interaction_type,
            "meme_id": meme_data.get('id', 'unknown'),
            "analysis": meme_analysis
        }
        
        persona["interaction_history"]["recent_activity"].append(interaction)
        
        # Keep only last 100 interactions
        if len(persona["interaction_history"]["recent_activity"]) > 100:
            persona["interaction_history"]["recent_activity"] = persona["interaction_history"]["recent_activity"][-100:]
        
        # Update counters
        if interaction_type == "created":
            persona["interaction_history"]["total_memes_created"] += 1
        
        # Update humor profile based on meme analysis
        self.update_humor_profile(persona, meme_analysis)
        
        # Update digital twin
        self.update_digital_twin(persona)
        
        # Save updated persona
        persona["updated_at"] = datetime.now().isoformat()
        self.save_persona(persona)
        
        logger.info(f"Updated persona for user {user_id} with {interaction_type} interaction")
        return persona
    
    def analyze_meme_content(self, meme_data: Dict) -> Dict:
        """Analyze meme content to extract humor style and characteristics."""
        analysis = {
            "humor_categories": [],
            "meme_format": "unknown",
            "topics": [],
            "sentiment": "neutral",
            "complexity": 0.0,
            "originality": 0.0
        }
        
        if not self.openai_client:
            return analysis
        
        try:
            # Combine meme text for analysis
            meme_text = ""
            if "text" in meme_data:
                meme_text = meme_data["text"]
            elif "caption" in meme_data:
                meme_text = meme_data["caption"]
            elif "top_text" in meme_data and "bottom_text" in meme_data:
                meme_text = f"{meme_data['top_text']} {meme_data['bottom_text']}"
            
            if not meme_text:
                return analysis
            
            # Analyze with OpenAI
            prompt = f"""
            Analyze this meme text and provide a JSON response:
            {{
                "humor_categories": ["category1", "category2"],
                "meme_format": "format_type",
                "topics": ["topic1", "topic2"],
                "sentiment": "positive/negative/neutral",
                "complexity": 0.0-1.0,
                "originality": 0.0-1.0
            }}
            
            Meme text: "{meme_text}"
            
            Humor categories: {list(self.humor_categories.keys())}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a meme analysis expert. Provide accurate JSON responses."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
            
        except Exception as e:
            logger.error(f"Error analyzing meme content: {e}")
        
        return analysis
    
    def update_humor_profile(self, persona: Dict, meme_analysis: Dict):
        """Update user's humor profile based on meme analysis."""
        try:
            humor_categories = meme_analysis.get("humor_categories", [])
            
            # Update humor scores
            for category in humor_categories:
                if category in persona["humor_profile"]["humor_scores"]:
                    persona["humor_profile"]["humor_scores"][category] += 0.1
            
            # Determine primary style
            humor_scores = persona["humor_profile"]["humor_scores"]
            if humor_scores:
                primary_style = max(humor_scores.items(), key=lambda x: x[1])[0]
                persona["humor_profile"]["primary_style"] = primary_style
            
            # Update confidence based on number of interactions
            total_interactions = len(persona["interaction_history"]["recent_activity"])
            persona["humor_profile"]["confidence"] = min(total_interactions / 50.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error updating humor profile: {e}")
    
    def update_digital_twin(self, persona: Dict):
        """Update the user's digital twin based on their persona data."""
        try:
            primary_style = persona["humor_profile"]["primary_style"]
            
            # Generate personality traits
            trait_mapping = {
                "sarcastic": ["witty", "cynical", "sharp-tongued"],
                "wholesome": ["optimistic", "caring", "positive"],
                "dark": ["edgy", "provocative", "unconventional"],
                "absurd": ["creative", "unpredictable", "imaginative"],
                "relatable": ["down-to-earth", "authentic", "empathetic"]
            }
            
            persona["digital_twin"]["personality_traits"] = trait_mapping.get(primary_style, ["unique", "creative"])
            
            # Generate communication style
            communication_styles = {
                "sarcastic": "Uses dry wit and irony, often making clever observations",
                "wholesome": "Communicates with warmth and positivity, uplifting others",
                "dark": "Uses edgy humor and isn't afraid of controversial topics",
                "absurd": "Communicates in unexpected ways, often surreal and creative",
                "relatable": "Speaks authentically about everyday experiences"
            }
            
            persona["digital_twin"]["communication_style"] = communication_styles.get(
                primary_style, "Has a unique communication style"
            )
            
            # Update prediction accuracy
            total_memes = persona["interaction_history"]["total_memes_created"]
            if total_memes > 0:
                persona["digital_twin"]["prediction_accuracy"] = min(total_memes / 100.0, 1.0)
            
        except Exception as e:
            logger.error(f"Error updating digital twin: {e}")
    
    def generate_personalized_suggestions(self, user_id: str, context: str = "") -> List[Dict]:
        """Generate personalized meme suggestions based on user's humor profile."""
        try:
            persona = self.get_user_persona(user_id)
            
            if not persona:
                persona = self.create_user_persona(user_id)
            
            # If user has limited data, generate general suggestions
            if persona["interaction_history"]["total_memes_created"] < 3:
                return self.generate_default_suggestions(context)
            
            if not self.openai_client:
                return self.generate_fallback_suggestions(persona, context)
            
            # Get user's humor profile
            primary_style = persona["humor_profile"]["primary_style"]
            humor_scores = persona["humor_profile"]["humor_scores"]
            
            # Find top humor categories
            top_categories = sorted(humor_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            
            prompt = f"""
            Generate 4 personalized meme suggestions for a user with this humor profile:
            
            Primary Style: {primary_style}
            Top Categories: {[cat[0] for cat in top_categories]}
            Context: {context}
            
            For each suggestion, provide:
            {{
                "template": "meme template name",
                "caption": "meme caption text",
                "reason": "why this matches user's style",
                "match_score": confidence (0-100)
            }}
            
            Return as JSON array of 4 suggestions.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a meme personalization expert. Generate suggestions that match the user's specific humor style."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            
            # Parse JSON response
            response_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                suggestions = json.loads(json_match.group())
                return suggestions
            
            # Fallback if parsing fails
            return self.generate_fallback_suggestions(persona, context)
            
        except Exception as e:
            logger.error(f"Error generating personalized suggestions: {e}")
            return self.generate_default_suggestions(context)
    
    def generate_default_suggestions(self, context: str = "") -> List[Dict]:
        """Generate default suggestions for new users."""
        default_suggestions = [
            {
                "template": "Drake Pointing",
                "caption": "Old way of doing things | Using AI to do it better",
                "reason": "Classic format that works for everyone",
                "match_score": 85
            },
            {
                "template": "Distracted Boyfriend",
                "caption": "Me | My productivity | New meme generator",
                "reason": "Relatable procrastination humor",
                "match_score": 80
            },
            {
                "template": "This is Fine",
                "caption": "This is fine while using AI for everything",
                "reason": "Perfect for current tech trends",
                "match_score": 90
            },
            {
                "template": "Woman Yelling at Cat",
                "caption": "Traditional tools | MemeZap's AI magic",
                "reason": "Great for showing contrast",
                "match_score": 75
            }
        ]
        
        # Customize based on context
        if context and "trend" in context.lower():
            default_suggestions[0]["caption"] = "Following old trends | Creating viral content with AI"
            default_suggestions[0]["match_score"] = 95
        
        return default_suggestions
    
    def generate_fallback_suggestions(self, persona: Dict, context: str = "") -> List[Dict]:
        """Generate fallback suggestions when AI is not available."""
        primary_style = persona["humor_profile"]["primary_style"]
        
        style_suggestions = {
            "sarcastic": [
                {
                    "template": "Drake Pointing",
                    "caption": "Being genuinely happy | Pretending everything is fine",
                    "reason": "Matches your sarcastic humor style",
                    "match_score": 92
                },
                {
                    "template": "Woman Yelling at Cat",
                    "caption": "Life giving me problems | Me acting like it's normal",
                    "reason": "Perfect for your ironic perspective",
                    "match_score": 88
                }
            ],
            "wholesome": [
                {
                    "template": "Drake Pointing",
                    "caption": "Being mean to others | Supporting friends' dreams",
                    "reason": "Aligns with your positive humor",
                    "match_score": 90
                },
                {
                    "template": "Distracted Boyfriend",
                    "caption": "Me | Negativity | Choosing to be grateful",
                    "reason": "Reflects your uplifting style",
                    "match_score": 87
                }
            ],
            "dark": [
                {
                    "template": "This is Fine",
                    "caption": "This is fine while everything burns around me",
                    "reason": "Perfect for your dark humor edge",
                    "match_score": 95
                },
                {
                    "template": "Expanding Brain",
                    "caption": "Level 4: Accepting that nothing matters",
                    "reason": "Matches your existential humor",
                    "match_score": 89
                }
            ]
        }
        
        suggestions = style_suggestions.get(primary_style, style_suggestions["sarcastic"])
        
        # Add general suggestions to fill up to 4
        while len(suggestions) < 4:
            suggestions.extend(self.generate_default_suggestions(context))
            suggestions = suggestions[:4]
        
        return suggestions
    
    def get_user_persona(self, user_id: str) -> Optional[Dict]:
        """Get user persona by ID."""
        try:
            persona_file = self.personas_dir / f"{user_id}.json"
            if persona_file.exists():
                with open(persona_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading persona for user {user_id}: {e}")
        return None
    
    def save_persona(self, persona: Dict):
        """Save user persona to file."""
        try:
            user_id = persona["user_id"]
            persona_file = self.personas_dir / f"{user_id}.json"
            with open(persona_file, 'w') as f:
                json.dump(persona, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving persona: {e}") 