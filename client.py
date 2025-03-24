# client.py
import socket
import threading
import json
import os
import time
import sys
import curses
from curses import wrapper


class GameClient:
    def __init__(self, host="localhost", port=5555):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = port
        self.game_state = None
        self.player_name = ""
        self.running = True

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
                    break

                self.game_state = json.loads(data)

            except:
                print("Connection lost")
                self.running = False
                break

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

    def run_game(self, stdscr):
        # Set up curses
        curses.curs_set(0)  # Hide cursor
        stdscr.clear()

        # Colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Food
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)  # Other snakes
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)  # Player snake
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Border
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Text

        # Start receiving game state in a separate thread
        receive_thread = threading.Thread(target=self.receive_game_state)
        receive_thread.daemon = True
        receive_thread.start()

        # Game loop
        stdscr.nodelay(True)  # Non-blocking input
        while self.running:
            try:
                # Handle input
                key = stdscr.getch()
                if key != -1:
                    if key == ord("q"):
                        self.running = False
                        break
                    elif key == ord("w") or key == curses.KEY_UP:
                        self.send_input("w")
                    elif key == ord("s") or key == curses.KEY_DOWN:
                        self.send_input("s")
                    elif key == ord("a") or key == curses.KEY_LEFT:
                        self.send_input("a")
                    elif key == ord("d") or key == curses.KEY_RIGHT:
                        self.send_input("d")

                # Render game state
                game_state = self.game_state
                if not game_state:
                    time.sleep(0.1)
                    continue

                stdscr.clear()

                # Draw border
                width = game_state["width"]
                height = game_state["height"]
                for i in range(width):
                    stdscr.addch(0, i, "#", curses.color_pair(4))
                    stdscr.addch(height - 1, i, "#", curses.color_pair(4))
                for i in range(height):
                    stdscr.addch(i, 0, "#", curses.color_pair(4))
                    stdscr.addch(i, width - 1, "#", curses.color_pair(4))

                # Draw food
                for food in game_state["foods"]:
                    x, y = food["pos"]
                    stdscr.addch(y, x, "*", curses.color_pair(1))

                # Draw snakes
                player_self = self.find_player()
                for player in game_state["players"]:
                    if player["alive"]:
                        is_self = player["name"] == self.player_name
                        color = (
                            curses.color_pair(3) if is_self else curses.color_pair(2)
                        )

                        # Draw body
                        for i, (x, y) in enumerate(player["body"]):
                            if i == 0:  # Head
                                # Use first letter of player's name as head
                                stdscr.addch(y, x, player["name"][0].upper(), color)
                            else:  # Body
                                stdscr.addch(y, x, "o", color)

                # Draw scoreboard
                y_pos = 1
                stdscr.addstr(y_pos, width + 2, "SCOREBOARD", curses.color_pair(5))
                y_pos += 2

                # Sort players by score
                sorted_players = sorted(
                    game_state["players"], key=lambda p: p["score"], reverse=True
                )

                for player in sorted_players:
                    status = "ALIVE" if player["alive"] else "DEAD"
                    name_display = player["name"]
                    if player["name"] == self.player_name:
                        name_display = f"{name_display} (YOU)"

                    stdscr.addstr(
                        y_pos,
                        width + 2,
                        f"{name_display}: {player['score']} - {status}",
                        curses.color_pair(5),
                    )
                    y_pos += 1

                # Draw instructions
                y_pos += 2
                stdscr.addstr(y_pos, width + 2, "Controls:", curses.color_pair(5))
                y_pos += 1
                stdscr.addstr(y_pos, width + 2, "W/↑: Up", curses.color_pair(5))
                y_pos += 1
                stdscr.addstr(y_pos, width + 2, "S/↓: Down", curses.color_pair(5))
                y_pos += 1
                stdscr.addstr(y_pos, width + 2, "A/←: Left", curses.color_pair(5))
                y_pos += 1
                stdscr.addstr(y_pos, width + 2, "D/→: Right", curses.color_pair(5))
                y_pos += 1
                stdscr.addstr(y_pos, width + 2, "Q: Quit", curses.color_pair(5))

                stdscr.refresh()

                time.sleep(0.05)

            except Exception as e:
                self.running = False
                break

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

    # Start the game with curses
    try:
        wrapper(client.run_game)
    finally:
        client.close()


if __name__ == "__main__":
    main()
