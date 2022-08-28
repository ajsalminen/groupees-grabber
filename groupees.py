#!/usr/bin/env python
#Python3 bindings for groupees.com
#to easiely access your profile,
#keys and downloads
__author__ = "Frederik Lauber"
__copyright__ = "Copyright 2014"
__license__ = "GPL3"
__version__ = "0.5"
__maintainer__ = "Frederik Lauber"
__status__ = "Development"
__contact__ = "https://flambda.de/impressum.html"

import os
import re
import json
import pprint
from string import Template
from codecs import encode,decode
from collections import Counter
import urllib.error
import CookieCon
from getpass import getpass

URL_LOGIN = "https://groupees.com/login"
URL_LOGIN_AUTH = "https://groupees.com/auth/email_password"
URL_PRODUCT_LIST = Template("https://groupees.com/users/${user_id}/more_entries?page=${page}&kind=bundles")
URL_PROFILE_PAGE = Template("https://groupees.com/users/${user_id}/purchases?page=${page}")
URL_REVEAL_BUNDLE = Template("https://groupees.com/orders/${bundle_id}/reveal_all_products")
URL_BUNDLE_DETAILS = Template("https://groupees.com/orders/${bundle_id}?user_id=${user_id}") #&_=8758406998210")
URL_BASE = Template("https://groupees.com${relative}")
REGEX_USER_ID = r"""(?<=user_walls/)\d+(?=/edit)"""
REGEX_COVER_URL = r"""(?<=^background-image:url\(').*(?='\))"""

class _groupees_base_exception(Exception):
	pass

class _url_exception(_groupees_base_exception):
	def __init__(self, url):
		self.url = url
	def __str__(self):
		return "".join([str(self.__class__.__name__), "\nUrl: ", self.url])
class MultipleExceptions(_groupees_base_exception):
	def __init__(self, exceptions):
		self.exceptions = exceptions
	def __str__(self):
		tmp = []
		for e in self.exceptions:
			tmp.append(str(e))
		return "\n".join(tmp)
class NeitherLinkNoKey(_groupees_base_exception):
	def __str__(self):
		return str(self.__class__.__name__)
class ToSmallFile(_url_exception):
	pass
class LinkNotReachable(_url_exception):
	pass
class NoCover(_groupees_base_exception):
	pass
class NoLink(_groupees_base_exception):
	pass
class NoKey(_groupees_base_exception):
	pass
class LoginFailed(_groupees_base_exception):
	pass

class product(object):
	@property
	def name(self):
		#Get the name of the product
		return self._name

	@property
	def link_urls(self):
		if not hasattr(self, "_link_urls"):
			print(URL_BUNDLE_DETAILS.substitute(bundle_id = self._id, user_id = self._user_id))
			self._con._opener.addheaders = [('accept', '*/*')]
			request = self._con.request(URL_BUNDLE_DETAILS.substitute(bundle_id = self._id, user_id = self._user_id))
			# Grab all games and music
			self._link_urls = re.findall(r'https://storage.groupees.com/(?:albums|games)/[0-9]+/(?:flac/|mp3/)?download(?:/[0-9]+)?', request)
			# Grab all other things
			self.link_urls.extend(re.findall(r'https://storage.groupees.com/other_products/[0-9]+?/download\?file_id=[0-9]+', request))
		if self._link_urls is None:
			raise NoLink
		else:
			return self._link_urls

	def download_file(self, url, folder, filename = None):
		print(url)
		self._con._opener.addheaders = [('accept', '*/*')]
		self._con.urlretrieve(url, folder, filename)

	def __init__(self, con, product):
		self._con = con
		self._name = product['bundle_name']
		self._id = product['id']
		# If a bundle was received as a gift, the user_id will be wrong
		# Need to use the gift_taker_id as that is the user_id in other bundles
		if product['gift_taker_id']:
			self._user_id = product['gift_taker_id']
		else:
			self._user_id = product['user_id']

	def reveal(self):
		self._con._opener.addheaders = [('accept', '*/*')]
		request = self._con.request(URL_REVEAL_BUNDLE.substitute(bundle_id = self._id), {'v': '0'})

	def auto_download(self, folder):
		path = os.path.join(folder, self.name.replace(":", ""))
		if not os.path.exists(path): os.makedirs(path)
		for file in self.link_urls:
			try:
				self.download_file(file, path)
			except Exception as E:
				print(E)

	def test(self, filesize_limit = 180):
		#Groupees has still a lot of defect profiles.
		#This functions tries to detect whose.
		#The first criteria is:
		#	1. Every product needs at least one key or one link_url
		#If a link_url exists, headers are checked. If the file is smaller then
		#filesize_limit in kb, it will be regarded as defect.
		num = 0
		try:
			num += len(self.keys)
		except NoKey:
			pass
		try:
			num += len(self.link_urls)
		except NoLink:
			pass
		if not num:
			raise NeitherLinkNoKey
		#check if links have a bigger size than 180kb if they exist
		exception_list = []
		try:
			for platform in self.link_urls:
				url = URL_BASE.substitute(relative = self.link_urls[platform])
				try:
					(filename, filesize) = self._con.urlgetfileinfo(url)
					if filesize <= filesize_limit:
						exception_list.append(ToSmallFile(url))
				except urllib.error.HTTPError:
					exception_list.append(LinkNotReachable(url))
		except NoLink:
			pass
		else:
			if len(exception_list) == 1:
				raise exception_list[0]
			elif len(exception_list) > 1:
				raise MultipleExceptions(exception_list)

