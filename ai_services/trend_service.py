"""
Trend Service for MemeZap - Handles real-time trend scraping and viral content analysis
"""
import logging
import json
import os
import requests
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
import time
import hashlib
import re
from collections import Counter

load_dotenv()

logger = logging.getLogger(__name__)

class TrendService:
    """Service for analyzing trends and generating viral content suggestions."""
    
    def __init__(self):
        """Initialize the TrendService."""
        self.data_dir = Path(__file__).parent.parent / "data"
        self.trends_dir = self.data_dir / "trends"
        self.trends_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenAI client for AI-powered analysis
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # News API setup
        self.news_api_key = os.getenv('NEWS_API_KEY')
        
        # Trending topics cache
        self.trends_cache = {}
        self.last_update = None
    
    def get_trending_topics(self, refresh: bool = False) -> List[Dict]:
        """Get current trending topics from various sources."""
        # Check cache first
        if not refresh and self.last_update:
            cache_age = (datetime.now() - self.last_update).total_seconds()
            if cache_age < 1800:  # 30 minutes
                return list(self.trends_cache.values())
        
        trends = []
        
        # Get news trends
        news_trends = self.get_news_trends()
        trends.extend(news_trends)
        
        # Get Reddit trends (simplified)
        reddit_trends = self.get_reddit_trends()
        trends.extend(reddit_trends)
        
        # If no trends found (e.g., no API keys), add mock trends
        if not trends:
            trends = self.get_mock_trends()
        
        # Update cache
        self.trends_cache = {trend['id']: trend for trend in trends}
        self.last_update = datetime.now()
        
        logger.info(f"Retrieved {len(trends)} trending topics")
        return trends
    
    def get_news_trends(self) -> List[Dict]:
        """Get trending topics from news sources."""
        trends = []
        
        if not self.news_api_key:
            return trends
        
        try:
            # Get top headlines
            url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={self.news_api_key}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for article in data.get('articles', []):
                title = article.get('title', '')
                if title and title != '[Removed]':
                    trends.append({
                        'id': hashlib.md5(title.encode()).hexdigest(),
                        'name': title,
                        'source': 'news',
                        'volume': 0,
                        'url': article.get('url', ''),
                        'timestamp': datetime.now().isoformat(),
                        'meme_potential': self.calculate_meme_potential(title),
                        'description': article.get('description', '')
                    })
        
        except Exception as e:
            logger.error(f"Error getting news trends: {e}")
        
        return trends
    
    def get_reddit_trends(self) -> List[Dict]:
        """Get trending topics from Reddit."""
        trends = []
        
        try:
            # Get popular posts from r/all
            url = "https://www.reddit.com/r/all/hot.json?limit=25"
            headers = {'User-Agent': 'MemeZap/1.0'}
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for post in data.get('data', {}).get('children', []):
                post_data = post.get('data', {})
                title = post_data.get('title', '')
                
                if title and post_data.get('score', 0) > 1000:
                    trends.append({
                        'id': hashlib.md5(title.encode()).hexdigest(),
                        'name': title,
                        'source': 'reddit',
                        'volume': post_data.get('score', 0),
                        'url': f"https://reddit.com{post_data.get('permalink', '')}",
                        'timestamp': datetime.now().isoformat(),
                        'meme_potential': self.calculate_meme_potential(title),
                        'subreddit': post_data.get('subreddit', '')
                    })
        
        except Exception as e:
            logger.error(f"Error getting Reddit trends: {e}")
        
        return trends
    
    def calculate_meme_potential(self, text: str) -> float:
        """Calculate the meme potential of a trending topic."""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        score = 0.0
        
        # Check for meme-worthy keywords
        meme_keywords = [
            'drama', 'controversy', 'exposed', 'cancelled', 'viral',
            'memes', 'trending', 'breaking', 'shocking', 'outrageous',
            'vs', 'fight', 'beef', 'roast', 'clap back', 'shade',
            'cringe', 'awkward', 'fail', 'epic', 'legendary'
        ]
        
        for keyword in meme_keywords:
            if keyword in text_lower:
                score += 0.1
        
        # Cap at 1.0
        return min(score, 1.0)
    
    def generate_meme_suggestions_from_trends(self, limit: int = 5) -> List[Dict]:
        """Generate meme suggestions based on current trends."""
        if not self.openai_client:
            return []
        
        trends = self.get_trending_topics()
        
        # Filter trends with high meme potential
        meme_worthy_trends = [t for t in trends if t['meme_potential'] > 0.3][:limit]
        
        suggestions = []
        
        for trend in meme_worthy_trends:
            try:
                suggestion = self.generate_meme_for_trend(trend)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.error(f"Error generating meme for trend {trend['name']}: {e}")
        
        return suggestions
    
    def generate_meme_for_trend(self, trend: Dict) -> Optional[Dict]:
        """Generate a meme suggestion for a specific trend."""
        if not self.openai_client:
            return None
        
        try:
            prompt = f"""
            Create a viral meme suggestion based on this trending topic:
            
            Topic: {trend['name']}
            Source: {trend['source']}
            
            Generate a meme suggestion with:
            1. Template/format (e.g., "Drake Pointing", "Distracted Boyfriend", etc.)
            2. Caption/text for the meme
            3. Why this would be viral
            
            Return as JSON: {{"template": "...", "caption": "...", "reason": "..."}}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral meme creator."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.8
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                suggestion = json.loads(json_match.group())
                suggestion['trend_id'] = trend['id']
                suggestion['trend_name'] = trend['name']
                suggestion['created_at'] = datetime.now().isoformat()
                return suggestion
        
        except Exception as e:
            logger.error(f"Error generating meme for trend: {e}")
        
        return None
    
    def get_mock_trends(self) -> List[Dict]:
        """Get mock trending topics when APIs aren't available."""
        mock_trends = [
            {
                'id': 'ai_revolution_2024',
                'name': 'AI Revolution Takes Over Everything in 2024',
                'source': 'tech_news',
                'volume': 50000,
                'url': 'https://example.com/ai-revolution',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.9,
                'description': 'AI tools are becoming mainstream across all industries'
            },
            {
                'id': 'remote_work_culture',
                'name': 'Remote Work Culture Shifts Post-Pandemic',
                'source': 'business',
                'volume': 35000,
                'url': 'https://example.com/remote-work',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.7,
                'description': 'How remote work is changing professional dynamics'
            },
            {
                'id': 'crypto_market_volatility',
                'name': 'Crypto Market Volatility Continues',
                'source': 'finance',
                'volume': 42000,
                'url': 'https://example.com/crypto-volatility',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.8,
                'description': 'Cryptocurrency prices fluctuate wildly'
            },
            {
                'id': 'social_media_drama',
                'name': 'Latest Social Media Platform Drama',
                'source': 'social',
                'volume': 28000,
                'url': 'https://example.com/social-drama',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.9,
                'description': 'Users revolt against platform changes'
            },
            {
                'id': 'climate_change_action',
                'name': 'Climate Change Action Debate',
                'source': 'environment',
                'volume': 31000,
                'url': 'https://example.com/climate-action',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.6,
                'description': 'Environmental policies spark discussion'
            },
            {
                'id': 'streaming_wars',
                'name': 'Streaming Service Wars Heat Up',
                'source': 'entertainment',
                'volume': 25000,
                'url': 'https://example.com/streaming-wars',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.8,
                'description': 'New streaming services compete for viewers'
            },
            {
                'id': 'food_delivery_costs',
                'name': 'Food Delivery Costs Reaching New Heights',
                'source': 'lifestyle',
                'volume': 18000,
                'url': 'https://example.com/delivery-costs',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.7,
                'description': 'Delivery fees and tips become major expense'
            },
            {
                'id': 'gaming_industry_news',
                'name': 'Gaming Industry Major Releases',
                'source': 'gaming',
                'volume': 22000,
                'url': 'https://example.com/gaming-news',
                'timestamp': datetime.now().isoformat(),
                'meme_potential': 0.8,
                'description': 'New game releases and industry updates'
            }
        ]
        
        logger.info("Using mock trending topics (no API keys available)")
        return mock_trends
