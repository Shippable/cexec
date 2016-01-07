import uuid
import os
from base import Base

class ScriptRunner(Base):
    def __init__(self, params):
        Base.__init__(self, __name__)
        self.script_dir = self.config['HOME']
        self.script_name = '{0}/{1}.sh'.format(self.script_dir, uuid.uuid4())
        self.config['BUILDER_API_TOKEN'] = params['BUILDER_API_TOKEN']
        self.config['JOB_ID'] = params['JOB_ID']

    def execute_script(self, script):
        self.log.debug('executing script runner')
        if not script:
            error_message = 'No "script" provided for script runner'
            self.log.error(error_message)
            raise Exception(error_message)

        self.__write_to_file(script)
        return self.__execute_script()

    def __execute_script(self):
        self.log.debug('executing script file')
        # First we need to enumerate all the files in SSH_DIR so we can
        # assemble the ssh-add commands for all of them
        ssh_dir = self.config['SSH_DIR']
        ssh_add_fragment = '';
        for file_name in os.listdir(ssh_dir):
            file_path = os.path.join(ssh_dir, file_name)
            ssh_add_fragment += 'ssh-add {0};'.format(file_path)

        run_script_cmd = 'ssh-agent bash -c \'{0} cd {1} && {2}\''.format(
            ssh_add_fragment, self.script_dir, self.script_name)

        script_status = self.command(
            run_script_cmd, self.script_dir, script=True)
        self.log.debug('Execute script completed with status: {0}'.format(
            script_status))
        return script_status

    def __write_to_file(self, script):
        self.log.debug('Writing script to file')
        create_script_cmd = 'mkdir -p {0} '\
                            '&& touch {1} '\
                            '&& chmod +x {1}' \
                            .format(self.script_dir, self.script_name)

        self.command(create_script_cmd, self.script_dir)
        self.log.debug('Script file created')

        script_file = open(self.script_name, 'w')
        script_file.write(script)
        script_file.close()

        self.log.debug('Executing file')
        with open(self.script_name) as script_file:
            self.log.debug(script_file.read())
