import numpy as np
from scipy.ndimage import label

def transform(grid):
    arr = np.array(grid)
    R, C = arr.shape
    
    # Identify zero cells
    is_zero = (arr == 0)
    
    # Use 4-connectivity to label connected components of 0s
    struct = np.array([[0, 1, 0], 
                       [1, 1, 1], 
                       [0, 1, 0]])
    labeled_zeros, num_features = label(is_zero, structure=struct)
    
    # Find which labels touch the border (background zeros)
    border_labels = set()
    for r in range(R):
        for c in range(C):
            if r == 0 or r == R - 1 or c == 0 or c == C - 1:
                if is_zero[r, c]:
                    border_labels.add(labeled_zeros[r, c])
                    
    out = arr.copy()
    
    # Process each enclosed zero component (hole)
    for lbl in range(1, num_features + 1):
        if lbl in border_labels:
            continue
        
        coords = np.argwhere(labeled_zeros == lbl)
        if len(coords) == 0:
            continue
            
        min_r, min_c = coords.min(axis=0)
        max_r, max_c = coords.max(axis=0)
        
        height = max_r - min_r + 1
        width = max_c - min_c + 1
        
        # Check if the hole is a solid square
        if height == width and len(coords) == height * width:
            out[min_r:max_r+1, min_c:max_c+1] = 2
                
    return out.tolist()
