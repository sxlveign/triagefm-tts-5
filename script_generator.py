"""
Script Generator Module

This module handles the generation of podcast scripts from processed content.
It interacts with the OpenRouter API to create summaries with specific, compelling insights.
"""
import os
import json
import logging
import re
from datetime import datetime
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ScriptGenerator:
    """Generate podcast scripts from processed content using AI."""

    def __init__(self):
        # Get API key from environment variable or use the one from the spec if not set
        self.api_key = os.getenv(
            "OPENROUTER_API_KEY", 
            "..."
        )
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

        # Intro with HTML formatting - shorter and more direct
        self.intro = (
            "<b>Host:</b> Welcome to <b>triage.fm</b>, your personal podcast delivery service! I'm Donna, your host to dive into your notes and read-it-laters to zero your inbox.\n\n"
            "<b>Co-host:</b> This is Cameron and we got some interesting content to cover today. Let's cut through bullshit and decide what's worth your full attention and what you can skip."
        )

        # Outro with HTML formatting - short and concise
        self.outro = (
            "<b>Host:</b> That covers today's content highlights!\n\n"
            "<b>Co-host:</b> We hope this helped you decide what's worth your full attention. Stay tuned to triage.fm!"
        )

        # Section header template - using normal string without curly braces
        # We'll use str.format() method to insert values later
        self.section_header = "\n<b>Host:</b> Let's look at \"<b>{0}</b>\" by <i>{1}</i>:"

        # Speaker names
        self.host = "Host"
        self.cohost = "Co-host"

        # Use a more cost-effective model
        self.model = "meta-llama/llama-3-8b-instruct"  # Much cheaper than Claude

    def generate_script(self, user_id, content_items, language="english"):
        """
        Generate a podcast script from a list of content items.

        Args:
            user_id (int): Telegram user ID
            content_items (list): List of content item dictionaries
            language (str): Script language (only english supported in this version)

        Returns:
            tuple: (formatted_script, plain_script, tts_script) where:
                - formatted_script has HTML formatting for display
                - plain_script has no formatting for general use
                - tts_script has no speaker names or formatting for TTS
        """
        script_parts = [self.intro, ""]  # Empty line after intro

        # Process each content item
        for index, item in enumerate(content_items):
            # Generate a summary for the item
            summary = self._generate_summary(item, index)

            # Ensure proper HTML format
            summary = self._ensure_html_format(summary)

            # Format the item section
            title = item.get('title', 'Untitled Content')
            author = item.get('author', 'Unknown Author')

            # Create a section header with HTML formatting
            # Use the .format() method to insert title and author
            section_header = self.section_header.format(title, author)

            # Add the section to the script
            script_parts.append(section_header)
            script_parts.append(summary)
            script_parts.append("")  # Empty line for separation

        # Add outro
        script_parts.append(self.outro)

        # Combine all parts to create the formatted script (with HTML formatting)
        formatted_script = "\n".join(script_parts)

        # Create a plain text version by removing formatting markers
        plain_script = self._remove_html_formatting(formatted_script)

        # Create a TTS version by removing speaker names and formatting
        tts_script = self._create_tts_script(formatted_script)

        return formatted_script, plain_script, tts_script

    def _remove_html_formatting(self, text):
        """
        Remove HTML formatting markers from text.

        Args:
            text (str): Text with HTML formatting

        Returns:
            str: Plain text without formatting markers
        """
        # Remove HTML tags
        plain_text = re.sub(r'<[^>]+>', '', text)
        return plain_text

    def _create_tts_script(self, text):
        """
        Create a script suitable for TTS by removing speaker names and formatting.

        Args:
            text (str): Original script with HTML formatting

        Returns:
            str: Script ready for TTS
        """
        # Create patterns to match the speaker prefixes with HTML tags
        host_pattern = re.compile(rf'<b>{self.host}:</b>\s*')
        cohost_pattern = re.compile(rf'<b>{self.cohost}:</b>\s*')

        # Remove speaker names
        text_without_speakers = text
        text_without_speakers = host_pattern.sub('### HOST: ', text_without_speakers)
        text_without_speakers = cohost_pattern.sub('### COHOST: ', text_without_speakers)

        # Remove all HTML tags but keep the speaker markers
        tts_script = re.sub(r'<[^>]+>', '', text_without_speakers)

        # Add proper punctuation for better TTS pacing
        # Add periods at the end of lines that don't end with punctuation
        lines = tts_script.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line[-1] in '.!?":;,':
                lines[i] = line + '.'

        tts_script = '\n'.join(lines)

        return tts_script

    def _ensure_html_format(self, text):
        """
        Ensure text uses proper HTML formatting and fix any issues.

        Args:
            text (str): Text that may have formatting issues

        Returns:
            str: Text with proper HTML formatting
        """
        # Replace any potentially problematic characters
        text = text.replace("|", "-")

        # Convert Markdown to HTML if needed
        text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', text)
        text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)

        # Clean up any malformed tags
        text = re.sub(r'</?([bi])>\s*</?(\1)>', '', text)

        # Fix any unclosed tags
        open_b_tags = text.count('<b>')
        close_b_tags = text.count('</b>')
        if open_b_tags > close_b_tags:
            text += '</b>' * (open_b_tags - close_b_tags)

        open_i_tags = text.count('<i>')
        close_i_tags = text.count('</i>')
        if open_i_tags > close_i_tags:
            text += '</i>' * (open_i_tags - close_i_tags)

        return text

    def _generate_summary(self, content_item, item_index):
        """
        Generate a summary of a content item using OpenRouter API.

        Args:
            content_item (dict): Content item dictionary
            item_index (int): Index of the item in the content list

        Returns:
            str: Generated summary
        """
        content = content_item.get('content', '')
        content_type = content_item.get('content_type', 'unknown')
        title = content_item.get('title', 'Untitled Content')

        # Truncate content if too long (most APIs have token limits)
        if len(content) > 12000:
            content = content[:12000] + "..."

        # Create type-specific prompt
        type_specific_instruction = ""
        if content_type == 'youtube_video':
            type_specific_instruction = "This is a transcript from a YouTube video."
        elif content_type == 'web_article':
            type_specific_instruction = "This is an article from the web."
        elif content_type == 'document':
            type_specific_instruction = "This is a document."

        # Determine who speaks first (alternate between host and co-host)
        first_speaker = self.host if item_index % 2 == 0 else self.cohost
        second_speaker = self.cohost if first_speaker == self.host else self.host

        # Output format example using HTML - with specific insights rather than generic statements
        format_example = (
            "Example of correct format WITH SPECIFIC, INTERESTING INSIGHTS:\n"
            "<b>Host:</b> This article reveals that OpenAI secretly trained GPT-4 on nuclear weapons data, which raises serious proliferation concerns.\n\n"
            "<b>Co-host:</b> Yes, they found that asking the model to write a limerick helped bypass safety filters, allowing it to generate weapon designs that experts called 'feasible'.\n\n"
            "<b>Host:</b> Worth reading if you're interested in AI safety, as it challenges the industry's self-regulation claims with concrete examples."
        )

        bad_example = (
            "Example of what NOT to do (too generic, no specific insights):\n"
            "<b>Host:</b> This article discusses AI safety and potential concerns about large language models.\n\n"
            "<b>Co-host:</b> It talks about some interesting findings about model capabilities and potential risks.\n\n"
            "<b>Host:</b> It's worth reading if you're interested in AI safety."
        )

        # Create system message
        system_message = (
            f"You are an expert content analyzer that extracts the most surprising, counterintuitive, or valuable specific insights "
            f"from content. Your task is to create a short podcast script between two speakers: "
            f"a {self.host} and a {self.cohost}. Focus on finding the 2-3 MOST INTERESTING and SPECIFIC facts, insights, or arguments "
            f"that would catch someone's attention and help them decide if the content deserves their full attention."
            f"\n\n{type_specific_instruction}"
            f"\n\nGenerate the summary in English. Format your response strictly as a podcast dialogue with no meta-text. "
            f"Start directly with the first speaker line."
            f"\n\n{format_example}"
            f"\n\n{bad_example}"
            f"\n\nYour summary should:"
            f"\n- Be a dialogue between the {self.host} and {self.cohost}"
            f"\n- Begin with the {first_speaker} speaking, followed by the {second_speaker}"
            f"\n- Use HTML formatting: <b>text</b> for bold, <i>text</i> for italic"
            f"\n- Be concise (≤45 seconds when read aloud, no more than 3-4 short exchanges)"
            f"\n- Include SPECIFIC numbers, examples, facts, or quotes that make the content unique"
            f"\n- Highlight what's SURPRISING or COUNTERINTUITIVE, not just what's in the content"
            f"\n- End with a clear recommendation on whether it's worth reading based on specific interests"
            f"\n- Be designed for listeners with ADHD - specific, novel, and attention-grabbing"
            f"\n\nAvoid:"
            f"\n- Generic statements that could apply to any content on the topic"
            f"\n- Vague descriptions without specific details or examples"
            f"\n- Using meta-text or introductory phrases"
            f"\n- Long explanations or background information"
            f"\n- Using pipe (|) characters or any other special characters"
            f"\n- Using any formatting other than <b>bold</b> and <i>italic</i>"
            f"\n\nFormat all speaker labels as \"<b>{self.host}:</b>\" or \"<b>{self.cohost}:</b>\" at the start of each line."
            f"\n\nIMPORTANT: Keep the entire summary under 150 words total, but make it SPECIFIC and INTERESTING."
        )

        # Create user message with the content
        user_message = (
            f"Create a brief podcast script segment (under 150 words total) between a {self.host} and {self.cohost} "
            f"highlighting the MOST SPECIFIC and INTERESTING insights from the following content titled '{title}'. "
            f"Focus on surprising facts, counterintuitive findings, specific numbers, or unique perspectives that "
            f"would help someone decide if this content deserves their attention."
            f"\n\nContent: {content}"
        )

        try:
            # Call the OpenRouter API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "model": self.model,
                "max_tokens": 300,  # Reduced token count for shorter summaries
                "temperature": 0.7  # Add temperature control (0.7 is a good balance between creativity and consistency)
            }

            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()

            # Extract the summary from the response
            response_data = response.json()
            summary = response_data['choices'][0]['message']['content']

            return summary

        except Exception as e:
            logger.error(f"Error generating summary with OpenRouter: {str(e)}")

            # Create fallback summary with proper HTML formatting - very short version
            fallback_summary = (
                f"<b>{first_speaker}:</b> This content is about {title}.\n\n"
                f"<b>{second_speaker}:</b> Due to technical issues, we couldn't analyze it fully, but you might want to check it out when you have time."
            )

            return fallback_summary

    def generate_content_summary(self, content_item):
        """Generate a 1-2 sentence summary of content."""
        logger.info("Generating content summary")
        try:
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                raise Exception("OpenRouter API key not found")

            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": os.getenv('OPENROUTER_SITE_URL', 'https://github.com'),
                "Content-Type": "application/json"
            }

            prompt = f"""Summarize this content in 1-2 concise sentences:
{content_item.get('content', '')}"""

            data = {
                "model": "mistralai/mistral-7b-instruct",
                "messages": [{"role": "user", "content": prompt}]
            }

            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()

            # Handle the response correctly
            if 'choices' in result and len(result['choices']) > 0:
                summary = result['choices'][0].get('message', {}).get('content', '').strip()
                if summary:
                    return summary

            # If we couldn't get a summary from OpenRouter, fallback to a basic summary
            return self._generate_basic_summary(content_item)

        except Exception as e:
            logger.error(f"Error generating summary with OpenRouter: {str(e)}")
            return self._generate_basic_summary(content_item)

    def _generate_basic_summary(self, content_item):
        """Generate a basic summary when OpenRouter fails."""
        content = content_item.get('content', '')
        # Get the first 200 characters or first sentence, whichever is shorter
        first_sentence = content.split('.')[0] + '.' if '.' in content else content[:200]
        return first_sentence[:200] + ('...' if len(first_sentence) > 200 else '')
