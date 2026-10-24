def transform(grid):
    R = len(grid)
    C = len(grid[0])
    
    # Find the frame
    frame_box = None
    border_col = None
    
    for r1 in range(R):
        for r2 in range(r1 + 2, R):
            for c1 in range(C):
                for c2 in range(c1 + 2, C):
                    c = grid[r1][c1]
                    if c == 0:
                        continue
                    
                    # Verify top and bottom rows
                    is_frame = True
                    for j in range(c1, c2 + 1):
                        if grid[r1][j] != c or grid[r2][j] != c:
                            is_frame = False
                            break
                    if not is_frame:
                        continue
                    
                    # Verify left and right columns
                    for i in range(r1, r2 + 1):
                        if grid[i][c1] != c or grid[i][c2] != c:
                            is_frame = False
                            break
                    
                    if is_frame:
                        frame_box = (r1, c1, r2, c2)
                        border_col = c
                        break
            if frame_box:
                break
        if frame_box:
            break
            
    r1, c1, r2, c2 = frame_box
    
    # Collect interior colors
    interior_colors = set()
    for r in range(r1 + 1, r2):
        for c in range(c1 + 1, c2):
            interior_colors.add(grid[r][c])
            
    # Find outside horizontal pairs
    mapping = {}
    for r in range(R):
        for c in range(C - 1):
            in_frame_1 = (r1 <= r <= r2 and c1 <= c <= c2)
            in_frame_2 = (r1 <= r <= r2 and c1 <= c + 1 <= c2)
            
            if not in_frame_1 and not in_frame_2:
                v1 = grid[r][c]
                v2 = grid[r][c + 1]
                if v1 != 0 and v2 != 0:
                    if v1 in interior_colors and v2 not in interior_colors:
                        mapping[v1] = v2
                    elif v2 in interior_colors and v1 not in interior_colors:
                        mapping[v2] = v1
                        
    # Build output grid
    out_height = r2 - r1 + 1
    out_width = c2 - c1 + 1
    
    output = [[border_col for _ in range(out_width)] for _ in range(out_height)]
    
    for i in range(1, out_height - 1):
        for j in range(1, out_width - 1):
            orig_r = r1 + i
            orig_c = c1 + j
            val = grid[orig_r][orig_c]
            output[i][j] = mapping.get(val, val)
            
    return output
