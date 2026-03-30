import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import axios from "axios";

function RepoDetails() {
  const { owner, repo } = useParams();

  const [prs, setPrs] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selectedPRs, setSelectedPRs] = useState([]); // 🔥 MULTI SELECT
  const [activePR, setActivePR] = useState(null);

  const [files, setFiles] = useState([]);
  const [suggestions, setSuggestions] = useState({});
  const [aiLoading, setAiLoading] = useState({});
  const [actionLoading, setActionLoading] = useState(false);
  const [smartResult, setSmartResult] = useState("");

  // FETCH PRs
  useEffect(() => {
    axios.get(`http://localhost:8000/prs/${owner}/${repo}`)
      .then(res => {
        setPrs(res.data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [owner, repo]);

  // LOAD FILES
  const loadFiles = (prNumber) => {
    setActivePR(prNumber);
    setSmartResult("");

    axios.get(`http://localhost:8000/pr-files/${owner}/${repo}/${prNumber}`)
      .then(res => setFiles(res.data || []));
  };

  // 🔥 SELECT MULTIPLE PRs
  const togglePR = (prNumber) => {
    setSelectedPRs(prev => {
      if (prev.includes(prNumber)) {
        return prev.filter(p => p !== prNumber);
      } else {
        return [...prev, prNumber];
      }
    });
  };

  // AI Suggest
  const getSuggestion = async (patch, index) => {
    setAiLoading(prev => ({ ...prev, [index]: true }));

    const res = await axios.post(
      "http://localhost:8000/ai-suggest",
      { patch }
    );

    setSuggestions(prev => ({
      ...prev,
      [index]: res.data.suggestion
    }));

    setAiLoading(prev => ({ ...prev, [index]: false }));
  };

  // 🔥 SMART MERGE FIXED
 const smartMerge = async () => {
  console.log("Selected PR:", activePR); // DEBUG

  if (!activePR) {
    setSmartResult("❌ Please click a PR first");
    return;
  }

  setActionLoading(true);
  setSmartResult("🤖 Analyzing PR...");

  try {
    const res = await axios.post(
      "http://localhost:8000/smart-merge",
      {
        owner,
        repo,
        pr: activePR   // ✅ FIXED HERE
      },
      { timeout: 180000 }
    );

    console.log("Smart Merge Response:", res.data);

    if (res.data && res.data.result) {
      setSmartResult(res.data.result);
    } else {
      setSmartResult("❌ No response from AI");
    }

  } catch (err) {
    console.error("SMART MERGE FRONTEND ERROR:", err);
    setSmartResult("❌ Smart merge failed");
  }

  setActionLoading(false);
};

  // BEST PR
  const bestPR = async () => {
    setActionLoading(true);

    try {
      const res = await axios.post(
        "http://localhost:8000/best-pr",
        { owner, repo }
      );

      setSmartResult(`⭐ Best PR Recommended: #${res.data.best_pr}`);

    } catch {
      setSmartResult("❌ Best PR failed");
    }

    setActionLoading(false);
  };

  return (
    <div className="container">
      <h1>🔀 PRs for {repo}</h1>

      {loading && <div className="spinner"></div>}

     
      {/* PR LIST */}
{prs.map(pr => (
  <div
    key={pr.number}
    className="card"
    onClick={() => {
      setActivePR(pr.number);   // ✅ SET SELECTED PR
      loadFiles(pr.number);     // ✅ LOAD FILES
    }}
  >

    {/* ✅ CHECKBOX (optional, keep if needed) */}
    <input
      type="checkbox"
      checked={selectedPRs.includes(pr.number)}
      onChange={(e) => {
        e.stopPropagation();   // ✅ IMPORTANT FIX
        togglePR(pr.number);
      }}
    />

    <span style={{ marginLeft: "10px" }}>
      <h3>{pr.title}</h3>
      <p>👤 {pr.user}</p>
    </span>

    {/* ✅ SHOW SELECTED PR */}
    {activePR === pr.number && (
      <p style={{ color: "#58a6ff" }}>✅ Selected</p>
    )}

  </div>
))}

      {/* SELECTED PR DISPLAY */}
      {selectedPRs.length > 0 && (
        <p style={{ marginTop: "10px", color: "#58a6ff" }}>
          Selected PRs: {selectedPRs.join(", ")}
        </p>
      )}

      {/* ACTION PANEL */}
      {selectedPRs.length > 0 && (
        <div className="ai-actions">
          <button onClick={smartMerge} disabled={actionLoading}>
            {actionLoading ? "🤖 Processing..." : "🤖 Smart Merge"}
          </button>

          <button onClick={bestPR} disabled={actionLoading}>
            ⭐ Best PR
          </button>
        </div>
      )}

      {/* SMART RESULT */}
      {smartResult && (
        <div className="ai-box">
          <h3>🤖 AI Result</h3>

          {smartResult.split("###").map((sec, i) => {
            if (!sec.trim()) return null;

            const lines = sec.trim().split("\n");
            const title = lines[0];
            const content = lines.slice(1).join("\n");

            return (
              <div key={i}>
                <h4>{title}</h4>

                {title.toLowerCase().includes("code") ? (
                  <pre>{content}</pre>
                ) : (
                  <p>{content}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* FILE VIEW */}
      {activePR && (
        <div>
          <h2>📂 Files (PR #{activePR})</h2>

          {files.map((file, index) => (
            <div key={index} className="card">
              <h4>{file.filename}</h4>
              <pre>{file.patch}</pre>

              <button class= "aisuggest" onClick={() => getSuggestion(file.patch, index)}>
                {aiLoading[index] ? "👀Analyzing..." : "AI Suggest ✦"}
              </button>

              {suggestions[index] && (
                <div className="ai-box">
                  {suggestions[index].split("###").map((sec, i) => {
                    if (!sec.trim()) return null;

                    const lines = sec.trim().split("\n");
                    const title = lines[0];
                    const content = lines.slice(1);

                    return (
                      <div key={i}>
                        <h4>{title}</h4>
                        {content.map((line, j) => (
                          <p key={j}>{line.replace("-", "•")}</p>
                        ))}
                      </div>
                    );
                  })}
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