#-*- coding:utf-8 -*-


class ServerAdapter(object):
	def __init__(self,host='127.0.0.1',port=8000):
		self.host=host
		self.port=port

	def __repr__(self,app):
		return "%s (%s:%s)" % (self.__class__.__name__,self.host,self.port)

	def run(self,app):
		pass


class WSGIRefServer(ServerAdapter):
	def run(self,app):
		from wsgiref.simple_server import make_server
		httpd=make_server(self.host,self.port,app)
		httpd.server_forever()

class TornadoServer(ServerAdapter):
	def run(self,app):
		import tornado.wsgi
		import tornado.httpserver
		import tornado.ioloop
		container = tornado.wsgi.WSGIContainer(app)
		server = tornado.httpserver.HTTPServer(container)
		server.listen(port=self.port, address=self.host)
		tornado.ioloop.IOLoop.instance().start()

