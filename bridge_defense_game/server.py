import socket
import json
import hashlib
import random

class BridgeDefenseServer:
    def __init__(self, port, river):
        self.port = port
        self.river = river
        self.bridges = 8

        self.cannons = []
        self.ships = []
        n = random.randint(1, 32)
        n_ship = 1
        for _ in range(n):
            # Generate cannons
            y = random.randint(1, 8)
            x = random.randint(river-1, river)
            self.cannons.append([x, y])
            # Generate ships
            ship_types = ["frigate", "destroyer", "battleship"]
            max_hits = random.randrange(len(ship_types))
            hull = ship_types[max_hits]
            bridge = random.randint(1, 8)
            self.ships.append({
                "id": n_ship,
                "hull": hull,
                "hits": 0,
                "max_hits": max_hits,
                "bridge": bridge
                })
            n_ship = n_ship+1
            
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('localhost', self.port))
            print(f"Server on port {self.port} is listening...")
            while True:
                data, addr = s.recvfrom(1024)
                message = json.loads(data.decode())
                self.serve(s, message, addr)

    def serve(self, s, message, addr):
        message_type = message.get("type")
        if message_type == "authreq":
            self.handle_auth_request(s, message, addr)
        elif message_type == "getcannons":
            self.handle_cannons_request(s, message, addr)
        elif message_type == "getturn":
            self.handle_turn_request(s, message, addr)
        else:
            print("Unsupported message type")
    
    def send_response(self, s, addr, response):
        s.sendto(json.dumps(response).encode(), addr)

    def handle_auth_request(self, s, message, addr):
        # Verify GAS
        status = 1
        if hashlib.sha256(message["gas"][:-64]).hexdigest() == message['gas'][-64:]:
            status = 0

        auth_response = {
            "type": "authresp",
            "auth": message["auth"],
            "status": status,
            "river": self.river
        }
        self.send_response(s, addr, auth_response)

    def handle_cannons_request(self, s, message, addr):
        cannons_response = {
            "type": "cannons",
            "auth": message["auth"],
            "cannons": self.cannons
        }
        self.send_response(s, addr, cannons_response)

    def handle_turn_request(self, s, message, addr):
        turn_responses = []
        for bridge in range(1, self.bridges):   
            ships = [{"id": obj["id"], "hull": obj["hull"], "hits": obj["hits"]} 
                     for obj in self.ships if obj.get("bridge") == bridge]
            turn_responses.append({
                "type": "state",
                "auth": message["auth"],
                "turn": message["turn"],
                "bridge": bridge,
                "ships": ships
                })
        self.send_response(s, addr, turn_responses)

    # Function to handle Shot Message
    def handle_shot_message(self, s, message, addr):
        # Extract shot details
        cannon_coordinates = message["cannon"]
        ship_id = message["id"]

        # If the cannon and ship exist in this server
        # And ship is withing cannon's reach, shoot
        if cannon_coordinates in self.cannons and any(item.get("id") == ship_id for item in self.ships):
            ship = next((index for index, item in enumerate(self.ships) if item.get("id") == ship_id), None)
            if cannon_coordinates[1] in [self.ships[ship]["bridge"], self.ships[ship]["bridge"]]:
                shot_response = {
                    "type": "shotresp",
                    "auth": message["auth"],
                    "cannon": cannon_coordinates,
                    "id": ship_id,
                    "status": 0
                }
                if self.ships[ship]["hits"]+1 >= self.ships[ship]["max_hits"]:
                     self.ships.pop(ship)
                self.send_response(s, addr, shot_response)
            else:
                error_response = {
                "type": "shotresp",
                "auth": message["auth"],
                "cannon": cannon_coordinates,
                "id": ship_id,
                "status": 1,
                "description": "Invalid shot"
                }
                self.send_response(s, addr, error_response)

    # Function to handle Game Termination Request
    def handle_game_termination_request(self, s, message, addr):
        gameover_response = {
            "type": "gameover", 
            "auth": message["auth"], 
            "status": 0, 
            "score": self.score}
        self.send_response(s, addr, gameover_response)

    # Function to handle incoming messages
    def handle_message(message):
        message_type = message.get("type")
        if message_type == "shot":
            return handle_shot_message(message)
        elif message_type == "quit":
            handle_game_termination_request(message)


if __name__ == "__main__":
    global server_socket
    ports = [51111, 51112, 51113, 51114]
    rivers = [1, 2, 3, 4]
    for port, river in zip(ports, rivers):
        server = BridgeDefenseServer(port, river)
        server.start()
