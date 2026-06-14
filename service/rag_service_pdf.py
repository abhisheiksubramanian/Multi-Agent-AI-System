from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from service.llm_service import ask_llm


# Load pdf
loader = PyPDFLoader("docs/resume.pdf")
pages = loader.load()

# Split text into chunks
splitter = CharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

docs = splitter.split_documents(pages)

# Convert to embeddings
embeddings = HuggingFaceEmbeddings()

# Store in FAISS (Vector DB)
db = FAISS.from_documents(docs, embeddings)
db.save_local("faiss_index")

db = FAISS.load_local(
    "faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)

def search(query: str):
    results = db.similarity_search(query, k=3)

    return [doc.page_content for doc in results]


def rag_answer(query: str):
    docs = search(query)
    
    context = "\n".join(docs)

    prompt = f"""
        You are an AI assistant.

        Answer ONLY from the provided context.
        If answer is not present, say:
        "I could not find it in the document."

        Context:
        {context}

        Question:
        {query}
        """

    return ask_llm(prompt)