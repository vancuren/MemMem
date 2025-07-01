from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import os
import logging
from dotenv import load_dotenv

import anthropic
import openai
import google.generativeai as genai

from .models import MemoryItem

load_dotenv()
logger = logging.getLogger(__name__)

class LLMClient(ABC):
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = "", 
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        raise NotImplementedError

class ClaudeClient(LLMClient):
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(
            api_key=api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.default_model = "claude-3-sonnet-20240229"
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = "", 
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        try:
            messages = [{"role": "user", "content": prompt}]
            
            response = self.client.messages.create(
                model=model or self.default_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error generating Claude response: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "anthropic",
            "default_model": self.default_model,
            "available_models": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229", 
                "claude-3-haiku-20240307"
            ]
        }

class OpenAIClient(LLMClient):
    def __init__(self, api_key: str = None):
        self.client = openai.AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        self.default_model = "gpt-4"
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = "", 
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "openai",
            "default_model": self.default_model,
            "available_models": [
                "gpt-4",
                "gpt-4-turbo-preview",
                "gpt-3.5-turbo"
            ]
        }

class GeminiClient(LLMClient):
    def __init__(self, api_key: str = None):
        genai.configure(api_key=api_key or os.getenv("GOOGLE_API_KEY"))
        self.default_model = "gemini-pro"
    
    async def generate(
        self, 
        prompt: str, 
        system_prompt: str = "", 
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        try:
            model_instance = genai.GenerativeModel(model or self.default_model)
            
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nUser: {prompt}"
            
            response = model_instance.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating Gemini response: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            "provider": "google",
            "default_model": self.default_model,
            "available_models": [
                "gemini-pro",
                "gemini-pro-vision"
            ]
        }

def create_llm_client(provider: str = "claude") -> LLMClient:
    if provider.lower() == "claude":
        return ClaudeClient()
    elif provider.lower() == "openai":
        return OpenAIClient()
    elif provider.lower() == "gemini":
        return GeminiClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

class MemoryAugmentedLLM:
    def __init__(self, llm_client: LLMClient, memory_manager):
        self.llm_client = llm_client
        self.memory_manager = memory_manager
    
    def build_augmented_prompt(
        self, 
        user_query: str, 
        memories: List[MemoryItem],
        system_prompt: str = ""
    ) -> tuple[str, str]:
        if not memories:
            return user_query, system_prompt
        
        # Format memories for context
        memory_context = "Relevant memories from previous conversations:\n"
        for i, memory in enumerate(memories, 1):
            memory_context += f"{i}. {memory.content} (from {memory.timestamp})\n"
        
        # Build augmented system prompt
        augmented_system = system_prompt + "\n\n" + memory_context if system_prompt else memory_context
        
        return user_query, augmented_system
    
    async def generate_with_memory(
        self, 
        user_query: str,
        system_prompt: str = "",
        top_k_memories: int = 3,
        memory_filter: Dict[str, Any] = None,
        model: str = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        try:
            # Retrieve relevant memories
            memories = await self.memory_manager.retrieve_memory(
                user_query, 
                top_k=top_k_memories,
                metadata_filter=memory_filter
            )
            
            # Build augmented prompt
            augmented_query, augmented_system = self.build_augmented_prompt(
                user_query, memories, system_prompt
            )
            
            # Generate response
            response = await self.llm_client.generate(
                augmented_query,
                augmented_system,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                "response": response,
                "memories_used": memories,
                "model_info": self.llm_client.get_model_info()
            }
            
        except Exception as e:
            logger.error(f"Error generating memory-augmented response: {e}")
            raise