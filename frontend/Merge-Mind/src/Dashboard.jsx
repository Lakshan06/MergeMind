import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";

function Dashboard() {
  const [repos, setRepos] = useState([]);
  const navigate = useNavigate(); // ✅ MUST be inside component

  useEffect(() => {
    axios.get("http://localhost:8000/repos")
      .then(res => {
        console.log(res.data);
        setRepos(res.data);
      })
      .catch(err => console.error(err));
  }, []);

  return (
    <div>
      <h1>Your Repositories</h1>

      {repos.map(repo => (
        <div 
          key={repo.id}
          onClick={() => navigate(`/repo/${repo.owner.login}/${repo.name}`)} // ✅ CLICK HANDLER
          style={{
            border: "1px solid gray",
            margin: "10px",
            padding: "10px",
            cursor: "pointer"
          }}
        >
          <h3>{repo.name}</h3>
          <p>{repo.description}</p>
        </div>
      ))}

    </div>
  );
}

export default Dashboard;