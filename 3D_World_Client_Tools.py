import json
import zmq
import socket
import datetime
from tabulate import tabulate
from pick import pick

class Three_D_World_Client(object):

	def __init__(self, host_address="18.93.5.202", 
				 queue_port_num="23402",
				 requested_port_num=None, 
				 environment_config=None, 
				 debug=True, 
				 selected_build=None, 
				 selected_forward=None, 
				 initial_command="", 
				 username=None, 
				 description=None):

		self.queue_host_address = host_address
		self.queue_port_number = queue_port_num

		self.port_num = requested_port_num
		self.selected_build = selected_build
		self.selected_forward = selected_forward
		self.environment_config = environment_config
		self.initial_command = initial_command
		self.username = username
		self.description = description
		
		self.ctx = zmq.Context()

		self.debug = debug

		print "\n\n"
		print '=' * 60
		print " " * 17, "WELCOME TO 3D WORLD CLIENT"
		print '=' * 60
		print "\n"

		if (self.debug):
			print ("\nconnecting...")
		self.sock = self.ctx.socket(zmq.REQ)
		self.sock.connect("tcp://" + self.queue_host_address + ":" + self.queue_port_number)
		if (self.debug):
			print "...connected @", self.queue_host_address, ":", self.queue_port_number, "\n\n"

		self.connected_to_queue = True
		self.manually_pick_port_num = True
		self.ready_for_input = True
		self.ready_for_recv = False

	#main loop
	def run(self):
		commands = {
			"request_create_environment" : self.request_create_environment,
			"request_active_processes" : self.request_active_processes,
			"request_join_environment" : self.request_join_environment,
		}

		if (self.initial_command in commands.keys() and not self.ready_for_recv):
			commands[self.initial_command]()

		while(not self.ready_for_recv):
			title = "Pick a command:"
			options = commands.keys()
			option, index = pick(options, title)
			commands[option]()
			
		while(self.connected_to_queue):
			if (self.ready_for_recv):
				msg = self.recv_json(self.sock)
	
				j = json.loads(msg)
				
				self.ready_for_recv = False

			while(not self.ready_for_recv):
				title = "Pick a command:"
				options = commands.keys()
				option, index = pick(options, title)
				commands[option]()

		print "=" * 60
		print " " * 19, "Client Setup Complete"
		print "=" * 60
		return self.sock

	######################################################################################################
									  	    #USER FUNCTIONS#
	######################################################################################################

	def load_config(self, config_dict):
		self.environment_config = config_dict

	def reconnect(self):
		try:
			self.connect_to_port(self.port_num, use_config=False)
			return True
		except:
			return False

	#######################################################################################################


	#######################################################################################################
										  #COMMANDS TO QUEUE#
	#######################################################################################################
	
	def request_create_environment(self):
		print '_' * 60
		print " " * 16, "Requesting Create Environment"
		print '_' * 60, "\n"

		if (not self.port_num):
			self.pick_new_port_num()

	#phase 1
		has_valid_port_num = False
		while (not has_valid_port_num):
			self.send_json(json.dumps({"msg" : {"msg_type" : "CREATE_ENVIRONMENT_1"}, "port_num" : str(self.port_num)}), self.sock)
			msg = self.recv_json(self.sock)

			msg = json.loads(msg)

			if (msg["msg"]["msg_type"] == "PORT_UNAVAILABLE"):
				self.pick_new_port_num()
			elif (msg["msg"]["msg_type"] == "SEND_OPTIONS"):
				has_valid_port_num = True
			else:
				print "Error: " + msg["msg"]["msg_type"] + "\n"
				self.press_enter_to_continue()
				return

		build_option = self.pick_option(msg, default_choice=self.selected_build)

	#phase 2
		has_valid_port_num = False
		while (not has_valid_port_num):
			self.send_json(json.dumps({"msg" : {"msg_type" : "CREATE_ENVIRONMENT_2"}, "port_num" : str(self.port_num)}), self.sock)
			msg = self.recv_json(self.sock)

			msg = json.loads(msg)

			if (msg["msg"]["msg_type"] == "PORT_UNAVAILABLE"):
				self.pick_new_port_num()
			elif (msg["msg"]["msg_type"] == "SEND_OPTIONS"):
				has_valid_port_num = True
			else:
				print "Error: " + msg["msg"]["msg_type"] + "\n"
				self.press_enter_to_continue()
				return

	
		forward_option = self.pick_option(msg, default_choice=self.selected_forward)

	#phase 3
		username, description = self.username, self.description

		#collect username and description if not given in initialization
		while (not username):
			print "\nPlease type a username:"
			username = raw_input()
			print ""
		while (not description):
			print "\nPlease type a description:"
			description = raw_input()
			print ""

		has_valid_port_num = False
		while (not has_valid_port_num):

			base_msg = {"msg" : {"msg_type" : "CREATE_ENVIRONMENT_3"}, "port_num" : str(self.port_num), 
																   "selected_build" : build_option,
																   "selected_forward" : forward_option,
																   "username" : username,
																   "description" : description}
			msg = base_msg.copy()
		
			#add config
			msg.update(self.environment_config)
		
			#request environment
			msg = json.dumps(msg)
			self.send_json(msg, self.sock)

			#receive environment port number
			msg = self.recv_json(self.sock)

			msg = json.loads(msg)

			if (msg["msg"]["msg_type"] == "PORT_UNAVAILABLE"):
				self.pick_new_port_num()
			elif (msg["msg"]["msg_type"] == "JOIN_OFFER"):
				has_valid_port_num = True
			else:
				print "Error: " + msg["msg"]["msg_type"] + "\n"
				self.press_enter_to_continue()
				return
		
		#connect at received port
		self.port_num = msg["port_num"]
		self.connect_to_port(msg["port_num"])

		self.ready_for_recv = True

		print "=" * 60

	def request_join_environment(self):
		print '_' * 60
		print " " * 16, "Requesting Join Environment"
		print '_' * 60, "\n"

	#phase 1
		#send join request
		msg = json.dumps({"msg" : {"msg_type" : "JOIN_ENVIRONMENT_1"}})
		self.send_json(msg, self.sock)

		#wait for environment options
		msg = self.recv_json(self.sock)

		msg = json.loads(msg)

		if (msg["msg"]["msg_type"] == "NO_AVAILABLE_ENVIRONMENTS"):
			print "No available environments on server!"
			self.press_enter_to_continue()
			return
		elif (msg["msg"]["msg_type"] == "SEND_OPTIONS"):
			has_valid_port_num = True
		else:
			print "Error: " + msg["msg"]["msg_type"] + "\n"
			self.press_enter_to_continue()
			return

		#pick option
		option = self.pick_option(msg)

	#phase 2
		#send selected option
		msg = json.dumps({"msg" : {"msg_type" : "JOIN_ENVIRONMENT_2"}, "selected" : option})
		self.send_json(msg, self.sock)

		#wait for selected options port number (and eventually also confimation that selected option is still online)
		msg = self.recv_json(self.sock)

		msg = json.loads(msg)

		if (msg["msg"]["msg_type"] == "ENVIRONMENT_UNAVAILABLE"):
			print "Environment no longer available! Look for a new environment? (y/n)"
			while True:
				ans = raw_input()
				if (ans in ["y", "Y"]):
					self.request_join_environment()
					return
				elif (ans in ["n", "N"]):
					return
				else:
					print "Not a valid response please enter \'y\' or \'n\'"				
		elif (msg["msg"]["msg_type"] == "JOIN_OFFER"):
			pass
		else:
			print "Error: " + msg["msg"]["msg_type"] + "\n"
			self.press_enter_to_continue()
			returnif (debug):


		#connect to received port number
		self.port_num = msg["port_num"]
		self.connect_to_port(msg["port_num"], use_config=False)

		self.ready_for_recv = True

		print "=" * 60, "\n"

	def request_active_processes(self):
		print '_' * 60
		print " " * 16, "Requesting Active Processes"
		print '_' * 60
		print ""

		msg = json.dumps({"msg" : {"msg_type" : "GET_ACTIVE_ENVIRONMENTS"}})
		self.send_json(msg, self.sock)

		msg = self.recv_json(self.sock)

		msg = json.loads(msg)

		if (msg["msg"]["msg_type"] == "ACTIVE_PROCESSES"):
			pass
		else:
			print "Error: " + msg["msg"]["msg_type"] + "\n"
			self.press_enter_to_continue()
			return

		self.print_processes(msg["processes"])

		self.press_enter_to_continue()

	#######################################################################################################


	#######################################################################################################
											#HELPER FUNCTIONS#
	#######################################################################################################

	#send and receive functions
	def send_json(self, msg, sock):
		if (self.debug):
			print ">" * 20
			print "sending message..."
		sock.send_json(msg)
		if (self.debug):
			print "...message sent:\n", msg
			print ">" * 20, "\n"
	
	def recv_json(self, sock):
		if (self.debug):
			print "<" * 20
			print "waiting for message..."
		msg = sock.recv_json()
		if (self.debug):
			print "...message received:\n", msg
			print "<" * 20
		return msg

	def pick_new_port_num(self):
		if (self.manually_pick_port_num):
			self.manual_port_selection()
		else:
			self.automatic_port_selection()

	def manual_port_selection(self):
		print("\nPlease enter a port number or type 'scan' to sweep the host to find an available port and connect:")
		get_port_num = True
		x = None
		while (get_port_num):
			x = raw_input()
			get_port_num = False
			try:
				if (x == "scan"):
					self.manually_pick_port_num = False
					self.pick_new_port_num()
					return
				x = int(x)
				if (x < 0 or x > 65535):
					raise ValueError()
			except ValueError:
				get_port_num = True
				print ("Not a valid port number, enter a number between 0 and 65535:")
		self.send_json(json.dumps({"msg" : {"msg_type" : "CHECK_PORT"}, "port_num" : x}), self.sock)

		msg = self.recv_json(self.sock)

		msg = json.loads(msg)

		if (not msg["status"]):
			self.pick_new_port_num()
		else:
			self.port_num = x

	def automatic_port_selection(self):
		self.send_json(json.dumps({"msg" : {"msg_type" : "AUTO_SELECT_PORT"}}), self.sock)

		msg = self.recv_json(self.sock)

		msg = json.loads(msg)

		if (msg["msg"]["msg_type"] == "AUTO_SELECT_PORT"):if (debug):

			self.port_num = msg["port_num"]
		else:
			print "Error: " + msg["msg"]["msg_type"] + "\n"
			self.press_enter_to_continue()
			return

	def press_enter_to_continue(self):
		print '=' * 60
		print " " * 18, "Press Enter to continue"
		print '=' * 60

		raw_input()
	
	def print_processes(self, entries):
		table = list()
		for entry in entries:
			table = table + [[entry["env_owner"], entry["proc_pid"], entry["port_num"], datetime.datetime.fromtimestamp(float(entry["proc_create_time"])).strftime("%Y-%m-%d %H:%M:%S"), entry["env_desc"]]]
		
		print tabulate(table, headers=["Owner", "PID", "Port", "Create Time", "Description"], tablefmt="fancy_grid")

	def pick_option(self, msg, default_choice=None):
		title = msg["title"]
		options = msg["options"]

		if not default_choice == None and default_choice in options:
			return default_choice
