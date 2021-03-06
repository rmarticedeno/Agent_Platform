from time import monotonic
from hashlib import sha1
from json import loads, dumps
from engine.utils.network import get_hash


class Contact:
    '''
    Mantains the info that the contact (peers), 
    wich is used for determinig whether a peer should be tested for eviction.
    '''

    def __init__(self, ip, port, id=None):
        assert (
            isinstance(port, int)
            and (isinstance(id, int) or id is None)
            and isinstance(ip, str)
        )
        self.last_seen = None
        self.ip, self.port = ip, port
        self.id = id if id is not None else get_hash(ip=ip, port=port)

    def to_json(self):
        return dumps({'ip': self.ip, 'port': self.port, 'id': self.id})

    @staticmethod
    def from_json(jsn_s):
        _dict = loads(jsn_s)
        return Contact(_dict['ip'], _dict['port'], _dict['id'])

    def __str__(self):
        return f'<{self.ip}:{self.port},{self.id}>'

    __repr__ = __str__

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return self.id != other.id

    def touch(self):
        self.last_seen = monotonic()

    def __iter__(self):
        yield from (self.id, self.ip, self.port)

    def __hash__(self):
        return hash(self.id)
