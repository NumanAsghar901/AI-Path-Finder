import pygame
import sys
import random
import time
from collections import deque
from queue import PriorityQueue
from enum import Enum
import heapq

class CellType(Enum):
    EMPTY = 0
    WALL = 1
    START = 2
    TARGET = 3
    FRONTIER = 4
    EXPLORED = 5
    PATH = 6
    DYNAMIC_OBSTACLE = 7

class Colors:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)           # Static walls
    GREEN = (0, 255, 0)         # Start point
    RED = (255, 0, 0)           # Target point
    BLUE = (0, 100, 255)        # Frontier nodes
    YELLOW = (255, 255, 0)      # Final path
    PINK = (255, 20, 147)       # Dynamic obstacles
    GRAY = (128, 128, 128)      # Grid lines
    LIGHT_GRAY = (200, 200, 200)
    DARK_GRAY = (64, 64, 64)
    LIGHT_BLUE = (173, 216, 230) # Explored nodes

class Node:
    def __init__(self, x, y, cost=0, parent=None):
        self.x = x
        self.y = y
        self.cost = cost
        self.parent = parent
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))
    
    def __lt__(self, other):
        return self.cost < other.cost

class Button:
    def __init__(self, x, y, width, height, text, color=Colors.LIGHT_GRAY, text_color=Colors.BLACK):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.text_color = text_color
        self.font = pygame.font.Font(None, 24)
        self.hovered = False
    
    def draw(self, screen):
        color = Colors.WHITE if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, Colors.BLACK, self.rect, 2)
        
        text_surface = self.font.render(self.text, True, self.text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)
    
    def update_hover(self, pos):
        self.hovered = self.rect.collidepoint(pos)

