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
  const [mergeAccepted, setMergeAccepted] = useState(false);

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
  console.log("Selected PRs:", selectedPRs);

  if (selectedPRs.length < 2) {
    setSmartResult("❌ Select at least 2 PRs");
    return;
  }

  setMergeAccepted(false); // 🔥 reset state
  setActionLoading(true);
  setSmartResult("🤖 Merging PRs intelligently...");

  try {
    const res = await axios.post(
      "http://localhost:8000/smart-merge",
      {
        owner,
        repo,
        prs: selectedPRs
      },
      { timeout: 180000 }
    );

    if (res.data && res.data.result) {
      setSmartResult(res.data.result);
    } else {
      setSmartResult("❌ No response from AI");
    }

  } catch (err) {
    console.error("SMART MERGE ERROR:", err);
    setSmartResult("❌ Smart merge failed");
  }

  setActionLoading(false);
};

//mergeready Ai
const mergeReady = async () => {
  setActionLoading(true);
  setSmartResult("🟢 Scanning PRs...");

  try {
    const res = await axios.post(
      "http://localhost:8000/merge-ready",
      { owner, repo }
    );

    let text = "";

    if (res.data.ready?.length) {
      text += `### 🟢 Ready to Merge\n${res.data.ready.map(p => `✔ PR #${p}`).join("\n")}\n\n`;
    }

    if (res.data.risky?.length) {
      text += `### ⚠ Risky PRs\n${res.data.risky.map(p => `⚠ PR #${p}`).join("\n")}\n\n`;
    }

    if (res.data.conflict?.length) {
      text += `### ❌ Conflicts\n${res.data.conflict.map(p => `✖ PR #${p}`).join("\n")}\n\n`;
    }

    if (res.data.ai) {
      text += `### 🤖 AI Insight\n${res.data.ai}`;
    }

    setSmartResult(text);

  } catch (err) {
    console.error(err);
    setSmartResult("❌ MergeReady AI failed");
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
      setActivePR(pr.number);   // ✅ for file view
      loadFiles(pr.number);
    }}
  >

    {/* ✅ MULTI SELECT CHECKBOX (FOR SMART MERGE) */}
    <input
      type="checkbox"
      checked={selectedPRs.includes(pr.number)}
      onChange={(e) => {
        e.stopPropagation();   // 🔥 VERY IMPORTANT (prevents click conflict)
        togglePR(pr.number);
      }}
    />

    <span style={{ marginLeft: "10px" }}>
      <h3>{pr.title}</h3>
      <p>👤 {pr.user}</p>
    </span>

    {/* ✅ ACTIVE PR (for file view) */}
    {activePR === pr.number && (
      <p style={{ color: "#58a6ff" }}>📂 Viewing</p>
    )}

    {/* ✅ SELECTED PR (for smart merge) */}
    {selectedPRs.includes(pr.number) && (
      <p style={{ color: "#2ea043" }}>✅ Selected for Merge</p>
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

          <button onClick={mergeReady} disabled={actionLoading}>
         🟢 MergeReady AI
        </button>
        </div>
      )}

      
      {/* SMART RESULT */}
{/* SMART RESULT */}
{smartResult && (
  <div className="ai-box">
    <h3>🤖 Smart Merge Studio</h3>

    {/* 🔥 LOADING UI */}
    {actionLoading && (
      <p style={{ color: "#58a6ff" }}>
        ⏳ AI is merging PRs... please wait
      </p>
    )}

    {/* 🔥 SHOW BUTTONS ONLY WHEN READY */}
    {!actionLoading &&
      smartResult &&
      !mergeAccepted &&
      !smartResult.includes("❌") &&
      !smartResult.includes("⏳") && (
        <div style={{ marginBottom: "15px" }}>
          <button
            style={{
              marginRight: "10px",
              background: "#2ea043",
              border: "none",
              padding: "8px 15px",
              borderRadius: "6px",
              cursor: "pointer"
            }}
            onClick={async () => {
              try {
                setActionLoading(true);

                await axios.post("http://localhost:8000/apply-merge", {
                  owner,
                  repo,
                  prs: selectedPRs,
                  result: smartResult
                });

                setMergeAccepted(true);
              } catch {
                alert("❌ Failed to apply merge");
              }

              setActionLoading(false);
            }}
          >
            ✅ Accept Merge
          </button>

          <button
            style={{
              background: "#f85149",
              border: "none",
              padding: "8px 15px",
              borderRadius: "6px",
              cursor: "pointer"
            }}
            onClick={() => {
              setSmartResult("");
              setMergeAccepted(false);
            }}
          >
            ❌ Reject
          </button>
        </div>
      )}

    {/* 🔥 RESULT DISPLAY */}
    {!actionLoading &&
      smartResult.split("###").map((sec, i) => {
        if (!sec.trim()) return null;

        const lines = sec.trim().split("\n");
        const title = lines[0].toLowerCase();
        const content = lines.slice(1).join("\n");

        let boxStyle = {};
        let icon = "📄";

        if (title.includes("merged")) {
          icon = "📂";
          boxStyle = { borderLeft: "4px solid #58a6ff" };
        }

        if (title.includes("final")) {
          icon = "💻";
          boxStyle = { borderLeft: "4px solid #2ea043" };
        }

        if (title.includes("conflict")) {
          icon = "⚠";
          boxStyle = { borderLeft: "4px solid #f85149" };
        }

        if (title.includes("notes")) {
          icon = "🧠";
          boxStyle = { borderLeft: "4px solid #a371f7" };
        }

        return (
          <div
            key={i}
            style={{
              marginBottom: "20px",
              padding: "15px",
              background: "#161b22",
              borderRadius: "10px",
              ...boxStyle
            }}
          >
            <h4>{icon} {lines[0]}</h4>

            {title.includes("code") ? (
              <pre
                style={{
                  background: "#0d1117",
                  padding: "15px",
                  borderRadius: "8px",
                  overflowX: "auto"
                }}
              >
                {content}
              </pre>
            ) : (
              content.split("\n").map((line, j) => (
                <p key={j}>{line.replace("-", "•")}</p>
              ))
            )}
          </div>
        );
      })}

    {/* SUCCESS */}
    {mergeAccepted && (
      <div style={{ color: "#2ea043", marginTop: "10px" }}>
        ✅ Merge Applied Successfully 🚀
      </div>
    )}
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