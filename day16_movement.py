import pybullet as p
import pybullet_data
import matplotlib.pyplot as plt

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

diff_x, diff_y = 50, -40
direction = get_direction(diff_x, diff_y)
print(f"方向判斷結果: {direction}", flush=True)

fx, fy = direction_to_force(direction)
print(f"轉換後的施力: fx={fx}, fy={fy}", flush=True)

physicsClient = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
planeId = p.loadURDF("plane.urdf")

droneStartPos = [0, 0, 1]
droneStartOrientation = p.getQuaternionFromEuler([0, 0, 0])
droneId = p.loadURDF("sphere2.urdf", droneStartPos, droneStartOrientation)

mass = p.getDynamicsInfo(droneId, -1)[0]
hover_force = mass * 9.8

x_positions = []
y_positions = []
z_positions = []

for i in range(2000):
    p.applyExternalForce(droneId, -1, [fx, fy, hover_force], [0, 0, 0], p.WORLD_FRAME)
    p.stepSimulation()

    pos, orn = p.getBasePositionAndOrientation(droneId)
    x_positions.append(pos[0])
    y_positions.append(pos[1])
    z_positions.append(pos[2])

p.disconnect()

print(f"起始x位置: {x_positions[0]:.3f}, 最終x位置: {x_positions[-1]:.3f}", flush=True)
print(f"起始y位置: {y_positions[0]:.3f}, 最終y位置: {y_positions[-1]:.3f}", flush=True)
print(f"起始高度: {z_positions[0]:.3f}, 最終高度: {z_positions[-1]:.3f}", flush=True)

fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14, 4))
ax1.plot(x_positions)
ax1.set_xlabel("Simulation Step")
ax1.set_ylabel("X Position (m)")
ax1.set_title("X Movement (Right/Left)")

ax2.plot(y_positions)
ax2.set_xlabel("Simulation Step")
ax2.set_ylabel("Y Position (m)")
ax2.set_title("Y Movement (Up/Down)")

ax3.plot(z_positions)
ax3.set_xlabel("Simulation Step")
ax3.set_ylabel("Height (m)")
ax3.set_title("Height Stability")

plt.tight_layout()
plt.savefig("day16_movement_result.png")
print("圖表已存成 day16_movement_result.png", flush=True)

fig2 = plt.figure(figsize=(8, 6))
ax2_3d = fig2.add_subplot(111, projection='3d')

skip = 20
indices = list(range(0, len(x_positions), skip))
xs = [x_positions[i] for i in indices]
ys = [y_positions[i] for i in indices]
zs = [z_positions[i] for i in indices]
colors = range(len(indices))

scatter = ax2_3d.scatter(xs, ys, zs, c=colors, cmap='viridis', s=30)
ax2_3d.plot(xs, ys, zs, 'gray', alpha=0.3)

ax2_3d.set_xlabel("X")
ax2_3d.set_ylabel("Y")
ax2_3d.set_zlabel("Z (Height)")
ax2_3d.set_title("Drone Simulation Trajectory (color = time)")
fig2.colorbar(scatter, label="Simulation Step (later = brighter)")

ax2_3d.view_init(elev=15, azim=-60)

plt.savefig("day16_trajectory_static.png", dpi=150)
print("軌跡圖已存成 day16_trajectory_static.png", flush=True)