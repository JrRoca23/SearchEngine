import requests
import os
import json
import pdfplumber
from argparse import Namespace
from queue import Queue
from typing import Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class Crawler:
    def __init__(self, args: Namespace):
        self.args = args
        self.visited_urls = set()

    def crawl(self) -> None:
        queue = Queue()
        visited_urls = set()
        queue.put(self.args.url)
        processed_urls = []

        while not queue.empty() and len(visited_urls) < self.args.max_webs:
            current_url = queue.get()

            if current_url in visited_urls:
                continue

            try:
                response = requests.get(current_url)
                if response.status_code == 200:
                    html_content = response.text
                    new_urls = self.find_urls(current_url, html_content)
                    #print(f"Nuevas URLs encontradas: {new_urls}")

                    for new_url in new_urls:
                        if new_url not in visited_urls:
                            queue.put(new_url)
                            #print(f"Nueva URL descubierta: {new_url}")

                    data = {"url": current_url, "text": html_content}
                    if current_url.endswith(".pdf"):
                        pdf_filename = os.path.join(self.args.output_folder, os.path.basename(current_url))
                        data["type"] = "pdf"
                        data["title"] = ""  #Extraer el título del PDF si es posible
                        self.download_pdf(current_url, pdf_filename)
                    else:
                        data["type"] = "url"
                        data["title"] = ""  #Extraer el título de la página si es posible

                    processed_urls.append(data)
                    visited_urls.add(current_url)
                    print(f"Total URLs procesadas: {len(visited_urls)}")

            except Exception as e:
                print(f"Error al procesar {current_url}: {type(e).__name__} - {str(e)}")

        processed_urls_filename = os.path.join(self.args.output_folder, "processed_urls.json")
        with open(processed_urls_filename, 'w', encoding='utf-8') as file:
            json.dump(processed_urls, file, ensure_ascii=False, indent=4)

    def find_urls(self, base_url: str, text: str) -> Set[str]:
        soup = BeautifulSoup(text, 'html.parser')
        urls = set()

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            if href.startswith("https://universidadeuropea.com/") and href not in self.visited_urls:
                urls.add(href)

                if href.endswith(".pdf"):
                    pdf_filename = os.path.join(self.args.output_folder, os.path.basename(href))
                    self.download_pdf(base_url, href, pdf_filename)

                    # Agrega la URL del PDF al conjunto de URLs visitadas
                    self.visited_urls.add(href)
                    print(f"Nueva URL de PDF descubierta: {href}")

        return urls
    
    def download_pdf(self, base_url: str, pdf_url: str, pdf_filename: str) -> None:
        try:
            # Construir correctamente la URL del PDF
            pdf_url = urljoin(base_url, pdf_url)

            response = requests.get(pdf_url, stream=True)

            # Utilizar os.path.join para obtener la ruta completa del archivo PDF
            pdf_filename = os.path.join(self.args.output_folder, os.path.basename(pdf_url))

            with open(pdf_filename, 'wb') as pdf_file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        pdf_file.write(chunk)

            # Extract text from the PDF file
            with pdfplumber.open(pdf_filename) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text()

            # Save the extracted text to a text file
            text_filename = os.path.splitext(pdf_filename)[0] + ".txt"
            with open(text_filename, 'w', encoding='utf-8') as text_file:
                text_file.write(text)

            print(f"PDF descargado y texto extraído: {text_filename}")

        except Exception as e:
            print(f"Error al descargar el PDF desde {pdf_url} o extraer texto: {type(e).__name__} - {str(e)}")

