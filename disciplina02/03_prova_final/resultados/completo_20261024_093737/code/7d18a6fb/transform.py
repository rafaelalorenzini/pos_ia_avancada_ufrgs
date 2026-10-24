def transform(grid):
    R = len(grid)
    C = len(grid[0])
    
    grid_r, grid_c = -1, -1
    markers_to_check = {(1, 1), (1, 5), (5, 1), (5, 5)}
    
    for r in range(R - 6):
        for c in range(C - 6):
            is_target = True
            for dr in range(7):
                for dc in range(7):
                    if (dr, dc) not in markers_to_check:
                        if grid[r + dr][c + dc] != 1:
                            is_target = False
                            break
                if not is_target:
                    break
            if is_target:
                grid_r, grid_c = r, c
                break
                
    c_tl = grid[grid_r + 1][grid_c + 1]
    c_tr = grid[grid_r + 1][grid_c + 5]
    c_bl = grid[grid_r + 5][grid_c + 1]
    c_br = grid[grid_r + 5][grid_c + 5]
    
    def get_shape(color):
        pixels = []
        for r in range(R):
            for c in range(C):
                if grid[r][c] == color:
                    pixels.append((r, c))
        if not pixels:
            return [[0]*3 for _ in range(3)]
        min_r = min(p[0] for p in pixels)
        min_c = min(p[1] for p in pixels)
        
        subgrid = []
        for dr in range(3):
            row = []
            for dc in range(3):
                nr = min_r + dr
                nc = min_c + dc
                if 0 <= nr < R and 0 <= nc < C:
                    row.append(grid[nr][nc])
                else:
                    row.append(0)
            subgrid.append(row)
        return subgrid

    tl_shape = get_shape(c_tl)
    tr_shape = get_shape(c_tr)
    bl_shape = get_shape(c_bl)
    br_shape = get_shape(c_br)
    
    output = [[0] * 7 for _ in range(7)]
    
    for r in range(3):
        for c in range(3):
            output[r][c] = tl_shape[r][c]
            output[r][c + 4] = tr_shape[r][c]
            output[r + 4][c] = bl_shape[r][c]
            output[r + 4][c + 4] = br_shape[r][c]
            
    return output
