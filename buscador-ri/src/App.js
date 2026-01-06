import { useState } from "react";
import "./App.css";

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    setError("");
    try {
      const response = await fetch("http://localhost:8000/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: query,
          topk: 20,
          page: 1,
          page_size: 10,
        }),
      });

      if (!response.ok) {
        throw new Error("Response HTTP not OK");
      }

      const data = await response.json();
      setResults(data.results ?? []);
    } catch (error) {
      console.error("Error al hacer search:", error);
      setError("Error al buscar — revisa la consola.");
      setResults([]);
    }
  };

  return (
    <div className="app-container">
      <h1>Buscador de Recuperación de Información</h1>

      <div className="search-bar">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Escribe tu consulta..."
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSearch();
            }
          }}
        />
        <button onClick={handleSearch}>Buscar</button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="results-container">
        {results.map((result) => (
          <div key={result.doc_id} className="result-item">
            {/* Título que actúa como enlace */}
            <a
              href={result.path}
              target="_blank"
              rel="noopener noreferrer"
              className="result-title"
            >
              <h3>{result.title || result.path}</h3>
            </a>

            {/* Snippet con HTML (resaltado) */}
            <p
              className="result-snippet"
              dangerouslySetInnerHTML={{ __html: result.snippet }}
            ></p>

            {/* Metadatos adicionales */}
            <div className="result-meta">
              <span className="score">
                Score: {(result.score ?? 0).toFixed(4)}
              </span>
              <span className="path">Path: {result.path}</span>
            </div>

            <hr />
          </div>
        ))}

        {/* Si no hay resultados después de buscar */}
        {results.length === 0 && query && (
          <p>No se obtuvieron resultados para esta consulta.</p>
        )}
      </div>
    </div>
  );
}

export default App;