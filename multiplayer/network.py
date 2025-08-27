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
                    # Extract player ID
                    self.player_id = int(response[3:])
                    self.connected = True
                    
                    # Start receive thread now
                    self.receive_thread = threading.Thread(target=self._receive_messages, daemon=True)
                    self.receive_thread.start()
                    
                    return True, f"Connected successfully as Player {self.player_id}"
                elif response == "errBusy":
                    return False, "Server is full"
                elif response == "errVer":
                    return False, "Version mismatch"
                elif response == "errLock":
                    return False, "Server is locked"
                else:
                    return False, f"Unknown response: {response}"
                    
            except socket.timeout:
                return False, "Server did not respond"
                
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
                    player_info = self._wait_for_message(timeout=2.0)
                    if player_info and len(player_info) >= 5:
                        # Parse player info: "1234a" -> id=1234, status=active
                        player_id = int(player_info[:-1])
                        status = "active" if player_info[-1] == 'a' else "busy"
                        players.append({"id": player_id, "status": status})
                            
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
                if message and message != "........":                    
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
        """Handle incoming messages with callbacks - FIXED"""
        print(f"DEBUG: Received message: '{message}'")
        
        # Handle game requests
        if message.startswith("gr") and len(message) > 2:
            try:
                requester_id = int(message[2:])
                print(f"DEBUG: Game request from Player {requester_id}")
                if "game_request" in self.callbacks:
                    self.callbacks["game_request"](requester_id)
            except ValueError:
                pass
                
        # Handle game start
        elif message == "start":
            print("DEBUG: Received 'start' message - game beginning as White")
            if "game_start" in self.callbacks:
                self.callbacks["game_start"](True)  # White goes first
                
        # Handle game rejection  
        elif message == "nostart":
            print("DEBUG: Game request was rejected")
            if "game_rejected" in self.callbacks:
                self.callbacks["game_rejected"]()
                
        # Handle game actions
        elif message in ["draw", "resign", "end"]:
            print(f"DEBUG: Game action received: {message}")
            if "game_action" in self.callbacks:
                self.callbacks["game_action"](message)
                
        # Handle chess moves - IMPROVED FILTERING
        elif self._is_chess_move(message):
            print(f"DEBUG: Chess move received: {message}")
            if "move_received" in self.callbacks:
                self.callbacks["move_received"](message)
        else:
            # All other messages go to queue for synchronous handling
            # Don't print debug for routine server messages
            if message not in ["pStat"] and not message.endswith(('a', 'b')):
                print(f"DEBUG: Queuing message: {message}")
            self.message_queue.put(message)



    def _is_chess_move(self, message: str) -> bool:
        """Check if message is a valid chess move - COMPLETELY FIXED"""
        # Must be exactly 4 or 5 characters
        if not message or len(message) < 4 or len(message) > 5:
            return False
            
        # Exclude ALL known server messages
        server_messages = {
            "errKey", "close", "msgOk", "errPBusy", "pStat", "ready",
            "start", "nostart", "draw", "resign", "end", "quit", "gmOk", "gmNo"
        }
        
        if message in server_messages:
            return False
            
        # Exclude messages with known prefixes
        if (message.startswith(("enum", "gr", "key", "rg")) or 
            (len(message) >= 2 and message.endswith(('a', 'b')) and message[:-1].isdigit())):
            return False
        
        # Must be valid chess notation: letter+digit+letter+digit (optionally +letter)
        try:
            if (len(message) >= 4 and
                message[0] in 'abcdefgh' and message[1] in '12345678' and
                message[2] in 'abcdefgh' and message[3] in '12345678'):
                
                # If 5 characters, last must be promotion piece
                if len(message) == 5:
                    return message[4].lower() in 'qrbn'
                else:
                    return True
        except:
            pass
            
        return False



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
        """Send a move to the opponent - Fixed implementation"""
        if not self.game_active:
            print("DEBUG: Game not active, not sending move")
            return
            
        # Convert to algebraic notation
        move_str = self._pos_to_algebraic(from_pos) + self._pos_to_algebraic(to_pos)
        if promotion:
            move_str += promotion.lower()
            
        print(f"DEBUG: Sending move: {move_str}")
        self.network.send_move(move_str)    
    
    def _pos_to_algebraic(self, pos: tuple) -> str:
        """Convert (row, col) position to algebraic notation"""
        col_letter = chr(ord('a') + pos[1])
        row_number = str(8 - pos[0])
        return col_letter + row_number
    
    def _algebraic_to_pos(self, algebraic: str) -> tuple:
        """Convert algebraic notation to (row, col) position"""
        if len(algebraic) != 2:
            raise ValueError(f"Invalid algebraic notation: {algebraic}")
        col = ord(algebraic[0].lower()) - ord('a')
        row = 8 - int(algebraic[1])
        if not (0 <= row < 8 and 0 <= col < 8):
            raise ValueError(f"Position out of bounds: {algebraic}")
        return (row, col)    
    
    def parse_move(self, move_str: str) -> tuple:
        """Parse received move string - Fixed implementation"""
        print(f"DEBUG: Parsing move string: '{move_str}'")
        if len(move_str) >= 4:
            try:
                from_alg = move_str[:2]
                to_alg = move_str[2:4]
                promotion = move_str[4] if len(move_str) == 5 else None
                
                from_pos = self._algebraic_to_pos(from_alg)
                to_pos = self._algebraic_to_pos(to_alg)
                
                print(f"DEBUG: Parsed move: {from_pos} -> {to_pos}, promotion: {promotion}")
                return (from_pos, to_pos, promotion)
                
            except Exception as e:
                print(f"DEBUG: Failed to parse move: {e}")
                return None
        
        print(f"DEBUG: Move string too short: {len(move_str)}")
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