import pygame
import sys
import os
from code_logic.save_manager import SaveManager
from ui.load_dialog import LoadDialog

class StartMenu:
    def __init__(self, screen_width, screen_height):
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font = pygame.font.Font(None, 36)
        self.save_manager = SaveManager()
        
        # Main menu buttons
        button_width = screen_width // 2
        button_height = 50
        button_x = screen_width // 4
        spacing = 80
        
        self.buttons = {
            'new_game': pygame.Rect(button_x, screen_height//4, button_width, button_height),
            'online_multiplayer': pygame.Rect(button_x, screen_height//4 + spacing, button_width, button_height),
            'load_game': pygame.Rect(button_x, screen_height//4 + spacing * 2, button_width, button_height),
            'quit': pygame.Rect(button_x, screen_height//4 + spacing * 3, button_width, button_height)
        }
        
        # Game mode selection buttons (for new game)
        self.game_mode_buttons = {
            'Human_vs_Human': pygame.Rect(button_x, screen_height//4, button_width, button_height),
            'Human_vs_AI': pygame.Rect(button_x, screen_height//4 + spacing, button_width, button_height),
            'AI_vs_AI': pygame.Rect(button_x, screen_height//4 + spacing * 2, button_width, button_height),
            'back': pygame.Rect(button_x, screen_height//4 + spacing * 3, button_width, button_height)
        }
        
        self.show_game_modes = False
        self.load_dialog = None
        self.clock = pygame.time.Clock()

    def draw_button(self, rect, text, hover=False, enabled=True):
        if not enabled:
            color = (40, 40, 40)
            text_color = (100, 100, 100)
        else:
            color = (100, 100, 100) if hover else (70, 70, 70)
            text_color = (255, 255, 255)
            
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=5)
        text_surface = self.font.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    def draw_title(self):
        title_font = pygame.font.Font(None, 72)
        title_text = title_font.render("Chess AI Game", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=self.screen_width//2, top=50)
        self.screen.blit(title_text, title_rect)

    def run(self):
        while True:
            dt = self.clock.tick(60)
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                    
                # Handle load dialog events
                if self.load_dialog:
                    result = self.load_dialog.handle_event(event)
                    if result:
                        if result == "cancel":
                            self.load_dialog = None
                        elif result.startswith("load:"):
                            game_name = result[5:]
                            self.load_dialog = None
                            return f"load_game:{game_name}"
                        elif result.startswith("delete:"):
                            game_name = result[7:]
                            success, message = self.save_manager.delete_game(game_name)
                            # Refresh the dialog with updated game list
                            saved_games = self.save_manager.get_saved_games()
                            self.load_dialog = LoadDialog(self.screen_width, self.screen_height, saved_games)
                    continue
                    
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if not self.show_game_modes:
                        # Main menu
                        if self.buttons['new_game'].collidepoint(mouse_pos):
                            self.show_game_modes = True
                        elif self.buttons['online_multiplayer'].collidepoint(mouse_pos):
                            # Online multiplayer
                            return 'online_multiplayer'
                        elif self.buttons['load_game'].collidepoint(mouse_pos):
                            # Check if there are saved games
                            saved_games = self.save_manager.get_saved_games()
                            if saved_games:
                                self.load_dialog = LoadDialog(self.screen_width, self.screen_height, saved_games)
                        elif self.buttons['quit'].collidepoint(mouse_pos):
                            pygame.quit()
                            sys.exit()
                    else:
                        # Game mode selection
                        if self.game_mode_buttons['Human_vs_Human'].collidepoint(mouse_pos):
                            return 'Human_vs_Human'
                        elif self.game_mode_buttons['Human_vs_AI'].collidepoint(mouse_pos):
                            return 'Human_vs_AI'
                        elif self.game_mode_buttons['AI_vs_AI'].collidepoint(mouse_pos):
                            return 'AI_vs_AI'
                        elif self.game_mode_buttons['back'].collidepoint(mouse_pos):
                            self.show_game_modes = False

            # Update load dialog
            if self.load_dialog:
                self.load_dialog.update(dt)

            self.screen.fill((30, 30, 30))
            self.draw_title()
            
            if not self.show_game_modes:
                # Draw main menu
                saved_games_exist = len(self.save_manager.get_saved_games()) > 0
                
                for button_name, button_rect in self.buttons.items():
                    hover = button_rect.collidepoint(mouse_pos) and not self.load_dialog
                    enabled = True
                    
                    if button_name == 'load_game':
                        enabled = saved_games_exist
                    
                    display_name = button_name.replace('_', ' ').title()
                    if button_name == 'online_multiplayer':
                        display_name = 'Online Multiplayer'
                        
                    self.draw_button(button_rect, display_name, hover, enabled)
                    
                # Show saved games count
                if saved_games_exist:
                    games_count = len(self.save_manager.get_saved_games())
                    count_text = pygame.font.Font(None, 24).render(
                        f"({games_count} saved game{'s' if games_count != 1 else ''})", 
                        True, (150, 150, 150)
                    )
                    count_rect = count_text.get_rect(
                        centerx=self.buttons['load_game'].centerx,
                        top=self.buttons['load_game'].bottom + 5
                    )
                    self.screen.blit(count_text, count_rect)
            else:
                # Draw game mode selection
                for button_name, button_rect in self.game_mode_buttons.items():
                    hover = button_rect.collidepoint(mouse_pos)
                    display_name = button_name.replace('_', ' ').title()
                    self.draw_button(button_rect, display_name, hover)

            # Draw load dialog on top
            if self.load_dialog:
                self.load_dialog.draw(self.screen)

            pygame.display.flip()