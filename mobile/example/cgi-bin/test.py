#!/usr/bin/env python

import subprocess

print "Content-type: text/html"
print
print "<title>Test CGI</title>"
print "<p>Hello World!</p>"

vnc = subprocess.Popen(
	["gedit",], 
	stdout=subprocess.PIPE, 
	stderr=subprocess.PIPE, 
	close_fds=True
)