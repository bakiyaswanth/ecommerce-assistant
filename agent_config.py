"""
Google ADK Agent configuration for the Shopping Assistant.

Defines the agent, its tools, and system instructions.
Uses Gemini 1.5 Flash as the underlying LLM.
"""

import logging
import json
from typing import Any

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

import db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Instruction
# ---------------------------------------------------------------------------

SYSTEM_INSTRUCTION = """You are a friendly and knowledgeable **Shopping Assistant** for an e-commerce store.

## Your Capabilities
- Search for products by name, category, price range, or description keywords.
- Compare products and make personalized recommendations.
- Provide detailed product information including pricing.

## Rules
1. **ALWAYS use the `query_products` tool** to look up product information. NEVER invent or hallucinate product data.
2. Present results in a clear, well-formatted way:
   - Use **bold** for product names.
   - Always include the price.
   - Add a brief description highlight.
3. If no products match the query, say so honestly and suggest:
   - Broader search terms
   - Alternative categories
   - Ask the user to clarify their needs
4. For recommendation requests, call the tool and then rank/filter results based on the user's stated preferences.
5. Be conversational, helpful, and concise. Avoid overly long responses.
6. If the user asks something unrelated to shopping, politely redirect them.

## Response Format Example
When listing products:
> Here are some options I found:
>
> 1. **Product Name** — ₹X,XXX
>    _Brief description highlight_
>
> 2. **Product Name** — ₹X,XXX
>    _Brief description highlight_

When comparing:
> Comparing the two options:
> | Feature | Product A | Product B |
> |---------|-----------|-----------|
> | Price   | ₹X,XXX    | ₹X,XXX    |
"""

# ---------------------------------------------------------------------------
# Tool Definition
# ---------------------------------------------------------------------------


def query_products(question: str) -> str:
    """Search the product catalog using a natural language question.

    Use this tool to find products by name, category, price range,
    features, or any other product attribute. The question is
    automatically converted to a database query.

    Args:
        question: A natural language question about products.
                  Examples:
                  - "wireless headphones under $100"
                  - "what electronics do you have?"
                  - "cheapest yoga mat"
                  - "compare running shoes and yoga mats"

    Returns:
        A formatted string with matching product information,
        or an error / no-results message.
    """
    try:
        logger.info("Tool query_products called with: %s", question)
        results = db.execute_nl_query(question)

        if not results:
            return "No products found matching your query. Try broadening your search or using different keywords."

        # Format results as a readable string for the LLM
        formatted_lines = []
        for i, product in enumerate(results, 1):
            parts = []
            if "name" in product:
                parts.append(f"Name: {product['name']}")
            if "price" in product:
                parts.append(f"Price: ${product['price']}")
            if "category" in product:
                parts.append(f"Category: {product['category']}")
            if "description" in product:
                parts.append(f"Description: {product['description']}")
            # Handle any other columns returned by the NL query
            for key, value in product.items():
                if key not in ("name", "price", "category", "description", "id", "embedding"):
                    parts.append(f"{key}: {value}")

            formatted_lines.append(f"Product {i}: " + " | ".join(parts))

        return "\n".join(formatted_lines)

    except Exception as e:
        error_msg = str(e)
        logger.error("Error in query_products tool: %s", error_msg, exc_info=True)
        return f"Database query error: {error_msg}. The query was: '{question}'. Please try a different search."


# ---------------------------------------------------------------------------
# Agent & Runner Factory
# ---------------------------------------------------------------------------

# Shared session service (in-memory, per container instance)
session_service = InMemorySessionService()

# The ADK Agent
shopping_agent = Agent(
    name="shopping_assistant",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[query_products],
    description="An AI shopping assistant that helps users find and compare e-commerce products.",
)

# The Runner executes the agent
runner = Runner(
    agent=shopping_agent,
    app_name="ecommerce_product_scout",
    session_service=session_service,
)


async def chat(session_id: str, user_message: str, model_name: str = "gemini-2.5-flash") -> str:
    """
    Send a user message to the Shopping Assistant and return its response.

    # Dynamically update the agent's model based on user selection
    shopping_agent.model = model_name

    Args:
        session_id:   Unique identifier for this chat session.
        user_message: The user's message text.

    Returns:
        The agent's response as a string.
    """
    from google.genai import types

    # Ensure session exists
    session = await session_service.get_session(
        app_name="ecommerce_product_scout",
        user_id="web_user",
        session_id=session_id,
    )

    if session is None:
        session = await session_service.create_session(
            app_name="ecommerce_product_scout",
            user_id="web_user",
            session_id=session_id,
        )

    # Build the user content
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    # Run the agent and collect the final response
    final_response = ""
    async for event in runner.run_async(
        session_id=session.id,
        user_id="web_user",
        new_message=user_content,
    ):
        if event.is_final_response():
            for part in event.content.parts:
                if part.text:
                    final_response += part.text

    if not final_response:
        final_response = "I'm sorry, I wasn't able to generate a response. Please try again."

    return final_response
