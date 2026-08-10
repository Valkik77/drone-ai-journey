import pybullet as p
import pybullet_data
import time
import matplotlib.pyplot as plt

physicsClient = p.connect(p.DIRECT)
# 用意:改用DIRECT模式,不開3D視窗,純粹在背景做物理運算
# 原理:GUI模式需要即時渲染3D畫面,對顯示卡要求較高,容易在某些機器上不穩定;
#      DIRECT模式跳過視覺渲染,只做數學計算,速度更快、更穩定,
#      這在正式做機器學習訓練、大量模擬時也是業界常用的做法

p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
planeId = p.loadURDF("plane.urdf")

droneStartPos = [0, 0, 1]
droneStartOrientation = p.getQuaternionFromEuler([0, 0, 0])
droneId = p.loadURDF("sphere2.urdf", droneStartPos, droneStartOrientation)

mass = p.getDynamicsInfo(droneId, -1)[0]
print(f"物體質量: {mass} kg", flush=True)

hover_force = mass * 9.8

heights = []
# 用意:建立一個空list,記錄每一格模擬時,球體的高度(z座標)

for i in range(2000):
    p.applyExternalForce(droneId, -1, [0, 0, hover_force], [0, 0, 0], p.WORLD_FRAME)
    p.stepSimulation()

    pos, orn = p.getBasePositionAndOrientation(droneId)
    # 用意:取得物體目前的位置(x,y,z座標)跟旋轉狀態
    # 原理:getBasePositionAndOrientation回傳一個tuple,
    #      pos是(x,y,z)座標,orn是旋轉的四元數表示,這裡只需要位置

    heights.append(pos[2])
    # 用意:只記錄z軸(高度)的數值,存進heights這個list

p.disconnect()

print(f"最終高度: {heights[-1]:.3f} 公尺", flush=True)
print(f"起始高度: {heights[0]:.3f} 公尺", flush=True)

plt.plot(heights)
plt.xlabel("模擬步數")
plt.ylabel("高度 (公尺)")
plt.title("球體懸停測試 - 高度變化")
plt.savefig("day15_hover_result.png")
# 用意:把整個模擬過程中高度隨時間變化的曲線畫成圖表,存成圖片檔
# 原理:比起看3D動畫,這種數據圖表更直接證明「懸停有沒有成功」——
#      如果懸停成功,曲線應該會穩定維持在高度1公尺附近,呈一條接近水平的線;
#      如果一直掉落,曲線會持續往下降

print("圖表已存成 day15_hover_result.png", flush=True)