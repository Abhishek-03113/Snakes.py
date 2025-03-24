# Snakes Multiplayer Game

### Fixes Required

    - Custom Game Rooms
    - A lobby where players wait till other players join in
    - a start menu so that game dont begin when you join the server
    - Find possible race condtions and deadlocks

## Table of Contents

- [About](#about)
- [Getting Started](#getting_started)
- [Usage](#usage)
- [Contributing](../CONTRIBUTING.md)

## About <a name = "about"></a>

Snakes is a multiplayer game where players control snakes on a grid, trying to eat food to grow longer while avoiding collisions with walls, themselves, and other snakes. The game is implemented using Python and uses sockets for network communication between the server and clients.

## Getting Started <a name = "getting_started"></a>

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See [deployment](#deployment) for notes on how to deploy the project on a live system.

### Prerequisites

You need to have Python installed on your machine. You can download it from [python.org](https://www.python.org/).

### Installing

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/snakes.git
   cd snakes
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

### Running the Server

To start the game server, run the following command:

```
python server.py
```

### Running the Client

To start the game client, run the following command:

```
python client.py
```

You will be prompted to enter the server IP and port, as well as your player name.

## Usage <a name = "usage"></a>

Once the client is connected to the server, use the following controls to play the game:

- `W` or `↑`: Move up
- `S` or `↓`: Move down
- `A` or `←`: Move left
- `D` or `→`: Move right
- `Q`: Quit the game

The objective is to eat the food (represented by `*`) to grow your snake and increase your score. Avoid colliding with walls, yourself, and other snakes.

Enjoy the game!
