"""
Database Module

This module handles all data persistence for the Onager bot.
For simplicity in the MVP, we'll use a JSON-based file storage system.
"""
import os
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    """Simple file-based database for content storage."""
    
    def __init__(self):
        """Initialize the database."""
        self.db_dir = "data"
        self.content_file = os.path.join(self.db_dir, "content.json")
        self.user_prefs_file = os.path.join(self.db_dir, "user_preferences.json")
    
    def initialize(self):
        """Create database files if they don't exist."""
        # Create data directory if it doesn't exist
        os.makedirs(self.db_dir, exist_ok=True)
        
        # Create content file if it doesn't exist
        if not os.path.exists(self.content_file):
            with open(self.content_file, 'w') as f:
                json.dump([], f)
        
        # Create user preferences file if it doesn't exist
        if not os.path.exists(self.user_prefs_file):
            with open(self.user_prefs_file, 'w') as f:
                json.dump({}, f)
        
        logger.info("Database initialized successfully")

    def is_duplicate(self, content_item, existing_content):
        """
        Check if content item is a duplicate based on content type.
        
        Args:
            content_item (dict): New content item to check
            existing_content (list): List of existing content items
        
        Returns:
            bool: True if content is duplicate, False otherwise
        """
        user_id = content_item.get('user_id')
        content_type = content_item.get('content_type')
        
        # Filter for user's content only
        user_content = [item for item in existing_content if item.get('user_id') == user_id]
        
        if not user_content:
            return False
            
        if content_type == 'web_article':
            # Check source URL for web articles
            source_url = content_item.get('source_url')
            return any(
                item.get('source_url') == source_url
                for item in user_content
                if item.get('content_type') == 'web_article' and not item.get('processed', False)
            )
            
        elif content_type == 'youtube_video':
            # Check source URL for YouTube videos
            source_url = content_item.get('source_url')
            return any(
                item.get('source_url') == source_url
                for item in user_content
                if item.get('content_type') == 'youtube_video' and not item.get('processed', False)
            )
            
        elif content_type == 'plain_text':
            # Check content text for plain text
            content = content_item.get('content', '').strip()
            return any(
                item.get('content', '').strip() == content
                for item in user_content
                if item.get('content_type') == 'plain_text' and not item.get('processed', False)
            )
            
        elif content_type == 'document':
            # Check title and content length for documents
            title = content_item.get('title')
            content = content_item.get('content', '').strip()
            return any(
                item.get('title') == title and len(item.get('content', '').strip()) == len(content)
                for item in user_content
                if item.get('content_type') == 'document' and not item.get('processed', False)
            )
            
        return False

    def add_content(self, content_item):
        """
        Add a new content item to the database if it's not a duplicate.
        
        Args:
            content_item (dict): Content item to add
        
        Returns:
            bool: True if content was added, False if it was a duplicate
        """
        try:
            # Load existing content
            content = self._load_content()
            
            # Check for duplicates
            if self.is_duplicate(content_item, content):
                logger.info(f"Duplicate content detected, skipping: {content_item.get('title')}")
                return False
                
            # Add new content item
            content.append(content_item)
            
            # Save updated content
            self._save_content(content)
            
            logger.info(f"Added content item with ID: {content_item.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding content item: {str(e)}")
            return False

    def get_unprocessed_content(self, user_id):
        """
        Get all unprocessed content for a user.
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            list: List of unprocessed content items
        """
        try:
            # Load all content
            content = self._load_content()
            
            # Filter for user's unprocessed content
            unprocessed = [
                item for item in content 
                if item.get('user_id') == user_id and not item.get('processed', False)
            ]
            
            return unprocessed
            
        except Exception as e:
            logger.error(f"Error getting unprocessed content: {str(e)}")
            return []
    
    def mark_content_as_processed(self, user_id, content_ids):
        """
        Mark content items as processed.
        
        Args:
            user_id (int): Telegram user ID
            content_ids (list): List of content IDs to mark as processed
        """
        try:
            # Load all content
            content = self._load_content()
            
            # Mark specified content as processed
            for item in content:
                if (item.get('user_id') == user_id and 
                    item.get('id') in content_ids and 
                    not item.get('processed', False)):
                    item['processed'] = True
                    item['date_processed'] = datetime.now().isoformat()
            
            # Save updated content
            self._save_content(content)
            
            logger.info(f"Marked {len(content_ids)} items as processed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error marking content as processed: {str(e)}")
    
    def clear_unprocessed_content(self, user_id):
        """
        Clear all unprocessed content for a user.
        
        Args:
            user_id (int): Telegram user ID
        """
        try:
            # Load all content
            content = self._load_content()
            
            # Filter out user's unprocessed content
            updated_content = [
                item for item in content 
                if not (item.get('user_id') == user_id and not item.get('processed', False))
            ]
            
            # Save updated content
            self._save_content(updated_content)
            
            logger.info(f"Cleared unprocessed content for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error clearing unprocessed content: {str(e)}")
    
    def get_user_language(self, user_id):
        """
        Get a user's preferred language.
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            str: Language code (english, chinese, russian) or None if not set
        """
        try:
            # Load user preferences
            user_prefs = self._load_user_preferences()
            
            # Convert user_id to str for JSON dictionary keys
            user_id_str = str(user_id)
            
            # Get language preference
            if user_id_str in user_prefs and 'language' in user_prefs[user_id_str]:
                return user_prefs[user_id_str]['language']
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user language: {str(e)}")
            return None
    
    def set_user_language(self, user_id, language):
        """
        Set a user's preferred language.
        
        Args:
            user_id (int): Telegram user ID
            language (str): Language code (english, chinese, russian)
        """
        try:
            # Load user preferences
            user_prefs = self._load_user_preferences()
            
            # Convert user_id to str for JSON dictionary keys
            user_id_str = str(user_id)
            
            # Initialize user preferences if not exists
            if user_id_str not in user_prefs:
                user_prefs[user_id_str] = {}
            
            # Set language preference
            user_prefs[user_id_str]['language'] = language
            
            # Save updated preferences
            self._save_user_preferences(user_prefs)
            
            logger.info(f"Set language preference for user {user_id} to {language}")
            
        except Exception as e:
            logger.error(f"Error setting user language: {str(e)}")
    
    def _load_content(self):
        """
        Load content from the database file.
        
        Returns:
            list: List of content items
        """
        try:
            with open(self.content_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading content: {str(e)}")
            return []
    
    def _save_content(self, content):
        """
        Save content to the database file.
        
        Args:
            content (list): List of content items to save
        """
        try:
            with open(self.content_file, 'w') as f:
                json.dump(content, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving content: {str(e)}")
    
    def _load_user_preferences(self):
        """
        Load user preferences from the database file.
        
        Returns:
            dict: User preferences
        """
        try:
            with open(self.user_prefs_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user preferences: {str(e)}")
            return {}
    
    def _save_user_preferences(self, user_prefs):
        """
        Save user preferences to the database file.
        
        Args:
            user_prefs (dict): User preferences to save
        """
        try:
            with open(self.user_prefs_file, 'w') as f:
                json.dump(user_prefs, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user preferences: {str(e)}")
