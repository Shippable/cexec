from datetime import datetime
import uuid
import os
import json
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import traceback
from base import Base

class ScriptRunner2(Base):
    def __init__(self, job_id, shippable_adapter, \
        flushed_consoles_size_in_bytes, sent_console_truncated_message):
        Base.__init__(self, __name__)
        self.script_dir = self.config['HOME']
        self.script_name = '{0}/{1}.sh'.format(self.script_dir, uuid.uuid4())
        self.job_id = job_id
        self.shippable_adapter = shippable_adapter
        self.max_consoles_size_in_bytes = self.config['MAX_CONSOLES_SIZE_BYTES']
        self.flushed_consoles_size_in_bytes = flushed_consoles_size_in_bytes
        self.sent_console_truncated_message = sent_console_truncated_message

        # Log directory and file
        self._temporary_log_directory = tempfile.mkdtemp()
        self._log_file_path = \
            os.path.join(self._temporary_log_directory, 'logs')
        buffer_size = 0
        self._write_log_file = open(self._log_file_path, 'w', buffer_size)
        self._read_log_file = open(self._log_file_path, 'r')

        # Threads
        self._logger_thread = None
        self._command_thread = None

    def __del__(self):
        shutil.rmtree(self._temporary_log_directory, ignore_errors=True)

    def execute_script(self, script):
        self.log.debug('executing script runner')
        if not script:
            error_message = 'No "script" provided for script runner'
            self.log.error(error_message)
            raise Exception(error_message)

        self.__write_to_file(script)
        self.log.debug('executing script file')
        # First we need to enumerate all the files in SSH_DIR so we can
        # assemble the ssh-add commands for all of them
        ssh_dir = self.config['SSH_DIR']
        ssh_add_fragment = ''
        key_files = os.listdir(ssh_dir)
        key_files.sort()
        for file_name in key_files:
            file_path = os.path.join(ssh_dir, file_name)
            ssh_add_fragment += 'ssh-add {0};'.format(file_path)

        run_script_cmd = 'ssh-agent bash -c \'{0} cd {1} && {2}\''.format(
            ssh_add_fragment, self.script_dir, self.script_name)

        script_status, exit_code, should_continue = self._run_command(
            run_script_cmd, self.script_dir)
        self.log.debug('Execute script completed with status: {0}'.format(
            script_status))
        return script_status, exit_code, should_continue, \
            self.flushed_consoles_size_in_bytes, \
            self.sent_console_truncated_message

    def __write_to_file(self, script):
        self.log.debug('Writing script to file')
        if not os.path.isdir(self.script_dir):
            os.mkdir(self.script_dir)

        script_file = open(self.script_name, 'w')
        script_file.write(script.encode('UTF-8'))
        script_file.close()

        # Make it executable
        script_stat = os.stat(self.script_name)
        os.chmod(self.script_name, script_stat.st_mode | stat.S_IEXEC)

    def _run_command(self, cmd, working_dir):
        self.log.debug('Executing streaming command: {0}\nDir: {1}'.format(
            cmd, working_dir))
        current_step_state = self.STATUS['FAILED']

        command_thread_result = {
            'success': False,
            'returncode': None,
            'should_continue': True
        }

        self._command_thread = threading.Thread(
            target=self.__command_runner,
            args=(cmd, working_dir, command_thread_result,))

        self._logger_thread = threading.Thread(target=self.logger)

        self._command_thread.start()
        self._logger_thread.start()

        self.log.debug('Waiting for command thread to complete')
        self._command_thread.join()
        self.log.debug('Command thread join has returned. Result: {0}'\
                .format(command_thread_result))

        self._logger_thread.join()

        if self._command_thread.is_alive():
            self.append_command_err('Command timed out')
            self.log.error('Command thread is still running')
            is_command_success = False
            current_step_state = self.STATUS['TIMEOUT']
            should_continue = False
        else:
            self.log.debug('Command completed {0}'.format(cmd))
            is_command_success = command_thread_result['success']
            if is_command_success:
                self.log.debug('command executed successfully: {0}'.format(cmd))
                current_step_state = self.STATUS['SUCCESS']

            else:
                error_message = 'Command failed : {0}'.format(cmd)
                exception = command_thread_result.get('exception', None)
                if exception:
                    error_message += '\nException {0}'.format(exception)
                self.log.error(error_message)
                current_step_state = self.STATUS['FAILED']
                self.log.error(error_message)

            should_continue = command_thread_result['should_continue']

        # For timeouts we want to inject our own exit code because the script
        # hasn't returned yet
        if current_step_state == self.STATUS['TIMEOUT']:
            exit_code = self.STATUS['TIMEOUT']
        else:
            exit_code = command_thread_result['returncode']

        return current_step_state, exit_code, should_continue

    def __command_runner(self, cmd, working_dir, result):
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        self.log.debug('command runner \nCmd: {0}\nDir: {1}'.format(
            cmd, working_dir))
        cmd = '{0} 2>&1'.format(cmd)
        self.log.debug('Running {0}'.format(cmd))

        proc = None
        success = False
        should_continue = True
        try:
            # Unset LD_LIBRARY_PATH
            env = dict(os.environ)
            env.pop('LD_LIBRARY_PATH', None)
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                cwd=working_dir,
                env=env,
                universal_newlines=True)

            exception = 'Invalid or no script tags received'
            current_group_info = None
            current_group_name = None
            current_cmd_info = None
            for line in iter(proc.stdout.readline, ''):
                timestamp = self.__get_timestamp()
                self.log.debug(line)
                line_split = line.split('|')
                if line.startswith('__SH__GROUP__START__'):
                    current_group_info = line_split[1]
                    current_group_name = '|'.join(line_split[2:])
                    current_group_info = json.loads(current_group_info)
                    show_group = current_group_info.get('is_shown', True)
                    if show_group == 'false':
                        show_group = False
                    console_out = {
                        'consoleId': current_group_info.get('id'),
                        'parentConsoleId': 'root',
                        'type': 'grp',
                        'message': current_group_name,
                        'timestamp': timestamp,
                        'isShown': show_group
                    }
                    self._append_to_log_file(console_out)
                elif line.startswith('__SH__CMD__START__'):
                    current_cmd_info = line_split[1]
                    current_cmd_name = '|'.join(line_split[2:])
                    current_cmd_info = json.loads(current_cmd_info)
                    parent_id = current_group_info.get('id') if \
                        current_group_info else None
                    console_out = {
                        'consoleId': current_cmd_info.get('id'),
                        'parentConsoleId': parent_id,
                        'type': 'cmd',
                        'message': current_cmd_name,
                        'timestamp': timestamp,
                    }
                    if parent_id:
                        self._append_to_log_file(console_out)
                elif line.startswith('__SH__CMD__END__'):
                    current_cmd_end_info = line_split[1]
                    current_cmd_end_name = '|'.join(line_split[2:])
                    current_cmd_end_info = json.loads(current_cmd_end_info)
                    parent_id = current_group_info.get('id') if \
                        current_group_info else None
                    is_success = False
                    if current_cmd_end_info.get('exitcode') == '0':
                        is_success = True
                    console_out = {
                        'consoleId': current_cmd_info.get('id'),
                        'parentConsoleId': parent_id,
                        'type': 'cmd',
                        'message': current_cmd_end_name,
                        'timestamp': timestamp,
                        'timestampEndedAt': timestamp,
                        'isSuccess': is_success,
                        'isShown': show_group
                    }
                    if parent_id:
                        self._append_to_log_file(console_out)
                elif line.startswith('__SH__GROUP__END__'):
                    current_grp_end_info = line_split[1]
                    current_grp_end_name = '|'.join(line_split[2:])
                    current_grp_end_info = json.loads(current_grp_end_info)
                    is_success = False
                    if current_grp_end_info.get('exitcode') == '0':
                        is_success = True
                    console_out = {
                        'consoleId': current_group_info.get('id'),
                        'parentConsoleId': 'root',
                        'type': 'grp',
                        'message': current_grp_end_name,
                        'timestamp': timestamp,
                        'timestampEndedAt': timestamp,
                        'isSuccess': is_success,
                        'isShown': show_group
                    }
                    self._append_to_log_file(console_out)
                elif line.startswith('__SH__SCRIPT_END_SUCCESS__'):
                    success = True
                    break
                elif line.startswith('__SH__SCRIPT_END_FAILURE__'):
                    success = False
                    exception = 'Script failure tag received'
                    break
                elif line.startswith('__SH__SHOULD_NOT_CONTINUE__'):
                    should_continue = False
                elif line.startswith('__SH__SHOULD_CONTINUE__'):
                    should_continue = True
                else:
                    parent_id = current_cmd_info.get('id') if \
                        current_cmd_info else None
                    console_out = {
                        'consoleId': str(uuid.uuid4()),
                        'parentConsoleId': parent_id,
                        'type': 'msg',
                        'message': line,
                        'timestamp': timestamp,
                    }

                    if parent_id:
                        self._append_to_log_file(console_out)
                    else:
                        self.log.debug(console_out)

            proc.kill()
            if success == False:
                self.log.debug('Command failure')
                result['returncode'] = 99
                result['success'] = False
                result['exception'] = exception
                result['should_continue'] = should_continue
            else:
                self.log.debug('Command successful')
                result['returncode'] = 0
                result['success'] = True
                result['should_continue'] = should_continue
        # pylint: disable=broad-except
        except Exception as exc:
            self.log.error('Exception while running command: {0}'.format(exc))
            trace = traceback.format_exc()
            self.log.error(trace)
            result['returncode'] = 98
            result['success'] = False
            result['exception'] = trace

        self.log.debug('Command returned {0}'.format(result['returncode']))

    def logger(self):
        logs_to_post = {
            'jobId': self.job_id,
            'jobConsoleModels': []
        }
        logs_last_posted_at = datetime.now()

        while True:
            post_logs = False
            and_break = False

            log_line = self._read_log_file.readline()

            if log_line:
                try:
                    parsed_log_line = json.loads(log_line)
                    logs_to_post['jobConsoleModels'].append(parsed_log_line)
                except Exception as ex:
                    trace = traceback.format_exc()
                    error = '{0}: {1}'.format(str(ex), trace)
                    self.log.error(error)

                # We added a new line, if the new array length exceeds max
                # log lines, post logs.
                if len(logs_to_post['jobConsoleModels']) \
                    >= self.config['MAX_LOG_LINES_TO_FLUSH']:
                    post_logs = True
            else:
                # If the script runner is dead and there are no more logs to
                # read, attempt to post any remaining logs and break.
                if not self._command_thread.isAlive():
                    post_logs = True
                    and_break = True
                # If its been a while since we posted logs, post.
                elif (datetime.now() - logs_last_posted_at).total_seconds() \
                    > self.config['MAX_LOGS_FLUSH_WAIT_TIME_IN_S'] \
                    and logs_to_post['jobConsoleModels']:
                    post_logs = True
                # Sleep a bit if there hasn't been any activity.
                else:
                    time.sleep(self.config['LOGS_FILE_READ_WAIT_TIME_IN_S'])

            # Post logs if asked and there is something to post.
            if post_logs and logs_to_post['jobConsoleModels']:
                logs_last_posted_at = datetime.now()
                self.shippable_adapter.post_job_consoles(self.job_id, \
                    logs_to_post)
                logs_to_post['jobConsoleModels'] = []

            if and_break:
                break

    def __get_timestamp(self):
        # pylint: disable=no-self-use
        return int(time.time() * 1000000)

    def append_command_err(self, err):
        console_out = {
            'consoleId': str(uuid.uuid4()),
            'parentConsoleId': '',
            'type': 'msg',
            'message' : err,
            'timestamp': self.__get_timestamp(),
            'completed' : False
        }
        self._append_to_log_file(console_out)

    def _append_to_log_file(self, console_out):
        self.flushed_consoles_size_in_bytes += \
            len(console_out['message'])
        logs_exceed_limit = self.flushed_consoles_size_in_bytes > \
            self.max_consoles_size_in_bytes
        if logs_exceed_limit and \
            not self.sent_console_truncated_message:
            self.send_console_truncated_message()
            self.sent_console_truncated_message = True
        elif not self.sent_console_truncated_message:
            try:
                self._write_log_file.write(json.dumps(console_out) + '\n')
            except Exception as ex:
                trace = traceback.format_exc()
                error = '{0}: {1}'.format(str(ex), trace)
                self.log.error(error)

    def send_console_truncated_message(self):
        self.log.debug('Flushing final {0} MB limit message'.format(
            self.max_consoles_size_in_bytes / (1024 * 1024)))

        fatal_grp = {
            'consoleId': str(uuid.uuid4()),
            'parentConsoleId': 'root',
            'type': 'grp',
            'message': 'console_limit_error',
            'timestamp': int(time.time() * 1000000),
            'isSuccess': False
        }

        fatal_msg = {
            'consoleId': str(uuid.uuid4()),
            'parentConsoleId': fatal_grp['consoleId'],
            'type': 'msg',
            'message': 'Console size exceeds {0} MB limit. Truncated from \
                here.'.format(self.max_consoles_size_in_bytes / (1024 * 1024)),
            'timestamp': int(time.time() * 1000000),
            'isSuccess': False
        }

        console = {
            'jobId': self.job_id,
            'jobConsoleModels': [fatal_grp, fatal_msg]
        }

        self.shippable_adapter.post_job_consoles(self.job_id, console)
