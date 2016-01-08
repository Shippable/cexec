import sys
from execute import Execute

if __name__ == '__main__':
    print('Booting up CEXEC..')
    executor = Execute()
    print executor.config
    exit(executor.run())
