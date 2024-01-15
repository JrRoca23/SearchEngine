import pickle as pkl
from argparse import Namespace
from dataclasses import dataclass
from time import time
from typing import Dict, List
from bs4 import BeautifulSoup

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
        """Método para resolver una query utilizando el algoritmo Shunting Yard."""
        print(f"Query: {query}")  # Agregar mensaje de depuración
        query_terms = self.shunting_yard(query)
        result_stack = []  # Agrega esta línea para inicializar la pila
        final_results = self._evaluate_query(query_terms)
    
        # Devolver los resultados de la evaluación de la consulta
        return final_results
    
    def shunting_yard(self, query: str) -> List[str]:
        """Implementación del algoritmo Shunting Yard para convertir la consulta a notación posfija."""
        precedence = {"NOT": 3, "AND": 2, "OR": 1}
        output = []
        operator_stack = []

        for token in query.split():
            if token.isalnum():
                output.append(token)
            elif token in {"AND", "OR", "NOT"}:
                while (
                    operator_stack
                    and operator_stack[-1] != "("
                    and precedence.get(operator_stack[-1], 0) >= precedence.get(token, 0)
                ):
                    output.append(operator_stack.pop())
                operator_stack.append(token)
            elif token == "(":
                operator_stack.append(token)
            elif token == ")":
                while operator_stack and operator_stack[-1] != "(":
                    output.append(operator_stack.pop())
                if operator_stack and operator_stack[-1] == "(":
                    operator_stack.pop()  # Pop el paréntesis de apertura

        while operator_stack:
            output.append(operator_stack.pop())

        return output


    def search_from_file(self, fname: str) -> Dict[str, List[Result]]:
        """Método para hacer consultas desde fichero."""
        with open(fname, "r") as fr:
            ts = time()
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
        result = list(set(posting_a) & set(posting_b))
        print(f"\nAND: {posting_a} AND {posting_b} = {result}")
        return result

    def _or_(self, posting_a: List[int], posting_b: List[int]) -> List[int]:
        """Método para calcular la unión de dos posting lists."""
        result = list(set(posting_a) | set(posting_b))
        print(f"\nOR: {posting_a} OR {posting_b} = {result}")
        return result

    def _not_(self, operand_a: List[int]) -> List[int]:
        """Calcula el complementario de una posting list."""
        result = list(set(range(1, len(self.index.documents) + 1)) - set(operand_a))
        print(f"\nNOT: ~{operand_a} = {result}")
        return result

    def _evaluate_query(self, query_terms):
        result_stack = []  # Pila para almacenar resultados intermedios
        operator_stack = []  # Pila para almacenar operadores
        inside_parenthesis = 0  # Variable para rastrear la profundidad de los paréntesis

        for term in query_terms:
            # Si el término es un término de búsqueda (un token en los documentos)
            if term in self.index.postings:
                posting_list = self.index.postings[term]
                print(f"\nposting['{term}'] = {posting_list} (doc ids que tienen '{term}')")
                result_stack.append(posting_list)  # Agrega la lista de documentos que contienen el término a la pila de resultados
            # Si el término es "NOT"
            elif term == "NOT":
                operator_stack.append("NOT")  # Agrega "NOT" a la pila de operadores
            # Si el término es "AND" o "OR"
            elif term in {"AND", "OR"}:
                while (
                    operator_stack
                    and operator_stack[-1] in {"AND", "OR"}
                    and inside_parenthesis == 0
                ):
                    operator = operator_stack.pop()  # Obtiene el último operador de la pila de operadores
                    if operator == "NOT":
                        operand_a = result_stack.pop()  # Obtiene el operando de la pila de resultados
                        result = self._not_(operand_a)
                    else:
                        operand_b = result_stack.pop()  # Obtiene el segundo operando de la pila de resultados
                        operand_a = result_stack.pop()  # Obtiene el primer operando de la pila de resultados
                        if operator == "AND":
                            result = self._and_(operand_a, operand_b)
                        elif operator == "OR":
                            result = self._or_(operand_a, operand_b)
                    result_stack.append(result)  # Agrega el resultado de la operación a la pila de resultados
                operator_stack.append(term)  # Agrega "AND" o "OR" a la pila de operadores
            # Si el término es "("
            elif term == "(":
                inside_parenthesis += 1
            # Si el término es ")"
            elif term == ")":
                inside_parenthesis -= 1
                while operator_stack and operator_stack[-1] != "(":
                    operator = operator_stack.pop()  # Obtiene el último operador de la pila de operadores
                    if operator == "NOT":
                        operand_a = result_stack.pop()  # Obtiene el operando de la pila de resultados
                        result = self._not_(operand_a)
                    elif operator in {"AND", "OR"}:
                        operand_b = result_stack.pop()  # Obtiene el segundo operando de la pila de resultados
                        operand_a = result_stack.pop()  # Obtiene el primer operando de la pila de resultados
                        if operator == "AND":
                            result = self._and_(operand_a, operand_b)
                        elif operator == "OR":
                            result = self._or_(operand_a, operand_b)
                    result_stack.append(result)  # Agrega el resultado de la operación a la pila de resultados
                operator_stack.pop()  # Elimina el "(" de la pila de operadores
            # Si el término es un espacio en blanco, ignóralo
            elif term == " ":
                continue

        # Procesa los operadores y operandos restantes en la pila
        while operator_stack:
            operator = operator_stack.pop()  # Obtiene el último operador de la pila de operadores

            # Si el operador es "NOT", realiza la operación correspondiente
            if operator == "NOT":
                if not result_stack:
                    print("ERROR: Operador 'NOT' sin suficientes operandos.")
                    return []
                operand_a = result_stack.pop()  # Obtiene el operando de la pila de resultados
                result = self._not_(operand_a)
                result_stack.append(result)  # Agrega el resultado de la operación a la pila de resultados

            # Si el operador es "AND" o "OR", agrega el operador a la pila de resultados
            elif operator in {"AND", "OR"}:
                if operator == "OR" and len(result_stack) < 2:
                    print(f"ERROR: Operador 'OR' sin suficientes operandos.")
                    return []
                elif operator == "AND" and len(result_stack) < 2:
                    print(f"ERROR: Operador 'AND' sin suficientes operandos.")
                    return []

                operand_b = result_stack.pop()  # Obtiene el segundo operando de la pila de resultados
                operand_a = result_stack.pop()  # Obtiene el primer operando de la pila de resultados
                if operator == "AND":
                    result = self._and_(operand_a, operand_b)
                elif operator == "OR":
                    result = self._or_(operand_a, operand_b)
                result_stack.append(result)  # Agrega el resultado de la operación a la pila de resultados

        # Procesa la pila de resultados para obtener el resultado final
        if result_stack and isinstance(result_stack[0], list):
            final_result_ids = result_stack[0]
            print(f"\nFinal Result IDs: {final_result_ids}\n")

            # Recupera la URL y el snippet de cada documento
            results = [self._get_result_info(doc_id) for doc_id in final_result_ids]
            # Imprime la URL y el snippet de cada documento final
            for doc_id in final_result_ids:
                result = self._get_result_info(doc_id)
                print(f"ID: {[doc_id]} \nURL: {result.url}\nSnippet: {result.snippet}\n")
            return results
        else:
            print("ERROR: Operadores sin operandos suficientes.")
            return []


    def _get_result_info(self, doc_id: int) -> Result:
        """Obtiene la información real de un documento."""
        document = self.index.documents[doc_id - 1]  # Restar 1 para obtener el índice correcto
        url = document.url
        snippet = self._generate_snippet(document.text)  # Usar el atributo 'text' en lugar de 'content'
        return Result(url=url, snippet=snippet)

    def _generate_snippet(self, content: str) -> str:
        """Genera un snippet a partir del contenido del documento."""
        soup = BeautifulSoup(content, 'html.parser')
        paragraphs = soup.find_all(['h1','h2', 'h3', 'h4', 'h5', 'h6'])

        if paragraphs:
            # Tomar el texto de los primeros tres párrafos
            snippet_text = ' '.join([p.get_text() for p in paragraphs[:3]])
            # Limitar la longitud del snippet a 150 caracteres
            return snippet_text[:150]
        else:
            # Si no hay párrafos, simplemente tomar los primeros 150 caracteres
            return content[:150]