if (debug):

		option, index = pick(options, title)

		return option

	def port_num_taken(self):
		print ("Port requested is unavailable!")
		if (self.manually_pick_port_num):
			self.port_num = self.manual_port_selection()
		else:
			s = socket.socket()		
			s.bind(('', 0))
			self.port_num = s.getsockname()[1]
			s.close()

		msg = json.dumps({"msg" : {"msg_type" : "CREATE_ENVIRONMENT"}, "port_num" : str(self.port_num)})
		self.send_json(msg, self.sock)

		self.ready_for_recv = True

	def connect_to_port(self, port_num, use_config=True):
		self.sock.disconnect("tcp://" + self.queue_host_address + ":" + self.queue_port_number)

		self.connected_to_queue = False
	    
		if (self.debug):
			print("\nconnecting...")
		self.sock.connect("tcp://" + self.queue_host_address + ":" + str(port_num))
		if (self.debug):
			print "...connected @", self.queue_host_address, ":", port_num, "\n"

		self.port_num = port_num

		if (use_config and self.environment_config):
			if (self.debug):
				print "sending with config..."
			self.sock.send_json(json.dumps({"msg" : {"msg_type" : "CLIENT_JOIN_WITH_CONFIG"}, "config" : self.environment_config}))
			if (self.debug):
				print "...sent with config\n"
		else:
			if (self.debug):
				print "sending without config..."
			self.sock.send_json(json.dumps({"msg" : {"msg_type" : "CLIENT_JOIN"}}))
			if (self.debug):
				print "...sent without config\n"

	#######################################################################################################

	
