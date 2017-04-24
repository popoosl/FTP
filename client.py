import socket
import pickle
import threading
import time
import sys

# Get input
# host, port, send_file, N, MSS = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
host, port, send_file, N, MSS = 'Leon-PC', 7735, 'in02.pdf', 10, 10000

# Create socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Only for test in local machine (same host), cannot use 7735 (server side has taken it)
ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket.bind((host, 62223))

packets = []  # all the packets
sent_buffer = []  # the packets have been sent
new_buffer = []  # after receiving ACK, put new packets into new_buffer and send

ack = 0


# Checksum
def calc_checksum(data):
    return 0


# Listen ACK thread
def listen_ack(s, h, p):
    global new_buffer
    global sent_buffer
    global ack

    # Listen to ACK
    while True:
        ack_packet, addr = s.recvfrom(256)
        ack_packet = pickle.loads(ack_packet)
        ack = int('0b' + ack_packet[0], 2)  # get ack number(next expected packet)

        print("Receive ACK: ", ack)

        # print(sent_buffer)
        # print(new_buffer)

        # Do not consider a "previous" ack
        if len(packets) > ack > int('0b' + sent_buffer[0][0], 2):
            # the next packet of sent_buffer[-1](latest packet sent) is the smallest packet we should send
            # "ack+N-1" is the largest packet number we should send
            for j in range(int('0b' + sent_buffer[-1][0], 2)+1, min(len(packets), ack+N)):
                # In this thread, only send new packet (slide the window to next)
                if packets[j] not in sent_buffer:
                    new_buffer.append(packets[j])
                    print("prepare: ", j)
        elif ack == len(packets):
            print("Success!!!")
            break


# Send packets
def send_packet(h, p):
    global new_buffer
    global sent_buffer
    global cur_time

    while True:
        # send packet from new_buffer
        while new_buffer:
            packet = new_buffer.pop(0)
            # update right side of sent_buffer (sliding window)
            sent_buffer.append(packet)
            client_socket.sendto(pickle.dumps(packet), (host, port))
            print("Send packet: ", int('0b' + packet[0], 2))
            # update left side of sent_buffer (sliding window)
            if len(sent_buffer) > N:
                sent_buffer.pop(0)

            cur_time = time.time()

            # t = threading.Timer(10, timer).start()


def timer():
    global cur_time
    while True:
        if time.time() >= cur_time + 1:
            # Prepare resend packets
            for k in range(ack, min(len(packets), ack+N)):
                client_socket.sendto(pickle.dumps(packets[k]), (host, port))
                print("ReSend packet: ", int('0b' + packets[k][0], 2))
            cur_time = time.time()
        if ack == len(packets):
            print("Success!!!")
            break


# Read file and make packets
seq = 0
with open(send_file, 'rb') as f:
    while True:
        split_file = f.read(MSS)  # Split file by MSS
        if split_file:
            # Calculate checksum
            checksum = calc_checksum(split_file)
            # Make packets
            packets.append([bin(seq)[2:].zfill(32), checksum, '0101010101010101', split_file])
            seq += 1
        else:
            break

# Build packets to be sent at window size in the very beginning, then listen to ACK and send packets
# (Hence this part only execute once)
for i in range(min(N, len(packets))):
    # client_socket.sendto(pickle.dumps(packets[i]), (host, port))
    new_buffer.append(packets[i])

cur_time = time.time()


threading.Thread(target=send_packet, args=(host, port)).start()
threading.Thread(target=listen_ack, args=(ack_socket, host, 62223)).start()
threading.Thread(target=timer).start()
