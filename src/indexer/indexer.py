from argparse import ArgumentParser
from dataclasses import dataclass, field
from typing import Dict, List
import os
import json
import string
from bs4 import BeautifulSoup
from time import time
from tqdm import tqdm
import pickle as pkl
from nltk.corpus import stopwords
from unidecode import unidecode
import pdfplumber

@dataclass
class Document:
    id: int
    title: str
    url: str
    text: str

@dataclass
class Index:
    postings: Dict[str, List[int]] = field(default_factory=lambda: {})
    documents: List[Document] = field(default_factory=lambda: [])

    def save(self, output_folder: str, output_name: str) -> None:
        output_path = os.path.join(output_folder, output_name)
        with open(output_path, "wb") as fw:
            pkl.dump(self, fw)

@dataclass
class Stats:
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
    def __init__(self, args):
        self.args = args
        self.index = Index()
        self.stats = Stats()
        self.failed_pdfs = []  # Añadir el atributo failed_pdfs

    def build_index(self) -> None:
        ts = time()

        for filename in tqdm(os.listdir(self.args.input_folder), desc="Indexing"):
            if filename.endswith(".json"):
                self.process_json(filename)
            elif filename.endswith(".pdf"):
                try:
                    self.process_pdf(filename)
                except Exception as e:
                    print(f"Error al procesar PDF {filename}: {type(e).__name__} - {str(e)}")

        te = time()

        output_folder = "etc/indexes"
        os.makedirs(output_folder, exist_ok=True)
        self.index.save(output_folder, self.args.output_name)

        self.show_stats(building_time=te - ts)

    def process_pdf(self, filename: str) -> None:
        """Método para procesar archivos PDF."""
        pdf_path = os.path.join(self.args.input_folder, filename)

        try:
            # Utilizar pdfplumber para extraer texto de PDF
            with pdfplumber.open(pdf_path) as pdf_document:
                text = ""
                for page in pdf_document.pages:
                    text += page.extract_text()

                # Utilizar PyMuPDF para extraer el título del PDF
                metadata = pdf_document.metadata
                title = metadata.get("title", "")

                # Incrementar el identificador único para cada documento
                doc_id = len(self.index.documents) + 1

                # Crear un nuevo objeto Document con los datos del archivo PDF
                document = Document(id=doc_id, title=title, url="", text=text)

                # Agregar el documento a la lista de documentos en el índice
                self.index.documents.append(document)

                # Limpiar y tokenizar el texto del documento
                cleaned_text = self.parse(document.text)
                tokens = self.tokenize(cleaned_text)

                # Actualizar las posting lists en el index
                self.update_postings(doc_id, tokens)

        except Exception as e:
            print(f"Error al procesar PDF {filename}: {type(e).__name__} - {str(e)}")
            self.failed_pdfs.append(filename)  # Agregar a la lista de archivos PDF que fallan
            pass  # Ignorar el error y continuar con el siguiente archivo

    def process_json(self, filename: str) -> None:
        """Método para procesar archivos JSON."""
        with open(os.path.join(self.args.input_folder, filename), "r", encoding="utf-8") as file:
            data_list = json.load(file)

            # Iterar sobre los datos en la lista
            for data in data_list:
                # Generar un nuevo identificador de documento
                doc_id = len(self.index.documents) + 1

                # Crear un nuevo objeto Document con los datos del archivo JSON
                document = Document(id=doc_id, title=data.get("title", ""), url=data["url"], text=data["text"])

                # Agregar el documento a la lista de documentos en el índice
                self.index.documents.append(document)

                # Limpiar y tokenizar el texto del documento
                cleaned_text = self.parse(document.text)
                tokens = self.tokenize(cleaned_text)

                # Actualizar las posting lists en el index
                self.update_postings(doc_id, tokens)
    
    def update_postings(self, doc_id: int, text: str) -> None:
        """Método para actualizar las posting lists."""
        words = self.tokenize(" ".join(text))
        words = self.remove_stopwords(words)
        words = [unidecode(word) for word in words]  # Quitar tildes
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
        return [word for word in words if unidecode(word.lower()) not in stop_words]

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
