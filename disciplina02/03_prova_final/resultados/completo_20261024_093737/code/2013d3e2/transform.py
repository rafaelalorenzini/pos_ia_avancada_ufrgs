def transform(grid):
    non_zero = [(r, c) for r, row in enumerate(grid) for c, val in enumerate(row) if val != 0]
    min_r = min(r for r, c in non_zero)
    min_c = min(c for r, c in non_zero)
    
    output = []
    for r in range(min_r, min_r + 3):
        output.append(grid[r][min_c : min_c + 3])
    return output
