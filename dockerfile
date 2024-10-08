# Usa una imagen base de Python
FROM python:3.11-slim

# Crea un directorio de trabajo en el contenedor
WORKDIR /app/src

# Copia el archivo de dependencias
COPY requirements.txt .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de Chord a la imagen
COPY src/chord_node.py .

# Exponer el puerto que utilizará el nodo Chord
EXPOSE 8001
EXPOSE 8002

# Define la variable de entorno para el puerto (puedes cambiarlo según tu implementación)
# Define el comando para ejecutar tu nodo Chord
