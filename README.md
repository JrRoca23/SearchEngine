# Implemantación de un Buscador en python
Para este proyecto se ha desarrollado un buscador basado en un índice invertido,
diseñado para realizar consultas eficientes sobre un conjunto de documentos previamente indexados.

## Instalación
Para instalar y poder utilizar el programa será necesario:
1. Clonar el repositorio: https://github.com/JrRoca23/SearchEngine.git
2. Navegar desde la consola al directorio del proyecto: cd .../searcher
3. Instalar las dependencias requeridas: 'pip install requirements.txt'

## Uso del programa
Si usa el programa por primera vez, deberá hacerlo en orden:

1. Crawler: 
Puede utilizar el siguiente comando para que se ejecute con los argumentos agregados por defecto:
**python** -m src.crawler.app 

Este comando va a buscar 300 enlaces de "https://universidadeuropea.com/" y los almacenará en esta ruta "etc/webpages", 
puede modificar esto haciendo uso de los argumentos definidos en app.py

2. Indexer:
Puede utilizar el siguiente comando para que se ejecute con los argumentos agregados por defecto:
**python** -m src.indexer.app -o indexed.pkl
Este comando no tiene un nombre por defecto definido en los argumento, por lo que será necesario que especifique el nombre
con el que se guardará en índice invertido. Puede hacer uso de los argumentos para una ejecución más personalizada.

3. Retriever:
Este paso se puede ejecutar de dos maneras, se pueden hacer consultas independientes o se puede pasar un fichero con una lista de queries.
Si hace una consulta independente puede ejecutar este comando:
**python** -m src.retriever.app -i "etc/indexes/indexed.pkl" -q "Consulta AND entre AND comillas"
El programa asume que su consulta está bien planteada por lo que será necesario que lo revise antes de ejecutar. Además, la consulta debe estar dentro de comillas.

Si tiene una lista de queries pude usar este otro comando:
**python** -m src.retriever.app -i "etc/indexes/indexed.pkl" -f "Ruta/delDocumentoConUnaQueryPorLinea.txt"

De igual manera se pueden modificar los argumentos para una ejecución personalizada.
