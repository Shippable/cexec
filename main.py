import sys
from execute import Execute

if __name__ == '__main__':
    print('Booting up CEXEC')
    executor = Execute()
    print('Running CEXEC script')
    exit_code=executor.run()
    print('CEXEC has completed')
    exit(exit_code)
