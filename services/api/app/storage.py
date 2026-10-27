"""Where uploaded files are kept.

Local disk for the demo. This class is the only place to change to use
S3 or Cloudflare R2 later; the rest of the app just calls save/path/delete.
"""

from pathlib import Path
from typing import Annotated

from fastapi import Depends

from app.config import settings


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, key: str) -> Path:
        return self.root / key

    def save(self, key: str, content: bytes) -> None:
        path = self.path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)


def get_storage() -> LocalStorage:
    return LocalStorage(settings.upload_dir)


# Use in a route as `storage: StorageDep` to receive the storage.
StorageDep = Annotated[LocalStorage, Depends(get_storage)]
