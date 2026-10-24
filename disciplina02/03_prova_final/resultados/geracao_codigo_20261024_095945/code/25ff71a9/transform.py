def transform(grid):
    h = len(grid)
    w = len(grid[0])
    output = [[0] * w for _ in range(h)]
    for r in range(h - 1):
        output[r + 1] = list(grid[r])
    return output
