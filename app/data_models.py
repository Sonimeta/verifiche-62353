# app/data_models.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class Limit:
    unit: str
    high_value: Optional[float] = None

@dataclass
class AppliedPart:
    name: str
    part_type: str

@dataclass
class Test:
    name: str
    parameter: Optional[str] = ""
    limits: Dict[str, Limit] = field(default_factory=dict)
    is_applied_part_test: bool = False

@dataclass
class VerificationProfile:
    name: str
    tests: List[Test]