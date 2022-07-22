#!/usr/bin/env python
"""Python3 urllib wrapper with Cookie support
Supports request and urlretrive on
Conenction which need Cookies
for auth or other"""
__author__ = "Frederik Lauber"
__copyright__ = "Copyright 2014"
__license__ = "GPL3"
__version__ = "0.5"
__maintainer__ = "Frederik Lauber"
__status__ = "Development"
__contact__ = "https://flambda.de/impressum.html"
import os
import re
from shutil import copyfileobj
from urllib.parse import urlencode
from urllib.request import build_opener, HTTPCookieProcessor, Request
from http.cookiejar import CookieJar

class CookieCon(object):
	"""Object which holds all cookies etc."""
	def __init__(self, encoding='utf-8', userAgent=None):
		self._encoding = encoding
		self._cookiejar = CookieJar()
		self._opener = build_opener(HTTPCookieProcessor(self._cookiejar))

		if not userAgent is None:
			self._opener.addheaders = [('User-agent', userAgent)]

	def _encode_dict(self, header_dict):
		"""Function used to encode dicts based
		on the given encoding"""
		encoded_headers = dict()
		for header, value in header_dict.items():
			encoded_header = header.encode(self._encoding)
			encoded_value = value.encode(self._encoding)
			encoded_headers[encoded_header] = encoded_value
		return encoded_headers

	def _encode_url(self, params=None):
		"""Function used to encode urls based
		on the given encoding
		If params is None or has length 0,
		None will be returned.
		This was implemented as self._opener
		also takes None as an argument if
		no params are needed
		"""
		if params is None or not len(params):
			return None
		else:
			return urlencode(self._encode_dict(params)).encode(self._encoding)

	def request(self, url, params=None):
		"""Usage:
		from CookieCon import CookieCon
		con = CookieCon()
		con.request("http://google.de")
			get-request, returns response
		con.request("http://google.de", {'foo': 'bar'})
			post-request, returns response
		"""
		with self._opener.open(url, self._encode_url(params)) as sock:
			return sock.read().decode(self._encoding)

	def urlgetfileinfo(self, url):
		"""Returns a tuple with the filesize and filename
		as defined in the Content-Length and Content-Disposition headers.
		If the header does not exist, None will be returned"""
		with self._opener.open(Request(url, method="HEAD")) as sock:
			try:
				header = sock.info()['Content-Disposition']
				filename = re.search('(?<=").*(?=")', header).group(0)
			except Exception:
				filename = None
			# try:
				# filesize = int(sock.headers['Content-Length'])
			# except KeyError:
				# filesize = None
		filesize = None
		return (filename, filesize)

	class NoFileName(Exception):
		pass
	def urlretrieve(self, url, folder, optname = None):
		"""Usage:
		from CookieCon import CookieCon
		con = CookieCon()
		con.urlretrive("http://foo.bar/1.zip", "~/home/")
			Downloads 1.zip to ~/home/1.zip, resumes if file already exists.
			The filename is discovered by the Content-Disposition header
		con.urlretrive("http://foo.bar/1.zip", "~/home/", "2.zip")
			Downloads 1.zip to ~/home/2.zip, resumes if file already exists.
			The given filename is used.
		If no filename is given nor discovered, a NoFileName exception is raised.
		This will not check that the given foldername and filename are valid but
		raise an exception.
		"""
		(urlname, urlfilesize) = self.urlgetfileinfo(url)
		filename = optname if optname is not None else urlname
		if filename is None:
			raise self.NoFileName
		filesize = float("inf") if urlfilesize is None else urlfilesize
		filepath = os.path.join(folder, filename)
		try:
			currentsize = os.path.getsize(filepath)
		except os.error:
			currentsize = 0
		if currentsize < filesize:
			headers = {"Range":"bytes=%s-" % currentsize}
			encoded_headers = self._encode_dict(headers)
			with self._opener.open(Request(url, headers=encoded_headers)) as sock:
				with open(filepath, "ab") as file:
					copyfileobj(sock, file)
