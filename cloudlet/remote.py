#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Example Google style docstrings.

This module demonstrates documentation as specified by the `Google Python
Style Guide`_. Docstrings may extend over multiple lines. Sections are created
with a section header and a colon followed by a block of indented text.

Example:
  Examples can be given using either the ``Example`` or ``Examples``
  sections. Sections support any reStructuredText formatting, including
  literal blocks::

      $ python example_google.py

Section breaks are created by simply resuming unindented text. Section breaks
are also implicitly created anytime a new section starts.

Attributes:
  module_level_variable (int): Module level variables may be documented in
    either the ``Attributes`` section of the module docstring, or in an
    inline docstring immediately following the variable.

    Either form is acceptable, but the two should not be mixed. Choose
    one convention to document module level variables and be consistent
    with it.

.. _Google Python Style Guide:
   http://google-styleguide.googlecode.com/svn/trunk/pyguide.html

"""

import os
import threading
import tempfile
import threading
import logging as logger
import requests as req
from math import ceil, floor
from bitarray import bitarray

# Block size
BSIZE = 65536
BSIZE = 262144

class RemoteIOError(Exception):
	pass

class RemoteFile(object):
	""" RemoteFile class

	The class provides streamming and on-demand transmission to access
	files on remote servers over Http.

	Attributes:
		fp (file)		: the file pointer to the local file copy.
		url (str)		: full url for the remote file.
		path (str)		: full local path to store the file copy.
		size (int)		: the size of the file in bytes.
		dirty (bitarray) 	: a bitarray indicating if the file block is dirty 
			or not.
		bitmap (bitarray)	: a bitarray indicating if the file block has been 
			transferred or not.
		blocks (int)	: the number of blocks the file has.
	"""

	fp 		= None
	tmp 	= None
	url		= None
	path 	= None
	size 	= None
	dirty	= None
	bitmap 	= None
	blocks	= None

	close_flag = False

	#lock = threading.Lock()

	def __init__(self, remote_url):
		""" Constructor for RemoteFile class

		Initialize necessary variables and connect to remote servers to get 
		the properties of the file. Then it will start transferring the file in 
		background based the result from a predictor

		Args:
			self (RemoteFile)	: the calling RemoteFile instance.
			remote_url (str)	: full url for the remote file.
			local_path (str)	: full local path to store the transferred copy.

		Returns:
			the method returns None

		Raises:
			IOError	: An error occurred accessing the local file copy.
			RemoteIOError: An error occurred when get the file size.
		"""

		self.url = remote_url

		self.get_size()
		self.tmp = tempfile.NamedTemporaryFile()
		self.path = self.tmp.name

		self.bitmap = bitarray(self.blocks)
		self.bitmap.setall(0)
		self.dirty = bitarray(self.bitmap)

		#self.bg_run()

	def create(self):
		if not os.path.exists(self.path):
			open(self.path, "w+b").close()

	def open(self):
		self.fp = open(self.path, "r+b")
		#n = self.url.rpartition('/')[-1]
		#self.real_fp = open(n, "r+b")
		return self.fp.fileno()

	def get_size(self):
		size = int(req.head(self.url).headers['content-length'])
		self.size, self.blocks = size, size / BSIZE + 1

	def block_list(self, offset, length):
		return xrange(offset / BSIZE, (offset + length - 1) / BSIZE + 1)
	
	def check(self, offset, length):
		return self.bitmap[offset / BSIZE : (offset+length-1)/BSIZE + 1].all()

	def read(self, offset, length):
		if not self.check(offset, length):
			n_data =  self.load(offset, length)
		else:
			self.fp.seek(offset)
			n_data = self.fp.read(length)
		'''	
		self.real_fp.seek(offset)
		r_data = self.real_fp.read(length)
		if len(n_data) != len(r_data):
			logger.log(45, "Fatal Error in length %d, %d, n %d, r %d, " % (offset, length, len(n_data), len(r_data)))
			#x = raw_input("waitng")
		else:
			for i in xrange(len(n_data)):
				if n_data[i] != r_data[i]:
					my_b = i/BSIZE
					if self.dirty[my_b] == 0:
						logger.log(45, "Fatal Error %d, %d in byte %d" % (offset, length, i))
		'''
		return n_data

	def load(self, offset, length):
		chunks = ""
		for blk in self.block_list(offset, length):
			chunks += self.load_block(blk)
		s = offset / BSIZE
		start = offset - s * BSIZE
		return chunks[start:start+length]

	def load_block(self, blk):	
		offset = blk * BSIZE
		self.fp.seek(offset)
		if self.bitmap[blk]:
			data = self.fp.read(BSIZE)
		else: 
			header = {'Range': 'bytes=%s-%s' % (offset, offset + BSIZE - 1)}
			data = req.get(self.url, headers = header).content
			self.fp.write(data)
			self.bitmap[blk] = True
			self.fp.flush()
		return data

	def write(self, offset, buf):
		for blk in self.block_list(offset, len(buf)):
			#self.bitmap[blk] = True
			self.dirty[blk] = True
			self.load_block(blk)
		self.fp.seek(offset)
		self.fp.write(buf)
		self.fp.flush()
		return len(buf)

	def flush(self):
		self.fp.flush()
		
	def close(self):
		'''
		self.close_flag = True
		self.t.join(10)
		if self.t.isAlive():
			print "Error thread still alive"
		if self.dirty.any():
			print "Dirty block. Need writeback"
		'''
		if self.fp is not None:
			return self.fp.close()

	def _close(self):
		self.tmp.close()
	
	def stream(self, queue):
		for blk in queue:
			if not self.bitmap[blk]:
				print "Loading Block " + str(blk)
				self.load_block(blk)
			if self.close_flag:
				return
		print "Stop loading complete rate %d / %d" % (int(self.bitmap.count()), self.blocks)

	def bg_run(self):
		if self.fp == None:
			self.open()
		queue = [i for i in range(self.blocks)]
		self.t = threading.Thread(target = self.stream, args = (queue,))
		self.t.start()

class StreamThread(threading.Thread):
	
	def __init__(self, queue, remote_file):
		super(StreamThread, self).__init__()
		self.flag = False
		self.queue = queue
		self.rfp = remote_file

	def run(self):
		for blk in self.queue:
			if not self.rfp.bitmap[blk]:
				self.rfp.load_block(blk)
			if self.flag:
				break
		
	def end(self):
		self.flag = True

class Predictor(object):

	def __init__(self):
		pass

	def read(self, blk):
		pass

	def load(self, path):
		pass

	def save(self, path):
		pass

	def next(self, path):
		pass

	def update(self, path):
		pass
