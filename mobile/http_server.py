#!/usr/bin/env python

import os
import cgi
import gzip
import urllib
import shutil
import mimetypes
import posixpath
import BaseHTTPServer

from cStringIO import StringIO

class RangeHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	def do_GET(self):
		f, start_range, end_range = self.send_head()
		#gzip_out = gzip.GzipFile(mode = 'wb', fileobj = self.wfile)
		#print "Got values of ", start_range, " and ", end_range, "...\n"
		if f:
			f.seek(start_range, 0)
			chunk = 0x1000
			total = 0
			while chunk > 0:
				if start_range + chunk > end_range:
					chunk = end_range - start_range
				try:
					self.wfile.write(f.read(chunk))
					#gzip_out.write(f.read(chunk))
				except:
					break
				total += chunk
				start_range += chunk
			#gzip_out.close()
			f.close()

	def do_HEAD(self):
		f, start_range, end_range = self.send_head()
		if f:
			f.close()

	def send_head(self):
		path = self.translate_path(self.path)
		f = None
		if os.path.isdir(path):
			if not self.path.endswith('/'):
				self.send_response(301)
				self.send_header("Location", self.path + "/")
				self.end_headers()
				return (None, 0, 0)
			for index in "index.html", "index.htm":
				index = os.path.join(path, index)
				if os.path.exists(index):
					path = index
					break
			else:
				return self.list_directory(path)
		ctype = self.guess_type(path)
		try:
			f = open(path, 'rb')
		except IOError:
			self.send_error(404, "File not found")
			return (None, 0, 0)
		if "Range" in self.headers:
			self.send_response(206)
		else:
			self.send_response(200)
		self.send_header("Content-type", ctype)
		#self.send_header("Content-Encoding", "gzip")
		fs = os.fstat(f.fileno())
		size = int(fs[6])
		start_range = 0
		end_range = size
		self.send_header("Accept-Ranges", "bytes")
		if "Range" in self.headers:
			s, e = self.headers['range'][6:].split('-', 1)
			sl = len(s)
			el = len(e)
			if sl > 0:
				start_range = int(s)
				if el > 0:
					end_range = int(e) + 1
			elif el > 0:
				ei = int(e)
				if ei < size:
					start_range = size - ei
		self.send_header("Content-Range", 'bytes ' + str(start_range) + '-' + str(end_range - 1) + '/' + str(size))
		self.send_header("Content-Length", end_range - start_range)
		self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
		self.end_headers()
		print "Sending Bytes ",start_range, " to ", end_range, "..."
		return (f, start_range, end_range)

	def list_directory(self, path):
		try:
			list = os.listdir(path)
		except os.error:
			self.send_error(404, "No permission to list directory")
			return None
		list.sort(key=lambda a: a.lower())
		f = StringIO()
		displaypath = cgi.escape(urllib.unquote(self.path))
		f.write('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
		f.write("<html>\n<title>Directory listing for %s</title>\n" % displaypath)
		f.write("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath)
		f.write("<hr>\n<ul>\n")
		for name in list:
			fullname = os.path.join(path, name)
			displayname = linkname = name
			# Append / for directories or @ for symbolic links
			if os.path.isdir(fullname):
				displayname = name + "/"
				linkname = name + "/"
			if os.path.islink(fullname):
				displayname = name + "@"
			f.write('<li><a href="%s">%s</a>\n'
					% (urllib.quote(linkname), cgi.escape(displayname)))
		f.write("</ul>\n<hr>\n</body>\n</html>\n")
		length = f.tell()
		f.seek(0)
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		#self.send_header("Content-Encoding", "gzip")
		self.send_header("Content-Length", str(length))
		self.end_headers()
		return (f, 0, length)

	def translate_path(self, path):
		path = path.split('?',1)[0]
		path = path.split('#',1)[0]
		path = posixpath.normpath(urllib.unquote(path))
		words = path.split('/')
		words = filter(None, words)
		path = os.getcwd()
		for word in words:
			drive, word = os.path.splitdrive(word)
			head, word = os.path.split(word)
			if word in (os.curdir, os.pardir): continue
			path = os.path.join(path, word)
		return path

	def copyfile(self, source, outputfile):
		shutil.copyfileobj(source, outputfile)

	def guess_type(self, path):
		'''
		if not mimetypes.inited:
			mimetypes.init() # try to read system mime.types
			self.extensions_map = mimetypes.types_map.copy()
			self.extensions_map.update({
				'': 'application/octet-stream', # Default
				'.py': 'text/plain',
				'.c': 'text/plain',
				'.h': 'text/plain',
				'.mp4': 'video/mp4',
				'.ogg': 'video/ogg',
				})
		base, ext = posixpath.splitext(path)
		if ext in self.extensions_map:
			return self.extensions_map[ext]
		ext = ext.lower()
		if ext in self.extensions_map:
			return self.extensions_map[ext]
		else:
			return self.extensions_map['']
		'''
		return 'application/octet-stream'


def main(HandlerClass = RangeHTTPRequestHandler,
		 ServerClass = BaseHTTPServer.HTTPServer):
	BaseHTTPServer.test(HandlerClass, ServerClass)

if __name__ == '__main__':
	main()
