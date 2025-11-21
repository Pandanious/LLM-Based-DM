from dataclasses import dataclass
from typing import Optional, Literal

Role = Literal['system','user','assistant']

@dataclass
class Message:
    role: Role
    content: str
    speaker: Optional[str] = None

    