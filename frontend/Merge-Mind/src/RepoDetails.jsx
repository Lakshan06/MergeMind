import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import axios from "axios";

function RepoDetails() {
  const { owner, repo } = useParams();

  const [prs, setPrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPR, setSelectedPR] = useState(null);
  const [files, setFiles] = useState([]);
  const [suggestions, setSuggestions] = useState({});
  const [aiLoading, setAiLoading] = useState({});

  useEffect(() => {
    axios.get(`http://localhost:8000/prs/${owner}/${repo}`)
      .then(res => {
        setPrs(res.data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("PR fetch error:", err);
        setLoading(false);
      });
  }, [owner, repo]);

  const loadFiles = (prNumber) => {
    setSelectedPR(prNumber);

    axios.get(`http://localhost:8000/pr-files/${owner}/${repo}/${prNumber}`)
      .then(res => setFiles(res.data || []))
      .catch(err => console.error("Files fetch error:", err));
  };

  const getSuggestion = async (patch, index) => {
    if (!patch) {
      alert("No patch data available");
      return;
    }

    setAiLoading(prev => ({ ...prev, [index]: true }));

    try {
      const res = await axios.post(
        "http://localhost:8000/ai-suggest",
        { patch }, // ✅ CORRECT FORMAT
        {
          headers: {
            "Content-Type": "application/json"
          }
        }
      );

      console.log("AI RESPONSE:", res.data);

      setSuggestions(prev => ({
        ...prev,
        [index]: res.data.suggestion || "No suggestion returned"
      }));

    } catch (err) {
      console.error("AI ERROR:", err);
      setSuggestions(prev => ({
        ...prev,
        [index]: "❌ AI request failed"
      }));
    }

    setAiLoading(prev => ({ ...prev, [index]: false }));
  };

  return (
    <div className="container">
      <h1>🔀 PRs for {repo}</h1>

      {loading && <p>Loading PRs...</p>}

      {prs.map(pr => (
        <div
          key={pr.number}
          className="card"
          onClick={() => loadFiles(pr.number)}
        >
          <h3>{pr.title}</h3>
          <p style={{ color: "#8b949e" }}>👤 {pr.user}</p>

          <span className={`badge ${
            pr.mergeable === true ? "success" :
            pr.mergeable === false ? "error" :
            "pending"
          }`}>
            {
              pr.mergeable === true ? "Mergeable" :
              pr.mergeable === false ? "Conflict" :
              "Checking..."
            }
          </span>
        </div>
      ))}

      {selectedPR && (
        <div>
          <h2>📂 Changed Files (PR #{selectedPR})</h2>

          {files.map((file, index) => (
            <div key={index} className="card" style={{ cursor: "default" }}>
              <h4>{file.filename}</h4>
              <p>Status: {file.status}</p>

              <pre style={{
                background: "#0d1117",
                padding: "10px",
                overflowX: "auto",
                fontSize: "12px",
                borderRadius: "6px"
              }}>
                {file.patch || "No diff available"}
              </pre>

              <button
                className="button"
                onClick={(e) => {
                  e.stopPropagation(); // 🔥 IMPORTANT FIX
                  getSuggestion(file.patch, index);
                }}
              >
                {aiLoading[index] ? "🤖 Analyzing..." : "AI Suggest"}
              </button>

              {suggestions[index] && (
                <div className="ai-box">
                  <strong>🧠 AI Review:</strong>
                  <pre style={{ whiteSpace: "pre-wrap" }}>
                    {suggestions[index]}
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RepoDetails;