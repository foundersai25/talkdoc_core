from core.talkdoc_core.prompts import get_system_prompt_for_chat
import openai
from openai import OpenAI
import logging
import os

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.azure import AzureOpenAI
logging.basicConfig(level=logging.INFO)


class Agno_Service:  
    def __init__(self, api_key: str = None):

        self.api_key = os.getenv("AZURE_API_KEY")
        self.base_url=os.getenv("AZURE_BASE_URL")
        self.api_version=os.getenv("API_VERSION")
        
        # API key validation
        if not self.api_key:
            raise ValueError("AZURE_API_KEY environment variable is not set and no api_key provided")
        
        # Standard OpenAI Client for fallback
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Add Google Maps tool
        tools = []
        
        try:
            from core.talkdoc_core.agents import validate_address, validate_regex
            # Add standalone tool function directly
            tools.append(validate_address)
            logging.info("Google Maps address validation successfully added")

        except Exception as e:
            logging.warning(f"Google Maps address validation could not be added: {e}")
            logging.warning("Agent running without address validation")
        try:
            tools.append(validate_regex)
            logging.info("Regex validation successfully added")
        except Exception as e:
            logging.warning(f"Regex validation could not be added: {e}")
            logging.warning("Agent running without regex validation")
        self.agent = Agent(
            model=AzureOpenAI(id="gpt-4o", api_key=self.api_key, base_url=self.base_url,  api_version=self.api_version),
            # model=OpenAIChat(id="gpt-4o", api_key=self.api_key),
            tools=tools,
            markdown=True,
            debug_mode=True  # Enable debug mode to see tool calls
        )
    
    def chat(
        self,
        messages,
        model: str = "gpt-4o",
        stream: bool = True,
        json_mode: bool = False,
    ):
        try:
            # Use Agno Agent directly - let it handle tools automatically
            logging.info("Using Agno Agent directly")
            
            # Convert messages to a format that Agno can understand
            # Agno expects a single conversation context, not individual messages
            conversation_context = self._build_conversation_context(messages)
            
            if not conversation_context:
                logging.warning("No conversation context found, using fallback")
                # return self._fallback_chat(messages, model, stream, json_mode)
            
            logging.info(f"Processing conversation with Agno: {conversation_context[:200]}...")
            
            # Use Agno's built-in response method with full context
            if stream:
                # For streaming, we need to simulate the response
                response_content = self.agent.run(conversation_context)
                return self._create_streaming_response(response_content.content)
            else:
                response_content = self.agent.run(conversation_context)
                logging.info(f"Agno response: {response_content.content}")
                return response_content.content

        except Exception as e:
            logging.error(f"Agno Service error: {e}")
            # Fallback to normal chat
            return self._fallback_chat(messages, model, stream, json_mode)
    
    
    def _build_conversation_context(self, messages):
        """
        Baut den vollständigen Chat-Kontext für Agno auf.
        Konvertiert die Nachrichten-Liste in einen zusammenhängenden Text.
        """
        if not messages:
            logging.warning("No messages provided to build conversation context")
            return ""
        
        logging.info(f"Building conversation context from {len(messages)} messages")
        
        conversation_parts = []
        
        for i, message in enumerate(messages):
            role = message.get('role', '')
            content = message.get('content', '')
            
            logging.debug(f"Message {i+1}: {role} - {content[:100]}...")
            
            if role == 'system':
                conversation_parts.append(f"System: {content}")
            elif role == 'user':
                conversation_parts.append(f"User: {content}")
            elif role == 'assistant':
                conversation_parts.append(f"Assistant: {content}")
            else:
                logging.warning(f"Unknown role '{role}' in message {i+1}")
        
        # Füge die aktuelle Anfrage hinzu
        full_context = "\n\n".join(conversation_parts)
        
        logging.info(f"Built conversation context with {len(conversation_parts)} parts")
        logging.debug(f"Full context preview: {full_context[:500]}...")
        
        # Für Agno: Gib den Kontext als eine zusammenhängende Unterhaltung zurück
        return full_context
    
    def _create_streaming_response(self, content: str):
        """
        Creates a streaming-like response for compatibility.
        """
        # Simulate OpenAI Streaming Response Format
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
        Fallback to normal OpenAI Chat without Agno.
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
    
    
    # Interface compatibility with GPTService
    def add_system_prompt_for_chat(self, json_fields):
        """
        Compatibility with GPTService - adds system prompt.
        """
        return [{"role": "system", "content": get_system_prompt_for_chat(json_fields)}]

    def add_user_prompt(self, messages, user_input):
        """
        Compatibility with GPTService - adds user prompt.
        """
        return messages + [{"role": "user", "content": user_input}]

    def add_assistant_response(self, messages, response):
        """
        Compatibility with GPTService - adds assistant response.
        """
        return messages + [{"role": "assistant", "content": response}]

    def check_openai_api_key(self):
        """
        Compatibility with GPTService - checks OpenAI API key.
        """
        try:
            self.client.models.list()
            return True
        except openai.AuthenticationError:
            logging.error("Invalid OpenAI API key")
            return False
    
