import requests
import os
import json
from argparse import Namespace
from queue import Queue
from typing import Set
from bs4 import BeautifulSoup

class Crawler:
    """Clase que representa un Crawler"""

    def __init__(self, args: Namespace):
        self.args = args

    def crawl(self) -> None:
        """Método para crawlear la URL base. `crawl` debe crawlear, desde
        la URL base `args.url`, usando la librería `requests` de Python,
        el número máximo de webs especificado en `args.max_webs`.
        Puedes usar una cola para esto:

        https://docs.python.org/3/library/queue.html#queue.Queue

        Para cada nueva URL que se visite, debe almacenar en el directorio
        `args.output_folder` un fichero .json con, al menos, lo siguiente:

        - "url": URL de la web
        - "text": Contenido completo (en crudo, sin parsear) de la web
        """
        # Inicializamos una cola y un conjunto para evitar duplicados
        queue = Queue()
        visited_urls = set()
        # Añadimos la URL base a la cola
        queue.put(self.args.url)
        # Creamos una lista para almacenar las URLs procesadas
        processed_urls = []

        # Limitamos el número de URLs a 200
        while not queue.empty() and len(visited_urls) < self.args.max_webs:
            # Obtenemos la siguiente URL de la cola
            current_url = queue.get()

            # Verificamos si la URL ya ha sido visitada
            if current_url in visited_urls:
                continue

            try:
                # Realizamos una solicitud HTTP a la URL actual
                response = requests.get(current_url)
                if response.status_code == 200:
                    # Obtenemos el contenido HTML de la respuesta
                    html_content = response.text

                    # Extraer URLs de la página actual
                    new_urls = self.find_urls(html_content)
                    print(f"Nuevas URLs encontradas: {new_urls}")
                    for new_url in new_urls:
                        # Verificamos que la nueva URL no haya sido visitada y que no exceda el límite
                        if new_url not in visited_urls:
                            # Agregamos la nueva URL a la cola
                            queue.put(new_url)
                            print(f"Nueva URL descubierta: {new_url}")

                    # Almacenar el contenido en un archivo JSON
                    data = {"url": current_url, "text": html_content}
                    output_folder = os.path.abspath(self.args.output_folder)
                    print(f"Output folder: {output_folder}")

                    # Utilizamos os.path.join para manejar rutas de archivo de manera compatible
                    filename = os.path.join(output_folder, f"{current_url.replace('/', '_')}.json")

                    # Agregamos la URL actual a la lista de URLs procesadas
                    processed_urls.append({"url": current_url, "text": html_content})

                    # Marcamos la URL actual como visitada
                    visited_urls.add(current_url)
                    print(f"Total URLs procesadas: {len(visited_urls)}")

            except Exception as e:
                # Manejamos errores al procesar la URL actual
                print(f"Error al procesar {current_url}: {type(e).__name__} - {str(e)}")

        # Almacenar la lista de URLs procesadas en un archivo JSON
        processed_urls_filename = os.path.join(output_folder, "processed_urls.json")
        with open(processed_urls_filename, 'w', encoding='utf-8') as file:
            json.dump(processed_urls, file, ensure_ascii=False, indent=4)

    def find_urls(self, text: str) -> Set[str]:
        """Método para encontrar URLs de la Universidad Europea en el
        texto de una web. SOLO se deben extraer URLs que aparezcan en
        como valores "href" y que sean de la Universidad, esto es,
        deben empezar por "https://universidadeuropea.com".
        `find_urls` será útil para el proceso de crawling en el método `crawl`

        Args:
            text (str): text de una web
        Returns:
            Set[str]: conjunto de urls (únicas) extraídas de la web
        """
        # Utilizamos BeautifulSoup para analizar el contenido HTML de la página
        soup = BeautifulSoup(text, 'html.parser')
        urls = set()

        # Iteramos sobre todas las etiquetas 'a' con un atributo 'href' en el contenido HTML
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Verificamos que la URL comience con "https://universidadeuropea.com/"
            if href.startswith("https://universidadeuropea.com/"):
                # Agregamos la URL al conjunto de URLs
                urls.add(href)

        return urls
