import socket
import json
import threading
import time
import sys

N_RIVERS = 4
N_BRIDGES = 8

FRIGATE = 1
DESTROYER = 2
BATTLESHIP = 3

class BridgeDefenseClient:
    # Generate client's variables
    def __init__(self, hostname, port, gas):
        self.hostname = hostname
        self.port = port
        self.river = abs(port) % 10
        self.gas = gas
        self.cannons = []
        self.quadrants = []
        self.turn = 0


    # Generalized function to facilitate sending messages
    def send_message(self, message):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(json.dumps(message).encode(), (self.hostname, self.port))
                data, _ = s.recvfrom(1024)
                response = json.loads(data.decode())
                return response
        except socket.error as e:
            print(f"Socket error: {e}")
            return None


    # Authreq
    def request_authentication(self):
        message = {
            "type": "authreq",
            "auth": self.gas
        }
        return self.send_message(message)


    # Getcannons
    def request_cannons(self):
        message = {
            "type": "getcannons",
            "auth": self.gas
        }
        return self.send_message(message)


    # Getturn
    def request_turn_state(self):
        message = {
            "type": "getturn",
            "auth": self.gas,
            "turn": self.turn
        }
        return self.send_message(message)


    # Shot
    def request_shoot(self, cannon, ship_id):
        message = {
            "type": "shot",
            "auth": self.gas,
            "cannon": cannon,
            "id": ship_id
        }
        return self.send_message(message)
    

    # Quit
    def request_quit(self):
        message = {
            "type": "quit",
            "auth": self.gas
        }
        return self.send_message(message)


# Command line interface for client   
def cli():
    # Get server and base port from command line
    server, base_port = (sys.argv[1], int(sys.argv[2]))
    
    # Generate port id's from base port
    ports = []
    for i in range(1, 5):
        ports.append(int(str(base_port)[:4] + str(i)))
    # Create empty clients
    clients = [None, None, None, None]

    while True:
        try: 
            # Get command from client command line
            command = sys.argv[3]

            # Request authentication
            if command == "authreq":
                gas = sys.argv[4]
                # Generate actual clients
                for client in clients:
                    client = BridgeDefenseClient(server, ports[i], gas)
                    # Authenticate each client
                    auth_response = client.request_authentication()
                    # Tell user if their client is authenticated
                    if auth_response.get("status") == 0:
                        print("Successful authentication!")
                    else: 
                        print("Authentication error, closing...")
                        break
            
            
            # Request cannons
            elif command == "getcannons":
                # Generate grid for printing game on terminal
                grid = [[' ' for _ in range(N_BRIDGES + 1)] for _ in range(N_RIVERS + 1)]
                # If the client has not ben authenticated it does not exist
                for client in clients:
                    if client == None:
                        print("Access denied, please authenticate first")
                        break
                    # Get cannons from server
                    client.cannons = client.request_cannons()["cannons"]
                    # Mark cannons on grid
                    for (x,y) in client.cannons:
                        grid[x][y] = 'X'
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
                    
            
            # Request turn status: ships positions
            elif command == "getturn":
                # Generate grid for printing game on terminal
                grid = [[' ' for _ in range(N_BRIDGES + 1)] for _ in range(N_RIVERS + 1)]
                # If the client has not ben authenticated it does not exist
                for client in clients:
                    if client == None:
                        print("please authenticate first")
                        break
                    # Get turn status from server
                    client.quadrants = [{"bridge": obj["bridge"], "ships": obj["ships"]} 
                                 for obj in client.request_turn_state()]
                    # Mark cannons on grid
                    for (x,y) in client.cannons:
                        grid[x][y] = 'X'
                    # Mark ships on grid
                    for quadrant in client.quadrants:
                        for ship_info in quadrant["ships"]:
                            grid[client.river][quadrant["bridge"]] = ship_info["id"]
                    # Update turn
                    client.turn = client.turn+1
                # Print the grid
                print("Turn " + client.turn)
                print('\n')
                print('  +' + '-' * (N_BRIDGES * 3 + 1))
                for y, row in enumerate(grid):
                    print(f'{y} |', end=' ')
                    for x, cell in enumerate(row):
                        print(cell if cell != ' ' else ' ', end=' | ' if x < N_BRIDGES else '')
                    print('\n  +' + '-' * (N_BRIDGES * 3 + 1))
                print('    ', end='')
                for x in range(N_BRIDGES + 1):
                    print(f'{x:2d}', end=' ')
                print('\n')
                # Print table with ship IDs, hull, hits, and shots to sink
                print("Ship ID | Hull      | Hits | Shots to Sink")
                print("-------------------------------------------")
                for client in clients:
                    for ship in client.ships:
                        for ship_info in ship["ships"]:
                            hull = ship_info['hull']
                            if hull == 'frigate':
                                shots_to_sink = FRIGATE
                            elif hull == 'destroyer':
                                shots_to_sink = DESTROYER
                            elif hull == 'battleship':
                                shots_to_sink = BATTLESHIP
                            print(f"{ship_info['id']:8} | {hull:9} | {ship_info['hits']:4} | {shots_to_sink:13}")
            
            # Request to shoot ship
            elif command == "shot":
                cannon = sys.argv[5]
                ship_id = sys.argv[6]
                # If the client has not ben authenticated it does not exist
                for (count, client) in enumerate(clients):
                    if client == None:
                        print("please authenticate first")
                        break
                    # If cannon near river that this client talks to
                    if cannon[1] == count-1 or cannon[1] == count:
                        response = client.request_shoot(cannon, ship_id)
                        if response["status"] != 0:
                            print("something went wrong with your shooting")
                        else:
                            print("yay, ship shot!")

            # Request to quit
            elif command == "quit":
                print("Quitting game...")
                # Variables to accumulate results from servers
                total_ships = 0
                total_messages = 0
                total_time = 0
                # Print table header
                print("Server ID | Ships Crossed Last Bridge | Messages Received | Time")
                print("---------------------------------------------------------------")
                # If the client has not ben authenticated it does not exist
                for client in clients:
                    if client == None:
                        print("please authenticate first")
                        break
                    response = client.request_quit()
                    # If server quit correctly
                    if response["score"] == 0:
                        # Extract information from the response
                        n_winning_ships = response["score"]["ships that crossed last bridge"]
                        n_messages = response["score"]["messages received"]
                        time = response["score"]["time"]
                        # Print score in a tabular format
                        print(f"{client.server_id:^9} | {n_winning_ships:^26} | {n_messages:^18} | {time:^4}")
                        # Update totals
                        total_ships += n_winning_ships
                        total_messages += n_messages
                        total_time += time
                    else:
                        print("Server error while quitting...")
                # Print totals
                print("---------------------------------------------------------------")
                print(f"{'Total':^9} | {total_ships:^26} | {total_messages:^18} | {total_time:^4}")
                break


            # Requests that are not implemented
            else: 
                print("command not found, quitting")
                break   

        # Exceptional error while using cli        
        except Exception as e:
            print("Exceptional error:", e)
            break


if __name__ == "__main__":
    cli()