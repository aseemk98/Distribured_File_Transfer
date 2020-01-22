import socket
import sys
import threading
import struct
import os
import time

#multicast_group = ('224.3.29.71', 20000)
listening_sock_address = ('192.168.0.11',10000)
multicast_ip = '224.3.29.71'
multicast_address = ('',20000)

global coordinators
coordinators = []

global file_data
file_data = {}
file_list = []

#if node is cood set it to 0
global is_cood


#runs the multicast receive socket
def open_multicast_rcv():
	print("multicast receive set")
	multicast_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	multicast_recv.bind(multicast_address)
	group = socket.inet_aton(multicast_ip)
	mreq = struct.pack('4sL', group, socket.INADDR_ANY)
	multicast_recv.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

	while True:
		data,address = multicast_recv.recvfrom(1024)
		

		#dont listen to your own mukticast address
		#if address[0]!=listening_sock_address[0]:
		print(data.decode(),address)
		msg_parser(data.decode())
		#else:
			#msg_list = data.decode().split()
			#if msg_list[1] == "REQ":
			#	msg_parser(data.decode())

# this function will keep a socket open
def open_receiving_socket():

	unicast_recv = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	#server_address = ('localhost',10000)
	unicast_recv.bind(listening_sock_address)
	while True:
		data,address = unicast_recv.recvfrom(4096)
		if data:
			print(data.decode(),str(address))
			msg_parser(data.decode())



#use this to send a multicast message
def send_multicast(msg):
	multicast_sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	multicast_sender.settimeout(0.5)
	ttl = struct.pack('b',1)
	multicast_sender.setsockopt(socket.IPPROTO_IP,socket.IP_MULTICAST_TTL, ttl)
	#msg = "this is a multicasted message"
	print('message being multicasted:',msg)
	for x in range(20000,20010):
		multicast_group = ('224.3.29.71',x)
		multicast_sender.sendto(msg.encode(),multicast_group)

#use this to send a unicast message to a certain peer whose address is known
def send_unicast(msg,target_address):

	unicast_sender = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
	#msg = "This message has been unicasted"
	print('message being multicasted:',msg)
	unicast_sender.sendto(msg.encode(),target_address)

def send_introduction_as_coordinator():

	msg = "0 HELLO "+listening_sock_address[0]+" "+str(listening_sock_address[1])
	send_multicast(msg)


def compile_file_message(f_str):
	return "0 FILES SF "+f_str+" EF "+listening_sock_address[0]+" "+str(listening_sock_address[1])

def read_file_list():
	file_list = os.listdir('./shared/')
	file_string = ' '.join(x for x in file_list)

	msg = compile_file_message(file_string)
	return msg

def send_files_as_node():
	file_str = read_file_list()
	#print('file_str',file_str)
	msg_to_send = file_str
	#broadcast message
	send_multicast(msg_to_send)

def search_file_data(file_req):
	#search the file_data dict
	#print(file_data)
	for node in file_data:
		#print('node',file_data[node])
		if file_req in file_data[node]:
			return node

	return None


