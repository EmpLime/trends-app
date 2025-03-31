import React, { useState } from 'react';
import './App.css';

function App() {
  const [keyword, setKeyword] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const fetchTrends = async () => {
    try {
      const res = await fetch(`http://localhost:5000/trends?keyword=${keyword}`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const result = await res.json();
      if (result.error) throw new Error(result.error);
      setData(result);
      setError(null);
    } catch (err) {
      setError(err.message);
      setData(null);
    }
  };

  return (
    <div className="container">
      <h1>Research Topic Explorer</h1>
      <div className="search-bar">
        <input
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Enter research topic (e.g., javascript)"
        />
        <button onClick={fetchTrends}>Search</button>
      </div>

      {error && <p className="error">Error: {error}</p>}

      {data && (
        <div className="results">
          <h2>Search Results</h2>
          <table>
            <thead>
              <tr>
                <th>Title</th>
                <th>Date</th>
                <th>Author</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {data.results
                .filter(r => r.title !== 'N/A' && r.link && r.link !== '#')
                .map((r, i) => (
                  <tr key={i}>
                    <td>
                      <a href={r.link} target="_blank" rel="noopener noreferrer">
                        {r.title}
                      </a>
                    </td>
                    <td>{r.date !== 'N/A' ? r.date : '-'}</td>
                    <td>{r.author !== 'N/A' ? r.author : '-'}</td>
                    <td>{r.source}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default App;