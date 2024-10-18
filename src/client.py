import json
import socket

DEFAULT_BROADCAST_PORT = 8255

DISCOVER = 16
ENTRY_POINT = 17
FILE_KEYS_KEY = 'file_keys'
class ChordClient:
    def __init__(self, ip=None, port=None):
        self.ip = ip
        self.port = port
        if not ip or not port:
            self.autodiscover()

    def discover_nodes(self, timeout=5):
        nodes = []
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.bind(("", 0))  # Bind to a random port
                sock.settimeout(timeout)  # Set timeout for the broadcast

                message = f"{DISCOVER},,{0}".encode()  # Sending discovery message with no specific port (using 0)
                sock.sendto(message, ('<broadcast>', DEFAULT_BROADCAST_PORT))
                print("Sent broadcast discovery request", flush=True)

                while True:
                    try:
                        data, addr = sock.recvfrom(1024)
                        if data.decode().startswith(str(ENTRY_POINT)):
                            node_ip = data.decode().split(',')[1]
                            if node_ip not in nodes:
                                nodes.append((node_ip, addr[1]))  # Save IP and port
                                print(f"Discovered node: {node_ip}", flush=True)
                    except socket.timeout:
                        break
                    except Exception as e:
                        print(f"Error receiving broadcast response: {e}", flush=True)

        except Exception as e:
            print(f"Error during broadcast discovery: {e}", flush=True)

        return nodes

    def autodiscover(self):
        nodes = self.discover_nodes()
        if nodes:
            self.ip, self.port = nodes[0]
            print(f"Auto-discovered node: {self.ip}:{self.port}")
            self.port = 8001
        else:
            raise Exception("No available nodes found")

    def retry_request(self, func, *args, retries=3):
        """Retry a request by autodiscovering a new node if the current one fails."""
        attempts = 0
        while attempts < retries:
            try:
                return func(*args)
            except (socket.timeout, socket.error) as e:
                print(f"Error with node {self.ip}:{self.port}, retrying with another node. Error: {e}", flush=True)
                self.autodiscover()  # Attempt to discover a new node
                attempts += 1
        print("Failed to complete the request after multiple retries.")
        return None

    def store_key(self, key, value):
        def _store():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ip, self.port))
                data = f"11,{key},{value}"  # STORE_KEY operation
                s.sendall(data.encode())
                response = s.recv(1024).decode()
                if response == "OK":
                    print(f"Key '{key}' stored successfully")
                else:
                    print(f"Error storing key '{key}', response: {response}")
        
        # Use retry mechanism for store key
        self.retry_request(_store)

    def retrieve_key(self, key):
        def _retrieve():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.ip, self.port))
                data = f"12,{key}"  # RETRIEVE_KEY operation
                s.sendall(data.encode())
                response = s.recv(1024).decode()
                if response:
                    if key == FILE_KEYS_KEY:
                        print(f"Value for key '{key}': {response}")
                        return response
                    else:
                        while True:
                            d = s.recv(1024)
                            if not d:
                                break
                            response = response + d.decode()
                            if response.endswith('}'):
                                break
                        return json.loads(response.replace("'", "\"").replace("b\"", "\""))
                else:
                    print(f"Key '{key}' not found")
                    return None

        # Use retry mechanism for retrieve key
        return self.retry_request(_retrieve)

if __name__ == '__main__':
    # Example usage
    client = ChordClient("172.28.1.11", 8001)
    client.store_key("hello world", "world hello")
    client.retrieve_key("hello world")
    print("Done")
