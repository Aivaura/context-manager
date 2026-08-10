from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConnectorStatus:
    status: str
    last_sync_at: datetime | None
    document_count: int
    error_message: str | None


class BaseConnector(ABC):
    @abstractmethod
    async def authenticate(self, **kwargs) -> dict:
        raise NotImplementedError

    @abstractmethod
    async def fetch_documents(self, connector_record, since: datetime | None = None) -> list:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, connector_record) -> ConnectorStatus:
        raise NotImplementedError
