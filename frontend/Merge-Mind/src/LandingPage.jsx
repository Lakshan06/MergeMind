import Navbar from "./Navbar";

function LandingPage() {

  const handleLogin = () => {
    window.location.href = "http://localhost:8000/auth/github";
  };

  return (
    <div className="landing">

      <Navbar />

      {/* HERO */}
      <section className="hero">
        <div className="hero-content">

          <h1 className="hero-title">
            🚀 MergeMind
          </h1>

          <p className="hero-subtitle">
            AI-powered GitHub PR Intelligence — Review faster, merge safer.
          </p>

          <div className="hero-actions">
            <button className="cta-btn" onClick={handleLogin}>
              Get Started with GitHub
            </button>
          </div>

        </div>
      </section>

      {/* ABOUT */}
      <section id="about" className="section">
        <h2>What is MergeMind?</h2>
        <p>
          MergeMind is an AI-powered code review assistant that analyzes GitHub pull requests,
          detects risks, highlights conflicts, and provides intelligent merge suggestions —
          helping developers save time and reduce errors.
        </p>
      </section>

      {/* PROBLEM */}
      <section className="section alt">
        <h2>The Problem</h2>
        <p>
          Developers spend hours reviewing pull requests, identifying conflicts,
          and understanding code changes. This slows down development and increases
          the chance of production bugs.
        </p>
      </section>

      {/* FEATURES */}
      <section id="features" className="section">
        <h2>Our Solution</h2>

        <div className="features">

          <div className="feature-card">
            <h3>🤖 AI PR Analysis</h3>
            <p>Understand code changes instantly with AI-generated summaries.</p>
          </div>

          <div className="feature-card">
            <h3>⚠️ Conflict Detection</h3>
            <p>Identify merge risks before they become a problem.</p>
          </div>

          <div className="feature-card">
            <h3>✅ Smart Suggestions</h3>
            <p>Get actionable recommendations for safer merges.</p>
          </div>

        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <h2>Start reviewing smarter today</h2>
        <button className="cta-btn" onClick={handleLogin}>
          Login with GitHub
        </button>
      </section>

    </div>
  );
}

export default LandingPage;