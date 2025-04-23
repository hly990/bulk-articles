#!/usr/bin/env python
"""
Local Model Fallback Demo

This script demonstrates the local model fallback functionality implemented in Task 4.8.
It shows different ways to use the FallbackModelService, including various fallback modes
and how to handle different scenarios.

Key features demonstrated:
1. Setting up FallbackModelService with different configurations
2. Using different fallback modes (AUTO, MANUAL, LOCAL_ONLY, DEEPSEEK_ONLY)
3. Handling fallback scenarios
4. Monitoring which service is active
5. Force switching to local model when needed
"""

import os
import sys
import logging
import time
from typing import List, Dict, Any, Optional

# Add the src directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services import (
    FallbackModelService, 
    FallbackMode,
    DeepSeekService,
    LocalModelService,
    LocalModelConfig,
    TokenUsageTracker
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("fallback_demo")

def setup_environment():
    """Set up environment variables for the demo."""
    # Check if API key is set
    if not os.getenv("DEEPSEEK_API_KEY"):
        logger.warning("DEEPSEEK_API_KEY not set. Using a dummy value for demonstration.")
        os.environ["DEEPSEEK_API_KEY"] = "dummy_api_key_for_demo"
        
    # Check if HuggingFace token is set
    if not os.getenv("HUGGINGFACE_TOKEN"):
        logger.warning(
            "HUGGINGFACE_TOKEN not set. You'll need this for downloading models. "
            "Get a token from https://huggingface.co/settings/tokens"
        )

def create_fallback_service(mode: str = "auto") -> FallbackModelService:
    """Create a FallbackModelService with the specified mode.
    
    Parameters
    ----------
    mode : str
        The fallback mode to use.
        
    Returns
    -------
    FallbackModelService
        The configured fallback service.
    """
    # Create a token tracker for monitoring usage
    token_tracker = TokenUsageTracker()
    
    # Create a LocalModelConfig with custom settings
    local_config = LocalModelConfig(
        model_id="meta-llama/Meta-Llama-3-8B-Instruct",
        model_basename="Meta-Llama-3-8B-Instruct-Q5_K_M.gguf",
        num_threads=4,  # Adjust based on your CPU
        num_gpu_layers=0,  # Set to higher number if you have a GPU
        context_size=2048,  # Smaller context size for faster inference
        max_tokens=256,  # Limit token generation for the demo
    )
    
    # Create a FallbackModelService
    # Note: LocalModelService is lazily initialized to avoid downloading
    # the model unnecessarily
    service = FallbackModelService(
        fallback_mode=mode,
        token_tracker=token_tracker,
        logger=logger,
    )
    
    logger.info(f"Created FallbackModelService with mode: {mode}")
    return service

def demonstrate_auto_fallback():
    """Demonstrate automatic fallback behavior."""
    logger.info("===== DEMONSTRATING AUTO FALLBACK MODE =====")
    
    # Create a service with AUTO fallback mode
    service = create_fallback_service(mode="auto")
    
    # Check which service is active
    info = service.get_active_service_info()
    logger.info(f"Initial active service: {info['active_service']}")
    
    # Try a simple completion
    try:
        prompt = "Write a short paragraph about AI."
        logger.info(f"Sending prompt: {prompt}")
        
        # This will try DeepSeek first, then fall back to local if DeepSeek fails
        result = service.completion(prompt, max_tokens=50)
        logger.info(f"Result: {result}")
        
        # Check which service was used
        info = service.get_active_service_info()
        logger.info(f"Service used: {info['active_service']}")
        
    except Exception as e:
        logger.error(f"Error during completion: {e}")

def demonstrate_local_only():
    """Demonstrate LOCAL_ONLY mode."""
    logger.info("===== DEMONSTRATING LOCAL_ONLY MODE =====")
    
    # Create a service with LOCAL_ONLY mode
    service = create_fallback_service(mode="local_only")
    
    # Try a simple completion
    try:
        prompt = "Explain what a language model is in one sentence."
        logger.info(f"Sending prompt: {prompt}")
        
        # This will only use the local model, regardless of DeepSeek availability
        result = service.completion(prompt, max_tokens=30)
        logger.info(f"Result: {result}")
        
        # Check service info
        info = service.get_active_service_info()
        logger.info(f"Service used: {info['active_service']}")
        
    except Exception as e:
        logger.error(f"Error during completion: {e}")

