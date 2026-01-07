import sqlite3
import os
from app.core.paths import data_index_dir

# === DEFINICIÓN DE RUTA GLOBAL A LA BASE DE DATOS ===
DB_PATH = os.path.join(data_index_dir(), "ri_index.db")

def get_connection():
    """
    Conexión SQLite a la base de datos de índice.
    """
    # Asegura que existe la carpeta de índice
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    con = sqlite3.connect(DB_PATH)
    # Puedes habilitar WAL si lo deseas también aquí:
    # con.execute("PRAGMA journal_mode=WAL;")
    return con

def load_graph():
    """
    Construye el grafo de enlaces desde la tabla `links`.
    Devuelve un diccionario {doc_id: [lista de doc_id destino]}.
    """
    con = get_connection()
    cur = con.cursor()

    # Leer todos los doc_id de la tabla docs
    cur.execute("SELECT doc_id FROM docs")
    all_docs = [row[0] for row in cur.fetchall()]

    # Inicializar grafo con nodos sin enlaces
    graph = {doc_id: [] for doc_id in all_docs}

    # Leer enlaces existentes
    cur.execute("SELECT from_doc_id, to_doc_id FROM links")
    for frm, to in cur.fetchall():
        # Añadir enlace solo si ambos existen en el conjunto docs
        if frm in graph and to in graph:
            graph[frm].append(to)

    con.close()
    return graph

def compute_pagerank(graph, damping=0.85, max_iter=100, tol=1.0e-6):
    """
    Calcula PageRank para el grafo dado.
    """
    nodes = list(graph.keys())
    N = len(nodes)
    if N == 0:
        return {}

    # inicializa PageRank uniformemente
    pr = {node: 1.0 / N for node in nodes}
    base = (1.0 - damping) / N

    for iteration in range(max_iter):
        diff = 0.0
        new_pr = {}

        # calcula el nuevo PageRank
        for node in nodes:
            rank_sum = 0.0
            # recorrer cada nodo posible v que enlaza a node
            for v in nodes:
                if node in graph[v]:
                    outdeg = len(graph[v])
                    if outdeg > 0:
                        rank_sum += pr[v] / outdeg

            new_pr[node] = base + damping * rank_sum
            diff += abs(new_pr[node] - pr[node])

        pr = new_pr
        # si la diferencia total < tol → convergencia
        if diff < tol:
            # print(f"[PageRank] Convergencia tras {iteration+1} iteraciones")
            break

    return pr

def save_pagerank(pr_scores):
    """
    Guarda los valores de PageRank en la tabla `pagerank`.
    """
    con = get_connection()
    cur = con.cursor()

    # Crear tabla si no existe (por seguridad)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pagerank(
        doc_id INTEGER PRIMARY KEY,
        rank REAL
    );
    """)

    # Insertar o actualizar el ranking
    for doc_id, score in pr_scores.items():
        cur.execute("""
        INSERT OR REPLACE INTO pagerank(doc_id, rank)
        VALUES (?,?)
        """, (doc_id, score))

    con.commit()
    con.close()

def run_pagerank(verbose: bool = False):
    """
    Función principal para ejecutar todo el flujo de PageRank:
      1) Cargar grafo
      2) Calcular PageRank si hay datos
      3) Guardar resultados en la base de datos
    """

    try:
        # === 1) Cargar grafo desde la base de datos ===
        if verbose:
            print("[PageRank] Cargando grafo de enlaces desde la base de datos...")

        graph = load_graph()

        # === 2) Chequeo de nodos antes de calcular ===
        if not graph:
            if verbose:
                print("[PageRank] No hay nodos en el grafo. Saltando cálculo.")
            return {}
        
        if verbose:
            print(f"[PageRank] Número de nodos en grafo: {len(graph)}")
            print("[PageRank] Calculando PageRank…")

        # === 3) Calcular PageRank ===
        pr_scores = compute_pagerank(graph)

        # === 4) Guardar en la base de datos ===
        if verbose:
            print("[PageRank] Guardando PageRank en la base de datos…")

        save_pagerank(pr_scores)

        if verbose:
            print("[PageRank] Proceso finalizado con éxito.")

        return pr_scores

    except Exception as e:
        # === Manejo de errores ===
        if verbose:
            print(f"[PageRank] Error al ejecutar PageRank: {e}")
        # Devolver diccionario vacío para no romper
        return {}