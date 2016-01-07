import json
import os
from base import Base
from script_runner import ScriptRunner

class Execute(Base):
    def __init__(self):
        Base.__init__(self, __name__)
        self.user_headers = None
        self.publish_queue = None
        self.script_runner = None
        self.raw_message = None
        self.steps = None
        self.__load_message_from_file()
        self.script_runner_params = {
            'BUILDER_API_TOKEN': None,
            'JOB_ID': None
        }
        self.__validate_message()

    def __load_message_from_file(self):
        message_json_full_path = os.path.join(
            self.config['MESSAGE_DIR'],
            self.config['MESSAGE_JSON_NAME'])
        if not os.path.isfile(message_json_full_path):
            error_message = 'The file {0} was not found'.format(
                message_json_full_path)
            raise Exception(error_message)

        with open(message_json_full_path, 'r') as message_json_file:
            raw_message = message_json_file.read()

        self.log.debug('Loaded raw_message from {0} with length {1}'.format(
            message_json_full_path,
            len(raw_message)))
        self.raw_message = raw_message

    def __validate_message(self):
        self.log.debug('Validating message')
        error_message = ''
        error_occurred = False
        try:
            self.parsed_message = json.loads(self.raw_message)
            steps = self.parsed_message.get('steps')
            if not steps:
                error_message = 'No "steps" property present'
                raise Exception(error_message)

            for step in steps:
                if not step['execOrder']:
                    error_message = 'Missing "execOrder" property in step ' \
                        '{0}'.format(step)

            steps = sorted(steps, key=lambda step: step.get('execOrder'), reverse=False)
            self.steps = steps

            builder_api_token = self.parsed_message.get('builderApiToken', None)

            if builder_api_token is None:
              error_message = 'No "builderApiToken" property present'
              raise Exception(error_message)

            self.script_runner_params['BUILDER_API_TOKEN'] = builder_api_token

            job_id = self.parsed_message.get('jobId', None)

            if job_id is None:
              error_message = 'No "jobId" property present'
              raise Exception(error_message)

            self.script_runner_params['JOB_ID'] = job_id

        except ValueError as verr:
            error_message = 'Invalid message received: ' \
                            'Error : {0} : {1}'.format(
                                str(verr),
                                self.raw_message)
            error_occurred = True
        except Exception as err:
            error_message = 'Invalid message received: ' \
                            'Error : {0} : {1}'.format(
                                str(err),
                                self.raw_message)
            error_occurred = True
        finally:
            if error_occurred:
                self.log.error(error_message, self.log.logtype['USER'])
                raise Exception(error_message)

    def run(self):
        self.log.debug('Inside Execute')
        for step in self.steps:
            if step.get('who', None) == self.config['WHO']:
                script = step.get('script', None)
                if not script:
                    error_message = 'No script to execute in step ' \
                        ' {0}'.format(step)
                script_runner = ScriptRunner(self.script_runner_params)
                script_status = script_runner.execute_script(script)
                self.log.debug(script_status)
            else:
                break
