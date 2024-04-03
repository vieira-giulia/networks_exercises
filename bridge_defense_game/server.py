import socket
import json
import hashlib
import random

N_BRIDGES = 8

class BridgeDefenseServer:
    # Generate server's variables
    def __init__(self, port, river):
        # Server's port
        self.port = port
        # Server's river 
        self.river = river
        # Server's cannons
        self.cannons = []
        # Server's ships
        self.ships = []
        n = random.randint(1, 32)
        n_ship = 1
        for _ in range(n):
            # Generate cannons:
            # at a bridge
            y = random.randint(1, N_BRIDGES)
            # up or down from server's river
            x = random.randint(river-1, river)
            self.cannons.append([x, y])
            # Generate ships at server's river
            # from a specific type and max hits
            ship_types = ["frigate", "destroyer", "battleship"]
            max_hits = random.randrange(len(ship_types))
            hull = ship_types[max_hits]
            # near a bridge
            bridge = random.randint(1, N_BRIDGES)
            self.ships.append({
                "id": n_ship,
                "hull": hull,
                "hits": 0,
                "max_hits": max_hits,
                "bridge": bridge
                })
            n_ship = n_ship+1
            # Number of messages received
            self.n_messages = 0
            # Number of ships that remained alive and crossed last bridge
            self.n_winning_ships = 0

    
    # Start server at port
    def serve(self):
        # Open server at port
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('localhost', self.port))
            print(f"Server on port {self.port} is listening...")
            # Deal with requests
            while True:
                data, addr = s.recvfrom(1024)
                message = json.loads(data.decode())
                message_type = message.get("type")
                if message_type == "authreq":
                    self.n_messages = self.n_messages+1
                    self.handle_auth_request(s, message, addr)
                elif message_type == "getcannons":
                    self.n_messages = self.n_messages+1
                    self.handle_cannons_request(s, message, addr)
                elif message_type == "getturn":
                    self.n_messages = self.n_messages+1
                    self.handle_turn_request(s, message, addr)
                elif message_type == "shot":
                    self.n_messages = self.n_messages+1
                    self.handle_shot_request(message)
                elif message_type == "quit":
                    self.n_messages = self.n_messages+1
                    self.handle_game_termination_request(message)
                    break
                else:
                    print("Unsupported message type")
    

    # Generalized function to facilitate sending responses
    def send_response(self, s, addr, response):
        s.sendto(json.dumps(response).encode(), addr)

    
    # Check GAS validity for authentication
    def handle_auth_request(self, s, message, addr):
        # Verify GAS
        status = 1
        if hashlib.sha256(message["gas"][:-64]).hexdigest() == message['gas'][-64:]:
            status = 0
        # Generate and send response message
        response = {
            "type": "authresp",
            "auth": message["auth"],
            "status": status,
            "river": self.river
        }
        self.send_response(s, addr, response)


    # Send cannons display to client
    def handle_cannons_request(self, s, message, addr):
        # Generate and send response message
        response = {
            "type": "cannons",
            "auth": message["auth"],
            "cannons": self.cannons
        }
        self.send_response(s, addr, response)


    # Send ships display to client per bridge
    def handle_turn_request(self, s, message, addr):
        # Get ships positions based on bridges
        responses = []
        for bridge in range(1, self.bridges):   
            ships = [{"id": obj["id"], "hull": obj["hull"], "hits": obj["hits"]} 
                     for obj in self.ships if obj.get("bridge") == bridge]
            # Generate and send response message
            responses.append({
                "type": "state",
                "auth": message["auth"],
                "turn": message["turn"],
                "bridge": bridge,
                "ships": ships
                })
        self.send_response(s, addr, responses)
        # Move ships for the future
        for ship in self.ships:
            if ship["bridge"]+1 < N_BRIDGES:
                ship["bridge"] = ship["bridge"]+1
            else:
                self.n_winning_ships = self.n_winning_ships+1 

    # Function to handle Shot Message
    def handle_shot_request(self, s, message, addr):
        # Extract shot details
        cannon_coordinates = message["cannon"]
        ship_id = message["id"]
        # If the cannon and ship exist in this server
        if cannon_coordinates in self.cannons and any(item.get("id") == ship_id for item in self.ships):
            ship = next((index for index, item in enumerate(self.ships) if item.get("id") == ship_id), None)
            # If ship is withing cannon's reach, shoot
            if cannon_coordinates[1] in [self.ships[ship]["bridge"], self.ships[ship]["bridge"]]:
                # Generate and send response message
                shot_response = {
                    "type": "shotresp",
                    "auth": message["auth"],
                    "cannon": cannon_coordinates,
                    "id": ship_id,
                    "status": 0
                }
                self.send_response(s, addr, shot_response)
                # Kill ship if enough shots to kill it
                if self.ships[ship]["hits"]+1 >= self.ships[ship]["max_hits"]:
                     self.ships.pop(ship)
            else:
                # Generate and send error response message 
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
        # Generate and send response message
        gameover_response = {
            "type": "gameover", 
            "auth": message["auth"], 
            "status": 0, 
            "score": {"ships that crossed last bridge": self.n_winning_ships,
                      "messages received": self.n_messages,
                      "time": 0
                      }}
        self.send_response(s, addr, gameover_response)
        

if __name__ == "__main__":
    global server_socket
    ports = [51111, 51112, 51113, 51114]
    rivers = [1, 2, 3, 4]
    # TODO TIMER FOR GAMEOVER
    for port, river in zip(ports, rivers):
        server = BridgeDefenseServer(port, river)
        server.serve()
