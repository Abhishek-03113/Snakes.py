# server_debug.py
import socket
import threading
import random
import time
import json

# Game settings
WIDTH = 60
HEIGHT = 20
MAX_FOODS = 5
TICK_RATE = 0.1  # seconds between game updates


class GameServer:
    def __init__(self, host="0.0.0.0", port=5555):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind((host, port))
        except socket.error as e:
            print(f"Socket binding error: {e}")
            exit()

        self.server.listen(5)

        self.players = {}  # {conn: player_data}
        self.foods = []
        self.lock = threading.Lock()

        print(f"Server started on {host}:{port}")

        # Initialize food
        self.generate_foods()

        # Start game loop
        self.game_thread = threading.Thread(target=self.game_loop, daemon=True)
        self.game_thread.start()
        print("Game loop started")

    def generate_foods(self):
        with self.lock:
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
            print(f"Foods generated: {len(self.foods)}")

    def handle_client(self, conn, addr):
        print(f"New connection from {addr}")

        try:
            print(f"Waiting for name from {addr}")
            name_data = conn.recv(1024).decode("utf-8")
            if not name_data:
                print(f"No name received from {addr}")
                conn.close()
                return

            name = name_data.strip()
            print(f"Name received from {addr}: {name}")

            if not name or len(name) == 0:
                print(f"Invalid name from {addr}")
                conn.close()
                return

            # Initialize player
            with self.lock:
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

                direction = random.randint(0, 3)
                self.players[conn] = {
                    "name": name,
                    "body": [(x, y)],
                    "direction": direction,
                    "score": 0,
                    "alive": True,
                }

            print(f"Player initialized: {name} from {addr}")

            # **DEBUG CHECKPOINT**
            print(f"About to send game state to {name}...")
            self.send_game_state(conn)
            print(f"Game state sent successfully to {name}")

            while True:
                try:
                    data = conn.recv(1024).decode("utf-8")
                    if not data:
                        print(f"Connection closed for {name}")
                        break
                    print(f"Received input from {name}: {data}")
                except Exception as e:
                    print(f"Error handling input from {name}: {e}")
                    break
        finally:
            with self.lock:
                if conn in self.players:
                    print(f"Player disconnected: {self.players[conn]['name']}")
                    del self.players[conn]
            conn.close()

    def send_game_state(self, conn=None):
        with self.lock:
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

            if conn:
                try:
                    conn.sendall(state_json.encode("utf-8"))  # Use sendall()
                    print(f"Sent game state to {self.players[conn]['name']}")
                except Exception as e:
                    print(f"Error sending game state to specific client: {e}")
            else:
                for player_conn in list(self.players.keys()):
                    try:
                        player_conn.sendall(state_json.encode("utf-8"))  # Use sendall()
                    except Exception as e:
                        print(
                            f"Error sending game state to {self.players[player_conn]['name']}: {e}"
                        )
                        continue
                print("Game state broadcasted to all players")

    def move_snakes(self):
        with self.lock:
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
                    print(f"Player {player['name']} hit wall")
                    continue

                # Check collision with self
                if new_head in player["body"]:
                    player["alive"] = False
                    print(f"Player {player['name']} hit self")
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
                                print(
                                    f"Player {player['name']} hit larger snake {other_player['name']}"
                                )
                                collision = True
                                break
                            else:
                                other_player["alive"] = False
                                player["score"] += len(other_player["body"])
                                print(
                                    f"Player {player['name']} destroyed smaller snake {other_player['name']}"
                                )

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
                        print(f"Player {player['name']} ate food")
                        break

                if not ate_food:
                    # Remove tail if no food was eaten
                    player["body"].pop()

            # Generate new food if needed
            self.generate_foods()

    def game_loop(self):
        while True:
            try:
                print("Game loop running...")
                self.move_snakes()
                self.send_game_state()
                time.sleep(TICK_RATE)
            except Exception as e:
                print(f"Error in game loop: {e}")

    def start(self):
        try:
            while True:
                conn, addr = self.server.accept()
                print(f"Connected with {addr}")
                thread = threading.Thread(target=self.handle_client, args=(conn, addr))
                thread.daemon = True
                thread.start()
                print(f"Active connections: {threading.active_count() - 1}")
        except KeyboardInterrupt:
            print("Server shutting down...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            if self.server:
                self.server.close()
                print("Server socket closed")


if __name__ == "__main__":
    server = GameServer()
    server.start()
