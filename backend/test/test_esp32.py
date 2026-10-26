import websockets
import random
import dotenv
import asyncio
import json

dotenv.load_dotenv()

DEVICE_ID = "esp32-plant-device"
# uri = f"ws://{os.getenv('HOST')}/ws/smart-hydroponic/device"
uri = "ws://localhost:8000/smart-hydroponic/api/v2/hydroponics/ws/sensor-data"


def data_plant():
    return {
        "moisture1": 60,
        "moisture2": 70,
        "moisture3": 80,
        "moisture4": 100,
        "moisture5": 40,
        "moisture6": 50,
        "flowrate": random.randint(1, 100),
        "total_litres": random.randint(1, 100),
        "distance_cm": random.randint(1, 100),
    }


async def send_pong(websocket):
    while True:
        try:
            await asyncio.sleep(5)  # Wait for 5 seconds before sending pong
            await websocket.send("pong")
            print("Sent pong")
        except websockets.exceptions.ConnectionClosedError:
            print("Connection closed, stopping pong sender.")
            break


async def main():
    while True:
        try:
            ws = websockets.connect(uri)
            async with ws as websocket:
                # register_data = {
                #     "deviceId": DEVICE_ID,
                #     "type": "join",
                #     "room": "plant",
                # }
                # await websocket.send(json.dumps(register_data))
                # print(f"Sent register data: {register_data}")
                while True:
                    data = data_plant()
                    json_data = json.dumps(data)
                    await websocket.send(json_data)
                    print(f"Sent data: {json_data}\n")
                    await asyncio.sleep(
                        5
                    )  # Delay of 5 seconds before sending the next data
        except (
            websockets.exceptions.ConnectionClosedError,
            ConnectionRefusedError,
        ) as e:
            print(f"Connection error: {e}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
