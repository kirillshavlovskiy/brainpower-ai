# filename: battleship.py

import random

# Create a 5x5 grid filled with 'O' to represent empty cells
def create_grid():
    return [['O' for _ in range(5)] for _ in range(5)]

# Place 3 ships randomly on the grid
def place_ships(grid):
    for _ in range(3):
        while True:
            row = random.randint(0, 4)
            col = random.randint(0, 4)
            if grid[row][col] == 'O':
                grid[row][col] = 'S'
                break

# Check if a cell contains a ship
def check_hit(grid, row, col):
    return grid[row][col] == 'S'

# Check if all ships have been sunk
def check_win(grid):
    for row in grid:
        if 'S' in row:
            return False
    return True

# Print the grid
def print_grid(grid):
    for row in grid:
        print(' '.join(row))
    print()

# Create the grids for the computer and the user
computer_grid = create_grid()
user_grid = create_grid()

# Place the ships on the grids
place_ships(computer_grid)
place_ships(user_grid)

# Print the grids
print("Computer's grid:")
print_grid(computer_grid)
print("User's grid:")
print_grid(user_grid)