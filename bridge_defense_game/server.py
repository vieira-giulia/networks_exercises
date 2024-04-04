import socket
import json
import hashlib
import random
import sys

N_BRIDGES = 8

################ GAME ####################
class Game:  
    def start(self, river):
        self.river = river
        self.cannons = []
        self.ships = []
        n = random.randint(1, 32)
        for i in range(n):
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
                "id": i,
                "hull": hull,
                "hits": 0,
                "max_hits": max_hits,
                "bridge": bridge
                })
    
            self.score = 0
    
    def update(self):
        # Move ships for the future
        for ship in self.ships:
            if ship["bridge"]+1 < N_BRIDGES:
                ship["bridge"] = ship["bridge"]+1
            else:
                self.score = self.score+1
    
    def shoot_ship(self, ship_id, cannon_coord):
        status = 1
        if cannon_coord in self.cannons and any(item.get("id") == ship_id for item in self.ships):
            if cannon_coord[1] in [self.ships[ship_id]["bridge"], self.ships[ship_id]["bridge"]]:
                status = 0
                if self.ships[ship_id]["hits"]+1 >= self.ships[ship_id]["max_hits"]:
                    self.ships.pop(ship_id)
                else:
                    self.ships[ship_id]["hits"] = self.ships[ship_id]["hits"]+1
        self.update()
        return status


########### MESSAGE HANDLING ########################

def send_message(message, client_address):
    server_socket.sendto(json.dumps(message).encode(), client_address)

# AUTHENTICATION REQUEST

def verify_gas(gas):
    correct_token = hashlib.sha256(gas[-64].encode()).hexdigest()
    if  correct_token == gas[-64:]: 
        return 0
    else: 
        return 1

def handle_auth_request(request, game, client_address):
    status = verify_gas(request["auth"])
    message = {
        "type": "authresp",
         "auth": request["auth"],
        "status": status,
        "river": game.river
    }
    send_message(message, client_address)


# DISPLAY CANNONS NEAR THIS RIVER REQUEST

def handle_cannons_request(request, game, client_address):
    message = {
        "type": "cannons",
        "auth": request["auth"],
        "cannons": game.cannons
    }
    send_message(message, client_address)


# DISPLAY SHIPS IN THIS RIVER REQUEST

def handle_turn_request(request, game, client_address):
    # Get ships positions based on bridges
    for bridge in range(1, N_BRIDGES):   
        ships = [{"id": obj["id"], "hull": obj["hull"], "hits": obj["hits"]} 
                 for obj in game.ships if obj.get("bridge") == bridge]
        # Generate and send message request
        message = {
            "type": "state",
            "auth": request["auth"],
            "turn": request["turn"],
            "bridge": bridge,
            "ships": ships
            }
    
        send_message(message, client_address)
    game.update()


# SHOT REQUEST

def handle_shot_request(request, game, client_address):
    status = game.shoot_ship(request["id"], request["cannon"])
    message = {"type": "shotresp", 
               "auth": request["auth"], 
               "cannon": request["cannon"], 
               "id": request["id"], 
               "status": status
            }
    send_message(message, client_address)

    
# QUITTING REQUEST

def handle_game_termination_request(request, game, client_address):
    message = {
        "type": "gameover", 
        "auth": request["auth"], 
        "status": 0, 
        "score": {game.score}
        }
    send_message(message, client_address)

    
########### SERVER ###############

def serve():
    # TODO TIMER FOR GAMEOVER
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #server_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    port = sys.argv[1]
    server_socket.bind(('localhost', int(port)))
        
    print(f"Server on port {port} is listening...")
        
    game = Game()
    game.start(int(port[-1]))
       
    while True:
        request, client_address = server_socket.recvfrom(1024)
        request_json = json.loads(request.decode())
        request_type = request_json.get("type")
        if request_type == "authreq":
            handle_auth_request(request_json, game, client_address)
        elif request_type == "getcannons":
            handle_cannons_request(request_json, game, client_address)
        elif request_type == "getturn":
            handle_turn_request(request_json, game, client_address)
        elif request_type == "shot":
            handle_shot_request(request_json, game, client_address)
        elif request_type == "quit":
            handle_game_termination_request(request_json, game, client_address)
            break
        else:
            print("Unsupported request type")
            break
        

if __name__ == "__main__":
    serve()
