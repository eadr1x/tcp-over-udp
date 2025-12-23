from TCPoverUDP import TCPClient, UPDHolePuncher, stun, addr2int, int2adddr
import socket
import time
import random
import threading

client = TCPClient(5555)
print(client.get_code())
client.connect(int(input("enter code: ")))
client.run()
