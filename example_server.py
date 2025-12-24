from TCPoverUDP import TCPServer
import socket
import time
import random
import threading

server = TCPServer(5555)
print(server.get_code())
server.connect(int(input("enter code: ")))
server.run()

