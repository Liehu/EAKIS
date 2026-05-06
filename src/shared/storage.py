from typing import Any


class StorageClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str = "eakis") -> None:
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        # TODO: initialize MinIO client
