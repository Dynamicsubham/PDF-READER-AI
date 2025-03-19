import os
import uuid
import json
from datetime import datetime, timedelta

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from pydantic import BaseModel
from langchain.embeddings import BedrockEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.document_loaders import PyPDFLoader

import boto3

# -------------- ENV VARS -------------- #
BUCKET_NAME = os.getenv("BUCKET_NAME", "<YOUR_S3_BUCKET>")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# -------------- AWS CLIENTS -------------- #
s3_client = boto3.client("s3", region_name=AWS_REGION)
bedrock_client = boto3.client(service_name="bedrock-runtime", region_name=AWS_REGION)

# -------------- EMBEDDINGS -------------- #
bedrock_embeddings = BedrockEmbeddings(
    model_id="amazon.titan-embed-text-v1",
    client=bedrock_client
)

# -------------- FASTAPI APP -------------- #
app = FastAPI(
    title="Admin PDF Upload & Index",
    version="1.0"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],  # Adjust as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------- UTILS -------------- #
def split_text(pages, chunk_size: int, chunk_overlap: int):
    """
    Splits pages into chunks using LangChain's RecursiveCharacterTextSplitter.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = text_splitter.split_documents(pages)
    return docs

def create_vector_store(file_name: str, documents):
    """
    Creates a FAISS vector store, saves it locally in /tmp, and uploads to S3.
    Returns True on success, False otherwise.
    """
    vectorstore_faiss = FAISS.from_documents(documents, bedrock_embeddings)
    folder_path = "/tmp/"
    os.makedirs(folder_path, exist_ok=True)

    # Save local (FAISS index)
    vectorstore_faiss.save_local(index_name=file_name, folder_path=folder_path)

    faiss_file = os.path.join(folder_path, f"{file_name}.faiss")
    pkl_file = os.path.join(folder_path, f"{file_name}.pkl")

    if not os.path.exists(faiss_file) or not os.path.exists(pkl_file):
        print(f"[ERROR] FAISS or PKL file not found: {faiss_file}, {pkl_file}")
        return False

    # Upload to S3 (FAISS + PKL)
    try:
        s3_client.upload_file(Filename=faiss_file, Bucket=BUCKET_NAME, Key=f"{file_name}.faiss")
        s3_client.upload_file(Filename=pkl_file, Bucket=BUCKET_NAME, Key=f"{file_name}.pkl")
    except Exception as e:
        print(f"[ERROR] Uploading FAISS to S3 => {e}")
        return False

    return True

def store_raw_text_s3(file_name: str, documents):
    """
    Joins all doc.page_content into a single string of raw text, then uploads
    that text as a .txt file to S3.
    """
    # Combine chunk contents into one big string.
    full_text = "\n".join(doc.page_content for doc in documents)

    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"{file_name}.txt",
            Body=full_text.encode("utf-8")  # ensure correct encoding
        )
        print("[INFO] Uploaded raw text to S3 successfully.")
    except Exception as e:
        print(f"[ERROR] Uploading raw text to S3 => {e}")
        # Optionally handle the error or raise an exception

def upload_original_pdf_to_s3(file_name: str, local_path: str) -> bool:
    """
    Uploads the original PDF to S3.
    """
    try:
        s3_client.upload_file(Filename=local_path, Bucket=BUCKET_NAME, Key=f"{file_name}.pdf")
        print(f"[INFO] Uploaded original PDF '{file_name}.pdf' to S3 successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] Uploading original PDF to S3 => {e}")
        return False

def generate_presigned_url(file_name: str, expiration: int = 3600) -> str:
    try:
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': f"{file_name}.pdf"},
            ExpiresIn=expiration
        )
    except Exception as e:
        print(f"[ERROR] Generating presigned URL failed for {file_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate presigned URL.")


# -------------- ROUTES -------------- #
@app.post("/upload-pdf")
async def upload_pdf(
    pdf: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200)
):
    """
    - Receives a PDF file from the admin.
    - Splits the PDF into pages, chunk it, embed with Bedrock, create FAISS index.
    - Uploads .faiss and .pkl to S3.
    - Also uploads the original PDF and raw text to S3.
    Returns success or error message.
    """

    if not pdf.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    # Extract file name (w/o extension)
    file_name_without_extension = os.path.splitext(pdf.filename)[0]
    saved_file_name = f"/tmp/{file_name_without_extension}.pdf"  # store temp in /tmp

    # Save the uploaded file locally
    with open(saved_file_name, "wb") as f:
        f.write(await pdf.read())

    # Load and split the PDF
    try:
        loader = PyPDFLoader(saved_file_name)
        pages = loader.load_and_split()
        print(f"[INFO] Total pages: {len(pages)}")

        # Split text
        splitted_docs = split_text(pages, chunk_size, chunk_overlap)
        print(f"[INFO] splitted_docs length: {len(splitted_docs)}")

        # Create vector store & upload to S3
        result = create_vector_store(file_name_without_extension, splitted_docs)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create/upload FAISS index.")

        # Store raw text in S3 as well
        store_raw_text_s3(file_name_without_extension, splitted_docs)

        # Upload the original PDF to S3
        upload_pdf_success = upload_original_pdf_to_s3(file_name_without_extension, saved_file_name)
        if not upload_pdf_success:
            raise HTTPException(status_code=500, detail="Failed to upload original PDF to S3.")

        return {
            "message": f"Successfully processed PDF '{pdf.filename}'.",
            "chunks": len(splitted_docs)
        }

    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        print("[ERROR]", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-pdf-url")
def get_pdf_url(base_name: str):
    """
    Generates a presigned URL for the original PDF.
    """
    if not base_name:
        raise HTTPException(status_code=400, detail="base_name is required.")

    presigned_url = generate_presigned_url(base_name)
    if not presigned_url:
        raise HTTPException(status_code=500, detail="Could not generate presigned URL.")

    return {"pdf_url": presigned_url}

@app.get("/")
def root():
    return {"message": "Admin PDF Uploader is running."}

# -------------- LOCAL DEV ENTRY -------------- #
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
