"""
Text-to-Speech processor for converting podcast scripts to audio using Google TTS
With proper multi-voice support that properly distinguishes between speakers
"""
import os
import time
import logging
from typing import Optional
from gtts import gTTS
import re
from pydub import AudioSegment
from pydub.effects import speedup

logger = logging.getLogger(__name__)

class TTSProcessor:
    def __init__(self):
        """Initialize the TTS processor"""
        # Create a directory for audio files if it doesn't exist
        self.audio_dir = "temp/audio"
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Maximum size for each audio chunk (in characters)
        # gTTS has limitations on text length
        self.max_chunk_size = 4000
        
        # Ensure proper silence between segments
        self.segment_silence_ms = 500  # Slightly shorter pauses for better ADHD attention
        
        # Voice settings for different speakers using non-deprecated codes
        self.voice_settings = {
            "host": "en",      # English for host
            "cohost": "en"     # English for co-host
        }
        
        # Speed factor for processing (1.0 = normal speed, higher = faster)
        # Slightly faster pace helps retain ADHD attention
        self.speed_factor = 1.15

    def generate_audio(self, script: str, language: str = "english", filename: Optional[str] = None) -> str:
        """Convert text to speech using Google TTS with proper multi-voice support."""
        try:
            # Generate a filename if not provided
            if filename is None:
                timestamp = int(time.time())
                filename = f"podcast_{timestamp}.mp3"
            
            filepath = os.path.join(self.audio_dir, filename)
            
            # Split script by speaker markers
            segments = self._split_by_speakers(script)
            logger.info(f"Split script into {len(segments)} speaker segments")
            
            # Process each segment with the appropriate voice and combine them
            combined_audio = None
            
            for segment in segments:
                if not segment['text'].strip():
                    continue  # Skip empty segments
                
                # Clean the text for TTS
                cleaned_text = self._clean_for_tts(segment['text'])
                if not cleaned_text.strip():
                    continue  # Skip if cleaning removed all content
                
                # Process the segment with the appropriate voice
                temp_path = os.path.join(self.audio_dir, f"temp_segment_{time.time()}.mp3")
                
                try:
                    # Select voice based on speaker
                    voice = self.voice_settings["host"] if segment['speaker'] == 'HOST' else self.voice_settings["cohost"]
                    
                    # Generate TTS for this segment
                    tts = gTTS(text=cleaned_text, lang=voice, slow=False)
                    tts.save(temp_path)
                    
                    # Load the audio segment
                    segment_audio = AudioSegment.from_mp3(temp_path)
                    
                    # Apply ADHD-friendly audio processing
                    segment_audio = self._process_audio_for_adhd(segment_audio, is_host=(segment['speaker'] == 'HOST'))
                    
                    # Add to combined audio
                    if combined_audio is None:
                        combined_audio = segment_audio
                    else:
                        # Add a small pause between segments for natural speech
                        silence = AudioSegment.silent(duration=self.segment_silence_ms)
                        combined_audio = combined_audio + silence + segment_audio
                    
                    # Clean up temp file
                    os.remove(temp_path)
                    
                except Exception as e:
                    logger.error(f"Error processing segment: {str(e)}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    continue  # Try next segment even if one fails
            
            # Save the final combined audio
            if combined_audio:
                # Add intro/outro effects
                final_audio = self._add_bookend_effects(combined_audio)
                
                final_audio.export(filepath, format="mp3")
                logger.info(f"Generated multi-voice audio file at {filepath}")
                return filepath
            else:
                logger.error("Failed to create combined audio - no segments were processed")
                raise Exception("Failed to generate audio segments")
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            raise
    
    def _split_by_speakers(self, text: str) -> list:
        """Split text into segments by speaker markers."""
        segments = []
        current_speaker = None
        current_text = []

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            if line.startswith('### HOST:'):
                if current_speaker and current_text:
                    segments.append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text)
                    })
                current_speaker = 'HOST'
                current_text = [line.replace('### HOST:', '').strip()]
            elif line.startswith('### COHOST:'):
                if current_speaker and current_text:
                    segments.append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text)
                    })
                current_speaker = 'COHOST'
                current_text = [line.replace('### COHOST:', '').strip()]
            else:
                if current_speaker:
                    current_text.append(line)

        # Add the last segment
        if current_speaker and current_text:
            segments.append({
                'speaker': current_speaker,
                'text': ' '.join(current_text)
            })

        return segments

    def _process_audio_for_adhd(self, segment, is_host=True):
        """
        Apply ADHD-friendly processing to an audio segment
        
        Args:
            segment: The AudioSegment to process
            is_host: Whether this is the host's voice
            
        Returns:
            The processed AudioSegment
        """
        # Different processing for host vs cohost for more distinct voices
        if is_host:
            # Host voice - slightly faster with a bit more bass
            segment = speedup(segment, self.speed_factor, 150)
            # Add a slight bass boost to host voice
            segment = segment.low_pass_filter(2000)
        else:
            # Cohost voice - slightly slower with a bit more treble
            segment = speedup(segment, self.speed_factor * 0.9, 150)
            # Add a slight treble boost to cohost voice
            segment = segment.high_pass_filter(1000)
        
        # Normalize the volume for consistent listening experience
        segment = segment.normalize()
        
        return segment
    
    def _add_bookend_effects(self, audio):
        """
        Add subtle attention-focusing effects at beginning and end
        
        Args:
            audio: The main audio content
            
        Returns:
            AudioSegment with added effects
        """
        # For simplicity, we're just adding a short silence at the beginning and end
        # In a more advanced implementation, you could add gentle tones or transitions
        start_silence = AudioSegment.silent(duration=500)
        end_silence = AudioSegment.silent(duration=750)
        
        return start_silence + audio + end_silence
    
    def _chunk_text(self, text: str) -> list:
        """
        Split text into chunks suitable for TTS.
        
        Args:
            text (str): Text to split
            
        Returns:
            list: List of text chunks
        """
        # Split by sentences for more natural breaks
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) + 1 <= self.max_chunk_size:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = sentence
                else:
                    # If the sentence itself is too long, split it by commas
                    phrase_parts = sentence.split(', ')
                    if len(phrase_parts) > 1:
                        current_phrase = ""
                        for part in phrase_parts:
                            if len(current_phrase) + len(part) + 2 <= self.max_chunk_size:
                                if current_phrase:
                                    current_phrase += ", " + part
                                else:
                                    current_phrase = part
                            else:
                                chunks.append(current_phrase)
                                current_phrase = part
                        
                        if current_phrase:
                            current_chunk = current_phrase
                    else:
                        # Last resort: split by words
                        chunks.append(sentence[:self.max_chunk_size])
                        if len(sentence) > self.max_chunk_size:
                            current_chunk = sentence[self.max_chunk_size:]
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _clean_for_tts(self, text: str) -> str:
        """Clean text to make it more suitable for TTS."""
        # Remove any remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Replace quotes with spoken equivalents
        text = text.replace('"', ' ')
        text = text.replace("'", ' ')
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Add proper pauses for punctuation
        text = text.replace('...', '. ')
        text = text.replace('--', ', ')
        
        # Clean up bullet points and list markers
        text = re.sub(r'^\s*[-•*]\s*', '', text)
        text = re.sub(r'\n\s*[-•*]\s*', ' ', text)
        
        # Ensure proper ending punctuation
        text = text.strip()
        if text and not text[-1] in '.!?:;,':
            text = text + '.'
        
        return text

    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Clean up old audio files to prevent disk space issues
        
        Args:
            max_age_hours (int): Maximum age of files to keep in hours
        """
        try:
            current_time = time.time()
            for filename in os.listdir(self.audio_dir):
                filepath = os.path.join(self.audio_dir, filename)
                if os.path.getmtime(filepath) < current_time - (max_age_hours * 3600):
                    os.remove(filepath)
                    logger.info(f"Removed old audio file: {filepath}")
        except Exception as e:
            logger.error(f"Error cleaning up old files: {str(e)}")
