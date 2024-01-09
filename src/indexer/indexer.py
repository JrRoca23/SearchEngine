import pickle as pkl
import os
import json
import string
from bs4 import BeautifulSoup
from argparse import Namespace
from dataclasses import dataclass, field
from time import time
from typing import Dict, List
from nltk.corpus import stopwords

@dataclass
class Document:
    """Dataclass para representar un documento.
    Cada documento contendrá:
        - id: identificador único de documento.
        - title: título del documento.
        - url: URL del documento.
        - text: texto del documento, parseado y limpio.
    """

    id: int
    title: str
    url: str
    text: str


@dataclass
class Index:
    """Dataclass para representar un índice invertido.

    - "postings": diccionario que mapea palabras a listas de índices. E.g.,
                  si la palabra w1 aparece en los documentos con índices
                  d1, d2 y d3, su posting list será [d1, d2, d3].

    - "documents": lista de `Document`.
    """

    postings: Dict[str, List[int]] = field(default_factory=lambda: {})
    documents: List[Document] = field(default_factory=lambda: [])

    def save(self, output_name: str) -> None:
        """Serializa el índice (`self`) en formato binario usando Pickle"""
        with open(output_name, "wb") as fw:
            pkl.dump(self, fw)

@dataclass
class Stats:
    """Dataclass para representar estadísticas del indexador"""

    n_words: int = field(default_factory=lambda: 0)
    n_docs: int = field(default_factory=lambda: 0)
    building_time: float = field(default_factory=lambda: 0.0)

    def __str__(self) -> str:
        return (
            f"Words: {self.n_words}\n"
            f"Docs: {self.n_docs}\n"
            f"Time: {self.building_time}"
        )


class Indexer:
    """Clase que representa un indexador"""

    def __init__(self, args: Namespace):
        self.args = args
        self.index = Index()
        self.stats = Stats()

    def build_index(self) -> None:
        """Método para construir un índice.
        El método debe iterar sobre los ficheros .json creados por el crawler.
        Para cada fichero, debe crear y añadir un nuevo `Document` a la lista
        `documents`, al que se le asigna un id entero secuencial, su título
        (se puede extraer de <title>), su URL y el texto del documento
        (contenido parseado y limpio). Al mismo tiempo, debe ir actualizando
        las posting lists. Esto es, dado un documento, tras parsearlo,
        limpiarlo y tokenizarlo, se añadirá el id del documento a la posting
        list de cada palabra en dicho documento. Al final, almacenará el objeto
        Index en disco como un fichero binario.

        [Nota] El indexador no debe distinguir entre mayúsculas y minúsculas, por
        lo que deberás convertir todo el texto a minúsculas desde el principio.
        """
        # Indexing
        ts = time()
       # Iterar sobre los ficheros .json creados por el crawler
        for filename in os.listdir(self.args.input_folder):
            if filename.endswith(".json"):
                with open(os.path.join(self.args.input_folder, filename), "r", encoding="utf-8") as file:
                    data = json.load(file)
                    # Crear y añadir un nuevo Document a la lista documents
                    doc_id = len(self.index.documents) + 1
                    title = data.get("title", "")
                    url = data.get("url", "")
                    text = self.parse(data["text"])
                    document = Document(id=doc_id, title=title, url=url, text=text)
                    self.index.documents.append(document)
                    # Actualizar las posting lists
                    self.update_postings(doc_id, text)
        te = time()

        # Save index
        self.index.save(self.args.output_name)

        # Show stats
        self.show_stats(building_time=te - ts)
    
    def update_postings(self, doc_id: int, text: str) -> None:
        """Método para actualizar las posting lists."""
        words = self.tokenize(text)
        words = self.remove_stopwords(words)
        for word in set(words):
            if word not in self.index.postings:
                self.index.postings[word] = [doc_id]
            else:
                self.index.postings[word].append(doc_id)
    
    def parse(self, text: str) -> str:
        """Método para extraer el texto de un documento.
        Puedes utilizar la librería 'beautifulsoup' para extraer solo
        el texto del bloque principal de una página web (lee el pdf de la
        actividad para más detalles)

        Args:
            text (str): texto de un documento
        Returns:
            str: texto parseado
        """
        # Utilizar BeautifulSoup para extraer solo el texto del bloque principal
        soup = BeautifulSoup(text, "html.parser")
        main_text = soup.get_text(separator=" ", strip=True)
        return main_text

    def tokenize(self, text: str) -> List[str]:
        """Método para tokenizar un texto. Esto es, convertir
        un texto a una lista de palabras. Puedes utilizar tokenizers
        existentes en NLTK, Spacy, etc. O simplemente separar por
        espacios en blanco.

        Args:
            text (str): text de un documento
        Returns:
            List[str]: lista de palabras del documento
        """
        # En este ejemplo, simplemente dividimos el texto por espacios
        return text.split()

    def remove_stopwords(self, words: List[str]) -> List[str]:
        """Método para eliminar stopwords después del tokenizado.
        Puedes usar cualquier lista de stopwords, e.g., de NLTK.

        Args:
            words (List[str]): lista de palabras de un documento
        Returns:
            List[str]: lista de palabras del documento, sin stopwords
        """
        # En este ejemplo, simplemente excluimos algunas palabras comunes en español
        stop_words = set(stopwords.words("english"))
        return [word for word in words if word.lower() not in stop_words]

    def remove_punctuation(self, text: str) -> str:
        """Método para eliminar signos de puntuación de un texto:
         < > ¿ ? , ; : . ( ) [ ] " ' ¡ !

        Args:
            text (str): texto de un documento
        Returns:
            str: texto del documento sin signos de puntuación.
        """
        translation_table = str.maketrans("", "", string.punctuation)
        return text.translate(translation_table)

    def remove_elongated_spaces(self, text: str) -> str:
        """Método para eliminar espacios duplicados.
        E.g., "La     Universidad    Europea" --> "La Universidad Europea"

        Args:
            text (str): texto de un documento
        Returns:
            str: texto sin espacios duplicados
        """
        return " ".join(text.split())

    def remove_split_symbols(self, text: str) -> str:
        """Método para eliminar símbolos separadores como
        saltos de línea, retornos de carro y tabuladores.

        Args:
            text (str): texto de un documento
        Returns:
            str: texto sin símbolos separadores
        """
        return text.replace("\n", " ").replace("\t", " ").replace("\r", " ")
    
    def show_stats(self, building_time: float) -> None:
        self.stats.building_time = building_time
        self.stats.n_words = len(self.index.postings)
        self.stats.n_docs = len(self.index.documents)
        print(self.stats)
