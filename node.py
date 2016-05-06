'''
node.py
Tasks:
Send info to directory node
Decrypt layer of encryption
Relay data onward
On data coming back, decrypt and send to previous node
'''

import socket
import sys
from os import chmod
from aes_rsa import *

#DIR_IP = '172.17.224.57'
DIR_PORT = 1600

TCP_IP = socket.gethostbyname(socket.gethostname())
TCP_PORT = 1601

BUFFER_SIZE = 4096 
NODES = {}
NUM_NODES = 3

# Generate RSA Keys
# -----------------------------
RSAKeys = []
AESKey = ""
privateKeyFile = "privateRSA.key"
publicKeyFile = "publicRSA.key"

if len(sys.argv) == 2 and sys.argv[1] == "-genKey":
    print "Generating RSA key pair."
    RSAKeys = genRSAKey()
    with open(privateKeyFile, 'w') as myContent:
        chmod(privateKeyFile, 0600)
        myContent.write(RSAKeys[1])
    with open(publicKeyFile, 'w') as myContent:
        chmod(privateKeyFile, 0600)
        myContent.write(RSAKeys[0])

elif len(sys.argv) == 1:
    print "importing keys"   
else:
    print "Incorrect arguments"
    sys.exit()

try:
    publicRSA = open(publicKeyFile).read()
    privateRSA = open(privateKeyFile).read()
except:
    print "importing keys failed"
    exit()

DIR_IP = raw_input("Directory server to connect to: ")
print "Sending request to directory server."
# Update Directory
# -----------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((DIR_IP, DIR_PORT))
s.send('Onion Router###' + publicRSA)
s.close()

# Get Directory Data
# -----------------------------
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, DIR_PORT))
s.listen(1)

conn, addr = s.accept()
addr = addr[0]
myData = conn.recv(BUFFER_SIZE).split("###")

NUM_NODES = int(myData[0])
myData = myData[1:]

print 'Connection address:', addr
print "Return data from directory server: "
for x in range(NUM_NODES):
    NODES[myData[2 * x]] = myData[2 * x + 1]
    print myData[2 * x] + ":" + myData[2 * x + 1]

conn.close()
s.close()

# Run Node
# -----------------------------
entranceFlag = ""
entranceAddr = ""
exitAddr = ""

# Start Listening
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

while 1:
	conn, addr = s.accept()
	addr = addr[0]
	data = conn.recv(BUFFER_SIZE)

	print "[Node Running] Connection address: ", addr

	if not data: break
	print "[Node Running] Received data: ", data

	myEncryptedData = data.split("###")
	decryptedMessage = decryptAESRSA(myEncryptedData[1], privateRSA, myEncryptedData[0]).split("###")
	nextNode = decryptedMessage[0]

	# Entrance Node Case
	if len(decryptedMessage) == 4:
		entranceFlag = decryptedMessage[3]
		entranceAddr = addr
		if decryptedMessage[3] == "entrance":
			print "This is the entrance node receiving initial packet."
		conn.close()
		s.close()
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

	# Send to Next Node
	if nextNode in NODES:
		conn.close()
		s.close()
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((nextNode, TCP_PORT))
		s.send(decryptedMessage[1] + "###" + decryptedMessage[2])
		s.close()
		print "This is not an exit node. Nothing special here."
		
	# Entrance Node
	elif entranceFlag == "entrance" and not nextNode:

		conn.close()
		s.close()
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((entranceAddr, TCP_PORT))
		# original's server response (at least it's supposed to be)
		s.send(decryptedMessage[1])
		s.close()
		print "This is the entrance node returning to the client"
		entranceFlag = ""
		entranceAddr = ""
		
	# Exit Node - Send Data Back
	elif nextNode not in NODES:
		conn.close()
		s.close()
		print "This is the exit node."
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((nextNode, TCP_PORT))
		s.send(decryptedMessage[1])

		serverResponse = s.recv(BUFFER_SIZE)
		s.close()
		
		returnRoute = decryptedMessage[3:]
		returnRoute.reverse()
		returnMessage = serverResponse
		print "Return Route: "
		print returnRoute
                print "Decrypted Message:"
		print decryptedMessage

		for x in range(len(returnRoute)):
			returnMessage = "###" + returnMessage
			if x != 0:
				returnMessage = returnRoute[x-1] + returnMessage
			encryptedKey, encryptedMsg = easyEncrypt(NODES[returnRoute[x]], returnMessage)
			returnMessage = encryptedMsg + "###" + encryptedKey
			
		
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((decryptedMessage[3], TCP_PORT))
		s.send(returnMessage)
		s.close()
		
	# Continue Listening
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.bind((TCP_IP, TCP_PORT))
	s.listen(1)
