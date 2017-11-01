# -*- coding: utf-8 -*-
import hashlib
import struct
import socket
import base64
import json
import urllib
from _thread import *
from random import random
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

class EB_Websocket():
	# Constructor
	def __init__(self, addr=('',3131), handlers=None, specialHandlers=None, autoRun=True):
		if handlers is None:
			handlers = {}
		if specialHandlers is None:
			specialHandlers = {}

		self.HOST   = addr[0]
		self.PORT   = addr[1]
		self.SERVER = None
		self.SOCKET_LIST = {}
		self.HANDLERS    = handlers
		self.SPECIAL_HANDLERS = specialHandlers
		self.exception   = True
		self.debug       = True
		self.isClosed    = False

		if callable(specialHandlers["init"]):
			specialHandlers["init"](self)

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
			# if self.debug:
			# 	print('[?] New connection -', addr, end='\n\n')

			data = conn.recv(4096)
			conn.send(self.create_handshake(data.decode()))
			start_new_thread(self.clientHandler, (conn, addr,))

	# Close server
	def close_server(self):
		self.SERVER.close()
		self.isClosed = True
		if self.debug:
			print("[?] Server closed.")

	# HANDLER METHODS #
	def setHandler(self, name, handler):
		self.HANDLERS[name] = handler

	# Handler for clients
	def clientHandler(self, conn, addr):
		private_data = { "socket_id" : random() }
		socket_id    = private_data["socket_id"]

		try: # check if socket exist
			_a = self.SOCKET_LIST[socket_id]
		except: # if not exist create new one and store it
			self.SOCKET_LIST[socket_id] = { "conn":conn, "addr":addr, "private_data":private_data }

		# run on socket open event
		if callable(self.SPECIAL_HANDLERS["on_socket_open"]):
			self.SPECIAL_HANDLERS["on_socket_open"](self, private_data)

		while True:
			if(self.isClosed):
				exit_thread()

			data = conn.recv(4096)

			if not data:
				# if self.debug:
				# 	print('\nA socket has left.',end='\n\n')
				if callable(self.SPECIAL_HANDLERS["disconnect"]):
					self.SPECIAL_HANDLERS["disconnect"](self, private_data)
				self.SOCKET_LIST.pop(socket_id)
				conn.close()
				break
			else:
				where, recvData = self.message_decode(data)

				if where == False or recvData == False:
					# detected un-masked data or closing frame
					self.SOCKET_LIST.pop(socket_id)
					conn.close()
					break
				else:
					if not self.exception:
						try:
							self.HANDLERS[where](conn, recvData, self, private_data)
						except Exception as err:
							# couldn't find handler or an error occured in handler
							pass
					else:
						self.HANDLERS[where](conn, recvData, self, private_data)

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

	def emit_all(self, where, data):
		re_data = json.dumps({"where":where,"data":data})
		for i in self.SOCKET_LIST:
			conn = self.SOCKET_LIST[i]["conn"]
			self.send_message(conn, re_data)	

	def send_message(self, conn, data):
		send_data = self.message_encode(data)
		if send_data == False:
			raise Exception("Your data is too big for sending to client!")
		else:
			conn.send(send_data)

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

		if OPCODE == 8:
			return (False, False)

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
			return (False,False)

		payload = ""
		for i, c in enumerate(data):
			payload += chr(c ^ MASK[i % 4])

		payload = urllib.parse.unquote(payload)

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
