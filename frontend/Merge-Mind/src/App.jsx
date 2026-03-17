import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Dashboard from "./Dashboard";

function App() {

  const handleLogin = () => {
    window.location.href = "http://localhost:8000/auth/github";
  };

  return (
    <Router>
      <Routes>
        
        <Route path="/" element={
          <div>
            <h1>MergeMind</h1>
            <button onClick={handleLogin}>
              Login with GitHub
            </button>
          </div>
        } />

        <Route path="/dashboard" element={<Dashboard />} />

      </Routes>
    </Router>
  );
}

export default App;