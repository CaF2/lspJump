#	lspJump - a gedit plugin to browse code using the LSP protocol
#	Copyright (C) 2020  Florian Evaldsson

#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.

#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.

#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import re
import subprocess

import threading
import json
import time
import enum
import urllib.parse
from lspJump import settings

JSON_RPC_REQ_FORMAT = "Content-Length: {json_string_len}\r\n\r\n{json_string}"
LEN_HEADER = "Content-Length: "
TYPE_HEADER = "Content-Type: "

class SymbolKind(enum.Enum):
	File = 1
	Module = 2
	Namespace = 3
	Package = 4
	Class = 5
	Method = 6
	Property = 7
	Field = 8
	Constructor = 9
	Enum = 10
	Interface = 11
	Function = 12
	Variable = 13
	Constant = 14
	String = 15
	Number = 16
	Boolean = 17
	Array = 18
	Object = 19
	Key = 20
	Null = 21
	EnumMember = 22
	Struct = 23
	Event = 24
	Operator = 25
	TypeParameter = 26

class ErrorCodes(enum.Enum):
	# Defined by JSON RPC
	ParseError = -32700
	InvalidRequest = -32600
	MethodNotFound = -32601
	InvalidParams = -32602
	InternalError = -32603
	serverErrorStart = -32099
	serverErrorEnd = -32000
	ServerNotInitialized = -32002
	UnknownErrorCode = -32001

	# Defined by the protocol.
	RequestCancelled = -32800
	ContentModified = -32801

class MyEncoder(json.JSONEncoder): 
	def default(self, o): # pylint: disable=E0202
		return o.__dict__ 

class JsonRpcEndpoint(object):
	def __init__(self, stdin, stdout):
		self.stdin = stdin
		self.stdout = stdout
		self.read_lock = threading.Lock() 
		self.write_lock = threading.Lock() 

	@staticmethod
	def __add_header(json_string):
		return JSON_RPC_REQ_FORMAT.format(json_string_len=len(json_string), json_string=json_string)

	def send_request(self, message):
		json_string = json.dumps(message, cls=MyEncoder)
		jsonrpc_req = self.__add_header(json_string)
		with self.write_lock:
			write_data=jsonrpc_req.encode()
			print("OUT::"+str(write_data))
			self.stdin.write(write_data)
			self.stdin.flush()

	def recv_response(self):
		with self.read_lock:
			message_size = None
			while True:
				#read header
				line = self.stdout.readline()
				if not line:
					# server quit
					return None
				line = line.decode("utf-8")
				if not line.endswith("\r\n"):
					raise ResponseError(ErrorCodes.ParseError, "Bad header: missing newline")
				#remove the "\r\n"
				line = line[:-2]
				if line == "":
					# done with the headers
					break
				elif line.startswith(LEN_HEADER):
					line = line[len(LEN_HEADER):]
					if not line.isdigit():
						raise ResponseError(ErrorCodes.ParseError, "Bad header: size is not int")
					message_size = int(line)
				elif line.startswith(TYPE_HEADER):
					# nothing todo with type for now.
					pass
				else:
					raise ResponseError(ErrorCodes.ParseError, "Bad header: unkown header")
			if not message_size:
				raise ResponseError(ErrorCodes.ParseError, "Bad header: missing size")

			jsonrpc_res = self.stdout.read(message_size).decode("utf-8")
			
			print("IN::"+jsonrpc_res)
			return json.loads(jsonrpc_res)

def to_type(o, new_type):
	if new_type == type(o):
		return o
	else:
		return new_type(**o)

class ResponseError(Exception):
	def __init__(self, code, message, data = None):
		self.code = code
		self.message = message
		if data:
			self.data = data

class LspEndpoint(threading.Thread):
	def __init__(self, json_rpc_endpoint, method_callbacks={}, notify_callbacks={}):
		threading.Thread.__init__(self)
		self.json_rpc_endpoint = json_rpc_endpoint
		self.notify_callbacks = notify_callbacks
		self.method_callbacks = method_callbacks
		self.event_dict = {}
		self.response_dict = {}
		self.next_id = 0
		self.shutdown_flag = False

	def handle_result(self, rpc_id, result, error):
		self.response_dict[rpc_id] = (result, error)
		cond = self.event_dict[rpc_id]
		cond.acquire()
		cond.notify()
		cond.release()

	def stop(self):
		self.shutdown_flag = True

	def run(self):
		while not self.shutdown_flag:
			try:
				jsonrpc_message = self.json_rpc_endpoint.recv_response()
				if jsonrpc_message is None:
					print("server quit")
					break
				method = jsonrpc_message.get("method")
				result = jsonrpc_message.get("result")
				error = jsonrpc_message.get("error")
				rpc_id = jsonrpc_message.get("id")
				params = jsonrpc_message.get("params")

				if method:
					if rpc_id:
						# a call for method
						if method not in self.method_callbacks:
							raise ResponseError(ErrorCodes.MethodNotFound, "Method not found: {method}".format(method=method))
						result = self.method_callbacks[method](params)
						self.send_response(rpc_id, result, None)
					else:
						# a call for notify
						if method not in self.notify_callbacks:
							# Have nothing to do with this.
							print("Notify method not found: {method}.".format(method=method))
						else:
							self.notify_callbacks[method](params)
				else:
					self.handle_result(rpc_id, result, error)
			except ResponseError as e:
				self.send_response(rpc_id, None, e)

	def send_response(self, id, result, error):
		message_dict = {}
		message_dict["jsonrpc"] = "2.0"
		message_dict["id"] = id
		if result:
			message_dict["result"] = result
		if error:
			message_dict["error"] = error
		self.json_rpc_endpoint.send_request(message_dict)

	def send_message(self, method_name, params, id = None):
		message_dict = {}
		message_dict["jsonrpc"] = "2.0"
		if id is not None:
			message_dict["id"] = id
		message_dict["method"] = method_name
		message_dict["params"] = params
		self.json_rpc_endpoint.send_request(message_dict)

	def call_method(self, method_name, **kwargs):
		current_id = self.next_id
		self.next_id += 1
		cond = threading.Condition()
		self.event_dict[current_id] = cond

		cond.acquire()
		self.send_message(method_name, kwargs, current_id)
		if self.shutdown_flag:
			return None

		cond.wait()
		cond.release()

		self.event_dict.pop(current_id)
		result, error = self.response_dict.pop(current_id)
		if error:
			raise ResponseError(error.get("code"), error.get("message"), error.get("data"))
		return result

	def send_notification(self, method_name, **kwargs):
		self.send_message(method_name, kwargs)
		
	def initialize(self, processId, rootPath, rootUri, initializationOptions, capabilities, trace, workspaceFolders):
		if self.native_id is None:
			self.start()
		return self.call_method("initialize", processId=processId, rootPath=rootPath, rootUri=rootUri, initializationOptions=initializationOptions, capabilities=capabilities, trace=trace, workspaceFolders=workspaceFolders)
	
	def shutdown(self):
		self.stop()
		return self.call_method("shutdown")
		
class ReadPipe(threading.Thread):
	def __init__(self, pipe):
		threading.Thread.__init__(self)
		self.pipe = pipe

	def run(self):
		line = self.pipe.readline().decode('utf-8')
		while line:
			print(line)
			line = self.pipe.readline().decode('utf-8')

def workspace_configuration_function(params):
	print(params)

class LspNavigator:
	def __init__(self):
		self.process = subprocess.Popen(settings.LSP_BIN.strip().split(" "), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		read_pipe = ReadPipe(self.process.stderr)
		read_pipe.start()
		json_rpc_endpoint = JsonRpcEndpoint(self.process.stdin, self.process.stdout)
		# To work with socket: sock_fd = sock.makefile()
		method_callbacks={"workspace_configuration":workspace_configuration_function,"window/workDoneProgress/create":workspace_configuration_function}
		notify_callbacks={"$/progress":workspace_configuration_function}

		self.lsp_endpoint = LspEndpoint(json_rpc_endpoint,method_callbacks,notify_callbacks)

		# file_path = "/home/flev/dev/c++/qsound/sound.cpp"
		
	#	ugly
		time.sleep(0.1)
	#	self.lsp_endpoint.shutdown()
	#	self.lsp_endpoint.send_notification("exit")
		
		self._initialize_project_path(settings.PROJECT_PATH)
		
	def getDefinitions(self, doc, identifier):
#		realpath = os.path.realpath(doc.get_location().get_path())
#		doc_path = os.path.dirname(realpath)

#		doc_uri = doc.get_uri_for_display()
		doc_uri = doc.get_file().get_location().get_path()
		
		doc_curr_line=identifier.get_line()
		doc_curr_offset=identifier.get_line_offset()
		
		print("DOC1::")
		print(doc)
		print("identifier::")
		print(identifier)
		print("Line::"+str(doc_curr_line)+" Offset::"+str(doc_curr_offset)+" File:"+doc_uri)
#		yield from self._call_global(doc, identifier, '-x')

		uri = "file://" + doc_uri
		text = open(doc_uri, "r").read()
		languageId = settings.LSP_LANGUAGES
		version = 1
		
		text_doc={"uri":uri, "languageId":languageId, "version":version, "text":text}
		result=self.lsp_endpoint.send_notification("textDocument/didOpen", textDocument=text_doc)
		
		def_s=self.lsp_endpoint.call_method("textDocument/definition", textDocument={"uri":"file://"+doc_uri}, position={"line":doc_curr_line,"character":doc_curr_offset})
		
		try:
			urlp = urllib.parse.urlparse(def_s[0]['uri'])
			urlps = urllib.parse.unquote(os.path.abspath(os.path.join(urlp.netloc, urlp.path)))
			print(def_s)
			print("File:"+urlps+" From[Line:"+str(def_s[0]['range']['start']['line']+1)+" Character:"+str(def_s[0]['range']['start']['character'])+"]"+" To[Line:"+str(def_s[0]['range']['end']['line']+1)+" Character:"+str(def_s[0]['range']['end']['character'])+"]")
			
			return [[urlps, int(def_s[0]['range']['start']['line'])+1, int(def_s[0]['range']['start']['character']), def_s[0]['uri']]]
		except IndexError:
			return None
	def getReferences(self, doc, identifier):
#		doc_uri = doc.get_uri_for_display()
		doc_uri = doc.get_file().get_location().get_path()
		
		doc_curr_line=identifier.get_line()
		doc_curr_offset=identifier.get_line_offset()

		uri = "file://" + doc_uri
		text = open(doc_uri, "r").read()
		languageId = settings.LSP_LANGUAGES
		version = 1
		
		text_doc={"uri":uri, "languageId":languageId, "version":version, "text":text}
		result=self.lsp_endpoint.send_notification("textDocument/didOpen", textDocument=text_doc)
		
		def_s=self.lsp_endpoint.call_method("textDocument/references", textDocument={"uri":"file://"+doc_uri}, position={"line":doc_curr_line,"character":doc_curr_offset})
		
		retval=[]
		for def_itr in def_s:
			urlp = urllib.parse.urlparse(def_itr['uri'])
			urlps = urllib.parse.unquote(os.path.abspath(os.path.join(urlp.netloc, urlp.path)))
			# print(def_s)
			# print("File:"+urlps+" From[Line:"+str(def_s[0]['range']['start']['line']+1)+" Character:"+str(def_s[0]['range']['start']['character'])+"]"+" To[Line:"+str(def_s[0]['range']['end']['line']+1)+" Character:"+str(def_s[0]['range']['end']['character'])+"]")
			retval.append([urlps, int(def_itr['range']['start']['line'])+1, int(def_itr['range']['start']['character']), def_itr['uri']])
			
		return retval

	def _initialize_project_path(self, path):
		capabilities = json.loads(settings.LSP_SETTINGS)
		root_uri="file://"+path
		# root_uri = 'file:///home/flev/dev/c++/qsound/'
		workspace_folders = [{'name': 'python-lsp', 'uri': root_uri}]
		self.lsp_endpoint.initialize(self.process.pid, None, root_uri, None, capabilities, "off", workspace_folders)
		self.lsp_endpoint.send_notification("initialized")
