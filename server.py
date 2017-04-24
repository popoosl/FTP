import socket
import pickle
import threading
import sys

# packet = [seq(32bit), checksum(16bit), packet_type(16bit), data]

# Next expected packet number
next_seq = 0

# get input
# server_port, out_file, p = int(sys.argv[1]), sys.argv[2], float(sys.argv[3])
server_port, out_file, p = 7735, 'out03.pdf', 0.1

# set server
host = socket.gethostname()
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((host, server_port))
ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print("The server:", host, " is ready to receive")

acks = []


def calc_checksum():
    return 0


def send_ack(h, p):
    while True:
        while acks:
            ack_socket.sendto(pickle.dumps(acks.pop(0)), (h, p))


def listen(s, h, p):
    global next_seq
    global acks

    while True:
        recvd_data, addr = server_socket.recvfrom(1000000)
        # unserialize reveived List
        packet = pickle.loads(recvd_data)
        seq, checksum, packet_type, data = packet[0], packet[1], packet[2], packet[3]
        print("Receive: ", int('0b'+seq, 2))

        re_checksum = calc_checksum()

        if int('0b'+seq, 2) == next_seq:  # and re_checksum == checksum:
            next_seq += 1

            # prepare ACK
            acks.append([bin(next_seq)[2:].zfill(32), bin(0)[2:].zfill(16), '1010101010101010'])

            # write file
            with open(out_file, 'ab') as f:
                f.write(data)

        else:
            continue

threading.Thread(target=listen, args=(server_socket, host, server_port)).start()
threading.Thread(target=send_ack, args=(host, 62223)).start()
