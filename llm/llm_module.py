import os
from typing import Dict, Any, Optional, Tuple, List, Union
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage

# Import from your module
# Assume paste.py is renamed to llm_core.py for clarity in a larger project
from llm_router import LLMConfig, estimate_cost, save_final_cost_report

def get_price_for_model(provider: str, model_name: str) -> float:
    """Return approximate price per 1K tokens for the given model"""
    # These are approximate values and may need to be updated
    prices = {
        "anthropic": {
            "claude-3-opus": 15.0 / 1000,
            "claude-3-sonnet": 7.5 / 1000,
            "claude-3-haiku": 1.25 / 1000,
            "claude-3-opus-20240229": 15.0 / 1000,
            "claude-3-sonnet-20240229": 7.5 / 1000,
            "claude-3-haiku-20240307": 1.25 / 1000,
        },
        "openai": {
            "gpt-4": 30.0 / 1000,
            "gpt-4-turbo": 10.0 / 1000,
            "gpt-3.5-turbo": 0.5 / 1000,
        },
        "groq": {
            "llama3-70b-8192": 0.7 / 1000,
            "mixtral-8x7b-32768": 0.27 / 1000,
        },
        "azure": {
            "gpt-4": 30.0 / 1000,
            "gpt-4-turbo": 10.0 / 1000,
            "gpt-3.5-turbo": 0.5 / 1000,
        },
        "gemini":{
            "gemini-2.0-flash":0.0,
            "gemini-2.0-flash-lite":0.0,
            "gemini-2.0-pro-exp-02-05":0,
            "gemini-2.0-flash-thinking-exp-01-21":0,
        }
    }

    # Try to find the exact model
    if provider in prices and model_name in prices[provider]:
        return prices[provider][model_name]

    # If not found, try to match the base model name
    for base_model in prices.get(provider, {}):
        if model_name.startswith(base_model):
            return prices[provider][base_model]

    # Default fallback prices
    default_prices = {
        "anthropic": 7.5 / 1000,
        "openai": 10.0 / 1000,
        "groq": 0.5 / 1000,
        "azure": 10.0 / 1000,
        "gemini":0,
    }

    return default_prices.get(provider, 5.0 / 1000)

def create_llm_instance(
    provider: str = "anthropic",
    model_name: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    max_retries: int = 3,
    api_key: str = ""
) -> Tuple[Any, float]:
    """
    Create an LLM instance with the specified configuration.

    Args:
        provider: LLM provider ("anthropic", "openai", "groq", "azure","gemini")
        model_name: Name of the model to use
        temperature: Temperature for generation
        max_tokens: Maximum tokens for response
        max_retries: Maximum number of retries for API calls
        api_key: API key (if empty, uses environment variables)

    Returns:
        Tuple of (LLM instance, token price per 1K)
    """
    # Set default model based on provider if not specified
    if not model_name:
        if provider == "anthropic":
            model_name = "claude-3-sonnet-20240229"
        elif provider == "openai":
            model_name = "gpt-4"
        elif provider == "groq":
            model_name = "llama3-70b-8192"
        elif provider == "azure":
            model_name = "gpt-4"
        elif provider=="gemini":
            model_name="gemini-2.0-flash"

    # Get pricing for the model
    token_price = get_price_for_model(provider, model_name)

    # Create LLM configuration
    llm_config = LLMConfig(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        max_retries=max_retries,
        api_key=api_key,
        token_price_per_1k=token_price
    )

    # Create and return the LLM
    llm = llm_config.create_llm()
    return llm, token_price

def send_prompt(
    llm: Any,
    prompt: str,
    system_message: Optional[str] = None,
    token_price: float = 0.0,
    calculate_cost: bool = True
) -> Dict[str, Any]:
    """
    Send a single prompt to the LLM and get a response.

    Args:
        llm: The LLM instance
        prompt: The prompt to send
        system_message: Optional system message to include
        token_price: Price per 1K tokens for cost estimation
        calculate_cost: Whether to calculate and return cost estimation

    Returns:
        Dictionary containing response and metadata
    """
    # Create messages list
    messages = []
    if system_message:
        messages.append(SystemMessage(content=system_message))
    messages.append(HumanMessage(content=prompt))

    # Estimate cost if requested
    cost_info = {}
    if calculate_cost and token_price > 0:
        tokens, cost = estimate_cost(llm, messages, token_price)
        cost_info = {
            "estimated_tokens": tokens,
            "estimated_cost": cost
        }

    # Get response
    if system_message:
        # When using system message, we need to pass the full messages list
        response = llm.invoke(messages)
    else:
        # For simple prompts, we can just pass the prompt string
        response = llm.invoke(prompt)

    # Return response and metadata
    return {
        "content": response.content,
        "cost_info": cost_info,
        "raw_response": response
    }


def save_costs():
    """Save the accumulated cost report"""
    save_final_cost_report()