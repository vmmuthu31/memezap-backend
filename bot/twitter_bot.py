#!/usr/bin/env python3
"""
MemeZap Twitter Bot - Enhanced with template recognition and trend analysis
Anyone can mention @memezap with an image to generate memes
"""

import tweepy
import requests
import os
import time
import logging
from PIL import Image
from io import BytesIO
import textwrap
from datetime import datetime
import json
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add parent directory to path to import AI services
sys.path.append(str(Path(__file__).parent.parent))

# Import our enhanced AI services
from ai_services.template_service import TemplateService
from ai_services.trend_service import TrendService
from ai_services.persona_service import PersonaService
from ai_services.trendzombie_service import TrendZombieService

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot/meme_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MemeZapBot:
    def __init__(self):
        """Initialize the enhanced MemeZap bot"""
        # Load API credentials from environment variables
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        
        # MemeZap API configuration
        self.memezap_api_url = os.getenv('MEMEZAP_API_URL', 'http://127.0.0.1:8000/api/smart_generate')
        
        if not all([self.api_key, self.api_secret, self.access_token, 
                   self.access_token_secret, self.bearer_token]):
            raise ValueError("Missing Twitter API credentials in environment variables")
        
        # Initialize Twitter API clients
        self.setup_twitter_clients()
        
        # Initialize AI services
        logger.info("🧠 Initializing AI services...")
        self.template_service = TemplateService()
        self.trend_service = TrendService()
        self.persona_service = PersonaService()
        self.trendzombie_service = TrendZombieService()
        logger.info("✅ AI services initialized")
        
        # Track processed tweets to avoid duplicates
        self.processed_tweets = set()
        self.load_processed_tweets()
        
        # Bot configuration
        self.trigger_phrases = ["meme", "make meme", "meme this", "generate meme", "meme it", "resurrect", "trendzombie"]
        self.meme_it_phrases = ["meme it", "make it a meme", "meme this"]
        self.trendzombie_phrases = ["resurrect", "trendzombie", "bring back", "revive meme"]
        self.max_text_length = 200
        
        # Get bot's user info
        self.bot_user_id = None
        self.bot_username = None
        self.get_bot_info()
        
        # Rate limiting
        self.last_check_time = None
        self.check_interval = 180  # 3 minutes between checks
        
        # Enhanced features
        self.use_template_recognition = True
        self.use_trend_analysis = True
        self.use_persona_analysis = True
    
    def setup_twitter_clients(self):
        """Setup Twitter API clients"""
        try:
            # Twitter API v1.1 (for media upload and posting)
            auth = tweepy.OAuthHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=False)
            
            # Twitter API v2 (for reading tweets)
            self.client = tweepy.Client(
                bearer_token=self.bearer_token,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=False
            )
            
            # Test authentication
            me = self.api_v1.verify_credentials()
            logger.info(f"🤖 Enhanced MemeZap Bot authenticated as @{me.screen_name}")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Twitter API: {e}")
            raise
    
    def get_bot_info(self):
        """Get the bot's user info"""
        try:
            me_v1 = self.api_v1.verify_credentials()
            me_v2 = self.client.get_me()
            
            self.bot_user_id = me_v2.data.id
            self.bot_username = me_v1.screen_name.lower()
            
            logger.info(f"🎭 Bot Username: @{me_v1.screen_name}")
            logger.info(f"📝 Enhanced features: Template recognition, Trend analysis, Persona learning")
            
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
    
    def load_processed_tweets(self):
        """Load previously processed tweet IDs"""
        try:
            processed_file = Path(__file__).parent / 'processed_tweets.json'
            if processed_file.exists():
                with open(processed_file, 'r') as f:
                    self.processed_tweets = set(json.load(f))
        except Exception as e:
            logger.warning(f"Could not load processed tweets: {e}")
            self.processed_tweets = set()
    
    def save_processed_tweets(self):
        """Save processed tweet IDs"""
        try:
            processed_file = Path(__file__).parent / 'processed_tweets.json'
            with open(processed_file, 'w') as f:
                json.dump(list(self.processed_tweets), f)
        except Exception as e:
            logger.error(f"Could not save processed tweets: {e}")
    
    def check_mentions(self):
        """Check for new mentions with enhanced processing using search (works with basic API access)"""
        try:
            # Rate limiting check
            current_time = time.time()
            if self.last_check_time and (current_time - self.last_check_time) < self.check_interval:
                return
            
            self.last_check_time = current_time
            
            try:
                # Use search instead of mentions_timeline (works with basic access)
                # Search for tweets mentioning the bot
                search_query = f"@{self.bot_username}"
                
                # Use Twitter API v2 search instead of mentions_timeline
                tweets = self.client.search_recent_tweets(
                    query=search_query,
                    max_results=20,
                    tweet_fields=['created_at', 'author_id', 'text', 'attachments', 'referenced_tweets'],
                    user_fields=['username'],
                    expansions=['author_id', 'attachments.media_keys'],
                    media_fields=['url', 'preview_image_url']
                )
                
                if not tweets or not tweets.data:
                    logger.info("No new mentions found")
                    return
                
                logger.info(f"📬 Found {len(tweets.data)} mentions to process")
                
                for tweet in tweets.data:
                    # Skip if already processed
                    if str(tweet.id) in self.processed_tweets:
                        continue
                    
                    # Skip if it's the bot's own tweet
                    if str(tweet.author_id) == str(self.bot_user_id):
                        continue
                    
                    # Convert v2 tweet to v1-like structure for compatibility
                    v1_like_tweet = self.convert_v2_to_v1_format(tweet, tweets.includes)
                    
                    # Process the mention with enhanced features
                    logger.info(f"👤 Processing enhanced mention from user {tweet.author_id}")
                    self.process_enhanced_meme_request(v1_like_tweet)
                        
                    # Mark as processed
                    self.processed_tweets.add(str(tweet.id))
                
                self.save_processed_tweets()
                
            except tweepy.TooManyRequests:
                logger.warning("⏰ Rate limit hit, waiting...")
                time.sleep(900)  # Wait 15 minutes
            except tweepy.Forbidden as e:
                logger.error(f"API access forbidden: {e}")
                logger.error("This might be due to API access level restrictions.")
                logger.info("💡 Consider upgrading to Elevated API access for full functionality")
                time.sleep(300)  # Wait 5 minutes before retrying
            except Exception as e:
                logger.error(f"Error checking mentions: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
                
        except Exception as e:
            logger.error(f"Unexpected error in check_mentions: {e}")

    def convert_v2_to_v1_format(self, v2_tweet, includes):
        """Convert v2 tweet format to v1-like format for compatibility"""
        class V1LikeTweet:
            def __init__(self, v2_tweet, includes):
                self.id = v2_tweet.id
                self.full_text = v2_tweet.text
                self.text = v2_tweet.text
                self.created_at = v2_tweet.created_at
                
                # Find user info from includes
                self.user = None
                if includes and 'users' in includes:
                    for user in includes['users']:
                        if user.id == v2_tweet.author_id:
                            self.user = type('User', (), {
                                'id': user.id,
                                'screen_name': user.username,
                                'name': user.name if hasattr(user, 'name') else user.username
                            })()
                            break
                
                # If user not found in includes, create minimal user object
                if not self.user:
                    self.user = type('User', (), {
                        'id': v2_tweet.author_id,
                        'screen_name': f'user_{v2_tweet.author_id}',
                        'name': f'User {v2_tweet.author_id}'
                    })()
                
                # Handle media/attachments
                self.entities = {'media': []}
                if hasattr(v2_tweet, 'attachments') and v2_tweet.attachments:
                    if 'media_keys' in v2_tweet.attachments:
                        if includes and 'media' in includes:
                            for media in includes['media']:
                                if media.media_key in v2_tweet.attachments['media_keys']:
                                    media_obj = {
                                        'media_url_https': media.url if hasattr(media, 'url') else None,
                                        'type': media.type if hasattr(media, 'type') else 'photo'
                                    }
                                    self.entities['media'].append(media_obj)
        
        return V1LikeTweet(v2_tweet, includes)
    
    def process_enhanced_meme_request(self, tweet):
        """Process a meme request with enhanced AI features"""
        try:
            user_id = str(tweet.user.id)
            username = tweet.user.screen_name
            
            # Check if this is a "meme it" request
            if self.is_meme_it_request(tweet.full_text):
                logger.info(f"🎭 Processing 'meme it' request from @{username}")
                self.process_meme_it_request(tweet)
                return
            
            # Check if this is a TrendZombie request
            if self.is_trendzombie_request(tweet.full_text):
                logger.info(f"🧟‍♂️ Processing TrendZombie request from @{username}")
                self.process_trendzombie_request(tweet)
                return
            
            # Extract image URL if present
            image_url = self.extract_image_url(tweet)
            
            if not image_url:
                # Try to get image from quoted tweet or reply chain
                image_url = self.get_image_from_context(tweet)
            
            if not image_url:
                # Enhanced no-image response with trend suggestions
                self.reply_no_image_enhanced(tweet.id, username)
                return
            
            # Extract text for meme
            meme_text = self.extract_meme_text(tweet.full_text)
            
            # Enhanced meme generation with AI services
            logger.info(f"🎨 Generating enhanced meme for @{username}")
            
            # Try template recognition first
            template_info = None
            if self.use_template_recognition:
                template_info = self.identify_template_from_url(image_url)
                if template_info:
                    logger.info(f"🎯 Template detected: {template_info['template_name']}")
            
            # Create meme using enhanced API
            meme_image = self.create_enhanced_meme(image_url, meme_text, template_info)
            
            # Update persona if enabled
            if self.use_persona_analysis:
                self.update_user_persona(user_id, {
                    'text': meme_text,
                    'template': template_info['template_name'] if template_info else 'custom',
                    'id': str(tweet.id)
                }, 'created')
            
            if meme_image:
                # Reply with enhanced meme
                self.reply_with_enhanced_meme(tweet.id, username, meme_image, template_info)
            else:
                # Fallback to GPT-4 generation
                self.fallback_to_gpt4(tweet.id, username, meme_text)
                
        except Exception as e:
            logger.error(f"Error processing enhanced meme request: {e}")
            self.reply_error(tweet.id, tweet.user.screen_name)
    
    def identify_template_from_url(self, image_url):
        """Identify template from image URL"""
        try:
            # Download image temporarily
            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                # Save temporarily
                temp_dir = Path(__file__).parent.parent / "data" / "temp"
                temp_dir.mkdir(parents=True, exist_ok=True)
                temp_path = temp_dir / f"temp_image_{int(time.time())}.jpg"
                
                with open(temp_path, 'wb') as f:
                    f.write(response.content)
                
                # Identify template
                template_info = self.template_service.identify_template(str(temp_path))
                
                # Clean up
                temp_path.unlink()
                
                return template_info
            
        except Exception as e:
            logger.error(f"Error identifying template: {e}")
        
        return None
    
    def create_enhanced_meme(self, image_url, text, template_info=None):
        """Create meme using enhanced API with template info"""
        try:
            data = {
                'image_url': image_url,
                'caption': text
            }
            
            # Add template info if available
            if template_info:
                data['template_id'] = template_info.get('template_id')
                data['template_name'] = template_info.get('template_name')
            
            response = requests.post(
                self.memezap_api_url,
                data=data,
                timeout=120
            )
            
            if response.status_code == 200:
                logger.info("✅ Enhanced meme generated successfully")
                return BytesIO(response.content)
            else:
                logger.error(f"❌ Enhanced MemeZap API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling enhanced MemeZap API: {e}")
            return None
    
    def fallback_to_gpt4(self, tweet_id, username, meme_text):
        """Fallback to GPT-4 when template detection fails"""
        try:
            logger.info(f"🤖 Using GPT-4 fallback for @{username}")
            
            # Generate witty caption using GPT-4
            if hasattr(self.template_service, 'openai_client') and self.template_service.openai_client:
                prompt = f"""
                Create a witty meme caption based on this text: "{meme_text}"
                
                Since no template was detected, create a general meme-style caption that would work as:
                - A reaction meme
                - A relatable statement
                - A humorous observation
                
                Make it viral-worthy and shareable. Return just the caption text.
                """
                
                response = self.template_service.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a viral meme caption generator."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.8
                )
                
                generated_caption = response.choices[0].message.content.strip()
                
                # Reply with generated caption
                reply_text = f"@{username} Couldn't detect a known template, but here's a viral-worthy caption! 🎭\n\n\"{generated_caption}\"\n\n#MemeZap #AIGenerated"
                
                self.api_v1.update_status(
                    status=reply_text,
                    in_reply_to_status_id=tweet_id
                )
                
                logger.info(f"✅ GPT-4 fallback reply sent to @{username}")
            else:
                # Simple fallback message
                self.reply_template_not_found(tweet_id, username)
                
        except Exception as e:
            logger.error(f"Error in GPT-4 fallback: {e}")
            self.reply_template_not_found(tweet_id, username)
    
    def reply_template_not_found(self, tweet_id, username):
        """Reply when template is not found"""
        try:
            reply_text = f"@{username} Couldn't detect a known meme template! 🤖\n\nTry using popular templates like:\n• Drake pointing\n• Distracted boyfriend\n• Woman yelling at cat\n\n#MemeZap"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"📝 Template not found reply sent to @{username}")
            
        except Exception as e:
            logger.error(f"Error replying template not found: {e}")
    
    def reply_no_image_enhanced(self, tweet_id, username):
        """Enhanced reply when no image found - includes trend suggestions"""
        try:
            # Get trending suggestions
            trending_suggestions = ""
            if self.use_trend_analysis:
                try:
                    trend_suggestions = self.trend_service.generate_meme_suggestions_from_trends(limit=2)
                    if trend_suggestions:
                        trending_suggestions = f"\n\n🔥 Trending now:\n• {trend_suggestions[0].get('caption', 'Trending meme')}\n• {trend_suggestions[1].get('caption', 'Another trending meme')}"
                except Exception as e:
                    logger.error(f"Error getting trend suggestions: {e}")
            
            reply_text = f"@{username} I need an image to make a meme! 📸\n\nTry:\n• Quote tweet an image with @{self.bot_username} text1|text2\n• Reply to an image with @{self.bot_username} your text{trending_suggestions}\n\n#MemeZap"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"📝 Enhanced no-image reply sent to @{username}")
            
        except Exception as e:
            logger.error(f"Error sending enhanced no-image reply: {e}")
    
    def reply_with_enhanced_meme(self, tweet_id, username, meme_image, template_info=None):
        """Reply with generated meme - enhanced with template info"""
        try:
            # Upload media
            media = self.api_v1.media_upload(filename="meme.jpg", file=meme_image)
            
            # Create enhanced reply text
            template_text = ""
            if template_info:
                template_text = f" using {template_info['template_name']} template"
            
            reply_text = f"@{username} Here's your meme{template_text}! 🎭✨\n\nPowered by #MemeZap AI 🤖"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id,
                media_ids=[media.media_id]
            )
            
            logger.info(f"✅ Enhanced meme reply sent to @{username}")
            
        except Exception as e:
            logger.error(f"Error sending enhanced meme reply: {e}")
    
    def update_user_persona(self, user_id, meme_data, interaction_type):
        """Update user persona based on interaction"""
        try:
            self.persona_service.analyze_meme_interaction(user_id, meme_data, interaction_type)
            logger.info(f"🧠 Updated persona for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating persona: {e}")
    
    def is_meme_it_request(self, text):
        """Check if tweet is a 'meme it' request"""
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in self.meme_it_phrases)
    
    def is_trendzombie_request(self, text):
        """Check if tweet is a TrendZombie request"""
        text_lower = text.lower()
        return any(phrase in text_lower for phrase in self.trendzombie_phrases)
    
    def process_meme_it_request(self, tweet):
        """Process a 'meme it' request by meme-ifying the original tweet"""
        try:
            username = tweet.user.screen_name
            
            # Get the original tweet this is replying to
            if not tweet.in_reply_to_status_id:
                self.reply_meme_it_error(tweet.id, username, "I need a tweet to meme! Reply to a tweet with '@memezap meme it'")
                return
            
            # Fetch the original tweet
            try:
                original_tweet = self.api_v1.get_status(
                    tweet.in_reply_to_status_id,
                    tweet_mode='extended',
                    include_entities=True
                )
            except Exception as e:
                logger.error(f"Error fetching original tweet: {e}")
                self.reply_meme_it_error(tweet.id, username, "Couldn't fetch the original tweet. Try again!")
                return
            
            logger.info(f"🎭 Meme-ifying tweet from @{original_tweet.user.screen_name}: {original_tweet.full_text[:50]}...")
            
            # Extract content from original tweet
            original_text = original_tweet.full_text
            original_image_url = self.extract_image_url(original_tweet)
            
            # Generate meme from tweet content
            if original_image_url:
                # Tweet has image - use it for meme generation
                self.generate_meme_from_tweet_with_image(tweet, original_tweet, original_image_url)
            else:
                # Tweet has no image - generate text-based meme
                self.generate_meme_from_tweet_text(tweet, original_tweet, original_text)
            
        except Exception as e:
            logger.error(f"Error processing meme it request: {e}")
            self.reply_meme_it_error(tweet.id, tweet.user.screen_name, "Something went wrong! Try again later.")
    
    def process_trendzombie_request(self, tweet):
        """Process a TrendZombie request to resurrect old memes"""
        try:
            user_id = str(tweet.user.id)
            username = tweet.user.screen_name
            
            # Extract context from the tweet
            context = self.extract_trendzombie_context(tweet.full_text)
            
            if not context:
                self.reply_trendzombie_error(tweet.id, username, "I need a context to resurrect! Try: '@memezap resurrect doge with crypto news'")
                return
            
            # Parse meme name and context
            meme_name, resurrection_context = self.parse_trendzombie_request(context)
            
            if not meme_name:
                # Auto-select based on current trends
                logger.info(f"🤖 Auto-selecting meme for resurrection with context: {resurrection_context}")
                resurrection = self.trendzombie_service.resurrect_memes_for_trends(
                    [{'name': resurrection_context, 'description': resurrection_context}], 
                    limit=1
                )
                if resurrection:
                    self.reply_with_resurrection(tweet.id, username, resurrection[0])
                else:
                    self.reply_trendzombie_error(tweet.id, username, "Couldn't find a good meme to resurrect!")
            else:
                # User specified meme
                logger.info(f"🧟‍♂️ Resurrecting {meme_name} with context: {resurrection_context}")
                resurrection = self.trendzombie_service.resurrect_custom_meme(meme_name, resurrection_context)
                
                if resurrection:
                    self.reply_with_resurrection(tweet.id, username, resurrection)
                else:
                    self.reply_trendzombie_error(tweet.id, username, f"Couldn't resurrect {meme_name}. Try: Doge, Drake, This is Fine, etc.")
                    
        except Exception as e:
            logger.error(f"Error processing TrendZombie request: {e}")
            self.reply_trendzombie_error(tweet.id, username, "Something went wrong with the resurrection!")
    
    def extract_trendzombie_context(self, tweet_text):
        """Extract context from TrendZombie tweet"""
        import re
        
        # Remove bot mention
        text = re.sub(f'@{self.bot_username}', '', tweet_text, flags=re.IGNORECASE)
        
        # Remove trigger phrases
        for phrase in self.trendzombie_phrases:
            text = text.replace(phrase, "")
        
        # Clean up
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text if len(text) > 3 else None
    
    def parse_trendzombie_request(self, context):
        """Parse TrendZombie request to extract meme name and context"""
        import re
        
        # Look for "meme_name with context" pattern
        with_pattern = re.match(r'(\w+)\s+with\s+(.+)', context, re.IGNORECASE)
        if with_pattern:
            return with_pattern.group(1), with_pattern.group(2)
        
        # Look for just context (no specific meme mentioned)
        return None, context
    
    def reply_with_resurrection(self, tweet_id, username, resurrection):
        """Reply with resurrected meme"""
        try:
            meme_name = resurrection['original_meme']['name']
            caption = resurrection['resurrection_data']['caption']
            viral_reason = resurrection['resurrection_data'].get('viral_reason', 'Perfect nostalgia meets modern context!')
            
            reply_text = f"@{username} 🧟‍♂️ **{meme_name} RESURRECTED!** 🧟‍♂️\n\n"
            reply_text += f"💀➡️✨ \"{caption}\"\n\n"
            reply_text += f"🔥 Why it's viral: {viral_reason[:100]}...\n\n"
            reply_text += f"#TrendZombie #MemeResurrection #MemeZap"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"🧟‍♂️ TrendZombie reply sent to @{username}")
            
        except Exception as e:
            logger.error(f"Error sending TrendZombie reply: {e}")
    
    def reply_trendzombie_error(self, tweet_id, username, error_message):
        """Reply with error message for TrendZombie requests"""
        try:
            reply_text = f"@{username} {error_message} 🧟‍♂️\n\n💡 Try:\n"
            reply_text += f"• '@{self.bot_username} resurrect doge with AI news'\n"
            reply_text += f"• '@{self.bot_username} bring back drake with crypto'\n"
            reply_text += f"• '@{self.bot_username} trendzombie current events'\n\n"
            reply_text += f"#TrendZombie #MemeZap"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"📝 TrendZombie error reply sent to @{username}")
            
        except Exception as e:
            logger.error(f"Error sending TrendZombie error reply: {e}")
    
    def generate_meme_from_tweet_with_image(self, reply_tweet, original_tweet, image_url):
        """Generate meme from tweet that contains an image"""
        try:
            username = reply_tweet.user.screen_name
            
            # Try template recognition
            template_info = None
            if self.use_template_recognition:
                template_info = self.identify_template_from_url(image_url)
            
            # Use original tweet text as meme text, or generate AI caption
            meme_text = original_tweet.full_text
            
            # Clean up the text (remove URLs, mentions, etc.)
            meme_text = self.clean_tweet_text_for_meme(meme_text)
            
            # If text is too long or empty, generate AI caption
            if len(meme_text) > self.max_text_length or len(meme_text) < 5:
                meme_text = self.generate_ai_caption_for_image(image_url, original_tweet.full_text)
            
            # Create meme
            meme_image = self.create_enhanced_meme(image_url, meme_text, template_info)
            
            if meme_image:
                # Reply with meme
                reply_text = f"@{username} Here's your meme! 🎭✨\n\nOriginal tweet by @{original_tweet.user.screen_name}\n\n#MemeZap #MemeIt"
                
                # Upload and reply
                media = self.api_v1.media_upload(filename="meme.jpg", file=meme_image)
                self.api_v1.update_status(
                    status=reply_text,
                    in_reply_to_status_id=reply_tweet.id,
                    media_ids=[media.media_id]
                )
                
                logger.info(f"✅ Meme It reply sent to @{username}")
            else:
                self.reply_meme_it_error(reply_tweet.id, username, "Couldn't generate meme from that image. Try another!")
                
        except Exception as e:
            logger.error(f"Error generating meme from tweet with image: {e}")
            self.reply_meme_it_error(reply_tweet.id, reply_tweet.user.screen_name, "Error generating meme!")
    
    def generate_meme_from_tweet_text(self, reply_tweet, original_tweet, tweet_text):
        """Generate meme from tweet that has only text"""
        try:
            username = reply_tweet.user.screen_name
            
            # Generate meme using AI based on tweet content
            if hasattr(self.template_service, 'openai_client') and self.template_service.openai_client:
                # Use GPT-4 to create a meme format suggestion
                prompt = f"""
                Create a meme based on this tweet: "{tweet_text}"
                
                Generate a meme in this format:
                1. Choose a popular meme template (like "Drake pointing", "Distracted boyfriend", etc.)
                2. Create appropriate text for the meme
                3. Make it funny and shareable
                
                Tweet author: @{original_tweet.user.screen_name}
                
                Return as JSON: {{"template": "template name", "top_text": "...", "bottom_text": "...", "explanation": "why this is funny"}}
                """
                
                response = self.template_service.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a viral meme creator. Transform tweets into hilarious memes."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200,
                    temperature=0.8
                )
                
                response_text = response.choices[0].message.content.strip()
                
                # Parse JSON response
                import json
                import re
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    meme_data = json.loads(json_match.group())
                    
                    # Create reply with meme suggestion
                    reply_text = f"@{username} Here's your meme! 🎭✨\n\n"
                    reply_text += f"**{meme_data.get('template', 'Custom')} Template:**\n"
                    reply_text += f"Top: {meme_data.get('top_text', '')}\n"
                    reply_text += f"Bottom: {meme_data.get('bottom_text', '')}\n\n"
                    reply_text += f"Original tweet by @{original_tweet.user.screen_name}\n#MemeZap #MemeIt"
                    
                    self.api_v1.update_status(
                        status=reply_text,
                        in_reply_to_status_id=reply_tweet.id
                    )
                    
                    logger.info(f"✅ Text-based Meme It reply sent to @{username}")
                else:
                    self.reply_meme_it_error(reply_tweet.id, username, "Couldn't parse AI response. Try again!")
                    
            else:
                # Fallback without AI
                clean_text = self.clean_tweet_text_for_meme(tweet_text)
                reply_text = f"@{username} Here's your meme! 🎭\n\n"
                reply_text += f"**Custom Meme:**\n\"{clean_text}\"\n\n"
                reply_text += f"Original tweet by @{original_tweet.user.screen_name}\n#MemeZap #MemeIt"
                
                self.api_v1.update_status(
                    status=reply_text,
                    in_reply_to_status_id=reply_tweet.id
                )
                
                logger.info(f"✅ Simple Meme It reply sent to @{username}")
                
        except Exception as e:
            logger.error(f"Error generating meme from tweet text: {e}")
            self.reply_meme_it_error(reply_tweet.id, reply_tweet.user.screen_name, "Error generating meme!")
    
    def clean_tweet_text_for_meme(self, text):
        """Clean tweet text for meme generation"""
        import re
        
        # Remove URLs
        text = re.sub(r'http\S+', '', text)
        # Remove mentions (except the original)
        text = re.sub(r'@\w+', '', text)
        # Remove hashtags
        text = re.sub(r'#\w+', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def generate_ai_caption_for_image(self, image_url, context_text):
        """Generate AI caption for image with context"""
        try:
            if hasattr(self.template_service, 'openai_client') and self.template_service.openai_client:
                prompt = f"""
                Generate a witty meme caption for this image context: "{context_text}"
                
                Make it:
                - Funny and relatable
                - Suitable for meme format
                - Under 100 characters
                - Viral-worthy
                
                Return just the caption text.
                """
                
                response = self.template_service.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a viral meme caption generator."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=50,
                    temperature=0.8
                )
                
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating AI caption: {e}")
        
        # Fallback
        return "When you see this tweet|And decide to meme it"
    
    def reply_meme_it_error(self, tweet_id, username, error_message):
        """Reply with error message for meme it requests"""
        try:
            reply_text = f"@{username} {error_message} 🤖\n\n💡 Try: Reply to any tweet with '@{self.bot_username} meme it'\n\n#MemeZap"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"📝 Meme It error reply sent to @{username}")
            
        except Exception as e:
            logger.error(f"Error sending meme it error reply: {e}")
    
    def extract_image_url(self, tweet):
        """Extract image URL from tweet"""
        try:
            # Check for images in the tweet
            if hasattr(tweet, 'entities') and 'media' in tweet.entities:
                for media in tweet.entities['media']:
                    if media['type'] == 'photo':
                        return media['media_url_https']
            
            if hasattr(tweet, 'extended_entities') and 'media' in tweet.extended_entities:
                for media in tweet.extended_entities['media']:
                    if media['type'] == 'photo':
                        return media['media_url_https']
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image URL: {e}")
            return None
    
    def get_image_from_context(self, tweet):
        """Get image from quoted tweet or reply chain"""
        try:
            # Check if this is a quote tweet
            if hasattr(tweet, 'quoted_status'):
                return self.extract_image_url(tweet.quoted_status)
            
            # Check if this is a reply
            if tweet.in_reply_to_status_id:
                try:
                    referenced_tweet = self.api_v1.get_status(
                        tweet.in_reply_to_status_id,
                        tweet_mode='extended',
                        include_entities=True
                    )
                    return self.extract_image_url(referenced_tweet)
                except:
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting image from context: {e}")
            return None
    
    def extract_meme_text(self, tweet_text):
        """Extract meme text from tweet"""
        import re
        
        # Remove bot mention
        text = re.sub(f'@{self.bot_username}', '', tweet_text, flags=re.IGNORECASE)
        
        # Remove trigger phrases
        for phrase in self.trigger_phrases:
            text = text.replace(phrase, "")
        
        # Remove other mentions and URLs
        words = text.split()
        filtered_words = [word for word in words if not word.startswith('@') and not word.startswith('http')]
        
        meme_text = ' '.join(filtered_words).strip()
        
        # Remove extra whitespace
        meme_text = re.sub(r'\s+', ' ', meme_text)
        
        # Default text if empty
        if not meme_text or len(meme_text) < 3:
            meme_text = "When someone mentions me|But forgets the text"
        
        return meme_text[:self.max_text_length]
    
    def reply_error(self, tweet_id, username):
        """Reply when error occurs"""
        try:
            reply_text = f"@{username} Sorry, I couldn't generate your meme right now! 😅 Please try again later.\n\n#MemeZap"
            
            self.api_v1.update_status(
                status=reply_text,
                in_reply_to_status_id=tweet_id
            )
            
            logger.info(f"⚠️ Error reply sent to @{username}")
            
        except Exception as e:
            logger.error(f"Error sending error reply: {e}")
    
    def run(self):
        """Enhanced bot main loop"""
        logger.info("🚀 Starting Enhanced MemeZap Bot...")
        logger.info(f"🎯 Listening for mentions of @{self.bot_username}")
        logger.info(f"🔗 MemeZap API: {self.memezap_api_url}")
        logger.info(f"⏱️ Check interval: {self.check_interval} seconds")
        logger.info(f"🧠 AI Features: Template Recognition ✓, Trend Analysis ✓, Persona Learning ✓")
        
        while True:
            try:
                logger.info("👀 Checking for new mentions with enhanced processing...")
                self.check_mentions()
                logger.info(f"😴 Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("🛑 Enhanced bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(60)

def main():
    """Entry point for enhanced bot"""
    try:
        bot = MemeZapBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start enhanced bot: {e}")

if __name__ == "__main__":
    main()