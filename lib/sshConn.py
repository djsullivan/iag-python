import sys
import argparse
import requests
import yaml
import json
import paramiko
import os
import scp
from scp import SCPClient


class sshConn:
    '''
       Class to aid with ssh connection management
    '''

    def __init__(self, user, keypath):
        self.user = user
        self.cert = paramiko.RSAKey.from_private_key_file(keypath)
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self, server):
        self.ssh.connect(server, username=self.user, pkey=self.cert)
        return

    def exec(self, command):
        stdin, stdout, stderr = self.ssh.exec_command(command)
        output = stdout.readlines()
        otp = ''
        for lin in output:
            otp = otp + lin
        return otp

    def close(self):
        if self.ssh is not None:
            self.ssh.close()




