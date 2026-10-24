def transform(grid):
    # Find all non-zero coordinates
    non_zero = []
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] != 0:
                non_zero.append((r, c))
                
    min_r = min(r for r, c in non_zero)
    min_c = min(c for r, c in non_zero)
    
    # Extract 3x3 subgrid starting from (min_r, min_c)
    output = []
    for r in range(min_r, min_r + 3):
        row = []
        for c in range(min_c, min_c + 3):
            row.append(grid[r][c])
        output.append(row)
        
    return output
