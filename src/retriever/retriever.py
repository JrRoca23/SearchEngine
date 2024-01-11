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
        """Método para resolver una query utilizando el algoritmo Shunting Yard.

        Args:
            query (str): consulta a resolver
        Returns:
            List[Result]: lista de resultados que cumplen la consulta
        """
        query_terms = self.shunting_yard(query)
        result_stack = []

        for term in query_terms:
            if term == "AND" or term == "OR" or term == "NOT":
                # Si es un operador, aplicar la operación a los elementos en la pila
                if term == "NOT":
                    if result_stack:
                        operand_a = result_stack.pop()
                        result_stack.append(self._not_(operand_a))
                else:
                    if len(result_stack) >= 2:
                        operand_b = result_stack.pop()
                        operand_a = result_stack.pop()
                        if term == "AND":
                            result_stack.append(self._and_(operand_a, operand_b))
                        else:
                            result_stack.append(self._or_(operand_a, operand_b))
            else:
                # Es un término, agregar a la pila
                result_stack.append(self.index.postings.get(term, []))

            # Imprimir información de depuración
            print(f"Term: {term}, Stack: {result_stack}")

        # Al final, result_stack debería contener el resultado final o estar vacía
        final_result = result_stack.pop() if result_stack else []
        print(f"Final Result: {final_result}")
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

    def _not_(self, operand_a: List[int]) -> List[int]:
        """Método para calcular el complementario de una posting list."""
        all_docs = set(range(1, len(self.index.documents) + 1))
        complement_list = list(all_docs - set(operand_a))
        
        return complement_list

    def shunting_yard(self, query: str) -> List[str]:
        """Método que implementa el algoritmo Shunting Yard para convertir
        una expresión en notación infija a notación polaca inversa (postfija).

        Args:
            query (str): consulta en notación infija
        Returns:
            List[str]: lista de términos en notación polaca inversa
        """
        output_queue = []
        operator_stack = []

        # Definir la precedencia de los operadores
        precedence = {"NOT": 3, "AND": 2, "OR": 1}

        # Tokenizar la consulta
        tokens = query.split()

        for token in tokens:
            if token.isalnum():
                # Si es un término, agregar a la salida
                output_queue.append(token)
            elif token in precedence:
                # Si es un operador, desapilar operadores de mayor precedencia y agregarlos a la salida
                while operator_stack and precedence.get(operator_stack[-1], 0) >= precedence.get(token, 0):
                    output_queue.append(operator_stack.pop())
                operator_stack.append(token)
            elif token == "(":
                # Si es un paréntesis de apertura, agregar a la pila de operadores
                operator_stack.append(token)
            elif token == ")":
                # Si es un paréntesis de cierre, desapilar operadores hasta encontrar el paréntesis de apertura
                while operator_stack and operator_stack[-1] != "(":
                    output_queue.append(operator_stack.pop())
                operator_stack.pop()  # Quitar el paréntesis de apertura

        # Desapilar operadores restantes
        while operator_stack:
            output_queue.append(operator_stack.pop())

        return output_queue
    
    