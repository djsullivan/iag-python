import sys
import argparse
import json
import os
import time
import requests
from prints import Prints
from os import walk


class Iap:
    '''
        Class to log in to Itential Automation Platform and execute
        various IAP functions
    '''

    def __init__(self, user, password, server, port=443):
        self.user = user
        self.password = password
        self.iap = server
        self.url = f"https://{server}:{port}"
        self.auto = f"https://{server}:{port}/operations-manager"
        self.work = f"https://{server}:{port}/workflow_engine"
        self.p = Prints(start=1)
        self.filename = "build.env"

        payload = {
            "user": {
                "username": user,
                "password": password
            }
        }

        resp = requests.request('POST', f"{self.url}/login",
                                headers={'Content-Type': 'application/json'},
                                data=json.dumps(payload))

        if (resp.status_code == 200) or (resp.status_code == 201):
            self.hdrs = {'Content-Type': 'application/json',
                         'Cookie': f"token={resp.text}"}
        else:
            raise Exception(
                f"Error: Unexpected response {resp.text}: Failed to get auth token")

    def runAutomation(self, automation, payload, result=True):

        self.p.task(f"Executing automation {automation}")
        resp = requests.request('POST',
                                f"{self.auto}/triggers/endpoint/{automation}",
                                headers=self.hdrs,
                                data=json.dumps(payload))

        if (resp.status_code == 200) or (resp.status_code == 201):
            data = json.loads(resp.text)
            view = json.dumps(data, indent=3)

            self.p.prints(f"Job ID    :{data['data']['_id']}", indent=2)
            self.p.prints(f"Job Status:{data['data']['status']}\n", indent=2)

            return data['data']['_id']
        else:
            print(f"IAP ERROR: API Response Code ({resp.status_code})")
            raise Exception(
                "Error: Unable to launch requested automation due to input errors")

    def waitForAutomation(self, jobId):

        self.p.task(f"Waiting for automation to complete")

        while True:

            resp = requests.request(
                'GET', f"{self.work}/getJobShallow/{jobId}", headers=self.hdrs)

            if (resp.status_code == 200) or (resp.status_code == 201):
                data = json.loads(resp.text)

                if data['status'] == 'running':
                    time.sleep(10)
                    continue
                self.p.prints(f"Job ID    :{jobId}", indent=2)
                self.p.prints(f"Job Status:{data['status']}\n", indent=2)

                return data
            else:
                print(f"IAP ERROR: API Response Code ({resp.status_code})")
                raise Exception("Error: JOB Failure")

    def automationStatus(self, jobId):

        self.p.task(f"Retreive Automation Status")
        self.p.prints(f"Job ID: {jobId}", indent=2)

        resp = requests.request(
            'GET', f"{self.auto}/jobs/{jobId}", headers=self.hdrs)

        if (resp.status_code == 200) or (resp.status_code == 201):
            data = json.loads(resp.text)
            data['data']['tasks'] = {}
            data['data']['transitions'] = {}
            self.p.json(json.dumps(data, indent=3), indent=3)

            return data

    def extractEnvVar(self, jobId, envList, jobOutput):

        self.p.task(f"Extract Job Data => Environment variables")
        self.p.prints(f"Job ID: {jobId}\n", indent=2)

        envs = envList.split(',')
        envVars = []
        for env in envs:
            values = env.split('=')
            val = f"{values[0]}={jobOutput['data']['variables'][values[1]]}"
            os.environ[values[0]
                       ] = f"{jobOutput['data']['variables'][values[1]]}"
            envVars.append(val)

        # Write out environment variables
        self.p.prints(f"Environment Variables ({self.filename})", indent=2)
        self.p.prints("-" * 32, indent=2)
        with open(self.filename, 'a+') as f:
            for env in envVars:
                self.p.prints(f"{env}", indent=2)
                f.write(env + "\n")

    def runCommandTemplate(self, payload, result=True):
        '''
           Execute an command template
        '''
        Pass = ['Fail', 'Pass']
        self.p.task(f"Executing command template {payload['template']}")
        resp = requests.request('POST',
                                f"{self.url}/mop/RunCommandTemplate",
                                headers=self.hdrs,
                                data=json.dumps(payload))

        if (resp.status_code == 200) or (resp.status_code == 201):
            data = json.loads(resp.text)
            view = json.dumps(data, indent=3)

            self.p.prints("Detailed Command Output\n", indent=3)

            for cmd in data['commands_results']:
                self.p.prints(f"{'*':*<70}", indent=3)
                self.p.prints(f"Command: {cmd['evaluated']}\n\n", indent=3)
                self.p.json(cmd['response'], indent=3)
                self.p.prints("\n")

            res = 'Failed'
            if (data['result'] == True):
                res = 'Passed'
            self.p.prints(f"Command Template Result: {res}", indent=2)
            self.p.prints(f"All Pass : {data['all_pass_flag']}\n", indent=2)

            self.p.prints(f"Command Rule Execution Summary\n", indent=2)

            self.p.prints(
                f"{'-':-<20} {'-':-<28} {'-':-<8} {'-':-<8}", indent=2)
            self.p.prints(
                f"{'Device':<20} {'Command':<28} {'Pass':<8} {'Severity':<8}", indent=2)
            self.p.prints(
                f"{'-':-<20} {'-':-<28} {'-':-<8} {'-':-<8}", indent=2)
            for cmd in data['commands_results']:
                self.p.prints(
                    f"{cmd['device']:<20} {cmd['evaluated']:<28} {Pass[cmd['rules'][0]['result']]:<8} {cmd['rules'][0]['severity']:<8}", indent=2)
                if len(cmd['rules']) > 1:
                    for rule in cmd['rules'][1:]:
                        self.p.prints(
                            f"{' ':<20} {' ':<28} {Pass[rule['result']]:<8} {rule['severity']:<8}", indent=2)
            if res == 'Failed':
                raise Exception(
                    "Error: Command Template Failure")

        else:
            print(f"IAP ERROR: API Response Code ({resp.status_code})")
            raise Exception(
                "Error: Unable to launch requested automation due to input errors")

    def getTaskId(self, jobId, taskSummary, result=True):
        '''
           Retrieve job data from IAP for the specified jobId
        '''
        self.p.task(
            f"Retreiving task id for task [{taskSummary}] jobId [{jobId}]")
        resp = requests.request('GET',
                                f"{self.auto}/jobs/{jobId}",
                                headers=self.hdrs)

        if (resp.status_code == 200) or (resp.status_code == 201):
            data = json.loads(resp.text)

            for key, value in data['data']['tasks'].items():
                if 'summary' in value.keys():
                    if (value['summary'] == taskSummary) and (value['status'] == 'running'):

                        self.p.prints(f"Task ID: {key}", indent=2)
                        self.p.prints(f"Summary: {value['summary']}", indent=2)
                        self.p.prints(
                            f"Status:  {value['status']}\n", indent=2)
                        return key

    def advanceTask(self, jobId, taskId, result=True):
        '''
           Retrieve job data from IAP for the specified jobId
        '''
        payload = {
            "task_id": taskId,
            "job_id": jobId,
            "taskData": {
                "finish_state": "success"
            }
        }

        self.p.task(f"Advancing Manual Task [{jobId}] task [{taskId}]")
        resp = requests.request('POST',
                                f"{self.auto}/jobs/{jobId}/tasks/{taskId}/finish",
                                headers=self.hdrs,
                                data=json.dumps(payload))

        if (resp.status_code == 200) or (resp.status_code == 201):
            return
        else:
            print(f"IAP ERROR: API Response Code ({resp.status_code})")
            raise Exception(
                "Error: Unable to finish manual task")


