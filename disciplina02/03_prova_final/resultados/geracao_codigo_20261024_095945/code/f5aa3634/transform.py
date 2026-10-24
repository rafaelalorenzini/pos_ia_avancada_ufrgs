import numpy as np
from scipy.ndimage import label

def transform(grid):
    grid = np.array(grid)
    mask = (grid != 0)
    labeled_array, num_features = label(mask)
    
    # Find all components that contain color 5
    comp_indices = []
    for i in range(1, num_features + 1):
        if 5 in grid[labeled_array == i]:
            comp_indices.append(i)
            
    # If multiple components contain 5, choose the one with unique colors not present in other components
    best_comp = comp_indices[0]
    if len(comp_indices) > 1:
        other_colors = set()
        for i in range(1, num_features + 1):
            if i not in comp_indices:
                other_colors.update(grid[labeled_array == i])
                
        best_score = -1
        for i in comp_indices:
            comp_mask = (labeled_array == i)
            comp_colors = set(grid[comp_mask]) - {0}
            score = len(comp_colors - other_colors)
            if score > best_score:
                best_score = score
                best_comp = i
                
    comp_mask = (labeled_array == best_comp)
    rows, cols = np.where(comp_mask)
    
    # Find rows containing core shape pixels (color >= 5) to trim peripheral pointer pixels
    core_rows = []
    for r in range(rows.min(), rows.max() + 1):
        row_colors = grid[r, comp_mask[r]]
        if any(c >= 5 for c in row_colors):
            core_rows.append(r)
            
    if core_rows:
        min_r, max_r = min(core_rows), max(core_rows)
        sub_mask = np.zeros_like(comp_mask)
        sub_mask[min_r:max_r+1, :] = comp_mask[min_r:max_r+1, :]
        sub_rows, sub_cols = np.where(sub_mask)
        min_c, max_c = sub_cols.min(), sub_cols.max()
        subgrid = grid[min_r:max_r+1, min_c:max_c+1]
        sub_comp_mask = comp_mask[min_r:max_r+1, min_c:max_c+1]
        subgrid = np.where(sub_comp_mask, subgrid, 0)
        return subgrid.tolist()
    
    min_r, max_r = rows.min(), rows.max()
    min_c, max_c = cols.min(), cols.max()
    subgrid = grid[min_r:max_r+1, min_c:max_c+1]
    return subgrid.tolist()
