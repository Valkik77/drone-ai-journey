import asyncio
import json
import socket
import time

import pybullet as p
import pybullet_data
import websockets

HOST = "0.0.0.0"
PORT = 8765
HORIZONTAL_FORCE = 45.0  # 提高一點,抵銷下面阻尼帶來的減速,實際移動幅度才感覺得出來
DRAG_COEFFICIENT = 30.0  # 水平方向阻尼(模擬空氣阻力/飛控主動煞車):放開搖桿後速度約1-2秒內衰減到接近0,不會無限漂移
FAILSAFE_TIMEOUT = 0.5  # 秒:超過這麼久沒收到搖桿訊息就歸零施力,避免斷線後持續漂移
SIM_DT = 1 / 50
TELEMETRY_INTERVAL = 1 / 15

# ---------- 目前搖桿狀態(所有連線共用同一台模擬無人機) ----------
joystick_state = {"x": 0.0, "y": 0.0, "last_update": 0.0}


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def init_simulation():
    physics_client = p.connect(p.DIRECT)
    p.setAdditionalSearchPath(pybullet_data.getDataPath())
    p.setTimeStep(SIM_DT)  # 沒設的話stepSimulation()預設固定用1/240s,跟迴圈的實際節奏(SIM_DT)對不上,模擬就會用「慢動作」在跑
    p.setGravity(0, 0, -9.8)
    p.loadURDF("plane.urdf")
    drone_id = p.loadURDF("sphere2.urdf", [0, 0, 1], p.getQuaternionFromEuler([0, 0, 0]))
    mass = p.getDynamicsInfo(drone_id, -1)[0]
    hover_force = mass * 9.8
    return physics_client, drone_id, hover_force


async def sim_loop(drone_id, hover_force, get_telemetry_ref):
    while True:
        now = time.time()
        if now - joystick_state["last_update"] > FAILSAFE_TIMEOUT:
            input_x, input_y = 0.0, 0.0
        else:
            input_x = joystick_state["x"]
            input_y = joystick_state["y"]

        (vx, vy, _), _ = p.getBaseVelocity(drone_id)
        fx = input_x * HORIZONTAL_FORCE - DRAG_COEFFICIENT * vx
        fy = input_y * HORIZONTAL_FORCE - DRAG_COEFFICIENT * vy

        p.applyExternalForce(drone_id, -1, [fx, fy, hover_force], [0, 0, 0], p.WORLD_FRAME)
        p.stepSimulation()

        pos, _ = p.getBasePositionAndOrientation(drone_id)
        get_telemetry_ref["x"] = pos[0]
        get_telemetry_ref["y"] = pos[1]
        get_telemetry_ref["z"] = pos[2]
        get_telemetry_ref["fx"] = fx
        get_telemetry_ref["fy"] = fy

        await asyncio.sleep(SIM_DT)


async def receive_control(websocket):
    async for message in websocket:
        try:
            data = json.loads(message)
            joystick_state["x"] = max(-1.0, min(1.0, float(data["x"])))
            joystick_state["y"] = max(-1.0, min(1.0, float(data["y"])))
            joystick_state["last_update"] = time.time()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            continue


async def send_telemetry(websocket, telemetry):
    while True:
        await websocket.send(json.dumps(telemetry))
        await asyncio.sleep(TELEMETRY_INTERVAL)


async def handle_client(websocket):
    print(f"手機已連線: {websocket.remote_address}", flush=True)
    try:
        await asyncio.gather(
            receive_control(websocket),
            send_telemetry(websocket, telemetry),
        )
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        joystick_state["x"] = 0.0
        joystick_state["y"] = 0.0
        print(f"手機已斷線: {websocket.remote_address}", flush=True)


async def main():
    _, drone_id, hover_force = init_simulation()
    asyncio.create_task(sim_loop(drone_id, hover_force, telemetry))

    local_ip = get_local_ip()
    print(f"伺服器啟動,手機App請連線到: ws://{local_ip}:{PORT}", flush=True)
    print(f"同一台電腦測試可用: ws://127.0.0.1:{PORT}", flush=True)

    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # 永久執行,直到Ctrl+C


telemetry = {"x": 0.0, "y": 0.0, "z": 0.0, "fx": 0.0, "fy": 0.0}

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n伺服器已停止", flush=True)
