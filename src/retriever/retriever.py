import pickle as pkl
from argparse import Namespace
from dataclasses import dataclass
from time import time
from typing import Dict, List

from ..indexer.indexer import Index


@dataclass
class Result:
    """Clase que contendrá un resultado de búsqueda"""

    url: str
    snippet: str

    def __str__(self) -> str:
        return f"{self.url} -> {self.snippet}"


class Retriever:
    """Clase que representa un recuperador"""

    def __init__(self, args: Namespace):
        self.args = args
        self.index = self.load_index()

    def search_query(self, query: str) -> List[Result]:
        """Método para resolver una query.
        Este método debe ser capaz, al menos, de resolver consultas como:
        "grado AND NOT master OR docencia", con un procesado de izquierda
        a derecha. Por simplicidad, podéis asumir que los operadores AND,
        NOT y OR siempre estarán en mayúsculas.

        Ejemplo para "grado AND NOT master OR docencia":

        posting["grado"] = [1,2,3] (doc ids que tienen "grado")
        NOT posting["master"] = [3, 4, 5] (doc ids que no tienen "master")
        posting["docencia"] = [6] (doc ids que tienen docencia)

        [1, 2, 3] AND [3, 4, 5] OR [6] = [3] OR [6] = [3, 6]

        Args:
            query (str): consulta a resolver
        Returns:
            List[Result]: lista de resultados que cumplen la consulta
        """
        query_terms = query.split()
        result_stack = []

        for term in query_terms:
            if term == "AND" or term == "OR" or term == "NOT":
                # Si es un operador, aplicar la operación a los elementos en la pila
                if term == "NOT":
                    operand_a = result_stack.pop()
                    result_stack.append(self._not_(operand_a))
                else:
                    operand_b = result_stack.pop()
                    operand_a = result_stack.pop()
                    if term == "AND":
                        result_stack.append(self._and_(operand_a, operand_b))
                    else:
                        result_stack.append(self._or_(operand_a, operand_b))
            else:
                # Es un término, agregar a la pila
                result_stack.append(self.index.postings.get(term, []))

        # Al final, result_stack debería contener el resultado final
        final_result = result_stack.pop()
        return final_result

    def search_from_file(self, fname: str) -> Dict[str, List[Result]]:
        """Método para hacer consultas desde fichero.
        Debe ser un fichero de texto con una consulta por línea.

        Args:
            fname (str): ruta del fichero con consultas
        Return:
            Dict[str, List[Result]]: diccionario con resultados de cada consulta
        """
        with open(fname, "r") as fr:
            ts = time()
            # Leer cada línea del fichero como una consulta y almacenar los resultados
            results_dict = {query.strip(): self.search_query(query.strip()) for query in fr}
            te = time()
            print(f"Time to solve {len(results_dict)} queries: {te-ts}")
            return results_dict

    def load_index(self) -> Index:
        """Método para cargar un índice invertido desde disco."""
        with open(self.args.index_file, "rb") as fr:
            return pkl.load(fr)

    def _and_(self, posting_a: List[int], posting_b: List[int]) -> List[int]:
        """Método para calcular la intersección de dos posting lists."""
        return list(set(posting_a) & set(posting_b))

    def _or_(self, posting_a: List[int], posting_b: List[int]) -> List[int]:
        """Método para calcular la unión de dos posting lists."""
        return list(set(posting_a) | set(posting_b))

    def _not_(self, posting_a: List[int]) -> List[int]:
        """Método para calcular el complementario de una posting list."""
        all_docs = set(range(1, len(self.index.documents) + 1))
        return list(all_docs - set(posting_a))