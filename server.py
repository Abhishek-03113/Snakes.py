# server.py
import socket
import threading
import random
import time
import json

# Game settings
WIDTH = 100
HEIGHT = 40
MAX_FOODS = 5
TICK_RATE = 0.1  # seconds between game updates


class GameServer:
    def __init__(self, host="0.0.0.0", port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()

        self.players = {}  # {conn: player_data}
        self.foods = []

        print(f"Server started on {host}:{port}")

        # Initialize food
        self.generate_foods()

        # Start game loop
        threading.Thread(target=self.game_loop, daemon=True).start()

    def generate_foods(self):
        while len(self.foods) < MAX_FOODS:
            x = random.randint(1, WIDTH - 2)
            y = random.randint(1, HEIGHT - 2)

            # Check if position is already occupied
            if (x, y) not in [food["pos"] for food in self.foods]:
                self.foods.append(
                    {
                        "pos": (x, y),
                        "value": random.randint(
                            1, 3
                        ),  # Food value (length added when eaten)
                    }
                )

    def handle_client(self, conn, addr):
        try:
            # Get player name
            name_data = conn.recv(1024).decode("utf-8")
            name = name_data.strip()

            if not name or len(name) == 0:
                conn.close()
                return

            # Initialize player
            # Find a free spot for the new snake
            while True:
                x = random.randint(5, WIDTH - 5)
                y = random.randint(5, HEIGHT - 5)
                collision = False

                for player in self.players.values():
                    if (x, y) in player["body"]:
                        collision = True
                        break

                if not collision:
                    break

            # Initial direction (0: right, 1: down, 2: left, 3: up)
            direction = random.randint(0, 3)

            self.players[conn] = {
                "name": name,
                "body": [(x, y)],  # Head is at index 0
                "direction": direction,
                "score": 0,
                "alive": True,
            }

            print(f"New player connected: {name} from {addr}")

            # Send initial game state
            self.send_game_state(conn)

            # Handle player input
            while True:
                try:
                    data = conn.recv(1024).decode("utf-8")
                    if not data:
                        break

                    player = self.players.get(conn)
                    if player and player["alive"]:
                        current_dir = player["direction"]

                        if data == "w" and current_dir != 1:  # Up
                            player["direction"] = 3
                        elif data == "s" and current_dir != 3:  # Down
                            player["direction"] = 1
                        elif data == "a" and current_dir != 0:  # Left
                            player["direction"] = 2
                        elif data == "d" and current_dir != 2:  # Right
                            player["direction"] = 0

                except:
                    break

        finally:
            if conn in self.players:
                print(f"Player disconnected: {self.players[conn]['name']}")
                del self.players[conn]

            conn.close()

    def send_game_state(self, conn=None):
        game_state = {
            "width": WIDTH,
            "height": HEIGHT,
            "players": [],
            "foods": self.foods,
        }

        for player_conn, player_data in self.players.items():
            game_state["players"].append(
                {
                    "name": player_data["name"],
                    "body": player_data["body"],
                    "score": player_data["score"],
                    "alive": player_data["alive"],
                }
            )

        state_json = json.dumps(game_state)

        if conn:  # Send to specific client
            try:
                conn.send(state_json.encode("utf-8"))
            except:
                pass
        else:  # Send to all clients
            for player_conn in list(self.players.keys()):
                try:
                    player_conn.send(state_json.encode("utf-8"))
                except:
                    continue

    def move_snakes(self):
        for conn, player in list(self.players.items()):
            if not player["alive"]:
                continue

            head = player["body"][0]
            direction = player["direction"]

            # Calculate new head position
            if direction == 0:  # Right
                new_head = (head[0] + 1, head[1])
            elif direction == 1:  # Down
                new_head = (head[0], head[1] + 1)
            elif direction == 2:  # Left
                new_head = (head[0] - 1, head[1])
            elif direction == 3:  # Up
                new_head = (head[0], head[1] - 1)

            # Check wall collision
            if (
                new_head[0] <= 0
                or new_head[0] >= WIDTH - 1
                or new_head[1] <= 0
                or new_head[1] >= HEIGHT - 1
            ):
                player["alive"] = False
                continue

            # Check collision with self
            if new_head in player["body"]:
                player["alive"] = False
                continue

            # Check collision with other snakes
            collision = False
            for other_conn, other_player in self.players.items():
                if conn != other_conn and other_player["alive"]:
                    if new_head in other_player["body"]:
                        # Compare lengths to determine which snake dies
                        if len(player["body"]) <= len(other_player["body"]):
                            player["alive"] = False
                            other_player["score"] += len(player["body"])
                            collision = True
                            break
                        else:
                            other_player["alive"] = False
                            player["score"] += len(other_player["body"])

            if collision:
                continue

            # Move the snake (add new head)
            player["body"].insert(0, new_head)

            # Check food collision
            ate_food = False
            for i, food in enumerate(self.foods):
                if new_head == food["pos"]:
                    player["score"] += food["value"]
                    # Don't remove tail when food is eaten
                    ate_food = True
                    del self.foods[i]
                    break

            if not ate_food:
                # Remove tail if no food was eaten
                player["body"].pop()

        # Generate new food if needed
        self.generate_foods()

    def game_loop(self):
        while True:
            self.move_snakes()
            self.send_game_state()
            time.sleep(TICK_RATE)

    def start(self):
        try:
            while True:
                conn, addr = self.server.accept()
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            if self.server:
                self.server.close()


if __name__ == "__main__":
    server = GameServer()
    server.start()
