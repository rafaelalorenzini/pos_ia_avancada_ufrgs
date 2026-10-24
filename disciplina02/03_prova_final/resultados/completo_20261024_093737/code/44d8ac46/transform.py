import numpy as np

def transform(grid):
    grid = np.array(grid)
    h, w = grid.shape
    
    # 1. Find background (0s connected to the border)
    visited = np.zeros((h, w), dtype=bool)
    queue = []
    
    for r in range(h):
        for c in range(w):
            if (r == 0 or r == h - 1 or c == 0 or c == w - 1) and grid[r, c] == 0:
                if not visited[r, c]:
                    queue.append((r, c))
                    visited[r, c] = True
                    
    head = 0
    while head < len(queue):
        r, c = queue[head]
        head += 1
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and grid[nr, nc] == 0:
                visited[nr, nc] = True
                queue.append((nr, nc))
                
    # Interior 0s are 0s that are not visited
    interior = (grid == 0) & (~visited)
    
    # 2. Find connected components of interior 0s using BFS
    comp_visited = np.zeros((h, w), dtype=bool)
    out = grid.copy()
    
    for r in range(h):
        for c in range(w):
            if interior[r, c] and not comp_visited[r, c]:
                comp_cells = []
                q = [(r, c)]
                comp_visited[r, c] = True
                q_head = 0
                while q_head < len(q):
                    curr_r, curr_c = q[q_head]
                    q_head += 1
                    comp_cells.append((curr_r, curr_c))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = curr_r + dr, curr_c + dc
                        if 0 <= nr < h and 0 <= nc < w and interior[nr, nc] and not comp_visited[nr, nc]:
                            comp_visited[nr, nc] = True
                            q.append((nr, nc))
                
                # Analyze component bounding box
                rows = [cell[0] for cell in comp_cells]
                cols = [cell[1] for cell in comp_cells]
                min_r, max_r = min(rows), max(rows)
                min_c, max_c = min(cols), max(cols)
                
                height = max_r - min_r + 1
                width = max_c - min_c + 1
                
                # If it's a solid square hole, fill it with 2
                if height == width and len(comp_cells) == height * width:
                    for cr in range(min_r, max_r + 1):
                        for cc in range(min_c, max_c + 1):
                            out[cr, cc] = 2
                            
    return out.tolist()
