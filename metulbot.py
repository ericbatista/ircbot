import sys
import socket
import string
import time
import datetime
import os
import random
import subprocess
from bs4 import BeautifulSoup
import urllib
from urllib.request import urlopen
from urllib.request import Request
from urllib.parse import urlencode
import json as m_json

#metulbot version 1.0

argv_flag = {'-c':None, '-h':None, '-p':None, '-k':None, '-n':None}
flag_help = {'-c':'channel ',
			 '-h':'host',
			 '-p':'port',
			 '-k':'character to call on bot',
			 '-n':'bot name'}
show_help = 'Icorrect argument, "{} -help" for help'.format(sys.argv[0])

def cmd_arg():
	'''return IrcBot object based on values supplied by sys.argv'''
	arguments = sys.argv
	if len(sys.argv) == 1:
		connect = IrcBot()
	elif len(sys.argv) == 2:
		if sys.argv[1] == '-help':
			print('')
			for key in flag_help.keys():
				print('\t{0} -- {1}'.format(key, flag_help[key]))
			sys.exit()
		else:
			print(show_help)
	else:
		h, p, c , k, n = None, None, None, None, None
		for flag in argv_flag.keys():
			for user_flag in arguments:
				if flag == user_flag:
					index = arguments.index(user_flag)
					value = arguments[index + 1]
					argv_flag[flag] = value
		connect = IrcBot(h=argv_flag['-h'], p=argv_flag['-p'], c=argv_flag['-c'],
						  k=argv_flag['-k'],n=argv_flag['-n'])
	return connect

