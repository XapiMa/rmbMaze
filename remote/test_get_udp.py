
import socket
import sys
from contextlib import closing


def main():
    args = sys.argv
    network_host = args[1]
    network_port = int(args[2])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bufsize = 4096
    with closing(sock):
        sock.bind((network_host, network_port))
        while True:
            key = sock.recv(bufsize).decode('utf-8')
            print(key)
            if key == 'c':    # ESC キー: 終了
                break


if __name__ == '__main__':
    main()