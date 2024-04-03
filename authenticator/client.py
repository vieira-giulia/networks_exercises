import socket
import struct
import sys
import time


TIMEOUT = 20
TIMEOUT_THRESHOLD = 50


#Error code
ERROR = 256
INVALID_MESSAGE_CODE = 1
INCORRECT_MESSAGE_LENGTH = 2
INVALID_PARAMETER = 3
INVALID_SINGLE_TOKEN = 4
ASCII_DECODE_ERROR = 5


# INDIVIDUAL TOKENS

def request_individual_token(server_address, student_id, nonce):
    message = struct.pack('!H', 1) + student_id.ljust(12).encode('ascii') + struct.pack('!I', nonce)
    client_socket.sendto(message, server_address)

def validate_individual_token(server_address, sas):
    message = struct.pack('!H', 3) + sas
    client_socket.sendto(message, server_address)


# GROUP TOKENS
    
def request_group_token(server_address, sas_list):
    message = struct.pack('!HH', 5, len(sas_list)) + b''.join(sas_list)
    client_socket.sendto(message, server_address)

def validate_group_token(server_address, gas_list):
    message = struct.pack('!HH', 7, len(gas_list)-1) + b''.join(gas_list)
    client_socket.sendto(message, server_address)


# PARSERS

def sas_to_bin(data):
    student_id, nonce, token = data.split(':')
    student_id_bytes = student_id.encode('ascii').ljust(12)
    nonce_bytes = struct.pack('!I', int(nonce))
    token_bytes = token.encode('ascii')
    return (student_id_bytes + nonce_bytes + token_bytes)

def bin_to_sas(data):
    student_id = data[:12].decode('ascii').strip()
    nonce = str(struct.unpack('!I', data[12:16])[0])
    token = data[16:].decode('ascii')
    return f"{student_id}:{nonce}:{token}"

def bin_to_gas(data):
    n = struct.unpack('!H', data[:2])[0]
    sas_list = [bin_to_sas(data[2+i*80 : 2+(i+1)*80]) for i in range(n)]
    token = data[-64:].decode('ascii')
    return sas_list, token

def gas_to_bin(data):
    gas = data.split('+')
    sas_list_bytes = [sas_to_bin(gas[i]) for i in range(len(gas)-1)]
    token_bytes = gas[-1].encode('ascii')
    return sas_list_bytes, token_bytes


# ERROR HANDLING 

def handle_error(error_code):
    if error_code == INVALID_MESSAGE_CODE:
        print("Error: Invalid message code")
    elif error_code == INCORRECT_MESSAGE_LENGTH:
        print("Error: Incorrect message length")
    elif error_code == INVALID_PARAMETER:
        print("Error: Invalid parameter")
    elif error_code == INVALID_SINGLE_TOKEN:
        print("Error: Invalid single token")
    elif error_code == ASCII_DECODE_ERROR:
        print("Error: ASCII decode error")
    else:
        print("Unknown error")

# COMMAND LINE INTERFACE

        
def cli():
    global client_socket
    # Create a UDP socket that supports both IPv4 and IPv6
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except OSError:
        # If IPv4 is not supported, attempt to create a socket with IPv6
        client_socket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    server_address = (sys.argv[1], int(sys.argv[2]))
    
    #client_socket.settimeout(TIMEOUT)

    #last_request_time = time.time()

    while True:
        try:
            command = sys.argv[3]
            
            if command == 'itr':
                if len(sys.argv) != 6:
                    print("Usage: ./client.py <host> <port> itr <id> <nonce>")
                    return
                student_id = sys.argv[4]
                nonce = int(sys.argv[5])
                request_individual_token(server_address, student_id, nonce)
                binary_data, _ = client_socket.recvfrom(1024)
                # Decode message type, see if there is an error
                message_type = int.from_bytes(binary_data[:2], byteorder='big')
                if message_type ==  ERROR:
                    handle_error(struct.unpack('!H', binary_data[2:4])[0])
                else:
                    print(bin_to_sas(binary_data[2:]))
                break

            elif command == 'itv':
                if len(sys.argv) != 5:
                    print("Usage: ./client.py <host> <port> itv <SAS>")
                    return
                bin_sas = sas_to_bin(sys.argv[4])
                validate_individual_token(server_address, bin_sas)
                binary_data, _ = client_socket.recvfrom(1024)
                # Decode message type, see if there is an error
                message_type = int.from_bytes(binary_data[:2], byteorder='big')
                if message_type ==  ERROR:
                    handle_error(struct.unpack('!H', binary_data[2:4])[0])
                else:
                    # Status 0 = pass, 1 = not pass
                    status = struct.unpack('B', binary_data[-1:])[0]
                    print(status)
                break
    
            elif command == 'gtr':
                if len(sys.argv) < 6:
                    print("Usage: ./client.py <host> <port> gtr <N> <SAS1> <SAS2> ... <SASN>")
                    return
                n = int(sys.argv[4])
                if len(sys.argv) != n + 5:
                    print("Incorrect number of SAS provided")
                    return
                bin_sas_list = [sas_to_bin(sys.argv[i]) for i in range(5, 5 + n)]
                request_group_token(server_address, bin_sas_list)
                binary_data, _ = client_socket.recvfrom(1024)
                # Decode message type, see if there is an error
                message_type = int.from_bytes(binary_data[:2], byteorder='big')
                if message_type ==  ERROR:
                    handle_error(struct.unpack('!H', binary_data[2:4])[0])
                else:
                    gas, token = bin_to_gas(binary_data[2:])
                    print('+'.join(gas) + "+" + token)
                break
    
            elif command == 'gtv':
                if len(sys.argv) != 6:
                    print("Usage: ./client.py <host> <port> gtv <SAS1>+<SAS2>+...+<SASN>+<GAS>")
                    return
                n = int(sys.argv[4])
                gas = sys.argv[5]
                bin_sas_list, bin_token = gas_to_bin(gas)
                bin_sas_list.append(bin_token)
                validate_group_token(server_address, bin_sas_list)
                binary_data, _ = client_socket.recvfrom(1024)
                # Decode message type, see if there is an error
                message_type = int.from_bytes(binary_data[:2], byteorder='big')
                if message_type ==  ERROR:
                    handle_error(struct.unpack('!H', binary_data[2:4])[0])
                else:
                    # Status 0 = pass, 1 = not pass
                    status = struct.unpack('B', binary_data[-1:])[0]
                    print(status)
                break
    
            else:
                handle_error(1)
                break

        #except socket.timeout:
        #    if time.time() - last_request_time > TIMEOUT_THRESHOLD:
        #        print("Timeout occurred. Resending request...")
        #        last_request_time = time.time()
        #    else:
        #       print("Timeout occurred, but not enough time has passed since the last request.")
        except Exception as e:
            print("Exceptional error:", e)
            break

    #client_socket.close()

if __name__ == "__main__":
    cli()
