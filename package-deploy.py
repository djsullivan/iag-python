import sys
import argparse
import requests
import yaml
import json
import paramiko
import os
import scp
from sshConn import sshConn
from scp import SCPClient
from prints import Prints
from iagApi import iagConn


def getScriptSource(name, info):

    for proj in info['projects']:
        if name == proj['name']:
            return f"{info['deployment-dir']}/{name}/{proj['script-name']}"

    return ''


def main(agrv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--keypath", action="store", dest='key', nargs='?',
                        default='/home/ubuntu/.ssh/se-lab-us-east-1.pem', help="Configure path to pem key file")
    parser.add_argument("-u", "--user", action="store", dest='user', nargs='?',
                        default='itential', help="Configure user (default=itential)")
    parser.add_argument("-p", "--pass", action="store", dest='password',
                        nargs='?', default='admin', help="Configure user (default=itential)")
    parser.add_argument("-s", "--server", action="store", dest='server',
                        nargs='?', default='44.209.81.98', help="Server to connect")
    parser.add_argument("-c", "--clean", action="store_true",
                        dest='clean', help="Cleanup remote server")
    parser.add_argument("-f", "--files", action="store",
                        dest='file', help="Configuration file")

    args = parser.parse_args()

    print("\nStarting IAG virtual deployment/cleanup script...\n")

    cwd = os.getcwd()
    p = Prints(start=1)

    p.task("Load IAG deployment instructions")
    info = yaml.safe_load(
        open(cwd + '/assets/deployment/project-deployment.yaml'))

    p.task("Log into IAG instance")
    sshc = sshConn("itential", args.key)
    sshc.connect(args.server)
    iagc = iagConn(args.user, args.password, args.server, 443)
    iagc.login()

    p.task("Execute IAG script refresh")
    iagc.Api("POST", 'scripts/refresh')

    p.task("Remove existing decorations")
    for inst in info['iag-deployments']:
        p.prints("{0:<10} removing decoration".format(
            inst['script-name']), indent=2)
        res = iagc.Api(
            "DELETE", f"scripts/{inst['script-name']}/schema", ignore=True)

    p.task("Remove existing type=indirect script deployments")
    iagScriptPath = info['dir']
    for inst in info['iag-deployments']:
        if inst['type'] == "direct":
            continue
        script = f"{iagScriptPath}/{inst['script-name']}"
        output = sshc.exec(f"ls -la {script}")
        if script in output:
            sshc.exec(f"unlink {script}")
            p.prints(f"Removing {script}", indent=2)

    p.task("Remove existing type=direct script deployments")
    iagScriptPath = info['dir']
    for inst in info['iag-deployments']:
        if inst['type'] == "indirect":
            continue
        script = f"{iagScriptPath}/{inst['script-name']}"
        output = sshc.exec(f"ls -la {script}")
        if script in output:
            sshc.exec(f"unlink {script}")
            p.prints(f"Removing {script}", indent=3)

    p.task("Execute IAG script refresh")
    iagc.Api("POST", 'scripts/refresh')

    if args.clean:
        print("\nIAG Cleanup completed\n")
        exit(0)

    p.task("Handle type=direct script deployments")
    iagScriptPath = info['dir']
    for inst in info['iag-deployments']:
        if inst['type'] == "indirect":
            continue
        script = f"{iagScriptPath}/{inst['script-name']}"
        output = sshc.exec(f"ls -la {script}")
        if script in output:
            sshc.exec("unlink {0}".format(script))

        sshc.exec(f"ln -s {getScriptSource(inst['name'],info)} {script}")
        p.prints(f"{script} ==> {getScriptSource(inst['name'],info)}", indent=2)

    p.task("Execute IAG script refresh")
    iagc.Api("POST", 'scripts/refresh')

    p.task("Update/Add Decorations")
    for inst in info['iag-deployments']:
        try:
            dec = inst['decoration']
        except:
            dec = None
        if dec:
            p.prints("Decorated {0:<16} type={1}".format(
                inst['script-name'], inst['type']), indent=2)
            print(json.dumps(inst['decoration'], indent=3))
            res = iagc.Api(
                "PUT", f"scripts/{inst['script-name']}/schema", payload=inst['decoration'])
            
        else:
            p.prints("Skipping  {0:<16} type={1}".format(
                inst['script-name'], inst['type']), indent=2)

    print("\nCompleted virtual deployment script\n")


if __name__ == "__main__":
    main(sys.argv[1:])
