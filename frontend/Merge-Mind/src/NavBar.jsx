import { Link } from "react-router-dom";

function Navbar() {
  return (
    <nav className="navbar">
      <h2 className="logo">🚀 MergeMind</h2>

      <div className="nav-links">
        <Link to="/">Home</Link>
        <a href="#about">About</a>
        <a href="#features">Features</a>
        <Link to="/dashboard" className="nav-btn">Dashboard</Link>
      </div>
    </nav>
  );
}

export default Navbar;