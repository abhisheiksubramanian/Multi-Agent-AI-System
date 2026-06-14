from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from service.llm_service import ask_llm


# Load text
with open("docs/data.txt") as f:
    text = f.read()

# Split text into chunks
splitter = CharacterTextSplitter(chunk_size=200, chunk_overlap=20)
docs = splitter.split_text(text)

# Convert to embeddings
embeddings = HuggingFaceEmbeddings()

# Store in FAISS (Vector DB)
db = FAISS.from_texts(docs, embeddings)

def search(query: str):
    results = db.similarity_search(query, k=2)
    return [doc.page_content for doc in results]


def rag_answer(query: str):
    docs = search(query)
    
    context = "\n".join(docs)

    prompt = f"""
    Answer the question using the context below:

    Context:
    {context}

    Question:
    {query}
    """

    return ask_llm(prompt)