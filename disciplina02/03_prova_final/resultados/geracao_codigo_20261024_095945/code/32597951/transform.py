import numpy as np

def transform(grid):
    arr = np.array(grid)
    h, w = arr.shape
    output = arr.copy()
    
    for r in range(h):
        for c in range(w):
            if arr[r, c] == 1:
                # Count 8-connected neighbors that are equal to 8
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        if dr == 0 and dc == 0:
                            continue
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < h and 0 <= nc < w:
                            if arr[nr, nc] == 8:
                                count += 1
                if count >= 2:
                    output[r, c] = 3
                    
    return output.tolist()
