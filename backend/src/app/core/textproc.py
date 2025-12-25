import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Inicializamos stopwords para español
STOPWORDS = set(stopwords.words("spanish"))

def normalize_text(text: str) -> str:
    """
    Normaliza un texto:
    - minusculas
    - elimina URLs
    - elimina puntuación y caracteres raros
    - limpia espacios
    """
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-záéíóúüñ0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize_text(text: str):
    """
    Tokeniza el texto usando nltk word_tokenize
    """
    tokens = word_tokenize(text, language="spanish")
    return tokens

def remove_stopwords(tokens: list):
    """
    Elimina stopwords de una lista de tokens
    """
    return [t for t in tokens if t not in STOPWORDS and len(t) > 2]