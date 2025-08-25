import pygame
from typing import Optional, Tuple

class ConnectionDialog:
    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # Dialog dimensions
        self.dialog_width = 450
        self.dialog_height = 300
        self.dialog_x = (screen_width - self.dialog_width) // 2
        self.dialog_y = (screen_height - self.dialog_height) // 2
        
        # Input field for server address
        self.input_rect = pygame.Rect(
            self.dialog_x + 20,
            self.dialog_y + 120,
            self.dialog_width - 40,
            40
        )
        
        # Protocol selection buttons
        self.ipv4_button = pygame.Rect(
            self.dialog_x + 50,
            self.dialog_y + 180,
            80,
            30
        )
        
        self.ipv6_button = pygame.Rect(
            self.dialog_x + 150,
            self.dialog_y + 180,
            80,
            30
        )
        
        # Control buttons
        self.connect_button = pygame.Rect(
            self.dialog_x + 50,
            self.dialog_y + self.dialog_height - 60,
            120,
            40
        )
        
        self.cancel_button = pygame.Rect(
            self.dialog_x + self.dialog_width - 170,
            self.dialog_y + self.dialog_height - 60,
            120,
            40
        )
        
        # State
        self.server_address = "127.0.0.1"  # Default localhost
        self.use_ipv6 = False
        self.input_active = True
        self.cursor_visible = True
        self.cursor_timer = 0
        
    def handle_event(self, event) -> Optional[Tuple[str, bool]]:
        """
        Handle connection dialog events
        Returns: (server_address, use_ipv6) or None for cancel
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                if self.server_address.strip():
                    return self.server_address.strip(), self.use_ipv6
            elif event.key == pygame.K_ESCAPE:
                return None
            elif event.key == pygame.K_BACKSPACE:
                self.server_address = self.server_address[:-1]
            else:
                # Add character if it's printable and not too long
                if len(self.server_address) < 50 and event.unicode.isprintable():
                    self.server_address += event.unicode
                    
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            
            # Check input field click
            if self.input_rect.collidepoint(x, y):
                self.input_active = True
                
            # Check protocol buttons
            elif self.ipv4_button.collidepoint(x, y):
                self.use_ipv6 = False
            elif self.ipv6_button.collidepoint(x, y):
                self.use_ipv6 = True
                
            # Check control buttons
            elif self.connect_button.collidepoint(x, y):
                if self.server_address.strip():
                    return self.server_address.strip(), self.use_ipv6
            elif self.cancel_button.collidepoint(x, y):
                return None
                
        return False  # Continue showing dialog
    
    def update(self, dt: int):
        """Update cursor blinking"""
        self.cursor_timer += dt
        if self.cursor_timer >= 500:  # Blink every 500ms
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0
    
    def draw(self, screen):
        """Draw the connection dialog"""
        # Draw overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        screen.blit(overlay, (0, 0))
        
        # Draw dialog background
        dialog_rect = pygame.Rect(self.dialog_x, self.dialog_y, self.dialog_width, self.dialog_height)
        pygame.draw.rect(screen, (60, 60, 60), dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), dialog_rect, 2, border_radius=10)
        
        # Draw title
        title_text = self.font.render("Connect to Server", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=dialog_rect.centerx, top=dialog_rect.top + 20)
        screen.blit(title_text, title_rect)
        
        # Draw instructions
        instructions = [
            "Enter the server address to connect to:",
            "• Use 127.0.0.1 or localhost for local server",
            "• Use your friend's IP address for remote play",
            "• Make sure the server is running on port 26104"
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.small_font.render(instruction, True, (200, 200, 200))
            screen.blit(text, (self.dialog_x + 20, self.dialog_y + 60 + i * 20))
        
        # Draw input field
        input_color = (80, 80, 80) if self.input_active else (60, 60, 60)
        pygame.draw.rect(screen, input_color, self.input_rect, border_radius=5)
        pygame.draw.rect(screen, (150, 150, 150), self.input_rect, 2, border_radius=5)
        
        # Draw input text
        if self.server_address:
            text_surface = self.small_font.render(self.server_address, True, (255, 255, 255))
            text_rect = text_surface.get_rect(
                left=self.input_rect.left + 10,
                centery=self.input_rect.centery
            )
            screen.blit(text_surface, text_rect)
            
            # Draw cursor
            if self.input_active and self.cursor_visible:
                cursor_x = text_rect.right + 2
                cursor_y1 = self.input_rect.centery - 10
                cursor_y2 = self.input_rect.centery + 10
                pygame.draw.line(screen, (255, 255, 255), (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)
        else:
            # Draw placeholder
            placeholder_surface = self.small_font.render("Enter server address...", True, (120, 120, 120))
            placeholder_rect = placeholder_surface.get_rect(
                left=self.input_rect.left + 10,
                centery=self.input_rect.centery
            )
            screen.blit(placeholder_surface, placeholder_rect)
        
        # Draw protocol selection
        protocol_label = self.small_font.render("Protocol:", True, (255, 255, 255))
        screen.blit(protocol_label, (self.dialog_x + 20, self.dialog_y + 160))
        
        mouse_pos = pygame.mouse.get_pos()
        
        # IPv4 button
        ipv4_hover = self.ipv4_button.collidepoint(mouse_pos)
        ipv4_selected = not self.use_ipv6
        ipv4_color = (100, 150, 100) if ipv4_selected else ((100, 100, 100) if ipv4_hover else (70, 70, 70))
        
        pygame.draw.rect(screen, ipv4_color, self.ipv4_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.ipv4_button, 2, border_radius=5)
        
        ipv4_text = self.small_font.render("IPv4", True, (255, 255, 255))
        ipv4_text_rect = ipv4_text.get_rect(center=self.ipv4_button.center)
        screen.blit(ipv4_text, ipv4_text_rect)
        
        # IPv6 button
        ipv6_hover = self.ipv6_button.collidepoint(mouse_pos)
        ipv6_selected = self.use_ipv6
        ipv6_color = (100, 150, 100) if ipv6_selected else ((100, 100, 100) if ipv6_hover else (70, 70, 70))
        
        pygame.draw.rect(screen, ipv6_color, self.ipv6_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.ipv6_button, 2, border_radius=5)
        
        ipv6_text = self.small_font.render("IPv6", True, (255, 255, 255))
        ipv6_text_rect = ipv6_text.get_rect(center=self.ipv6_button.center)
        screen.blit(ipv6_text, ipv6_text_rect)
        
        # Draw control buttons
        # Connect button
        connect_hover = self.connect_button.collidepoint(mouse_pos)
        connect_color = (100, 150, 100) if connect_hover else (70, 120, 70)
        if not self.server_address.strip():
            connect_color = (50, 50, 50)  # Disabled state
            
        pygame.draw.rect(screen, connect_color, self.connect_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.connect_button, 2, border_radius=5)
        
        connect_text = self.small_font.render("Connect", True, (255, 255, 255))
        connect_text_rect = connect_text.get_rect(center=self.connect_button.center)
        screen.blit(connect_text, connect_text_rect)
        
        # Cancel button
        cancel_hover = self.cancel_button.collidepoint(mouse_pos)
        cancel_color = (150, 100, 100) if cancel_hover else (120, 70, 70)
        
        pygame.draw.rect(screen, cancel_color, self.cancel_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.cancel_button, 2, border_radius=5)
        
        cancel_text = self.small_font.render("Cancel", True, (255, 255, 255))
        cancel_text_rect = cancel_text.get_rect(center=self.cancel_button.center)
        screen.blit(cancel_text, cancel_text_rect)