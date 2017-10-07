# -*- coding: utf-8 -*-
import hashlib
import struct
import socket
import base64
import json
import sys
from _thread import *
from random import random

class EB_Websocket():
	# Constructor
	def __init__(self, handlers, autoRun=True):
		self.HOST   = ''
		self.PORT   = 3131
		self.SERVER = None
		self.SOCKET_LIST = {}
		self.HANDLERS    = handlers
		self.exception   = True
		self.debug       = True

		if autoRun == True:
			self.run_server()

	# SERVER METHODS #
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
				print('[?] Creating handshake.', end='\n\n')
			conn.send(self.create_handshake(data.decode()))

			start_new_thread(self.clientHandler, (conn, addr,))

	# Close server
	def close_server(self):
		self.SERVER.close()
		if self.debug:
			print("[?] Server closed.")
		sys.exit()

	# HANDLER METHODS #
	def setHandler(self, name, handler):
		self.HANDLERS[name] = handler

	# Handler for clients
	def clientHandler(self, conn, addr):
		addr = addr + (random(),)
		socket_id = addr[2]

		try:
			_a = self.SOCKET_LIST[socket_id]
		except:
			self.SOCKET_LIST[socket_id] = { "conn":conn, "addr":addr }

		while True:
			data = conn.recv(4096)

			if not data:
				if self.debug:
					print('\nA socket has left.',end='\n\n')
				self.SOCKET_LIST.pop(socket_id)
				conn.close()
				break
			else:
				where, recvData = self.message_decode(data)
				try:
					self.HANDLERS[where](conn, recvData, self)
				except:
					pass

	# HANDSHAKE METHODS #
	def create_handshake(self, hs):
		HANDSHAKE = 'HTTP/1.1 101 Web Socket Protocol Handshake\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\nWebSocket-Origin: {host}\r\n'\
			.format(host=self.HOST, port=self.PORT)
		hsList = hs.split('\r\n')
		hsBody = hs.split('\r\n\r\n')[1]
		magic = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
		key = ''

		for i in hsList:
			if i.startswith('Sec-WebSocket-Key:'):
				key = i[19:]
			else:
				continue
		s = hashlib.sha1()
		s.update((key + magic).encode())
		h = s.digest()
		a = base64.b64encode(h)
		a = a.decode()
		HANDSHAKE += 'Sec-WebSocket-Accept: ' + str(a) + '\r\n\r\n'
		return HANDSHAKE.encode()

	# MESSAGE METHODS #
	def emit(self, conn, where, data):
		re_data = json.dumps({"where":where,"data":data})
		self.send_message(conn, re_data)

	def send_message(self, conn, data):
		conn.send(self.message_encode(data))

	def message_decode(self, data):
		HEADER, = struct.unpack("!H", data[:2])
		data = data[2:]

		FIN    = (HEADER >> 15) & 0x01
		RSV1   = (HEADER >> 14) & 0x01
		RSV2   = (HEADER >> 13) & 0x01
		RSV3   = (HEADER >> 12) & 0x01
		OPCODE = (HEADER >>  8) & 0x0F
		MASKED = (HEADER >>  7) & 0x01
		LEN    = (HEADER >>  0) & 0x7F

		if LEN == 126:
			LEN, = struct.unpack("!H", data[:2])
			data = data[2:]
		elif LEN == 127:
			LEN, = struct.unpack("!4H", data[:8])
			data = data[8:]

		if MASKED:
			MASK = struct.unpack("4B", data[:4])
			data = data[4:]
		else:
			return False

		payload = ""
		for i, c in enumerate(data):
			payload += chr(c ^ MASK[i % 4])

		try:
			_data = json.loads(payload)
		except:
			_data = {"where": "null", "data": {}}

		return (_data["where"], _data["data"])

	def message_encode(self, data):
		FIN    = 0x80
		OPCODE = 0x01
		EXT_16 = 0x7E
		EXT_64 = 0x7F

		HEADER      = bytearray()
		PAYLOAD     = data.encode()
		PAYLOAD_LEN = len(data)

		if PAYLOAD_LEN <= 125:
			HEADER.append(FIN | OPCODE)
			HEADER.append(PAYLOAD_LEN)
		elif PAYLOAD_LEN <= 65535:
			HEADER.append(FIN | OPCODE)
			HEADER.append(EXT_16)
			HEADER.extend(struct.pack(">H", PAYLOAD_LEN))
		elif PAYLOAD_LEN < 18446744073709551616:
			HEADER.append(FIN | OPCODE)
			HEADER.append(EXT_64)
			HEADER.extend(struct.pack(">Q", PAYLOAD_LEN))
		else:
			return False

		return HEADER + PAYLOAD

def start(socket, data, f):
	f.emit(socket, "welcome", {"deneme":123})

server = EB_Websocket({"start":start})