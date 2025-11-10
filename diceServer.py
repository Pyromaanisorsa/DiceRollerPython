import asyncio
import json
import socket
import sys
from godice_manager import GoDiceManager

# Connection parameters & GoDiceManager instance
HOST = "127.0.0.1"
PORT = 5005
manager = GoDiceManager()

# Send JSON message to Unity
def send_to_unity(client, message_dict):
    try:
        message = json.dumps(message_dict).encode()
        client.sendall(message + b"\n")
    except:
        print("Failed to send message to Unity.")

# Async event to start server shutdown
shutdown_event = asyncio.Event()

# Client logic code; wait for messages from Unity and react
async def handle_client(client_socket):
    loop = asyncio.get_running_loop()

    # Set callback function for GoDiceManager so that it can send messages to Unity via server
    def dice_callback(msg):
        send_to_unity(client_socket, msg)

    # Register callback to GoDiceManager
    manager.set_dice_callback(dice_callback)

    while True:
        try:
            # Wait for message from Unity
            data = await loop.sock_recv(client_socket, 1024)
            if not data:
                break
            
            # Parse JSON message
            command = json.loads(data.decode().strip())
            print(command)

            # Try to connect dice to GoDiceManager and send result to Unity
            if command["type"] == "connect":
                result = await manager.connect_dice()
                success = result["success"]
                name = result["message"]
                print(f"{success} | {name}")
                send_to_unity(client_socket, {"type": "connect", "success": success, "message": name})

            # Disconnect current connected dice
            elif command["type"] == "disconnect":
                await manager.disconnect_dice()
                send_to_unity(client_socket, {"type": "disconnect"})

            # Shutdown the server
            elif command["type"] == "shutdown":
                print("Shutdown command received.")
                #send_to_unity(client_socket, {"type": "shutting down"})
                shutdown_event.set()
                break
            
            # Testing purposes
            else:
                send_to_unity(client_socket, {"type": "error", "message": "Unknown command."})

        except Exception as e:
            print(f"Client connection error: {e}")
            break

# Connetion logic; bind to localhost and port, start listerning to connections and set non-blocking for asynchio
async def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    server_socket.setblocking(False)

    print(f"[] Server listening on {HOST}:{PORT}")
    loop = asyncio.get_running_loop()

    # Listen to Unity connections periodically in a loop
    async def accept_loop():
        while not shutdown_event.is_set():
            try:
                client, addr = await asyncio.wait_for(loop.sock_accept(server_socket), timeout=1.0)
                print(f"[+] Accepted Unity connection from {addr}.")
                asyncio.create_task(handle_client(client))
            except asyncio.TimeoutError:
                continue

    # Run accept loop in background
    accept_task = asyncio.create_task(accept_loop())

    # Wait for shutdown signal
    await shutdown_event.wait()
    print("Server shutting down.")

    # Cancel accept loop and close socket
    accept_task.cancel()
    server_socket.close()
    await asyncio.sleep(0.1)
    sys.exit(0)

# Start entire script
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error {e}")
        input("Press to exit")