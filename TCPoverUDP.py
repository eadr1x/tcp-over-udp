import socket
import time
import random
import threading

def addr2int(ip, port):
    binport = bin(port)[2:].rjust(16, "0")
    binip = "".join([bin(int(i))[2:].rjust(8, "0") for i in ip.split(".")])
    return int(binip + binport, 2)

def int2addr(num):
    num = bin(num)[2:].rjust(48, "0")
    num = [str(int(i, 2)) for i in [num[0:8], num[8:16], num[16:24], num[24:32], num[32:48]]]
    return ".".join(num[0:4]), int(num[4])

def stun(port, host="stun.ekiga.net", sock = None):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.setblocking(False)
    server = socket.gethostbyname(host)
    while True:
        sock.sendto(b"\x00\x01\x00\x00!\x12\xa4B\xd6\x85y\xb8\x11\x030\x06xi\xdfB", (server, 3478),)
        for i in range(20):
            try:
                ans, addr = sock.recvfrom(2048)
                sock.close()
                return socket.inet_ntoa(ans[28:32]), int.from_bytes(ans[26:28], byteorder="big")
            except:
                time.sleep(0.05)


class UDPHolePuncher:
    def __init__(self):
        self.queue = []
        self.out_queue = []
        self.__current_client = None
        self.state = 0  # not connected

        self.__local_port = random.randint(20000, 30000)
        self.__public_ip, self.__public_port = [stun(self.__local_port) for _ in range(10)][0]
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind(('0.0.0.0', self.__local_port))

        self.__th = threading.Thread(target=self.__listener, daemon=True)
        self.__ping = threading.Thread(target=self.__pinger, daemon=True)
        self.__kpl = threading.Thread(target=self.__kpl_sender, daemon=True)

    def __listener(self):
        while True:
            data, addr = self.__sock.recvfrom(9999)
            if data[0] == 2:
                self.queue.append(data[1:])
                print(addr, "->", data[1:])

    def __pinger(self):
        while self.state == 0:
            self.__sock.sendto(b'\x00',self.__current_client)
            time.sleep(0.5)

    def __kpl_sender(self):
        t = time.time()
        while self.state == 1:
            data = b''
            try:
                data = self.out_queue.pop(0)
            except IndexError:
                pass
            if data:
                self.__sock.sendto(b'\x02'+data, self.__current_client)
            if time.time() - t > 0.5:
                self.__sock.sendto(b'\x11', self.__current_client)
                t = time.time()

    def connect(self,code):
        self.__current_client = int2addr(code)
        self.__ping.start()
        while self.state == 0:
            data, addr = self.__sock.recvfrom(4096)
            time.sleep(5)
            self.state = 1
            time.sleep(1)
            self.__th.start()
            self.__kpl.start()
        print('connected')

    def get_code(self):
        return addr2int(self.__public_ip, self.__public_port)

    def send_data(self, data):
        self.out_queue.append(data)

class TCPClient(UDPHolePuncher):
    def __init__(self, port = 5555):
        super().__init__()
        self.__current_client = None
        self.tcp_state = 0  # not connected

        self.__port = port
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.__sock.bind(('0.0.0.0', self.__port))
        self.__sock.listen(1)

        self.__send = threading.Thread(target=self.__tcp_sender, daemon=True)

    def run(self):
        self.__send.start()
        while True:
            self.__current_client, addr = self.__sock.accept()
            self.send_data(b'\x00')
            self.tcp_state = 1
            self.__current_client.setblocking(False)
            while self.tcp_state:
                try:
                    data = self.__current_client.recv(4096)
                    if data:
                        self.send_data(b'\x02' + data)
                    else:
                        self.tcp_state = 0
                        self.send_data(b'\x01')
                        self.__current_client.close()
                except BlockingIOError:
                    pass


    def __tcp_sender(self):
        while True:
            data = b''
            try:
                data = self.queue.pop(0)
            except IndexError:
                pass
            if data:
                if data[0] == 1 and self.tcp_state:
                    self.tcp_state = 0
                    self.__current_client.close()
                elif data[0] == 2 and self.tcp_state:
                    self.__current_client.sendall(data[1:])


class TCPServer(UDPHolePuncher):
    def __init__(self, port=5555):
        super().__init__()
        self.__current_client = None
        self.tcp_state = 0  # not connected

        self.__port = port
        self.__send = threading.Thread(target=self.__udp_sender, daemon=True)

    def run(self):
        self.__send.start()
        while True:
            data = b''
            try:
                data = self.queue.pop(0)
            except IndexError:
                pass
            if data:
                if data[0] == 0 and not self.tcp_state:
                    self.__sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.__sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.__sock.connect(('0.0.0.0', self.__port))
                    self.__sock.setblocking(False)
                    self.tcp_state = 1
                elif data[0] == 1 and self.tcp_state:
                    self.tcp_state = 0
                    self.__sock.close()
                elif data[0] == 2 and self.tcp_state:
                    self.__sock.sendall(data[1:])

    def __udp_sender(self):
        while True:
            if self.tcp_state:
                try:
                    data = self.__sock.recv(4096)
                    if data:
                        self.send_data(b'\x02' + data)
                    else:
                        self.tcp_state = 0
                        self.send_data(b'\x01')
                        self.__sock.close()
                except BlockingIOError:
                    pass
                except ConnectionResetError:
                    self.tcp_state = 0
                    self.send_data(b'\x01')
                    self.__sock.close()
                except OSError as e:
                    pass

