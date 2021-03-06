from ..utils.network import Tcp_Message
from ..utils.logger import getLogger
from threading import Thread, Lock
from random import randint

class SimpleDataBase:
    def __init__(self, logger=getLogger()):
        '''
        Clase que mantiene un funcionamiento Basico de una Bd de agentes (Thread Safe)
        '''
        self.dbs = {}
        self.lock = Lock()
        self.dblogger = logger

    def _insert(self, tag, agent):
        '''
        Inserta un nuevo agente y si existe, acutaliza su tiempo de vida
        '''
        with self.lock:
            if not tag in self.dbs:
                self.dbs[tag] = [(agent,6)]
            else:
                for i,val in enumerate(self.dbs[tag]):
                    if agent in val:
                        self.dbs[tag][i] = (agent,6)
                        break
                else:
                    self.dbs[tag].append((agent,6))
                    

    def _get(self,tag):
        '''
        Devuelve una lista con a lo sumo 3 agentes que tienen ese servicio
        '''
        with self.lock:
            if tag in self.dbs:
                n_data = len(self.dbs[tag])
                response = []
                if n_data:
                    if n_data <= 3:
                        for i in range(0,n_data):
                            response.append(self.dbs[tag][i][0])
                    else:
                        a = randint(0,n_data-1)
                        b = randint(0,n_data-1)
                        while(b == a):
                            b = randint(0,n_data-1)
                        c = randint(0,n_data-1)
                        while(c == a or c == b):
                            c = randint(0,n_data-1)
                        choice = [a,b,c]
                        for i in choice:
                            response.append(self.dbs[tag][i][0])
                return response
            return None

    def _reset(self):
        '''
        Reinicia la BD
        '''
        self.dbs = {}

    def _dbrefresh(self):
        '''
        Resfresca el estado de todos los registros en la bd
        '''
        with self.lock:
            newdb = {}
            for key in self.dbs:
                for tup in self.dbs[key]:
                    if tup[1] > 0:
                        if not key in newdb:
                            newdb[key] = []
                        newdb[key].append((tup[0],tup[1]-1))
 
