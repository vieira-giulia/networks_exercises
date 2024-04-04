import socket
import json
import selectors
import sys

N_RIVERS = 4
N_BRIDGES = 8

FRIGATE = 1
DESTROYER = 2
BATTLESHIP = 3

#selector = selectors.DefaultSelector()


# GAME VARIABLES

class Game:
    river, turn = 0, 0
    cannons = []


# GET CLIENT SOCKET CONNECTED TO MULTIPLEXER

def get_socket(server_name):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        # If IPv4 is not supported, attempt to create a socket with IPv6
        client_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    client_socket.setblocking(False) 
    #selector.register(client_socket, selectors.EVENT_READ, data=server_name)
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

            # Generate grid for printing game on terminal
            # This is just so I understand what is happening better
            grid = [[' ' for _ in range(N_BRIDGES + 1)] for _ in range(N_RIVERS + 1)]
            
            # Accumulator for score display at the end
            # Also just for my understanding
            total_score = 0

            # If user asks to quit, print results for each server
            # Also just for my understanding
            if request_type == "quit":
                # Print table header
                print("River | Score")
                print("---------------------")
            
            # If user asks for turn_status, print adjacent table with
            # ship_ids and their status
            # Also just for my understanding
            elif request_type == "getturn":
                # Print table with current ships and their individual info
                print("Ship ID | Hull      | Hits | Shots to Sink")
                print("-------------------------------------------")
            
            # Send message to all servers.
            # Messages have similar formats so I made only one send_message 
            # function that fills the json with necessary information for
            # every type of request
            for _, server_infos in servers.items():
                send_message(client_socket=server_infos["client_socket"],
                            server_address=server_infos["server_address"],
                            request_type=request_type, gas=gas, 
                            turn=turn, cannon_coord=cannon_coord, ship_id=ship_id)

                # Get responses for requests.
                # Response format is also a generalized json, so I made
                # one function that takes care of that and evaluate information
                # given afterwards
                #events = selector.select()
                responses = []
                #for key, _ in events:
                # Only case where response is actually a list of messages
                if request_type == "getturn":
                    while len(responses) < N_BRIDGES:
                        responses.append(receive_message(servers.get(key.data)["client_socket"]))
                else:
                    response = receive_message(servers.get(key.data)["client_socket"])
                    print(response)
                
                # Request receives only one response
                if response:
                    # Status come for authentication and shooting
                    # In both cases 0 means it worked and anything different
                    # means it didn't
                    # In this project's specification there was no need to 
                    # stop communication in case either of them receive status != 0
                    # so I decided to just warn the user and let him/her try again
                    if "status" in response:
                        if response["status"] == 0:
                            print("Go forward")
                        else:
                            print("Error, try again")  
                            
                    # Get info received
                    if "river" in response:
                        games[key.data].river = response["river"]
                        if response.get("turn"):
                            games[key.data].turn = response["turn"]
                            print("Turn " + response["turn"])  
                            if response.get("cannons"):
                                for coord in response["cannons"]:
                                    games[key.data].cannons.append([coord[0], coord[1]])
                                    # Mark printing grid
                                    grid[coord[0]][coord[1]] = 'X'
                            if response.get("score"):
                                score = response["score"]
                                total_score += score
                                # Print score in a tabular format
                                print(f"{games[key.data].server_id:^9} | {score:^26}")

                    # Request receives many response messages  
                    else:
                        for response in responses:
                            # I used an aux variable ships_list to help me print ships locations
                            # and information on terminal. I didn't put it in Game object because
                            # ships are supposed to move every round, so there is no need to 
                            # save old rounds positions or infos
                            ships_list = []
                            if response.get("bridge") and response.get("ships"):
                                ships_list[response["bridge"]] = response["ships"]
                                
                                # This is part of the ships information adjacent table
                                # whose header was printted in the beginning
                                for (bridge, ship_info) in enumerate(ships_list):
                                    # Mark printing grid
                                    grid[games[key.data].river][bridge] = ship_info["id"]
                                # Mark ship info table
                                hull = ship_info["hull"]
                                if hull == 'frigate':
                                    shots_to_sink = FRIGATE
                                elif hull == 'destroyer':
                                    shots_to_sink = DESTROYER
                                elif hull == 'battleship':
                                    shots_to_sink = BATTLESHIP
                                print(f"{ship_info['id']:8} | {hull:9} | {ship_info['hits']:4} | {shots_to_sink:13}")      

                    # For requests about the state of the game I decided to print the game's quadrants
                    # in terminal so I can visualize cannons and ships positions
                    # Cannons are marked with X, as seen before, and ships are marked with their id's
                    if request_type in ["shot", "getturn", "getcannons"]:           
                        # Print grid
                        print('  +' + '-' * (N_BRIDGES * 3 + 1))
                        for y, row in enumerate(grid):
                            print(f'{y} |', end=' ')
                            for x, cell in enumerate(row):
                                print(cell if cell == 'X' else ' ', end=' | ' if x < N_BRIDGES else '')
                            print('\n  +' + '-' * (N_BRIDGES * 3 + 1))
                        print('    ', end='')
                        for x in range(N_BRIDGES + 1):
                            print(f'{x:2d}', end=' ')
                        print('\n')

                    # For quitting requests or if server decides for gameover, 
                    # I use total_score accumulator described before also to help visualize results
                    elif request_type == "quit":
                        # Print totals
                        print("--------------------------------")
                        print(f"{'Total':^9} | {total_score:^26}")
                        #selector.close()
                        #sys.exit()
                        break
                        
        # Exceptional error while using cli        
        except Exception as e:
            print("Exceptional error:", e)
            #selector.close()
            #sys.exit()
            break

if __name__ == "__main__":
    cli()