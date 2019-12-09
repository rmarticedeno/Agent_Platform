'''
Leader Db File
'''

from ..utils.leader_election import Leader_Election, StoppableThread
from ..utils.logger import getLogger
from threading import Lock
from ..utils.logger import getLogger
from time import sleep
from ..utils.network import Tcp_Message
from threading import Thread

class LDatabase:
    def __init__(self):
        self.dblock = Lock()
        self.database = {}
        self.main_count = 0
        self.node_count = 0
        self.is_full = True

    def insert(self, ip, id = None):
        with self.dblock:
            self.node_count += 1
            if not id:
                for key in self.database:
                    for i in range(0,2):
                        if self.database[key][i] == None:
                            self.database[key][i] = ip
                            return (key, i)
                self.database[self.main_count] = (ip,None)
                self.main_count += 1
                return (self.main_count -1 , 0)
            else:
                for i in range(0,2):
                    if self.database[id][i] == None:
                        self.database[id][i] = ip
                        return (key, i)

    def delete(self, ip):
        with self.dblock:
            self.node_count -= 1
            for key in self.database:
                for i in range(0,2):
                    if self.database[key][i] == ip:
                        self.database[key][i] = None
                        if self.database[key] == (None,None):
                            del self.database[key]
                            if key == self.main_count -1 :
                                self.main_count -= 1
                        return (key, i)

    def get_backup(self):
        with self.dblock:
            for key in self.database:
                if self.database[key][1] != None:
                    return (key, self.database[key][1])
            return None

    def __getitem__(self, value):
        return self.database[value]



class DbLeader(Leader_Election):
    def __init__(self, ip, mask, leport, logger = getLogger()):
        Leader_Election.__init__(self,ip,mask,leport, logger)
        self.database = {}
        self.freelist = []
        self.deadlist = []
        self.main_count = 0
        self.node_count = 0
        self.dblock = Lock()
        self.freelock = Lock()
        self.deadlock = Lock()
        self.dbleaderlogger = logger

    def _dbleader_start(self, time):
        Thread(target=self._check, args=(time), daemon=True, name="Leader Checker")
        self._start()     

    def _check(self, time):
        while(True):
            if not self.im_leader:
                break
            lista = self.Get_Partners()
            self._check_newones(lista)
            self.lelogger.debug(f' deadones checker initated')
            self._check_deadones(lista)            
            sleep(time)


    def _check_newones(self, lista):
        for i in lista:
            present = False
            for j in range(0,len(self.database.keys()) - 1):
                if present:
                    break
                for k in range(0,2):
                    if i == self.database[j][k]:
                        present = True
                        break
            if not present:
                if not i in self.freelist:
                    self.dbleaderlogger.debug(f' new ip found {i}')
                    with self.freelock:
                        self.freelist.append(i)
                self.node_count += 1

    def _check_deadones(self, lista):
        for _,val in self.database.items():
            for j in range(0,2):
                if val[j] and val[j] not in lista:
                    with self.deadlock:
                        self.dbleaderlogger.debug(f'IP LOST {val[j]}')
                        self.deadlist.append(val[j])



    #region database
    def _leinsert(self, ip, id = None):
        if ip != self.ip:
            with self.dblock:
                self.node_count += 1
                if not id:
                    for key in self.database:
                        for i in range(0,2):
                            if self.database[key][i] == None:
                                self.database[key] = self._build_tuple(key, i, ip)
                                return (key, i)
                    self.database[self.main_count] = (ip,None)
                    self.main_count += 1
                    return (self.main_count -1 , 0)
                else:
                    for i in range(0,2):
                        if self.database[id][i] == None:
                            self.database[id] = self._build_tuple(id, i, ip)
                            return (key, i)

    def _ledelete(self, ip):
        with self.dblock:
            self.node_count -= 1
            for key in self.database:
                for i in range(0,2):
                    if self.database[key][i] == ip:
                        self.database[key] = self._build_tuple(key,i, None)
                        if self.database[key] == (None,None):
                            del self.database[key]
                            if key == self.main_count -1 :
                                self.main_count -= 1
                        return (key, i)

    def _leget_backup(self):
        with self.dblock:
            for key in self.database:
                if self.database[key][1] != None:
                    return (key, self.database[key][1])
            return None

    def _build_tuple(self, key, i, val):
        other = self.database[key][(i-1)%2]
        tup = (other, val) if i else (val,other)
        return tup

    def _exist(self, ip):
        for _,tup in self.database.items():
            if ip in tup:
                return True
        return False
    #endregion