import pygame
import threading
import time
from typing import Optional, Tuple
from code_logic.chessboard import ChessBoard
from code_logic.game_rules import GameRules
from ui.game_menu import GameMenu
from ui.status_display import StatusDisplay
from code_logic.save_manager import SaveManager
from ui.save_dialog import SaveDialog
from ui.load_dialog import LoadDialog
from ui.popup import Popup
from multiplayer.network import NetworkGame

class OnlineMultiplayerGame:
    def __init__(self, screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, network_game: NetworkGame):
        self.screen = screen
        self.screen_width = screen_width
        self.board_height = board_height
        self.sidebar_width = sidebar_width
        self.sound_manager = sound_manager
        self.save_manager = save_manager
        self.network_game = network_game
        
        self.board_width = screen_width - sidebar_width
        self.chess_board = ChessBoard(screen, self.board_width, board_height)
        self.game_rules = GameRules(self.chess_board)
        self.game_menu = GameMenu(screen_width, board_height, sidebar_width)
        self.status_display = StatusDisplay(self.board_width, board_height, sidebar_width)
        
        self.clock = pygame.time.Clock()
        self.running = True
        self.selected_piece = None
        
        # Dialog states
        self.popup = None
        self.save_dialog = None
        self.load_dialog = None
        
        # Game state tracking
        self.check_sound_played = False
        self.checkmate_sound_played = False
        self.stalemate_sound_played = False
        
        # FIXED: Proper color and turn assignment
        self.my_color = 'white' if self.network_game.is_white else 'black'
        # White always starts, so if I'm white, it's my turn
        self.is_my_turn = self.network_game.is_white
        self.waiting_for_opponent = False
        self.game_ended = False
        
        print(f"DEBUG: I am playing as {self.my_color}, is_my_turn: {self.is_my_turn}")
        print(f"DEBUG: Current game turn: {self.game_rules.current_turn}")
        
        # Set up network callbacks
        self.network_game.network.set_callback("move_received", self._handle_opponent_move)
        self.network_game.network.set_callback("game_action", self._handle_game_action)

        

    def _handle_opponent_move(self, move_str: str):
        """Handle move received from opponent - Fixed implementation"""
        print(f"DEBUG: Received opponent move: {move_str}")
        
        try:
            move_data = self.network_game.parse_move(move_str)
            if move_data:
                from_pos, to_pos, promotion = move_data
                
                # Find piece at from_pos
                piece = self.chess_board.get_piece_at(from_pos)
                if piece and piece.color != self.my_color:
                    # Move the piece
                    captured_piece = self.chess_board.get_piece_at(to_pos)
                    if self.chess_board.move_piece(piece, to_pos):
                        # Record the move
                        self.game_rules.record_move(piece, from_pos, to_pos, captured_piece)
                        
                        # Handle promotion
                        if promotion:
                            # Remove pawn and add promoted piece
                            if piece.type == 'pawn':
                                self.chess_board.pieces.remove(piece)
                                promoted_piece_image = self.chess_board.get_piece_image(promotion, piece.color)
                                
                                # Create promoted piece
                                piece_classes = {
                                    'q': self.chess_board.Queen,
                                    'r': self.chess_board.Rook, 
                                    'b': self.chess_board.Bishop,
                                    'n': self.chess_board.Knight
                                }
                                
                                if promotion in piece_classes:
                                    piece_class = piece_classes[promotion]
                                    new_piece = piece_class(self.screen, promoted_piece_image, piece.color, to_pos)
                                    self.chess_board.pieces.append(new_piece)
                        
                        # Switch turns
                        self.game_rules.switch_turn()
                        self.sound_manager.play_move_sound()
                        
                        # Now it's my turn
                        self.is_my_turn = True
                        self.waiting_for_opponent = False
                        
                        # Reset sound flags
                        self.check_sound_played = False
                        self.checkmate_sound_played = False
                        self.stalemate_sound_played = False
                        
                        print("DEBUG: Opponent move processed, now my turn")
                    else:
                        print("DEBUG: Failed to move opponent's piece")
                else:
                    print(f"DEBUG: No valid piece found at {from_pos} for opponent")
        except Exception as e:
            print(f"Error handling opponent move: {e}")
    
    def _handle_game_action(self, action: str):
        """Handle game actions from opponent"""
        if action == "draw":
            self.popup = Popup(self.screen, "Opponent offers a draw!", duration=5000)
            self.popup.show()
        elif action == "resign":
            self.popup = Popup(self.screen, "Opponent resigned! You win!", duration=5000)
            self.popup.show()
            self.game_ended = True
        elif action == "end":
            self.popup = Popup(self.screen, "Game ended by opponent", duration=3000)
            self.popup.show()
            self.game_ended = True
        elif action == "quit":
            self.popup = Popup(self.screen, "Opponent disconnected", duration=3000)
            self.popup.show()
            self.game_ended = True

    def draw_turn_indicator(self):
        """Draw the sidebar color - FIXED to show correct colors"""
        if self.game_ended:
            sidebar_color = (100, 100, 100)  # Gray when game ended
        else:
            # FIXED: White background for white's turn, black background for black's turn
            sidebar_color = (255, 255, 255) if self.game_rules.current_turn == 'white' else (0, 0, 0)
            
        pygame.draw.rect(self.screen, sidebar_color, (self.board_width, 0, self.sidebar_width, self.board_height))

    def handle_move(self, selected_piece, final_position) -> bool:
        """Handle a move - COMPLETELY FIXED"""
        print(f"DEBUG: Attempting move - My turn: {self.is_my_turn}, Game ended: {self.game_ended}")
        print(f"DEBUG: Selected piece: {selected_piece.type} {selected_piece.color} at {selected_piece.position}")
        print(f"DEBUG: My color: {self.my_color}, Current turn: {self.game_rules.current_turn}")
        
        if not self.is_my_turn or self.game_ended:
            print("DEBUG: Not my turn or game ended, ignoring move")
            return False
            
        if selected_piece.color != self.my_color:
            print(f"DEBUG: Wrong color piece - selected {selected_piece.color}, my color is {self.my_color}")
            return False
            
        if selected_piece.color != self.game_rules.current_turn:
            print(f"DEBUG: Not the current player's turn - current: {self.game_rules.current_turn}, piece: {selected_piece.color}")
            return False
            
        if not self.game_rules.is_move_legal(selected_piece, final_position):
            print("DEBUG: Illegal move attempted")
            return False
            
        original_position = selected_piece.position
        captured_piece = self.chess_board.get_piece_at(final_position)
        
        print(f"DEBUG: Moving piece from {original_position} to {final_position}")
        
        if self.chess_board.move_piece(selected_piece, final_position):
            self.game_rules.record_move(selected_piece, original_position, final_position, captured_piece)
            
            # Handle promotion
            promotion = None
            if (selected_piece.type == 'pawn' and 
                ((selected_piece.color == 'white' and final_position[0] == 0) or 
                 (selected_piece.color == 'black' and final_position[0] == 7))):
                promotion = 'q'  # Auto-promote to queen for now
                print(f"DEBUG: Pawn promotion to queen")
                
            # Send move to opponent
            print(f"DEBUG: Sending move to opponent: {original_position} -> {final_position}")
            self.network_game.send_move(original_position, final_position, promotion)
            
            # Switch turns locally
            self.game_rules.switch_turn()
            self.sound_manager.play_move_sound()
            
            # Now wait for opponent
            self.is_my_turn = False
            self.waiting_for_opponent = True
            
            print(f"DEBUG: Move completed. New turn: {self.game_rules.current_turn}, waiting for opponent")
            
            # Reset sound flags
            self.check_sound_played = False
            self.checkmate_sound_played = False
            self.stalemate_sound_played = False
            
            return True
            
        print("DEBUG: Failed to move piece on board")
        return False
 
    def handle_events(self):
        """Handle pygame events"""
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return 'quit'

            # Handle save dialog events
            if self.save_dialog:
                result = self.save_dialog.handle_event(event)
                if result:
                    if result.startswith("save:"):
                        game_name = result[5:]
                        success, message = self.save_manager.save_game(
                            self.chess_board, self.game_rules, 'Online_Multiplayer', game_name
                        )
                        self.popup = Popup(self.screen, message, duration=3000)
                        self.popup.show()
                    self.save_dialog = None
                return None

            # Handle load dialog events
            if self.load_dialog:
                result = self.load_dialog.handle_event(event)
                if result:
                    if result.startswith("load:"):
                        game_name = result[5:]
                        success, message, game_mode = self.save_manager.load_game(
                            game_name, self.chess_board, self.game_rules
                        )
                        self.popup = Popup(self.screen, message, duration=3000)
                        self.popup.show()
                    elif result.startswith("delete:"):
                        game_name = result[7:]
                        success, message = self.save_manager.delete_game(game_name)
                        self.popup = Popup(self.screen, message, duration=3000)
                        self.popup.show()
                        # Refresh dialog
                        saved_games = self.save_manager.get_saved_games()
                        self.load_dialog = LoadDialog(self.screen_width, self.board_height, saved_games)
                    elif result == "cancel":
                        self.load_dialog = None
                return None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                menu_result = self.game_menu.handle_click(event.pos)
                if menu_result == 'resume':
                    self.game_menu.menu_open = False
                elif menu_result == 'save_game':
                    self.save_dialog = SaveDialog(self.screen_width, self.board_height)
                    self.game_menu.menu_open = False
                elif menu_result == 'load_game':
                    saved_games = self.save_manager.get_saved_games()
                    self.load_dialog = LoadDialog(self.screen_width, self.board_height, saved_games)
                    self.game_menu.menu_open = False
                elif menu_result == 'main_menu':
                    return 'main_menu'

                if not self.game_menu.menu_open and not self.save_dialog and not self.load_dialog:
                    if (50 <= event.pos[0] <= self.board_width and 
                        50 <= event.pos[1] <= self.board_height):
                        
                        board_pos = self.chess_board.handle_click(event.pos)
                        
                        if self.selected_piece is None:
                            piece = self.chess_board.get_piece_at(board_pos)
                            if (piece and piece.color == self.my_color and 
                                piece.color == self.game_rules.current_turn and
                                self.is_my_turn):
                                self.selected_piece = piece
                        else:
                            if board_pos == self.selected_piece.position:
                                self.selected_piece = None
                            else:
                                if self.handle_move(self.selected_piece, board_pos):
                                    self.selected_piece = None
                                else:
                                    piece = self.chess_board.get_piece_at(board_pos)
                                    if (piece and piece.color == self.my_color and 
                                        piece.color == self.game_rules.current_turn and
                                        self.is_my_turn):
                                        self.selected_piece = piece
                                    else:
                                        self.selected_piece = None

        return None

    def update(self, dt: int):
        """Update game state"""
        # Update dialogs
        if self.save_dialog:
            self.save_dialog.update(dt)

    def update_game_status(self):
        """Update game status and play appropriate sounds"""
        current_player = self.game_rules.current_turn
        opponent = 'black' if current_player == 'white' else 'white'

        game_over = self.game_rules.is_game_over()
        if game_over:
            if "Checkmate" in game_over and not self.checkmate_sound_played:
                winner = 'White' if current_player == 'black' else 'Black'
                self.status_display.update_status(f"{winner} wins by checkmate!", "checkmate")
                self.sound_manager.play_checkmate_sound()
                self.checkmate_sound_played = True
                self.game_ended = True
            elif "Stalemate" in game_over and not self.stalemate_sound_played:
                self.status_display.update_status("Game ends in stalemate!", "stalemate")
                self.sound_manager.play_stalemate_sound()
                self.stalemate_sound_played = True
                self.game_ended = True
            return

        if self.game_rules.is_in_check(current_player) and not self.check_sound_played:
            checking_piece = None
            opponent_pieces = self.chess_board.get_pieces_by_color(opponent)
            king_position = self.chess_board.find_king(current_player).position

            for piece in opponent_pieces:
                if king_position in piece.get_possible_moves(self.chess_board):
                    checking_piece = piece.type
                    break
            
            if current_player == 'black':
                self.status_display.update_status("Black king is in check!", "check", checking_piece, current_player)
            else:
                self.status_display.update_status("White king is in check!", "check", checking_piece, current_player)
            
            self.sound_manager.play_check_sound()
            self.check_sound_played = True


    def draw(self):
        """Draw the game"""
        # Fill with white background like other game modes
        self.screen.fill((255, 255, 255))
        
        # Draw the chess board
        self.chess_board.construct_board()

        # Highlight selected piece and possible moves
        if self.selected_piece:
            # Highlight selected piece
            x = self.chess_board.board_offset_x + self.selected_piece.position[1] * self.chess_board.tile_size
            y = self.chess_board.board_offset_y + self.selected_piece.position[0] * self.chess_board.tile_size
            pygame.draw.rect(self.screen, (255, 255, 0), (x, y, self.chess_board.tile_size, self.chess_board.tile_size), 3)
            
            # Draw possible moves
            possible_moves = self.selected_piece.get_possible_moves(self.chess_board)
            for move in possible_moves:
                if self.game_rules.is_move_legal(self.selected_piece, move):
                    move_x = self.chess_board.board_offset_x + move[1] * self.chess_board.tile_size
                    move_y = self.chess_board.board_offset_y + move[0] * self.chess_board.tile_size
                    highlight_surface = pygame.Surface((self.chess_board.tile_size, self.chess_board.tile_size), pygame.SRCALPHA)
                    pygame.draw.rect(highlight_surface, (0, 255, 0, 128), highlight_surface.get_rect())
                    self.screen.blit(highlight_surface, (move_x, move_y))

        # Draw pieces
        self.chess_board.draw_pieces()
        
        # Draw turn indicator sidebar
        self.draw_turn_indicator()
        
        # Update and draw game status
        self.update_game_status()
        
        # Draw status display and move history
        self.status_display.draw_move_history(self.screen, self.game_rules.move_history)
        self.status_display.draw(self.screen)
        
        # Draw online game status
        self._draw_online_status()
        
        # Draw game menu
        self.game_menu.draw_menu(self.screen)

        # Draw dialogs on top
        if self.save_dialog:
            self.save_dialog.draw(self.screen)
        if self.load_dialog:
            self.load_dialog.draw(self.screen)

        # Draw popup messages
        if self.popup:
            if not self.popup.draw():
                self.popup = None

        pygame.display.flip()



    def _draw_online_status(self):
        """Draw online game status information"""
        font = pygame.font.Font(None, 24)
        
        # Player role - use white text on sidebar
        role = "White" if self.network_game.is_white else "Black"
        role_text = font.render(f"You are: {role}", True, (255, 255, 255))
        self.screen.blit(role_text, (self.board_width + 10, self.board_height - 120))
        
        # Turn indicator
        if self.game_ended:
            status_text = "Game Ended"
            color = (150, 150, 150)
        elif self.is_my_turn:
            status_text = "Your Turn"
            color = (0, 255, 0)
        else:
            status_text = "Opponent's Turn"
            color = (255, 255, 0)
            
        status_surface = font.render(status_text, True, color)
        self.screen.blit(status_surface, (self.board_width + 10, self.board_height - 100))
        
        # Current turn indicator
        current_turn_text = font.render(f"Current turn: {self.game_rules.current_turn.capitalize()}", True, (200, 200, 200))
        self.screen.blit(current_turn_text, (self.board_width + 10, self.board_height - 80))

    def run(self) -> Optional[str]:
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(60)
            
            result = self.handle_events()
            if result:
                return result
                
            self.update(dt)
            self.draw()

        return None