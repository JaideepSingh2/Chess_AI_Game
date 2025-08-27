import pygame
import os
import threading
from ui.popup import Popup
from code_logic.chessboard import ChessBoard
from code_logic.game_rules import GameRules
from code_logic.chess_ai import ChessAI
from audio.sounds import SoundManager
from ui.start_menu import StartMenu
from ui.game_menu import GameMenu
from ui.status_display import StatusDisplay
from code_logic.save_manager import SaveManager
from ui.save_dialog import SaveDialog
from ui.load_dialog import LoadDialog
from ui.connection_dialog import ConnectionDialog
from ui.online_lobby import OnlineLobby
from multiplayer.network import NetworkClient, NetworkGame
from multiplayer.online_multiplayer_game import OnlineMultiplayerGame

def main():
    pygame.init()
    sound_manager = SoundManager()
    board_width, board_height = 900, 900
    sidebar_width = 250
    screen_width = board_width + sidebar_width
    screen = pygame.display.set_mode((screen_width, board_height))
    pygame.display.set_caption('Chess AI Game')
    
    save_manager = SaveManager()
    start_menu = StartMenu(screen_width, board_height)
    
    while True:
        choice = start_menu.run()
        
        if choice == 'Human_vs_Human':
            run_game(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, 'Human_vs_Human')
        elif choice == 'Human_vs_AI':
            run_game(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, 'Human_vs_AI')
        elif choice == 'AI_vs_AI':
            run_game(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, 'AI_vs_AI')
        elif choice == 'online_multiplayer':
            # Run online multiplayer
            result = run_online_multiplayer(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager)
            if result == 'main_menu':
                continue
        elif choice.startswith('load_game:'):
            # Load and run a saved game
            game_name = choice[10:]  # Remove 'load_game:' prefix
            load_and_run_game(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, game_name)


def run_online_multiplayer(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager):
    """Handle online multiplayer game flow"""
    
    # Show connection dialog
    connection_dialog = ConnectionDialog(screen_width, board_height)
    clock = pygame.time.Clock()
    
    while True:
        dt = clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'main_menu'
                
            result = connection_dialog.handle_event(event)
            if result is None:  # Cancel
                return 'main_menu'
            elif result is not False:  # Got connection info
                server_address, use_ipv6 = result
                break
        else:
            connection_dialog.update(dt)
            screen.fill((30, 30, 30))
            connection_dialog.draw(screen)
            pygame.display.flip()
            continue
        break
    
    # Try to connect to server
    network_client = NetworkClient()
    
    # Show connecting message
    popup = Popup(screen, f"Connecting to {server_address}...")
    popup.show()
    
    screen.fill((30, 30, 30))
    popup.draw()
    pygame.display.flip()
    
    success, message = network_client.connect(server_address, 26104)
    
    if not success:
        # Show error message
        error_popup = Popup(screen, f"Connection failed: {message}", duration=5000)
        error_popup.show()
        
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < 5000:
            screen.fill((30, 30, 30))
            if not error_popup.draw():
                break
            pygame.display.flip()
            clock.tick(60)
        
        network_client.disconnect()
        return 'main_menu'
    
    # Connected successfully, show lobby
    try:
        lobby = OnlineLobby(screen_width, board_height, network_client)
        
        while True:
            dt = clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    network_client.disconnect()
                    return 'main_menu'
                    
                result = lobby.handle_event(event)
                if result == "disconnect":
                    network_client.disconnect()
                    return 'main_menu'
                elif isinstance(result, tuple) and result[0] == "start_game":
                    # Game is starting
                    is_white = result[1]
                    
                    # Create network game
                    network_game = NetworkGame(network_client)
                    network_game.is_white = is_white
                    network_game.game_active = True
                    
                    print(f"DEBUG: Starting game as {'White' if is_white else 'Black'}")
                    
                    # Start online game
                    online_game = OnlineMultiplayerGame(
                        screen, screen_width, board_height, sidebar_width,
                        sound_manager, save_manager, network_game
                    )
                    
                    game_result = online_game.run()
                    
                    # Game ended, return to lobby or main menu
                    if game_result in ['main_menu', 'quit']:
                        network_client.disconnect()
                        return 'main_menu'
                    else:
                        # Return to lobby for another game
                        lobby = OnlineLobby(screen_width, board_height, network_client)
                        break
            
            # Check for lobby updates
            lobby_result = lobby.update()
            if isinstance(lobby_result, tuple) and lobby_result[0] == "start_game":
                # Game is starting from update (when we sent the request)
                is_white = lobby_result[1]
                
                # Create network game
                network_game = NetworkGame(network_client)
                network_game.is_white = is_white
                network_game.game_active = True
                
                print(f"DEBUG: Starting game as {'White' if is_white else 'Black'}")
                
                # Start online game
                online_game = OnlineMultiplayerGame(
                    screen, screen_width, board_height, sidebar_width,
                    sound_manager, save_manager, network_game
                )
                
                game_result = online_game.run()
                
                # Game ended, return to lobby or main menu
                if game_result in ['main_menu', 'quit']:
                    network_client.disconnect()
                    return 'main_menu'
                else:
                    # Return to lobby for another game
                    lobby = OnlineLobby(screen_width, board_height, network_client)
                    break
            
            screen.fill((30, 30, 30))
            lobby.draw(screen)
            pygame.display.flip()
            
    except Exception as e:
        # Handle any errors
        print(f"ERROR in online multiplayer: {e}")
        error_popup = Popup(screen, f"Error: {str(e)}", duration=5000)
        error_popup.show()
        
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < 5000:
            screen.fill((30, 30, 30))
            if not error_popup.draw():
                break
            pygame.display.flip()
            clock.tick(60)
        
        network_client.disconnect()
        return 'main_menu'