client = Three_D_World_Client()
client.load_config({
    # Procedural generation
	"environment_scene" : "ProceduralGeneration",
    "random_seed": 1, # Omit and it will just choose one at random. Chosen seeds are output into the log(under warning or log level).
    "should_use_standardized_size": False,
    "standardized_size": [1.0, 1.0, 1.0],
    "disabled_items": [], #["SQUIRL", "SNAIL", "STEGOSRS"], # A list of item names to not use, e.g. ["lamp", "bed"] would exclude files with the word "lamp" or "bed" in their file path
    "permitted_items": [], #["bed1", "sofa_blue", "lamp"],
    "complexity": 7500,
    "num_ceiling_lights": 4,
    "minimum_stacking_base_objects": 15,
    "minimum_objects_to_stack": 100,
    "room_width": 10.0,
    "room_height": 20.0,
    "room_length": 10.0,
    "wall_width": 1.0,
    "door_width": 1.5,
    "door_height": 3.0,
    "window_size_width": 5.0,
    "window_size_height": 5.0,
    "window_placement_height": 5.0,
    "window_spacing": 10.0,  # Average spacing between windows on walls
    "wall_trim_height": 0.5,
    "wall_trim_thickness": 0.01,
    "min_hallway_width": 5.0,
    "number_rooms": 1,
    "max_wall_twists": 3,
    "max_placement_attempts": 300,   # Maximum number of failed placements before we consider a room fully filled.
    "grid_size": 0.4,    # Determines how fine tuned a grid the objects are placed on during Proc. Gen. Smaller the number, the
})
client.run()
