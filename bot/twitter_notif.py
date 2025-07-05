#!/usr/bin/env python3
"""
Twitter Notification System for MemeZap
Automatically posts promotional tweets when memes are generated via smart_generate API
"""

import tweepy
import os
import logging
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image
import tempfile
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class TwitterNotificationService:
    """Service to post promotional tweets when memes are generated"""
    
    def __init__(self):
        """Initialize Twitter notification service"""
        # Load Twitter API credentials
        self.api_key = os.getenv('TWITTER_API_KEY')
        self.api_secret = os.getenv('TWITTER_API_SECRET')
        self.access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
        
        # Initialize OpenAI client
        self.openai_client = None
        if os.getenv('OPENAI_API_KEY'):
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            logger.warning("OpenAI API key not found. Will use default promotional messages.")
        
        if not all([self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            logger.error("Missing Twitter API credentials")
            raise ValueError("Missing Twitter API credentials in environment variables")
        
        # Setup Twitter clients
        self.setup_twitter_clients()
        
        # Configuration
        self.enabled = os.getenv('TWITTER_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        
    def setup_twitter_clients(self):
        """Setup Twitter API clients using OAuth1UserHandler"""
        try:
            # Twitter API v1.1 (for media upload) - using OAuth1UserHandler
            auth = tweepy.OAuth1UserHandler(self.api_key, self.api_secret)
            auth.set_access_token(self.access_token, self.access_token_secret)
            self.api_v1 = tweepy.API(auth, wait_on_rate_limit=True)
            
            # Twitter API v2 (for posting tweets) - using Client with proper auth
            self.client_v2 = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Test authentication
            me = self.api_v1.verify_credentials()
            logger.info(f"🤖 Twitter notification service authenticated as @{me.screen_name}")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Twitter API: {e}")
            raise
    
    def generate_promotional_tweet(self, input_text, meme_generated=True):
        """Generate a promotional tweet using OpenAI"""
        if not self.openai_client:
            # Fallback promotional messages
            fallback_messages = [
                f"🔥 Just generated an epic meme! Someone said: '{input_text}' and our AI-powered MemeZap engine created pure gold! ✨ #MemeGeneration #AI #Memes",
                f"💡 Another masterpiece created! Input: '{input_text}' → Output: Viral meme potential! 🚀 Try MemeZap for your own meme magic! #MemeZap #AIArt",
                f"🎯 MemeZap strikes again! From '{input_text}' to meme perfection in seconds! Our AI knows what's funny 😂 #MemeMaker #TechMagic",
                f"⚡ Fresh meme alert! Someone dropped '{input_text}' and we turned it into comedy gold! 🏆 #MemeGeneration #Innovation #Viral"
            ]
            import random
            return random.choice(fallback_messages)
        
        try:
            # Create a prompt for OpenAI to generate an engaging promotional tweet
            prompt = f"""
            Create an engaging, fun promotional tweet for our meme generation platform called MemeOS. 
            
            Context:
            - Someone just used our AI-powered meme generator
            - Their input text was: "{input_text}"
            - We successfully generated a meme from their text
            - We want to create buzz about our meme generation engine
            - Keep it under 280 characters
            - Make it sound exciting and viral-worthy
            - Include relevant hashtags
            - Don't be too salesy, make it fun and engaging
            - Mention that it's AI-powered
            
            Generate a single tweet that celebrates this meme creation and promotes our platform.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a social media expert who creates viral, engaging tweets for a meme generation platform. Keep tweets fun, energetic, and under 280 characters."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.8
            )
            
            tweet_text = response.choices[0].message.content.strip()
            
            # Ensure it's under 280 characters (leaving room for media)
            if len(tweet_text) > 250:
                tweet_text = tweet_text[:247] + "..."
            
            logger.info(f"Generated promotional tweet: {tweet_text}")
            return tweet_text
            
        except Exception as e:
            logger.error(f"Error generating promotional tweet with OpenAI: {e}")
            # Fallback to default message
            return f"🔥 Just generated another epic meme! Input: '{input_text}' → Pure meme magic! ✨ Try MemeZap for AI-powered meme creation! #MemeZap #AI #Memes"
    
    def download_image(self, image_path_or_url):
        """Download image from local path or URL and return as BytesIO"""
        try:
            if image_path_or_url.startswith('http'):
                # Download from URL
                response = requests.get(image_path_or_url, timeout=30)
                response.raise_for_status()
                return BytesIO(response.content)
            else:
                # Read from local file
                with open(image_path_or_url, 'rb') as f:
                    return BytesIO(f.read())
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    def post_meme_notification(self, input_text, meme_image_path, from_template=False, similarity_score=0):
        """Post a promotional tweet with the generated meme"""
        if not self.enabled:
            logger.info("Twitter notifications are disabled")
            return False
        
        try:
            # Generate promotional tweet text
            tweet_text = self.generate_promotional_tweet(input_text)
            
            # Add template info if applicable
            if from_template and similarity_score > 0:
                template_info = f" 🎯 {similarity_score:.1f}% template match!"
                if len(tweet_text) + len(template_info) <= 280:
                    tweet_text += template_info
            
            # Download the meme image
            image_data = self.download_image(meme_image_path)
            if not image_data:
                logger.error("Failed to download meme image for Twitter post")
                return False
            
            # Save image to temporary file for upload
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                temp_file.write(image_data.getvalue())
                temp_file_path = temp_file.name
            
            try:
                # Upload media using simple_upload (like in reference code)
                media = self.api_v1.simple_upload(filename=temp_file_path)
                media_id = media.media_id
                
                # Post tweet with media using v2 client
                tweet = self.client_v2.create_tweet(
                    text=tweet_text,
                    media_ids=[media_id]
                )
                
                logger.info(f"✅ Successfully posted promotional tweet: {tweet.data['id']}")
                logger.info(f"Tweet text: {tweet_text}")
                return True
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            
        except tweepy.TooManyRequests:
            logger.warning("⏰ Twitter rate limit hit, skipping notification")
            return False
        except Exception as e:
            logger.error(f"Error posting meme notification to Twitter: {e}")
            return False
    
    def post_simple_notification(self, input_text):
        """Post a simple text-only notification (fallback)"""
        if not self.enabled:
            logger.info("Twitter notifications are disabled")
            return False
        
        try:
            tweet_text = self.generate_promotional_tweet(input_text)
            
            tweet = self.client_v2.create_tweet(text=tweet_text)
            
            logger.info(f"✅ Successfully posted simple promotional tweet: {tweet.data['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting simple notification to Twitter: {e}")
            return False

# Global instance for easy import
twitter_notifier = TwitterNotificationService()

def notify_meme_generated(input_text, meme_image_path, from_template=False, similarity_score=0):
    """
    Convenience function to notify about meme generation
    
    Args:
        input_text (str): The original text input from user
        meme_image_path (str): Path to the generated meme image
        from_template (bool): Whether a template was used
        similarity_score (float): Template similarity score (0-100)
    
    Returns:
        bool: True if notification was posted successfully
    """
    try:
        return twitter_notifier.post_meme_notification(
            input_text=input_text,
            meme_image_path=meme_image_path,
            from_template=from_template,
            similarity_score=similarity_score
        )
    except Exception as e:
        logger.error(f"Error in notify_meme_generated: {e}")
        return False

def notify_simple(input_text):
    """
    Simple notification without image
    
    Args:
        input_text (str): The original text input from user
    
    Returns:
        bool: True if notification was posted successfully
    """
    try:
        return twitter_notifier.post_simple_notification(input_text)
    except Exception as e:
        logger.error(f"Error in notify_simple: {e}")
        return False
