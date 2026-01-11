# Sistema de Recuperación de Información sobre Wikipedia

**Trabajo Final – P4**  
Autor: Daniel Martínez Infantes  
Curso: 2025–2026  
Universidad: Universidad de Granada (Ceuta)

---

## Descripción general

Este proyecto implementa un **Sistema de Recuperación de Información (SRI)** completo,
capaz de recolectar, procesar, indexar y consultar grandes volúmenes de información
textual procedente de **Wikipedia**.

El sistema ha sido diseñado con un enfoque **modular, escalable y reproducible**,
permitiendo la construcción de un **corpus de más de 10 GB** de contenido textual
respetando las políticas de acceso de los sitios web.

---

## Objetivos

- Diseñar un **crawler concurrente** que respete `robots.txt`
- Construir un **corpus textual de gran tamaño** (>10 GB)
- Implementar un **índice invertido** eficiente
- Desarrollar una **API REST** para indexación y consulta

---

## Arquitectura del sistema

El sistema se divide en cuatro componentes principales:

### 1. Crawler
- Descarga páginas web de forma concurrente usando `ThreadPoolExecutor`
- Respeta `robots.txt` y `crawl-delay`
- Normaliza URLs para evitar duplicados semánticos
- Controla el tamaño máximo del corpus
- Guarda HTML y metadatos en disco organizados por rangos de IDs (buckets)

### 2. Extracción de contenido
- Eliminación de elementos no visibles (scripts, menús, tablas, etc.)
- Extracción de texto principal
- Extractor especializado para Wikipedia (`mw-content-text`)
- Filtros para eliminar bloques de texto irrelevantes

### 3. Indexador
- Tokenización y normalización de texto
- Eliminación de stopwords
- Construcción de índice invertido
- Almacenamiento en SQLite:
  - documentos
  - postings (tf)
  - df
  - enlaces
  - estadísticas globales

### 4. Buscador (API)
- Implementado con FastAPI
- Permite lanzar procesos de crawling e indexación
- Base para consultas textuales futuras

---

## Organización del backend
```
backend/src/
├── app/
│ ├── api/
│ │ ├── routes_crawl.py
│ │ ├── routes_index.py
│ │ ├── routes_preprocess.py
│ │ └──  routes_search.py
│ ├── core/
│ │ ├── crawler.py
│ │ ├── download_nltk_resources.py
│ │ ├── paths.py
│ │ └──  textproc.py
│ ├── index/
│ │ ├── bm25.py
│ │ ├── pagerank.py
│ │ ├── storage.py
│ │ └── indexer.py
│ ├── api/
│ │ └── routes_index.py
│ └── main.py
└── requirements.txt

```

---

## Crawling

El crawling se realiza mediante una cola BFS con concurrencia controlada.
Parámetros principales:

- `seed_urls`: URLs iniciales
- `max_pages`: número máximo de páginas
- `max_depth`: profundidad del crawling
- `MAX_WORKERS`: número de hilos
- `MAX_TOTAL_BYTES`: límite del corpus

Ejemplo de petición:

```json
{
  "seed_urls": [
    "https://es.wikipedia.org/wiki/Inteligencia_artificial"
  ],
  "max_pages": 20,
  "max_depth": 1
}

```
---

## Indexación

Durante la indexación:

- Se recorren recursivamente todos los subdirectorios (buckets)

- Se evita la indexación de URLs duplicadas

- Se construyen postings y frecuencias de documento

- Se almacena información estructurada en SQLite

Tablas principales:

- docs(doc_id, url, title, path, length)

- postings(term, doc_id, tf)

- df(term, doc_freq)

- links(from_doc_id, to_doc_id)

- meta(key, value)

## Base de datos

Se utiliza SQLite por su simplicidad y adecuación a entornos académicos.
El diseño permite una futura migración a motores más escalables
(PostgreSQL, ElasticSearch, etc.).

## Ejecución del proyecto

1. Crear entorno virtual

2. Instalar dependencias

3. Lanzar backend

4. Ejecutar crawling

5. Ejecutar indexación

Ejemplo para ejecutar frontend:

Ubicado en el directorio raiz del proyecto (martinez_infantes_daniel_pFinal), ejecutar
'python3 run.py' y en otra terminal ubicándonos igual y accediendo al direcotorio 'buscador-ri',
ejecutar 'npm start'.

## Corpus

- Fuente principal: Wikipedia (es.wikipedia.org)

- Tamaño: >10 GB

- Dominio temático: Informática

- Idioma: Español

## Consideraciones éticas y legales

- Se respeta estrictamente el archivo robots.txt

- Se limita la velocidad y concurrencia de peticiones

- El corpus se utiliza exclusivamente con fines académicos

- No se redistribuye contenido
