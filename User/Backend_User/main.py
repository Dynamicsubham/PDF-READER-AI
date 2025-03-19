import os
import uuid
import json
import traceback
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

import boto3
from langchain_community.embeddings import BedrockEmbeddings
from langchain_aws import ChatBedrock
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS

# ---------------------- ENV & GLOBALS ---------------------- #
AWS_REGION="us-east-1"
BUCKET_NAME="subham-bedrock-pdf-ai-test"
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Initialize S3 client
s3_client = boto3.client("s3", region_name=AWS_REGION)
bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)

# Embeddings
bedrock_embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v1",
    client=bedrock_client
)

# In-memory caches (for demo)
LOADED_FAISS_INDICES = {}  # key: base_name, value: FAISS instance

app = FastAPI(title="RAG with Bedrock", version="1.0")

# CORS
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------- DATA MODELS ---------------------- #
class LoadContextRequest(BaseModel):
    base_name: str

class AskQuestionRequest(BaseModel):
    base_name: str
    question: str

# ---------------------- UTILS ---------------------- #
def load_raw_text_from_s3(base_name: str) -> str:
    """
    Fetches <base_name>.txt from S3, returns its contents as a string.
    Raises HTTPException if the file is not found or there's an error.
    """
    text_key = f"{base_name}.txt"
    try:
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=text_key)
        text_content = response["Body"].read().decode("utf-8")
        return text_content
    except Exception as e:
        print(f"[ERROR] Retrieving raw text from S3 => {e}")
        raise HTTPException(status_code=404, detail=f"No raw text found for '{base_name}'.")

def load_index_from_s3(base_name: str) -> bool:
    """
    Download the FAISS (.faiss) and PKL (.pkl) files from S3, store them in /tmp,
    then load them locally. Returns True if successful, False otherwise.
    """
    faiss_key = f"{base_name}.faiss"
    pkl_key = f"{base_name}.pkl"
    folder_path = "/tmp/"
    os.makedirs(folder_path, exist_ok=True)

    try:
        s3_client.download_file(BUCKET_NAME, faiss_key, os.path.join(folder_path, faiss_key))
        s3_client.download_file(BUCKET_NAME, pkl_key, os.path.join(folder_path, pkl_key))
    except Exception as e:
        print(f"[ERROR] Downloading FAISS/PKL from S3 for {base_name} => {e}")
        return False

    faiss_path = os.path.join(folder_path, faiss_key)
    pkl_path = os.path.join(folder_path, pkl_key)
    if not (os.path.isfile(faiss_path) and os.path.isfile(pkl_path)):
        print("[ERROR] Downloaded FAISS or PKL files are missing.")
        return False
    if (os.path.getsize(faiss_path) == 0 or os.path.getsize(pkl_path)) == 0:
        print("[ERROR] Downloaded FAISS or PKL files are empty.")
        return False

    # Load the FAISS index
    try:
        faiss_index = FAISS.load_local(
            index_name=base_name,
            folder_path=folder_path,
            embeddings=bedrock_embeddings,
            allow_dangerous_deserialization=True
        )
        LOADED_FAISS_INDICES[base_name] = faiss_index
        print(f"[DEBUG] FAISS index stats: {faiss_index.index.ntotal} vectors loaded")
    except Exception as e:
        print(f"[ERROR] Loading FAISS index => {e}")
        return False

    print(f"[INFO] Successfully loaded FAISS index for {base_name}")
    return True

def get_llm() -> ChatBedrock:
    return ChatBedrock(
        provider="anthropic",
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",  # Simplified model ID
        client=bedrock_client,
        model_kwargs={
            "max_tokens": 200000,  # Reduced from 100k
            "temperature": 0.5,
            "stop_sequences": ["\n\nHuman"]  # Add stop sequence
        }
    )    


