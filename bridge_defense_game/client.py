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
    def __init__(self, hostname, port, gas):
        self.hostname = hostname
        self.port = port
        self.river = abs(port) % 10
        self.gas = gas
        self.cannons = []
        self.quadrants = []
        self.turn = 0

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

    def request_authentication(self):
        message = {
            "type": "authreq",
            "auth": self.gas
        }
        return self.send_message(message)

    def request_cannons(self):
        message = {
            "type": "getcannons",
            "auth": self.gas
        }
        return self.send_message(message)

    def request_turn_state(self):
        message = {
            "type": "getturn",
            "auth": self.gas,
            "turn": self.turn
        }
        return self.send_message(message)

    def request_shoot(self, cannon, ship_id):
        message = {
            "type": "shot",
            "auth": self.gas,
            "cannon": cannon,
            "id": ship_id
        }
        return self.send_message(message)
    
    def request_quit(self):
        message = {
            "type": "quit",
            "auth": self.gas
        }
        return self.send_message(message)
    
def cli():
    server, base_port = (sys.argv[1], int(sys.argv[2]))
    
    ports = []
    for i in range(1, 5):
        ports.append(int(str(base_port)[:4] + str(i)))
    
    clients = [None, None, None, None]

    while True:
        try: 
            command = sys.argv[3]

            if command == "authreq":
                gas = sys.argv[4]
                for client in clients:
                    client = BridgeDefenseClient(server, ports[i], gas)
                    auth_response = client.request_authentication()
                    if auth_response.get("status") == 0:
                        print("Successful authentication!")
                    else: 
                        print("Authentication error, closing...")
                        break
            
            elif command == "getcannons":
                grid = [[' ' for _ in range(N_BRIDGES + 1)] for _ in range(N_RIVERS + 1)]
                for client in clients:
                    if client == None:
                        print("Access denied, please authenticate first")
                        break
                    
                    client.cannons = client.request_cannons()["cannons"]
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
                    
            
            elif command == "getturn":
                grid = [[' ' for _ in range(N_BRIDGES + 1)] for _ in range(N_RIVERS + 1)]
                for client in clients:
                    if client == None:
                        print("please authenticate first")
                        break
                    client.turn = client.turn+1
                    client.quadrants = [{"bridge": obj["bridge"], "ships": obj["ships"]} 
                                 for obj in client.request_turn_state()]
                    for (x,y) in client.cannons:
                        grid[x][y] = 'X'
                    for quadrant in client.quadrants:
                        for ship_info in quadrant["ships"]:
                            grid[client.river][quadrant["bridge"]] = ship_info["id"]
                
                # Print the grid
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
            
            elif command == "shot":
                cannon = sys.argv[5]
                ship_id = sys.argv[6]
                for client in clients:
                    if client == None:
                        print("please authenticate first")
                        break

                    response = client.request_shoot(cannon, ship_id)
                    if response["status"] != 0:
                        print("something went wrong with your shooting")
                    else:
                        print("yay, ship shot!")

            elif command == "quit":
                for client in clients:
                    if client == None:
                        print("please authenticate first")
                        break
                    client.request_quit()
                    print("Quitting game...")
                break
            
            else: 
                print("command not found, quitting")
                break   
                
        except Exception as e:
            print("Exceptional error:", e)
            break


if __name__ == "__main__":
    cli()