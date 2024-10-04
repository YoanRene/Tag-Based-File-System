import socket

class ChordClient:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

    def store_key(self, key, value):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip, self.port))
            data = f"11,{key},{value}"  # STORE_KEY operation
            s.sendall(data.encode())
            response = s.recv(1024).decode()
            if response == "OK":
                print(f"Key '{key}' stored successfully")
            else:
                print(f'Response {response}')
                print(f"Error storing key '{key}'")

    def retrieve_key(self, key):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.ip, self.port))
            data = f"12,{key}"  # RETRIEVE_KEY operation
            s.sendall(data.encode())
            response = s.recv(1024).decode()
            if response:
                print(f"Value for key '{key}': {response}")
            else:
                print(f"Key '{key}' not found")

# Example usage
client = ChordClient("172.28.1.11", 8001)
client.store_key("hello world", "world hello")
client.retrieve_key("hello world")
print("Done")