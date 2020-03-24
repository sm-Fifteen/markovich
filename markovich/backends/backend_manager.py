from .markov_backend_sqlite import open_markov_backend_sqlite, sqlite_db_directory
from .markov_backend import MarkovBackend
from contextlib import asynccontextmanager
from typing import Dict, AsyncIterator

class MarkovManager:
    open_backends: Dict[str, MarkovBackend]

    def __init__(self, **kwargs):
        self.open_backends = {}

        # Recieves a list of initial mappings, the rest will be created dynamically
        for k,v in kwargs:
            if type(v) is MarkovBackendSQLite:
                open_backends[k] = v

    @asynccontextmanager
    async def get_markov(self, context_id: str) -> AsyncIterator[MarkovBackend]:
        # In the case of SQLite, connections are opened and closed each time, no pooling

        db_path = sqlite_db_directory / context_id
        db_path = db_path.with_suffix('.db')

        async with open_markov_backend_sqlite(db_path) as backend:
            yield backend
