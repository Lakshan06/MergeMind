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

  // 🔹 Fetch PRs
  useEffect(() => {
    axios.get(`http://localhost:8000/prs/${owner}/${repo}`)
      .then(res => {
        console.log("PRS DATA:", res.data);
        setPrs(res.data || []);
        setLoading(false);
      })
      .catch(err => {
        console.error("ERROR:", err);
        setLoading(false);
      });
  }, [owner, repo]);

  // 🔹 Load files of PR
  const loadFiles = (prNumber) => {
    setSelectedPR(prNumber);

    axios.get(`http://localhost:8000/pr-files/${owner}/${repo}/${prNumber}`)
      .then(res => {
        console.log("FILES:", res.data);
        setFiles(res.data || []);
      })
      .catch(err => console.error(err));
  };

  // 🔹 AI Suggestion
  const getSuggestion = (patch, index) => {
    axios.post("http://localhost:8000/ai-suggest", { patch })
      .then(res => {
        setSuggestions(prev => ({
          ...prev,
          [index]: res.data.suggestion
        }));
      })
      .catch(err => console.error(err));
  };

  return (
    <div>
      <h1>PRs for {repo}</h1>

      {loading && <p>Loading PRs...</p>}

      {!loading && prs.length === 0 && (
        <p>No Pull Requests found 🚫</p>
      )}

      {/* 🔹 PR LIST */}
      {prs.map(pr => (
        <div
          key={pr.number}
          onClick={() => loadFiles(pr.number)}
          style={{
            border: "1px solid gray",
            margin: "10px",
            padding: "10px",
            cursor: "pointer"
          }}
        >
          <h3>{pr.title}</h3>
          <p>By: {pr.user}</p>

          <p>
            Status: {
              pr.mergeable === true ? "✅ No Conflict" :
              pr.mergeable === false ? "❌ Conflict" :
              "⏳ Checking..."
            }
          </p>
        </div>
      ))}

      {/* 🔹 FILES SECTION */}
      {selectedPR && (
        <div>
          <h2>Changed Files (PR #{selectedPR})</h2>

          {files.length === 0 && <p>No file changes</p>}

          {files.map((file, index) => (
            <div key={index} style={{
              border: "1px solid red",
              margin: "10px",
              padding: "10px"
            }}>
              <h4>{file.filename}</h4>
              <p>Status: {file.status}</p>

              <pre style={{
                background: "#eee",
                padding: "10px",
                overflowX: "auto"
              }}>
                {file.patch}
              </pre>

              <button onClick={() => getSuggestion(file.patch, index)}>
                Get AI Suggestion
              </button>

              {suggestions[index] && (
                <p style={{
                  color: "green",
                  fontWeight: "bold"
                }}>
                  {suggestions[index]}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default RepoDetails;