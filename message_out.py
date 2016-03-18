import time
import json
import logging
import requests

class MessageOut(object):
    def __init__(self, module, config):
        requests.packages.urllib3.disable_warnings()
        self.log = None
        self.module = module
        self.config = config
        self.vortex_url = self.config['SHIPPABLE_VORTEX_URL']
        self.__setup_logging()

    def __setup_logging(self):
        logging.basicConfig(level=self.config['LOG_LEVEL'])
        self.log = logging.getLogger(self.module)
        self.log.setLevel(self.config['LOG_LEVEL'])

    def console(self, req_body):
        self.log.debug('Posting message : {0}'.format(req_body))
        url = '{0}/jobs/{1}/postConsoles'.format(
            self.config['SHIPPABLE_API_URL'],
            self.config['JOB_ID'])
        headers = {
            'Authorization': 'apiToken {0}'.format(
                self.config['BUILDER_API_TOKEN']),
            'content-type': 'application/json'
        }
        while True:
            try:
                request = requests.post(
                    url,
                    data=json.dumps(req_body),
                    headers=headers)
                self.log.debug('post response : {0}'.format(request))
                break
            except Exception as exc:
                self.log.error('{0}\n{1}\nretrying...'.format(
                    post_data, str(exc)))
                time.sleep(self.config['SHIPPABLE_VORTEX_RETRY_INTERVAL'])

    def status(self, headers, status, api_res=None):
        self.log.debug('Posting status: {0}: {1}'.format(status, headers))
        post_data = {
            "where": "micro.su",
            "payload": {
                "headers": headers,
                "status": status,
                "apiResponse": api_res
            }
        }
        headers = {
            'Authorization': 'apiToken {0}'.format(
                self.config['SHIPPABLE_API_TOKEN']),
            'content-type': 'application/json'
        }
        self.__push_to_vortex(headers, post_data)

    def __push_to_vortex(self, headers, post_data):
        self.log.debug('Pushing to vortex')
        while True:
            try:
                request = requests.post(
                    self.vortex_url,
                    data=json.dumps(post_data),
                    headers=headers)
                self.log.debug('post status response : {0}'.format(request))
                break
            except Exception as exc:
                self.log.error('{0}\n{1}\nretrying...'.format(
                    post_data, str(exc)))
                time.sleep(self.config['SHIPPABLE_VORTEX_RETRY_INTERVAL'])
