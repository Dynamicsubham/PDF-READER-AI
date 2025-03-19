import React, { useState } from "react";
import "./App.css"; // Import the CSS file
import { ClipLoader } from "react-spinners"; // Importing a spinner
import { Document, Page, pdfjs } from "react-pdf";

// Setting the workerSrc for react-pdf
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

function App() {
  const [pdfFile, setPdfFile] = useState(null);
  const [chunkSize, setChunkSize] = useState(1000);
  const [chunkOverlap, setChunkOverlap] = useState(200);
  const [message, setMessage] = useState("");
  const [uploading, setUploading] = useState(false); // Loading state
  const [uploadSuccess, setUploadSuccess] = useState(false); // Success state
  const [rawText, setRawText] = useState(""); // Raw text state
  const [pdfUrl, setPdfUrl] = useState(""); // PDF URL state
  const [numPages, setNumPages] = useState(null); // Number of pages in PDF

  const handleFileChange = (e) => {
    setPdfFile(e.target.files[0]);
    setRawText(""); // Clear previous raw text
    setPdfUrl(""); // Clear previous PDF URL
    setMessage(""); // Clear previous messages
    setUploadSuccess(false); // Reset success state
  };

  const handleUpload = async () => {
    if (!pdfFile) {
      alert("Please select a PDF file first.");
      return;
    }
    setUploading(true);
    setMessage("");
    setUploadSuccess(false);
    setRawText("");
    setPdfUrl("");

    try {
      const formData = new FormData();
      formData.append("pdf", pdfFile);
      formData.append("chunk_size", chunkSize);
      formData.append("chunk_overlap", chunkOverlap);

      const response = await fetch("http://localhost:8100/upload-pdf", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        setMessage(`Error: ${errorData.detail}`);
        setUploadSuccess(false);
      } else {
        const data = await response.json();
        setMessage(`${data.message} (Chunks: ${data.chunks})`);
        setUploadSuccess(true);

        const baseName = pdfFile.name.split(".pdf")[0];
        await fetchRawTextAndPdf(baseName);
      }
    } catch (err) {
      console.error("Error uploading PDF:", err);
      setMessage("Error uploading PDF. Check console.");
      setUploadSuccess(false);
    } finally {
      setUploading(false);
    }
  };

  const fetchRawTextAndPdf = async (baseName) => {
    try {
      const [rawTextResponse, pdfUrlResponse] = await Promise.all([
        fetch(`http://localhost:8100/preview-context?base_name=${baseName}`),
        fetch(`http://localhost:8100/get-pdf-url?base_name=${baseName}`),
      ]);

      if (rawTextResponse.ok) {
        const rawData = await rawTextResponse.json();
        setRawText(rawData.preview || "No raw text available.");
      } else {
        setRawText("Unable to fetch raw text.");
      }

      if (pdfUrlResponse.ok) {
        const pdfData = await pdfUrlResponse.json();
        setPdfUrl(pdfData.pdf_url);
      } else {
        throw new Error("Failed to fetch PDF URL");
      }
    } catch (error) {
      console.error("Error fetching raw text or PDF URL:", error);
      setRawText("Failed to fetch raw text.");
      setPdfUrl("");
    }
  };

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

  return (
    <div className="app-container">
      <h1 className="title">Admin PDF Uploader</h1>

      {/* File Selection */}
      <div className="form-group">
        <label className="label">Pick a PDF:</label>
        <input
          className="file-input"
          type="file"
          accept="application/pdf"
          onChange={handleFileChange}
        />
      </div>

      {/* Chunk Size */}
      <div className="form-group">
        <label className="label">Chunk Size:</label>
        <input
          className="number-input"
          type="number"
          value={chunkSize}
          onChange={(e) => setChunkSize(Number(e.target.value))}
          min="100"
          max="5000"
        />
      </div>

      {/* Chunk Overlap */}
      <div className="form-group">
        <label className="label">Chunk Overlap:</label>
        <input
          className="number-input"
          type="number"
          value={chunkOverlap}
          onChange={(e) => setChunkOverlap(Number(e.target.value))}
          min="0"
          max="1000"
        />
      </div>

      {/* Upload Button */}
      <button className="upload-button" onClick={handleUpload} disabled={uploading}>
        {uploading ? <ClipLoader color={"#ffffff"} size={20} /> : "Upload & Process PDF"}
      </button>

      {/* Success Message */}
      {uploadSuccess && (
        <div className="success-message">
          <p>✅ Upload and processing completed successfully!</p>
        </div>
      )}

      {/* Error or Info Message */}
      {message && (
        <div className={`message-box ${uploadSuccess ? "success" : "error"}`}>
          <p>{message}</p>
        </div>
      )}

      {/* Raw Text Preview */}
      {rawText && (
        <div className="raw-text-box">
          <h2>Raw Text Preview:</h2>
          <textarea
            className="raw-textarea"
            value={rawText}
            readOnly
            rows="10"
          />
        </div>
      )}

      {/* PDF Viewer */}
      {pdfUrl && (
        <div className="pdf-viewer-box">
          <h2>PDF Preview:</h2>
          <Document
            file={pdfUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            className="pdf-document"
          >
            {Array.from(new Array(numPages), (el, index) => (
              <Page
                key={`page_${index + 1}`}
                pageNumber={index + 1}
                className="pdf-page"
              />
            ))}
          </Document>
        </div>
      )}
    </div>
  );
}

export default App;
