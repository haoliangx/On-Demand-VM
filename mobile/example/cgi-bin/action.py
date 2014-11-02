#!/usr/bin/env python

import time
from random import random

print "Content-type: text/html"
print
print "<title>Test CGI</title>"
print "<p>Hello World!</p>"
print "<p>%s</p>" % time.asctime()
print "Random Number %f" % (random() * 1000)
