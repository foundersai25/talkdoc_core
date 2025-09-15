from core.talkdoc_core.prompts import get_system_prompt_for_chat
import openai
from openai import OpenAI
import logging
import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat

logging.basicConfig(level=logging.INFO)


class GPTService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)

    def chat(
        self,
        messages,
        model: str = "gpt-4.1",
        stream: bool = True,
        json_mode: bool = False,
    ):
        try:
            params = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }

            if json_mode:
                params["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**params)

            if stream:
                return response

            return response.choices[0].message.content

        except openai.error.OpenAIError as e:
            logging.error(f"OpenAI API error: {e}")
            raise

    def add_system_prompt_for_chat(self, json_fields):
        return [{"role": "system", "content": get_system_prompt_for_chat(json_fields)}]

    def add_user_prompt(self, messages, user_input):
        return messages + [{"role": "user", "content": user_input}]

    def add_assistant_response(self, messages, response):
        return messages + [{"role": "assistant", "content": response}]

    def check_openai_api_key(self):
        try:
            self.client.models.list()
            return True
        except openai.AuthenticationError:
            logging.error("Invalid OpenAI API key")
            return False


class Agno_Service:  
    def __init__(self, api_key: str = None):

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        
        # Validierung des API Keys
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set and no api_key provided")
        
        # Standard OpenAI Client für Fallback
        self.client = OpenAI(api_key=self.api_key)
        
        # Google Maps Tool hinzufügen
        tools = []
        
        try:
            from core.talkdoc_core.agents import validate_address
            
            # Standalone Tool-Funktion direkt hinzufügen
            tools.append(validate_address)
            
            logging.info("Google Maps Adressvalidierung erfolgreich hinzugefügt")
        except Exception as e:
            logging.warning(f"Google Maps Adressvalidierung konnte nicht hinzugefügt werden: {e}")
            logging.warning("Agent läuft ohne Adressvalidierung")
        
        self.agent = Agent(
            model=OpenAIChat(id="gpt-4o", api_key=self.api_key),
            tools=tools,
            markdown=True,
            debug_mode=True  # Debug-Modus aktivieren um Tool-Calls zu sehen
        )
    
    def chat(
        self,
        messages,
        model: str = "gpt-4o",
        stream: bool = True,
        json_mode: bool = False,
    ):
        try:
            # Verwende Agno Agent direkt - lass ihn Tools automatisch verwenden
            logging.info("Verwende Agno Agent direkt")
            
            # Hole die letzte User-Nachricht für Agno
            user_message = ""
            if messages:
                # Finde die letzte User-Nachricht
                for msg in reversed(messages):
                    if msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        break
            
            if not user_message:
                logging.warning("Keine User-Nachricht gefunden, verwende Fallback")
                return self._fallback_chat(messages, model, stream, json_mode)
            
            logging.info(f"Verarbeite User-Nachricht mit Agno: {user_message}")
            
            # Verwende Agno's eingebaute Response-Methode
            if stream:
                # Für Streaming müssen wir die Response simulieren
                response_content = self.agent.run(user_message)
                return self._create_streaming_response(response_content.content)
            else:
                response_content = self.agent.run(user_message)
                logging.info(f"Agno Response: {response_content.content}")
                return response_content.content

        except Exception as e:
            logging.error(f"Agno Service error: {e}")
            # Fallback zu normalem Chat
            return self._fallback_chat(messages, model, stream, json_mode)
    
    
    def _create_streaming_response(self, content: str):
        """
        Erstellt eine Streaming-ähnliche Response für Kompatibilität.
        """
        # Simuliere OpenAI Streaming Response Format
        class StreamingResponse:
            def __init__(self, content):
                self.content = content
                self.chunks = [{'choices': [{'delta': {'content': content}}]}]
            
            def __iter__(self):
                for chunk in self.chunks:
                    yield type('StreamChunk', (), chunk)
        
        return StreamingResponse(content)
    
    def _fallback_chat(self, messages, model, stream, json_mode):
        """
        Fallback zu normalem OpenAI Chat ohne Agno.
        """
        try:
            params = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }

            if json_mode:
                params["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**params)

            if stream:
                return response

            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Fallback chat error: {e}")
            raise
    
    
    # Interface-Kompatibilität mit GPTService
    def add_system_prompt_for_chat(self, json_fields):
        """
        Kompatibilität mit GPTService - fügt System-Prompt hinzu.
        """
        return [{"role": "system", "content": get_system_prompt_for_chat(json_fields)}]

    def add_user_prompt(self, messages, user_input):
        """
        Kompatibilität mit GPTService - fügt User-Prompt hinzu.
        """
        return messages + [{"role": "user", "content": user_input}]

    def add_assistant_response(self, messages, response):
        """
        Kompatibilität mit GPTService - fügt Assistant-Response hinzu.
        """
        return messages + [{"role": "assistant", "content": response}]

    def check_openai_api_key(self):
        """
        Kompatibilität mit GPTService - prüft OpenAI API Key.
        """
        try:
            self.client.models.list()
            return True
        except openai.AuthenticationError:
            logging.error("Invalid OpenAI API key")
            return False
    
