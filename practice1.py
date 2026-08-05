number = int(input("請輸入一個數字:"))
if number % 2 == 0:
    print("這個數字是偶數")
else:
    print("這個數字是奇數")

i=0
for i in range(1,100):
    if i%3==0:
        print(i,end=" ")

print("\n")
points = [(3, 4), (1, 1), (10, 10), (0, 5)]
point=points[0]
dis=points[0][0] ** 2 + points[0][1] ** 2
for j in range(1, len(points)):
    p=points[j]
    x = (points[j][0] - points[j-1][0]) ** 2 + (points[j][1] - points[j-1][1]) ** 2
    if x< dis:
        point=points[j]
print("距离原点最近的点是:",point)


def find_closest_point(points):
    closest_point = points[0]
    min_distance = points[0][0]**2+points[0][1]**2
    for point in points[1:]:
        distance = point[0]**2 + point[1]**2
        if distance < min_distance:
            closest_point = point
            min_distance = distance
    return closest_point

points = [(2, 4), (3, 3), (10, 0), (1, 5)]
closest_point = find_closest_point(points)
print("距离原点最近的点是:", closest_point)