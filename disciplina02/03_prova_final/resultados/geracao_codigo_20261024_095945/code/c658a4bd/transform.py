import numpy as np


def transform(grid):
  grid = np.array(grid)
  # Find all unique non-zero colors
  colors = [c for c in np.unique(grid) if c != 0]

  # Compute bounding box area for each color object
  color_areas = []
  for c in colors:
    rows, cols = np.where(grid == c)
    min_r, max_r = rows.min(), rows.max()
    min_c, max_c = cols.min(), cols.max()
    area = (max_r - min_r + 1) * (max_c - min_c + 1)
    color_areas.append((area, c, min_r, max_r, min_c, max_c))

  # Sort by area ascending (smallest / innermost first, largest / outermost last)
  color_areas.sort(key=lambda x: x[0])

  # Initialize with the innermost object
  _, c0, min_r, max_r, min_c, max_c = color_areas[0]
  sub = grid[min_r : max_r + 1, min_c : max_c + 1]
  current = np.where(sub == c0, c0, 0)

  def wrap_grid(inner_grid, color):
    h, w = inner_grid.shape
    new_grid = np.zeros((h + 2, w + 2), dtype=int)
    new_grid[0, :] = color
    new_grid[-1, :] = color
    new_grid[:, 0] = color
    new_grid[:, -1] = color
    new_grid[1 : h + 1, 1 : w + 1] = inner_grid
    return new_grid

  # Iteratively wrap with each outer layer
  for _, c, _, _, _, _ in color_areas[1:]:
    current = wrap_grid(current, c)

  return current.tolist()
