import socket
import json
import selectors
import sys
import time

N_RIVERS = 4
N_BRIDGES = 8

TIMEOUT = 20
TIMEOUT_THRESHOLD = 50

AUX_FILE = "game_board.txt"

selector = selectors.DefaultSelector()


# GET CLIENT SOCKET CONNECTED TO MULTIPLEXER

def get_socket(server_name):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        # If IPv4 is not supported, attempt to create a socket with IPv6
        client_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    client_socket.setblocking(False) 
    selector.register(client_socket, selectors.EVENT_READ, data=server_name)
    client_socket.settimeout(TIMEOUT)
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


# PRINT ROUNDS TO FILE TO MAKE THE GAME EASIER TO VISUALIZE

def print_river_to_file(server_name, river_number, file_name=AUX_FILE):
   with open(file_name, 'a') as f: f.write(f"Server {server_name} = river {river_number}\n")

def print_cannons_to_file(cannon_coords, file_name=AUX_FILE):
    board = [[' ' for _ in range(2*N_RIVERS+1)] for _ in range(2*N_BRIDGES+1)]
    
    # Mark cannons on the board
    for coord in cannon_coords:
        col, row = coord
        # Bridges are every other column
        board[row - 1][col * 2 - 1] = 'X'
    
    # Open the file for writing
    with open(file_name, 'a') as f:
        # Print column names
        f.write('  ')
        col_name = 1
        for col in range(0, 2*N_BRIDGES+1):
            if col % 2 != 0:
                f.write(' | ' + str(col_name) + ' | ')
                col_name += 1
        f.write('\n')
        
        # Print rows and board content
        row_name = 1
        for row in range(0, 2*N_RIVERS+1):
            f.write('-------------------------------------------------------------------------------------------')
            if row % 2 != 0:
                f.write('{:2d}'.format(row_name))
                for col in range(2*N_BRIDGES+1): print(' | ')
                row_name += 1
            else: 
                f.write(' ')
                for col in range(2*N_BRIDGES+1):
                    if col % 2 != 0: f.write(' | ' + board[row][col] + ' | ')
                    else: print(' | ')
            f.write('\n')

def remove_ships_from_file(file_name=AUX_FILE):
    # Read existing board from file
    with open(file_name, 'r') as f:
        lines = f.readlines()
    board = [list(line.strip()) for line in lines]

    # Delete previous ships
    for row in range(len(board)):
        for col in range(len(board[row])):
            if board[row][col] == 'O':
                board[row][col] = ' '

def print_ships_to_file(ship_coords, file_name=AUX_FILE):
    # Read existing board from file
    with open(file_name, 'r') as f:
        lines = f.readlines()

    board = [list(line.strip()) for line in lines]

    # Mark ships on the board
    for coord in ship_coords:
        row, col = coord
        # Rivers are every other row
        board[row * 2 - 2][col] = 'O' 

    # Write the updated board to file
    with open(file_name, 'w') as f:
        for line in board:
            f.write(''.join(line) + '\n')

def print_ships_info_to_file(ships, file_name=AUX_FILE):
    with open(file_name, 'r+') as f:
        lines = f.readlines()

        # Check if the table exists
        table_exists = False
        for line in lines:
            if 'ID' in line and 'BRIDGE' in line and 'RIVER' in line and 'HITS' in line and 'HULL' in line:
                table_exists = True
                break

        # If table does not exist, append it to the file
        if not table_exists:
            f.write("\nID   RIVER  BRIDGE   HITS    HULL\n")
        else:
            # Write rows to the existing table
            for ship in ships:
                f.seek(0, 2)  # Move the cursor to the end of the file
                f.write(f"{ship['id']} {ship['river']} {ship['bridge']} {ship['hits']} {ship['hull']}\n")


def print_score_to_file(server_name, score, file_name=AUX_FILE):
   with open(file_name, 'a') as f:
        f.write(f"Server {server_name}: score {score}\n")


