import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

function Dashboard() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    axios.get("http://localhost:8000/repos")
      .then(res => {
        setRepos(res.data || []);
        setLoading(false); // ✅ FIX
      })
      .catch(err => {
        console.error("Repo fetch error:", err);
        setLoading(false); // ✅ FIX
      });
  }, []);

  return (
    <div className="container">
      <h1>📦 Your Repositories</h1>

      {/* LOADER */}
{loading && (
  <div className="loader">
    <div className="spinner"></div>
    <p className="loader-text">Fetching your repositories...</p>
    <div className="progress-bar">
      <div className="progress-fill"></div>
    </div>
  </div>
)}
      {/* ✅ EMPTY STATE */}
      {!loading && repos.length === 0 && (
        <p style={{ color: "#8b949e" }}>
          No repositories found 🚫
        </p>
      )}

      {/* ✅ REPO LIST */}
      {!loading && repos.map(repo => (
        <div
          key={repo.id}
          className="card"
          onClick={() => navigate(`/repo/${repo.owner.login}/${repo.name}`)}
        >
          <h3>{repo.name}</h3>
          <p style={{ color: "#8b949e" }}>
            {repo.description || "No description"}
          </p>
        </div>
      ))}
    </div>
  );
}

export default Dashboard;