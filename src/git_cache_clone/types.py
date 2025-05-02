import sys

if sys.version_info >= (3, 8):  # noqa: UP036
    from typing import Literal
else:
    from typing_extensions import Literal

CloneMode = Literal["bare", "mirror"]
CLONE_MODES = {"bare", "mirror"}

MetadataStoreMode = Literal["json", "sqlite", "none"]
METADATA_STORE_MODES = {"json", "sqlite", "none"}
