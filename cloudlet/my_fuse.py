#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import errno
import signal
import tempfile
import logging as logger

from functools import wraps
from fuse import FUSE, FuseOSError, Operations
from remote import RemoteFile

import threading

''' Decorate functions for logging and timming
'''
def log_this(level = 25):
	def decorate(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			message = func.__name__ + '(): '
			argc, argv = func.func_code.co_argcount, func.func_code.co_varnames
			for i in range(1, argc):
				message += "%s = %s " % (argv[i], args[i])
			logger.log(level, message)
			return func(*args, **kwargs)
		return wrapper
	return decorate

def time_this(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		start = time.time()
		result = func(*args, **kwargs)
		end = time.time()
		message = func.__name__ + '(): Runtime = %.4f ms'%((end - start) * 1000)
		logger.log(25, message)
		return result
	return wrapper

''' Fuse class
'''
class myFuse(Operations):

	def __init__(self, base_url):
		self.root = tempfile.mkdtemp()
		self.rfiles = {}
		self.rfile_list = ['conf.xml', 'mem-4kaligned', 'disk.raw']
		self.base_url = base_url

		self.my_lock = threading.Lock()

	@log_this()
	def init(self, path):
		for f in self.rfile_list:
			self.rfiles[f] = RemoteFile(self.base_url + f)
		print "INITIALIZED"

	def _full_path(self, p):
		path = os.path.join(self.root, p[1:] if p.startswith("/") else p)
		fn = path.rpartition('/')[-1]
		return self.rfiles[fn].path if fn in self.rfiles else path

	@log_this()
	def access(self, path, mode):
		if not os.access(self._full_path(path), mode):
			raise FuseOSError(errno.EACCES)
	
	@log_this()
	def chmod(self, path, mode):
		return os.chmod(self._full_path(path), mode)

	@log_this()
	def chown(self, path, uid, gid):
		return os.chown(self._full_path(path), uid, gid)

	@log_this()
	def getattr(self, path, fh = None):
		st = os.lstat(self._full_path(path))
		ret = dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
			'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
		if path[1:] in self.rfiles:
			ret['st_size'] = self.rfiles[path[1:]].size
		return ret

	@log_this()
	def readdir(self, path, fh):
		full_path = self._full_path(path)
		dirents = ['.', '..'] + self.rfiles.keys()
		if os.path.isdir(full_path):
			dirents.extend(os.listdir(full_path))
		for r in dirents:
			yield r

	@log_this()
	def readlink(self, path):
		pathname = os.readlink(self._full_path(path))
		if pathname.startswith("/"):
			return os.path.relpath(pathname, self.root)
		else:
			return pathname

	@log_this()
	def mknod(self, path, mode, dev):
		return os.mknod(self._full_path(path), mode, dev)

	@log_this()
	def rmdir(self, path):
		return os.rmdir(self._full_path(path))

	@log_this()
	def mkdir(self, path, mode):
		return os.mkdir(self._full_path(path), mode)

	@log_this()
	def statfs(self, path):
		stv = os.statvfs(self._full_path(path))
		return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
			'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
			'f_frsize', 'f_namemax'))

	@log_this()
	def unlink(self, path):
		return os.unlink(self._full_path(path))

	@log_this()
	def symlink(self, target, name):
		return os.symlink(self._full_path(target), self._full_path(name))

	@log_this()
	def rename(self, old, new):
		return os.rename(self._full_path(old), self._full_path(new))

	@log_this()
	def link(self, target, name):
		return os.link(self._full_path(target), self._full_path(name))

	@log_this()
	def utimens(self, path, times=None):
		return os.utime(self._full_path(path), times)

	@log_this()
	def open(self, path, flags):
		if path[1:] in self.rfiles:
			return self.rfiles[path[1:]].open()
		else:
			full_path = self._full_path(path)
			return os.open(full_path, flags)

	@log_this()
	def create(self, path, mode, fi=None):
		if path[1:] in self.rfiles:
			return self.rfiles[path[1:]].open()
		else:
			full_path = self._full_path(path)
			return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)		

	@time_this
	@log_this()
	def read(self, path, length, offset, fh):
		if path[1:] in self.rfiles:
			self.my_lock.acquire()
			data = self.rfiles[path[1:]].read(offset, length)
			self.my_lock.release()
			return data
		else:
			os.lseek(fh, offset, os.SEEK_SET)
			return os.read(fh, length)

	@time_this
	@log_this()
	def write(self, path, buf, offset, fh):
		if path[1:] in self.rfiles:
			self.my_lock.acquire()
			data = self.rfiles[path[1:]].write(offset, buf)
			self.my_lock.release()
			return data
		else:
			os.lseek(fh, offset, os.SEEK_SET)
			return os.write(fh, buf)

	@log_this()
	def truncate(self, path, length, fh=None):
		with open(self._full_path(path), 'r+') as f:
			f.truncate(length)

	@log_this()
	def flush(self, path, fh):
		return os.fsync(fh)

	@log_this()
	def release(self, path, fh):
		if path[1:] in self.rfiles:
			return self.rfiles[path[1:]].close()
		else:
			return os.close(fh)

	@log_this()
	def fsync(self, path, fdatasync, fh):
		return self.flush(path, fh)

	@log_this()
	def destroy(self, path):
		for f in self.rfiles.values():
			f.close()
			f._close()
		os.rmdir(self.root)

if __name__ == '__main__':
	logger.basicConfig(
		stream = sys.stdout, 
		level = 25, 
		#format='[%(asctime)s] %(funcName)10s(): %(message)s',
		format='\r[%(asctime)s] %(message)s', 
		datefmt='%H:%M:%S',
	)

	mount_point = '/mnt/Home/Haoliang/Desktop/test-mount'
	remote_url 	= 'http://localhost:8000/test-vm/'
	#remote_url = 'http://192.168.1.101:8000/test-vm/'

	if len(sys.argv) == 3:
		remote_url = sys.argv[1]
		mount_point = sys.argv[2]

	fuse_obj = myFuse(remote_url)
	fuse = FUSE(fuse_obj, mount_point, foreground = True)
