from __future__ import annotations

from typing import Any

# MyHDL signals are highly dynamic at runtime. We keep aliases lightweight so
# annotations document intent without pretending to provide stricter static
# guarantees than the library supports today.
BitSignal = Any
