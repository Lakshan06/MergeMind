import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import axios from "axios";

function RepoDetails() {
  const { owner, repo } = useParams();

  const [prs, setPrs] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selectedPRs, setSelectedPRs] = useState([]);
  const [activePR, setActivePR] = useState(null);

  const [files, setFiles] = useState([]);
  const [suggestions, setSuggestions] = useState({});
  const [aiLoading, setAiLoading] = useState({});
  const [actionLoading, setActionLoading] = useState(false);
  const [smartResult, setSmartResult] = useState("");
  const [mergedFiles, setMergedFiles] = useState({});  // {filename: code} from smart-merge
  const [mergeAccepted, setMergeAccepted] = useState(false);
  const [createdPR, setCreatedPR] = useState(null);   // {pr_url, pr_number, branch}

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

  // SMART MERGE
  const smartMerge = async () => {
    if (selectedPRs.length < 2) {
      setSmartResult("❌ Select at least 2 PRs");
      return;
    }

    setMergeAccepted(false);
    setCreatedPR(null);
    setMergedFiles({});
    setActionLoading(true);
    setSmartResult("🤖 AI is fetching and merging your PRs...");

    try {
      const res = await axios.post(
        "http://localhost:8000/smart-merge",
        { owner, repo, prs: selectedPRs },
        { timeout: 240000 }
      );

      if (res.data?.result) {
        setSmartResult(res.data.result);
        setMergedFiles(res.data.files || {});   // store structured files for real PR
      } else {
        setSmartResult("❌ No response from AI");
      }
    } catch (err) {
      console.error("SMART MERGE ERROR:", err);
      setSmartResult("❌ Smart merge failed — " + (err.message || "unknown error"));
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
{smartResult && (
  <div className="ai-box">
    <h3>🤖 Smart Merge Studio</h3>

    {/* LOADING */}
    {actionLoading && (
      <div>
        <p style={{ color: "#58a6ff" }}>🤖 AI is analysing and merging your PRs...</p>
        <div className="progress-bar"><div className="progress-fill"></div></div>
      </div>
    )}

    {/* ACTION BUTTONS — Accept / Reject */}
    {!actionLoading && smartResult && !mergeAccepted &&
      !smartResult.includes("❌") && !smartResult.includes("⏳") &&
      Object.keys(mergedFiles).length > 0 && (
        <div style={{ marginBottom: "16px", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>

          {/* ACCEPT — creates real GitHub PR */}
          <button
            id="accept-merge-btn"
            style={{ background: "#2ea043", border: "none", padding: "10px 20px", borderRadius: "6px", cursor: "pointer", fontWeight: 700, fontSize: "14px", color: "#fff" }}
            onClick={async () => {
              setActionLoading(true);
              try {
                const res = await axios.post(
                  "http://localhost:8000/apply-merge",
                  {
                    owner,
                    repo,
                    prs: selectedPRs,
                    merged_files: mergedFiles   // real structured data, not markdown
                  },
                  { timeout: 60000 }
                );

                if (res.data?.status === "success") {
                  setMergeAccepted(true);
                  setCreatedPR(res.data);   // {pr_url, pr_number, branch, committed}
                } else {
                  alert("❌ " + (res.data?.message || "PR creation failed"));
                }
              } catch (err) {
                alert("❌ Failed: " + (err.response?.data?.message || err.message));
              }
              setActionLoading(false);
            }}
          >
            ✅ Accept &amp; Create PR
          </button>

          {/* REJECT */}
          <button
            id="reject-merge-btn"
            style={{ background: "#f85149", border: "none", padding: "10px 20px", borderRadius: "6px", cursor: "pointer", fontWeight: 700, fontSize: "14px", color: "#fff" }}
            onClick={() => {
              setSmartResult("");
              setMergedFiles({});
              setMergeAccepted(false);
              setCreatedPR(null);
            }}
          >
            ❌ Reject
          </button>

          <span style={{ color: "#8b949e", fontSize: "12px" }}>
            💡 Accept will create a real GitHub PR with the merged code
          </span>
        </div>
      )}

    {/* SMART MERGE RESULT RENDERER */}
    {!actionLoading && (() => {
      const sections = smartResult.split(/\n(?=### )/).filter(s => s.trim());

      return sections.map((sec, i) => {
        const lines   = sec.trim().split("\n");
        const rawTitle = lines[0].replace(/^### /, "").trim();
        const body    = lines.slice(1).join("\n").trim();

        // ── "Final Merged Code" section → code card with Copy button
        if (rawTitle === "Final Merged Code") {
          const codeMatch = body.match(/```[^\n]*\n([\s\S]*?)```/);
          const code = codeMatch ? codeMatch[1] : body;
          return (
            <div key={i} style={{ marginBottom: "20px", borderRadius: "10px", overflow: "hidden", border: "1px solid #2ea043" }}>
              <div style={{ background: "#161b22", padding: "10px 15px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#2ea043", fontWeight: 700 }}>💻 Final Merged Code</span>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(code);
                    alert("✅ Code copied to clipboard!");
                  }}
                  style={{ background: "#238636", border: "none", color: "#fff", padding: "5px 12px", borderRadius: "5px", cursor: "pointer", fontSize: "12px", fontWeight: 600 }}
                >📋 Copy Code</button>
              </div>
              <pre style={{ background: "#0d1117", margin: 0, padding: "16px", overflowX: "auto", whiteSpace: "pre", fontSize: "13px", lineHeight: "1.5", color: "#e6edf3" }}>
                {code.trim()}
              </pre>
            </div>
          );
        }

        // ── "Merge Explanation" section → formatted explanation card
        if (rawTitle === "Merge Explanation") {
          const explanationLines = body.split("\n");
          return (
            <div key={i} style={{ marginBottom: "20px", padding: "16px", background: "#161b22", borderRadius: "10px", borderLeft: "4px solid #a371f7" }}>
              <h4 style={{ color: "#a371f7", marginBottom: "12px" }}>🧠 Merge Explanation</h4>
              {explanationLines.map((line, j) => {
                if (!line.trim()) return <br key={j} />;
                if (line.startsWith("**") && line.endsWith("**"))
                  return <p key={j} style={{ color: "#58a6ff", fontWeight: 700, marginTop: "10px", marginBottom: "4px" }}>{line.replace(/\*\*/g, "")}</p>;
                if (line.startsWith("- "))
                  return <p key={j} style={{ color: "#c9d1d9", paddingLeft: "12px", marginBottom: "4px" }}>• {line.slice(2)}</p>;
                return <p key={j} style={{ color: "#c9d1d9", marginBottom: "4px" }}>{line}</p>;
              })}
            </div>
          );
        }

        // ── "📄 File:" section header
        if (rawTitle.startsWith("📄 File:")) {
          return (
            <div key={i} style={{ margin: "24px 0 8px 0", padding: "10px 14px", background: "#21262d", borderRadius: "8px", borderLeft: "4px solid #58a6ff" }}>
              <h4 style={{ color: "#58a6ff", margin: 0 }}>📄 {rawTitle.replace("📄 ", "")}</h4>
            </div>
          );
        }

        // ── "Merged PRs" summary
        if (rawTitle === "Merged PRs") {
          return (
            <div key={i} style={{ marginBottom: "16px", padding: "12px 16px", background: "#161b22", borderRadius: "8px", borderLeft: "4px solid #58a6ff" }}>
              <h4 style={{ color: "#58a6ff", marginBottom: "8px" }}>🔀 Merged PRs</h4>
              {body.split("\n").filter(Boolean).map((l, j) => (
                <p key={j} style={{ color: "#c9d1d9", marginBottom: "4px" }}>{l.replace(/\*\*/g, "")}</p>
              ))}
            </div>
          );
        }

        // ── "Developer Notes" & everything else
        if (rawTitle === "Developer Notes") {
          return (
            <div key={i} style={{ marginTop: "16px", padding: "12px 16px", background: "#161b22", borderRadius: "8px", borderLeft: "4px solid #30363d", opacity: 0.75 }}>
              <h4 style={{ color: "#8b949e", marginBottom: "8px" }}>🧾 Developer Notes</h4>
              {body.split("\n").filter(Boolean).map((l, j) => (
                <p key={j} style={{ color: "#8b949e", fontSize: "12px", marginBottom: "2px" }}>{l}</p>
              ))}
            </div>
          );
        }

        // ── Separator line (---)
        if (rawTitle === "---") return <hr key={i} style={{ borderColor: "#30363d", margin: "20px 0" }} />;

        // ── Generic fallback section
        return (
          <div key={i} style={{ marginBottom: "16px", padding: "14px", background: "#161b22", borderRadius: "8px" }}>
            <h4 style={{ color: "#e6edf3", marginBottom: "8px" }}>{rawTitle}</h4>
            {body.split("\n").map((l, j) => <p key={j} style={{ color: "#c9d1d9", marginBottom: "4px" }}>{l}</p>)}
          </div>
        );
      });
    })()}

    {/* SUCCESS BANNER — real PR created */}
    {mergeAccepted && createdPR && (
      <div style={{
        marginTop: "16px",
        padding: "16px 20px",
        background: "#0d2d1a",
        border: "1px solid #2ea043",
        borderRadius: "10px"
      }}>
        <p style={{ color: "#3fb950", fontWeight: 700, fontSize: "16px", marginBottom: "8px" }}>
          ✅ PR #{createdPR.pr_number} created successfully!
        </p>
        <p style={{ color: "#8b949e", fontSize: "13px", marginBottom: "12px" }}>
          Branch: <code style={{ color: "#58a6ff" }}>{createdPR.branch}</code>
          &nbsp;·&nbsp;
          Files committed: {createdPR.committed?.join(", ")}
        </p>
        <a
          href={createdPR.pr_url}
          target="_blank"
          rel="noreferrer"
          style={{
            display: "inline-block",
            background: "#238636",
            color: "#fff",
            padding: "8px 18px",
            borderRadius: "6px",
            fontWeight: 700,
            textDecoration: "none",
            fontSize: "14px"
          }}
        >
          🔗 View PR on GitHub →
        </a>
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

              <button className="aisuggest" onClick={() => getSuggestion(file.patch, index)}>
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