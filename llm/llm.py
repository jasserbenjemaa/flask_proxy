from llm_router import LLMConfig, estimate_cost, save_final_cost_report

# Configure LLM
llm_config = LLMConfig(
    provider="groq",  # Choose your provider: "groq", "openai", "azure", "anthropic"
    model_name="qwen-2.5-coder-32b",
    temperature=0,
    max_tokens=4000,
    max_retries=3,
    api_key=" " ,# Replace with your actual API key or set as environment variable
    token_price_per_1k=0.002  # Replace with the actual price per 1000 tokens
  )

llm = llm_config.create_llm()

total_tokens, total_cost = estimate_cost(llm, messages, llm_config.token_price_per_1k)
print(f"Estimated tokens: {total_tokens}, Cost: ${total_cost:.4f}")