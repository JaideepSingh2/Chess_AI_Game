import pygame
from code_logic.game_rules import GameRules as gr

class StatusDisplay:
    def __init__(self, board_width, board_height, sidebar_width):
        self.board_width = board_width
        self.board_height = board_height
        self.sidebar_width = sidebar_width
        self.stats_sidebar_width = sidebar_width
        self.font = pygame.font.Font(None, 24)
        
        self.status_height = 140
        self.padding = 10
        
        self.x_position = board_width + self.padding
        self.y_position = (board_height // 2) - (self.status_height // 2) - 50
        
        self.ai_stats = {
            'depth': 0,
            'positions_evaluated': 0,
            'evaluation_time': 0,
            'positions_per_second': 0
        }
        self.ai_stats_height = 160
        self.ai_stats_x_position = self.x_position
        self.ai_stats_y_position = 0
        
        self.title_font_size = 22
        self.message_font_size = 18
        self.action_font_size = 16
        self.stats_font_size = 16
        self.title_font = pygame.font.SysFont("Arial", self.title_font_size, bold=True)
        self.message_font = pygame.font.SysFont("Segoe UI", self.message_font_size, bold=True)
        self.action_font = pygame.font.SysFont("Segoe UI", self.action_font_size, bold=True)
        self.stats_font = pygame.font.SysFont("Consolas", self.stats_font_size)
        
        self.colors = {
            'normal': {
                'bg': (248, 250, 252),
                'border': (226, 232, 240),
                'text': (15, 23, 42)
            },
            'check': {
                'bg': (254, 243, 199),
                'border': (251, 191, 36),
                'text': (146, 64, 14)
            },
            'checkmate': {
                'bg': (254, 226, 226),
                'border': (239, 68, 68),
                'text': (153, 27, 27)
            },
            'stalemate': {
                'bg': (241, 245, 249),
                'border': (148, 163, 184),
                'text': (51, 65, 85)
            },
            'stats': {
                'bg': (243, 244, 246),
                'border': (209, 213, 219),
                'text': (17, 24, 39)
            }
        }
        
        self.current_message = ""
        self.checking_piece = ""
        self.current_turn = ""
        self.message_type = "normal"
        self.display_time = 4000
        self.message_start_time = 0
        self.should_display = False
        
    def update_ai_stats(self, depth, positions_evaluated, evaluation_time):
        self.ai_stats['depth'] = depth
        self.ai_stats['positions_evaluated'] = positions_evaluated
        self.ai_stats['evaluation_time'] = evaluation_time
        if evaluation_time > 0:
            self.ai_stats['positions_per_second'] = int(positions_evaluated / evaluation_time)
        else:
            self.ai_stats['positions_per_second'] = 0

    def draw_ai_stats(self, screen):
        stats_rect = pygame.Rect(
            self.ai_stats_x_position,
            self.ai_stats_y_position,
            self.stats_sidebar_width - self.padding * 2,
            self.ai_stats_height
        )
        
        color_scheme = self.colors['stats']
        
        shadow_rect = stats_rect.copy()
        shadow_rect.move_ip(2, 2)
        pygame.draw.rect(screen, (0, 0, 0, 30), shadow_rect, border_radius=10)
        
        pygame.draw.rect(screen, color_scheme['bg'], stats_rect, border_radius=10)
        pygame.draw.rect(screen, color_scheme['border'], stats_rect, 2, border_radius=10)
        
        title_surface = self.title_font.render("AI Statistics", True, color_scheme['text'])
        title_rect = title_surface.get_rect(
            centerx=stats_rect.centerx,
            top=stats_rect.top + self.padding
        )
        screen.blit(title_surface, title_rect)
        
        # Draw separator
        separator_y = title_rect.bottom + 5
        pygame.draw.line(
            screen,
            color_scheme['border'],
            (stats_rect.left + self.padding, separator_y),
            (stats_rect.right - self.padding, separator_y),
            1
        )
        
        # Draw statistics
        stats_start_y = separator_y + 15
        line_height = self.stats_font.get_linesize() + 5
        
        stats_items = [
            ("Search Depth", f"{self.ai_stats['depth']}"),
            ("Positions", f"{self.ai_stats['positions_evaluated']:,}"),
            ("Time", f"{self.ai_stats['evaluation_time']:.2f} sec"),
            ("Positions/sec", f"{self.ai_stats['positions_per_second']:,}")
        ]
        
        for i, (label, value) in enumerate(stats_items):
            # Draw label
            label_surface = self.stats_font.render(label + ":", True, color_scheme['text'])
            screen.blit(label_surface, (stats_rect.left + self.padding * 2, stats_start_y + (i * line_height)))
            
            # Draw value (right-aligned)
            value_surface = self.stats_font.render(value, True, color_scheme['text'])
            value_rect = value_surface.get_rect(
                right=stats_rect.right - self.padding * 2,
                top=stats_start_y + (i * line_height)
            )
            screen.blit(value_surface, value_rect)
    


    def draw_move_history(self, screen, move_history):
        """Draw move history in a yellow box with proper text formatting and clipping."""
        line_height = 22  # Increased line height for better spacing
        box_height = 10 * line_height + 30  # Added more padding
        box_width = self.sidebar_width - 20
        x = self.board_width + 10
        y = self.board_height - box_height - 20

        background_rect = pygame.Rect(x, y, box_width, box_height)
        pygame.draw.rect(screen, (255, 255, 0), background_rect, border_radius=10)
        pygame.draw.rect(screen, (0, 0, 0), background_rect, 2, border_radius=10)

        # Draw header
        header_font = pygame.font.Font(None, 24)
        header = header_font.render("Move History", True, (0, 0, 0))
        header_rect = header.get_rect(centerx=background_rect.centerx, top=y + 8)
        screen.blit(header, header_rect)

        # Create text area with proper bounds
        text_area_x = x + 10
        text_area_y = y + 35
        text_area_width = box_width - 20
        text_area_height = box_height - 45
        text_area_rect = pygame.Rect(text_area_x, text_area_y, text_area_width, text_area_height)

        # Create a surface for clipping text
        text_surface = pygame.Surface((text_area_width, text_area_height))
        text_surface.fill((255, 255, 0))  # Yellow background

        max_moves = 9
        visible_moves = move_history[-max_moves:] if move_history else []

        if not visible_moves:
            # Show "No moves yet" message
            no_moves_font = pygame.font.Font(None, 20)
            no_moves_text = no_moves_font.render("No moves yet", True, (100, 100, 100))
            no_moves_rect = no_moves_text.get_rect(center=(text_area_width//2, text_area_height//2))
            text_surface.blit(no_moves_text, no_moves_rect)
        else:
            # Draw moves with proper formatting
            move_font = pygame.font.Font(None, 18)  # Slightly larger font
            
            for i, move in enumerate(visible_moves):
                # Format move text more compactly
                move_text = f"{move['color'][0].upper()}: {move['piece'][:3]} {move['from']}-{move['to']}"
                if move['captured']:
                    move_text += f" x{move['captured'][:3]}"
                
                # Ensure text fits within the available width
                max_width = text_area_width - 10
                
                # Truncate text if too long
                while move_font.size(move_text)[0] > max_width and len(move_text) > 8:
                    if 'x' in move_text:
                        # Remove capture info first
                        move_text = move_text.split(' x')[0]
                    else:
                        move_text = move_text[:-4] + "..."
                    
                # Render and draw the text
                text_rendered = move_font.render(move_text, True, (0, 0, 0))
                text_y_pos = i * line_height
                
                # Only draw if within bounds
                if text_y_pos + line_height <= text_area_height:
                    text_surface.blit(text_rendered, (5, text_y_pos))

        # Blit the clipped text surface to the main screen
        screen.blit(text_surface, text_area_rect)


    def update_status(self, message, message_type="normal", checking_piece=None, current_turn=None):
        if message != self.current_message or message_type == "check":
            self.current_message = message
            self.message_type = message_type
            self.checking_piece = checking_piece if checking_piece else ""
            self.current_turn = current_turn if current_turn else ""
            self.message_start_time = pygame.time.get_ticks()
            self.should_display = True

    def draw(self, screen):
        self.draw_ai_stats(screen)
        if not self.should_display or not self.current_message:
            return

        current_time = pygame.time.get_ticks()
        elapsed = current_time - self.message_start_time

        if elapsed > self.display_time and self.message_type not in ['checkmate', 'stalemate']:
            self.should_display = False
            return

        status_rect = pygame.Rect(
            self.x_position,
            self.y_position,
            self.sidebar_width - (self.padding * 2),
            self.status_height + 20
        )

        color_scheme = self.colors[self.message_type]
        shadow_rect = status_rect.copy()
        shadow_rect.move_ip(2, 2)
        pygame.draw.rect(screen, (0, 0, 0, 30), shadow_rect, border_radius=10)

        pygame.draw.rect(screen, color_scheme['bg'], status_rect, border_radius=10)
        pygame.draw.rect(screen, color_scheme['border'], status_rect, 2, border_radius=10)

        title_text = self.get_title_text()
        title_surface = self.title_font.render(title_text, True, color_scheme['text'])
        title_rect = title_surface.get_rect(
            centerx=status_rect.centerx,
            top=status_rect.top + self.padding
        )
        screen.blit(title_surface, title_rect)

        separator_y = title_rect.bottom + 5
        pygame.draw.line(
            screen,
            color_scheme['border'],
            (status_rect.left + self.padding, separator_y),
            (status_rect.right - self.padding, separator_y),
            1
        )

        # Message box
        message_box_height = status_rect.height - separator_y - (self.padding * 3)
        if self.message_type in ['checkmate', 'check']:
            message_box_height += 20

        message_box_rect = pygame.Rect(
            status_rect.left + self.padding * 2,
            separator_y + self.padding,
            status_rect.width - (self.padding * 4),
            message_box_height
        )

        message_height = self.draw_wrapped_text(
            screen,
            self.current_message,
            self.message_font,
            color_scheme['text'],
            message_box_rect
        )

        if self.message_type == 'checkmate':
            action_text = "Game Over!"
            action_surface = self.action_font.render(action_text, True, color_scheme['text'])
            action_y = message_box_rect.bottom - action_surface.get_height()
            screen.blit(action_surface, (message_box_rect.left, action_y))

        elif self.message_type == 'check' and self.checking_piece:
            piece_text = f"by {self.checking_piece.capitalize()}"
            piece_surface = self.action_font.render(piece_text, True, color_scheme['text'])
            piece_y = message_box_rect.bottom - piece_surface.get_height()
            screen.blit(piece_surface, (message_box_rect.left, piece_y))
    
    def get_title_text(self):
        titles = {
            'normal': 'Game Status',
            'check': 'Check!',
            'checkmate': 'Checkmate!',
            'stalemate': 'Stalemate'
        }
        return titles.get(self.message_type, 'Game Status')

    def draw_wrapped_text(self, surface, text, font, color, rect):
        words = text.split()
        lines = []
        current_line = []
        
        max_width = rect.width - self.padding * 2
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if font.size(test_line)[0] <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        line_spacing = 1.2
        total_height = len(lines) * (font.get_linesize() * line_spacing)
        current_y = rect.top + (rect.height - total_height) // 2
        
        for line in lines:
            line_surface = font.render(line, True, color)
            line_rect = line_surface.get_rect(centerx=rect.centerx, top=current_y)
            surface.blit(line_surface, line_rect)
            current_y += font.get_linesize() * line_spacing
            
        return total_height

    def clear(self):
        self.current_message = ""
        self.checking_piece = ""
        self.should_display = False