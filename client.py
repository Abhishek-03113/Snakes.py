# client_basic.py
import socket
import threading
import json
import os
import time
import sys


class GameClient:
    def __init__(self, host="localhost", port=5555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.game_state = None
        self.player_name = ""
        self.running = True
        self.lock = threading.Lock()

    def connect(self):
        try:
            self.client.connect((self.host, self.port))
            return True
        except:
            print("Could not connect to server")
            return False

    def send_name(self, name):
        self.player_name = name
        self.client.send(name.encode("utf-8"))

    def receive_game_state(self):
        while self.running:
            try:
                data = self.client.recv(4096).decode("utf-8")
                if not data:
                    print("Server closed the connection.")
                    self.running = False
                    break

                with self.lock:
                    self.game_state = json.loads(data)

            except (json.JSONDecodeError, UnicodeDecodeError):
                print("Received malformed data. Ignoring...")
            except ConnectionResetError:
                print("Connection reset by server.")
                self.running = False
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
                self.running = False
                break
        self.close()  # Ensure socket is closed when exiting

    def send_input(self, direction):
        try:
            self.client.send(direction.encode("utf-8"))
        except:
            self.running = False

    def find_player(self):
        if not self.game_state:
            return None

        for player in self.game_state["players"]:
            if player["name"] == self.player_name:
                return player

        return None

    def display_game(self):
        os.system("cls" if os.name == "nt" else "clear")

        if not self.game_state:
            print("Waiting for game state...")
            return

        required_keys = ["players", "width", "height", "foods"]
        if not all(key in self.game_state for key in required_keys):
            print("Invalid game state received.")
            return

        width = self.game_state["width"]
        height = self.game_state["height"]

        # Create empty board
        board = [[" " for _ in range(width)] for _ in range(height)]

        # Draw border
        for i in range(width):
            board[0][i] = "#"
            board[height - 1][i] = "#"
        for i in range(height):
            board[i][0] = "#"
            board[i][width - 1] = "#"

        # Draw food
        for food in self.game_state["foods"]:
            x, y = food.get(
                "pos", (-1, -1)
            )  # Default to an invalid position if key is missing
            if 0 <= x < width and 0 <= y < height:
                board[y][x] = "*"

        # Draw snakes
        for player in self.game_state["players"]:
            if (
                not isinstance(player, dict)
                or "alive" not in player
                or "body" not in player
            ):
                continue  # Skip malformed player data

            if player["alive"]:
                for i, (x, y) in enumerate(player["body"]):
                    if 0 <= x < width and 0 <= y < height:
                        if i == 0:
                            board[y][x] = player["name"][0].upper()
                        else:
                            board[y][x] = "o"

        # Print the board
        for row in board:
            print("".join(row))

        # Print scoreboard
        print("\nSCOREBOARD")
        print("-----------")

        # Sort players by score
        sorted_players = sorted(
            self.game_state["players"], key=lambda p: p["score"], reverse=True
        )

        for player in sorted_players:
            status = "ALIVE" if player["alive"] else "DEAD"
            name_display = player["name"]
            if player["name"] == self.player_name:
                name_display = f"{name_display} (YOU)"

            print(f"{name_display}: {player['score']} - {status}")

        # Print instructions
        print("\nControls:")
        print("w: Up")
        print("s: Down")
        print("a: Left")
        print("d: Right")
        print("q: Quit")
        print("\nEnter your move: ", end="", flush=True)

    def run_game(self):
        # Start receiving game state in a separate thread
        receive_thread = threading.Thread(target=self.receive_game_state)
        receive_thread.daemon = True
        receive_thread.start()

        # Let the server send initial game state
        time.sleep(0.5)

        # Display thread
        def display_loop():
            while self.running:
                with self.lock:
                    self.display_game()
                time.sleep(0.2)

        # Start display thread
        display_thread = threading.Thread(target=display_loop)
        display_thread.daemon = True
        display_thread.start()

        # Main input loop - simple blocking input
        while self.running:
            try:
                key = input("\nEnter move (w/a/s/d/q): ").strip().lower()

                if key == "q":
                    print("Quitting the game...")
                    self.running = False
                    break
                elif key in ["w", "a", "s", "d"]:
                    self.send_input(key)
                    with self.lock:
                        self.display_game()
                else:
                    print(
                        "Invalid input! Use 'w', 'a', 's', 'd' to move or 'q' to quit."
                    )
            except KeyboardInterrupt:
                print("Game interrupted.")
                self.running = False
                break
            except Exception as e:
                print(f"Error: {e}")

    def close(self):
        self.client.close()


def main():
    # Clear the terminal
    os.system("cls" if os.name == "nt" else "clear")

    # Get server info
    host = input("Enter server IP (or press Enter for localhost): ")
    if not host:
        host = "localhost"

    port = input("Enter server port (or press Enter for default 5555): ")
    if not port:
        port = 5555
    else:
        port = int(port)

    # Get player name
    name = ""
    while not name:
        name = input("Enter your name: ")

    # Connect to server
    client = GameClient(host, port)
    if not client.connect():
        print("Failed to connect to server. Make sure the server is running.")
        return

    # Send player name
    client.send_name(name)

    # Start the game
    try:
        client.run_game()
    except KeyboardInterrupt:
        pass
    finally:
        client.close()


if __name__ == "__main__":
    main()
