# -*- coding: utf-8 -*-
import socket
import sys
import modules.handshake as handshake
import modules.message as message
from _thread import *

class EB_Websocket():
	def __init__(self, handlerFunc, autoRun=True):
		self.HOST = ''
		self.PORT = 3131
		self.SERVER = None
		self.SOCKET_LIST = {}
		self.handlerFunc = handlerFunc
		self.debug = False

		if autoRun == True:
			self.run_server()

	def run_server(self):
		# Create socket
		self.SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# Open Server
		self.SERVER.bind((self.HOST, self.PORT))
		if self.debug:
			print('[?] Server opened.', end='\n\n')

		# Listen connections
		self.SERVER.listen()
		if self.debug:
			print('[?] Server waiting for connections.', end='\n\n')

		while True:
			conn, addr = self.SERVER.accept()
			if self.debug:
				print('[?] New connection -', addr, end='\n\n')

			data = conn.recv(4096)

			if self.debug:
				print('[?] Sending handshake.', end='\n\n')
			conn.sendto(handshake.create(data.decode(),self.HOST,self.PORT), (addr[0], addr[1]))

			start_new_thread(self.clientHandler, (conn, addr,))

	def close_server(self):
		self.SERVER.close()
		if self.debug:
			print("[?] Server closed.")
		sys.exit()

	def clientHandler(self,conn,addr):
		while True:
			data = conn.recv(4096)

			if not data:
				if self.debug:
					print('\nA socket has left.',end='\n\n')
				conn.close()
				break
			else:
				try:
					where, recvData = message.decode(data)
					self.handlerFunc(conn, where, recvData)
				except:
					# detected un-masked data
					conn.close()
					break

def handler(sock, where, data):
	if where == "start":
		print(message.encode("hello"))
		sock.send(message.encode("hello"))

server = EB_Websocket(handler)