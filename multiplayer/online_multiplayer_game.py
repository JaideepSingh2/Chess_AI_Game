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
        
        # Online game state - FIXED LOGIC
        # White always goes first, so if we're white, it's our turn initially
        self.my_color = 'white' if self.network_game.is_white else 'black'
        self.is_my_turn = self.network_game.is_white  # White goes first
        self.waiting_for_opponent = False
        self.game_ended = False
        
        print(f"DEBUG: I am playing as {self.my_color}, is_my_turn: {self.is_my_turn}")
        
        # Set up network callbacks
        self.network_game.network.set_callback("move_received", self._handle_opponent_move)
        self.network_game.network.set_callback("game_action", self._handle_game_action)
        
    def _handle_opponent_move(self, move_str: str):
        """Handle move received from opponent"""
        print(f"DEBUG: Received opponent move: {move_str}")
        try:
            move_data = self.network_game.parse_move(move_str)
            if move_data:
                from_pos, to_pos, promotion = move_data
                print(f"DEBUG: Parsed move from {from_pos} to {to_pos}, promotion: {promotion}")
                
                # Find the piece at the from position
                piece = self.chess_board.get_piece_at(from_pos)
                if piece and piece.color == self.game_rules.current_turn:
                    print(f"DEBUG: Found piece {piece.type} at {from_pos}")
                    
                    # Handle promotion if needed
                    if promotion and piece.type == 'pawn':
                        # Check if this is actually a promotion move
                        if (piece.color == 'white' and to_pos[0] == 0) or (piece.color == 'black' and to_pos[0] == 7):
                            # Remove the pawn and create the promoted piece
                            self.chess_board.pieces.remove(piece)
                            promoted_piece = self._create_promoted_piece(promotion, piece.color, to_pos)
                            self.chess_board.pieces.append(promoted_piece)
                            
                            # Record the move with promotion
                            self.game_rules.record_move(piece, from_pos, to_pos, None)
                            self.game_rules.switch_turn()
                            self.sound_manager.play_move_sound()
                            
                            # Now it's our turn
                            self.is_my_turn = True
                            self.waiting_for_opponent = False
                            print("DEBUG: Opponent promoted pawn, now it's my turn")
                            return
                    
                    # Make the regular move
                    if self.chess_board.move_piece(piece, to_pos):
                        # Record the move
                        self.game_rules.record_move(piece, from_pos, to_pos, None)
                        self.game_rules.switch_turn()
                        self.sound_manager.play_move_sound()
                        
                        # Now it's our turn
                        self.is_my_turn = True
                        self.waiting_for_opponent = False
                        print("DEBUG: Opponent move processed, now it's my turn")
                    else:
                        print("DEBUG: Failed to move opponent's piece")
                else:
                    print(f"DEBUG: No valid piece found at {from_pos} or wrong color")
                        
        except Exception as e:
            print(f"Error handling opponent move: {e}")
    
    def _create_promoted_piece(self, promotion: str, color: str, position: tuple):
        """Create a promoted piece"""
        from code_logic.piece import Queen, Rook, Bishop, Knight
        
        piece_map = {
            'q': Queen,
            'r': Rook, 
            'b': Bishop,
            'n': Knight
        }
        
        piece_class = piece_map.get(promotion.lower(), Queen)
        piece_image = self.chess_board.get_piece_image(piece_class.__name__.lower(), color)
        return piece_class(self.screen, piece_image, color, position)
    
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
        """Draw the sidebar color to indicate current turn - FIXED COLORS"""
        if self.game_ended:
            sidebar_color = (100, 100, 100)  # Gray when game ended
        elif self.is_my_turn:
            # Use your normal game colors when it's your turn
            sidebar_color = (0, 0, 0) if self.game_rules.current_turn == 'white' else (255, 255, 255)
        else:
            # Different color when waiting for opponent
            sidebar_color = (150, 0, 0)  # Red when waiting
            
        pygame.draw.rect(self.screen, sidebar_color, (self.board_width, 0, self.sidebar_width, self.board_height))

    def update_game_status(self):
        """Update game status and play appropriate sounds"""
        current_player = self.game_rules.current_turn
        opponent = 'black' if current_player == 'white' else 'white'

        game_over = self.game_rules.is_game_over()
        if game_over:
            if "Checkmate" in game_over and not self.checkmate_sound_played:
                winner = 'black' if current_player == 'white' else 'white'
                self.status_display.update_status(game_over, "checkmate", current_turn=winner)
                self.sound_manager.play_checkmate_sound()
                self.checkmate_sound_played = True
                self.game_ended = True
                # Notify opponent
                self.network_game.end_game()
            elif "Stalemate" in game_over and not self.stalemate_sound_played:
                self.status_display.update_status(game_over, "stalemate")
                self.sound_manager.play_stalemate_sound()
                self.stalemate_sound_played = True
                self.game_ended = True
                # Notify opponent
                self.network_game.end_game()
            return

        if self.game_rules.is_in_check(current_player) and not self.check_sound_played:
            checking_piece = None
            opponent_pieces = self.chess_board.get_pieces_by_color(opponent)
            king_position = self.chess_board.find_king(current_player).position

            for piece in opponent_pieces:
                if king_position in piece.get_possible_moves(self.chess_board):
                    if opponent == 'black':
                        tempcolor2 = 'white'
                    else:
                        tempcolor2 = 'black'
                    checking_piece = f"{tempcolor2.capitalize()}'s {piece.__class__.__name__}"
                    break
            
            if current_player == 'black':
                tempplayer = 'white'
            else:
                tempplayer = 'black'

            self.status_display.update_status(
                f"{tempplayer.capitalize()} is in Check!",
                "check",
                checking_piece
            )
            self.sound_manager.play_check_sound()
            self.check_sound_played = True

    def handle_move(self, selected_piece, final_position) -> bool:
        """Handle a move and return whether it was successful"""
        # Only allow moves if it's our turn and the piece is our color
        if not self.is_my_turn or self.game_ended:
            print("DEBUG: Not my turn or game ended, ignoring move")
            return False
            
        if selected_piece.color != self.my_color:
            print(f"DEBUG: Wrong color piece - selected {selected_piece.color}, my color is {self.my_color}")
            return False
            
        if self.game_rules.is_move_legal(selected_piece, final_position) and self.chess_board.move_piece(selected_piece, final_position):
            original_position = selected_piece.position
            current_player = self.game_rules.current_turn
            opponent = 'black' if current_player == 'white' else 'white'

            captured_piece = self.chess_board.get_piece_at(final_position)
            self.game_rules.record_move(
                selected_piece,
                original_position,
                final_position,
                captured_piece
            )

            # Send move to opponent
            promotion = None
            # Check for pawn promotion
            if (selected_piece.type == 'pawn' and 
                ((current_player == 'white' and final_position[0] == 0) or 
                 (current_player == 'black' and final_position[0] == 7))):
                promotion = 'q'  # Default to queen
            
            self.network_game.send_move(original_position, final_position, promotion)
            
            # Now it's opponent's turn
            self.is_my_turn = False
            self.waiting_for_opponent = True
            print("DEBUG: Sent my move, now waiting for opponent")

            # Check for game over
            game_over = self.game_rules.is_game_over()
            if game_over:
                if "Checkmate" in game_over and not self.checkmate_sound_played:
                    winner = 'black' if current_player == 'white' else 'white'
                    self.status_display.update_status(game_over, "checkmate", current_turn=winner)
                    self.sound_manager.play_checkmate_sound()
                    self.checkmate_sound_played = True
                    self.game_ended = True
                    self.network_game.end_game()
                elif "Stalemate" in game_over and not self.stalemate_sound_played:
                    self.status_display.update_status(game_over, "stalemate")
                    self.sound_manager.play_stalemate_sound()
                    self.stalemate_sound_played = True
                    self.game_ended = True
                    self.network_game.end_game()
                return True

            # Check for check
            if self.game_rules.is_in_check(current_player) and not self.check_sound_played:
                checking_piece = None
                opponent_pieces = self.chess_board.get_pieces_by_color(opponent)
                king_position = self.chess_board.find_king(current_player).position

                for piece in opponent_pieces:
                    if king_position in piece.get_possible_moves(self.chess_board):
                        if opponent == 'black':
                            tempcolor2 = 'white'
                        else:
                            tempcolor2 = 'black'
                        checking_piece = f"{tempcolor2.capitalize()}'s {piece.__class__.__name__}"
                        break
                
                if current_player == 'black':
                    tempplayer = 'white'
                else:
                    tempplayer = 'black'

                self.status_display.update_status(
                    f"{tempplayer.capitalize()} is in Check!",
                    "check",
                    checking_piece,
                    current_turn=current_player
                )
                self.sound_manager.play_check_sound()
                self.check_sound_played = True
            else:
                self.check_sound_played = False

            self.game_rules.switch_turn()
            self.sound_manager.play_move_sound()
            self.check_sound_played = False
            self.checkmate_sound_played = False
            self.stalemate_sound_played = False
            return True
        return False

    def handle_events(self):
        """Handle pygame events"""
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.network_game.end_game()
                self.running = False

            # Handle save dialog events
            if self.save_dialog:
                result = self.save_dialog.handle_event(event)
                if result:
                    if result == "cancel":
                        self.save_dialog = None
                    elif result.startswith("save:"):
                        save_name = result[5:]
                        success, message = self.save_manager.save_game(
                            self.chess_board, self.game_rules, 'online_multiplayer', save_name
                        )
                        self.save_dialog = None
                        self.popup = Popup(self.screen, message, duration=3000)
                        self.popup.show()
                continue

            # Handle load dialog events
            if self.load_dialog:
                result = self.load_dialog.handle_event(event)
                if result:
                    if result == "cancel":
                        self.load_dialog = None
                    elif result.startswith("load:"):
                        game_name = result[5:]
                        success, message, loaded_game_mode = self.save_manager.load_game(
                            game_name, self.chess_board, self.game_rules
                        )
                        self.load_dialog = None
                        if success:
                            # Reset game state
                            self.selected_piece = None
                            self.check_sound_played = False
                            self.checkmate_sound_played = False
                            self.stalemate_sound_played = False
                        self.popup = Popup(self.screen, message, duration=3000)
                        self.popup.show()
                    elif result.startswith("delete:"):
                        game_name = result[7:]
                        success, message = self.save_manager.delete_game(game_name)
                        # Refresh the dialog with updated game list
                        saved_games = self.save_manager.get_saved_games()
                        self.load_dialog = LoadDialog(self.screen_width, self.board_height, saved_games)
                        self.popup = Popup(self.screen, message, duration=2000)
                        self.popup.show()
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Handle menu clicks
                menu_action = self.game_menu.handle_click(mouse_pos)
                if menu_action:
                    if menu_action == 'resume':
                        self.game_menu.menu_open = False
                    elif menu_action == 'save_game':
                        self.save_dialog = SaveDialog(self.screen_width, self.board_height)
                    elif menu_action == 'load_game':
                        saved_games = self.save_manager.get_saved_games()
                        if saved_games:
                            self.load_dialog = LoadDialog(self.screen_width, self.board_height, saved_games)
                        else:
                            self.popup = Popup(self.screen, "No saved games found!", duration=2000)
                            self.popup.show()
                    elif menu_action == 'main_menu':
                        self.network_game.end_game()
                        self.running = False
                        return 'main_menu'
                    continue

                # Handle piece selection only if it's our turn and game hasn't ended
                if not self.game_menu.menu_open and self.is_my_turn and not self.game_ended:
                    position = pygame.mouse.get_pos()
                    tile_position = self.chess_board.handle_click(position)
                    piece = self.chess_board.get_piece_at(tile_position) if tile_position else None

                    if self.selected_piece is None:
                        # Select a piece if it's our color and matches current turn
                        if (piece and 
                            piece.color == self.my_color and 
                            piece.color == self.game_rules.current_turn):
                            self.selected_piece = piece
                            print(f"DEBUG: Selected {piece.type} at {piece.position}")
                    else:
                        # Try to move the selected piece
                        if tile_position and self.handle_move(self.selected_piece, tile_position):
                            self.selected_piece = None
                        else:
                            # Reselect if clicking on another of our pieces
                            if (piece and 
                                piece.color == self.my_color and 
                                piece.color == self.game_rules.current_turn):
                                self.selected_piece = piece
                                print(f"DEBUG: Reselected {piece.type} at {piece.position}")
                            else:
                                self.selected_piece = None

        return None

    def update(self, dt: int):
        """Update game state"""
        # Update dialogs
        if self.save_dialog:
            self.save_dialog.update(dt)

    def draw(self):
        """Draw the game"""
        self.screen.fill((255, 255, 255))
        self.chess_board.construct_board()

        # Highlight selected piece and possible moves
        if self.selected_piece:
            x = self.chess_board.board_offset_x + self.selected_piece.position[1] * self.chess_board.tile_size
            y = self.chess_board.board_offset_y + self.selected_piece.position[0] * self.chess_board.tile_size
            pygame.draw.rect(self.screen, (255, 255, 0), (x, y, self.chess_board.tile_size, self.chess_board.tile_size), 3)

            possible_moves = self.selected_piece.get_possible_moves(self.chess_board)
            for move in possible_moves:
                move_x = self.chess_board.board_offset_x + move[1] * self.chess_board.tile_size
                move_y = self.chess_board.board_offset_y + move[0] * self.chess_board.tile_size
                highlight_surface = pygame.Surface((self.chess_board.tile_size, self.chess_board.tile_size), pygame.SRCALPHA)
                pygame.draw.rect(highlight_surface, (0, 255, 0, 128), highlight_surface.get_rect())
                self.screen.blit(highlight_surface, (move_x, move_y))

        self.chess_board.draw_pieces()
        self.draw_turn_indicator()
        self.update_game_status()
        self.status_display.draw_move_history(self.screen, self.game_rules.move_history)
        self.status_display.draw(self.screen)
        
        # Draw online game status
        self._draw_online_status()
        
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
        
        # Player role
        role = "White" if self.network_game.is_white else "Black"
        role_text = font.render(f"You are: {role}", True, (255, 255, 255))
        self.screen.blit(role_text, (self.board_width + 10, self.board_height - 100))
        
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
        self.screen.blit(status_surface, (self.board_width + 10, self.board_height - 80))
        
        # Current turn indicator
        current_turn_text = font.render(f"Current turn: {self.game_rules.current_turn.capitalize()}", True, (200, 200, 200))
        self.screen.blit(current_turn_text, (self.board_width + 10, self.board_height - 60))

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