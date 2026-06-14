import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, Request, Depends
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.logger import logger
from core.security import verify_api_key, limiter
from service.rag_service_pdf import vector_store  # Import your FAISS singleton

router = APIRouter(prefix="/documents", tags=["Documents"], dependencies=[Depends(verify_api_key)])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

def process_and_embed_pdf(file_path: str):
    """Background task to load, chunk, and update FAISS index."""
    try:
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = text_splitter.split_documents(pages)
        
        # Pseudo-code for incrementally adding to FAISS
        vector_store.add_documents(chunks)
        vector_store.save_local("faiss_index/")
        logger.info(f"Successfully embedded {len(chunks)} chunks from {file_path}")
    except Exception as e:
        logger.error(f"Error processing PDF {file_path}: {str(e)}")

@router.post("/upload")
@limiter.limit("5/minute")
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    background_tasks.add_task(process_and_embed_pdf, str(file_path))
    
    return {"message": "File uploaded successfully. Processing and embedding in the background."}