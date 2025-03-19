import React, { useState, useEffect } from "react";
import "./App.css"; // <-- Import the CSS file

function App() {
  const [contexts, setContexts] = useState([]);
  const [selectedContext, setSelectedContext] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loadingContext, setLoadingContext] = useState(false);
  const [loadingAnswer, setLoadingAnswer] = useState(false);

  // We'll store the first 500 chars of the context here:
  const [contextPreview, setContextPreview] = useState("");

  // Fetch available contexts on mount
  useEffect(() => {
    const fetchContexts = async () => {
      try {
        const res = await fetch("http://localhost:8000/list-contexts");
        if (!res.ok) {
          throw new Error("Failed to fetch contexts.");
        }
        const data = await res.json();
        setContexts(data);
      } catch (err) {
        console.error("Error fetching contexts:", err);
        // Optionally, set an error state to display in the UI
      }
    };

    fetchContexts();
  }, []);

  // This fetches the first 500 characters from the preview endpoint:
  const fetchContextPreview = async (baseName) => {
    try {
      const res = await fetch(`http://localhost:8000/preview-context?base_name=${baseName}`);
      if (!res.ok) {
        console.error("Error fetching context preview");
        setContextPreview("Unable to preview context.");
        return;
      }
      const data = await res.json(); // Assuming the endpoint returns JSON like { preview: "..." }
      // data.preview is the first 500 chars
      setContextPreview(data.preview || "No preview available.");
    } catch (error) {
      console.error("Error fetching context preview:", error);
      setContextPreview("Error fetching context preview.");
    }
  };

  const handleLoadContext = async () => {
    if (!selectedContext) return;
    setLoadingContext(true);
    setAnswer(""); // clear previous answers
    setContextPreview(""); // clear old preview
    try {
      const response = await fetch("http://localhost:8000/load-context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ base_name: selectedContext }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        alert(`Error: ${errorData.detail}`);
      } else {
        // Optionally, you can show a non-intrusive notification instead of alert
        // For better UX, consider using a toast notification library
        alert(`Loaded context: ${selectedContext}`);
        // Now fetch the first 500 chars
        await fetchContextPreview(selectedContext);
      }
    } catch (err) {
      console.error("Error loading context:", err);
      alert("Error loading context. Check console.");
    } finally {
      setLoadingContext(false);
    }
  };

  const handleAskQuestion = async () => {
    if (!selectedContext) {
      alert("Please select and load a context first.");
      return;
    }
    if (!question.trim()) {
      alert("Please enter a valid question.");
      return;
    }

    setLoadingAnswer(true);
    setAnswer("");

    try {
      const response = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ base_name: selectedContext, question }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        alert(`Error: ${errorData.detail}`);
      } else {
        const data = await response.json();
        setAnswer(data.answer);
      }
    } catch (err) {
      console.error("Error asking question:", err);
      alert("Error asking question. Check console.");
    } finally {
      setLoadingAnswer(false);
    }
  };

  return (
    <div className="container">
      <h1 className="title">RAG with Bedrock Demo</h1>

      {/* CONTEXT SELECTION */}
      <div className="form-group context-selection">
        <div style={{ flex: 1 }}>
          <label>Select Context:</label>
          <select
            className="context-select"
            value={selectedContext}
            onChange={(e) => setSelectedContext(e.target.value)}
          >
            <option value="">-- Choose a context --</option>
            {contexts.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <button
            className="load-button"
            onClick={handleLoadContext}
            disabled={!selectedContext || loadingContext}
          >
            {loadingContext ? "Loading..." : "Load Context"}
          </button>
        </div>

        {/* Show the first 500 chars in a scrollable preview box */}
        {contextPreview && (
          <div className="preview-box">
            {contextPreview}
          </div>
        )}
      </div>

      {/* QUESTION INPUT */}
      <div className="form-group">
        <label>Your Question:</label>
        <textarea
          className="question-textarea"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type your question here..."
        />
      </div>

      <button className="ask-button" onClick={handleAskQuestion} disabled={loadingAnswer}>
        {loadingAnswer ? "Asking..." : "Ask"}
      </button>

      {/* ANSWER DISPLAY */}
      {answer && (
        <div className="answer-box">
          <div className="answer-title">Answer:</div>
          <p>{answer}</p>
        </div>
      )}
    </div>
  );
}

export default App;