def msg_parser(msg):
	msg_list = msg.split()
	#message from coordinator

	if int(msg_list[0])==0:
		if msg_list[1] == "HELLO":
			#send file list and add coordnator address to the list
			# if((msg_list[2],int(msg_list[3])) not in coordinators):
			# 	coordinators.append((msg_list[2],int(msg_list[3])))
			#if the node is a coordinator, store the cooordinator in the list

			if is_cood==0:
				coordinators.append((msg_list[2],int(msg_list[3])))
				print('coordinators:',coordinators)





			msg_to_send = read_file_list()
			send_multicast(msg_to_send)

		#when the coordinator receives list of files
		if msg_list[1] == "FILES" and is_cood==0:
			#get files
			files = msg_list[msg_list.index("SF")+1:msg_list.index("EF")]
			sender_ip = msg_list[msg_list.index("EF")+1]
			sender_port = int(msg_list[msg_list.index(sender_ip)+1])
			file_data[(sender_ip,sender_port)] = files 
			#print(file_data)

		if msg_list[1] == "REQ" and is_cood==0:
			#search file data for file and send the target node the address of the requesting node
			#print("HERE IN REQ")
			print('here')
			search_res = search_file_data(msg_list[2])
			print('search_res',search_res)
			if search_res is not None:
				# file exists with some node 
				#check if the target node is the coordinator itself
				if search_res is listening_sock_address:
					#cood has the file
					#print('search_res',search_res)
					print('\nsearch res matched with own address')
					send_name(msg_list[2],(msg_list[3],int(msg_list[4])))
					time.sleep(3)
					send_file_data(msg_list[2],(msg_list[3],int(msg_list[4])))

				else:
					#search res has the address of the node that has the file
					msg_to_send = compile_send_file_message(msg_list[2],(msg_list[3],int(msg_list[4])))
					#print('send msg',type(msg_to_send))
					send_unicast(msg_to_send,search_res)
			else:
				send_unicast("0 ERROR ",(msg_list[3],int(msg_list[4])))
		if msg_list[1] == "SEND" and is_cood==1:
			#instruction from the cood to send the file
			send_name(msg_list[2],(msg_list[3],int(msg_list[4])))
			send_file_data(msg_list[2],(msg_list[3],int(msg_list[4])))
		if msg_list[1] == "ERROR":
			print("REQUESTED FILE NOT FOUND")
	else:
		if msg_list[1] == "NAME":

			file_list = os.listdir('./shared/')
			if msg_list[2] not in file_list:
				os.system('touch ./shared/'+msg_list[2])

		if msg_list[1] == "DATA":
			with open('./shared/'+msg_list[2],'r') as r:
				text = r.read()
			#write only if the file is empty
			if text is "":
				with open('./shared/'+msg_list[2],'w') as w:
					w.write(msg_list[3]) 


def send_name(filename,target_address):

	msg = "1 NAME "+filename

	send_unicast(msg,target_address)

def send_file_data(filename,target_address):

	r = open('./shared/'+filename,'r')
	text = r.read()
	r.close()
	print('text to be sent',text)
	msg = "1 DATA "+filename+" "+text
	print('msg file:',msg )
	send_unicast(msg,target_address)


def send_file(file_name,target_address):
	
	#send the name of the file that has been requested
	send_name(filename,target_address)
	time.sleep(3)
	send_file_data()

def compile_send_file_message(file_name,node):
	return "0 SEND "+file_name+" "+node[0]+" "+str(node[1])

def compile_req_msg(file_req):
	return "0 REQ "+file_req+" "+listening_sock_address[0]+" "+str(listening_sock_address[1])

def process_req(file_req):

	print('Input:',file_req)
	#if the requesting node is already a coordinator, check own database
	if is_cood==0:
		search_res = search_file_data(file_req)
		if search_res is not None:
				# file exists with some node 
				#check if the target node is the coordinator itself
				print('search_res:',search_res)
				if search_res == listening_sock_address:
					#send the file to the target 
					print("FILE ALREADY PRESENT")


				else:
					#search res has the address of the node that has the file
					msg_to_send = compile_send_file_message(file_req,(listening_sock_address[0],listening_sock_address[1]))
					print('send msg',msg_to_send)
					send_unicast(msg_to_send,search_res)
		else:
			print("FILE NOT FOUND")
	else:
	#if the node is a normal node, broadcast the request made

		if file_req in os.listdir('./shared/'):
			print("FILE ALREADY PRESENT")

		else:
			msg_to_send = compile_req_msg(file_req)
			send_multicast(msg_to_send)


if __name__=="__main__":

	argList = sys.argv
	is_cood = int(argList[1])

	print('is_cood',is_cood)

	t1 = threading.Thread(target=open_receiving_socket)
	t2 = threading.Thread(target=open_multicast_rcv)
	#open a socket
	t1.start()

	#open multicast rcv socket
	t2.start()
	print("socket has started")

	# if the current node is a coordinator node, send hello 
	if(is_cood==0):
		send_introduction_as_coordinator()
	#else:
	# the current node is a normal node
	send_files_as_node()

	#this part will display a menu
	while True:
		file_req = input('Enter the name of file that you want:')
		process_req(file_req)




	#broadcast it's IP over the network. if it reveives a response...append to available nodes. 


