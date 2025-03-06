# Flask Proxy

## Description
Flask Proxy is a project that integrates **mitmproxy** with Flask to intercept API requests, analyze their parameters, consult an LLM for corrections, and forward the corrected requests to the server. It helps in fixing incorrect API parameters dynamically.


## Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/your-username/flask_proxy.git
   ```
2. Add a `.env` file with necessary configurations:
   ```sh
   GEMINI_API_KEY=your_gemini_api_key
   GROQ_API_KEY=your_groq_api_key
   OPENAI_API_KEY=your_openai_api_key
   AZURE_OPENAI_API_KEY=your_azure_openai_api_key
   AZURE_OPENAI_API_BASE=your_azure_openai_api_base
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

## Usage
To run the project, use:
```sh
docker compose up --build
```

## API Endpoints
| Method | Endpoint  | Description |
|--------|----------|-------------|
| POST   | `/valid`   | Processes valid API requests |
| POST   | `/invalid` | Handles invalid API requests |

## LLM Provider Configuration
This project uses **Gemini** by default. If you want to change the provider, go to `llm/app.py`, find the provider and model, and modify it to one of the following:

### Available LLM Providers & Pricing

| Provider   | Model                           | Price per 1K Tokens ($) |
|------------|--------------------------------|-------------------------|
| **Anthropic** | claude-3-opus                   | 15.00                    |
|            | claude-3-sonnet                 | 7.50                     |
|            | claude-3-haiku                  | 1.25                     |
|            | claude-3-opus-20240229          | 15.00                    |
|            | claude-3-sonnet-20240229        | 7.50                     |
|            | claude-3-haiku-20240307         | 1.25                     |
| **OpenAI** | gpt-4                           | 30.00                    |
|            | gpt-4-turbo                     | 10.00                    |
|            | gpt-3.5-turbo                   | 0.50                     |
| **Groq**   | llama3-70b-8192                 | 0.70                     |
|            | mixtral-8x7b-32768              | 0.27                     |
| **Azure**  | gpt-4                           | 30.00                    |
|            | gpt-4-turbo                     | 10.00                    |
|            | gpt-3.5-turbo                   | 0.50                     |
| **Gemini** | gemini-2.0-flash                | 0.00                     |
|            | gemini-2.0-flash-lite           | 0.00                     |
|            | gemini-2.0-pro-exp-02-05        | 0.00                     |
|            | gemini-2.0-flash-thinking-exp-01-21 | 0.00                 |

