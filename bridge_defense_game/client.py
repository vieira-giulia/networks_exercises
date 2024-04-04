import socket
import json
import selectors
import sys

N_RIVERS = 4
N_BRIDGES = 8

selector = selectors.DefaultSelector()


# GAME VARIABLES

class Game:
    river = 0
    cannons = []


# GET CLIENT SOCKET CONNECTED TO MULTIPLEXER

def get_socket(server_name):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        # If IPv4 is not supported, attempt to create a socket with IPv6
        client_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    client_socket.setblocking(False) 
    selector.register(client_socket, selectors.EVENT_READ, data=server_name)
    print("Socket for", server_name, "setup successfully!")
    return client_socket


# SEND MESSAGE

def send_message(client_socket, server_address, 
                request_type, gas, turn, cannon_coord, ship_id):
    message = {
        "type": request_type,
        "auth": gas
    }
    if turn is not None: message["turn"] = turn
    if cannon_coord is not None: message["cannon"] = cannon_coord
    if ship_id is not None: message["id"] = ship_id
    client_socket.sendto(json.dumps(message).encode(), server_address)


# RECEIVE MESSAGE

def receive_message(client_socket):
    return json.loads(client_socket.recv(1024).decode())
    


# COMMAND LINE INTERFACE
  
def cli():
    # Get server and base port from command line
    server, base_port = (sys.argv[1], sys.argv[2])

    # Generate dicts for games and servers, server_name is key for both dicts
    # I chose to separate them to use the multiplexer more easily with the server sockets
    servers = {}
    games = {}
    for i in range(1, N_RIVERS+1):
        port = base_port[:-1] + str(i)
        server_address = (server, int(port))
        server_name = "Server " + str(i)
        servers[server_name] = {"server_address": server_address, 
                                "client_socket": get_socket(server_name)}
        games[server_name] = Game()

    while True:
        try: 
            request_type = sys.argv[3]
            gas = sys.argv[4]
            
            # Other variables that can be necessary for a request
            # The user either asks for turn_status or to shoot a ship
            # In the first case there is only one more argument, 
            # In the second one the user must specify two arguments
            # cannon_coord and ship_id
            turn, cannon_coord, ship_id = None, None, None
            if len(sys.argv) == 7:
                cannon_coord = sys.argv[5]
                ship_id = sys.argv[6]
            elif len(sys.argv) == 6:
                turn = sys.argv[5]
            else:
                pass

            if request_type in ["authreq", "quit", "getturn"]:
                for _, server_infos in servers.items():
                    send_message(client_socket=server_infos["client_socket"],
                                server_address=server_infos["server_address"],
                                request_type=request_type, gas=gas, 
                                turn=turn, cannon_coord=cannon_coord, ship_id=ship_id)
            
            elif request_type == "getcannons":
                server_infos = servers.get("Server 1")
                send_message(client_socket=server_infos["client_socket"],
                            server_address=server_infos["server_address"],
                            request_type=request_type, gas=gas, 
                            turn=turn, cannon_coord=cannon_coord, ship_id=ship_id)
            
            elif request_type == "shot":
                for server_name, game_info in games.items():
                    if game_info.river == cannon_coord[1]:
                        server_infos = servers.get(server_name)
                        send_message(client_socket=server_infos["client_socket"],
                            server_address=server_infos["server_address"],
                            request_type=request_type, gas=gas, 
                            turn=turn, cannon_coord=cannon_coord, ship_id=ship_id)
                    if game_info.river == cannon_coord[1]+1:
                        server_infos = servers.get(server_name)
                        send_message(client_socket=server_infos["client_socket"],
                            server_address=server_infos["server_address"],
                            request_type=request_type, gas=gas, 
                            turn=turn, cannon_coord=cannon_coord, ship_id=ship_id)

            else:
                print("invalid request")
                break

            # Get responses for requests.
            # Response format is also a generalized json, so I made
            # one function that takes care of that and evaluate information
            # given afterwards
            events = selector.select()
            responses = []
            for key, _ in events:
                # Only case where response is actually a list of messages
                if request_type == "getturn":
                    while len(responses) < N_BRIDGES:
                        responses.append(receive_message(servers.get(key.data)["client_socket"]))
                else:
                    response = receive_message(servers.get(key.data)["client_socket"])
                    print(response)
                    
                if response:
                    if "status" in response:
                        if response["status"] == 0:
                            print("Success!")
                        else:
                            print("Error, try again")  
                                
                    if "river" in response:
                        games[key.data].river = response["river"]
                        print("Server {} is river {}", key.data, response["river"])

                    if "cannons" in response:
                        for coord in response["cannons"]:
                            if [coord[0], coord[1]] not in games[key.data].cannons:
                                games[key.data].cannons.append([coord[0], coord[1]])

                    if "score" in response:
                        print("Server:", key.data)
                        print("Score:", response["score"])

                    else:
                        for response in responses:
                            ships_list = []
                            if "bridge" in response and "ships" in response:
                                ships_list[response["bridge"]] = response["ships"]
                                # This is part of the ships information adjacent table
                                # whose header was printted in the beginning
                                for (bridge, ship_info) in enumerate(ships_list):
                                    print("ID:", ship_info['id'])
                                    print("Bridge:", bridge)
                                    print("River:", games[key.data].river)
                                    print("HITS:", ship_info['hits'] )
                                    print("HULL", ship_info["hull"]) 
            break
                        
        # Exceptional error while using cli        
        except Exception as e:
            print("Exceptional error:", e)
            selector.close()
            sys.exit()

if __name__ == "__main__":
    cli()