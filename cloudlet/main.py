#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import libvirt
import tempfile
import subprocess
import struct
import sys
import signal
import time

from xml.etree import ElementTree
from xml.etree.ElementTree import Element

from uuid import uuid4

def start():
	#mount_point = tempfile.mkdtemp()
	mount_point = '/mnt/Home/Haoliang/Desktop/test-mount'
	remote_url 	= 'http://localhost:8000/test-vm/'
	remote_url 	= 'http://192.168.1.101:8000/test-vm/'
	redirect_port = 12580
	inner_port = 8000

	fuse_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'my_fuse.py')
	'''
	fuse = subprocess.Popen(
		[fuse_path, remote_url, mount_point], 
		stdin = subprocess.PIPE,
		stdout = subprocess.PIPE, 
		stderr = subprocess.PIPE, 
		close_fds = False
	)

	while True:
		line = fuse.stdout.readline()
		if line.find('INITIALIZED') != -1:
			break
		time.sleep(0.1)
	'''
	conf_path = os.path.join(mount_point, 'conf.xml')
	mem_path  = os.path.join(mount_point, 'mem-4kaligned')
	disk_path = os.path.join(mount_point, 'disk.raw')

	f = open(conf_path, 'r')
	xml_str = f.read()
	f.close()

	vm_uuid = str(uuid4())
	vm_name = 'test-vm-' + vm_uuid
	vm_name = 'Test-server-hwang'

	xml = ElementTree.fromstring(xml_str)
	#xml.find('name').text = vm_name
	#xml.find('uuid').text = vm_uuid
	xml.find('devices/disk/source').set('file', disk_path)
	#xmlns = "http://libvirt.org/schemas/domain/qemu/1.0"
	#for node in xml.findall("{%s}commandline/{%s}arg" % (xmlns, xmlns)):
	#	if node.get('value').startswith('tcp'):
	#		node.set('value', 'tcp:%d::%d' % (redirect_port, inner_port))
	xml_str = ElementTree.tostring(xml)

	conn = libvirt.open('qemu:///session')
	conn.restoreFlags(mem_path, xml_str, libvirt.VIR_DOMAIN_SAVE_RUNNING)
	machine = conn.lookupByName(vm_name)

	vnc = subprocess.Popen(
		["gvncviewer", "localhost:0"], 
		stdout=subprocess.PIPE, 
		stderr=subprocess.PIPE, 
		close_fds=True
	)
	vnc.wait()

	machine.destroy()

	#fuse.send_signal(signal.SIGINT)
	#fuse.wait()

	umount = subprocess.Popen(
		["fusermount", "-u", mount_point], 
		stdout=subprocess.PIPE, 
		stderr=subprocess.PIPE, 
		close_fds=True
	)
	umount.wait()

	#os.rmdir(mount_point)

if __name__ == '__main__':
	start()


def create(root_path):
	mem_path = "snapshot"

	conn = libvirt.open("qemu:///session")

	f = open("new_conf.xml", "r")
	xml_str = f.read()
	f.close()

	machine = conn.createXML(xml_str, 0)

	vnc = subprocess.Popen(
		["gvncviewer", "localhost:%d" % 0], 
		stdout=subprocess.PIPE, 
		stderr=subprocess.PIPE, 
		close_fds=True
	)

	vnc.wait()

	machine.suspend()
	machine.save(MEM_PATH)


def align_snapshot(snapshot):

	HDR_FMT		= '16s19I'
	HDR_SIZE	= 92
	PAGE_SIZE	= 4096

	f_in = open(snapshot, 'rb')
	f_out = open(snapshot + '-4kaligned', 'wb')

	header = list(struct.unpack(HDR_FMT, f_in.read(HDR_SIZE)))

	xml_str = f_in.read(header[2])
	xml_str += '\0' * (PAGE_SIZE - (HDR_SIZE + len(xml_str)) % PAGE_SIZE)

	header[2] = len(xml_str)
	header = struct.pack(HDR_FMT, *header) + xml_str

	f_out.write(header)
	f_out.write(f_in.read())

	f_in.close()
	f_out.close()

	return f_out.name