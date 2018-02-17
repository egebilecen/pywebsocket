# -*- coding: utf-8 -*-
import sys
import platform
import hashlib
import struct
import socket
import base64
import json
import urllib
import threading
from random import random

if platform.system() == "Linux":
	from signal import signal, SIGPIPE, SIG_DFL
	signal(SIGPIPE, SIG_DFL)

class EB_Websocket:
	# Constructor
	def __init__(self, addr=('',3131), handlers=None, specialHandlers=None, autoRun=True, debug=False):
		if handlers is None:
			handlers = {}
		if specialHandlers is None:
			specialHandlers = {}

		self.HOST   		  = addr[0]
		self.PORT  			  = addr[1]
		self.SERVER 		  = None
		self.SOCKET_LIST	  = {}
		self.HANDLERS    	  = handlers
		self.SPECIAL_HANDLERS = specialHandlers
		self.exception   	  = True
		self.debug       	  = debug
		self.isClosed    	  = False
		self.platform    	  = platform.system()
		self.threads		  = [] # client handler threads will be here.
		self._threads 		  = {} # for special threads like "Loop".

		if callable(specialHandlers["init"]):
			try:
				specialHandlers["init"](self)
			except Exception as e:
				print(e)
				sys.exit(0)

		# Multiprocessing for Loop Special Handler #
		if callable(self.SPECIAL_HANDLERS["loop"]):
			_t = threading.Thread(target=self.SPECIAL_HANDLERS["loop"],args=(self,))
			_t.daemon = False
			self._threads["loop"] = _t

		if autoRun:
			self.run_server()

	# SERVER METHODS #
	def run_server(self):
		# Create socket
		self.SERVER = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# Open Server
		self.SERVER.bind((self.HOST, self.PORT))
		if self.debug:
			print('[?] Server opened.', end='\n')

		# Listen connections
		self.SERVER.listen()
		if self.debug:
			print('[?] Server waiting for connections.', end='\n')

		# Run loop #
		self._threads["loop"].start()

		while True:
			if self.isClosed:
				break

			try:
				conn, addr = self.SERVER.accept()
				if self.debug:
					print('[?] New connection -', addr, end='\n')

				data = conn.recv(4096)
				conn.send(self.create_handshake(data.decode()))

				# create thread
				_t = threading.Thread(target=self.client_handler, args=(conn, addr,))
				self.threads.append(_t)
				_t.start()

			except KeyboardInterrupt:
				self.close_server()

	# Close server
	def close_server(self):
		self.SERVER.close()
		self.isClosed = True

		print("[?] Server closed.")

	# HANDLER METHODS #
	def close_client_connection(self, socket_id, conn, private_data):
		if callable(self.SPECIAL_HANDLERS["disconnect"]):
			self.SPECIAL_HANDLERS["disconnect"](self, private_data)
		self.SOCKET_LIST.pop(socket_id)
		conn.close()

	def client_handler(self, conn, addr):
		private_data = { "socket_id" : random() }
		socket_id    = private_data["socket_id"]

		try: # check if socket exist
			_a = self.SOCKET_LIST[socket_id]
		except: # if not exist create new one and store it
			self.SOCKET_LIST[socket_id] = { "conn":conn, "addr":addr, "private_data":private_data }

		# run on socket open event
		if callable(self.SPECIAL_HANDLERS["on_socket_open"]):
			self.SPECIAL_HANDLERS["on_socket_open"](self, private_data)

		while True and not self.isClosed:
			data = conn.recv(4096)

			if not data:
				if self.debug:
					print('\nA socket has left.',end='\n')
				self.close_client_connection(socket_id, conn, private_data)
				break
			else:
				where, recvData = self.message_decode(data)

				if where == False or recvData == False:
					# detected un-masked data or closing frame
					self.close_client_connection(socket_id, conn, private_data)
					break
				else:
					if not self.exception:
						try:
							self.HANDLERS[where](conn, recvData, self, private_data)
						except:
							# couldn't find handler or an error occured in handler
							pass
					else:
						self.HANDLERS[where](conn, recvData, self, private_data)

	def loop(self):
		if callable(self.SPECIAL_HANDLERS["loop"]):
			while True and not self.isClosed:
				self.SPECIAL_HANDLERS["loop"](self)

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
		if not send_data:
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
