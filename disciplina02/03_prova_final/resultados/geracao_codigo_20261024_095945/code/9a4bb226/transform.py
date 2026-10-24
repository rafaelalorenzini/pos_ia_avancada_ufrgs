import numpy as np

def transform(grid):
    grid = np.array(grid)
    h, w = grid.shape
    
    for r in range(h - 2):
        for c in range(w - 2):
            subgrid = grid[r:r+3, c:c+3]
            if np.all(subgrid != 0):
                if len(np.unique(subgrid)) == 3:
                    return subgrid.tolist()
                    
    return []
