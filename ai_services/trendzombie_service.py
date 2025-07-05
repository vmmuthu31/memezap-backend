"""
TrendZombie Service - AI Meme Resurrector
An AI that digs up old, dead memes and revives them with modern contexts.
"""
import logging
import json
import os
import requests
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import hashlib
import re
from collections import defaultdict

load_dotenv()

logger = logging.getLogger(__name__)

class TrendZombieService:
    """AI service for resurrecting old memes with modern contexts."""
    
    def __init__(self):
        """Initialize the TrendZombie service."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.zombie_dir = self.data_dir / "zombie_memes"
        self.zombie_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAI client for AI-powered resurrection
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Classic meme database
        self.classic_memes = self.load_classic_memes()
        
        # Resurrection cache
        self.resurrection_cache = {}
        self.last_cache_update = None
    
    def load_classic_memes(self) -> List[Dict]:
        """Load database of classic/old memes."""
        return [
            {
                'id': 'doge',
                'name': 'Doge',
                'description': 'Shiba Inu dog with Comic Sans text',
                'peak_years': [2013, 2014, 2015],
                'template': 'Doge face',
                'style': 'such {adjective}, very {noun}, wow',
                'context': 'Expressing enthusiasm or surprise about something',
                'revival_potential': 0.9,
                'keywords': ['crypto', 'dogecoin', 'wow', 'such', 'very', 'meme'],
                'example_captions': [
                    'such investment, very gains, wow',
                    'much confusion, very complex, wow'
                ]
            },
            {
                'id': 'distracted_boyfriend',
                'name': 'Distracted Boyfriend',
                'description': 'Man looking at another woman while girlfriend looks disapproving',
                'peak_years': [2017, 2018],
                'template': 'Three person relationship dynamic',
                'style': 'Boyfriend: {current_thing}, Girlfriend: {old_thing}, Other Woman: {new_thing}',
                'context': 'Showing preference for something new over something old',
                'revival_potential': 0.8,
                'keywords': ['choice', 'preference', 'relationship', 'temptation', 'new vs old'],
                'example_captions': [
                    'Me: Old habits, New trend: Better lifestyle',
                    'Investors: Traditional stocks, Crypto: Higher returns'
                ]
            },
            {
                'id': 'drake_pointing',
                'name': 'Drake Pointing',
                'description': 'Drake rejecting something in first panel, approving in second',
                'peak_years': [2015, 2016, 2017],
                'template': 'Two panel approval/rejection',
                'style': 'Top: {rejected_thing}, Bottom: {approved_thing}',
                'context': 'Showing preference between two options',
                'revival_potential': 0.9,
                'keywords': ['choice', 'preference', 'approval', 'rejection', 'comparison'],
                'example_captions': [
                    'Top: Paying full price, Bottom: Using discount codes',
                    'Top: Traditional meetings, Bottom: Async work'
                ]
            },
            {
                'id': 'expanding_brain',
                'name': 'Expanding Brain',
                'description': 'Four-panel brain getting progressively larger',
                'peak_years': [2017, 2018],
                'template': 'Four levels of intelligence/enlightenment',
                'style': 'Level 1: {basic}, Level 2: {better}, Level 3: {advanced}, Level 4: {galaxy_brain}',
                'context': 'Showing progression of ideas from basic to advanced',
                'revival_potential': 0.7,
                'keywords': ['intelligence', 'progression', 'levels', 'enlightenment', 'galaxy brain'],
                'example_captions': [
                    'Level 1: Using passwords, Level 2: Using 2FA, Level 3: Hardware keys, Level 4: Biometric everything'
                ]
            },
            {
                'id': 'woman_yelling_at_cat',
                'name': 'Woman Yelling at Cat',
                'description': 'Woman pointing and yelling, confused cat at table',
                'peak_years': [2019, 2020],
                'template': 'Argument/confrontation between two perspectives',
                'style': 'Woman: {angry_perspective}, Cat: {confused_innocent_perspective}',
                'context': 'Confrontation between opposing viewpoints',
                'revival_potential': 0.8,
                'keywords': ['argument', 'confrontation', 'confusion', 'perspective', 'cat'],
                'example_captions': [
                    'Woman: Why did you buy more crypto?, Cat: But line go up'
                ]
            },
            {
                'id': 'bernie_sanders_mittens',
                'name': 'Bernie Sanders Mittens',
                'description': 'Bernie Sanders sitting with mittens at inauguration',
                'peak_years': [2021],
                'template': 'Bernie sitting alone waiting/watching',
                'style': 'Bernie sitting waiting for {something}',
                'context': 'Waiting patiently for something, feeling left out',
                'revival_potential': 0.6,
                'keywords': ['waiting', 'patient', 'mittens', 'politics', 'inauguration'],
                'example_captions': [
                    'Bernie waiting for his crypto gains',
                    'Bernie waiting for AI to take over'
                ]
            },
            {
                'id': 'this_is_fine',
                'name': 'This is Fine',
                'description': 'Dog in burning room saying everything is fine',
                'peak_years': [2016, 2017, 2018],
                'template': 'Denial in face of obvious problems',
                'style': 'Everything is fine while {disaster_happening}',
                'context': 'Denial or acceptance of bad situations',
                'revival_potential': 0.9,
                'keywords': ['denial', 'disaster', 'fine', 'burning', 'dog', 'acceptance'],
                'example_captions': [
                    'This is fine while portfolio crashes',
                    'This is fine while AI takes all jobs'
                ]
            },
            {
                'id': 'two_buttons',
                'name': 'Two Buttons',
                'description': 'Man sweating over choosing between two buttons',
                'peak_years': [2017, 2018],
                'template': 'Difficult choice between two options',
                'style': 'Button 1: {option_a}, Button 2: {option_b}',
                'context': 'Difficult decisions with no clear right answer',
                'revival_potential': 0.7,
                'keywords': ['choice', 'decision', 'sweating', 'buttons', 'dilemma'],
                'example_captions': [
                    'Button 1: Save money, Button 2: Buy more crypto',
                    'Button 1: Work-life balance, Button 2: Startup grind'
                ]
            },
            {
                'id': 'galaxy_brain',
                'name': 'Galaxy Brain',
                'description': 'Brain getting progressively more cosmic and enlightened',
                'peak_years': [2018, 2019],
                'template': 'Levels of enlightenment/intelligence',
                'style': 'Small brain: {basic}, Big brain: {advanced}, Galaxy brain: {transcendent}',
                'context': 'Showing progression from basic to transcendent thinking',
                'revival_potential': 0.8,
                'keywords': ['intelligence', 'enlightenment', 'galaxy', 'brain', 'transcendent'],
                'example_captions': [
                    'Small brain: Using Excel, Big brain: Using databases, Galaxy brain: Using AI'
                ]
            },
            {
                'id': 'stonks',
                'name': 'Stonks',
                'description': 'Meme man with misspelled "stocks" and upward arrow',
                'peak_years': [2019, 2020, 2021],
                'template': 'Ironic celebration of financial gains',
                'style': 'Stonks ↗️ when {financial_situation}',
                'context': 'Ironic celebration of investments or financial decisions',
                'revival_potential': 0.9,
                'keywords': ['stocks', 'finance', 'gains', 'investment', 'meme man', 'stonks'],
                'example_captions': [
                    'Stonks when you buy AI stocks before the boom',
                    'Stonks when you invest in meme coins'
                ]
            }
        ]
    
    def resurrect_memes_for_trends(self, trends: List[Dict], limit: int = 5) -> List[Dict]:
        """Resurrect multiple memes based on current trends."""
        resurrections = []
        
        for trend in trends[:limit]:
            try:
                resurrection = self.resurrect_meme_for_trend(trend)
                if resurrection:
                    resurrections.append(resurrection)
            except Exception as e:
                logger.error(f"Error resurrecting meme for trend {trend.get('name', 'unknown')}: {e}")
        
        return resurrections
    
    def resurrect_meme_for_trend(self, trend: Dict) -> Optional[Dict]:
        """Resurrect a specific old meme for a current trend."""
        if not self.openai_client:
            return None
        
        try:
            # Find best matching classic meme
            best_meme = self.find_best_meme_match(trend)
            if not best_meme:
                return None
            
            # Generate modern context resurrection
            prompt = f"""
            You are the TrendZombie - an AI that resurrects old memes with modern contexts.
            
            TREND: {trend['name']}
            TREND DESCRIPTION: {trend.get('description', 'N/A')}
            
            CLASSIC MEME TO RESURRECT:
            Name: {best_meme['name']}
            Description: {best_meme['description']}
            Original Style: {best_meme['style']}
            Peak Years: {best_meme['peak_years']}
            
            RESURRECTION TASK:
            Take this classic meme and give it a modern twist based on the current trend.
            Make it feel fresh and relevant to 2024/2025 while maintaining the original meme's essence.
            
            Generate:
            1. Updated caption that combines the meme format with the trend
            2. Why this resurrection would be viral
            3. Modern context explanation
            
            Examples of good resurrections:
            - "What if Doge commented on Bitcoin ETFs?" → "such regulation, very adoption, wow"
            - "Distracted Boyfriend but it's AI vs Traditional Jobs"
            - "This is Fine but during AI revolution"
            
            Return as JSON: {{
                "caption": "...",
                "viral_reason": "...",
                "modern_context": "...",
                "resurrection_angle": "..."
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are TrendZombie, the AI meme resurrector. You specialize in bringing old memes back to life with modern contexts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.8
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                resurrection_data = json.loads(json_match.group())
                
                resurrection = {
                    'id': f"zombie_{hashlib.md5(f'{best_meme['id']}_{trend['name']}'.encode()).hexdigest()[:12]}",
                    'original_meme': best_meme,
                    'trend': trend,
                    'resurrection_data': resurrection_data,
                    'created_at': datetime.now().isoformat(),
                    'zombie_score': self.calculate_zombie_score(best_meme, trend),
                    'template_url': f"https://imgflip.com/memetemplate/{best_meme['id']}",
                    'type': 'resurrection'
                }
                
                return resurrection
        
        except Exception as e:
            logger.error(f"Error resurrecting meme: {e}")
        
        return None
    
    def find_best_meme_match(self, trend: Dict) -> Optional[Dict]:
        """Find the best classic meme to match with a trend."""
        trend_text = f"{trend['name']} {trend.get('description', '')}".lower()
        
        scored_memes = []
        
        for meme in self.classic_memes:
            score = 0.0
            
            # Check keyword overlap
            for keyword in meme['keywords']:
                if keyword.lower() in trend_text:
                    score += 0.2
            
            # Check revival potential
            score += meme['revival_potential'] * 0.3
            
            # Bonus for memes that peaked long ago (more resurrection potential)
            years_since_peak = datetime.now().year - max(meme['peak_years'])
            if years_since_peak > 3:
                score += 0.1
            if years_since_peak > 5:
                score += 0.2
            
            # Context matching
            if any(word in trend_text for word in ['choice', 'decision', 'vs', 'versus']):
                if meme['id'] in ['drake_pointing', 'two_buttons', 'distracted_boyfriend']:
                    score += 0.3
            
            if any(word in trend_text for word in ['disaster', 'crisis', 'problem', 'crash']):
                if meme['id'] in ['this_is_fine']:
                    score += 0.4
            
            if any(word in trend_text for word in ['crypto', 'bitcoin', 'finance', 'money', 'stocks']):
                if meme['id'] in ['doge', 'stonks']:
                    score += 0.3
            
            if any(word in trend_text for word in ['ai', 'artificial', 'intelligence', 'technology']):
                if meme['id'] in ['expanding_brain', 'galaxy_brain']:
                    score += 0.3
            
            scored_memes.append((meme, score))
        
        # Sort by score and return best match
        scored_memes.sort(key=lambda x: x[1], reverse=True)
        
        if scored_memes and scored_memes[0][1] > 0.3:
            return scored_memes[0][0]
        
        # If no good match, return a random high-potential meme
        high_potential = [m for m in self.classic_memes if m['revival_potential'] > 0.8]
        if high_potential:
            return random.choice(high_potential)
        
        return None
    
    def calculate_zombie_score(self, meme: Dict, trend: Dict) -> float:
        """Calculate how good this resurrection is."""
        score = 0.0
        
        # Base score from meme revival potential
        score += meme['revival_potential'] * 0.4
        
        # Trend meme potential
        score += trend.get('meme_potential', 0.5) * 0.3
        
        # Age bonus (older memes get higher resurrection scores)
        years_since_peak = datetime.now().year - max(meme['peak_years'])
        age_bonus = min(years_since_peak / 10, 0.3)
        score += age_bonus
        
        return min(score, 1.0)
    
    def get_zombie_hall_of_fame(self, limit: int = 10) -> List[Dict]:
        """Get the best resurrected memes."""
        # This would typically load from a database
        # For now, return some example resurrections
        return [
            {
                'id': 'zombie_doge_ai',
                'original_meme': {'name': 'Doge', 'peak_years': [2013, 2014]},
                'trend': {'name': 'AI Revolution 2024'},
                'resurrection_data': {
                    'caption': 'such intelligence, very artificial, wow',
                    'viral_reason': 'Classic meme format meets current AI hype',
                    'modern_context': 'AI taking over everything in 2024'
                },
                'zombie_score': 0.9,
                'created_at': datetime.now().isoformat()
            }
        ]
    
    def resurrect_custom_meme(self, meme_name: str, context: str) -> Optional[Dict]:
        """Resurrect a specific meme with custom context."""
        if not self.openai_client:
            return None
        
        # Find the meme
        target_meme = None
        for meme in self.classic_memes:
            if meme_name.lower() in meme['name'].lower():
                target_meme = meme
                break
        
        if not target_meme:
            return None
        
        try:
            prompt = f"""
            Resurrect the {target_meme['name']} meme with this context: {context}
            
            Original format: {target_meme['style']}
            Original context: {target_meme['context']}
            
            Create a modern version that fits the new context while maintaining the meme's essence.
            
            Return as JSON: {{
                "caption": "...",
                "explanation": "...",
                "viral_potential": "..."
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are TrendZombie, expert at resurrecting old memes with new contexts."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.8
            )
            
            response_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                resurrection_data = json.loads(json_match.group())
                return {
                    'original_meme': target_meme,
                    'context': context,
                    'resurrection_data': resurrection_data,
                    'created_at': datetime.now().isoformat(),
                    'type': 'custom_resurrection'
                }
        
        except Exception as e:
            logger.error(f"Error in custom resurrection: {e}")
        
        return None
    
    def get_resurrection_stats(self) -> Dict:
        """Get statistics about TrendZombie resurrections."""
        try:
            stats = {
                'total_classic_memes': len(self.classic_memes),
                'high_potential_memes': len([m for m in self.classic_memes if m['revival_potential'] > 0.7]),
                'average_age': 0.0,
                'total_resurrections': 0,
                'average_zombie_score': 0.0
            }
            
            # Calculate average age
            if self.classic_memes:
                current_year = datetime.now().year
                ages = []
                for meme in self.classic_memes:
                    peak_year = max(meme['peak_years'])
                    age = current_year - peak_year
                    ages.append(age)
                stats['average_age'] = sum(ages) / len(ages)
            
            # Get most resurrectable meme
            if self.classic_memes:
                best_meme = max(self.classic_memes, key=lambda x: x['revival_potential'])
                stats['most_resurrectable'] = best_meme['name']
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting resurrection stats: {e}")
            return {
                'total_classic_memes': 0,
                'high_potential_memes': 0,
                'average_age': 0.0,
                'total_resurrections': 0,
                'average_zombie_score': 0.0
            } 