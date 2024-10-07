from database import store_key, retrieve_key

# Constante para la clave de la lista de archivos
FILE_KEYS_KEY = 'file_keys'  # Nombre de la clave que almacenará la lista de archivos en la base de datos

def add_file(file_path, tag_list):
  """Copia un archivo al sistema y lo etiqueta."""
  with open(file_path, 'rb') as f:
    file_content = f.read()
  store_key(file_path, {'content': file_content, 'tags': tag_list})

  # Actualiza la lista de claves en la base de datos
  update_file_keys(file_path)

def delete_file(tag_query):
  """Elimina todos los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      store_key.delete(key)  # Suponiendo que store_key tiene una función delete
      remove_file_key(key)

def list_files(tag_query):
  """Lista los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      print(f"Archivo: {key}, Etiquetas: {file_data['tags']}")

def add_tags(tag_query, tag_list):
  """Agrega etiquetas a los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      file_data['tags'].extend(tag_list)
      store_key(key, file_data)

def delete_tags(tag_query, tag_list):
  """Elimina etiquetas de los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      for tag in tag_list:
        if tag in file_data['tags']:
          file_data['tags'].remove(tag)
      store_key(key, file_data)

def update_file_keys(file_path):
  """Actualiza la lista de claves en la base de datos."""
  file_keys = get_file_keys()
  file_keys.append(file_path)
  store_key(FILE_KEYS_KEY, file_keys)

def get_file_keys():
  """Obtiene la lista de claves de la base de datos."""
  return retrieve_key(FILE_KEYS_KEY) or []  # Si no existe, devuelve una lista vacía

def remove_file_key(file_path):
  """Elimina una clave de la lista de claves en la base de datos."""
  file_keys = get_file_keys()
  file_keys.remove(file_path)
  store_key(FILE_KEYS_KEY, file_keys)

# Ejemplo de uso:
add_file('my_file.txt', ['document', 'important'])
add_file('my_image.jpg', ['image', 'personal'])

delete_file(['document'])

list_files(['image'])

add_tags(['image'], ['shared'])

delete_tags(['image'], ['personal'])
