import json
import os
import subprocess
from shippable_adapter import ShippableAdapter
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
        self.builder_api_token = None
        self.job_id = None
        self.parsed_message = None
        self.test_results_file = 'testresults.json'
        self.coverage_results_file = 'coverageresults.json'
        self.__validate_message()
        self.shippable_adapter = ShippableAdapter(self.builder_api_token)
        self.exit_code = 0

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

            steps = sorted(steps, key=lambda step: step.get('execOrder'), \
                reverse=False)
            self.steps = steps

            self.builder_api_token = self.parsed_message.get('builderApiToken',
                None)

            if self.builder_api_token is None:
                error_message = 'No "builderApiToken" property present'
                raise Exception(error_message)

            self.job_id = self.parsed_message.get('jobId', None)

            if self.job_id is None:
                error_message = 'No "jobId" property present'
                raise Exception(error_message)

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
        exit_code = 0
        flushed_consoles_size_in_bytes = 0
        sent_console_truncated_message = False

        exit_code = self._check_for_ssh_agent()
        if exit_code > 0:
            return exit_code

        for step in self.steps:
            if step.get('who', None) == self.config['WHO']:
                script = step.get('script', None)
                if not script:
                    error_message = 'No script to execute in step ' \
                        ' {0}'.format(step)
                    raise Exception(error_message)
                script_runner = ScriptRunner(self.job_id,
                    self.shippable_adapter, flushed_consoles_size_in_bytes,
                    sent_console_truncated_message)
                script_status, script_exit_code, should_continue, \
                    flushed_consoles_size_in_bytes, \
                    sent_console_truncated_message = \
                    script_runner.execute_script(script)
                self._update_exit_code(script_exit_code)
                self.log.debug(script_status)
                if should_continue is False:
                    break
            else:
                break

        self._push_test_results()
        self._push_coverage_results()
        self._push_post_job_envs()

        return self.exit_code

    def _update_exit_code(self, new_exit_code):
        if self.exit_code is 0:
            self.exit_code = new_exit_code

    def _push_post_job_envs(self):
        self.log.debug('Inside _push_post_job_envs')
        job_env_dir = '{0}/postjobenvs/'.format(
            self.config['ARTIFACTS_DIR'])

        if os.path.exists(job_env_dir):
            self.log.debug('postJobEnvs exist, reading dir')

            err, job = self.shippable_adapter.get_job_by_id(self.job_id)
            if err is not None:
                self.log.error('Failed to GET job_by_id: {0}, {1}'.format(
                    self.job_id, err))
                return

            env_results = []
            for filename in os.listdir(job_env_dir):
                if filename.endswith(".json"):
                    f = open(os.path.join(job_env_dir, filename), "r")
                    try:
                        env_json = json.loads(f.read())
                    except ValueError as err:
                        env_json = None
                        self.log.error(
                            'Error posting job envs: {0}'.format(str(err)))
                    if env_json is not None:
                        env_results.append(env_json)

            if env_results:
                job['postJobEnvs'] = env_results

            self.shippable_adapter.put_job_by_id(self.job_id, job)
        else:
            self.log.debug('No postJobEnvs exist, skipping')

    def _push_test_results(self):
        self.log.debug('Inside _push_test_reports')
        test_results_file = '{0}/testresults/{1}'.format(
            self.config['ARTIFACTS_DIR'],
            self.test_results_file)
        if os.path.exists(test_results_file):
            self.log.debug('Test results exist, reading file')

            test_results = ''
            with open(test_results_file, 'r') as results_file:
                test_results = results_file.read()
            self.log.debug('Successfully read test results, parsing')
            try:
                test_results = json.loads(test_results)
                test_results['jobId'] = self.job_id
            except ValueError as err:
                test_results = None
                self.log.error(
                    'Error parsing test results: {0}'.format(str(err)))
            if test_results is not None:
                self.shippable_adapter.post_test_results(test_results)
        else:
            self.log.debug('No test results exist, skipping')


    def _push_coverage_results(self):
        self.log.debug('Inside _push_coverage_results')
        coverage_results_file = '{0}/coverageresults/{1}'.format(
            self.config['ARTIFACTS_DIR'],
            self.coverage_results_file)
        if os.path.exists(coverage_results_file):
            self.log.debug('Coverage results exist, reading file')

            coverage_results = ''
            with open(coverage_results_file, 'r') as results_file:
                coverage_results = results_file.read()

            self.log.debug('Successfully read coverage results, parsing')
            try:
                coverage_results = json.loads(coverage_results)
                coverage_results['jobId'] = self.job_id
            except ValueError as err:
                coverage_results = None
                self.log.error(
                    'Error parsing coverage results: {0}'.format(str(err)))
            if coverage_results is not None:
                self.shippable_adapter.post_coverage_results(coverage_results)
        else:
            self.log.debug('No coverage results exist,skipping')

    def _check_for_ssh_agent(self):
        self.log.debug('Inside _check_for_ssh_agent')
        devnull = open(os.devnull, 'wb')
        p = subprocess.Popen('ssh-agent', shell=True, stdout=devnull)
        p.communicate()
        return p.returncode
