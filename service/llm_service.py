from groq import Groq, AsyncGroq
import os
import time
from dotenv import load_dotenv
from utils.logger import logger
from config.settings import MODEL_NAME, GROQ_API_KEY
from prometheus_client import Counter

load_dotenv()

client = Groq(api_key=GROQ_API_KEY)
async_client = AsyncGroq(api_key=GROQ_API_KEY)

# Observability: Token tracking counters
TOKEN_COUNTER = Counter(
    "llm_tokens_total", "Total LLM tokens consumed", ["model", "token_type"]
)

def ask_llm(question: str):
    """
    Asks a question to the LLM synchronously and returns the response content.

    Args:
        question (str): The question to be asked to the LLM.

    Returns:
        str: The content of the response from the LLM.
    """
    
    logger.info(f"Asking LLM: {question}")
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor."},
                {"role": "user", "content": question}
            ]
        )
        end_time = time.time()
        logger.info(f"LLM response received in {end_time - start_time:.3f} seconds")
        logger.info(f"LLM Response: {response.choices[0].message.content}")
        
        # Track Token Usage
        if response.usage:
            TOKEN_COUNTER.labels(model=MODEL_NAME, token_type="prompt").inc(response.usage.prompt_tokens)
            TOKEN_COUNTER.labels(model=MODEL_NAME, token_type="completion").inc(response.usage.completion_tokens)
            
    except Exception as e:
        end_time = time.time()
        logger.error(f"Error occurred while asking LLM after {end_time - start_time:.3f} seconds: {e}")
        raise
    return response.choices[0].message.content


async def ask_llm_async(question: str):
    """
    Asks a question to the LLM asynchronously and returns the response content.

    Args:
        question (str): The question to be asked to the LLM.

    Returns:
        str: The content of the response from the LLM.
    """
    logger.info(f"Asking LLM Async: {question}")
    start_time = time.time()
    try:
        response = await async_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor."},
                {"role": "user", "content": question}
            ]
        )
        end_time = time.time()
        logger.info(f"LLM async response received in {end_time - start_time:.3f} seconds")
        
        # Track Token Usage
        if response.usage:
            TOKEN_COUNTER.labels(model=MODEL_NAME, token_type="prompt").inc(response.usage.prompt_tokens)
            TOKEN_COUNTER.labels(model=MODEL_NAME, token_type="completion").inc(response.usage.completion_tokens)
            
        return response.choices[0].message.content
    except Exception as e:
        end_time = time.time()
        logger.error(f"Error occurred while asking LLM async after {end_time - start_time:.3f} seconds: {e}")
        raise


async def ask_llm_stream(question: str):
    """
    Streams the LLM response asynchronously.

    Args:
        question (str): The question to be asked to the LLM.

    Yields:
        str: Chunks of the response content from the LLM as they are generated.
    """
    logger.info(f"Streaming LLM Response for: {question}")
    try:
        stream = await async_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful AI tutor."},
                {"role": "user", "content": question}
            ],
            stream=True
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Error occurred while streaming LLM: {e}")
        raise