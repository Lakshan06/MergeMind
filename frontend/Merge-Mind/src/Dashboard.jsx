import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

function Dashboard() {
  const [repos, setRepos] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    axios.get("http://localhost:8000/repos")
      .then(res => setRepos(res.data || []))
      .catch(err => console.error("Repo fetch error:", err));
  }, []);

  return (
    <div className="container">
      <h1>📦 Your Repositories</h1>

      {repos.map(repo => (
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