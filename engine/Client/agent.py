from socket import (
    socket,
    SOCK_DGRAM,
    SOL_SOCKET,
    SO_REUSEADDR,
    SOCK_STREAM,
    SO_BROADCAST,
    gethostbyname,
)
from ..utils.network import (
    Send_Broadcast_Message,
    Encode_Request,
    Decode_Response,
    retry,
    Udp_Message,
    Udp_Response,
    Get_Broadcast_Ip,
)
from threading import Thread, Semaphore
from pathlib import Path
from yaml import load, FullLoader, dump
from time import sleep
from random import randint
from hashlib import sha1
from os import path, makedirs, remove
from threading import Lock
from engine.utils.logger import setup_logger, debug, error, info
from json import loads
import os


def check_folder(path='../Templates'):
    if not os.path.exists(path):
        makedirs(path)


check_folder(path='./log')
setup_logger(name='PlatformInterface')


PLATAFORM_PORT = 10000


class PlatformInterface:
    def __init__(
        self,
        ip=None,
        mask=None,
        path='../Templates',
        extension='.agent',
        port=PLATAFORM_PORT,
        publish_time=20,
        publisher=True
    ):
        self.ip = ip
        self.mask = mask
        self.path = path
        self.extension = extension
        self.connection_port = port
        self.agent_publish_time = publish_time
        self.attenders_list = []
        self.attenders_list_lock = Lock()
        self.write_lock = Lock()
        check_folder(path=path)
        Thread(target=self.__discover_server, daemon=True).start()
        Thread(target=self.__get_attenders, daemon=True).start()
        if publisher:
            Thread(target=self._publish, daemon=True).start()
        Thread(target=self._dns_update, daemon=True).start()

    def register_agent(self, ip, port, url, protocol, name):
        '''
        Publicar Un Agente a la Plataforma
        '''

        check_folder()
        name1 = sha1(
            (str(ip) + str(port) + str(url) + str(protocol) + str(name)).encode()
        ).hexdigest()
        dicc = {
            'ip': ip,
            'port': port,
            'url': url,
            'protocol': 'UDP' if protocol else 'TCP',
            'service': name,
        }
        with self.write_lock:
            with open(self.path + '/' + name1 + self.extension, 'w') as file:
                dump(dicc, file)

    def delete_agent(self, ip, port, url, protocol, name):
        '''
        Eliminar un agente de la plataforma
        '''

        check_folder()
        name = sha1(
            (str(ip) + str(port) + str(url) + str(protocol) + str(name)).encode()
        ).hexdigest()
        remove(self.path + '/' + name + self.extension)

    def get_service_list(self, timeout=5):
        '''
        Obtener listado de servicios disponibles en la plataforma

        Devuelve una lista de strings si es posible conectar, None EOC
        '''
        try:
            service_list = []
            if len(self.attenders_list):
                with self.attenders_list_lock:
                    choice = randint(0, len(self.attenders_list) - 1)
                    service_list = Udp_Message(
                        {'get': 'list'},
                        self.attenders_list[choice],
                        PLATAFORM_PORT,
                        Udp_Response,
                        timeout,
                    )
            return service_list
        except Exception as e:
            error(f'Unhandled Exception: {e}')
            return []

    def get_agent(self, service, timeout=15):
        '''
        Obtener un agente que cumple un servicio descrito en la plataforma

        Devuelve una descripción de un agente de ser posible, None EOC
        '''
        try:
            agent_list = []
            with self.attenders_list_lock:
                index = randint(0, len(self.attenders_list) - 1)
                agent_list = Udp_Message(
                    {'get': service},
                    self.attenders_list[index],
                    PLATAFORM_PORT,
                    Udp_Response,
                    timeout,
                )
            if agent_list:
                return agent_list[randint(0, len(agent_list) - 1)]
            return {}
        except Exception as e:
            error(f'Unhandled Exception: {e}')
            return {}
        pass

    def _load_templates(self):
        # Directorio donde se encentran las planillas de los agentes
        agent_directory = Path(self.path)

        # Listado de agentes en la carpeta de configuracion
        agents = []

        with self.write_lock:
            for agent_config in agent_directory.iterdir():
                if agent_config.suffix == self.extension:
                    with agent_config.open() as config:
                        # cada planilla esta en formato yaml
                        agents.append(load(config, FullLoader))

        return agents

    def _publish(self):
        while True:
            self.template_list = self._load_templates()
            debug(self.template_list)
            for service in self.template_list:
                self.attenders_list_lock.acquire()
                if len(self.attenders_list):
                    index = randint(0, len(self.attenders_list) - 1)
                    choice = self.attenders_list[index]
                    self.attenders_list_lock.release()
                    msg = {
                        'post': service['service'],
                        'ip': service['ip'],
                        'port': service['port'],
                        'url': service['url'],
                        'protocol': service['protocol'],
                    }
                    ans = Udp_Message(msg, choice, self.connection_port)
                    if not ans:
                        with self.attenders_list_lock:
                            self.attenders_list.pop(index)
            sleep(self.agent_publish_time)

    def __discover_server(self):
        with socket(type=SOCK_DGRAM) as sock:
            sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)
            sock.bind(('', 10004))
            while True:
                msg, addr = sock.recvfrom(1024)
                debug(f'MESSAGE FROM {addr}')
                post = Decode_Response(msg)
                if 'ME' in post:
                    with self.attenders_list_lock:
                        if not addr[0] in self.attenders_list:
                            debug(f'ATTENDER LIST UPDATED!!!!!')
                            self.attenders_list.append(addr[0])

    def __get_attenders(self):
        while True:
            if self.ip and self.mask:
                Thread(
                    target=Send_Broadcast_Message,
                    args=(
                        {'WHOCANSERVEME': ''},
                        Get_Broadcast_Ip(self.ip, self.mask),
                        PLATAFORM_PORT,
                    ),
                    daemon=True,
                ).start()
                # 
            sleep(4)

    def _dns_update(self):
        while True:
            debug(f'started dns resolver')
            for i in ['m1.lragentplatform.grs.uh.cu', 'm2.lragentplatform.grs.uh.cu']:
                try:
                    ip = gethostbyname(i)
                    with self.attenders_list_lock:
                        if not ip in self.attenders_list:
                            self.attenders_list.append(ip)
                except Exception as e:
                    error(f'Fallo al resolver nombre de dominio')
                    error(e)
            sleep(4)

