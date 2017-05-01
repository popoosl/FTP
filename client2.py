import socket
import pickle
import threading
import time
import sys

# Get input
# host, port, send_file, N, MSS = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
host, port, send_file, N, MSS = socket.gethostname(), 7735, 'test.db', 4, 1000

# Create socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Only for test in local machine (same host), cannot use 7735 (server side has taken it)
ack_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ack_socket.bind((host, 62223))

packets = []  # all the packets
new_buffer = []  # after receiving ACK, put new packets into new_buffer and send
sending_buffer = {}  # stores packets sent but not acked
time_buffer = {}  # stores send time of packets

lock = threading.Lock()
ack = 0


# Checksum
def calc_checksum(data):
    return 0


def del_buffer(k):
    global time_buffer
    global sending_buffer

    lock.acquire()
    del time_buffer[k]
    del sending_buffer[k]
    lock.release()


def timer():
    global time_buffer

    resend_buffer = []

    while True:
        print(time_buffer)
        if time_buffer:
            resend_seq = min(time_buffer)
            if time.time() >= time_buffer[resend_seq] + 0.1:
                del_buffer(resend_seq)

                # Prepare resend packets
                resend_buffer.append(packets[resend_seq])
                print("Timeout, sequence number = ", resend_seq)
                socket_send(resend_buffer)


# Send packets
def socket_send(data):
    global most_recent_send
    global lock
    global sending_buffer
    global time_buffer

    lock.acquire()

    while data:
        p = data.pop(0)
        sending_buffer[int('0b' + p[0], 2)] = p
        time_buffer[int('0b' + p[0], 2)] = time.time()
        client_socket.sendto(pickle.dumps(p), (host, port))
        print("Send packet: ", int('0b' + p[0], 2))
        print(sending_buffer, time_buffer)
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
    max_ack = 0

    # Listen to ACK
    while True:
        ack_packet, addr = s.recvfrom(1024)
        ack_packet = pickle.loads(ack_packet)
        ack = int('0b' + ack_packet[0], 2)  # get ack number
        max_ack = max(ack, max_ack)

        print("Receive ACK: ", ack)

        if ack in time_buffer and ack in sending_buffer:
            del_buffer(ack)
        print(time_buffer)

        if not sending_buffer:
            max_to_send = min(most_recent_prepared+N, len(packets)-1)
        else:
            max_to_send = min(min(sending_buffer)+N, len(packets)-1)

        if len(packets)-1 > ack:
            for j in range(most_recent_prepared+1, max_to_send):
                # In this thread, only send new packet (slide the window to next)
                most_recent_prepared = max(most_recent_prepared, j)
                new_buffer.append(packets[j])
                print("prepare: ", j)
        elif ack == len(packets)-1:
            print("Success!!!", "Time: ", time.time()-start_time)
            break


# Send thread
def send_packet(h, p):
    global new_buffer

    while True:
        # send packet from new_buffer
        while new_buffer:
            socket_send(new_buffer)


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