def run_retrieval_qa(llm, vectorstore, question: str) -> str:
    prompt_template = """Human:

You are an advanced AI assisting a company with onboarding individuals or corporate entities via a web-based application called VERIDATE.
You have access to various documents—such as company policies, financial statements, investment documents,
and corporate reports—used in typical onboarding and compliance processes.

Instructions:

Answer thoroughly when asked for a detailed explanation; if asked for a short answer, comply accordingly.
Use the context (corporate policy documents, statements, financial documents, reports, etc.) to form responses. If you lack sufficient information to answer, say “I don’t know” rather than inventing details.
Never begin answers with phrases like “Based on the context” or disclaimers. Start speaking as though you already know the content.
Provide concise yet comprehensive answers. Avoid irrelevant or off-topic details.
Tables: If a question requests tabular data, present it in a well-formatted table without referencing “columns” in your text. For instance, just display a Markdown table or a neat text-based table when it makes sense. Only show tables when asked.
Summaries: If asked to summarize, do so. If the context is limited, provide whatever summary you can without apologizing for insufficient data.
Respect relevance: Answer only what pertains to the user’s question and the provided context.
Number the points: When some question's answers are there in points then provide some point symbol like bullet or show numberings.
Goal: Present answers as if you possess the knowledge already, offering a professional and organized response each time.

**Important**: End each response immediately after providing the 
answer. Do not ask the user new questions or continue the 
conversation unless explicitly requested. Do not show the table when not asked in the question. Give a very detailed answer of the question. Don't just provide a one line answer or a two line answer.
Provide a good and upto the point answer of the question with every detail from the context. Do not provide with HTML tags. Provide a symbol or a number when needed.
When a company document is provided answer every detail about the company. The answer should not leave any detail from the context.

context = {context}
Question = {question}

Assistant:
(Follows the above rules...)"""

    PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])

    try:
        print(f"\n[DEBUG] Initializing QA chain for question: {question}")
        qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            ),
            return_source_documents=False,  # Changed to False
            chain_type_kwargs={"prompt": PROMPT}
        )
    except Exception as e:
        print(f"[ERROR] Error initializing RetrievalQA: {str(e)}")
        traceback.print_exc()
        return "Error initializing question answering system."

    try:
        print(f"[DEBUG] Executing QA chain with question: {question}")
        result = qa.invoke({"query": question})  # Changed to invoke()
        print(f"[DEBUG] Raw QA result: {result}")
        
        # Handle different response formats
        if isinstance(result, dict):
            return result.get("result", "No answer found in response")
        elif hasattr(result, "get"):
            return result.get("output", str(result))
        return str(result)
        
    except Exception as e:
        print(f"[CRITICAL] QA execution failed: {str(e)}")
        traceback.print_exc()
        return f"Error processing question: {str(e)}"

def store_response_in_s3(base_name: str, query: str, response: str) -> None:
    """Stores query-response pair in S3 for memory."""
    memory_folder = f"{base_name}/memory/"
    memory_file = f"{uuid.uuid4()}.json"
    memory_data = {
        "query": query,
        "response": response,
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{memory_folder}{memory_file}",
            Body=json.dumps(memory_data))
        print("[INFO] Stored response in S3 successfully.")
    except Exception as e:
        print(f"[ERROR] Storing response in S3 => {e}")

# ---------------------- ROUTES ---------------------- #
@app.get("/list-contexts")
def list_contexts():
    """
    Returns a list of available FAISS contexts (base_name) from the S3 bucket.
    Looks for pairs of .faiss and .pkl.
    """
    prefix = ""
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        if 'Contents' not in response:
            return []

        file_extensions = {}
        for content in response.get('Contents', []):
            file_key = content['Key']
            bn, ext = os.path.splitext(os.path.basename(file_key))
            if ext in ['.faiss', '.pkl']:
                if bn not in file_extensions:
                    file_extensions[bn] = set()
                file_extensions[bn].add(ext)

        available_files = [bn for bn, exts in file_extensions.items() if '.faiss' in exts and '.pkl' in exts]
        return available_files
    except Exception as e:
        print(f"[ERROR] Listing contexts => {e}")
        raise HTTPException(status_code=500, detail="Failed to list contexts.")

@app.post("/load-context")
def load_context(request: LoadContextRequest):
    """
    Download and load the FAISS index for a specific base_name into memory.
    Returns generated questions for the loaded context.
    """
    base_name = request.base_name.strip()
    if not base_name:
        raise HTTPException(status_code=400, detail="base_name is required.")

    load_success = load_index_from_s3(base_name)
    if not load_success:
        raise HTTPException(status_code=500, detail="Failed to load context from S3.")
   
    try:
        raw_text = load_raw_text_from_s3(base_name)
    except HTTPException:
        print(f"[INFO] No raw text available for {base_name}, skipping question generation.")
    except Exception as e:
        print(f"[ERROR] Question generation failed: {str(e)}")

    return {
        "message": f"Context '{base_name}' loaded successfully."
    }

@app.post("/ask")
def ask_question(request: AskQuestionRequest):
    base_name = request.base_name.strip()
    question = request.question.strip()
    
    if not base_name or not question:
        raise HTTPException(status_code=400, detail="Missing required fields")

    if base_name not in LOADED_FAISS_INDICES:
        raise HTTPException(status_code=404, detail=f"Context '{base_name}' not loaded")

    try:
        vectorstore = LOADED_FAISS_INDICES[base_name]
        llm = get_llm()
        
        # Validate vectorstore
        if not hasattr(vectorstore, "as_retriever"):
            raise HTTPException(status_code=500, detail="Invalid vectorstore format")
            
        response_text = run_retrieval_qa(llm, vectorstore, question)
        store_response_in_s3(base_name, question, response_text)
        
        return {"answer": response_text}
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preview-context")
def preview_context(base_name: str):
    """
    Return first 500 characters of the .txt file stored in S3 (raw text).
    This assumes admin side has uploaded <base_name>.txt to S3.
    """
    if base_name not in LOADED_FAISS_INDICES:
        raise HTTPException(status_code=404, detail=f"Context '{base_name}' not loaded or not found.")

    raw_text = load_raw_text_from_s3(base_name)
    preview = raw_text[:500]
    return {"preview": preview}

# ---------------------- LAUNCH (for local dev) ---------------------- #
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)