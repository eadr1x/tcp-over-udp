from TCPoverUDP import TCPClient, UPDHolePuncher, stun, addr2int, int2adddr
import socket
import time
import random
import threading

server = TCPServer(5555)
print(server.get_code())
server.connect(int(input("enter code: ")))
server.run()

