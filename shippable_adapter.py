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
                response = requests.get(url, headers=headers)
                self.log.debug('GET {0} completed with {1}'.format(
                    url, response.status_code))
                res_obj = json.loads(response.text)
                if response.status_code >= 500:
                    # API server error, we must retry
                    err_msg = 'API server error: {0} {1}'.format(
                        response.status_code, response.text)
                    raise Exception(err_msg)
                elif response.status_code is not 200:
                    err = response.status_code
                return err, res_obj

            except Exception as exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(exc), trace)
                self.log.error('Exception GETting {0}: {1}'.format(
                    url, error))
                time.sleep(self.config['SHIPPABLE_API_RETRY_INTERVAL'])


    def __post(self, url, body):
        self.log.debug('POST {0}'.format(url))
        if isinstance(body, str):
            data = body
        else:
            try:
                data = json.dumps(body)
            except Exception as exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(exc), trace)
                self.log.error('POST {0} failed with error: {1}'.format(
                    url, error))
                return True, error

        headers = {
            'Authorization': 'apiToken {0}'.format(self.api_token),
            'Content-Type': 'application/json'
        }
        while True:
            try:
                err = None
                response = requests.post(
                    url,
                    data=data,
                    headers=headers)
                self.log.debug('POST {0} completed with {1}'.format(
                    url, response.status_code))
                if response.status_code >= 500:
                    # API server error, we must retry
                    err_msg = 'API server error: {0} {1}'.format(
                        response.status_code, response.text)
                    raise Exception(err_msg)
                elif response.status_code is not 200:
                    err = response.status_code
                res_obj = json.loads(response.text)
                return err, res_obj
            except Exception as exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(exc), trace)
                self.log.error('Exception POSTing to {0}: {1}'.format(
                    url, error))
                time.sleep(self.config['SHIPPABLE_API_RETRY_INTERVAL'])

    def __put(self, url, body):
        self.log.debug('PUT {0}'.format(url))
        try:
            data = json.dumps(body)
        except Exception as exc:
            trace = traceback.format_exc()
            error = '{0}: {1}'.format(str(exc), trace)
            self.log.error('PUT {0} failed with error: {1}'.format(
                url, error))
            return True, error

        headers = {
            'Authorization': 'apiToken {0}'.format(self.api_token),
            'Content-Type': 'application/json'
        }
        while True:
            try:
                err = None
                response = requests.put(
                    url,
                    data=data,
                    headers=headers)
                self.log.debug('PUT {0} completed with {1}'.format(
                    url, response.status_code))
                if response.status_code >= 500:
                    # API server error, we must retry
                    err_msg = 'API server error: {0} {1}'.format(
                        response.status_code, response.text)
                    raise Exception(err_msg)
                elif response.status_code is not 200:
                    err = response.status_code
                res_obj = json.loads(response.text)
                return err, res_obj
            except Exception as exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(exc), trace)
                self.log.error('Exception PUTing to {0}: {1}'.format(
                    url, error))
                time.sleep(self.config['SHIPPABLE_API_RETRY_INTERVAL'])

    def post_job_consoles(self, job_id, body):
        url = '{0}/jobs/{1}/postConsoles'.format(self.api_url, job_id)

        try:
            data = json.dumps(body)
        except Exception as exc:
            # if there is an error, test each console line and
            # replace the bad line with an error message
            new_job_console_models = []
            for console in body['jobConsoleModels']:
                try:
                    test_console = json.dumps(console)
                    new_job_console_models.append(console)
                except Exception as test_console_exc:
                    test_console_trace = traceback.format_exc()
                    test_console_error = '{0}: {1}'.format(\
                        str(test_console_exc), test_console_trace)
                    console['message'] = 'Failed to parse console log' \
                            ' with error: {0}'.format(test_console_error)
                    new_job_console_models.append(console)
            try:
                body['jobConsoleModels'] = new_job_console_models
                data = json.dumps(body)
            except Exception as new_job_console_models_exc:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(new_job_console_models_exc), trace)
                self.log.error('POST {0} failed with error: {1}'.format(
                    url, error))
                return True, error

        self.__post(url, data)

    def get_job_by_id(self, job_id):
        url = '{0}/jobs/{1}'.format(self.api_url, job_id)
        return self.__get(url)

    def put_job_by_id(self, job_id, job):
        url = '{0}/jobs/{1}'.format(self.api_url, job_id)
        self.__put(url, job)

    def post_test_results(self, body):
        url = '{0}/jobTestReports'.format(self.api_url)
        self.__post(url, body)

    def post_coverage_results(self, body):
        url = '{0}/jobCoverageReports'.format(self.api_url)
        self.__post(url, body)
