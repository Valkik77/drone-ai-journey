import pybullet as p
import pybullet_data
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation


def direction_to_force(direction_list, horizontal_force=5.0):
    fx, fy = 0, 0
    # 用意:把方向指令清單(例如['LEFT','UP']),轉換成實際的x、y方向施力數值
    # 原理:PyBullet世界座標系統中,x軸正方向通常代表「右」,y軸正方向代表「前」,
    #      這裡先定義:RIGHT給x正值、LEFT給x負值,UP在這裡先對應到y軸(前進),
    #      DOWN對應y軸負值(後退)——這個對應方式不是唯一標準答案,
    #      是你自己設計座標系統怎麼對應到「無人機飛行方向」的決定,
    #      之後可以依照你想呈現的demo效果調整

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

# 模擬一個情境:假設YOLO算出的偏移量是 diff_x=50, diff_y=-40
# (物體在畫面右上方,無人機該往右上修正)
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
# 用意:分別記錄x軸(水平位置)跟z軸(高度)的變化,
#      同時觀察兩個方向,確認水平移動的同時,懸停高度有沒有被影響

horizontal_force = 5.0
# 用意:設定一個額外施加在x軸方向的水平推力大小
# 原理:這個數字是「試出來的」,太小球體幾乎不會動,太大會衝太快,
#      之後你可以自己調整這個數字,體會力道大小跟移動速度的關係

for i in range(2000):
    p.applyExternalForce(droneId, -1, [fx, fy, hover_force], [0, 0, 0], p.WORLD_FRAME)
    # 用意:同時施加x軸方向的水平推力,跟z軸方向的懸停力
    # 原理:applyExternalForce的力向量[x,y,z]可以同時指定三個方向的分量,
    #      物體實際受到的是這三個力的合力效果,
    #      這裡x軸給horizontal_force(水平推力),z軸給hover_force(抵消重力)

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




fig = plt.figure(figsize=(8, 6))
ax = fig.add_subplot(111, projection='3d')
# 用意:建立一個3D座標系統的畫布,因為我們要同時呈現x、y、z三個方向的移動軌跡
# 原理:matplotlib的3d投影模式,能把三維空間的移動路徑用視覺化方式呈現出來

ax.set_xlim(min(x_positions), max(x_positions))
ax.set_ylim(min(y_positions), max(y_positions))
ax.set_zlim(min(z_positions), max(z_positions) + 0.5)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z (Height)")
ax.set_title("Drone Simulation Trajectory")

point, = ax.plot([], [], [], 'ro', markersize=10)
# 用意:建立一個紅色圓點,代表無人機(球體)當下的位置,之後會逐格更新它的座標
line, = ax.plot([], [], [], 'b-', alpha=0.5)
# 用意:建立一條藍色的線,用來畫出「走過的軌跡」,alpha=0.5讓線條半透明,不會太搶眼

skip = 20
# 用意:因為原始資料有2000個點,全部畫成動畫會非常慢、檔案也很肥大,
#      每隔20格取一個點來畫,大幅減少動畫的影格數量,讓生成速度更快、檔案更小

def update(frame):
    idx = frame * skip
    if idx >= len(x_positions):
        idx = len(x_positions) - 1
    # 用意:這個函式會被反覆呼叫,每次呼叫代表動畫的「下一格」,
    #      idx算出這一格對應到原始資料的哪個索引位置

    point.set_data([x_positions[idx]], [y_positions[idx]])
    point.set_3d_properties([z_positions[idx]])
    # 用意:更新紅點的位置到這一格的座標

    line.set_data(x_positions[:idx+1], y_positions[:idx+1])
    line.set_3d_properties(z_positions[:idx+1])
    # 用意:更新藍線,畫出從一開始到目前這一格,所有走過的路徑

    return point, line

num_frames = len(x_positions) // skip
ani = FuncAnimation(fig, update, frames=num_frames, interval=30, blit=False)
# 用意:建立動畫物件
# 原理:FuncAnimation會自動重複呼叫update函式num_frames次,
#      interval=30代表每一格動畫間隔30毫秒,讓動畫播放起來速度適中

ani.save("day16_trajectory_animation.gif", writer='pillow', fps=30)
# 用意:把動畫存成gif檔案
# 原理:writer='pillow'指定用pillow套件來輸出gif格式,fps=30是輸出的播放速率

print("動畫已存成 day16_trajectory_animation.gif", flush=True)