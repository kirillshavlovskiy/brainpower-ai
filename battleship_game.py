# filename: battleship_game.py

def guess_ship(grid, row, col):
    if grid[row][col] == 'S':
        print("Hit!")
        grid[row][col] = 'H'
    elif grid[row][col] == 'H':
        print("You already hit this spot.")
    else:
        print("Miss!")
        grid[row][col] = 'M'

def check_sunk_ship(grid, ship_size):
    hit_count = sum(row.count('H') for row in grid)
    if hit_count == ship_size:
        return True
    return False

def print_grid(grid):
    for row in grid:
        print(" ".join(row))
    print()

# Initialize a 5x5 grid
grid = [['O' for _ in range(5)] for _ in range(5)]

# Place a ship of size 3 at position (2, 2) horizontally
for i in range(3):
    grid[2][2 + i] = 'S'

# User guesses a coordinate
guess_ship(grid, 2, 2)
print_grid(grid)

# Check if the ship is sunk
if check_sunk_ship(grid, 3):
    print("Ship is sunk!")
else:
    print("Ship is not sunk yet.")