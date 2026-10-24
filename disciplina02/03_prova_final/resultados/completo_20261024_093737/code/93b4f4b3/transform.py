def transform(grid):
    grid = [list(row) for row in grid]
    H = len(grid)
    W = len(grid[0])
    
    # Find separator column c_mid
    c_mid = -1
    for c in range(W):
        if all(grid[r][c] == 0 for r in range(H)):
            c_mid = c
            break
    if c_mid == -1:
        c_mid = W // 2
        
    left_grid = [row[:c_mid] for row in grid]
    right_grid = [row[c_mid+1:] for row in grid]
    
    H_left = len(left_grid)
    W_left = len(left_grid[0])
    container_color = left_grid[0][0]
    
    solid_rows = []
    for r in range(H_left):
        if all(left_grid[r][c] == container_color for c in range(W_left)):
            solid_rows.append(r)
            
    all_rows = [-1] + solid_rows + [H_left]
    hole_regions = []
    for i in range(len(all_rows) - 1):
        r_start = all_rows[i] + 1
        r_end = all_rows[i+1] - 1
        if r_start <= r_end:
            has_holes = any(left_grid[r][c] != container_color for r in range(r_start, r_end+1) for c in range(W_left))
            if has_holes:
                sub = [left_grid[r] for r in range(r_start, r_end+1)]
                hole_rows = [r for r in range(len(sub)) for c in range(W_left) if sub[r][c] == 0]
                hole_cols = [c for c in range(W_left) for r in range(len(sub)) if sub[r][c] == 0]
                if hole_rows and hole_cols:
                    hr_min, hr_max = min(hole_rows), max(hole_rows)
                    hc_min, hc_max = min(hole_cols), max(hole_cols)
                    mask = tuple(tuple(sub[r][c] == 0 for c in range(hc_min, hc_max+1)) for r in range(hr_min, hr_max+1))
                    hole_regions.append({
                        'r_start_global': r_start + hr_min,
                        'c_start_global': hc_min,
                        'mask': mask
                    })
                    
    H_r = len(right_grid)
    W_r = len(right_grid[0]) if H_r > 0 else 0
    empty_rows = set()
    for r in range(H_r):
        if all(right_grid[r][c] == 0 for c in range(W_r)):
            empty_rows.add(r)
            
    shape_intervals = []
    in_shape = False
    s_start = 0
    for r in range(H_r):
        is_empty = r in empty_rows
        if not is_empty and not in_shape:
            in_shape = True
            s_start = r
        elif is_empty and in_shape:
            in_shape = False
            shape_intervals.append((s_start, r - 1))
    if in_shape:
        shape_intervals.append((s_start, H_r - 1))
        
    shapes = []
    for (s_start, s_end) in shape_intervals:
        sub = [right_grid[r] for r in range(s_start, s_end+1)]
        nz_rows = [r for r in range(len(sub)) for c in range(W_r) if sub[r][c] != 0]
        nz_cols = [c for c in range(W_r) for r in range(len(sub)) if sub[r][c] != 0]
        if nz_rows and nz_cols:
            sr_min, sr_max = min(nz_rows), max(nz_rows)
            sc_min, sc_max = min(nz_cols), max(nz_cols)
            mask = tuple(tuple(sub[r][c] != 0 for c in range(sc_min, sc_max+1)) for r in range(sr_min, sr_max+1))
            shape_sub = [[sub[r][c] for c in range(sc_min, sc_max+1)] for r in range(sr_min, sr_max+1)]
            shapes.append({
                'mask': mask,
                'grid': shape_sub
            })
            
    out_grid = [row[:] for row in left_grid]
    matched_shapes = [False] * len(shapes)
    for hr in hole_regions:
        for j, sh in enumerate(shapes):
            if matched_shapes[j]:
                continue
            if hr['mask'] == sh['mask']:
                matched_shapes[j] = True
                sh_grid = sh['grid']
                for lr in range(len(sh_grid)):
                    for lc in range(len(sh_grid[0])):
                        if sh_grid[lr][lc] != 0:
                            target_r = hr['r_start_global'] + lr
                            target_c = hr['c_start_global'] + lc
                            out_grid[target_r][target_c] = sh_grid[lr][lc]
                break
                
    return out_grid
