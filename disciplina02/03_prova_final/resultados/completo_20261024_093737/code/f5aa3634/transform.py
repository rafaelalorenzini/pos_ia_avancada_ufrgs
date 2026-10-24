import numpy as np

def transform(grid):
    grid = np.array(grid)
    H, W = grid.shape
    
    # Find all non-zero pixels
    non_zero = np.argwhere(grid != 0)
    if len(non_zero) == 0:
        return []
        
    visited = np.zeros((H, W), dtype=bool)
    components = []
    
    for r, c in non_zero:
        if visited[r, c]:
            continue
        # BFS to find connected component (8-connectivity)
        comp_pixels = []
        queue = [(r, c)]
        visited[r, c] = True
        
        while queue:
            curr_r, curr_c = queue.pop(0)
            comp_pixels.append((curr_r, curr_c))
            
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0:
                        continue
                    nr, nc = curr_r + dr, curr_c + dc
                    if 0 <= nr < H and 0 <= nc < W:
                        if not visited[nr, nc] and grid[nr, nc] != 0:
                            visited[nr, nc] = True
                            queue.append((nr, nc))
                            
        components.append(comp_pixels)
        
    # Filter components with height == 3
    valid_components = []
    for comp in components:
        rows = [p[0] for p in comp]
        cols = [p[1] for p in comp]
        min_r, max_r = min(rows), max(rows)
        min_c, max_c = min(cols), max(cols)
        height = max_r - min_r + 1
        if height == 3:
            valid_components.append({
                'min_r': min_r,
                'max_r': max_r,
                'min_c': min_c,
                'max_c': max_c,
            })
            
    if not valid_components:
        return []
        
    # Sort by min_r, then min_c to find the first occurrence
    valid_components.sort(key=lambda x: (x['min_r'], x['min_c']))
    
    target = valid_components[0]
    subgrid = grid[target['min_r']:target['max_r']+1, target['min_c']:target['max_c']+1]
    
    return subgrid.tolist()
