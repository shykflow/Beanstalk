import sys
import time
import threading

class CommandLineSpinner:
    """
    How to use:
    ```
    with CommandLineSpinner(label='Long Running Test'):
        # ... some long-running operations
        # time.sleep(3)
    ```

    But this can be very annoying if you import pdb; pdb.set_trace()
    as the spinner will overwrite your console commands as you type them.
    You can hand in bypass_spinning=True to turn the spinner off for testing/development.
    ```
    with CommandLineSpinner(bypass_spinning=True):
        # ... some long-running operations
        # time.sleep(3)
    ```
    """
    busy = False
    delay = 0.1
    bypass_spinning = False

    @staticmethod
    def spinning_cursor():
        while 1:
            for cursor in '|/-\\': yield cursor

    def __init__(self, label:str=None, delay=None, *args, **kwargs):
        if label is not None:
            print(label)
        self.bypass_spinning = kwargs.pop('bypass_spinning', False)
        self.spinner_generator = self.spinning_cursor()
        if delay and float(delay): self.delay = delay

    def spinner_task(self):
        while self.busy:
            sys.stdout.write(next(self.spinner_generator))
            sys.stdout.flush()
            time.sleep(self.delay)
            sys.stdout.write('\b')
            sys.stdout.flush()

    def __enter__(self):
        if not self.bypass_spinning:
            self.busy = True
            threading.Thread(target=self.spinner_task).start()

    def __exit__(self, exception, value, tb):
        self.busy = False
        time.sleep(self.delay)
        if exception is not None:
            return False
