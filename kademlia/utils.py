from rpyc import VoidService, SocketStream, connect_stream, connect as rpyc_connect
from time import monotonic
from threading import Lock, Thread, Semaphore
from engine.utils.logger import getLogger, debug, error, info
from time import sleep


def to_str(val: int, endian='little'):
    '''
    `endian`='little' o 'big'
    '''
    byts = ['0' * 8]  # force a positive number
    r = val

    while r != 0:
        if endian is 'little':
            byts.insert(-1, bin(r & 255)[2:].rjust(8, '0'))
        else:
            byts.insert(1, bin(r & 255)[2:].rjust(8, '0'))
        r >>= 8
    return ''.join(byts)


def to_boolean(val: int, endian='little'):
    return [b == '1' for b in to_str(val, endian=endian)]


class KSortedQueue:
    def __init__(self, k, id):
        self.k = k
        self.queue = []
        self.mid = id
        self.lock = Lock()

    def add(self, node):
        self.lock.acquire()
        debug(f'{list(self.queue)}.Add({node})')
        for i, cur_node in enumerate(self.queue):
            if node.id ^ self.mid < cur_node.id ^ self.mid:
                self.queue.insert(i, node)
                break
        else:
            if len(self.queue) < self.k:
                self.queue.append(node)
        if len(self.queue) > self.k:
            self.queue.pop()
        self.lock.release()

    def __iter__(self):
        self.lock.acquire()
        for node in self.queue:
            yield node
        self.lock.release()


class ThreadRunner:
    def __init__(self, alpha, cond, target, args=(), kwargs=None, time_to_sleep=0.1):
        self.condition = cond
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.time_to_sleep = time_to_sleep
        self.sem_alpha = Semaphore(value=alpha)
        self.count = 0
        self.count_lock = Lock()

        def alpha_running(*_args, **_kwargs):
            self.sem_alpha.acquire()
            target(*_args, **_kwargs)
            with self.count_lock:
                self.count -= 1
            self.sem_alpha.release()

        self.target = alpha_running

    def run_1by1(self):
        while True:
            condition = self.condition()
            debug(f'Start condition={condition}')
            if condition:
                with self.count_lock:
                    self.count += 1
                t = Thread(target=self.target, args=self.args, kwargs=self.kwargs)
                debug(f'Running ({self.count}) threads.')
                t.start()
                t.join()
            else:
                debug(f'Finish all threads.')
                return

    def start(self):
        self.run_1by1()


class FakeNTP:
    @staticmethod
    def now():
        '''Gives the monotonic clock time.'''
        return monotonic()
