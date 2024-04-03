import socket
import struct
import hashlib

# ERROR CODES
INVALID_MESSAGE_CODE = 1
INCORRECT_MESSAGE_LENGTH = 2
INVALID_PARAMETER = 3
INVALID_SINGLE_TOKEN = 4
ASCII_DECODE_ERROR = 5

# TOKEN GENERATION

def generate_token(data):
    return hashlib.sha256(data).hexdigest()


# INDIVIDUAL TOKENS


def handle_individual_token_request(data, client_address):
    if len(data) != 16:
        send_error(client_address, INCORRECT_MESSAGE_LENGTH)
        return
    try:
        # Get student id and nonce from client data package
        student_id = data[:12].decode('ascii').strip()
        nonce = struct.unpack('!I', data[12:16])[0]
    except UnicodeDecodeError:
        send_error(client_address, ASCII_DECODE_ERROR)
        return
    except struct.error:
        send_error(client_address, INVALID_PARAMETER)
        return
    
    # Generate token
    token = generate_token((student_id + str(nonce)).encode('ascii'))
    # Response: 2     | ID            | nonce         | token            
    response = struct.pack('!H', 2) + data[:16] + token.encode('ascii')
    server_socket.sendto(response, client_address)


def handle_individual_token_validation(data, client_address):
    if len(data) != 80:
        send_error(client_address, INCORRECT_MESSAGE_LENGTH)
        return
    
    try:
        # Get student id, nonce and token from client data package
        student_id = data[:12].decode('ascii').strip()
        nonce = struct.unpack('!I', data[12:16])[0]
        token = data[16:].decode('ascii')
    except UnicodeDecodeError:
        send_error(client_address, ASCII_DECODE_ERROR)
        return
    except struct.error:
        send_error(client_address, INVALID_PARAMETER)
        return
    
    # Validate token
    if token == generate_token((student_id + str(nonce)).encode('ascii')):
        status = 0
    else:
        status = 1
    
    # Response: 4     | ID            | nonce         | token               | s 
    response = struct.pack('!H', 4) + data + struct.pack('B', status)
    server_socket.sendto(response, client_address)


# GROUP TOKENS


def handle_group_token_request(data, client_address):
    try:
        count = struct.unpack('!H', data[:2])[0]
        if count <= 0 or count * 80 + 2 != len(data):
            send_error(client_address, INVALID_PARAMETER)
            return
    except struct.error:
        send_error(client_address, INVALID_PARAMETER)
        return
    
    if len(data) != 2 + 80 * count:
        send_error(client_address, INCORRECT_MESSAGE_LENGTH)
        return
    
    print(data[2:])
    group_token = generate_token(data[2:])
    print(group_token)
    response = struct.pack('!H', 6) + struct.pack('!H', count) + data[2:] + group_token.encode('ascii')
    
    sas_list = [data[i:i+80] for i in range(2, len(data), 80)]
    for sas in sas_list:
        try:
            student_id = sas[:12].decode('ascii').strip()
            nonce = struct.unpack('!I', sas[12:16])[0]
            token = sas[16:].decode('ascii')
        except UnicodeDecodeError:
            send_error(client_address, ASCII_DECODE_ERROR)
            return
        except struct.error:
            send_error(client_address, INVALID_PARAMETER)
            return
        
        if token != generate_token((student_id + str(nonce)).encode('ascii')):
            send_error(client_address, INVALID_SINGLE_TOKEN)
            break

    # Response: 6     | N     | SAS-1    | SAS-2     | SAS-N     | token 
    server_socket.sendto(response, client_address)


def handle_group_token_validation(data, client_address):
    if len(data) < 144:
        send_error(client_address, INCORRECT_MESSAGE_LENGTH)
        return
    try:
        token = data[-64:].decode('ascii')
    except UnicodeDecodeError:
            send_error(client_address, ASCII_DECODE_ERROR)
            return
    
    # Validate token
    print(data[2:-64])
    correct_token = generate_token(data[2:-64])
    print(token)
    print(correct_token)
    status = 1
    if token == correct_token:
        status = 0
    # Response: 8     | N     | SAA-1     | SAA-2     | SAA-N     | token   | s 
    response = struct.pack('!H', 8) + data[2:] + struct.pack('B', status)
    server_socket.sendto(response, client_address)


# ERROR HANDLING
    
def send_error(client_address, error_code):
    error_msg = struct.pack('!HH', 256, error_code)
    server_socket.sendto(error_msg, client_address)

# SERVER LOGIC
def serve():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('localhost', 51001))
    
    print("Server started.")

    while True:
        data, client_address = server_socket.recvfrom(1024)
        msg_type = struct.unpack('!H', data[:2])[0]
        if msg_type == 1:
            handle_individual_token_request(data[2:], client_address)
        elif msg_type == 3:
            handle_individual_token_validation(data[2:], client_address)
        elif msg_type == 5:
            handle_group_token_request(data[2:], client_address)
        elif msg_type == 7:
            handle_group_token_validation(data[2:], client_address)
        else:
           send_error(client_address, INVALID_MESSAGE_CODE)

if __name__ == "__main__":
    serve()
