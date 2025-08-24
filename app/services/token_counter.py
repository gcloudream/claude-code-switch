"""Token counting service for estimating API usage"""

import tiktoken
import re
from typing import Optional, Dict, Any
from app.core.logging import get_logger


logger = get_logger(__name__)


class TokenCounter:
    """Service for counting tokens in text"""
    
    # Model to encoding mapping
    MODEL_ENCODINGS = {
        # Claude models (using cl100k_base as approximation)
        "claude-3-opus": "cl100k_base",
        "claude-3-sonnet": "cl100k_base",
        "claude-3-haiku": "cl100k_base",
        "claude-2.1": "cl100k_base",
        "claude-2.0": "cl100k_base",
        "claude-instant-1.2": "cl100k_base",
        
        # OpenAI models
        "gpt-4": "cl100k_base",
        "gpt-4-32k": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "text-davinci-003": "p50k_base",
        "text-davinci-002": "p50k_base",
        
        # Default
        "default": "cl100k_base",
    }
    
    def __init__(self):
        """Initialize token counter with encodings"""
        self.encodings = {}
        self._load_default_encoding()
    
    def _load_default_encoding(self) -> None:
        """Load default encoding"""
        try:
            self.encodings["default"] = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error("Failed to load default encoding", error=str(e))
    
    def _get_encoding(self, model: Optional[str] = None) -> Optional[tiktoken.Encoding]:
        """Get encoding for a model
        
        Args:
            model: Model name
            
        Returns:
            Encoding object or None
        """
        if not model:
            model = "default"
        
        # Normalize model name
        model_lower = model.lower()
        
        # Find encoding name for model
        encoding_name = self.MODEL_ENCODINGS.get("default")
        for model_prefix, enc_name in self.MODEL_ENCODINGS.items():
            if model_lower.startswith(model_prefix):
                encoding_name = enc_name
                break
        
        # Get or load encoding
        if encoding_name not in self.encodings:
            try:
                self.encodings[encoding_name] = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                logger.error(f"Failed to load encoding {encoding_name}", error=str(e))
                return self.encodings.get("default")
        
        return self.encodings.get(encoding_name)
    
    def count_tokens(
        self,
        text: str,
        model: Optional[str] = None,
    ) -> int:
        """Count tokens in text
        
        Args:
            text: Text to count tokens in
            model: Optional model name for specific encoding
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        
        # Get encoding
        encoding = self._get_encoding(model)
        
        if not encoding:
            # Fallback to simple estimation (1 token ≈ 4 characters)
            return self._estimate_tokens(text)
        
        try:
            # Count tokens using tiktoken
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning("Token counting failed, using estimation", error=str(e))
            return self._estimate_tokens(text)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate tokens when encoding is not available
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated number of tokens
        """
        # Simple estimation rules:
        # - Average English word is ~4-5 characters
        # - Average token is ~4 characters (including spaces and punctuation)
        # - CJK characters are typically 2-3 tokens per character
        
        # Count CJK characters
        cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\u3040-\u309f\u30a0-\u30ff]')
        cjk_chars = len(cjk_pattern.findall(text))
        
        # Count non-CJK characters
        non_cjk_text = cjk_pattern.sub('', text)
        non_cjk_chars = len(non_cjk_text)
        
        # Estimate tokens
        cjk_tokens = cjk_chars * 2.5  # CJK characters average 2.5 tokens
        non_cjk_tokens = non_cjk_chars / 4  # Non-CJK average 4 chars per token
        
        return int(cjk_tokens + non_cjk_tokens)
    
    def count_messages_tokens(
        self,
        messages: list,
        model: Optional[str] = None,
    ) -> Dict[str, int]:
        """Count tokens in a list of messages (chat format)
        
        Args:
            messages: List of message dictionaries
            model: Optional model name
            
        Returns:
            Dictionary with token counts
        """
        result = {
            "prompt_tokens": 0,
            "total_tokens": 0,
            "messages_count": len(messages),
        }
        
        # Count tokens in each message
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            
            # Count role tokens (typically 1-2 tokens)
            role_tokens = self.count_tokens(role, model)
            
            # Count content tokens
            content_tokens = self.count_tokens(content, model)
            
            # Add message formatting overhead (typically 3-4 tokens per message)
            message_tokens = role_tokens + content_tokens + 4
            
            result["prompt_tokens"] += message_tokens
        
        result["total_tokens"] = result["prompt_tokens"]
        
        return result
    
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        """Estimate cost based on token usage
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: Optional model name for specific pricing
            
        Returns:
            Estimated cost in USD
        """
        # Pricing per 1K tokens (example rates, should be configurable)
        pricing = {
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "claude-2.1": {"input": 0.008, "output": 0.024},
            "claude-2.0": {"input": 0.008, "output": 0.024},
            "claude-instant-1.2": {"input": 0.0008, "output": 0.0024},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "default": {"input": 0.01, "output": 0.03},
        }
        
        # Get pricing for model
        model_pricing = pricing.get("default")
        if model:
            model_lower = model.lower()
            for model_prefix, prices in pricing.items():
                if model_lower.startswith(model_prefix):
                    model_pricing = prices
                    break
        
        # Calculate cost
        input_cost = (prompt_tokens / 1000) * model_pricing["input"]
        output_cost = (completion_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost