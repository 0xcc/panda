#-*- coding:utf-8 -*-
import json
import os
import sys
import traceback
import threading
import mimetypes

from functools import wraps
if sys.version < '3':
	from urllib import quote
	import sys
	reload(sys)
	sys.setdefaultencoding('utf8')
else:
	from urllib.parse import quote


from .server import ServerAdapter
from .server import WSGIRefServer
from .wrappers import Request, Response
from .router import Router, RouterException
from .template import Template
from .util import Stack

class PandaException(Exception):
	def __init__(self, code, response, server_handler, debug=False):
		self._debug = debug
		self._response = response
		self._response.set_status(code)
		self._server_handler = server_handler

	def __call__(self):
		body = self._response.status
		if self._debug:
			body = '<br>'.join(
				[self._response.status, traceback.format_exc().replace('\n', '<br>')])
		self._response.set_body(body)
		self._server_handler(self._response.status, self._response.headerlist)
		return [self._response.body]

class Panda(object):
	def __init__(self, pkg_name, templates='templates', static='static'):
		self._router=Router()

		self._request = Request()
		self._response = Response(None)

		#template
		self.package_name = pkg_name
		#app root
		self.root_path=self._get_package_path(self.package_name).replace('\\', '\\\\')

		#静态文件相关
		self.static_folder=static
		self.abspath=None
		self.modified=None
		self.static_url_cache={}

		self._session=self._request.cookies

		#server handler
		self._server_handler = None

		#debug
		self.debug=False

		#config
		self.config = {}
		#self.config.setdefault('DATABASE_NAME', 'lunar.db')

		global app_stack
		app_stack.push(self)

	def _get_package_path(self,name):
		#返回pkg在的绝对路径
		try:
			return os.path.abspath(os.path.dirname(sys.modules[name].__file__))
		except (KeyError,AttributeError):
			return os.getcwd()

	def route(self,path=None,methods=['GET']):
		if path is None:
			raise RouterException()
		methods=[m.upper() for m in methods]

		def wrapper(fn):
			self._router.register(path,fn,methods)
			return fn
		return wrapper

	@property
	def session(self):
	    return self._session
	
	def run(self,server=WSGIRefServer,host='localhost',port=8000,debug=False):
		self.debug=debug
		if isinstance(server,type) and issubclass(server,ServerAdapter):
			server=server(host=host,port=port)

		if not isinstance(server,ServerAdapter):
			raise RuntimeError("Server must be a subclass of ServerAdapter.")

		print("Running on %s:%s" % (host, port))
		try:
			server.run(self)
		except KeyboardInterrupt:
			pass

	def jsonify(self, *args, **kwargs):
		response =Response(body=json.dumps(dict(*args,**kwargs)),code=200)
		response.set_content_type('application/json')
		return response

	def render(self,file,**context):
		raise RuntimeError("not implemented")

	def not_found(self):
		response=Response(body='<h1>404 Not Found</h1>',code=404)
		return response

	def not_modified(self):
		response=Response('',code=304)
		del (response.headers['Content-Type'])
		return response

	def redirect(self,location,code=302):
		response = Response(body='<p>Redirecting...</p>', code=code)
		response.headers['Location'] = location
		return response

	def url_for(self,fn,filename=None,**kwargs):
		if fn==self.static_folder and filename:
			if filename in self.static_url_cache.keys():
				return self.static_url_cache[filename]
			else:
				url=self.construct_url(filename)
				self.static_url_cache[filename]=url
				return url

		if kwargs:
			return self._router.url_for(fn,**kwargs)
		return self._router.url_for(fn)

	def construct_url(self,filename):
		environ = self._request.headers
		url=environ['wsgi.url_scheme']+'://'
		if environ.get('HTTP_HOST'):
			url+=environ['HTTP_HOST']
		else:
			url+=environ['SERVER_NAME']

			if environ['wsgi.url_scheme'] == 'https':
				if environ['SERVER_PORT'] != '443':
					url+=':'+environ['SERVER_PORT']
			else:
				if environ['SERVER_PORT'] != '80':
					url += ':' + environ['SERVER_PORT']

		url += quote(environ.get('SCRIPT_NAME', ''))
		if environ.get('QUERY_STRING'):
			url += '?' + environ['QUERY_STRING']

		url += '/' + '/'.join([self.static_folder, filename])
		return url

	@property
	def request(self):
	    return self._request

	@property
	def response(self):
	    return self._response

	def get_content_type(self):
		fallback_content_type='text/plain'
		mime_type=mimetypes.guess_type(self.abspath)[0]
		return mime_type if mime_type else fallback_content_type

	def get_modified_time(self):
		stats=os.stat(self.abspath)
		last_modified_time=time.gmtime(stats.st_mtime)
		return last_modified_time

	def should_return_304(self):
		if_modified_since_str=self._request.if_modified_since
		if if_modified_since_str:
			if_modified_since_time=time.strptime(if_modified_since_str,"%a, %d %b %Y %H:%M:%S %Z")

		if if_modified_since_time>self.modified:
			return True
		return False


	def is_static_file_request(self):
		return self._request.path.lstrip('/').startswith(self.static_folder)

	def handle_static(self, path):
		response=Response(None)
		self.abspath=self.root_path+path
		if not os.path.exists(self.abspath) or not os.path.isfile(self.abspath):
			return self.not_found()

		content_type = self.get_content_type()
		response.set_content_type(content_type)

		self.modified = self.get_modified_time()
		if self.should_return_304():
			return self.not_modified()

		if 'Last-Modified' not in response.headers.keys():
			last_modified_str = time.strftime(
				"%a, %d %b %Y %H:%M:%S UTC", self.modified)
			response.headers['Last-Modified'] = last_modified_str
			with open(self.abspath, 'r') as f:
				response.set_body(body=(f.read()))
			return response

	def handle_router(self):
		try:
			handler,args=self._router.get(self._request.path,self._request.method)
		except TypeError:
			return self.not_found()

		if args:
			r=handler(**args)
		else:
			r=handler()
		return r

	def __call__(self,environ,start_response):
		self._response=Response(None)
		self._request=Request(None)
		self._server_handler=start_response
		self._request.bind(environ)

		if self.is_static_file_request():
			r = self.handle_static(self._request.path)
		else:
			try:
				r=self.handle_router()
			except Exception:
				return PandaException(500,self._response,self._server_handler,self.debug)()

		# Static files, 302, 304 and 404
		if isinstance(r,Response):
			self._response = r
			self._server_handler(r.status, r.headerlist)
			return [r.body]

		# Normal html
		self._response.set_body(body=r)
		self._response.set_status(200)
		start_response(self._response.status, self._response.headerlist)
		return [self._response.body]


app_stack=Stack()
default_app=app_stack.top()

if not default_app:
	default_app=Panda('/')

request=app_stack.top().request
response = app_stack.top().response
session = app_stack.top().session




	
	
	