class IrcBot:
	def __init__(self, h=None, p=None, c=None, k=None, n=None):
		'''adjust values based on sys.argv'''
		if h is None:
			self.host = "irc.freenode.net"
		else:
			self.host = h
		if p is None:
			self.port = 6667
		else:
			self.port = p
		if c is None:
			self.channel = '#robgraves'
		else:
			if c[:1] != '#':
				c = '#'+c
			self.channel = c
		if k is None:
			self.contact = '.'
		else:
			self.contact = k
		if n is None: 
			self.nick = "metulbot"
			self.ident = "metulbot"
			self.realname = "metulbot"
		else:
			self.nick = n
			self.ident = n
			self.realname = n

		self.list_cmds = { #functions with args need to be added to commands
			'help':(lambda:self.help()),
			'epoch':lambda:self.epoch(),
			'time':lambda:self.time(),
			'calc':lambda:self.calc(),
			'seen':lambda:self.seen(),
			'settings':lambda:self.settings(),
			'coin':lambda:self.coin(),
			'google':lambda:self.google(),
			'codepad':lambda:self.codepad(),
			'src':lambda:self.source(),
			'insult':lambda:self.insult(),
			'ip':lambda:self.iptrace(),
			'binary':lambda:self.binary()

			}
		
		self.op = ['metulburr','Awesome-O', 'robgraves','corp769',
				  'metulburr1', 'robgravesny', 'Optichip', 'Craps_Dealer']
		self.data = None
		self.operation = None
		self.addrname = None
		self.username = None
		self.text = None
		self.timer= None
		self.last_seen = {} #{'metulburr':time.time()}
		self.last_said = {}
		self.startup = True
		self.show_title = False
		self.owner = 'metulburr'
		self.copy_text = False
		self.giveop = True
		self.source_file = os.path.realpath(__file__)
		self.announce = True

		
		self.sock = self.irc_conn()
		self.wait_event()

		
	def irc_conn(self):
		'''connect to server/port channel, send nick/user '''
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		print('connecting to "{0}/{1}"'.format(self.host, self.port))
		sock.connect((self.host, self.port))
		print('sending NICK "{}"'.format(self.nick))
		sock.send("NICK {0}\r\n".format(self.nick).encode())
		sock.send("USER {0} {0} bla :{0}\r\n".format(
			self.ident,self.host, self.realname).encode())
		print('joining {}'.format(self.channel))
		sock.send(str.encode('JOIN '+self.channel+'\n'))
		return sock
	
	def say(self, string):
		'''send string to irc channel with PRIVMSG '''
		if len(str(string)) > 350: #protect from kicked for flooding
			self.sock.send('PRIVMSG {0} :{1}\r\n'.format(self.channel, string[:350]).encode())
			self.sock.send('PRIVMSG {0} :{1}\r\n'.format(self.channel, string[350:600]).encode())
		else:
			self.sock.send('PRIVMSG {0} :{1}\r\n'.format(self.channel, string).encode())
	
	def send_operation(self, operation=None, msg=None, username=None):
		'''send operation to irc with operation arg'''
		if msg is None:
			#send ping pong operation
			self.sock.send('{0} {1}\r\n'.format(operation, self.channel).encode())
		elif msg != None:
			#send private msg to one username
			self.sock.send('PRIVMSG {0} :{1}\r\n'.format(self.username,msg).encode())
	def get_user(self, stringer):
		start = stringer.find('~')
		end = stringer.find('@')
		user = stringer[start +1:end]
		return user
		
	def format_data(self):
		'''get data from server:
		self.operation = EXAMPLE: PRIVMSG, JOIN, QUIT
		self.text = what each username says
		self.addrname = the first name on address
		self.username = the username
		self.timer = time 
		'''
		try:
			data=self.sock.recv(1042) #recieve server messages
		except socket.error:
			self.rejoin()
		try:
			data = data.decode('utf-8') #data decoded
		except:
			return
		self.data = data.strip('\n\r') #data stripped
		try:
			self.operation = data.split()[1]
			textlist = data.split()[3:]
			text = ' '.join(textlist)
			self.text = text[1:]
			self.addrname = self.get_user(data) 
			self.username = data[:data.find('!')][1:]
			self.last_seen[self.username] = datetime.datetime.now().replace(microsecond=0)
			if self.operation == 'PRIVMSG' or self.operation == 'ACTION':
				if self.text[0] == '\x01':
					action = self.text[1:-1].split()[1:]
					action = ' '.join(action)
					self.last_said[self.username] = '*{} {}'.format(self.username, action)
				else:	
					self.last_said[self.username] = self.text
		except IndexError:
			pass
		self.timer = time.asctime(time.localtime(time.time()))
		
	def print_console(self):
		'''print to console '''
		#print('{0} ({1}): {2}'.format(self.username, self.timer, self.text))
		try:
			if self.data[:4] == 'PING':
				pass
			else:
				print(self.data)
		except:
			pass
		
	def ping_pong(self):
		'''server ping pong handling'''
		try:
			if self.data[:4] == 'PING':
				self.send_operation('PONG')
		except TypeError: #startup data
			pass
		
	def upon_join(self):
		'''when someone joins the channel'''
		if self.operation == 'JOIN':
			if self.username == self.nick: #get past start up data
				self.startup = False
			#give ops on joining
			elif self.username in self.op:
				if self.giveop is True:
					self.sock.send('MODE {0} +o {1}\r\n'.format(self.channel, self.username).encode())
			if self.announce is True:
				if self.username != self.nick:
					self.say('Hello, {} my commands are listed in {}help'.format(self.username, self.contact))
	def upon_leave(self):
		'''when someone leaves the channel'''
		if self.operation == 'QUIT' or self.operation == 'PART':
			pass

	def check_for_url(self):
		'''check url is valid and get title of url'''
		def adjust(u):
			if u[:3] == 'www':
				user_text = 'http://' + u
			elif u[:3] == 'www' or u[:4] == 'http':
				user_text = u
			#else:
				#user_text = 'http://www.' + u
			return user_text

		counter = 1
		for url in self.text.split():
			try:
				URL = adjust(url)
				u = urlopen(URL)
				soup = BeautifulSoup(u)
				title = str(soup.title.string)
				title = title.lstrip()
				if counter <= 2: #restrain amount of times title is display if numerous urls
					self.say('Title: {}'.format(title))
				counter += 1
			except:
				pass

	def rejoin(self):
		'''rejoin when kicked'''
		if self.operation == 'KICK':
			if (self.text.split()[-1][1:]) == self.nick:
				self.sock.send(str.encode('JOIN '+self.channel+'\n'))
				self.insult()
		else:
			self.sock.send(str.encode('JOIN '+self.channel+'\n'))

		
	def wait_event(self):
		'''main while loop'''
		while True:
			self.ping_pong()
			self.format_data() 
			self.print_console()
			self.upon_join()
			self.upon_leave()
			self.check_cmd()
			self.rejoin()

			if self.startup is False:
				if self.show_title is True:
					self.check_for_url()
				if self.copy_text is True:
					self.copy()

			
	def not_cmd(self, cmd):
		'''string for not a command response'''
		return '{0}: "{1}" is not one of my commands'.format(self.username, cmd)

	def check_cmd(self):
		'''check if contact is first char of text and send in cmd and its args to self.commands'''
		if self.text[:1] == self.contact:
			returner = self.commands(self.text.split()[0][1:], self.text.split()[1:])
			if returner != None:
				self.say(returner)

	def commands(self, cmd, *args):
		'''commands function for running cmds '''
		try:
			arg1 = args[0][0]
		except IndexError:
			arg1 = ''
		try:
			arg2 = args[0][1]
		except IndexError:
			arg2 = ''

		if cmd in self.list_cmds:
			if not arg1: #if no arguments
				self.list_cmds[cmd]()
			else: #argument with function, run function directly
				if cmd == 'help':# and arg1 in self.list_cmds.keys():
					self.help(arg1)
				elif cmd == 'epoch':
					self.epoch(arg1)
				elif cmd == 'calc':
					self.calc(args)
				elif cmd == 'seen':
					self.seen(arg1)
				elif cmd == 'settings':
					self.settings(arg1, arg2)
				elif cmd == 'google':
					self.google(args)
				elif cmd == 'codepad':
					self.codepad(args)
				elif cmd == 'ip':
					self.iptrace(arg1)
				elif cmd == 'binary':
					self.binary(' '.join(args[0]))

			#self.say('cmd is: {}'.format(cmd))
			#self.say('first two args are: {0} {1}'.format(arg1, arg2))
		elif cmd != '':
			self.say(self.not_cmd(cmd))
			
	def help(self, arg=None):
		'''display help string for commands and how to use them'''
		helper = '{0}: {1}help  --show all commands'.format(self.username,self.contact)
		epoch = '{0}: {1}epoch [epoch number]  --display epoch time in human readable format, [now] --display current epoch time'.format(self.username,self.contact)
		timer = '{0}: {1}time  --display current time'.format(self.username,self.contact)
		calc = '{0}: {1}calc [operand] [operator] [operand] --calculator, operators [+,-,/,*,%,**] Must have space between operands and operator'.format(self.username,self.contact)
		seen = '{0}: {1}seen [username]  --show user\'s last activity and statement'.format(self.username,self.contact)
		pythons = '{0}: {1}python [one line code]  --execute one liner python code'.format(self.username,self.contact)
		google = '{0}: {1}google [search] --return top 4 links from google search'.format(self.username,self.contact)
		codepad = '{0}: {1}codepad [filepath] --copy filepath to codepad and display url'.format(self.username,self.contact)
		srcs = '{0}: {1}src  --display {2}\'s source code'.format(self.username,self.contact, self.nick)
		insult = '{0}: {1}insult  --give an insult'.format(self.username,self.contact)
		binary = '{0}: {1}binary [text] --convert text to binary'.format(self.username,self.contact)
		ip = '{0}: {1}ip [ip address]  --display ip info [available searches today]["country_code country_name state city postal_code", "latitude, longitude", "ISP", "localtime"]'.format(self.username,self.contact)
		
		settings = '{0}: {1}settings [KEY] [VALUE] --change settings, options:[title:(True,False), copy:(True,False), giveop:(True,False), join_announce(True,False)]'.format(self.username,self.contact)

		if arg is None:
			tmp = []
			for key in self.list_cmds.keys():
				tmp.append(key)
			self.say('{0}help [cmd] for desc. cmds = {1}'.format(self.contact,tmp))
		else:
			if arg == 'help':
				self.say(helper)
			if arg == 'epoch':
				self.say(epoch)
			if arg == 'time':
				self.say(timer)
			if arg == 'calc':
				self.say(calc)
			if arg == 'seen':
				self.say(seen)
			if arg == 'settings':
				self.say(settings)
			if arg == 'google':
				self.say(google)
			if arg == 'codepad':
				self.say(codepad)
			if arg == 'src':
				self.say(srcs)
			if arg == 'insult':
				self.say(insult)
			if arg == 'ip':
				self.say(ip)
			if arg == 'binary':
				self.say(binary)


	def epoch(self, num=None):
		'''display epoch time based on arg'''
		if num is None:
			self.help('epoch')
		else:
			if str(num) == 'now':
				self.say(time.time())
			else:
				try:
					time_format = time.asctime(time.localtime(float(num)))
					self.say(time_format)
				except ValueError:
					self.say('epoch time is out of range')

	def time(self):
		'''display current time'''
		self.say(time.asctime(time.localtime(time.time())))

	def calc(self, args=None):
		'''calculator'''
		def cal():
			op1 = self.text.split()[1]
			op = self.text.split()[2]
			op2 = self.text.split()[3]
			#op1, op, op2 = args[0][0]
			#self.say('{} {} {}'.format(op1,op,op2))

			op1 =float(op1)
			op2 = float(op2)
			if op == '+':
				ans = op1+op2
			elif op == '-':
				ans = op1-op2
			elif op == '*':
				ans = op1*op2
			elif op == '/':
				ans = op1/op2
			elif op == '%':
				ans = op1%op2
			elif op == '**':
				ans = op1**op2
			return ans
		if args is None:
			self.help('calc')
			return

		if len(self.text.split()) != 4:
			self.say('incorrect arguments')
			return
		try:
			self.say('{}: {}'.format(self.username,str(cal())))
		except:
			self.say('incorrect arguments')




	def seen(self, name=None):
		'''display last seen person's time and statement'''
		if name is None:
			self.help('seen')
		else:
			try:
				a = self.last_seen[name]
				b = datetime.datetime.now().replace(microsecond=0)
				diff = str(b - a)
				diff = diff.split(':')
				diff = '{} hr {} min {} sec'.format(diff[0], diff[1], diff[2])

				said = ''.join(name + '\'s last statement: ' + self.last_said[name])
				self.say('{} was last seen {} ago: {}'.format(
					name, diff, said ))

			except KeyError:
				self.say('{} has had no activity since I have been on'.format(name))

	def settings(self, arg1=None, arg2=None):
		'''settings function to allow change without restarting bot'''
		owner_only = '{}: Only the owner {} has powers to change setting'.format(self.username,self.owner)
		
		if arg1 is None or arg2 is None:
			self.help('settings')
		else:
			if arg1 == 'title':
				if arg2.lower() == 'false': #arg2 == 'True':
					self.show_title = False
					self.say('show_title set to {}'.format('False'))
				elif arg2.lower() == 'true':
					self.show_title = True
					self.say('show_title set to {}'.format('True'))
					#self.show_title = eval(arg2.strip(),{'__builtins__':None})
			elif arg1 == 'copy':
				if self.username == self.owner:
					if arg2.lower() == 'false':# or arg2 == 'True':
						self.copy_text = False
						self.say('copy set to {}'.format('False'))
					elif arg2.lower() == 'true':
						self.copy_text = True
						self.say('copy set to {}'.format('True'))
				else:
					self.say(owner_only)

			elif arg1 == 'giveop':
				if self.username in self.op:
					if arg2.lower() == 'false':
						self.giveop = False
						self.say('give ops set to {}'.format('False'))
					elif arg2.lower() == 'true':
						self.giveop = True
						self.say('give ops set to {}'.format('True'))
				else:
					self.say('You do not have ops to change this settings')
			elif arg1 == 'join_announce':
				if arg2.lower() == 'false':
					self.announce = False
					self.say('join announcement set to {}'.format('False'))
				elif arg2.lower() == 'true':
					self.announce = True
					self.say('join announcement set to {}'.format('True'))



	def copy(self):
		'''copy text from channel to text file'''
		if self.data[:4] == 'PING':
			return
		path = os.environ['HOME'] + os.sep + 'Documents' + os.sep + 'irccopytext.txt'
		if not os.path.exists(path):
			filewrite = 'w'
		else:
			filewrite = 'a'
		filer = open(path, filewrite)
		textdata = '{} {} {} {}'.format(self.timer, self.channel, self.username, self.text)
		try:
			filer.write(textdata +'\n')
		except UnicodeEncodeError:
			filer.write('{} {} {} {}'.format(self.timer, self.channel, self.username, 'UnicodeEncodeError in text\n'))
		filer.close()

	def coin(self):
		'''give random coin flip'''
		coin_side = ['tails', 'heads']
		self.say('{}: {}'.format(self.username, random.choice(coin_side)))

	def google(self, string=None):
		'''return top 4 links from a google search'''
		if string is None:
			self.help('google')
			return
		query = urlencode({'q':string})
		response = urlopen('http://ajax.googleapis.com/ajax/services/search/web?v=1.0&' + query).read()
		json = m_json.loads(bytes.decode(response))
		results = json['responseData']['results']
		lister = []
		for result in results:
			title = result['title']
			url = result['url']   # was URL in the original and that threw a name error exception
			lister.append(url)
		self.say('{}: {}'.format(self.username,lister))

	def codepad(self, path=None):
		'''codepad a file and display link '''
		if self.addrname != self.owner or self.username != self.owner:
			self.say('You do not have permission')
			return
		if path is None:
			self.help('codepad')
			return
		url = 'http://codepad.org'
		try:
			content=open(path[0][0]).read()
		except IOError:
			self.say('No such file or unable to open file')
			return

		values = {'lang' : 'Plain Text',
				  'code' : content,
				  'submit':'Submit'}

		data = urlencode(values).encode("ascii")
		req = Request(url, data)
		try:
			response = urlopen(req)
		except urllib.error.HTTPError:
			self.say('HTTP Error 500: Internal Server Error')
			return
		the_page = response.read().decode()
		for href in the_page.split("</a>"):
			if "Link:" in href:
				ind=href.index('Link:')
				found = href[ind+5:]
				for i in found.split('">'):
					if '<a href=' in i:
						self.say("{}: {}".format(self.username, i.replace('<a href="',"").strip()))
						return

	def source(self):
		'''display current source code from codepad link'''
		self.codepad(([self.source_file],))

	def insult(self):
		'''return a random line form insults'''
		filer = open('/home/metulburr/Documents/botfight.txt')
		lines = filer.readlines()
		line = random.choice(lines)
		self.say(line)
		
	def iptrace(self, address=None):
		def string_search(line, string):
			string_len = len(string)
			return line[line.find(string)+string_len:].strip()
			
		if address is None:
			self.help('ip')
			return
		else:
			#bash_cmd = "lynx -dump http://www.ip-adress.com/ip_tracer/?QRY={}|grep address|egrep 'city|state|country'|awk '{print $3,$4,$5,$6,$7,$8}'|sed 's\ip address flag \\'|sed 's\My\\'".format(address)
			#proc = subprocess.Popen(bash_cmd.split(),stdout=subprocess.PIPE)
			test = "lynx -dump http://www.ip-adress.com/ip_tracer/?QRY={}".format(address)
			#run_bash = './iptrace {}'.format(address)
			proc = subprocess.Popen(test.split(), stdout=subprocess.PIPE)
			stdout = proc.communicate()[0].decode()
			#print(stdout)
			
			country_code = 'Unknown'
			country_name = 'Unknown'
			state_name = 'Unknown'
			city_name = 'Unknown'
			postcode = 'Unknown'
			lat = 'Unknown'
			lon = 'Unknown'
			isp = 'Unknown'
			localtime = 'Unknown'
			lookups = 'Unknown'
			 
			for line in stdout.split('\n'):
				if 'IP country code:' in line:
					country_code = string_search(line, ':')
				elif 'IP address country:' in line:
					country_name  = string_search(line, 'flag')
				elif 'IP address state:' in line:
					state_name = string_search(line, ':')
				elif 'IP address city:' in line:
					city_name = string_search(line, ':')
				elif 'IP postcode:' in line:
					postcode = string_search(line, ':')
					
				elif 'IP address latitude:' in line:
					lat = string_search(line, ':')
				elif 'IP address longitude:' in line:
					lon = string_search(line, ':')
					
				elif 'ISP [[6]?]' in line or 'IP [[6]?]:' in line:
					isp = string_search(line, ':')
				elif 'Local time' in line:
					localtime = string_search(line, ':')
					
				elif 'You reached your limit of 50 lookup queries per day' in line:
					self.say('You reached your limit of 50 lookup queries per day')
					return
				elif 'Remaining lookups today:' in line:
					#self.say(line.split())
					lookups = line.split()[3]
					#self.say('lookups left: {}'.format(lookups))

			lister = []
			lister.append('{} {} {} {} {}'.format(country_code, country_name, state_name, city_name, postcode))
			lister.append('latitude: {}, longitude: {}'.format(lat,lon))
			lister.append('ISP: {}'.format(isp))
			lister.append('localtime: {}'.format(localtime))
			self.say('{} {}: {}'.format(self.username, lookups, lister))
			
	def binary(self, args=None):
		if not args:
			return
		else:
			binary_ = ''.join(['%08d'%int(bin(ord(i))[2:]) for i in str(args)])
			self.say(binary_)


	def convert(self, arg1=None, arg2=None):
		pass



class Convert: #http://www.intuitivetransport.com/library/trade/metric.htm
	def __init__(self):
		#1 metric is equal to ___ us
		#LENGTH
		self.kilometer_to_mile = 0.62137 #mile
		self.meter_to_feet = 3.2808 #feet
		self.centimeter_to_inch = 0.3937 #inch
		self.mile_to_kilometer = 1.6093 #kilometer
		self.foot_to_meter = 0.3048 #meter
		self.inch_to_centimeter = 2.54 #centimeters

		#WEIGHT
		self.kilogram_to_lb = 2.2046 #lbs.
		self.gram_to_ounce = 0.0353 #ounce
		self.short_ton_to_kilos = 907.1847# kilos
		self.lb_to_kilos = 0.4536 #kilos
		self.ounce_to_gram = 28.3495 #grams

		#VOLUME
		self.gallon_to_liter = 3.7853 #liters





if __name__ == '__main__':
	connect = cmd_arg()
	try:
		print('channel: ', connect.channel)
		print('port: ', connect.port)
		print('host: ', connect.host)
		print('contact: ', connect.contact)
	except NameError:
		print(show_help)




