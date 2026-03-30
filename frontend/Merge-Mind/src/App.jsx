import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./Dashboard";
import RepoDetails from "./RepoDetails";
import LandingPage from "./LandingPage";
import "./index.css";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/repo/:owner/:repo" element={<RepoDetails />} />
      </Routes>
    </Router>
  );
}

export default App;