# COMMAND LINE INTERFACE
  
def cli():
    # Get server and base port from command line
    server, base_port = (sys.argv[1], sys.argv[2])

    # Generate dicts for games and servers, server_name is key for both dicts
    # I chose to separate them to use the multiplexer more easily with the server sockets
    servers = {}
    for i in range(1, N_RIVERS+1):
        port = base_port[:-1] + str(i)
        server_address = (server, int(port))
        servers[str(i)] = {"server_address": server_address, 
                           "client_socket": get_socket(str(i)),
                           "response": []}
    
    last_request_time = time.time() 
    all_answered, right_n_answers = 0, 0
    total_responses = N_RIVERS
    while True: 
        try:
            request_type = sys.argv[3]
            gas = sys.argv[4]
                    
            turn, cannon_coord, ship_id = None, None, None
            if len(sys.argv) == 7:
                cannon_coord = sys.argv[5]
                ship_id = sys.argv[6]
            elif len(sys.argv) == 6:
                turn = sys.argv[5]
            else:
                pass

            if request_type not in ["authreq", "quit", "getturn", "shot", "getcannons"]:
                print("invalid message!")

            for _, server_infos in servers.items():
                send_message(client_socket=server_infos["client_socket"],
                            server_address=server_infos["server_address"],
                            request_type=request_type, gas=gas, 
                            turn=turn, cannon_coord=cannon_coord, ship_id=ship_id)
                if request_type == "getcannons":
                    total_responses = 1
                    break
            
            if request_type == "getturn":
                remove_ships_from_file()
                total_responses = N_RIVERS*N_BRIDGES
 
            events = selector.select()
            
            while all_answered < N_RIVERS and right_n_answers < total_responses: 
                for key, _ in events:
                    response = receive_message(servers.get(key.data)["client_socket"])

                    if not servers[key.data]["response"]: 
                        servers[key.data]["response"] = [response]
                        all_answered += 1
                        right_n_answers += 1
                    
                    elif request_type == "getturn" and len(servers[key.data]["response"]) < N_BRIDGES:
                        servers[key.data]["response"].append(response)
                        right_n_answers += 1
        
            break
                        
        except socket.timeout:
            if time.time() - last_request_time > TIMEOUT_THRESHOLD:
                print("Timeout occurred. Closing...")
                break
            else:
               print("No answer. Resending requests.")      
        except Exception as e:
            print("Exceptional error:", e)
            selector.close()
            sys.exit()
        
    for server_name, server_info in servers.items():
        for response in server_info["response"]:
            if "type" in response:
                if response["type"] == "authresp":
                    if response["status"] == 0:
                        print("Successful authentication for server", server_name)
                        if "river" in response:
                            print_river_to_file(server_name, response["river"])
                            print("Server-river relationship printed on", AUX_FILE)
                    else:
                        print("Error while authenticating on server", server_name)

                elif response["type"] == "cannons":
                    print_cannons_to_file(response["cannons"])
                    print("Cannons printed on", AUX_FILE)

                elif response["type"] == "state":
                    if response["ships"]:
                        ships_coord = [server_name, response["bridge"]]
                        print_ships_to_file(ships_coord)
                        for ship in response["ships"]:
                            ship["bridge"] = response["bridge"]
                            ship["river"] = server_name
                        print_ships_info_to_file(response["ships"])

                elif response["type"] == "shotresp":
                    if response["status"] == 0:
                        print("Successful shot", server_name, 
                                "ship", response["id"], 
                                "shot by cannon", response["cannon"])
                    else:
                        print("Shot missed the target", response["description"])

                elif response["type"] == "gameover":
                    print("Gameover! Score printed on", AUX_FILE)
                    print_score_to_file(server_name, response["score"])
                    
                else:
                    print("ERROR: can't recognize response type", response["type"])
            else:
                print("ERROR: Response has no type", response)

if __name__ == "__main__":
    cli()