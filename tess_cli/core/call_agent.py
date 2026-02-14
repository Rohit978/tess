import time
import threading
import os
from .logger import setup_logger

logger = setup_logger("CallAgent")

class CallAgent:
    """
    Handles the active conversation loop: Listen -> Think -> Speak.
    """
    def __init__(self, brain, voice_client):
        self.brain = brain
        self.voice = voice_client
        self.is_active = False
        self.conversation_history = [] # Temporary history for the call
        
    def start_call_loop(self, contact_name, mission=None):
        """
        Starts the conversational loop.
        """
        if self.is_active:
            logger.warning("Call already active.")
            return

        self.is_active = True
        logger.info(f"Call Agent Started for {contact_name}")
        
        # Initial Greeting
        greeting = "Hello? This is Tess."
        self.voice.speak(greeting)
        self.conversation_history.append({"role": "assistant", "content": greeting})
        
        while self.is_active:
            try:
                # 1. LISTEN
                logger.info("Listening...")
                # Use smart listen (records until silence)
                audio_path = self.voice.listen(max_duration=15) 
                
                if not audio_path:
                    logger.info("Nothing heard (or timeout). Continuing...")
                    continue
                    
                # 2. TRANSCRIBE
                text = self.voice.transcribe(audio_path)
                if not text or len(text) < 2: # Ignore noise
                    continue
                    
                logger.info(f"Caller said: {text}")
                self.conversation_history.append({"role": "user", "content": text})
                
                # Check for exit phrases
                if any(x in text.lower() for x in ["bye", "goodbye", "hang up", "stop call"]):
                    self.voice.speak("Goodbye.")
                    self.stop()
                    break

                # 3. THINK (Fast, Conversational)
                mission_context = f"MISSION: {mission}" if mission else "Assist the caller."
                system_prompt = f"""
                You are TESS, speaking on the phone on behalf of Rohit.
                {mission_context}
                
                STYLE:
                - Be concise and natural (spoken word).
                - Use fillers like "Um", "Uh", "Okay" sparingly if it sounds natural.
                - Do not be robotic.
                - Keep answers short (1-2 sentences).
                
                CONTEXT:
                You are talking to {contact_name}.
                """
                
                # Construct messages for Brain
                messages = [{"role": "system", "content": system_prompt}] + self.conversation_history[-6:]
                
                # Use json_mode=False for natural text
                reply = self.brain.request_completion(messages, json_mode=False, temperature=0.6)
                
                if not reply:
                    reply = "I didn't catch that. Could you repeat?"
                    
                logger.info(f"TESS says: {reply}")
                self.conversation_history.append({"role": "assistant", "content": reply})
                
                # 4. SPEAK
                self.voice.speak(reply)
                
                # Small buffer to avoid hearing own echo if echo cancellation isn't perfect
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Call Loop Error: {e}")
                time.sleep(1)
                
        logger.info("Call Agent Stopped.")

    def stop(self):
        self.is_active = False
