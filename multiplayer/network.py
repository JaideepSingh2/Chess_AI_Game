import socket
import threading
import queue
import time
from typing import Optional, Tuple, Callable

class NetworkClient:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.player_id = None
        self.message_queue = queue.Queue()
        self.receive_thread = None
        self.callbacks = {}
        
    def connect(self, host: str, port: int = 26104) -> Tuple[bool, str]:
        """Connect to the server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)  # Longer timeout for connection
            self.socket.connect((host, port))
            
            # Send handshake immediately without starting receive thread yet
            self._send_raw_message("PyChess")
            self._send_raw_message("v3.2.0")
            
            # Wait for response directly from socket
            self.socket.settimeout(5.0)
            try:
                data = self.socket.recv(8)
                if not data:
                    return False, "No response from server"
                    
                response = data.decode('utf-8').strip()
                
                if response.startswith("key"):
                    self.player_id = int(response[3:])
                    self.connected = True
                    
                    # Now start the receive thread for ongoing communication
                    self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
                    self.receive_thread.start()
                    
                    return True, f"Connected as Player {self.player_id}"
                elif response == "errBusy":
                    return False, "Server is full"
                elif response == "errVer":
                    return False, "Version mismatch"
                elif response == "errLock":
                    return False, "Server is locked"
                else:
                    return False, f"Unknown response: {response}"
                    
            except socket.timeout:
                return False, "Handshake timeout"
                
        except socket.timeout:
            return False, "Connection timeout"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
    
    def disconnect(self):
        """Disconnect from server"""
        if self.connected:
            self._send_message("quit")
            self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
    
    def get_player_list(self) -> Optional[list]:
        """Request list of online players"""
        if not self.connected:
            return None
            
        # Clear any old messages
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except:
                break
                
        self._send_message("pStat")
        response = self._wait_for_message(timeout=3.0)
        
        if response and response.startswith("enum"):
            try:
                player_count = int(response[4:])
                players = []
                
                for _ in range(player_count):
                    player_data = self._wait_for_message(timeout=2.0)
                    if player_data and len(player_data) >= 5:
                        try:
                            player_id = int(player_data[:-1])  # All except last character
                            status_char = player_data[-1]      # Last character
                            status = 'active' if status_char == 'a' else 'busy'
                            
                            players.append({
                                'id': player_id,
                                'status': status,
                                'is_self': player_id == self.player_id
                            })
                        except ValueError:
                            continue
                            
                return players
            except ValueError:
                return None
        return None
    
    def send_game_request(self, target_player_id: int) -> bool:
        """Send game request to another player"""
        if not self.connected:
            return False
            
        # Clear message queue
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except:
                break
                
        self._send_message(f"rg{target_player_id}")
        
        # Wait for msgOk response
        response = self._wait_for_message(timeout=5.0)
        if response == "msgOk":
            # Server confirmed request was sent, now send ready signal
            self._send_message("ready")
            return True
        elif response == "errPBusy":
            return False  # Player is busy
        elif response == "errKey":
            return False  # Invalid player ID
        else:
            return False
    
    def respond_to_game_request(self, requester_id: int, accept: bool):
        """Respond to a game request"""
        if not self.connected:
            return
        if accept:
            self._send_message(f"gmOk{requester_id}")
        else:
            self._send_message(f"gmNo{requester_id}")
    
    def send_move(self, move_data: str):
        """Send a chess move to opponent"""
        if self.connected:
            self._send_message(move_data)
    
    def send_game_action(self, action: str):
        """Send game action (draw, resign, end)"""
        if self.connected:
            self._send_message(action)
    
    def set_callback(self, message_type: str, callback: Callable):
        """Set callback for specific message types"""
        self.callbacks[message_type] = callback
    
    def _send_raw_message(self, message: str):
        """Send raw message during handshake"""
        if self.socket:
            try:
                # Pad message to 8 bytes exactly like reference
                padded_msg = message + (" " * (8 - len(message)))
                self.socket.sendall(padded_msg.encode('utf-8'))
            except:
                pass
    
    def _send_message(self, message: str):
        """Send message to server"""
        if self.socket and self.connected:
            try:
                # Pad message to 8 bytes exactly like reference
                padded_msg = message + (" " * (8 - len(message)))
                self.socket.sendall(padded_msg.encode('utf-8'))
            except:
                self.connected = False
    
    def _receive_messages(self):
        """Background thread to receive messages"""
        while self.connected and self.socket:
            try:
                self.socket.settimeout(1.0)
                data = self.socket.recv(8)
                if not data:
                    break
                    
                message = data.decode('utf-8').strip()
                if message and message != "........":  # Ignore heartbeat
                    self.message_queue.put(message)
                    self._handle_message(message)
                    
            except socket.timeout:
                continue
            except:
                break
        self.connected = False
    
    def _wait_for_message(self, timeout: float = 1.0) -> Optional[str]:
        """Wait for a message with timeout"""
        try:
            return self.message_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _handle_message(self, message: str):
        """Handle incoming messages with callbacks"""
        print(f"DEBUG: Received message: '{message}'")
        
        # Handle game requests (format: "gr1234" from server)
        if message.startswith("gr"):
            try:
                requester_id = int(message[2:])
                print(f"DEBUG: Game request from Player {requester_id}")
                if "game_request" in self.callbacks:
                    self.callbacks["game_request"](requester_id)
            except ValueError:
                pass
        
        # Handle game start confirmation
        elif message == "start":
            print("DEBUG: Received 'start' message - game beginning as White")
            if "game_start" in self.callbacks:
                self.callbacks["game_start"](True)  # You're white (requested the game)
        
        elif message == "nostart":
            print("DEBUG: Received 'nostart' message - game request rejected")
            if "game_rejected" in self.callbacks:
                self.callbacks["game_rejected"]()
        
        # Handle moves and game actions
        elif message in ["draw", "resign", "end", "quit", "close"]:
            print(f"DEBUG: Game action received: {message}")
            if "game_action" in self.callbacks:
                self.callbacks["game_action"](message)
        
        # Handle chess moves (4+ chars, not special messages)
        elif (len(message) >= 4 and 
              message not in ["errKey", "close", "msgOk", "errPBusy"] and
              not message.startswith("key") and
              not message.startswith("enum") and
              not message.startswith("gr")):
            print(f"DEBUG: Chess move received: {message}")
            if "move_received" in self.callbacks:
                self.callbacks["move_received"](message)


class NetworkGame:
    def __init__(self, network_client: NetworkClient):
        self.network = network_client
        self.is_white = None
        self.opponent_id = None
        self.game_active = False
        
    def start_as_white(self, opponent_id: int):
        """Start game as white player"""
        self.is_white = True
        self.opponent_id = opponent_id
        self.game_active = True
        
    def start_as_black(self, opponent_id: int):
        """Start game as black player"""
        self.is_white = False
        self.opponent_id = opponent_id
        self.game_active = True
        
    def send_move(self, from_pos: tuple, to_pos: tuple, promotion: str = None):
        """Send a move to the opponent"""
        if not self.game_active:
            return
            
        # Convert to algebraic notation
        move_str = self._pos_to_algebraic(from_pos) + self._pos_to_algebraic(to_pos)
        if promotion:
            move_str += promotion.lower()
            
        self.network.send_move(move_str)
    
    def _pos_to_algebraic(self, pos: tuple) -> str:
        """Convert (row, col) position to algebraic notation"""
        col_letter = chr(ord('a') + pos[1])
        row_number = str(8 - pos[0])
        return col_letter + row_number
    
    def _algebraic_to_pos(self, algebraic: str) -> tuple:
        """Convert algebraic notation to (row, col) position"""
        col = ord(algebraic[0]) - ord('a')
        row = 8 - int(algebraic[1])
        return (row, col)
    
    def parse_move(self, move_str: str) -> tuple:
        """Parse received move string"""
        if len(move_str) >= 4:
            from_pos = self._algebraic_to_pos(move_str[:2])
            to_pos = self._algebraic_to_pos(move_str[2:4])
            promotion = move_str[4] if len(move_str) > 4 else None
            return from_pos, to_pos, promotion
        return None
    
    def offer_draw(self):
        """Offer a draw to opponent"""
        if self.game_active:
            self.network.send_game_action("draw")
    
    def resign(self):
        """Resign the game"""
        if self.game_active:
            self.network.send_game_action("resign")
            self.game_active = False
    
    def end_game(self):
        """End the game normally"""
        if self.game_active:
            self.network.send_game_action("end")
            self.game_active = False