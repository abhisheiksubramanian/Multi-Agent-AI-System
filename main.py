import time
from fastapi import FastAPI, Request, BackgroundTasks, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from service.llm_service import ask_llm, ask_llm_async, ask_llm_stream, async_client
from service.rag_service_txt import rag_answer as rag_txt_answer
from service.rag_service_pdf import rag_answer as rag_pdf_answer, db
from service.agent_service import agent
from service.multi_agent_service import multi_agent_workflow
from utils.request_tracker import generate_request_id
from utils.logger import logger
from models.request_models import Question, ChatQuestion
from prometheus_fastapi_instrumentator import Instrumentator
from core.security import configure_cors, verify_api_key, limiter
from core.exceptions import add_exception_handlers
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded


app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security: CORS Configuration
configure_cors(app)

# Observability: Prometheus Metrics
Instrumentator().instrument(app).expose(app)

# Exception Handlers
add_exception_handlers(app)

# Simple in-memory storage for conversational memory
conversation_memory = {}

@app.middleware("http")
async def request_tracking_middleware(request: Request, call_next):
    """
    Middleware to track incoming HTTP requests.
    Generates a unique request ID, logs the request, and measures processing time.

    Args:
        request (Request): The incoming FastAPI request.
        call_next (Callable): The next middleware or route handler in the chain.

    Returns:
        Response: The HTTP response with tracking headers added.
    """
    request_id = generate_request_id()
    request.state.request_id = request_id
    
    logger.info(f"Incoming request {request.method} {request.url} | Request ID: {request_id}")
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"
    logger.info(f"Completed request {request_id} in {process_time:.3f}s with status {response.status_code}")

    return response

def log_interaction_bg(request_id: str, question: str, answer: str):
    """
    Background task to simulate logging interactions to a database.

    Args:
        request_id (str): The unique identifier for the request.
        question (str): The user's question.
        answer (str): The generated answer.
    """
    time.sleep(1)  # Simulate DB IO
    logger.info(f"Background Task: Successfully logged interaction {request_id} to DB.")



@app.get("/health")
@limiter.limit("60/minute")
async def health(request: Request):
    """
    Health check endpoint to verify the application is running.

    Returns:
        dict: A status dictionary indicating the application is UP.
    """

    return {
        "status": "UP"
    }

@app.get("/ready")
@limiter.limit("60/minute")
async def ready(request: Request, response: Response):
    """
    Readiness check endpoint to verify external dependencies are connected.

    Returns:
        dict: A status dictionary indicating the connection state of the LLM and Vector DB.
    """
    llm_status = "disconnected"
    vector_db_status = "disconnected"

    try:
        # Lightweight API call to verify LLM connection
        await async_client.models.list()
        llm_status = "connected"
    except Exception as e:
        logger.error(f"LLM readiness check failed: {e}")

    try:
        # Perform a lightweight similarity search to ensure Vector DB is functional
        db.similarity_search("test", k=1)
        vector_db_status = "connected"
    except Exception as e:
        logger.error(f"Vector DB readiness check failed: {e}")

    if llm_status != "connected" or vector_db_status != "connected":
        response.status_code = 503

    return {
        "llm": llm_status,
        "vector_db": vector_db_status
    }

@app.post("/ask-llm")
@limiter.limit("10/minute")
async def ask_question(q: Question, background_tasks: BackgroundTasks, request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint to ask a question to the LLM asynchronously.
    Triggers a background task to log the interaction.

    Args:
        q (Question): The incoming question payload.
        background_tasks (BackgroundTasks): FastAPI background tasks manager.
        request (Request): The incoming request, used to access the request ID.

    Returns:
        dict: A dictionary containing the original question and the LLM's answer.
    """
    request_id = request.state.request_id
    logger.info(f"Processing request {request_id}: {q.text}")
    answer = await ask_llm_async(q.text)
    logger.info(f"Response for request {request_id}: {answer}")
    
    background_tasks.add_task(log_interaction_bg, request_id, q.text, answer)
    
    return {
        "question": q.text,
        "answer": answer
    }

@app.post("/ask-llm-stream")
@limiter.limit("10/minute")
async def ask_question_stream(q: Question, request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint to ask a question to the LLM and stream the response back.

    Args:
        q (Question): The incoming question payload.

    Returns:
        StreamingResponse: A streaming response yielding text chunks.
    """
    return StreamingResponse(ask_llm_stream(q.text), media_type="text/plain")

@app.post("/chat")
@limiter.limit("20/minute")
async def chat_with_memory(q: ChatQuestion, request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint to interact with the LLM maintaining conversation memory.

    Args:
        q (ChatQuestion): The incoming chat question containing the session ID and text.

    Returns:
        dict: A dictionary containing the session ID and the LLM's answer.
    """
    if q.session_id not in conversation_memory:
        conversation_memory[q.session_id] = "Conversation History:\n"
        
    conversation_memory[q.session_id] += f"User: {q.text}\n"
    
    prompt_with_history = conversation_memory[q.session_id] + "AI: "
    answer = await ask_llm_async(prompt_with_history)
    
    conversation_memory[q.session_id] += f"AI: {answer}\n"
    
    return {
        "session_id": q.session_id,
        "answer": answer
    }

@app.post("/summarize-llm")
@limiter.limit("5/minute")
def summarize(q: Question, request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint to summarize the provided text in exactly 2 lines.

    Args:
        q (Question): The text to be summarized.

    Returns:
        dict: A dictionary containing the summary.
    """
    prompt = f"Summarize this in 2 lines: {q.text}"
    answer = ask_llm(prompt)
    return {"summary": answer}

@app.post("/rag-txt")
@limiter.limit("10/minute")
def rag_txt(q: Question, request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint for Retrieval-Augmented Generation (RAG) using a text document source.

    Args:
        q (Question): The question to be answered using the RAG system.

    Returns:
        dict: A dictionary containing the generated answer.
    """
    answer = rag_txt_answer(q.text)
    return {"answer": answer}

@app.post("/rag-pdf")
@limiter.limit("10/minute")
def rag_pdf(q: Question, request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint for Retrieval-Augmented Generation (RAG) using a PDF document source.

    Args:
        q (Question): The question to be answered using the RAG system.

    Returns:
        dict: A dictionary containing the generated answer.
    """
    answer = rag_pdf_answer(q.text)
    return {"answer": answer}


@app.post("/agent")
@limiter.limit("5/minute")
def run_agent(q: Question, request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint to execute a single-agent workflow based on the provided text.

    Args:
        q (Question): The input text to guide the agent's actions.

    Returns:
        dict: A dictionary containing the agent's response.
    """
    answer = agent(q.text)

    return {
        "response": answer
    }

@app.get("/multi-agent")
@limiter.limit("2/minute")
def multi_agent(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Endpoint to execute a pre-defined multi-agent workflow.

    Returns:
        dict: The result of the multi-agent workflow execution.
    """

    return multi_agent_workflow()