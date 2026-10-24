import numpy as np

def transform(grid):
    arr = np.array(grid, dtype=int)
    H, W = arr.shape
    visited = np.zeros((H, W), dtype=bool)
    
    output = arr.copy()
    
    for r in range(H):
        for c in range(W):
            if arr[r, c] == 8 and not visited[r, c]:
                # BFS to find component of color 8
                comp = []
                queue = [(r, c)]
                visited[r, c] = True
                while queue:
                    curr_r, curr_c = queue.pop(0)
                    comp.append((curr_r, curr_c))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = curr_r + dr, curr_c + dc
                        if 0 <= nr < H and 0 <= nc < W and arr[nr, nc] == 8 and not visited[nr, nc]:
                            visited[nr, nc] = True
                            queue.append((nr, nc))
                
                # Find bounding box of the component
                min_r = min(p[0] for p in comp)
                max_r = max(p[0] for p in comp)
                min_c = min(p[1] for p in comp)
                max_c = max(p[1] for p in comp)
                
                # Check if it fits in a 2x2 bounding box and has 3 pixels
                if max_r - min_r == 1 and max_c - min_c == 1 and len(comp) == 3:
                    # Find the empty cell (0) within this 2x2 bounding box and set it to 1
                    for br in range(min_r, max_r + 1):
                        for bc in range(min_c, max_c + 1):
                            if arr[br, bc] == 0:
                                output[br, bc] = 1
                                
    return output.tolist()
