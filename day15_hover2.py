import pybullet as p
import pybullet_data
import time

physicsClient = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.8)
planeId = p.loadURDF("plane.urdf")

droneStartPos = [0, 0, 1]
droneStartOrientation = p.getQuaternionFromEuler([0, 0, 0])
droneId = p.loadURDF("sphere2.urdf", droneStartPos, droneStartOrientation)
# 用意:載入球體代替無人機,起始位置在高度1公尺處

mass = p.getDynamicsInfo(droneId, -1)[0]
# 用意:取得這個物體的實際質量
# 原理:getDynamicsInfo回傳一堆物理屬性,[0]是質量,
#      要先知道質量,才能算出讓它「剛好不掉落、也不上升」所需要的力

print(f"物體質量: {mass} kg", flush=True)
# 用意:先印出質量,方便你確認數值合理(sphere2.urdf預設質量通常是1kg左右)

hover_force = mass * 9.8
# 用意:算出讓物體「剛好抵消重力」所需要的向上力
# 原理:牛頓第二定律 F=ma,重力造成的下墜加速度是9.8,
#      施加大小相等、方向相反的力,合力就是0,物體不會動

for i in range(2000):
    p.applyExternalForce(droneId, -1, [0, 0, hover_force], [0, 0, 0], p.WORLD_FRAME)
    # 用意:每一格模擬,都對物體施加向上的力,持續抵消重力
    # 原理:applyExternalForce必須「每一格都重新呼叫」,因為PyBullet不會記住
    #      「上一格施過的力」,你要它每一瞬間都受力,就要每一格都下達一次指令,
    #      這跟真實世界的馬達持續運轉、持續產生升力的概念是一樣的

    p.stepSimulation()
    time.sleep(1./240.)

input("模擬結束,按Enter鍵關閉視窗...")
p.disconnect()