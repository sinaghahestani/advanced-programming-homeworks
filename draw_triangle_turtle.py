import turtle

def draw_triangle(side_length):
    for _ in range(3):
        turtle.forward(side_length)
        turtle.left(120)

turtle.speed(3)
draw_triangle(200)
turtle.done()
