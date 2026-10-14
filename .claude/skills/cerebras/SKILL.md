---
name: cerebras-inference
description: Use this to write code to call an LLM using LiteLLM with the Anthropic provider (replaces OpenRouter/Cerebras which is blocked on corporate networks)
---

# Calling an LLM via Anthropic (Claude 3.5 Haiku)

These instructions allow you to write code to call Claude using LiteLLM with the Anthropic provider directly.
This replaces the original OpenRouter/Cerebras approach which is blocked on Infosys corporate networks.

## Setup

The ANTHROPIC_API_KEY must be set in the .env file and loaded in as an environment variable.

The uv project must include litellm and pydantic:
`uv add litellm pydantic`

## Code snippets

Use code like these examples in order to call the LLM.

### Imports and constants

```python
from litellm import completion
MODEL = "claude-3-5-haiku-20241022"
```

### Code to call Anthropic for a text response

```python
response = completion(model=MODEL, messages=messages)
result = response.choices[0].message.content
```

### Code to call Anthropic for a Structured Outputs response

```python
response = completion(model=MODEL, messages=messages, response_format=MyBaseModelSubclass)
result = response.choices[0].message.content
result_as_object = MyBaseModelSubclass.model_validate_json(result)
```

### Environment variable loading

```python
import os
from dotenv import load_dotenv
load_dotenv()
os.environ["ANTHROPIC_API_KEY"]  # LiteLLM picks this up automatically
```

## Notes

- `claude-3-5-haiku-20241022` is fast and cheap — equivalent role to Cerebras in the original design
- For more complex reasoning, use `claude-3-5-sonnet-20241022`
- LiteLLM handles the Anthropic API format transparently — the `completion()` call signature is identical
- Structured outputs are supported via `response_format=PydanticModel` — LiteLLM uses Anthropic tool_use under the hood
