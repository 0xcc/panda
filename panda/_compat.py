#-*- coding:utf-8 -*-
'''
兼容 python 2 3
'''

import sys
if sys.version <'3':
	import httplib
	from urlparse import parse_qs
	from Cookie import SimpleCookie
else:
	import http.client as httplib
	from http.cookies import SimpleCookie
	from urllib.parse import parse_qs
