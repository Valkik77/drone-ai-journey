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
# 用意:先用球體代替無人機模型,驗證物理模擬邏輯是否正確
# 原理:sphere2.urdf是pybullet_data內建的標準球體模型,
#      因為你這個版本沒有內建無人機URDF,先用現成的簡單物體驗證重力、施力等物理概念,
#      之後如果需要外觀更像無人機,可以另外下載開源的無人機URDF檔案替換,
#      不影響現在要學的核心物理概念(施力、懸停控制)

for i in range(1000):
    p.stepSimulation()
    time.sleep(1./240.)

input("模擬結束,按Enter鍵關閉視窗...")
p.disconnect()