"""
Data models for the sheet cutting optimization app.
"""

from typing import List, Dict, Any, Optional

class Part:
    def __init__(self, part_id: int, ref: str, name: str, material: str, thickness: float, width: float, height: float, qty: int):
        self.id = part_id
        self.ref = ref
        self.name = name
        self.material = material
        self.thickness = thickness
        self.width = width
        self.height = height
        self.qty = qty

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'ref': self.ref,
            'name': self.name,
            'material': self.material,
            'thickness': self.thickness,
            'width': self.width,
            'height': self.height,
            'qty': self.qty
        }

class Placement:
    def __init__(self, part_id: int, ref: str, x: float, y: float, rotated: bool, width: float, height: float, spacing: Optional[Dict[str, float]] = None):
        self.part_id = part_id
        self.ref = ref
        self.x = x
        self.y = y
        self.rotated = rotated
        self.width = width
        self.height = height
        self.spacing = spacing or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.part_id,
            'ref': self.ref,
            'x': self.x,
            'y': self.y,
            'rotated': self.rotated,
            'width': self.width,
            'height': self.height,
            'spacing': self.spacing
        }

class Sheet:
    def __init__(self, size: tuple, material: str, thickness: float, placements: List[Placement], algorithm: str, sort_method: str, utilization: float, efficiency: Dict[str, float]):
        self.size = size
        self.material = material
        self.thickness = thickness
        self.placements = placements
        self.algorithm = algorithm
        self.sort_method = sort_method
        self.utilization = utilization
        self.efficiency = efficiency

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sheet_size': self.size,
            'material': self.material,
            'thickness': self.thickness,
            'placements': [p.to_dict() for p in self.placements],
            'algorithm': self.algorithm,
            'sort_method': self.sort_method,
            'utilization': self.utilization,
            'efficiency': self.efficiency
        }
