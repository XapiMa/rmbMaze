from __future__ import print_function
import socket
import time
from contextlib import closing
import getch
import sys


def main():
  args = sys.argv
  host = args[1]
  port = args[2]
  count = 0
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  with closing(sock):
    while True:
        message = getch.getch()
        print(message)
        if message == 'e':
            break
        sock.sendto(message.encode('utf-8'), (host, port))
        count += 1
    time.sleep(0.5)
  return

if __name__ == '__main__':
  main()