def demonstrate_manual_fallback():
    """Demonstrate MANUAL fallback mode."""
    logger.info("===== DEMONSTRATING MANUAL FALLBACK MODE =====")
    
    # Create a service with MANUAL fallback mode
    service = create_fallback_service(mode="manual")
    
    # Try with DeepSeek first
    try:
        prompt = "What is the capital of France?"
        logger.info(f"Trying with DeepSeek: {prompt}")
        
        # This will use DeepSeek if available, otherwise raise an error
        result = service.completion(prompt, max_tokens=10)
        logger.info(f"DeepSeek result: {result}")
        
    except Exception as e:
        logger.warning(f"DeepSeek failed: {e}")
        
        # Now manually trigger fallback
        logger.info("Manually triggering fallback to local model...")
        success = service.force_local_fallback()
        
        if success:
            logger.info("Local fallback successful, retrying...")
            try:
                result = service.completion(prompt, max_tokens=10)
                logger.info(f"Local model result: {result}")
            except Exception as e:
                logger.error(f"Local model also failed: {e}")
        else:
            logger.error("Failed to initiate local fallback")

def demonstrate_chat_completion():
    """Demonstrate chat completion with fallback."""
    logger.info("===== DEMONSTRATING CHAT COMPLETION =====")
    
    # Create a service with AUTO fallback mode
    service = create_fallback_service(mode="auto")
    
    # Create a simple chat conversation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, can you help me with a Python question?"},
        {"role": "assistant", "content": "Of course! I'd be happy to help with your Python question."},
        {"role": "user", "content": "How do I read a file in Python?"}
    ]
    
    try:
        logger.info("Sending chat messages...")
        
        # This will try DeepSeek first, then fall back to local if DeepSeek fails
        result = service.chat_completion(messages, max_tokens=100)
        logger.info(f"Response: {result}")
        
        # Check which service was used
        info = service.get_active_service_info()
        logger.info(f"Service used: {info['active_service']}")
        
    except Exception as e:
        logger.error(f"Error during chat completion: {e}")

def demonstrate_switching_modes():
    """Demonstrate switching between fallback modes."""
    logger.info("===== DEMONSTRATING MODE SWITCHING =====")
    
    # Create a service with AUTO fallback mode
    service = create_fallback_service(mode="auto")
    
    # Check initial mode
    info = service.get_active_service_info()
    logger.info(f"Initial mode: {info['fallback_mode']}")
    
    # Switch to LOCAL_ONLY mode
    service.set_fallback_mode("local_only")
    info = service.get_active_service_info()
    logger.info(f"New mode: {info['fallback_mode']}")
    
    # Try a completion with LOCAL_ONLY
    try:
        prompt = "Write one sentence about programming."
        logger.info(f"LOCAL_ONLY mode - Prompt: {prompt}")
        result = service.completion(prompt, max_tokens=20)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Error: {e}")
    
    # Switch to DEEPSEEK_ONLY mode
    service.set_fallback_mode("deepseek_only")
    info = service.get_active_service_info()
    logger.info(f"New mode: {info['fallback_mode']}")
    
    # Try a completion with DEEPSEEK_ONLY
    try:
        prompt = "Write one sentence about AI."
        logger.info(f"DEEPSEEK_ONLY mode - Prompt: {prompt}")
        result = service.completion(prompt, max_tokens=20)
        logger.info(f"Result: {result}")
    except Exception as e:
        logger.error(f"Error: {e}")
        # Try to force local fallback even in DEEPSEEK_ONLY mode
        logger.info("Forcing local fallback despite DEEPSEEK_ONLY mode...")
        if service.force_local_fallback():
            try:
                result = service.completion(prompt, max_tokens=20)
                logger.info(f"Result after forced fallback: {result}")
            except Exception as e2:
                logger.error(f"Error after forced fallback: {e2}")

def main():
    """Run the local model fallback demo."""
    logger.info("Starting Local Model Fallback Demo")
    
    # Set up environment variables
    setup_environment()
    
    # Demonstrate different fallback scenarios
    try:
        demonstrate_auto_fallback()
        time.sleep(1)  # Pause between demos
        
        demonstrate_local_only()
        time.sleep(1)
        
        demonstrate_manual_fallback()
        time.sleep(1)
        
        demonstrate_chat_completion()
        time.sleep(1)
        
        demonstrate_switching_modes()
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error in demo: {e}")
    
    logger.info("Demo completed")

if __name__ == "__main__":
    main() 