class GOODPERFORMANCETIMEAPPathfinder:
    def __init__(self):
        pygame.init()
        
        # Grid settings
        self.grid_size = 25
        self.rows = 20
        self.cols = 25
        self.grid_width = self.cols * self.grid_size
        self.grid_height = self.rows * self.grid_size
        
        # Window dimensions - Add space for bottom legend
        self.panel_width = 300
        self.bottom_legend_height = 80  # Space for horizontal legend
        self.total_width = self.grid_width + self.panel_width
        self.total_height = max(self.grid_height + self.bottom_legend_height, 600)
        
        self.screen = pygame.display.set_mode((self.total_width, self.total_height))
        pygame.display.set_caption("GOOD PERFORMANCE TIME APP")
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        self.title_font = pygame.font.Font(None, 32)
        
        # Grid initialization
        self.grid = [[CellType.EMPTY for _ in range(self.cols)] for _ in range(self.rows)]
        self.start = (1, 1)
        self.target = (self.rows - 2, self.cols - 2)
        self.grid[self.start[0]][self.start[1]] = CellType.START
        self.grid[self.target[0]][self.target[1]] = CellType.TARGET
        
        # Algorithm settings
        self.algorithms = ["BFS", "DFS", "UCS", "DLS", "IDDFS", "Bidirectional"]
        self.current_algorithm = "BFS"
        
        # Search state
        self.is_searching = False
        self.search_complete = False
        self.step_delay = 50
        self.paused = False
        self.path_blocked = False
        
        # Mode settings
        self.current_mode = "WALL"
        self.modes = ["WALL", "START", "TARGET"]
        
        # Dynamic obstacles
        self.dynamic_obstacle_probability = 0.001
        self.enable_dynamic_obstacles = True
        self.dynamic_obstacles_added = []
        
        # Movement directions in clockwise order with all diagonals
        self.directions = [
            (-1, 0),   # Up
            (0, 1),    # Right
            (1, 0),    # Bottom
            (1, 1),    # Bottom-Right (Diagonal)
            (0, -1),   # Left
            (-1, -1),  # Top-Left (Diagonal)
            (-1, 1),   # Top-Right (Diagonal)
            (1, -1)    # Bottom-Left (Diagonal)
        ]
        
        self.setup_ui()
        self.setup_sample_maze()
    
    def setup_ui(self):
        """Setup UI buttons and controls"""
        panel_x = self.grid_width + 10
        
        # Algorithm selection buttons
        self.algo_buttons = []
        for i, algo in enumerate(self.algorithms):
            button = Button(panel_x, 50 + i * 35, 120, 30, algo)
            self.algo_buttons.append(button)
        
        # Control buttons
        self.start_button = Button(panel_x, 280, 80, 30, "Start", Colors.GREEN)
        self.pause_button = Button(panel_x + 90, 280, 80, 30, "Pause", Colors.YELLOW)
        self.reset_button = Button(panel_x, 320, 80, 30, "Reset", Colors.RED)
        self.clear_button = Button(panel_x + 90, 320, 80, 30, "Clear", Colors.LIGHT_GRAY)
        
        # Mode buttons
        self.mode_buttons = []
        for i, mode in enumerate(self.modes):
            button = Button(panel_x, 380 + i * 35, 120, 30, f"Set {mode}")
            self.mode_buttons.append(button)
        
        # Speed settings
        self.speed_buttons = []
        speeds = [("Slow", 200), ("Normal", 100), ("Fast", 50)]
        for i, (name, delay) in enumerate(speeds):
            button = Button(panel_x + 140, 50 + i * 35, 80, 30, name)
            self.speed_buttons.append((button, delay))
        
        # Dynamic obstacles toggle
        self.dynamic_toggle = Button(panel_x, 500, 150, 30, "Dynamic: ON", Colors.PINK)
    
    def setup_sample_maze(self):
        """Create a sample maze"""
        wall_positions = [
            (5, 8), (6, 8), (7, 8), (8, 8), (9, 8),
            (12, 5), (12, 6), (12, 7), (12, 8), (12, 9), (12, 10),
            (15, 15), (15, 16), (15, 17), (16, 17), (17, 17),
            (3, 15), (4, 15), (10, 20), (11, 20)
        ]
        
        for row, col in wall_positions:
            if 0 <= row < self.rows and 0 <= col < self.cols:
                self.grid[row][col] = CellType.WALL
    
    def is_valid_position(self, row, col):
        """Check if position is valid for movement"""
        return (0 <= row < self.rows and 0 <= col < self.cols and
                self.grid[row][col] not in [CellType.WALL, CellType.DYNAMIC_OBSTACLE])
    
    def get_neighbors(self, node):
        """Get valid neighboring nodes in STRICT clockwise order"""
        neighbors = []
        for dr, dc in self.directions:
            new_row, new_col = node.x + dr, node.y + dc
            if self.is_valid_position(new_row, new_col):
                cost = 1.4 if abs(dr) + abs(dc) == 2 else 1.0
                neighbors.append(Node(new_row, new_col, node.cost + cost, node))
        return neighbors
    
    def add_dynamic_obstacle(self):
        """Add random dynamic obstacle during search"""
        if not self.enable_dynamic_obstacles:
            return False
            
        if random.random() < self.dynamic_obstacle_probability:
            empty_cells = []
            for row in range(self.rows):
                for col in range(self.cols):
                    if self.grid[row][col] == CellType.EMPTY:
                        empty_cells.append((row, col))
            
            if empty_cells:
                row, col = random.choice(empty_cells)
                self.grid[row][col] = CellType.DYNAMIC_OBSTACLE
                self.dynamic_obstacles_added.append((row, col))
                print(f"Dynamic obstacle added at ({row}, {col})")
                return True
        return False
    
    def clear_search_visualization(self):
        """Clear search visualization but keep walls"""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.grid[row][col] in [CellType.FRONTIER, CellType.EXPLORED, CellType.PATH]:
                    self.grid[row][col] = CellType.EMPTY
        
        if self.start:
            self.grid[self.start[0]][self.start[1]] = CellType.START
        if self.target:
            self.grid[self.target[0]][self.target[1]] = CellType.TARGET
    
    def clear_all(self):
        """Clear entire grid"""
        for row in range(self.rows):
            for col in range(self.cols):
                if self.grid[row][col] not in [CellType.START, CellType.TARGET]:
                    self.grid[row][col] = CellType.EMPTY
        self.dynamic_obstacles_added = []
    
    def reconstruct_path(self, node):
        """Reconstruct path from node to start"""
        path = []
        current = node
        while current:
            path.append((current.x, current.y))
            current = current.parent
        return path[::-1]
    
    def visualize_path(self, path):
        """Highlight the final path with step-by-step animation"""
        for i, (row, col) in enumerate(path):
            if (row, col) != self.start and (row, col) != self.target:
                self.grid[row][col] = CellType.PATH
            self.draw()
            pygame.display.flip()
            pygame.time.wait(50)
    
    # Algorithm implementations (keeping the same as before)
    def breadth_first_search(self):
        """BFS with step-by-step visualization"""
        start_node = Node(self.start[0], self.start[1])
        queue = deque([start_node])
        visited = {(start_node.x, start_node.y)}
        
        while queue and not self.paused:
            if self.add_dynamic_obstacle():
                pass
            
            current = queue.popleft()
            
            if (current.x, current.y) == self.target:
                path = self.reconstruct_path(current)
                self.visualize_path(path)
                return True
            
            if (current.x, current.y) != self.start:
                self.grid[current.x][current.y] = CellType.EXPLORED
            
            for neighbor in self.get_neighbors(current):
                pos = (neighbor.x, neighbor.y)
                if pos not in visited and self.is_valid_position(neighbor.x, neighbor.y):
                    visited.add(pos)
                    queue.append(neighbor)
                    if pos != self.target:
                        self.grid[neighbor.x][neighbor.y] = CellType.FRONTIER
            
            self.draw()
            pygame.display.flip()
            pygame.time.wait(self.step_delay)
            
            if not self.handle_events_during_search():
                return False
        
        return False
    
    def depth_first_search(self):
        """DFS with step-by-step visualization"""
        start_node = Node(self.start[0], self.start[1])
        stack = [start_node]
        visited = {(start_node.x, start_node.y)}
        
        while stack and not self.paused:
            if self.add_dynamic_obstacle():
                pass
            
            current = stack.pop()
            
            if (current.x, current.y) == self.target:
                path = self.reconstruct_path(current)
                self.visualize_path(path)
                return True
            
            if (current.x, current.y) != self.start:
                self.grid[current.x][current.y] = CellType.EXPLORED
            
            neighbors = self.get_neighbors(current)
            for neighbor in reversed(neighbors):
                pos = (neighbor.x, neighbor.y)
                if pos not in visited and self.is_valid_position(neighbor.x, neighbor.y):
                    visited.add(pos)
                    stack.append(neighbor)
                    if pos != self.target:
                        self.grid[neighbor.x][neighbor.y] = CellType.FRONTIER
            
            self.draw()
            pygame.display.flip()
            pygame.time.wait(self.step_delay)
            
            if not self.handle_events_during_search():
                return False
        
        return False
    
    def uniform_cost_search(self):
        """UCS with step-by-step visualization"""
        start_node = Node(self.start[0], self.start[1], 0)
        priority_queue = [start_node]
        visited = set()
        costs = {(start_node.x, start_node.y): 0}
        
        while priority_queue and not self.paused:
            if self.add_dynamic_obstacle():
                pass
            
            current = heapq.heappop(priority_queue)
            
            if (current.x, current.y) in visited:
                continue
            
            visited.add((current.x, current.y))
            
            if (current.x, current.y) == self.target:
                path = self.reconstruct_path(current)
                self.visualize_path(path)
                return True
            
            if (current.x, current.y) != self.start:
                self.grid[current.x][current.y] = CellType.EXPLORED
            
            for neighbor in self.get_neighbors(current):
                pos = (neighbor.x, neighbor.y)
                if pos not in visited and self.is_valid_position(neighbor.x, neighbor.y):
                    if pos not in costs or neighbor.cost < costs[pos]:
                        costs[pos] = neighbor.cost
                        heapq.heappush(priority_queue, neighbor)
                        if pos != self.target:
                            self.grid[neighbor.x][neighbor.y] = CellType.FRONTIER
            
            self.draw()
            pygame.display.flip()
            pygame.time.wait(self.step_delay)
            
            if not self.handle_events_during_search():
                return False
        
        return False
    
    def depth_limited_search(self, depth_limit=15):
        """DLS with step-by-step visualization"""
        def dls_recursive(node, depth, visited, path):
            if depth < 0 or self.paused:
                return False
            
            if self.add_dynamic_obstacle():
                pass
            
            pos = (node.x, node.y)
            
            if pos == self.target:
                full_path = path + [pos]
                self.visualize_path(full_path)
                return True
            
            if pos != self.start:
                self.grid[node.x][node.y] = CellType.EXPLORED
            
            visited.add(pos)
            
            for neighbor in self.get_neighbors(node):
                neighbor_pos = (neighbor.x, neighbor.y)
                if (neighbor_pos not in visited and 
                    self.is_valid_position(neighbor.x, neighbor.y)):
                    
                    if neighbor_pos != self.target:
                        self.grid[neighbor.x][neighbor.y] = CellType.FRONTIER
                    
                    self.draw()
                    pygame.display.flip()
                    pygame.time.wait(self.step_delay)
                    
                    if not self.handle_events_during_search():
                        return False
                    
                    if dls_recursive(neighbor, depth - 1, visited.copy(), path + [pos]):
                        return True
            
            return False
        
        start_node = Node(self.start[0], self.start[1])
        return dls_recursive(start_node, depth_limit, set(), [])
    
    def iterative_deepening_dfs(self):
        """IDDFS with step-by-step visualization"""
        for depth in range(30):
            print(f"IDDFS: Searching at depth {depth}")
            self.clear_search_visualization()
            
            if self.depth_limited_search(depth):
                return True
            
            if self.paused:
                return False
            
            pygame.time.wait(200)
        
        return False
    
    def bidirectional_search(self):
        """Bidirectional search with step-by-step visualization"""
        start_node = Node(self.start[0], self.start[1])
        target_node = Node(self.target[0], self.target[1])
        
        forward_queue = deque([start_node])
        backward_queue = deque([target_node])
        forward_visited = {(start_node.x, start_node.y): start_node}
        backward_visited = {(target_node.x, target_node.y): target_node}
        
        while (forward_queue or backward_queue) and not self.paused:
            if self.add_dynamic_obstacle():
                pass
            
            if forward_queue:
                current = forward_queue.popleft()
                pos = (current.x, current.y)
                
                if pos in backward_visited:
                    forward_path = self.reconstruct_path(current)
                    backward_path = self.reconstruct_path(backward_visited[pos])
                    backward_path.reverse()
                    full_path = forward_path + backward_path[1:]
                    self.visualize_path(full_path)
                    return True
                
                if pos != self.start:
                    self.grid[current.x][current.y] = CellType.EXPLORED
                
                for neighbor in self.get_neighbors(current):
                    neighbor_pos = (neighbor.x, neighbor.y)
                    if (neighbor_pos not in forward_visited and 
                        self.is_valid_position(neighbor.x, neighbor.y)):
                        forward_visited[neighbor_pos] = neighbor
                        forward_queue.append(neighbor)
                        if neighbor_pos != self.target:
                            self.grid[neighbor.x][neighbor.y] = CellType.FRONTIER
            
            if backward_queue:
                current = backward_queue.popleft()
                pos = (current.x, current.y)
                
                if pos in forward_visited:
                    forward_path = self.reconstruct_path(forward_visited[pos])
                    backward_path = self.reconstruct_path(current)
                    backward_path.reverse()
                    full_path = forward_path + backward_path[1:]
                    self.visualize_path(full_path)
                    return True
                
                if pos != self.target:
                    self.grid[current.x][current.y] = CellType.EXPLORED
                
                for neighbor in self.get_neighbors(current):
                    neighbor_pos = (neighbor.x, neighbor.y)
                    if (neighbor_pos not in backward_visited and 
                        self.is_valid_position(neighbor.x, neighbor.y)):
                        backward_visited[neighbor_pos] = neighbor
                        backward_queue.append(neighbor)
                        if neighbor_pos != self.start:
                            self.grid[neighbor.x][neighbor.y] = CellType.FRONTIER
            
            self.draw()
            pygame.display.flip()
            pygame.time.wait(self.step_delay)
            
            if not self.handle_events_during_search():
                return False
        
        return False
    
    def run_algorithm(self):
        """Run the selected algorithm"""
        if self.is_searching:
            return
        
        self.clear_search_visualization()
        self.is_searching = True
        self.search_complete = False
        self.paused = False
        
        print(f"Running {self.current_algorithm}...")
        
        success = False
        if self.current_algorithm == "BFS":
            success = self.breadth_first_search()
        elif self.current_algorithm == "DFS":
            success = self.depth_first_search()
        elif self.current_algorithm == "UCS":
            success = self.uniform_cost_search()
        elif self.current_algorithm == "DLS":
            success = self.depth_limited_search()
        elif self.current_algorithm == "IDDFS":
            success = self.iterative_deepening_dfs()
        elif self.current_algorithm == "Bidirectional":
            success = self.bidirectional_search()
        
        self.is_searching = False
        self.search_complete = True
        
        result = "Path found!" if success else "No path found!"
        print(f"{self.current_algorithm}: {result}")
    
    def handle_events_during_search(self):
        """Handle events during search execution"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
        return True
    
    def get_cell_color(self, cell_type):
        """Get color for each cell type"""
        color_map = {
            CellType.EMPTY: Colors.WHITE,
            CellType.WALL: Colors.BLACK,
            CellType.START: Colors.GREEN,
            CellType.TARGET: Colors.RED,
            CellType.FRONTIER: Colors.BLUE,
            CellType.EXPLORED: Colors.LIGHT_BLUE,
            CellType.PATH: Colors.YELLOW,
            CellType.DYNAMIC_OBSTACLE: Colors.PINK
        }
        return color_map.get(cell_type, Colors.WHITE)
    
    def draw_grid(self):
        """Draw the search grid"""
        for row in range(self.rows):
            for col in range(self.cols):
                x = col * self.grid_size
                y = row * self.grid_size
                
                color = self.get_cell_color(self.grid[row][col])
                pygame.draw.rect(self.screen, color, (x, y, self.grid_size, self.grid_size))
                pygame.draw.rect(self.screen, Colors.GRAY, (x, y, self.grid_size, self.grid_size), 1)
    
    def draw_bottom_legend(self):
        """Draw horizontal legend at the bottom of the grid"""
        legend_y = self.grid_height + 10
        legend_height = self.bottom_legend_height - 20
        
        # Background for legend area
        legend_rect = pygame.Rect(0, self.grid_height, self.grid_width, self.bottom_legend_height)
        pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, legend_rect)
        pygame.draw.rect(self.screen, Colors.BLACK, legend_rect, 2)
        
        # Legend title
        legend_title = self.font.render("Legend:", True, Colors.BLACK)
        self.screen.blit(legend_title, (10, legend_y))
        
        # Dynamic obstacles count
        dyn_count = len(self.dynamic_obstacles_added)
        dyn_text = self.small_font.render(f"Dynamic Obstacles: {dyn_count}", True, Colors.BLACK)
        self.screen.blit(dyn_text, (10, legend_y + 25))
        
        # Status
        status = "Searching..." if self.is_searching else "Ready"
        if self.paused:
            status = "Paused"
        elif self.search_complete:
            status = "Complete"
        
        status_text = self.small_font.render(f"Status: {status}", True, Colors.BLACK)
        self.screen.blit(status_text, (10, legend_y + 45))
        
        # Horizontal legend items
        legend_items = [
            ("Start", Colors.GREEN),
            ("Target", Colors.RED), 
            ("Path", Colors.YELLOW),
            ("Frontier", Colors.BLUE),
            ("Explored", Colors.LIGHT_BLUE),
            ("Wall", Colors.BLACK),
            ("Dynamic", Colors.PINK)
        ]
        
        # Calculate spacing for horizontal layout
        start_x = 200
        item_width = 80
        
        for i, (name, color) in enumerate(legend_items):
            x = start_x + i * item_width
            y = legend_y + 10
            
            # Draw color square
            pygame.draw.rect(self.screen, color, (x, y, 20, 20))
            pygame.draw.rect(self.screen, Colors.BLACK, (x, y, 20, 20), 1)
            
            # Draw text below the square
            text = self.small_font.render(name, True, Colors.BLACK)
            self.screen.blit(text, (x - 5, y + 25))
    
    def draw_panel(self):
        """Draw the control panel"""
        panel_x = self.grid_width
        panel_rect = pygame.Rect(panel_x, 0, self.panel_width, self.grid_height)
        pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, panel_rect)
        
        # Title
        title = self.title_font.render("GOOD PERFORMANCE", True, Colors.BLACK)
        self.screen.blit(title, (panel_x + 10, 10))
        title2 = self.title_font.render("TIME APP", True, Colors.BLACK)
        self.screen.blit(title2, (panel_x + 10, 35))
        
        # Algorithm selection
        algo_label = self.font.render("Algorithms:", True, Colors.BLACK)
        self.screen.blit(algo_label, (panel_x + 10, 70))
        
        for button in self.algo_buttons:
            if button.text == self.current_algorithm:
                button.color = Colors.LIGHT_BLUE
            else:
                button.color = Colors.WHITE
            button.draw(self.screen)
        
        # Speed control
        speed_label = self.font.render("Speed:", True, Colors.BLACK)
        self.screen.blit(speed_label, (panel_x + 150, 70))
        
        for button, delay in self.speed_buttons:
            if delay == self.step_delay:
                button.color = Colors.LIGHT_BLUE
            else:
                button.color = Colors.WHITE
            button.draw(self.screen)
        
        # Control buttons
        controls_label = self.font.render("Controls:", True, Colors.BLACK)
        self.screen.blit(controls_label, (panel_x + 10, 260))
        
        self.start_button.draw(self.screen)
        self.pause_button.draw(self.screen)
        self.reset_button.draw(self.screen)
        self.clear_button.draw(self.screen)
        
        # Mode selection
        mode_label = self.font.render("Drawing Mode:", True, Colors.BLACK)
        self.screen.blit(mode_label, (panel_x + 10, 360))
        
        for i, button in enumerate(self.mode_buttons):
            if self.modes[i] == self.current_mode:
                button.color = Colors.LIGHT_BLUE
            else:
                button.color = Colors.WHITE
            button.draw(self.screen)
        
        # Dynamic obstacles toggle
        self.dynamic_toggle.text = f"Dynamic: {'ON' if self.enable_dynamic_obstacles else 'OFF'}"
        self.dynamic_toggle.color = Colors.PINK if self.enable_dynamic_obstacles else Colors.GRAY
        self.dynamic_toggle.draw(self.screen)
    
    def draw(self):
        """Main draw function"""
        self.screen.fill(Colors.WHITE)
        self.draw_grid()
        self.draw_bottom_legend()  # Draw legend at bottom horizontally
        self.draw_panel()
        pygame.display.flip()
    
    def handle_grid_click(self, pos):
        """Handle clicks on the grid"""
        # Only handle clicks within the grid area (not in the legend area)
        if pos[1] > self.grid_height:
            return
            
        col = pos[0] // self.grid_size
        row = pos[1] // self.grid_size
        
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if self.current_mode == "START":
                if self.start:
                    self.grid[self.start[0]][self.start[1]] = CellType.EMPTY
                self.start = (row, col)
                self.grid[row][col] = CellType.START
                
            elif self.current_mode == "TARGET":
                if self.target:
                    self.grid[self.target[0]][self.target[1]] = CellType.EMPTY
                self.target = (row, col)
                self.grid[row][col] = CellType.TARGET
                
            elif self.current_mode == "WALL":
                if self.grid[row][col] == CellType.EMPTY:
                    self.grid[row][col] = CellType.WALL
                elif self.grid[row][col] == CellType.WALL:
                    self.grid[row][col] = CellType.EMPTY
    
    def handle_button_click(self, pos):
        """Handle button clicks"""
        for i, button in enumerate(self.algo_buttons):
            if button.is_clicked(pos):
                self.current_algorithm = self.algorithms[i]
                self.clear_search_visualization()
                return
        
        for button, delay in self.speed_buttons:
            if button.is_clicked(pos):
                self.step_delay = delay
                return
        
        if self.start_button.is_clicked(pos) and not self.is_searching:
            self.run_algorithm()
        elif self.pause_button.is_clicked(pos):
            self.paused = not self.paused
        elif self.reset_button.is_clicked(pos):
            self.clear_search_visualization()
            self.is_searching = False
            self.paused = False
        elif self.clear_button.is_clicked(pos):
            self.clear_all()
            self.is_searching = False
            self.paused = False
        
        for i, button in enumerate(self.mode_buttons):
            if button.is_clicked(pos):
                self.current_mode = self.modes[i]
                return
        
        if self.dynamic_toggle.is_clicked(pos):
            self.enable_dynamic_obstacles = not self.enable_dynamic_obstacles
    
    def update_button_hover(self, pos):
        """Update button hover states"""
        all_buttons = (self.algo_buttons + [self.start_button, self.pause_button, 
                      self.reset_button, self.clear_button] + self.mode_buttons + 
                      [button for button, _ in self.speed_buttons] + [self.dynamic_toggle])
        
        for button in all_buttons:
            button.update_hover(pos)
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            mouse_pos = pygame.mouse.get_pos()
            self.update_button_hover(mouse_pos)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        if event.pos[0] < self.grid_width and event.pos[1] < self.grid_height:
                            # Click on grid (not legend area)
                            if not self.is_searching:
                                self.handle_grid_click(event.pos)
                        elif event.pos[0] >= self.grid_width:
                            # Click on panel
                            self.handle_button_click(event.pos)
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE and not self.is_searching:
                        self.run_algorithm()
                    elif event.key == pygame.K_r:
                        self.clear_search_visualization()
                        self.is_searching = False
                        self.paused = False
            
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    pathfinder = GOODPERFORMANCETIMEAPPathfinder()
    pathfinder.run()