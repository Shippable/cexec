import os
import time
import json
import uuid
import threading
import traceback
import subprocess
from config import Config
from app_logger import AppLogger

class Base(object):
    STATUS = {
        'WAITING': 0,
        'QUEUED': 10,
        'PROCESSING': 20,
        'SUCCESS': 30,
        'SKIPPED': 40,
        'UNSTABLE': 50,
        'TIMEOUT': 60,
        'CANCELLED': 70,
        'FAILED': 80
    }

    def __init__(self, module_name):
        self.module = module_name
        self.config = Config()
        self.log = AppLogger(self.config, self.module)

    def command(self, cmd, working_dir, script=False):

        # pylint: disable=too-many-arguments

        self.log.debug('Executing command: {0}\nDir: {1}'.format(
            cmd, working_dir))
        if script:
            self.log.debug('Executing user command')
            return self.__exec_user_command(cmd, working_dir)
        else:
            self.log.debug('Executing system command')
            self.__exec_system_command(cmd, working_dir)

    def __exec_system_command(self, cmd, working_dir):
        self.log.debug('System command runner \nCmd: {0}\nDir: {1}'.format(
            cmd, working_dir))
        cmd = '{0} 2>&1'.format(cmd)
        self.log.debug('Running {0}'.format(cmd))

        proc = None
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                cwd=working_dir,
                env=os.environ.copy(),
                universal_newlines=True)
            stdout, stderr = proc.communicate()
            returncode = proc.returncode
            if returncode != 0:
                command_status = self.STATUS['FAILED']
                self.log.debug(stdout)
                self.log.debug(stderr)
            else:
                self.log.debug('System command completed {0}\nOut:{1}'.format(
                    cmd, stdout))
                command_status = self.STATUS['SUCCESS']
                #self.log.log_command_op(stdout)
                self.log.debug(stdout)
            self.log.debug('Command completed {0}'.format(cmd))
        except Exception as exc:
            error_message = 'Error running system command. Err: {0}'.format(exc)
            self.log.error(error_message)
            trace = traceback.format_exc()
            self.log.error(exc)
            self.log.error(trace)
            raise Exception(error_message)
        self.log.debug('Returning command status: {0}'.format(command_status))
        return command_status

    def __exec_user_command(self, cmd, working_dir):
        self.log.debug('Executing streaming command {0}'.format(cmd))
        current_step_state = self.STATUS['FAILED']

        command_thread_result = {
            'success': False,
            'returncode': None
        }

        command_thread = threading.Thread(
            target=self.__command_runner,
            args=(cmd, working_dir, command_thread_result,))

        command_thread.start()

        self.log.debug('Waiting for command thread to complete')
        command_thread.join(self.config['MAX_COMMAND_SECONDS'])
        self.log.debug('Command thread join has returned. Result: {0}'\
                .format(command_thread_result))

        if command_thread.is_alive():
            self.log.log_command_err('Command timed out')
            self.log.error('Command thread is still running')
            is_command_success = False
            current_step_state = self.STATUS['TIMEOUT']
            self.log.log_command_err('Command thread timed out')
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

        self.log.flush_console_buffer()

        return current_step_state

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
        try:
            proc = subprocess.Popen(
                cmd, shell=True,
                stdout=subprocess.PIPE,
                cwd=working_dir,
                env=os.environ.copy(),
                universal_newlines=True)

            exception = 'Invalid or no script tags received'
            current_group_info = None
            current_group_name = None
            current_cmd_info = None
            for line in iter(proc.stdout.readline, ''):
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
                        'parentConsoleId': '',
                        'type': 'grp',
                        'message': current_group_name,
                        'timestamp': self.__get_timestamp(),
                        'completed': False,
                        'isShown': show_group
                    }
                    self.__resolve_and_queue(console_out)
                elif line.startswith('__SH__CMD__START__'):
                    current_cmd_info = line_split[1]
                    current_cmd_name = '|'.join(line_split[2:])
                    current_cmd_info = json.loads(current_cmd_info)
                    parent_id = current_group_info.get('id') if current_group_info else None
                    console_out = {
                        'consoleId': current_cmd_info.get('id'),
                        'parentConsoleId': parent_id,
                        'type': 'cmd',
                        'message': current_cmd_name,
                        'timestamp': self.__get_timestamp(),
                        'completed': False
                    }
                    if parent_id:
                        self.__resolve_and_queue(console_out)
                elif line.startswith('__SH__CMD__END__'):
                    current_cmd_end_info = line_split[1]
                    current_cmd_end_name = '|'.join(line_split[2:])
                    current_cmd_end_info = json.loads(current_cmd_end_info)
                    parent_id = current_group_info.get('id') if current_group_info else None
                    is_completed = False
                    if current_cmd_end_info.get('completed') == '0':
                        is_completed = True
                    console_out = {
                        'consoleId': current_cmd_info.get('id'),
                        'parentConsoleId': parent_id,
                        'type': 'cmd',
                        'message': current_cmd_end_name,
                        'timestamp': self.__get_timestamp(),
                        'completed': is_completed
                    }
                    if parent_id:
                        self.__resolve_and_queue(console_out)
                elif line.startswith('__SH__GROUP__END__'):
                    current_grp_end_info = line_split[1]
                    current_grp_end_name = '|'.join(line_split[2:])
                    current_grp_end_info = json.loads(current_grp_end_info)
                    is_completed = False
                    if current_grp_end_info.get('completed') == '0':
                        is_completed = True
                    console_out = {
                        'consoleId': current_group_info.get('id'),
                        'parentConsoleId': '',
                        'type': 'grp',
                        'message': current_grp_end_name,
                        'timestamp': self.__get_timestamp(),
                        'completed': is_completed
                    }
                    self.__resolve_and_queue(console_out)
                elif line.startswith('__SH__SCRIPT_END_SUCCESS__'):
                    success = True
                    break
                elif line.startswith('__SH__SCRIPT_END_FAILURE__'):
                    if current_group_info:
                        console_out = {
                            'consoleId': current_group_info.get('id'),
                            'parentConsoleId': '',
                            'type': 'grp',
                            'message': current_group_name,
                            'timestamp': self.__get_timestamp(),
                            'completed': False
                        }
                        self.__resolve_and_queue(console_out)
                    success = False
                    exception = 'Script failure tag received'
                    break
                else:
                    parent_id = current_cmd_info.get('id') if current_cmd_info else None
                    console_out = {
                        'consoleId': str(uuid.uuid4()),
                        'parentConsoleId': parent_id,
                        'type': 'msg',
                        'message': line,
                        'timestamp': self.__get_timestamp(),
                        'completed': False
                    }
                    if parent_id:
                        self.__resolve_and_queue(console_out)
                    else:
                        self.log.debug(console_out)

            proc.kill()
            if success == False:
                self.log.debug('Command failure')
                result['returncode'] = 99
                result['success'] = False
                result['exception'] = exception
            else:
                self.log.debug('Command successful')
                self.log.reset_console_buffer()
                result['returncode'] = 0
                result['success'] = True
        # pylint: disable=broad-except
        except Exception as exc:
            self.log.error('Exception while running command: {0}'.format(exc))
            trace = traceback.format_exc()
            self.log.error(trace)
            result['returncode'] = 98
            result['success'] = False
            result['exception'] = trace

        self.log.debug('Command returned {0}'.format(result['returncode']))

    def __resolve_and_queue(self, console_out):
        self.log.append_console_buffer(console_out)

    def __get_timestamp(self):
        # pylint: disable=no-self-use
        return int(time.time() * 1000000)

    def pop_step(self, execute_plan, step):
        self.log.debug('popping the top of stack: {0}'\
                .format(execute_plan['steps']))
        try:
            for k in execute_plan['steps'].keys():
                if execute_plan['steps'][k]['name'] == step['name']:
                    del execute_plan['steps'][k]
            self.log.debug('popped out top of stack. \n stack {0}'\
                    .format(execute_plan['steps']))
            return execute_plan
        except Exception as exc:
            self.log.error('error occurred while poping step: ' \
                ' {0}'.format(str(exc)))
            raise exc

    def get_top_of_stack(self, execute_plan):
        error_occurred = False
        error_message = ''
        try:
            self.log.info('inside get_top_of_stack')
            steps = execute_plan.get('steps', None)
            if steps is None:
                error_message = 'No steps found in the execute plan: {0}'\
                        .format(execute_plan)
                error_occurred = True
                return
            if len(steps) == 0:
                self.log.info('No steps present in execute plan, returning' \
                    'empty TopOfStack')
                return None
            keys = []
            for k in steps.keys():
                keys.append(int(str(k)))

            self.log.debug('steps keys {0}'.format(keys))
            keys.sort()
            self.log.debug('sorted keys {0}'.format(keys))
            current_step_key = str(keys[0])
            current_step = steps[current_step_key]
            current_step['step_key'] = current_step_key
            return current_step
        # pylint: disable=broad-except
        except Exception as exc:
            error_message = 'Error occurred while trying to get the step' \
                    ' from execute plan \nError: {0} execute plan: {1}' \
                    .format(str(exc), execute_plan)
            error_occurred = True
        finally:
            if error_occurred:
                raise Exception(error_message)
