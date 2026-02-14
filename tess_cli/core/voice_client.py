import os
import sys
import logging
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
import threading
import time

logger = logging.getLogger("VoiceClient")

class VoiceClient:
    """
    Handles audio recording (via sounddevice) and transcription (via local Whisper).
    """
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = None
        self.is_recording = False
        self.audio_dir = os.path.join(os.getcwd(), "data", "voice")
        if not os.path.exists(self.audio_dir):
            os.makedirs(self.audio_dir)
            
        # Lazy load model to speed up startup if not used immediately
        self.model_loaded = False

    def load_model(self):
        """Loads the Whisper model into memory."""
        if self.model_loaded:
            return
            
        logger.info(f"Loading Whisper model ({self.model_size})... This may take a moment.")
        try:
            self.model = whisper.load_model(self.model_size)
            self.model_loaded = True
            logger.info("Whisper model loaded.")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            raise e

    def record_audio(self, duration=5, sample_rate=44100):
        """
        Records audio for a fixed duration.
        """
        logger.info(f"Recording for {duration} seconds...")
        try:
            recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait() # Wait until recording is finished
            logger.info("Recording finished.")
            
            # Save to file
            filename = f"voice_{int(time.time())}.wav"
            filepath = os.path.join(self.audio_dir, filename)
            wav.write(filepath, sample_rate, recording)
            
            return filepath
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            return None

    def listen(self, sample_rate=16000, silence_duration=1.5, max_duration=30):
        """
        Smart Listening: Records until silence is detected.
        Returns path to saved wav file.
        """
        logger.info("Adjusting for ambient noise... (Please stay quiet)")
        try:
            # 1. Calibrate Silence (0.5s)
            calibration_frames = int(sample_rate * 0.5)
            calib_data = sd.rec(calibration_frames, samplerate=sample_rate, channels=1, dtype='int16')
            sd.wait()
            
            # Calculate ambient noise energy (Root Mean Square)
            noise_rms = np.sqrt(np.mean(calib_data**2))
            threshold = max(noise_rms * 1.5, 300) # Minimum threshold to avoid pure silence triggering
            logger.info(f"Threshold set to: {threshold:.2f} (Noise: {noise_rms:.2f})")
            
            print("🎤 Listening... (Speak now)")
            
            # 2. Record Loop
            frames = []
            silent_chunks = 0
            chunk_duration = 0.2 # 200ms
            chunk_size = int(sample_rate * chunk_duration)
            retention_chunks = int(silence_duration / chunk_duration)
            
            max_chunks = int(max_duration / chunk_duration)
            
            with sd.InputStream(samplerate=sample_rate, channels=1, dtype='int16') as stream:
                for _ in range(max_chunks):
                    data, overflow = stream.read(chunk_size)
                    frames.append(data)
                    
                    # Check Energy
                    energy = np.sqrt(np.mean(data**2))
                    
                    if energy < threshold:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0 # Reset if speech detected
                        
                    # Stop if silence persists
                    if silent_chunks > retention_chunks:
                        logger.info("Silence detected. Stopping.")
                        break
                        
            # 3. Save
            recording = np.concatenate(frames, axis=0)
            
            # Don't save if it was ALL silence (very short)
            if len(recording) < sample_rate * 1.0: # Less than 1 second total
                logger.warning("Recording too short/empty.")
                return None
                
            filename = f"voice_{int(time.time())}.wav"
            filepath = os.path.join(self.audio_dir, filename)
            wav.write(filepath, sample_rate, recording)
            return filepath
            
        except Exception as e:
            logger.error(f"Smart Listen failed: {e}")
            return None

    def transcribe(self, audio_file):
        """
        Transcribes the given audio file using Whisper.
        """
        if not self.model_loaded:
            self.load_model()
            
        if not audio_file or not os.path.exists(audio_file):
            logger.error(f"Audio file not found: {audio_file}")
            return ""
            
        logger.info(f"Transcribing {audio_file}...")
        try:
            # Whisper handles ffmpeg loading internally
            # Use 'fp16=False' to avoid warnings on CPU
            result = self.model.transcribe(audio_file, fp16=False)
            text = result["text"].strip()
            logger.info(f"Transcription: {text}")
            return text
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    def speak(self, text, provider="auto"):
        """
        Converts text to speech using Google Cloud (Premium) or pyttsx3 (Offline).
        """
        logger.info(f"Speaking: {text}")
        
        # 1. Try Google Cloud TTS
        if provider in ["auto", "google"]:
            key_path = os.path.join(os.getcwd(), "google_key.json")
            if os.path.exists(key_path):
                try:
                    from google.cloud import texttospeech
                    from google.oauth2 import service_account
                    
                    credentials = service_account.Credentials.from_service_account_file(key_path)
                    client = texttospeech.TextToSpeechClient(credentials=credentials)
                    
                    synthesis_input = texttospeech.SynthesisInput(text=text)
                    
                    # Builidng the voice request (Neural / WaveNet)
                    voice = texttospeech.VoiceSelectionParams(
                        language_code="en-US",
                        name="en-US-Journey-F", # Premium Journey voice (or en-US-Neural2-F)
                        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
                    )
                    
                    audio_config = texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3
                    )
                    
                    response = client.synthesize_speech(
                        input=synthesis_input, voice=voice, audio_config=audio_config
                    )
                    
                    # Save and Play
                    filename = f"tts_{int(time.time())}.mp3"
                    filepath = os.path.join(self.audio_dir, filename)
                    
                    with open(filepath, "wb") as out:
                        out.write(response.audio_content)
                        
                    # Play using PowerShell (Reliable on Windows, plays MP3)
                    # playsound library is notoriously flaky on Windows (often ModuleNotFoundError or codec issues)
                    try:
                        # Use PowerShell to spawn a media player and wait for it
                        subprocess_cmd = f'powershell -c (New-Object Media.SoundPlayer "{filepath}").PlaySync();'
                        # Note: SoundPlayer ONLY supports .wav. For .mp3 we need a different approach context.
                        # Wait, SoundPlayer is WAV only.
                        # For MP3 on Windows via CLI, we can use the default handler or a hidden start
                        
                        # Better approach for MP3: 
                        # os.system(f'start /min "" "{filepath}"') # This opens a window. Bad.
                        
                        # Use playsound IF available, but handle error gracefully.
                        # BUT user has "No module named playsound".
                        
                        # Alternative: Use simpleaudio (WAV only) or pygame.
                        # OR: Use a PowerShell snippet that handles MP3 (using MediaPlayer)
                        
                        ps_script = f"""
                        $player = New-Object -ComObject WScript.Shell
                        $player.Run("wmplayer /play /close \\"{filepath}\\"", 0, $true)
                        """
                        # wmplayer might be overkill.
                        
                        # Let's fallback to pyttsx3 for now if playsound is missing, OR stick to converting response to WAV?
                        # Google TTS outputting MP3 is standard.
                        
                        # Installing playsound was supposed to fix this.
                        # If I simply import playsound inside the function, it failed.
                        
                        # Let's try importing playsound carefully.
                        import playsound
                        playsound.playsound(filepath)
                        return True
                        
                    except ImportError:
                        logger.warning("playsound module not found. Playing via system default.")
                        os.system(f'start /min "" "{filepath}"') # Fallback
                        return True
                    except Exception as e:
                        logger.error(f"Playback failed: {e}")
                        # Fallback to system default
                        os.system(f'start /min "" "{filepath}"')
                        return True

                except Exception as e:
                    logger.error(f"Google TTS Failed: {e}")
                    if provider == "google": return False
            else:
                if provider == "google":
                    logger.warning("Google Key not found (google_key.json).")
                    return False

        # 2. Fallback to pyttsx3
        try:
            import pyttsx3
            engine = pyttsx3.init()
            # Set Zira if available (Index 1 usually)
            voices = engine.getProperty('voices')
            if len(voices) > 1:
                engine.setProperty('voice', voices[1].id)
                
            engine.say(text)
            engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"pyttsx3 Failed: {e}")
            return False

if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    client = VoiceClient()
    # file = client.record_audio(3)
    # print(client.transcribe(file))
