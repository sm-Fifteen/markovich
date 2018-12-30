from .markov_backend_sqlite import MarkovBackendSQLite
from .markov_backend import MarkovBackend
from typing import Dict

class MarkovManager:
    def __init__(self, **kwargs):
        self.open_backends = {} # type: Dict[str, MarkovBackend]

        # Recieves a list of initial mappings, the rest will be created dynamically
        for k,v in kwargs:
            if type(v) is MarkovBackendSQLite:
                open_backends[k] = v

    def get_markov(self, context_id: str) -> MarkovBackend:
        backend = self.open_backends.get(context_id)
	
        if backend is None:
            print("Opening database \"{}\"".format(context_id))

            backend = MarkovBackendSQLite(context_id)
            self.open_backends[context_id] = backend

        return backend