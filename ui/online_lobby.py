import pygame
from typing import Optional, List, Dict
from multiplayer.network import NetworkClient

class OnlineLobby:
    def __init__(self, screen_width: int, screen_height: int, network_client: NetworkClient):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.network = network_client
        
        self.font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)
        self.large_font = pygame.font.Font(None, 48)
        
        # Lobby dimensions
        self.lobby_width = screen_width - 40
        self.lobby_height = screen_height - 40
        self.lobby_x = 20
        self.lobby_y = 20
        
        # Player list area
        self.player_list_rect = pygame.Rect(
            self.lobby_x + 20,
            self.lobby_y + 80,
            self.lobby_width - 40,
            self.lobby_height - 160
        )
        
        # Buttons
        button_width = 120
        button_height = 40
        button_y = self.lobby_y + self.lobby_height - 60
        
        self.refresh_button = pygame.Rect(
            self.lobby_x + 20,
            button_y,
            button_width,
            button_height
        )
        
        self.disconnect_button = pygame.Rect(
            self.lobby_x + self.lobby_width - button_width - 20,
            button_y,
            button_width,
            button_height
        )
        
        # State
        self.players = []
        self.selected_player = None
        self.last_refresh = 0
        self.refresh_interval = 3000  # 3 seconds
        self.status_message = ""
        self.status_timer = 0
        
        # Game request state
        self.pending_request = None
        self.incoming_request = None
        self.game_starting = False
        
        # Set up network callbacks
        self.network.set_callback("game_request", self._handle_game_request)
        self.network.set_callback("game_start", self._handle_game_start)
        self.network.set_callback("game_rejected", self._handle_game_rejected)
        
        # Auto-refresh players
        self._refresh_players()
    
    def _handle_game_request(self, requester_id: int):
        """Handle incoming game request"""
        self.incoming_request = requester_id
        self.status_message = f"Player {requester_id} wants to play!"
        self.status_timer = pygame.time.get_ticks()
        print(f"DEBUG: Received game request from Player {requester_id}")
    
    def _handle_game_start(self, is_white: bool):
        """Handle game start confirmation"""
        print(f"DEBUG: Game starting, playing as {'White' if is_white else 'Black'}")
        self.game_starting = True
        return ("start_game", is_white)
    
    def _handle_game_rejected(self):
        """Handle game request rejection"""
        self.pending_request = None
        self.status_message = "Game request was rejected"
        self.status_timer = pygame.time.get_ticks()
        print("DEBUG: Game request was rejected")
    
    def _refresh_players(self):
        """Refresh the player list"""
        players = self.network.get_player_list()
        if players is not None:
            self.players = players
            self.last_refresh = pygame.time.get_ticks()
            print(f"DEBUG: Refreshed player list: {len(players)} players")
    
    def _set_status(self, message: str):
        """Set a status message"""
        self.status_message = message
        self.status_timer = pygame.time.get_ticks()

    def handle_event(self, event) -> Optional[str]:
        """Handle events in the lobby"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "disconnect"
            elif event.key == pygame.K_F5:
                self._refresh_players()
                
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            
            # Handle refresh button
            if self.refresh_button.collidepoint(x, y):
                self._refresh_players()
                
            elif self.disconnect_button.collidepoint(x, y):
                return "disconnect"
                
            elif self.player_list_rect.collidepoint(x, y) and not self.incoming_request:
                # Handle player selection
                relative_y = y - self.player_list_rect.top
                player_index = relative_y // 50  # Assuming 50px per player item
                if 0 <= player_index < len(self.players):
                    player = self.players[player_index]
                    if not player.get('is_self', False) and player['status'] == 'active':
                        self.selected_player = player
                        
                        # Double click detection
                        current_time = pygame.time.get_ticks()
                        if (hasattr(self, '_last_click_time') and 
                            current_time - self._last_click_time < 500 and
                            hasattr(self, '_last_clicked_player') and
                            self._last_clicked_player == player['id']):
                            
                            # Double click - send game request
                            print(f"DEBUG: Sending game request to Player {player['id']}")
                            if self.network.send_game_request(player['id']):
                                self.pending_request = player['id']
                                self._set_status(f"Game request sent to Player {player['id']}")
                            else:
                                self._set_status("Failed to send game request")
                                
                        self._last_click_time = current_time
                        self._last_clicked_player = player['id']
                        
            elif self.incoming_request:
                # Handle accept/reject buttons for incoming requests
                accept_button = self._get_accept_button()
                reject_button = self._get_reject_button()
                
                if accept_button.collidepoint(x, y):
                    print(f"DEBUG: Accepting game request from Player {self.incoming_request}")
                    self.network.respond_to_game_request(self.incoming_request, True)
                    self.incoming_request = None
                    # Game will start, we play as black when accepting
                    return ("start_game", False)
                    
                elif reject_button.collidepoint(x, y):
                    print(f"DEBUG: Rejecting game request from Player {self.incoming_request}")
                    self.network.respond_to_game_request(self.incoming_request, False)
                    self.incoming_request = None
                    
        return None

    def update(self):
        """Update lobby state"""
        current_time = pygame.time.get_ticks()
        
        # Auto-refresh players
        if current_time - self.last_refresh > self.refresh_interval:
            self._refresh_players()
            
        # Clear status message after 5 seconds
        if self.status_message and current_time - self.status_timer > 5000:
            self.status_message = ""
            
        # Check if game is starting
        if self.game_starting:
            self.game_starting = False
            # When we sent the request, we play as white
            return ("start_game", True)
            
        return None
    
    def _get_accept_button(self) -> pygame.Rect:
        """Get accept button rect for incoming requests"""
        return pygame.Rect(
            self.screen_width // 2 - 100,
            self.screen_height // 2 + 50,
            80, 40
        )
    
    def _get_reject_button(self) -> pygame.Rect:
        """Get reject button rect for incoming requests"""
        return pygame.Rect(
            self.screen_width // 2 + 20,
            self.screen_height // 2 + 50,
            80, 40
        )
    
    def draw(self, screen):
        """Draw the lobby interface"""
        # Background
        screen.fill((30, 30, 30))
        
        # Main lobby area
        lobby_rect = pygame.Rect(self.lobby_x, self.lobby_y, self.lobby_width, self.lobby_height)
        pygame.draw.rect(screen, (50, 50, 50), lobby_rect, border_radius=10)
        pygame.draw.rect(screen, (150, 150, 150), lobby_rect, 2, border_radius=10)
        
        # Title
        title_text = self.large_font.render("Online Lobby", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=lobby_rect.centerx, top=lobby_rect.top + 20)
        screen.blit(title_text, title_rect)
        
        # Player info
        if self.network.player_id:
            player_info = self.small_font.render(f"You are Player {self.network.player_id}", True, (200, 200, 200))
            screen.blit(player_info, (self.lobby_x + 20, title_rect.bottom + 10))
        
        # Player list header
        list_header = self.font.render("Online Players (Double-click to challenge):", True, (255, 255, 255))
        screen.blit(list_header, (self.player_list_rect.left, self.player_list_rect.top - 30))
        
        # Player list background
        pygame.draw.rect(screen, (40, 40, 40), self.player_list_rect, border_radius=5)
        pygame.draw.rect(screen, (100, 100, 100), self.player_list_rect, 1, border_radius=5)
        
        # Draw players
        if not self.players:
            no_players_text = self.small_font.render("No other players online", True, (150, 150, 150))
            text_rect = no_players_text.get_rect(center=self.player_list_rect.center)
            screen.blit(no_players_text, text_rect)
        else:
            for i, player in enumerate(self.players):
                if player.get('is_self', False):
                    continue  # Skip self
                    
                item_y = self.player_list_rect.top + (i * 50)
                item_rect = pygame.Rect(
                    self.player_list_rect.left + 10,
                    item_y + 5,
                    self.player_list_rect.width - 20,
                    40
                )
                
                # Highlight selected player
                if (self.selected_player and 
                    player['id'] == self.selected_player['id']):
                    pygame.draw.rect(screen, (80, 120, 80), item_rect, border_radius=3)
                
                # Player name
                player_text = self.small_font.render(f"Player {player['id']}", True, (255, 255, 255))
                screen.blit(player_text, (item_rect.left + 10, item_rect.top + 5))
                
                # Player status
                status_color = (0, 255, 0) if player['status'] == 'active' else (255, 255, 0)
                status_text = self.small_font.render(player['status'].upper(), True, status_color)
                status_rect = status_text.get_rect(right=item_rect.right - 10, top=item_rect.top + 5)
                screen.blit(status_text, status_rect)
        
        # Draw buttons
        mouse_pos = pygame.mouse.get_pos()
        
        # Refresh button
        refresh_hover = self.refresh_button.collidepoint(mouse_pos)
        refresh_color = (100, 150, 100) if refresh_hover else (70, 120, 70)
        pygame.draw.rect(screen, refresh_color, self.refresh_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.refresh_button, 2, border_radius=5)
        
        refresh_text = self.small_font.render("Refresh", True, (255, 255, 255))
        refresh_text_rect = refresh_text.get_rect(center=self.refresh_button.center)
        screen.blit(refresh_text, refresh_text_rect)
        
        # Disconnect button
        disconnect_hover = self.disconnect_button.collidepoint(mouse_pos)
        disconnect_color = (150, 100, 100) if disconnect_hover else (120, 70, 70)
        pygame.draw.rect(screen, disconnect_color, self.disconnect_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), self.disconnect_button, 2, border_radius=5)
        
        disconnect_text = self.small_font.render("Disconnect", True, (255, 255, 255))
        disconnect_text_rect = disconnect_text.get_rect(center=self.disconnect_button.center)
        screen.blit(disconnect_text, disconnect_text_rect)
        
        # Status message
        if self.status_message:
            status_surface = self.small_font.render(self.status_message, True, (255, 255, 0))
            status_rect = status_surface.get_rect(centerx=lobby_rect.centerx, bottom=lobby_rect.bottom - 80)
            screen.blit(status_surface, status_rect)
        
        # Draw pending request status
        if self.pending_request:
            pending_text = self.small_font.render(f"Waiting for Player {self.pending_request} to respond...", True, (255, 255, 0))
            pending_rect = pending_text.get_rect(centerx=lobby_rect.centerx, bottom=lobby_rect.bottom - 100)
            screen.blit(pending_text, pending_rect)
        
        # Draw incoming request dialog
        if self.incoming_request:
            self._draw_request_dialog(screen)
    
    def _draw_request_dialog(self, screen):
        """Draw incoming game request dialog"""
        # Overlay
        overlay = pygame.Surface((self.screen_width, self.screen_height))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        screen.blit(overlay, (0, 0))
        
        # Dialog
        dialog_width = 400
        dialog_height = 200
        dialog_x = (self.screen_width - dialog_width) // 2
        dialog_y = (self.screen_height - dialog_height) // 2
        
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        pygame.draw.rect(screen, (60, 60, 60), dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (200, 200, 200), dialog_rect, 2, border_radius=10)
        
        # Title
        title_text = self.font.render("Game Request", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=dialog_rect.centerx, top=dialog_rect.top + 20)
        screen.blit(title_text, title_rect)
        
        # Message
        message_text = self.small_font.render(f"Player {self.incoming_request} wants to play chess!", True, (255, 255, 255))
        message_rect = message_text.get_rect(centerx=dialog_rect.centerx, top=title_rect.bottom + 20)
        screen.blit(message_text, message_rect)
        
        role_text = self.small_font.render("You will play as Black", True, (200, 200, 200))
        role_rect = role_text.get_rect(centerx=dialog_rect.centerx, top=message_rect.bottom + 10)
        screen.blit(role_text, role_rect)
        
        # Buttons
        accept_button = self._get_accept_button()
        reject_button = self._get_reject_button()
        
        mouse_pos = pygame.mouse.get_pos()
        
        # Accept button
        accept_hover = accept_button.collidepoint(mouse_pos)
        accept_color = (100, 150, 100) if accept_hover else (70, 120, 70)
        pygame.draw.rect(screen, accept_color, accept_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), accept_button, 2, border_radius=5)
        
        accept_text = self.small_font.render("Accept", True, (255, 255, 255))
        accept_text_rect = accept_text.get_rect(center=accept_button.center)
        screen.blit(accept_text, accept_text_rect)
        
        # Reject button
        reject_hover = reject_button.collidepoint(mouse_pos)
        reject_color = (150, 100, 100) if reject_hover else (120, 70, 70)
        pygame.draw.rect(screen, reject_color, reject_button, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), reject_button, 2, border_radius=5)
        
        reject_text = self.small_font.render("Reject", True, (255, 255, 255))
        reject_text_rect = reject_text.get_rect(center=reject_button.center)
        screen.blit(reject_text, reject_text_rect)