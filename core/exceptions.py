import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from utils.logger import logger

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent app crashes and return standardized errors."""
    logger.error(f"Unhandled Exception on {request.url.path}: {exc}\n{traceback.format_exc()}")
    
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500, 
        content={"message": "Internal Server Error", "request_id": request_id}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic payload validation errors cleanly."""
    request_id = getattr(request.state, "request_id", None)
    logger.warning(f"Validation Error on {request.url.path} | Request ID: {request_id} | Details: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "message": "Payload Validation Error",
            "details": exc.errors(),
            "request_id": request_id
        }
    )

def add_exception_handlers(app: FastAPI):
    """Register all custom exception handlers to the FastAPI app."""
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)