import { useEffect, useState } from "react";
import axios from "axios";

function Dashboard() {
  const [repos, setRepos] = useState([]);

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
        <div key={repo.id} style={{border: "1px solid gray", margin: "10px", padding: "10px"}}>
          <h3>{repo.name}</h3>
          <p>{repo.description}</p>
        </div>
      ))}

    </div>
  );
}

export default Dashboard;