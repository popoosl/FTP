import socket
import pickle
import threading
import time
import sys

# Get input
# host, port, send_file, N, MSS = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
# host, port, send_file, N, MSS = socket.gethostname(), 7735, 'test.db', 64, 500
host, port, send_file, N, MSS = "10.139.61.135", 7735, 'in01.pdf', 2, 500

# Create socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Only for test in local machine (same host), cannot use 7735 (server side has taken it)
ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# ack_socket.bind((host, 62223))
ack_socket.bind(("", port))

packets = []  # all the packets
new_buffer = []  # after receiving ACK, put new packets into new_buffer and send

lock = threading.Lock()
ack = 0


# Checksum
def calc_checksum(data):
    return 0


# Send packets
def socket_send(data):
    global most_recent_send
    global lock

    lock.acquire()

    while data:
        p = data.pop(0)
        client_socket.sendto(pickle.dumps(p), (host, port))
        print("Send packet: ", int('0b' + p[0], 2))
        # update
        most_recent_send = max(most_recent_send, int('0b' + p[0], 2))

    lock.release()


# Listen ACK thread
def listen_ack(s, h):
    global new_buffer
    global ack
    global most_recent_send
    global most_recent_prepared
    global cur_time

    # Listen to ACK
    while True:
        ack_packet, addr = s.recvfrom(1024)
        ack_packet = pickle.loads(ack_packet)
        ack = int('0b' + ack_packet[0], 2)  # get ack number(next expected packet)

        print("Receive ACK: ", ack)

        if len(packets) > ack:
            # the next packet of "most recent send packet" or "most recent planed to send packet"
            # is the smallest packet we should send
            # "ack+N-1" is the largest packet number we should send
            cur_time = time.time()
            for j in range(max(most_recent_send+1, most_recent_prepared+1), min(len(packets), ack+N)):
                # In this thread, only send new packet (slide the window to next)
                most_recent_prepared = max(most_recent_prepared, j)
                new_buffer.append(packets[j])
                print("prepare: ", j)
        elif ack == len(packets):
            print("Success!!!", "Time: ", time.time()-start_time)
            break


# Send thread
def send_packet(h, p):
    global new_buffer

    while True:
        # send packet from new_buffer
        while new_buffer:
            socket_send(new_buffer)


def timer():
    global cur_time
    resend_buffer = []
    while True:
        if time.time() >= cur_time + 0.1:
            # Prepare resend packets
            for k in range(ack, min(len(packets), ack+N)):
                resend_buffer.append(packets[k])
            print("Timeout, sequence number = ", ack)
            socket_send(resend_buffer)
            cur_time = time.time()
        if ack == len(packets):
            print("Success!!!", "Time: ", time.time()-start_time)
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
    new_buffer.append(packets[i])

cur_time = time.time()
start_time = time.time()

most_recent_send = 0
most_recent_prepared = min(N-1, len(packets)-1)

threading.Thread(target=send_packet, args=(host, port)).start()
threading.Thread(target=listen_ack, args=(ack_socket, host)).start()
threading.Thread(target=timer).start()
