import socket
import json
import selectors
import sys

N_RIVERS = 4
N_BRIDGES = 8

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
    #print("Socket for", server_name, "setup successfully!")
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
    

def print_board(cannon_coords, ship_coords):
    board = [[' ' for _ in range(17)] for _ in range(9)]
    
    # Mark cannons on the board
    for coord in cannon_coords:
        row, col = coord
        board[row - 1][col * 2 - 1] = 'X'  # Black columns are every other column
    
    # Mark ships on the board
    for coord in ship_coords:
        row, col = coord
        board[row * 2 - 2][col] = 'O'  # Black rows are every other row
    
    # Print column names
    print('   ', end='')
    for col in range(1, 10):
        if col % 2 == 0:
            print(col, end=' ')
    print()
    
    # Print rows and board content
    for row in range(1, 10):
        if row % 2 == 1:
            print('{:2d}'.format(row), end=' ')
            for col in range(17):
                if col % 2 == 0:
                    print(board[row - 1][col], end=' ')
            print()

# Example coordinates
cannon_coords = [(3, 2), (5, 4), (7, 6)]
ship_coords = [(2, 3), (6, 8), (8, 12)]

# Print the board
print_board(cannon_coords, ship_coords)


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
        server_name = "Server " + str(i)
        servers[server_name] = {"server_address": server_address, 
                                "client_socket": get_socket(server_name)}

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
                break
        
    except Exception as e:
        print("Exceptional error while sending message:", e)
        

    while True:  
        try:
            events = selector.select()
            for key, _ in events:
                response = receive_message(servers.get(key.data)["client_socket"])
                
                if response["type"] == "state":
                    print(key.data, "Bridge:", response["bridge"])
                    print("Ships", response["ships"])

                if "status" in response:
                    if response["status"] == 0:
                        print("Success!")
                    else:
                        print("Error, try again")  
                                
                if "river" in response:
                    print(key.data, "is river", response["river"])

                if "cannons" in response:
                    print("Game cannons coordinates:" , response["cannons"])

                if "score" in response:
                    print("Server:", key.data)
                    print("Score:", response["score"])           


        # Exceptional error while using cli        
        except Exception as e:
            print("Exceptional error:", e)
            selector.close()
            sys.exit()

if __name__ == "__main__":
    cli()