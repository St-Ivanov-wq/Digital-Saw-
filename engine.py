"""
Packing engine and optimization logic for the sheet cutting app.
"""
from rectpack import newPacker
from rectpack.maxrects import MaxRectsBaf, MaxRectsBl
from rectpack.skyline import SkylineMwf, SkylineBlWm
from rectpack.guillotine import GuillotineBafSas
from typing import List, Callable, Dict, Any
from models.part import Part, Placement, Sheet
from config import DEFAULT_SHEET_SIZES

ALGORITHMS = [
    (MaxRectsBaf, "MaxRects Best-Area-Fit"),
    (SkylineMwf, "Skyline Min-Waste-Fit"),
    (MaxRectsBl, "MaxRects Bottom-Left"),
    (SkylineBlWm, "Skyline Bottom-Left Waste-Map"),
    (GuillotineBafSas, "Guillotine Best-Area-Fit Split-Axis-Short")
]

class PackingEngine:
    def __init__(self, sheet_sizes: List[tuple]):
        self.sheet_sizes = sheet_sizes
        self.algorithms = ALGORITHMS

    def calculate_plan(self, parts: List[Part], progress_callback: Callable):
        try:
            sheets = []
            groups = {}
            for part in parts:
                key = (part.material, part.thickness)
                if key not in groups:
                    groups[key] = []
                groups[key].append(part)
            total_parts = sum(p.qty for p in parts)
            processed_parts = 0
            progress_callback(("Започва изчислението...", 0))
            import math
            import time
            start_time = time.time()
            for group_key, group_parts in groups.items():
                material, thickness = group_key
                all_pieces = []
                for part in group_parts:
                    for _ in range(part.qty):
                        all_pieces.append({
                            'width': part.width,
                            'height': part.height,
                            'ref': part.ref,
                            'part_id': part.id,
                            'original_width': part.width,
                            'original_height': part.height
                        })
                best_utilization = 0
                best_solution = None
                best_algorithm = None
                best_time = float('inf')
                best_sort = ""
                for attempt in range(4):
                    if attempt == 0:
                        sorted_pieces = sorted(all_pieces, key=lambda p: p['width'] * p['height'], reverse=True)
                        sort_name = "Площ (намаляващ)"
                    elif attempt == 1:
                        sorted_pieces = sorted(all_pieces, key=lambda p: max(p['width'], p['height']), reverse=True)
                        sort_name = "Макс размер (намаляващ)"
                    elif attempt == 2:
                        sorted_pieces = sorted(all_pieces, key=lambda p: 2*(p['width'] + p['height']), reverse=True)
                        sort_name = "Периметър (намаляващ)"
                    else:
                        sorted_pieces = sorted(all_pieces, 
                                             key=lambda p: (p['width'] * p['height'], 
                                                            max(p['width'], p['height']) / min(p['width'], p['height'])), 
                                             reverse=True)
                        sort_name = "Хибридно сортиране"
                    for algo, algo_name in self.algorithms:
                        algo_start_time = time.time()
                        if time.time() - start_time > 300:
                            progress_callback(("Грешка: Изчислението отне твърде много време", 100))
                            return None
                        try:
                            packer = newPacker(rotation=True, pack_algo=algo)
                            total_piece_area = sum(p['width'] * p['height'] for p in sorted_pieces)
                            for sheet_size in self.sheet_sizes:
                                eff_width = sheet_size[0] - 20
                                eff_height = sheet_size[1] - 20
                                sheet_area = eff_width * eff_height
                                min_for_size = max(1, math.ceil(total_piece_area / sheet_area))
                                for _ in range(min_for_size):
                                    packer.add_bin(eff_width, eff_height, bid=sheet_size)
                            for idx, piece in enumerate(sorted_pieces):
                                packer.add_rect(piece['width'] + 10, piece['height'] + 10, rid=idx)
                            packer.pack()
                            if packer.rect_list() and len(packer.rect_list()) < len(sorted_pieces):
                                unpacked_count = len(sorted_pieces) - len(packer.rect_list())
                                additional_bins = max(1, math.ceil(unpacked_count / 5))
                                for sheet_size in self.sheet_sizes:
                                    eff_width = sheet_size[0] - 20
                                    eff_height = sheet_size[1] - 20
                                    for _ in range(additional_bins):
                                        packer.add_bin(eff_width, eff_height, bid=sheet_size)
                                packer.pack()
                            total_sheet_area = 0
                            used_area = 0
                            placements_by_bin = {}
                            for rect in packer.rect_list():
                                b, x, y, w, h, rid = rect
                                piece = sorted_pieces[rid]
                                sheet_size = packer[b].bid
                                if b not in placements_by_bin:
                                    placements_by_bin[b] = {
                                        'sheet_size': sheet_size,
                                        'placements': [],
                                        'used_area': 0
                                    }
                                    total_sheet_area += sheet_size[0] * sheet_size[1]
                                rotated = False
                                if (math.isclose(w, piece['width'] + 10, abs_tol=0.1) and 
                                    math.isclose(h, piece['height'] + 10, abs_tol=0.1)):
                                    pass
                                elif (math.isclose(h, piece['width'] + 10, abs_tol=0.1) and 
                                      math.isclose(w, piece['height'] + 10, abs_tol=0.1)):
                                    rotated = True
                                else:
                                    rotated = not (w == piece['original_width'] + 10)
                                part_x = 10 + x + 5
                                part_y = 10 + y + 5
                                placement = Placement(
                                    part_id=piece['part_id'],
                                    ref=piece['ref'],
                                    x=part_x,
                                    y=part_y,
                                    rotated=rotated,
                                    width=piece.get('original_width', piece['width']),
                                    height=piece.get('original_height', piece['height']),
                                    spacing={
                                        'x': 10 + x,
                                        'y': 10 + y,
                                        'width': w,
                                        'height': h
                                    }
                                )
                                placements_by_bin[b]['placements'].append(placement)
                                placements_by_bin[b]['used_area'] += piece['original_width'] * piece['original_height']
                                used_area += piece['original_width'] * piece['original_height']
                            if total_sheet_area == 0:
                                continue
                            utilization = used_area / total_sheet_area
                            algo_time = time.time() - algo_start_time
                            if utilization > best_utilization or (utilization == best_utilization and algo_time < best_time):
                                best_utilization = utilization
                                best_solution = placements_by_bin
                                best_algorithm = algo_name
                                best_time = algo_time
                                best_sort = sort_name
                        except Exception as e:
                            print(f"Algorithm {algo_name} failed: {e}")
                            continue
                if best_solution is None:
                    progress_callback(("Грешка: Неуспешно опаковане на частите", 100))
                    return None
                if best_solution:
                    optimized_solution = {}
                    for bin_id, sheet_data in best_solution.items():
                        placements = sheet_data['placements']
                        used_area = sum(p.width * p.height for p in placements)
                        sheet_w, sheet_h = sheet_data['sheet_size']
                        sheet_area = sheet_w * sheet_h
                        waste_percent = (sheet_area - used_area) / sheet_area * 100
                        if waste_percent > 15:
                            placements_dicts = [p.to_dict() if hasattr(p, 'to_dict') else p for p in placements]
                            optimized_placements = self.optimize_sheet(
                                placements_dicts,
                                sheet_w,
                                sheet_h
                            )
                            if optimized_placements:
                                placements = [
                                    Placement(
                                        placement['part_id'],
                                        placement['ref'],
                                        placement['x'],
                                        placement['y'],
                                        placement['rotated'],
                                        placement['width'],
                                        placement['height'],
                                        {}) for placement in optimized_placements
                                ]
                                used_area = sum(p['width'] * p['height'] for p in optimized_placements)
                                waste_percent = (sheet_area - used_area) / sheet_area * 100
                        sheet_data['placements'] = placements
                        sheet_data['used_area'] = used_area
                        optimized_solution[bin_id] = sheet_data
                    best_solution = optimized_solution
                for bin_id, sheet_data in best_solution.items():
                    sheet_size = sheet_data['sheet_size']
                    placements = sheet_data['placements']
                    used_area = sheet_data['used_area']
                    sheet_area = sheet_size[0] * sheet_size[1]
                    utilization = used_area / sheet_area if sheet_area > 0 else 0
                    efficiency = self.calculate_sheet_efficiency(sheet_size, placements)
                    sheets.append(Sheet(
                        size=sheet_size,
                        material=material,
                        thickness=thickness,
                        placements=placements,
                        algorithm=best_algorithm,
                        sort_method=best_sort,
                        utilization=utilization,
                        efficiency=efficiency
                    ))
                processed_parts += len(all_pieces)
                progress_value = processed_parts / total_parts * 100
                progress_callback((f"Опаковани {len(all_pieces)} части (Алгоритъм: {best_algorithm}, Сортиране: {best_sort})", progress_value))
            sheets = self.global_optimization(sheets)
            return sheets
        except Exception as e:
            import traceback
            traceback.print_exc()
            progress_callback((f"Грешка: {str(e)}", 100))
            return None

    def global_optimization(self, sheets: List[Sheet]):
        if not sheets:
            return sheets
        import math
        all_parts = []
        for sheet in sheets:
            all_parts.extend(sheet.placements)
        all_parts.sort(key=lambda p: p.width * p.height, reverse=True)
        material = sheets[0].material
        thickness = sheets[0].thickness
        optimized_sheets = []
        packer = newPacker(rotation=True, pack_algo=MaxRectsBaf)
        total_piece_area = sum(p.width * p.height for p in all_parts)
        for sheet_size in self.sheet_sizes:
            eff_width = sheet_size[0] - 20
            eff_height = sheet_size[1] - 20
            sheet_area = eff_width * eff_height
            min_for_size = max(1, math.ceil(total_piece_area / sheet_area))
            for _ in range(min_for_size):
                packer.add_bin(eff_width, eff_height, bid=sheet_size)
        for idx, part in enumerate(all_parts):
            packer.add_rect(part.width + 10, part.height + 10, rid=idx)
        packer.pack()
        placements_by_bin = {}
        for rect in packer.rect_list():
            b, x, y, w, h, rid = rect
            piece = all_parts[rid]
            sheet_size = packer[b].bid
            if b not in placements_by_bin:
                placements_by_bin[b] = {
                    'sheet_size': sheet_size,
                    'placements': [],
                    'used_area': 0
                }
            rotated = False
            if (math.isclose(w, piece.width + 10, abs_tol=0.1) and 
                math.isclose(h, piece.height + 10, abs_tol=0.1)):
                pass
            elif (math.isclose(h, piece.width + 10, abs_tol=0.1) and 
                  math.isclose(w, piece.height + 10, abs_tol=0.1)):
                rotated = True
            else:
                rotated = piece.rotated
            part_x = 10 + x + 5
            part_y = 10 + y + 5
            placement = Placement(
                part_id=piece.part_id,
                ref=piece.ref,
                x=part_x,
                y=part_y,
                rotated=rotated,
                width=piece.width,
                height=piece.height,
                spacing={
                    'x': 10 + x,
                    'y': 10 + y,
                    'width': w,
                    'height': h
                }
            )
            placements_by_bin[b]['placements'].append(placement)
            placements_by_bin[b]['used_area'] += piece.width * piece.height
        for bin_id, sheet_data in placements_by_bin.items():
            sheet_size = sheet_data['sheet_size']
            placements = sheet_data['placements']
            used_area = sheet_data['used_area']
            sheet_area = sheet_size[0] * sheet_size[1]
            utilization = used_area / sheet_area if sheet_area > 0 else 0
            efficiency = self.calculate_sheet_efficiency(sheet_size, placements)
            optimized_sheets.append(Sheet(
                size=sheet_size,
                material=material,
                thickness=thickness,
                placements=placements,
                algorithm="Global Optimization",
                sort_method="Площ (намаляващ)",
                utilization=utilization,
                efficiency=efficiency
            ))
        return optimized_sheets

    def optimize_sheet(self, placements, sheet_w, sheet_h):
        try:
            parts = []
            for p in placements:
                parts.append({
                    'part_id': p['part_id'],
                    'width': p['width'],
                    'height': p['height'],
                    'ref': p['ref'],
                    'rotated': p['rotated'],
                    'x': p.get('x', 0),
                    'y': p.get('y', 0)
                })
            parts.sort(key=lambda p: p['width'] * p['height'], reverse=True)
            optimized_placements = []
            placed_positions = []
            for part in parts:
                placed = False
                for x in range(0, sheet_w - int(part['width']), 10):
                    for y in range(0, sheet_h - int(part['height']), 10):
                        if self.can_place(part, x, y, placed_positions):
                            optimized_placements.append({
                                'part_id': part['part_id'],
                                'ref': part['ref'],
                                'x': x,
                                'y': y,
                                'width': part['width'],
                                'height': part['height'],
                                'rotated': False
                            })
                            placed_positions.append((x, y, x + part['width'], y + part['height']))
                            placed = True
                            break
                    if placed:
                        break
                if not placed and part['width'] != part['height']:
                    for x in range(0, sheet_w - int(part['height']), 10):
                        for y in range(0, sheet_h - int(part['width']), 10):
                            if self.can_place(part, x, y, placed_positions, rotated=True):
                                optimized_placements.append({
                                    'part_id': part['part_id'],
                                    'ref': part['ref'],
                                    'x': x,
                                    'y': y,
                                    'width': part['height'],
                                    'height': part['width'],
                                    'rotated': True
                                })
                                placed_positions.append((x, y, x + part['height'], y + part['width']))
                                placed = True
                                break
                        if placed:
                            break
                if not placed:
                    optimized_placements.append({
                        'part_id': part['part_id'],
                        'ref': part['ref'],
                        'x': part['x'],
                        'y': part['y'],
                        'width': part['width'],
                        'height': part['height'],
                        'rotated': part['rotated']
                    })
            return optimized_placements
        except Exception as e:
            print(f"Optimization failed: {e}")
            return None

    def can_place(self, part, x, y, placed_positions, rotated=False):
        if rotated:
            w, h = part['height'], part['width']
        else:
            w, h = part['width'], part['height']
        new_rect = (x, y, x + w, y + h)
        for rect in placed_positions:
            if self.rect_overlap(new_rect, rect):
                return False
        if x < 0 or y < 0 or (x + w) > 2000 or (y + h) > 1000:
            return False
        return True

    def rect_overlap(self, r1, r2):
        return not (r1[2] < r2[0] or 
                   r1[0] > r2[2] or 
                   r1[3] < r2[1] or 
                   r1[1] > r2[3])

    def calculate_sheet_efficiency(self, sheet_size, placements):
        w, h = sheet_size
        sheet_area = w * h
        used_area = sum(p.width * p.height for p in placements)
        waste_area = sheet_area - used_area
        waste_percent = waste_area / sheet_area
        coverage = used_area / sheet_area
        density = len(placements) / (sheet_area / 1000000)
        efficiency = used_area / sheet_area * 100
        return {
            'used_area': used_area,
            'waste_area': waste_area,
            'waste_percent': waste_percent,
            'coverage': coverage,
            'density': density,
            'efficiency': efficiency
        }
