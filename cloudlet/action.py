#!/usr/bin/env python

import os
import cgi
import signal
import subprocess

argv = cgi.FieldStorage()

print "Content-type: text/html"
print

if 'start' in argv and int(argv['start'].value) == 1:
	main_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'main.py')

	main = subprocess.Popen(
		[main_path,], 
		stdin = subprocess.PIPE,
		stdout = subprocess.PIPE, 
		stderr = subprocess.PIPE, 
		close_fds = False
	)

	print main.pid

if 'end' in argv and int(argv['end'].value) == 1:
	pid = int(argv['pid'].value)
	ret = os.kill(pid, signal.SIGINT)

	print ret