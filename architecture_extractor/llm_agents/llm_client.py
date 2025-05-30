"""
LLM Client

Handles communication with various LLM models including Code LLaMA.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM model"""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None


@dataclass 
class LLMRequest:
    """Request to LLM model"""
    prompt: str
    system_prompt: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.1
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseLLMClient(ABC):
    """Base class for LLM clients"""
    
    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response from LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if LLM is available"""
        pass


class CodeLlamaClient(BaseLLMClient):
    """Client for Code LLaMA model"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:11434",
                 model_name: str = "codellama:7b-instruct",
                 timeout: int = 120):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.timeout = timeout
        self.session = requests.Session()
        
    def is_available(self) -> bool:
        """Check if Ollama server is running and model is available"""
        try:
            # Check if server is running
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                return False
            
            # Check if model is available
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            return any(self.model_name in name for name in model_names)
            
        except Exception as e:
            logger.debug(f"Code LLaMA not available: {e}")
            return False
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using Code LLaMA via Ollama API"""
        if not self.is_available():
            raise RuntimeError("Code LLaMA is not available. Please ensure Ollama is running and codellama model is installed.")
        
        # Prepare the prompt
        full_prompt = request.prompt
        if request.system_prompt:
            full_prompt = f"System: {request.system_prompt}\n\nUser: {request.prompt}"
        
        # Prepare API request
        api_request = {
            "model": request.model or self.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "top_p": 0.9,
                "top_k": 40
            }
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=api_request,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            return LLMResponse(
                content=result.get('response', '').strip(),
                model=result.get('model', self.model_name),
                usage={
                    'prompt_tokens': result.get('prompt_eval_count', 0),
                    'completion_tokens': result.get('eval_count', 0),
                    'total_tokens': result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                },
                metadata={
                    'eval_duration': result.get('eval_duration', 0),
                    'load_duration': result.get('load_duration', 0)
                }
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Code LLaMA API: {e}")
            raise RuntimeError(f"Failed to get response from Code LLaMA: {e}")


class OpenAIClient(BaseLLMClient):
    """Client for OpenAI models (fallback option)"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gpt-3.5-turbo"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://api.openai.com/v1"
        
        if not api_key:
            import os
            self.api_key = os.getenv('OPENAI_API_KEY')
    
    def is_available(self) -> bool:
        """Check if OpenAI API is available"""
        return self.api_key is not None
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using OpenAI API"""
        if not self.is_available():
            raise RuntimeError("OpenAI API key not available")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        
        api_request = {
            "model": request.model or self.model_name,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=api_request,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            choice = result['choices'][0]
            
            return LLMResponse(
                content=choice['message']['content'].strip(),
                model=result['model'],
                usage=result.get('usage', {}),
                metadata={'finish_reason': choice.get('finish_reason')}
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling OpenAI API: {e}")
            raise RuntimeError(f"Failed to get response from OpenAI: {e}")


class LocalLLMClient(BaseLLMClient):
    """Mock client for local/offline testing"""
    
    def __init__(self):
        self.responses = {
            'code_analysis': "This code appears to implement a data processing module with the following responsibilities:\n1. Data validation and sanitization\n2. Business logic execution\n3. Database interaction\n\nThe main classes are likely core business entities with clear separation of concerns.",
            'relationships': "Based on the code structure, I can identify these relationships:\n1. Controller -> Service (dependency)\n2. Service -> Repository (dependency)\n3. Repository -> Model (composition)\n\nThis follows a typical layered architecture pattern.",
            'responsibilities': "The module has these key responsibilities:\n1. **Primary**: Data processing and transformation\n2. **Secondary**: Input validation\n3. **Infrastructure**: Database operations\n\nThis suggests it's a core business logic component."
        }
    
    def is_available(self) -> bool:
        """Always available for testing"""
        return True
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate mock response based on request type"""
        # Simple keyword matching to provide relevant responses
        prompt_lower = request.prompt.lower()
        
        if 'relationship' in prompt_lower or 'depend' in prompt_lower:
            content = self.responses['relationships']
        elif 'responsibility' in prompt_lower or 'purpose' in prompt_lower:
            content = self.responses['responsibilities']
        else:
            content = self.responses['code_analysis']
        
        return LLMResponse(
            content=content,
            model="local-mock",
            usage={'prompt_tokens': len(request.prompt.split()), 'completion_tokens': len(content.split())},
            confidence=0.8
        )


class LLMClient:
    """Main LLM client that handles multiple providers"""
    
    def __init__(self, preferred_provider: str = "codellama"):
        self.preferred_provider = preferred_provider
        self.clients = {}
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize available LLM clients"""
        # Code LLaMA (preferred)
        self.clients['codellama'] = CodeLlamaClient()
        
        # OpenAI (fallback)
        self.clients['openai'] = OpenAIClient()
        
        # Local mock (always available)
        self.clients['local'] = LocalLLMClient()
    
    def get_available_client(self) -> BaseLLMClient:
        """Get the first available LLM client"""
        # Try preferred provider first
        if self.preferred_provider in self.clients:
            client = self.clients[self.preferred_provider]
            if client.is_available():
                logger.info(f"Using {self.preferred_provider} LLM client")
                return client
        
        # Try other providers
        for name, client in self.clients.items():
            if name != self.preferred_provider and client.is_available():
                logger.info(f"Falling back to {name} LLM client")
                return client
        
        # Use local mock as last resort
        logger.warning("No external LLM available, using local mock client")
        return self.clients['local']
    
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate response using available LLM client"""
        client = self.get_available_client()
        return client.generate(request)
    
    def generate_with_retry(self, request: LLMRequest, max_retries: int = 3) -> LLMResponse:
        """Generate response with retry logic"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.generate(request)
            except Exception as e:
                last_error = e
                logger.warning(f"LLM request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        raise RuntimeError(f"All LLM requests failed after {max_retries} attempts. Last error: {last_error}")
    
    def batch_generate(self, requests: List[LLMRequest], max_concurrent: int = 3) -> List[LLMResponse]:
        """Generate responses for multiple requests"""
        responses = []
        
        # Simple sequential processing for now
        # Could be enhanced with async/concurrent processing
        for request in requests:
            try:
                response = self.generate_with_retry(request)
                responses.append(response)
            except Exception as e:
                logger.error(f"Failed to process batch request: {e}")
                # Add empty response to maintain order
                responses.append(LLMResponse(
                    content="",
                    model="error",
                    metadata={'error': str(e)}
                ))
        
        return responses
