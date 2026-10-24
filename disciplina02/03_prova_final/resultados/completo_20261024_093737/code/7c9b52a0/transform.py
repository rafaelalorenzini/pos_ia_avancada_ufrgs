import numpy as np
from scipy.ndimage import label

def transform(grid):
    grid = np.array(grid)
    bg = grid[0][0]
    
    # Find connected components of non-background pixels
    mask = (grid != bg)
    labeled, num_features = label(mask)
    
    windows = []
    for i in range(1, num_features + 1):
        r_indices, c_indices = np.where(labeled == i)
        r_min, r_max = r_indices.min(), r_indices.max()
        c_min, c_max = c_indices.min(), c_indices.max()
        
        # Expand bounding box outward until hitting background (bg)
        while r_min > 0 and not np.any(grid[r_min - 1, c_min:c_max + 1] == bg):
            r_min -= 1
        while r_max < grid.shape[0] - 1 and not np.any(grid[r_max + 1, c_min:c_max + 1] == bg):
            r_max += 1
        while c_min > 0 and not np.any(grid[r_min:r_max + 1, c_min - 1] == bg):
            c_min -= 1
        while c_max < grid.shape[1] - 1 and not np.any(grid[r_min:r_max + 1, c_max + 1] == bg):
            c_max += 1
            
        win = grid[r_min:r_max + 1, c_min:c_max + 1].copy()
        # Replace any background pixels inside the window with 0
        win[win == bg] = 0
        windows.append(win)
        
    if not windows:
        return grid.tolist()
        
    # Find max height and width among all windows to ensure uniform overlay size
    max_h = max(w.shape[0] for w in windows)
    max_w = max(w.shape[1] for w in windows)
    
    overlay = np.zeros((max_h, max_w), dtype=int)
    for w in windows:
        h, width = w.shape
        sub = overlay[:h, :width]
        sub[w != 0] = w[w != 0]
        
    # Crop leading and trailing all-zero rows and columns
    non_zero_rows = np.any(overlay != 0, axis=1)
    non_zero_cols = np.any(overlay != 0, axis=0)
    
    if not np.any(non_zero_rows) or not np.any(non_zero_cols):
        return overlay.tolist()
        
    r_start, r_end = np.where(non_zero_rows)[0][[0, -1]]
    c_start, c_end = np.where(non_zero_cols)[0][[0, -1]]
    
    result = overlay[r_start:r_end + 1, c_start:c_end + 1]
    return result.tolist()
