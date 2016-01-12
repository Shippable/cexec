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

    def __get(self, url):
      self.log.debug('GET {0}'.format(url))
      headers = {
            'Authorization': 'apiToken {0}'.format(self.api_token),
            'Content-Type': 'application/json'
      }
      while True:
          try:
              err = None
              r = requests.get(url, headers=headers)
              self.log.debug('GET {0} completed with {1}'.format(
                  url, r.status_code))
              res_obj = json.loads(r.text)
              if r.status_code > 500:
                  # API server error, we must retry
                  err_msg = 'API server error: {0} {1}'.format(r.status_code,
                      r.text)
                  raise Exception(err_msg)
              elif r.status_code is not 200:
                  err = r.status_code
              return err, res_obj

          except Exception as exc:
              trace = traceback.format_exc()
              error = '{0}: {1}'.format(str(exc), trace)
              self.log.error('Exception GETting {0}: {1}'.format(
                  url, error))
              time.sleep(self.config['SHIPPABLE_API_RETRY_INTERVAL'])


    def __post(self, url, body):
        self.log.debug('POST {0}'.format(url))
        headers = {
            'Authorization': 'apiToken {0}'.format(self.api_token),
            'Content-Type': 'application/json'
        }
        while True:
            try:
                r = requests.post(
                    url,
                    data=json.dumps(body),
                    headers=headers)
                self.log.debug('POST {0} completed with {1}'.format(
                    url, r.status_code))
                break
            except Exception as exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(exc), trace)
                self.log.error('Exception POSTing to {0}: {1}'.format(
                    url, error))
                time.sleep(self.config['SHIPPABLE_API_RETRY_INTERVAL'])

    def __put(self, url, body):
        self.log.debug('PUT {0}'.format(url))
        headers = {
            'Authorization': 'apiToken {0}'.format(self.api_token),
            'Content-Type': 'application/json'
        }
        while True:
            try:
                r = requests.put(
                    url,
                    data=json.dumps(body),
                    headers=headers)
                self.log.debug('PUT {0} completed with {1}'.format(
                    url, r.status_code))
                break
            except Exception as exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(exc), trace)
                self.log.error('Exception PUTing to {0}: {1}'.format(
                    url, error))
                time.sleep(self.config['SHIPPABLE_API_RETRY_INTERVAL'])

    def post_job_consoles(self, job_id, body):
        url = '{0}/jobs/{1}/postConsoles'.format(self.api_url, job_id)
        self.__post(url, body)

    def get_job_by_id(self, job_id):
      url = '{0}/jobs/{1}'.format(self.api_url, job_id)
      return self.__get(url)

    def put_job_by_id(self, job_id, job):
      url = '{0}/jobs/{1}'.format(self.api_url, job_id)
      self.__put(url, job)
