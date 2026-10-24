def transform(grid):
    height = len(grid)
    width = len(grid[0])
    
    points = []
    for r in range(height):
        for c in range(width):
            if grid[r][c] != 0:
                points.append((r, c, grid[r][c]))
                
    r1, c1, v1 = points[0]
    r2, c2, v2 = points[1]
    
    dr = r2 - r1
    dc = c2 - c1
    
    output = [[0] * width for _ in range(height)]
    
    if dc == 0:
        is_vertical = False
    elif dr == 0:
        is_vertical = True
    else:
        if abs(dc) <= abs(dr):
            is_vertical = True
        else:
            is_vertical = False
            
    if is_vertical:
        step = abs(dc)
        direction = 1 if dc >= 0 else -1
        
        k = 0
        c = c1
        while 0 <= c < width:
            color = v1 if k % 2 == 0 else v2
            for r in range(height):
                output[r][c] = color
            k += 1
            c += direction * step
    else:
        step = abs(dr)
        direction = 1 if dr >= 0 else -1
        
        k = 0
        r = r1
        while 0 <= r < height:
            color = v1 if k % 2 == 0 else v2
            for c in range(width):
                output[r][c] = color
            k += 1
            r += direction * step
            
    return output
