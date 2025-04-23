import sys

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

CloneMode = Literal["bare", "mirror"]
CLONE_MODES = ["bare", "mirror"]
