def transform(grid):
    rows = len(grid)
    cols = len(grid[0])
    
    pairs = []
    
    # Find all 2x2 blocks of color 8
    for r in range(rows - 1):
        for c in range(cols - 1):
            if (grid[r][c] == 8 and grid[r][c+1] == 8 and 
                grid[r+1][c] == 8 and grid[r+1][c+1] == 8):
                pairs.append((r, c))
                
    # Group by row r
    row_dict = {}
    for r, c in pairs:
        if r not in row_dict:
            row_dict[r] = []
        row_dict[r].append(c)
        
    # Sort rows top-to-bottom
    sorted_rows = sorted(row_dict.keys())
    
    output = []
    for r in sorted_rows:
        col_indices = sorted(row_dict[r])
        if len(col_indices) >= 2:
            c1 = col_indices[0]
            c2 = col_indices[-1]
            
            # Extract the 2 rows between the left and right 2x2 blocks
            for dr in range(2):
                row_slice = grid[r + dr][c1 + 2 : c2]
                output.append(row_slice)
                
    return output
