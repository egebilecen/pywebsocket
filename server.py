# -*- coding: utf-8 -*-
import socket
import json
import modules.handshake as handshake
import modules.message as message
from _thread import *

class EB_Websocket():
	def __init__(self, handlerFunc, _autoRun):
		self.HOST = ''
		self.PORT = 3131
		self.SERVER = None
		self.SOCKET_LIST = {}
		self.handlerFunc = handlerFunc

		if _autoRun == True:
			self.run_server()

	def run_server(self):
		# Create socket
		self.SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# Open Server
		self.SERVER.bind((self.HOST, self.PORT))
		print('[?] Server opened.', end='\n\n')

		# Listen connections
		self.SERVER.listen()
		print('[?] Server waiting for connections.', end='\n\n')

		while True:
			conn, addr = self.SERVER.accept()
			print('[?] New connection -', addr, end='\n\n')

			data = conn.recv(4096)

			print('[?] Sending handshake.', end='\n\n')
			conn.sendto(handshake.create(data.decode(),self.HOST,self.PORT), (addr[0], addr[1]))

			start_new_thread(self.clientHandler, (conn, addr,))

	def close_server(self):
		self.SERVER.close()

	def clientHandler(self,conn,addr):
		while True:
			data = conn.recv(4096)

			if not data:
				print('\nA socket has left.',end='\n\n')
				conn.close()
				break
			else:
				where, recvData = message.decode(data)
				self.handlerFunc(where,json.loads(recvData))

def handler(where,data):
	if where == "start":
		print("works!!",str(data))

server = EB_Websocket(handler, True)