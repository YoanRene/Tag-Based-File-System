from client import ChordClient
import base64

# Constante para la clave de la lista de archivos
FILE_KEYS_KEY = 'file_keys'  # Nombre de la clave que almacenará la lista de archivos en la base de datos

def add_file(file_path, tag_list):
  """Copia un archivo al sistema y lo etiqueta."""
  with open(file_path, 'rb') as f:
    file_content = f.read()
  client.store_key(file_path, {'content': base64.b64encode(file_content), 'tags': tag_list})

  # Actualiza la lista de claves en la base de datos
  update_file_keys(file_path)

def delete_file(tag_query):
  """Elimina todos los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = client.retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      client.store_key(key,None)  # Suponiendo que store_key tiene una función delete
      remove_file_key(key)

def list_files(tag_query):
  """Lista los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = client.retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      print(f"Archivo: {key}, Etiquetas: {file_data['tags']}")

def add_tags(tag_query, tag_list):
  """Agrega etiquetas a los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = client.retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      print(file_data)
      file_data['tags'].extend(tag_list)
      client.store_key(key, file_data)

def delete_tags(tag_query, tag_list):
  """Elimina etiquetas de los archivos que coincidan con la consulta."""
  for key in get_file_keys():
    file_data = client.retrieve_key(key)
    if set(tag_query).issubset(set(file_data['tags'])):
      for tag in tag_list:
        if tag in file_data['tags']:
          file_data['tags'].remove(tag)
      client.store_key(key, file_data)

def update_file_keys(file_path):
  """Actualiza la lista de claves en la base de datos."""
  file_keys = get_file_keys()
  file_keys.append(file_path)
  print(file_keys)
  client.store_key(FILE_KEYS_KEY, file_keys)

def get_file_keys():
  """Obtiene la lista de claves de la base de datos."""
  keys_str = client.retrieve_key(FILE_KEYS_KEY)
  print(keys_str)
  if keys_str:
    return eval(keys_str)
  return []  # Si no existe, devuelve una lista vacía

def remove_file_key(file_path):
  """Elimina una clave de la lista de claves en la base de datos."""
  file_keys = get_file_keys()
  file_keys.remove(file_path)
  client.store_key(FILE_KEYS_KEY, file_keys)

def handle_command(command):
  """Maneja los comandos del usuario."""
  parts = command.split()
  if parts[0] == 'add':
    file_paths = parts[1].split(';')
    tag_list = parts[2].split(';')
    for file_path in file_paths:
      add_file(file_path, tag_list)
  elif parts[0] == 'delete':
    tag_query = parts[1].split(';')
    delete_file(tag_query)
  elif parts[0] == 'list':
    tag_query = parts[1].split(';')
    list_files(tag_query)
  elif parts[0] == 'add-tags':
    tag_query = parts[1].split(';')
    tag_list = parts[2].split(';')
    add_tags(tag_query, tag_list)
  elif parts[0] == 'delete-tags':
    tag_query = parts[1].split(';')
    tag_list = parts[2].split(';')
    delete_tags(tag_query, tag_list)
  else:
    print('Comando inválido.')

client = ChordClient()

while True:
  command = input('Ingresa un comando: ')
  handle_command(command)