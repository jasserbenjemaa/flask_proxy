import os
import json
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
from dotenv import load_dotenv
#from langchain_groq import ChatGroq
#from langchain_openai import AzureChatOpenAI, OpenAI
#from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage
from datetime import datetime
import tiktoken
from collections import defaultdict

load_dotenv()

class CostTracker:
    def __init__(self):
        self.costs = defaultdict(lambda: {
            'total_tokens': 0,
            'total_cost': 0.0,
            'calls': 0,
            'timestamps': []
        })

    def add_usage(self, operation: str, tokens: int, cost: float):
        self.costs[operation]['total_tokens'] += tokens
        self.costs[operation]['total_cost'] += cost
        self.costs[operation]['calls'] += 1
        self.costs[operation]['timestamps'].append(datetime.now().isoformat())

    def save_report(self):
        try:
            report = {
                'summary': {
                    'total_cost': sum(data['total_cost'] for data in self.costs.values()),
                    'total_tokens': sum(data['total_tokens'] for data in self.costs.values()),
                    'total_calls': sum(data['calls'] for data in self.costs.values()),
                    'timestamp': datetime.now().isoformat()
                },
                'operations': dict(self.costs)
            }

            with open('cost.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)

            print(f"\nCost report saved to cost.json")
            print(f"Total cost: ${report['summary']['total_cost']:.4f}")
            print(f"Total tokens: {report['summary']['total_tokens']}")

        except Exception as e:
            print(f"Error saving cost report: {e}")

# Create global cost tracker
cost_tracker = CostTracker()

@dataclass
class LLMConfig:
    provider: str
    model_name: str
    temperature: float
    max_tokens: int
    max_retries: int
    api_key: str
    token_price_per_1k: float

    def create_llm(self):
        """Create and return an LLM instance based on the configuration."""
        try:
            if self.provider == "groq":
                os.environ["GROQ_API_KEY"] = self.api_key or os.getenv("GROQ_API_KEY")
                llm = ChatGroq(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    max_retries=self.max_retries,
                )#.with_structured_output(method="json_mode", include_raw=True)
            elif self.provider == "openai":
                os.environ["OPENAI_API_KEY"] = self.api_key or os.getenv("OPENAI_API_KEY")
                llm = OpenAI(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    max_retries=self.max_retries,
                )
            elif self.provider == "azure":
                os.environ["AZURE_OPENAI_API_KEY"] = self.api_key or os.getenv("AZURE_OPENAI_API_KEY")
                os.environ["AZURE_OPENAI_API_BASE"] = os.getenv("AZURE_OPENAI_API_BASE")
                llm = AzureChatOpenAI(
                    azure_deployment=self.azure_deployment or os.getenv("AZURE_OPENAI_API_DEPLOYMENT_NAME"),
                    api_version=self.azure_api_version or os.getenv("AZURE_OPENAI_API_VERSION"),
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=None,
                    max_retries=self.max_retries,
                )
            elif self.provider == "anthropic":
                os.environ["ANTHROPIC_API_KEY"] = self.api_key or os.getenv("ANTHROPIC_API_KEY")
                llm = ChatAnthropic(
                    model_name=self.model_name,
                    temperature=self.temperature,
                    max_tokens_to_sample=self.max_tokens,
                )
            elif self.provider == "gemini":
                os.environ["GOOGLE_API_KEY"] = self.api_key or os.getenv("GEMINI_API_KEY")
                llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    convert_system_message_to_human=True,  # Gemini doesn't support system messages natively
                    #structured_llm = llm.with_structured_output(method="json_mode", include_raw=True)
                )

            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")


            return llm
        except Exception as e:
            print(f"Error creating LLM: {e}")
            return None

def count_tokens(messages: List[BaseMessage]) -> int:
    """Count tokens in messages"""
    encoding = tiktoken.get_encoding("cl100k_base")  # Default encoding
    total_tokens = 0

    for message in messages:
        total_tokens += len(encoding.encode(message.content))
        # Add 4 tokens for message type/role
        total_tokens += 4

    return total_tokens

def estimate_cost(llm, messages: List[BaseMessage], price_per_1k: float) -> Tuple[int, float]:
    """Estimate token count and cost for messages and track usage"""
    total_tokens = count_tokens(messages)
    estimated_cost = (total_tokens / 1000) * price_per_1k

    # Track the cost
    cost_tracker.add_usage(
        operation='llm_call',
        tokens=total_tokens,
        cost=estimated_cost
    )

    return total_tokens, estimated_cost

def save_final_cost_report():
    """Save the final cost report - call this at the end of generation"""
    cost_tracker.save_report()