def _get_auth_and_userid(username, password):
	connector = CookieCon.CookieCon(userAgent="Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0")
	#as of 15.01.2014, groupees refuses auth if no userAgent is given
	data_for_user_id = connector.request(URL_LOGIN_AUTH, {'identifier': username, 'password': password})
	try:
		userid = re.search(REGEX_USER_ID, data_for_user_id).group(0)
	except AttributeError:
		raise LoginFailed
	return (connector, userid)

def collect_products(username, password):
	#Takes your user name and password and will return a list of groupees_products. Each groupees_product represents one
	#item on your profile like a cd or a game. It can have multiple keys for different platforms and can have multiple downloadable
	#file. Please keep in mind that it does not need to have any at all. A NoKey, NoLink or NoCover Exception will be raised once
	#you try to access it.
	(connector, userid) = _get_auth_and_userid(username, password)
	products = {}
	i = 0
	last_request = ""
	while last_request != '[]':
		last_request = connector.request(URL_PRODUCT_LIST.substitute(user_id = userid, page = str(i)))
		product_list = json.loads(last_request)
		for product_data in product_list:
			p = json.loads(decode(encode(product_data, 'latin-1', 'backslashreplace'), 'unicode-escape'))
			products[p['id']] = (product(connector, p))
		i += 1
	return products.values()

def download_all_by_platform(product_list, platform, folder):
	for prod in product_list:
		try:
			prod.download_file(platform, folder)
		except groupees_product.NoLink:
			pass

def download_all_inverted(product_list, platform_list, folder):
	for prod in product_list:
		try:
			for platform in prod.link_urls:
				if platform in platform_list:
					pass
				else:
					try:
						prod.download_file(platform, folder)
					except KeyError:
						pass
		except NoLink:
			pass

def create_report(product_list):
	line_list = []
	for i in product_list:
		try:
			i.test()
		except Exception as E:
			line_list.append(i.name)
			line_list.append(str(E))
	return "\n".join(line_list)

def find_duplicates(products):
	print('Looking for bundles purchased more than once...')
	product_counts = Counter()
	for i in products:
		product_counts[i.name] += 1
	for i in products:
		if product_counts[i.name] > 1:
				print('Found multiple purchase "' + i.name + '" with id: ')
				print(i._id)
	return product_counts


if __name__ == "__main__":
	import groupees
	print("Start")
	un = input("Please, type your email address\n")
	pw = getpass("Please, type your password\n")
	print("Now trying to accumulate all your products on groupees")
	try:
		p = groupees.collect_products(un, pw)
	except groupees.LoginFailed:
		print("Login Failed")
		print("Check email and password")
		exit(1)
	print("All products found")
	counts = find_duplicates(p)
	download_folder = input("Give folder for auto download (default is the current folder)\n")
	if download_folder == "":
		download_folder = "./"
	print("Revealing and downloading")
	for i in p:
		print("Product:")
		print(i.name)
		try:
			if counts[i.name] == 1:
				i.reveal()
			else:
				print('not revealing ' + i.name)
			# print(i.link_urls)
			i.auto_download(download_folder)
		except Exception as E:
			print(i.name)
			print(E)
	print("Stop")
