import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./Dashboard";
import RepoDetails from "./RepoDetails";
import "./index.css";

function App() {

  const handleLogin = () => {
    window.location.href = "http://localhost:8000/auth/github";
  };

  return (
    <Router>
      <Routes>

        <Route path="/" element={
          <div className="container" style={{ textAlign: "center", marginTop: "100px" }}>
            <h1 style={{ fontSize: "40px" }}>🚀 MergeMind</h1>
            <p style={{ color: "#8b949e" }}>
              AI-powered GitHub PR Reviewer
            </p>

            <button className="button" onClick={handleLogin}>
              Login with GitHub
            </button>
          </div>
        } />

        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/repo/:owner/:repo" element={<RepoDetails />} />

      </Routes>
    </Router>
  );
}

export default App;