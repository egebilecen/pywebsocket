import hashlib
import base64

def create(hs,host,port):
	HANDSHAKE = '\
HTTP/1.1 101 Web Socket Protocol Handshake\r\n\
Upgrade: WebSocket\r\n\
Connection: Upgrade\r\n\
WebSocket-Origin: {host}\r\n\
WebSocket-Location: ws://localhost:{port}/\r\n\
'.format(host=host,port=port)
	hsList = hs.split('\r\n')
	hsBody = hs.split('\r\n\r\n')[1]
	magic  = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
	key    = ''

	for i in hsList:
		if i.startswith('Sec-WebSocket-Key:'):
			key = i[19:]
		else:
			continue
	s = hashlib.sha1()
	s.update((key+magic).encode())
	h = s.digest()
	a = base64.b64encode(h)
	a = a.decode()
	HANDSHAKE += 'Sec-WebSocket-Accept: '+str(a)+'\r\n\r\n'
	return HANDSHAKE.encode()