def readJsonFile(directory):

    ##
    # Read security group files
    ##
    filenames = next(walk(f"./{directory}"), (None, None, []))[2]
    filenames.remove('.gitkeep')
    filename = filenames[0]
    notify = json.load(open(f"./{directory}/{filename}"))

    return notify


def main(agrv):
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--user", action="store", dest='user', nargs='?',
                        default='itential', help="Configure user (default=itential)")
    parser.add_argument("-p", "--pass", action="store", dest='password',
                        nargs='?', default='admin', help="Configure user (default=itential)")
    parser.add_argument("-s", "--server", action="store", dest='server',
                        nargs='?', default='44.209.81.98', help="Server to connect")
    parser.add_argument("-automation", "--automation", action="store",
                        dest='auto', help="Automation to Execute")
    parser.add_argument("-payload", "--payload", action="store",
                        dest='payload', help="Automation Payload (JSON)")
    parser.add_argument("-port", "--port", action="store",
                        dest='port', default=443, help="IAP port")
    parser.add_argument("-w", "--wait", action="store_true",
                        dest='wait', default=True, help="Automation Payload (JSON)")
    parser.add_argument("-e", "--env", action="store",
                        dest='env', help="List of output environment variables")
    parser.add_argument("-command-template", "--command-template", action="store_true",
                        dest='template', help="Execute a command template")
    parser.add_argument("-notify", "--notify", action="store",
                        dest='notify', help="Specifies the notification file to load/process")
    args = parser.parse_args()

    print("\nItential Automation Platform (IAP) API access starting\n")

    # Login to Itential IAP server
    iap = Iap(args.user, args.password, args.server)

    if args.template:
        # Execute a command template
        iap.runCommandTemplate(json.loads(args.payload))

    if args.auto:
        # Execute the automation
        jobId = iap.runAutomation(args.auto, json.loads(args.payload))

        if args.wait:
            # Wait for the automation to complete
            iap.waitForAutomation(jobId)

            # Extract the job data/details
            jobOutput = iap.automationStatus(jobId)

            if args.env:
                # Generate environment variables
                iap.extractEnvVar(jobId, args.env, jobOutput)

    if args.notify:
        # Execute the notify action as needed
        data = readJsonFile(args.notify)
        taskId = iap.getTaskId(data['jobId'], 'GitLabWaitTask')
        iap.advanceTask(data['jobId'], taskId)

    print("\nItential Automation Platform (IAP) API access completed\n")


if __name__ == "__main__":
    main(sys.argv[1:])
