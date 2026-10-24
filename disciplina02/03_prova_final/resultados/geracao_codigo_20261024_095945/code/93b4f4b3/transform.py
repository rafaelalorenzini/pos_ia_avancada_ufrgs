def transform(grid):
    grid = [list(row) for row in grid]
    H = len(grid)
    W = len(grid[0])
    
    frame_color = grid[0][0]
    
    # Find frame width W_frame
    W_frame = 0
    while W_frame < W and grid[0][W_frame] == frame_color:
        W_frame += 1
        
    # Find separator rows (rows within W_frame that are entirely frame_color)
    separators = []
    for r in range(H):
        if all(grid[r][c] == frame_color for c in range(W_frame)):
            separators.append(r)
            
    # Sub-blocks are between consecutive separators
    sub_blocks = []
    for i in range(len(separators) - 1):
        r_start = separators[i] + 1
        r_end = separators[i+1] - 1
        if r_start <= r_end:
            sub_blocks.append((r_start, r_end))
            
    # Extract shapes from the right side for each sub-block
    shapes = []
    for idx, (r_start, r_end) in enumerate(sub_blocks):
        pixels = []
        color = None
        for r in range(r_start, r_end + 1):
            for c in range(W_frame, W):
                val = grid[r][c]
                if val != 0:
                    pixels.append((r, c))
                    color = val
        if pixels:
            min_r = min(p[0] for p in pixels)
            min_c = min(p[1] for p in pixels)
            pattern = frozenset((p[0] - min_r, p[1] - min_c) for p in pixels)
            shapes.append({'id': idx, 'color': color, 'pattern': pattern})
            
    # Extract frame hole patterns and min_c for each sub-block
    frame_info = []
    for idx, (r_start, r_end) in enumerate(sub_blocks):
        holes = []
        for r in range(r_start, r_end + 1):
            for c in range(W_frame):
                if grid[r][c] == 0:
                    holes.append((r, c))
        if holes:
            min_r = min(p[0] for p in holes)
            min_c = min(p[1] for p in holes)
            pattern = frozenset((p[0] - min_r, p[1] - min_c) for p in holes)
            frame_info.append({'id': idx, 'pattern': pattern, 'min_c': min_c, 'r_start': r_start})
            
    # Match shapes to frame sub-blocks by pattern equality
    matching = {}
    for shape in shapes:
        for fi in frame_info:
            if shape['pattern'] == fi['pattern']:
                matching[shape['id']] = fi['id']
                break
                
    # Build output grid (the left frame with separators)
    output = [[grid[r][c] for c in range(W_frame)] for r in range(H)]
    
    # Place matched shapes into their target frame sub-blocks
    for shape in shapes:
        shape_id = shape['id']
        color = shape['color']
        pattern = shape['pattern']
        if shape_id in matching:
            target_id = matching[shape_id]
            fi = next(item for item in frame_info if item['id'] == target_id)
            r_start = fi['r_start']
            min_c = fi['min_c']
            
            for rel_r, rel_c in pattern:
                output[r_start + rel_r][min_c + rel_c] = color
                
    return output
