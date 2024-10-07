import socket
import threading
import sys
import time
import hashlib
import os

FILE_KEYS_KEY = 'file_keys'
STORAGE_DIR = "chord_storage/"
os.makedirs(STORAGE_DIR, exist_ok=True)


# Operation codes
FIND_SUCCESSOR = 1
FIND_PREDECESSOR = 2
GET_SUCCESSOR = 3
GET_PREDECESSOR = 4
NOTIFY = 5
CHECK_PREDECESSOR = 6
CLOSEST_PRECEDING_FINGER = 7
STORE_KEY = 8
RETRIEVE_KEY = 9
NOTIFY_PREDECESSOR = 10
CLIENT_STORE_KEY = 11
CLIENT_RETRIEVE_KEY = 12
ELECTION = 13
LEADER = 14
REPLICATE_DATA = 15

# Function to hash a string using SHA-1 and return its integer representation
def getShaRepr(data: str):
    return int(hashlib.sha1(data.encode()).hexdigest(), 16)

# Class to reference a Chord node
class ChordNodeReference:
    def __init__(self, ip: str, port: int = 8001):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port

    # Internal method to send data to the referenced node
    def _send_data(self, op: int, data: str = None) -> bytes:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)  # 5 segundos de tiempo de espera
                s.connect((self.ip, self.port))
                s.sendall(f'{op},{data}'.encode('utf-8'))
                s.settimeout(5)  # 5 segundos de tiempo de espera
                try:
                    return s.recv(1024)
                except socket.timeout:
                    print("Tiempo de espera agotado", flush=True)
                    return b''
        except Exception as e:
            print(f"Error sending data: {e}",flush=True)
            return b''

    # Method to find the successor of a given id
    def find_successor(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(FIND_SUCCESSOR, str(id))
        if response != b'':
            response = response.decode().split(',')
            return ChordNodeReference(response[1], self.port)
        else:
            raise Exception("Error finding successor")

    # Method to find the predecessor of a given id
    def find_predecessor(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(FIND_PREDECESSOR, str(id))
        if response != b'':
            response = response.decode().split(',')
            return ChordNodeReference(response[1], self.port)
        else:
            raise Exception("Error finding predecessor")

    # Property to get the successor of the current node
    @property
    def succ(self) -> 'ChordNodeReference':
        response = self._send_data(GET_SUCCESSOR)
        if response != b'':
            response = response.decode().split(',')
            return ChordNodeReference(response[1], self.port)
        else:
            raise Exception("Error getting successor")

    # Property to get the predecessor of the current node
    @property
    def pred(self) -> 'ChordNodeReference':
        response = self._send_data(GET_PREDECESSOR)
        if response != b'':
            response = response.decode().split(',')
            return ChordNodeReference(response[1], self.port)
        else:
            raise Exception("Error getting predecessor")

    # Method to notify the current node about another node
    def notify(self, node: 'ChordNodeReference'):
        self._send_data(NOTIFY, f'{node.id},{node.ip}')

    #Method to notify the predecessor about the current node
    def notify_pred(self,node: 'ChordNodeReference'):
        self._send_data(NOTIFY_PREDECESSOR, f'{node.id},{node.ip}')
    # Method to check if the predecessor is alive
    def check_predecessor(self) -> bool:
        response = self._send_data(CHECK_PREDECESSOR)
        return response != b''

    # Method to find the closest preceding finger of a given id
    def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        response = self._send_data(CLOSEST_PRECEDING_FINGER, str(id))
        if response != b'':
            response = response.decode().split(',')
            return ChordNodeReference(response[1], self.port)
        else:
            raise Exception("Error finding closest preceding finger")

    def replicate_data(self,key,value):
        self._send_data(REPLICATE_DATA,f'{key},{value}')

    # Method to store a key-value pair in the current node
    def store_key(self, key: str, value: str):
        self._send_data(STORE_KEY, f'{key},{value}')

    # Method to retrieve a value for a given key from the current node
    def retrieve_key(self, key: str) -> str:
        response = self._send_data(RETRIEVE_KEY, key)
        if response != b'':
            response = response.decode()
            return response
        else:
            raise Exception("Error retrieving key")
    
    def send_election(self,node : 'ChordNodeReference'):
        response = self._send_data(ELECTION,f'{node.id},{node.ip}')
        return response != b''
    
    def propagate_leader(self,node):
        self._send_data(LEADER,f'{node.ip},{node.ip}')

    def __str__(self) -> str:
        return f'{self.id},{self.ip},{self.port}'

    def __repr__(self) -> str:
        return str(self)


# Class representing a Chord node
class ChordNode:
    def __init__(self, ip: str, port: int = 8001, m: int = 160):
        self.id = getShaRepr(ip)
        self.ip = ip
        self.port = port
        self.ref = ChordNodeReference(self.ip, self.port)
        self.succ = self.ref  # Initial successor is itself
        self.pred = None  # Initially no predecessor
        self.m = m  # Number of bits in the hash/key space
        self.finger = [self.ref] * self.m  # Finger table
        self.next = 0  # Finger table index to fix next
        self.data = {}  # Dictionary to store key-value pairs
        self.leader = self.ref
        self.in_election = False
        self.descarted = False

        # Start background threads for stabilization, fixing fingers, and checking predecessor
        threading.Thread(target=self.stabilize, daemon=True).start()  # Start stabilize thread
        threading.Thread(target=self.fix_fingers, daemon=True).start()  # Start fix fingers thread
        threading.Thread(target=self.check_predecessor, daemon=True).start()  # Start check predecessor thread
        threading.Thread(target=self.start_server, daemon=True).start()  # Start server thread
        threading.Thread(target=self.check_leader,daemon=True).start #Start check Leader Thread


    def start_election(self):
        if not self.in_election:
            self.in_election = True
            self.propagate_election()
            self.wait_election()

    def wait_election(self):
        time.sleep(5)
        if self.in_election and not self.descarted:
            self.leader = self.ref
            self.in_election = False
            self.propagate_leader()
    
    def propagate_election(self):
        if self.succ.check_predecessor():
            if self.succ.send_election(self.ref):
                self.descarted = True
    
    def propagate_leader(self,node:ChordNodeReference = None):
        if self.succ.check_predecessor():
            self.succ.propagate_leader(node if node else self.ref)

    # Helper method to check if a value is in the range (start, end]
    def _inbetween(self, k: int, start: int, end: int) -> bool:
        if start < end:
            return start < k <= end
        else:  # The interval wraps around 0
            return start < k or k <= end

    # Method to find the successor of a given id
    def find_succ(self, id: int) -> 'ChordNodeReference':
        node = self.find_pred(id)  # Find predecessor of id
        return node.succ  # Return successor of that node

    # Method to find the predecessor of a given id
    def find_pred(self, id: int) -> 'ChordNodeReference':
        node = self
        while not self._inbetween(id, node.id, node.succ.id):
            # print(f'find_pred {id} {node.id} {node.succ.id}',flush=True)
            node = node.closest_preceding_finger(id)
        return node

    # Method to find the closest preceding finger of a given id
    def closest_preceding_finger(self, id: int) -> 'ChordNodeReference':
        for i in range(self.m - 1, -1, -1):
            if self.finger[i] and self._inbetween(self.finger[i].id, self.id, id):
                return self.finger[i]
        return self.ref

    # Method to join a Chord network using 'node' as an entry point
    def join(self, node: 'ChordNodeReference'):
        if node:
            self.pred = None
            self.succ = node.find_successor(self.id)
            self.leader = self.succ
            self.succ.notify(self.ref)
        else:
            self.succ = self.ref
            self.pred = None

    # Stabilize method to periodically verify and update the successor and predecessor
    def stabilize(self):
        while True:
            try:
                if self.succ.id != self.id:
                    print('stabilize',flush=True)
                    if self.succ.check_predecessor():
                        x = self.succ.pred
                        if x.id != self.id:
                            print(x,flush=True)
                            if x and self._inbetween(x.id, self.id, self.succ.id):
                                self.succ = x
                            self.succ.notify(self.ref)
                            #Tenemos un nuevo sucesor, le enviamos los datos que le corresponden
                            for key, value in self.data.items():
                                key_hash = getShaRepr(key)
                                if key == FILE_KEYS_KEY:
                                    response = value
                                else:
                                    # Leer el archivo desde el sistema de archivos
                                    file_path = value['file_path']
                                    try:
                                        with open(file_path, 'rb') as f:
                                            file_content = f.read()
                                        
                                        # Preparar la respuesta con el contenido del archivo y las etiquetas
                                        response = {'content': file_content, 'tags': value['tags']}
                                    except FileNotFoundError:
                                        # Si el archivo no se encuentra, devolver un error
                                        response = "ERROR: File not found"
                                if self._inbetween(key_hash,self.id,self.succ.id):
                                    self.succ.store_key(key,response)
                                if self._inbetween(key_hash,self.pred.id,self.id):
                                    self.succ.replicate_data(key, response)
                                if self._inbetween(key_hash,self.succ.id,self.succ.succ.id):
                                    self.succ.replicate_data(key,response)
                                    del self.data[key]
                    else:
                        print("Succesor is dead")
                else:
                    #Si entra aqui es por que el succesor es el mismo, esto solo debe ocurrir en la red de un solo nodo
                    if self.pred and self.pred.check_predecessor():
                        self.succ = self.pred
                        self.succ.notify(self.ref)
            except Exception as e:
                print(f"Error in stabilize: {e}",flush=True)
            print(f'[{self.ip}] stabilize',flush=True)
            print(f"successor : {self.succ} predecessor {self.pred}",flush=True)
            print(f'{len(self.data)}',flush=True)
            time.sleep(10)
    # Notify method to inform the node about another node
    def notify(self, node: 'ChordNodeReference'):
        if node.id == self.id:
            pass
        if not self.pred or self._inbetween(node.id, self.pred.id, self.id):
            previous_pred  = self.pred
            self.pred = node
            for key, value in self.data.items():
                key_hash = getShaRepr(key)
                if key == FILE_KEYS_KEY:
                    response = value
                else:
                    # Leer el archivo desde el sistema de archivos
                    file_path = value['file_path']
                    try:
                        with open(file_path, 'rb') as f:
                            file_content = f.read()
                        
                        # Preparar la respuesta con el contenido del archivo y las etiquetas
                        response = {'content': file_content, 'tags': value['tags']}
                    except FileNotFoundError:
                        # Si el archivo no se encuentra, devolver un error
                        response = "ERROR: File not found"
                if self._inbetween(key_hash,self.pred.id,self.id):
                    self.succ.replicate_data(key,response)
                if previous_pred and self._inbetween(key_hash,previous_pred.id,self.pred.id):
                    self.succ.store_key(key, response)
                if previous_pred and self._inbetween(key_hash,previous_pred.pred.id,previous_pred.id):
                    self.succ.replicate_data(key,response)
                    del self.data[key]
    def notify_pred(self,node: 'ChordNodeReference'):
        if node.id == self.id:
            pass
        self.succ = node
    # Fix fingers method to periodically update the finger table
    def fix_fingers(self):
        while True:
            try:
                self.next += 1
                if self.next >= self.m:
                    self.next = 0
                self.finger[self.next] = self.find_succ((self.id + 2 ** self.next) % 2 ** self.m)
            except Exception as e:
                print(f"Error in fix_fingers: {e}",flush=True)
            time.sleep(10)
    # Check predecessor method to periodically verify if the predecessor is alive
    def check_predecessor(self):
        while True:
            try:
                if self.pred:
                    if not self.pred.check_predecessor():
                        print("Predecessor dead",flush=True)
                        self.pred = self.find_pred(self.pred.id)
                        if self.pred.id == self.id:
                            self.succ=self.ref
                            self.pred = None
                        else:
                            self.pred.notify_pred(self.ref)
                            # Update data in the new predecessor
                            for key, value in self.data.items():
                                key_hash = getShaRepr(key)
                                if self._inbetween(key_hash, self.pred.id, self.id):
                                    if key == FILE_KEYS_KEY:
                                        response = value
                                    else:
                                        # Leer el archivo desde el sistema de archivos
                                        file_path = value['file_path']
                                        try:
                                            with open(file_path, 'rb') as f:
                                                file_content = f.read()
                                            
                                            # Preparar la respuesta con el contenido del archivo y las etiquetas
                                            response = {'content': file_content, 'tags': value['tags']}
                                        except FileNotFoundError:
                                            # Si el archivo no se encuentra, devolver un error
                                            response = "ERROR: File not found"
                                    self.pred.replicate_data(key, response)
            except Exception as e:
                print(f"Error in check_predecessor: {e}",flush=True)
                self.pred = None if not self.succ.check_predecessor() else self.succ
                if self.pred == self.succ:
                    self.pred.notify_pred(self.ref)
            time.sleep(10)

    # Check the leader to periodically verify if the leader is alive
    def check_leader(self):
        while True:
            try:
                if self.leader != self.ref:
                    if not self.leader.check_predecessor():
                        print("Leader is dead find a new Leader")
                        self.start_election()
            except Exception as e:
                print(f'Leader check error: {e}')
            time.sleep(10)

    # Store key method to store a key-value pair and replicate to the successor
    def store_key(self, key: str, value: str):
        key_hash = getShaRepr(key)
        node = self.find_succ(key_hash)
        node.store_key(key, value)
        # self.data[key] = value  # Store in the current node
        # self.succ.store_key(key, value)  # Replicate to the successor

    # Retrieve key method to get a value for a given key
    def retrieve_key(self, key: str) -> str:
        key_hash = getShaRepr(key)
        node = self.find_succ(key_hash)
        if node.id == self.id:
            return self.data[key]
        return node.retrieve_key(key)

    # Start server method to handle incoming requests
    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.ip, self.port))
            s.listen(10)

            while True:
                conn, addr = s.accept()
                # print(f'new connection from {addr}',flush=True)

                data = conn.recv(1024).decode().split(',')

                data_resp = None
                option = int(data[0])

                if option == FIND_SUCCESSOR:
                    id = int(data[1])
                    data_resp = self.find_succ(id)
                elif option == FIND_PREDECESSOR:
                    id = int(data[1])
                    data_resp = self.find_pred(id)
                elif option == GET_SUCCESSOR:
                    data_resp = self.succ if self.succ else self.ref
                elif option == GET_PREDECESSOR:
                    data_resp = self.pred if self.pred else self.ref
                elif option == NOTIFY:
                    id = int(data[1])
                    ip = data[2]
                    self.notify(ChordNodeReference(ip, self.port))
                elif option == CHECK_PREDECESSOR:
                    data_resp = self.ref
                elif option == CLOSEST_PRECEDING_FINGER:
                    id = int(data[1])
                    data_resp = self.closest_preceding_finger(id)
                elif option == STORE_KEY or option == REPLICATE_DATA:
                    key, value = data[1], data[2]
                    if key == FILE_KEYS_KEY:
                        self.data[key] = value
                    else:
                        """Guarda los archivos en el sistema de archivos."""
                        file_path = os.path.join(STORAGE_DIR, key)
                        
                        # Guarda el contenido del archivo en la carpeta
                        with open(file_path, 'wb') as f:
                            f.write(value['content'])

                        # Guarda la referencia en self.data
                        self.data[key] = {'file_path': file_path, 'tags': value['tags']}
                    if option == STORE_KEY:
                        #Replicate Data in Succesor and Predecessor
                        self.pred.replicate_data(key,value)
                        self.succ.replicate_data(key,value)

                elif option == RETRIEVE_KEY:
                    key = data[1]
                    
                    # Verifica si la clave existe en self.data
                    file_info = self.data.get(key, None)
                    
                    if file_info:
                        # Si la clave es FILE_KEYS_KEY (que almacena una lista), devolver la lista directamente
                        if key == FILE_KEYS_KEY:
                            response = file_info
                        else:
                            # Leer el archivo desde el sistema de archivos
                            file_path = file_info['file_path']
                            try:
                                with open(file_path, 'rb') as f:
                                    file_content = f.read()
                                
                                # Preparar la respuesta con el contenido del archivo y las etiquetas
                                response = {'content': file_content, 'tags': file_info['tags']}
                            except FileNotFoundError:
                                # Si el archivo no se encuentra, devolver un error
                                response = "ERROR: File not found"
                    else:
                        # Si la clave no existe en self.data
                        response = "ERROR: Key not found"
                    
                    # Enviar la respuesta al cliente
                    conn.sendall(response.encode())

                elif option == NOTIFY_PREDECESSOR:
                    id = int(data[1])
                    ip = data[2]
                    self.notify_pred(ChordNodeReference(ip, self.port))
                elif option == CLIENT_STORE_KEY:
                    key, value = data[1], data[2]
                    self.store_key(key, value)
                    conn.sendall(b'OK')
                elif option == CLIENT_RETRIEVE_KEY:
                    key = data[1]
                    response = self.retrieve_key(key)
                    conn.sendall(response.encode())
                elif option == ELECTION:
                    id = int(data[1])
                    ip = data[2]
                    if self.id > id:
                        data_resp = self.ref
                    self.start_election()
                elif option == LEADER:
                    id = int(data[1])
                    ip = data[2]
                    self.in_election = False
                    self.leader = ChordNodeReference(ip,self.port)
                    if id !=self.id:
                        self.propagate_leader(id)
                if data_resp:
                    response = f'{data_resp.id},{data_resp.ip}'.encode()
                    conn.sendall(response)
                conn.close()

if __name__ == "__main__":
    ip = socket.gethostbyname(socket.gethostname())
    node = ChordNode(ip)

    if len(sys.argv) >= 2:
        other_ip = sys.argv[1]
        node.join(ChordNodeReference(other_ip, node.port))
    
    while True:
        pass
