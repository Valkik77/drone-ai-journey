import pybullet as p
import pybullet_data
import time

def direction_to_force(direction_list, horizontal_force=5.0):
    fx, fy = 0, 0
    if "RIGHT" in direction_list:
        fx += horizontal_force
    if "LEFT" in direction_list:
        fx -= horizontal_force
    if "UP" in direction_list:
        fy += horizontal_force
    if "DOWN" in direction_list:
        fy -= horizontal_force
    return fx, fy

def get_direction(diff_x, diff_y, threshold=30):
    commands = []
    if abs(diff_x) > threshold:
        commands.append("RIGHT" if diff_x > 0 else "LEFT")
    if abs(diff_y) > threshold:
        commands.append("DOWN" if diff_y > 0 else "UP")
    if not commands:
        commands.append("STAY")
    return commands

physicsClient = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
planeId = p.loadURDF("plane.urdf")
droneId = p.loadURDF("sphere2.urdf", [0, 0, 1], p.getQuaternionFromEuler([0, 0, 0]))
mass = p.getDynamicsInfo(droneId, -1)[0]
hover_force = mass * 9.8

x_positions, y_positions, z_positions = [], [], []

# 用意:模擬「假的YOLO輸入」,每隔一段時間切換不同的偏移量,
#      測試整個串接架構(輸入變化→方向判斷→施力→模擬反應)是否正確運作
fake_diff_sequence = [
    (50, -40),   # 前段:右上
    (-60, 30),   # 中段:左下
    (10, 10),    # 後段:接近中心,應該接近STAY
]

steps_per_phase = 700

for i in range(2000):
    phase = min(i // steps_per_phase, len(fake_diff_sequence) - 1)
    diff_x, diff_y = fake_diff_sequence[phase]
    # 用意:根據目前的模擬步數,決定現在該用哪一組假的偏移量測試

    direction = get_direction(diff_x, diff_y)
    fx, fy = direction_to_force(direction)

    p.applyExternalForce(droneId, -1, [fx, fy, hover_force], [0, 0, 0], p.WORLD_FRAME)
    p.stepSimulation()

    pos, orn = p.getBasePositionAndOrientation(droneId)
    x_positions.append(pos[0])
    y_positions.append(pos[1])
    z_positions.append(pos[2])

p.disconnect()
print(f"最終位置: x={x_positions[-1]:.2f}, y={y_positions[-1]:.2f}, z={z_positions[-1]:.2f}", flush=True)

import matplotlib.pyplot as plt
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))
ax1.plot(x_positions); ax1.set_title("X Position"); ax1.set_xlabel("Step")
ax2.plot(y_positions); ax2.set_title("Y Position"); ax2.set_xlabel("Step")
ax3.plot(z_positions); ax3.set_title("Z Height"); ax3.set_xlabel("Step")
plt.tight_layout()
plt.savefig("day17_phase_test.png")
print("圖表已存成 day17_phase_test.png", flush=True)