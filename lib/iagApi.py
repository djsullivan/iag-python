import requests
from urllib3.exceptions import InsecureRequestWarning
import json
import paramiko

class iagConn:
    '''
       Class to abstract IAG api calls
    '''

    def __init__(self, user, password, server, port):
        self.user = user
        self.password = password
        self.url = 'https://' + server + ":" + str(port) + "/api/v2.0/"
        self.session = requests.Session()
        self.session.verify = False
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Cookie': 'AutomationGatewayToken=ODMyMS4yNTI1NTcyMjY2OTk='
        }

    def login(self):

        payload = {"password": self.password, "username": self.user}
        resp = self.session.post(self.url + 'login', headers=self.headers, data=json.dumps(payload))
        result = json.loads(resp.content)
        self.headers['Cookie'] = 'AutomationGatewayToken=' + result['token']

    def Api(self, op, api, payload={}, ignore=False):
        url = self.url + api

        if op == 'GET':
            resp = self.session.get(url, headers=self.headers, data=json.dumps(payload))
        if op == 'POST':
            resp = self.session.post(url, headers=self.headers, data=json.dumps(payload))
        if op == 'DELETE':
            resp = self.session.delete(url, headers=self.headers, data=json.dumps(payload))
        if op == 'PUT':
            resp = self.session.put(url, headers=self.headers, data=json.dumps(payload))

        res = json.loads(resp.content)

        if (resp.status_code == 200 or resp.status_code == 201):
            return res

        if ignore:
            return None

        print(url)
        print(resp.status_code)
        print(resp)

        raise IagApiError(
            op, url, api, message=f"IAG API Response:{resp.status_code} {op} {url}")


class IagApiError(Exception):
    """
       Exception IAG API call failures

         Attributes:
           op  -- Operation (GET,POST,PUT,DELETE)
           url -- IAG url
           api -- api call
           message -- explanation of the error
    """

    def __init__(self, op, url, api, message="IAG API Failure"):
        self.url = url
        self.api = api
        self.message = message
        super().__init__(self.message)
