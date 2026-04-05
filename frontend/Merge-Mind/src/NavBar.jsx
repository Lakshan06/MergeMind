import { Link, useLocation } from "react-router-dom";

function Navbar() {
  const location = useLocation();

  const handleHomeClick = () => {
    if (location.pathname === "/") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <nav className="navbar">
     
      <h2 className="logo">🚀 MergeMind</h2>

      <div className="nav-links">
        <Link to="/" onClick={handleHomeClick}>Home</Link>
        <a href="#about">About</a>
        <a href="#features">Features</a>
        <Link to="/dashboard" className="nav-btn">Dashboard</Link>
      </div>
    </nav>
  );
}

export default Navbar;