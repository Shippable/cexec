import json
import traceback
import requests
import time
from base import Base

class ShippableAdapter(Base):
    def __init__(self, api_token):
        Base.__init__(self, __name__)
        self.api_token = api_token
        self.api_url = self.config['SHIPPABLE_API_URL']

    def __post(self, url, body):
        self.log.debug('POSTing to {0}'.format(url))
        headers = {
            'Authorization': 'apiToken {0}'.format(self.api_token),
            'Content-Type': 'application/json'
        }
        while True:
            try:
                request = requests.post(
                    url,
                    data=json.dumps(body),
                    headers=headers)
                self.log.debug('POST to {0} completed'.format(url))
                break
            except Exception as exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(exc), trace)
                self.log.error('Exception POSTing to {0}: {1}'.format(
                    url, error))
                time.sleep(self.config['SHIPPABLE_API_RETRY_INTERVAL'])

    def post_to_vortex(self, body):
        url = self.api_url + '/vortex'
        self.__post(url, body)
