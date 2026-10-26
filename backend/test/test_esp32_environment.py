import websockets
import random
import dotenv
import asyncio
import json

dotenv.load_dotenv()

DEVICE_ID = "esp32-environment-device"
uri = "ws://localhost:8000/smart-hydroponic/api/v2/hydroponics/ws/environment-data"


def data_environment():
    return {
        "temperature_atas": random.randint(1, 100),
        "temperature_bawah": random.randint(1, 100),
        "humidity_atas": random.randint(1, 100),
        "humidity_bawah": random.randint(1, 100),
        "light_intensity_atas": random.randint(100, 1000),
        "light_intensity_bawah": random.randint(100, 1000),
        "ph": random.uniform(5.0, 7.0),
        "tds": random.randint(100, 1000),
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
                #     "room": "environment",
                # }
                # await websocket.send(json.dumps(register_data))
                # print(f"Sent register data: {register_data}")
                while True:
                    data = data_environment()
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
