// src/App.js
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: query,
          topk: 50,
          page: 1,
          page_size: 50,
        }),
      });

      if (!response.ok) {
        throw new Error("Error en la búsqueda");
      }

      const data = await response.json();
      setResults(data.results || []);
    } catch (e) {
      console.error("Error al hacer search:", e);
      setError("Error al obtener resultados del servidor");
      setResults([]);
    }
  };

  return (
    <div className="app-container">
      <h1>Buscador de Recuperación de Información</h1>

      <div className="search-box">
        <input
          type="text"
          value={query}
          placeholder="Escribe tu consulta..."
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        />
        <button onClick={handleSearch}>Buscar</button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="results-list">
        {results.map((item) => (
          <div key={item.doc_id} className="result-card">

            {/* Título (enlace al path) */}
            <a
              href={item.path}
              target="_blank"
              rel="noopener noreferrer"
              className="result-title"
            >
              <h3>{item.title || item.path}</h3>
            </a>

            {/* URL/ruta interna */}
            <p><strong>Ruta Interna:</strong> {item.path}</p>

            {/* Snippet */}
            <p
              className="snippet"
              dangerouslySetInnerHTML={{ __html: item.snippet }}
            ></p>

            {/* Scores */}
            <p><strong>Score BM25:</strong> {item.score_bm25?.toFixed(4)}</p>
            <p><strong>Score Final:</strong> {item.score?.toFixed(4)}</p>

            {/* PageRank */}
            <p><strong>PageRank (crudo):</strong> {item.pagerank_raw?.toFixed(6)}</p>
            <p><strong>PageRank (normalizado):</strong> {item.pagerank_norm?.toFixed(6)}</p>

            {/* Conteo de palabras y tokens */}
            <p><strong>Words Count:</strong> {item.word_count}</p>
            <p><strong>Total Tokens:</strong> {item.total_tokens}</p>

            {/* Tokens → lista */}
            {item.tokens && item.tokens.length > 0 && (
              <p><strong>Tokens (primeros):</strong> {item.tokens.join(", ")}</p>
            )}

            {/* TF-IDF (top términos si existen) */}
            {item.tfidf && Object.keys(item.tfidf).length > 0 && (
              <div>
                <strong>TF-IDF (términos):</strong>
                <ul className="tfidf-list">
                  {Object.entries(item.tfidf).map(([term, val]) => (
                    <li key={term}>
                      {term}: {val.toFixed(6)}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <hr />
          </div>
        ))}
      </div>

      {results.length === 0 && query && (
        <p>No se encontraron resultados para: "{query}"</p>
      )}
    </div>
  );
}

export default App;