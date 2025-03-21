import socket
import threading
import random
import time
import json
import os
import socks

WIDTH = 60
HEIGHT = 20
MAX_FOOD = 5

TICK_RATE = 0.1


class GameServer:
    def __init__(self, host="localhost", port=8080):

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(5)

        self.players = {}
        self.food = []
        self.lock = threading.Lock()

        print(f"Server started on {host}:{port}")

        self.generate_food()
        threading.Thread(target=self.game_loop, daemon=True).start()

    def generate_food(self):
        with self.lock:
            while len(self.food) < MAX_FOOD:
                x = random.randint(0, WIDTH - 1)
                y = random.randint(0, HEIGHT - 1)
                if (x, y) not in [food["pos"] for food in self.food]:
                    self.food.append({"pos": (x, y), "value": random.randint(1, 3)})

    def handle_client(self, conn, addr):
        try:
            name_data = conn.recv(1024).decode("utf-8")
            name = name_data.strip()

            if not name or len(name) == 0:
                conn.close()
                return

            with self.lock:
                while True:
                    x = random.randint(5, WIDTH - 5)
                    y = random.randint(5, HEIGHT - 5)
                    collision = False

                    for player in self.players.values():
                        if player["pos"] == (x, y):
                            collision = True
                            break

                    if not collision:
                        break

                direction = random.randint(0, 3)

                self.player[conn] = {
                    "name": name,
                    "body": [(x, y)],
                    "direction": direction,
                    "score": 0,
                    "alive": True,
                }

                print(f"New player connected: {name} from {addr}")

                self.send_game_state(conn)

                while True:
                    try:
                        data = conn.recv(1024).decode("utf-8")
                        if not data:
                            break

                        with self.lock:
                            player = self.players.get(conn)
                            if player and player["alive"]:
                                current_dir = player["direction"]

                                if data == "w" and current_dir != 1:
                                    player["direction"] = 3
                                if data == "s" and current_dir != 3:
                                    player["direction"] = 1
                                if data == "a" and current_dir != 0:
                                    player["direction"] = 2
                                if data == "d" and current_dir != 2:
                                    player["direction"] = 0

                    except:
                        break
        finally:
            with self.lock:
                if conn in self.players:
                    print(f'Player {self.players[conn]["name"]} disconnected')
                    del self.players[conn]
            conn.close()

    def send_game_state(self, conn=None):
        with self.lock:
            game_state = {
                "width": WIDTH,
                "height": HEIGHT,
                "players": [],
                "food": self.food,
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
                    conn.send(state_json.encode("utf-8"))
                except:
                    pass
            else:
                for player_conn in self.players.keys():
                    try:
                        player_conn.send(state_json.encode("utf-8"))
                    except:
                        continue

    def move_snake(self):
        with self.lock:
            for conn, player in list(self.players.items()):
                if not player["alive"]:
                    continue

                head = player["body"][0]
                direction = player["direction"]

                if direction == 0:
                    new_head = (head[0] + 1, head[1])
                elif direction == 1:
                    new_head = (head[0], head[1] + 1)
                elif direction == 2:
                    new_head = (head[0] - 1, head[1])
                elif direction == 3:
                    new_head = (head[0], head[1] - 1)

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