def load_and_run_game(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, game_name):
    """Load and run a saved game"""
    board_width = screen_width - sidebar_width
    chess_board = ChessBoard(screen, board_width, board_height)
    game_rules = GameRules(chess_board)
    
    # Load the game
    success, message, game_mode = save_manager.load_game(game_name, chess_board, game_rules)
    
    if success:
        # Show success popup briefly
        popup = Popup(screen, f"Loaded game: {game_name}")
        popup.show()
        
        # Brief display of loading message
        clock = pygame.time.Clock()
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < 1500:  # Show for 1.5 seconds
            screen.fill((30, 30, 30))
            if not popup.draw():
                break
            pygame.display.flip()
            clock.tick(60)
        
        # Run the loaded game
        run_game(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, game_mode, chess_board, game_rules)
    else:
        # Show error and return to menu
        popup = Popup(screen, f"Failed to load game: {message}", duration=3000)
        popup.show()
        
        # Show popup for a moment then return
        clock = pygame.time.Clock()
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < 3000:
            screen.fill((30, 30, 30))
            if not popup.draw():
                break
            pygame.display.flip()
            clock.tick(60)


def run_game(screen, screen_width, board_height, sidebar_width, sound_manager, save_manager, game_mode='Human_vs_Human', chess_board=None, game_rules=None):
    board_width = screen_width - sidebar_width
    
    # Initialize game components if not provided (new game)
    if chess_board is None:
        chess_board = ChessBoard(screen, board_width, board_height)
    if game_rules is None:
        game_rules = GameRules(chess_board)
    
    game_menu = GameMenu(screen_width, board_height, sidebar_width)
    clock = pygame.time.Clock()
    popup = None
    save_dialog = None
    load_dialog = None

    # Initialize AI based on game mode
    ai_white = ChessAI(chess_board, game_rules, depth=3) if game_mode == 'AI_vs_AI' else None
    ai_black = ChessAI(chess_board, game_rules, depth=3) if game_mode in ['Human_vs_AI', 'AI_vs_AI'] else None

    ai_move_results = {'white': None, 'black': None}
    turn_lock = threading.Lock()
    ai_move_ready = threading.Event()
    ai_thread = None

    def calculate_ai_move(ai, color):
        best_move = ai.get_best_move(color)
        with turn_lock:
            ai_move_results[color] = best_move
            ai_move_ready.set()

    running = True
    selected_piece = None
    status_display = StatusDisplay(board_width, board_height, sidebar_width)
    if ai_white:
        ai_white.status_display = status_display
    if ai_black:
        ai_black.status_display = status_display

    check_sound_played = False
    checkmate_sound_played = False
    stalemate_sound_played = False

    def draw_turn_indicator():
        sidebar_color = (255, 255, 255) if game_rules.current_turn == 'white' else (0, 0, 0)
        pygame.draw.rect(screen, sidebar_color, (board_width, 0, sidebar_width, board_height))

    def update_game_status():
        nonlocal check_sound_played, checkmate_sound_played, stalemate_sound_played
        current_player = game_rules.current_turn
        opponent = 'black' if current_player == 'white' else 'white'

        game_over = game_rules.is_game_over()
        if game_over:
            if "Checkmate" in game_over and not checkmate_sound_played:
                winner = 'black' if current_player == 'white' else 'white'
                status_display.update_status(game_over, "checkmate", current_turn=winner)
                sound_manager.play_checkmate_sound()
                checkmate_sound_played = True
            elif "Stalemate" in game_over and not stalemate_sound_played:
                status_display.update_status(game_over, "stalemate")
                sound_manager.play_stalemate_sound()
                stalemate_sound_played = True
            return

        if game_rules.is_in_check(current_player) and not check_sound_played:
            checking_piece = None
            opponent_pieces = chess_board.get_pieces_by_color(opponent)
            king_position = chess_board.find_king(current_player).position

            for piece in opponent_pieces:
                if king_position in piece.get_possible_moves(chess_board):
                    if (opponent == 'black'):
                        tempcolor2 = 'white'
                    else:
                        tempcolor2 = 'black'
                    checking_piece = f"{tempcolor2.capitalize()}'s {piece.__class__.__name__}"
                    break

            if (current_player == 'black'):
                tempplayer = 'white'
            else:
                tempplayer = 'black'

            status_display.update_status(
                f"{tempplayer.capitalize()} is in Check!",
                "check",
                checking_piece
            )
            sound_manager.play_check_sound()
            check_sound_played = True

    def handle_move(selected_piece, final_position):
        nonlocal check_sound_played, checkmate_sound_played, stalemate_sound_played
        if game_rules.is_move_legal(selected_piece, final_position) and chess_board.move_piece(selected_piece, final_position):
            current_player = game_rules.current_turn
            opponent = 'black' if current_player == 'white' else 'white'

            captured_piece = chess_board.get_piece_at(final_position)
            game_rules.record_move(
                selected_piece,
                selected_piece.position,
                final_position,
                captured_piece
            )

            game_over = game_rules.is_game_over()
            if game_over:
                if "Checkmate" in game_over and not checkmate_sound_played:
                    winner = 'black' if current_player == 'white' else 'white'
                    status_display.update_status(game_over, "checkmate", current_turn=winner)
                    sound_manager.play_checkmate_sound()
                    checkmate_sound_played = True
                elif "Stalemate" in game_over and not stalemate_sound_played:
                    status_display.update_status(game_over, "stalemate")
                    sound_manager.play_stalemate_sound()
                    stalemate_sound_played = True
                return True

            if game_rules.is_in_check(current_player) and not check_sound_played:
                checking_piece = None
                opponent_pieces = chess_board.get_pieces_by_color(opponent)
                king_position = chess_board.find_king(current_player).position

                for piece in opponent_pieces:
                    if king_position in piece.get_possible_moves(chess_board):
                        if (opponent == 'black'):
                            tempcolor2 = 'white'
                        else:
                            tempcolor2 = 'black'
                        checking_piece = f"{tempcolor2.capitalize()}'s {piece.__class__.__name__}"
                        break
                
                if (current_player == 'black'):
                    tempplayer = 'white'
                else:
                    tempplayer = 'black'

                status_display.update_status(
                    f"{tempplayer.capitalize()} is in Check!",
                    "check",
                    checking_piece,
                    current_turn=current_player
                )
                sound_manager.play_check_sound()
                check_sound_played = True
            else:
                check_sound_played = False

            game_rules.switch_turn()
            sound_manager.play_move_sound()
            check_sound_played = False
            checkmate_sound_played = False
            stalemate_sound_played = False
            return True
        return False

    while running:
        dt = clock.tick(60)
        mouse_pos = pygame.mouse.get_pos()

        current_turn = game_rules.current_turn
        current_ai = ai_black if current_turn == 'white' else ai_white

        # Handle AI moves (non-blocking, threaded)
        if game_mode in ['Human_vs_AI', 'AI_vs_AI'] and current_ai and not save_dialog and not load_dialog and not game_menu.menu_open:
            if not ai_move_ready.is_set() and (ai_thread is None or not ai_thread.is_alive()):
                ai_thread = threading.Thread(target=calculate_ai_move, args=(current_ai, current_turn))
                ai_thread.start()
            elif ai_move_ready.is_set():
                with turn_lock:
                    best_move = ai_move_results[current_turn]
                    if best_move:
                        piece, new_position = best_move
                        handle_move(piece, new_position)
                        ai_move_results[current_turn] = None
                        ai_move_ready.clear()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle save dialog events
            if save_dialog:
                result = save_dialog.handle_event(event)
                if result:
                    if result == "cancel":
                        save_dialog = None
                    elif result.startswith("save:"):
                        save_name = result[5:]
                        success, message = save_manager.save_game(chess_board, game_rules, game_mode, save_name)
                        save_dialog = None
                        popup = Popup(screen, message, duration=3000)
                        popup.show()
                continue

            # Handle load dialog events
            if load_dialog:
                result = load_dialog.handle_event(event)
                if result:
                    if result == "cancel":
                        load_dialog = None
                    elif result.startswith("load:"):
                        game_name = result[5:]
                        success, message, loaded_game_mode = save_manager.load_game(game_name, chess_board, game_rules)
                        load_dialog = None
                        if success:
                            # Update game mode and AI
                            game_mode = loaded_game_mode
                            ai_white = ChessAI(chess_board, game_rules, depth=4) if game_mode == 'AI_vs_AI' else None
                            ai_black = ChessAI(chess_board, game_rules, depth=3) if game_mode in ['Human_vs_AI', 'AI_vs_AI'] else None
                            if ai_white:
                                ai_white.status_display = status_display
                            if ai_black:
                                ai_black.status_display = status_display
                            # Reset AI state
                            ai_move_ready.clear()
                        popup = Popup(screen, message, duration=3000)
                        popup.show()
                    elif result.startswith("delete:"):
                        game_name = result[7:]
                        success, message = save_manager.delete_game(game_name)
                        # Refresh the dialog with updated game list
                        saved_games = save_manager.get_saved_games()
                        load_dialog = LoadDialog(screen_width, board_height, saved_games)
                        popup = Popup(screen, message, duration=2000)
                        popup.show()
                continue

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Always allow menu clicks, even in AI vs AI mode
                menu_action = game_menu.handle_click(mouse_pos)
                if menu_action:
                    if menu_action == 'resume':
                        game_menu.menu_open = False
                    elif menu_action == 'save_game':
                        save_dialog = SaveDialog(screen_width, board_height)
                    elif menu_action == 'load_game':
                        saved_games = save_manager.get_saved_games()
                        if saved_games:
                            load_dialog = LoadDialog(screen_width, board_height, saved_games)
                        else:
                            popup = Popup(screen, "No saved games found!", duration=2000)
                            popup.show()
                    elif menu_action == 'main_menu':
                        return
                    continue

                # Only allow piece selection if not AI vs AI and menu is closed
                if not game_menu.menu_open and game_mode != 'AI_vs_AI':
                    position = pygame.mouse.get_pos()
                    tile_position = chess_board.handle_click(position)
                    piece = chess_board.get_piece_at(tile_position) if tile_position else None

                    if selected_piece is None:
                        if piece and piece.color == game_rules.current_turn:
                            selected_piece = piece
                    else:
                        if handle_move(selected_piece, tile_position):
                            selected_piece = None
                        else:
                            selected_piece = piece if piece and piece.color == game_rules.current_turn else None

        # Update dialogs
        if save_dialog:
            save_dialog.update(dt)


        # Draw everything
        screen.fill((255, 255, 255))
        chess_board.construct_board()

        # Highlight selected piece and possible moves
        if selected_piece:
            x = chess_board.board_offset_x + selected_piece.position[1] * chess_board.tile_size
            y = chess_board.board_offset_y + selected_piece.position[0] * chess_board.tile_size
            pygame.draw.rect(screen, (255, 255, 0), (x, y, chess_board.tile_size, chess_board.tile_size), 3)

            possible_moves = selected_piece.get_possible_moves(chess_board)
            for move in possible_moves:
                move_x = chess_board.board_offset_x + move[1] * chess_board.tile_size
                move_y = chess_board.board_offset_y + move[0] * chess_board.tile_size
                highlight_surface = pygame.Surface((chess_board.tile_size, chess_board.tile_size), pygame.SRCALPHA)
                pygame.draw.rect(highlight_surface, (0, 255, 0, 128), highlight_surface.get_rect())
                screen.blit(highlight_surface, (move_x, move_y))

        chess_board.draw_pieces()
        draw_turn_indicator()
        update_game_status()
        
        # FIXED: Draw status display first, then move history
        status_display.draw(screen)
        status_display.draw_move_history(screen, game_rules.move_history)
        
        game_menu.draw_menu(screen)

        # Draw dialogs on top
        if save_dialog:
            save_dialog.draw(screen)
        if load_dialog:
            load_dialog.draw(screen)

        # Draw popup messages
        if popup:
            if not popup.draw():
                popup = None

        pygame.display.flip()

if __name__ == "__main__":
    main()