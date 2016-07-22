#-*- coding:utf-8 -*-

import threading
from collections import OrderedDict


html_escape_table={
	'&': '&amp;',
	'"': '&quot;',
	'\'': '&apos;',
	'>': '&gt;',
	'<': '&lt;',
}

def html_escape(text):
	return ''.join(html_escape_table.get(c,c) for c in text)


class Stack(threading.local):
	def __init__(self):
		self._stack=[]

	def push(self,app):
		self._stack.append(app)

	def pop(self):
		try:
			return self._stack.pop()
		except IndexError:
			return None

	def top(self):
		try:
			return self._stack[-1]
		except IndexError:
			return None

	def __len__(self):
		return len(self._stack)

	def __str__(self):
		return str(self._stack)

	@property
	def empty(self):
	    return len(self._stack)==0

class LRUCache(object):
	def __init__(self,capacity):
		self.capacity=capacity
		self.cache=OrderedDict()

	def get(self,key):
		try:
			value=self.cache.get(key)
			return key
		except KeyError:
			return None

	def set(self,key,value):
		try:
			self.cache.pop(key)
		except KeyError:
			if len(self.cache)>=self.capacity :
				self.cache.popitem(last=False)
		self.cache[key] = value

	

		