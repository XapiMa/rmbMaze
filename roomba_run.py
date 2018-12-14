# -*- coding: utf-8 -*-
import sys
import socket
from contextlib import closing
import hurryRmb

args = sys.argv
network_host = args[1]
network_port = int(args[2])
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

with closing(sock):
    sock.bind((network_host, network_port))
    sock.setblocking(0)
    rmb = hurryRmb.HurryAPI(sock)
