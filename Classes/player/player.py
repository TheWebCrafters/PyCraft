# imports
from logging import root
from pyglet.window import key
from pyglet.gl import *
import math
from Classes.util.math_util import _to_radians, normalize

# player class
class Player:
    def __init__(self, pos=(0, 0, 0), rot=(0, 0), parent=None):
        """
        Player

        * the first person controller

        :pos: the position of the player
        :rot: the rotation of the player
        :parent: the parent of the player
        """
        self.pos = list(pos)
        self.rot = list(rot)
        self.vel = [0, 0]
        self.x = 0
        self.y = 0
        self.z = 0
        self.rotY = 0
        self.rotX = 0
        self.parent = parent
        self.speed = 0.3
        self.pointing_at = [[0,0,0], [0,0,0]]

        self.block_exists = {"left": False, "right": False,
                             "forward": False, "backward": False, "up": False, "down": False}
        self.suffocating = False
        self.falling = False
        self.velocity_y = 0
        self.gravity = 0.01
        self.hit_range = 8
        self.friction = 0.25

        self.terminal_velocity = 5

        self.mouse_click = False

    def mouse_motion(self, dx, dy):
        """
        mouse_motion

        * handles mouse movement

        :dx: the change in x
        :dy: the change in y
        """
        self.rot[0] += dy/8
        self.rot[1] -= dx/8
        if self.rot[0] > 90:
            self.rot[0] = 90
        elif self.rot[0] < -90:
            self.rot[0] = -90
        self.rot[0] = self.rot[0]
        self.rot[1] = self.rot[1]

    def collide(self):
        """
        collide

        * handles collision with the world
        """
        x_int = int(self.pos[0])
        y_int = int(self.pos[1])
        z_int = int(self.pos[2])

        if not self.parent.model.block_exists((x_int-1, y_int, z_int)) or self.parent.model.block_exists((x_int-1, y_int+1, z_int)):
            self.block_exists["left"] = False
        else:
            self.block_exists["left"] = True

        if self.parent.model.block_exists((x_int+1, y_int, z_int)) or self.parent.model.block_exists((x_int+1, y_int+1, z_int)):
            self.block_exists["right"] = False
        else:
            self.block_exists["right"] = True

        if not self.parent.model.block_exists((x_int, y_int, z_int-1)) or self.parent.model.block_exists((x_int, y_int+1, z_int+1)):
            self.block_exists["backward"] = False
        else:
            self.block_exists["backward"] = True

        if not self.parent.model.block_exists((x_int, y_int, z_int+1)) or self.parent.model.block_exists((x_int, y_int+1, z_int-1)):
            self.block_exists["forward"] = False
        else:
            self.block_exists["forward"] = True

        if self.parent.model.block_exists((x_int, y_int-2, z_int)):
            self.falling = False
            if self.velocity_y < 0:
                self.velocity_y = 0
        else:
            self.falling = True
            self.velocity_y -= self.gravity

        self._collide(self.pos)

    def hit_test(self, position, vector, max_distance=8):
        """
        hit_test

        * checks if the player is pointing at a block

        :position: the position of the player
        :vector: the vector of the player
        :max_distance: the maximum distance to check

        :return: a list of positions
        """
        m = 8
        x, y, z = position
        dx, dy, dz = vector
        previous = None
        for _ in range(max_distance * m):
            key = normalize((x, y, z))
            if key != previous and self.parent.model.block_exists(key):
                self.pointing_at[0] = key
                self.pointing_at[1] = previous
                return key, previous
            previous = key
            x, y, z = x + dx / m, y + dy / m, z + dz / m
        self.pointing_at[0] = None
        self.pointing_at[1] = None
        return None, None

    def get_surrounding_blocks(self):
        """
        get_surrounding_blocks

        * gets the surrounding blocks of the player

        :return: a list of blocks
        """
        value = []
        if self.block_exists["forward"]:
            value.append((0, 0, -1))
        if self.block_exists["backward"]:
            value.append((0, 0, 1))
        if self.block_exists["right"]:
            value.append((1, 0, 0))
        if self.block_exists["left"]:
            value.append((-1, 0, 0))
        if self.block_exists["up"]:
            value.append((0, 1, 0))
        if self.block_exists["down"]:
            value.append((0, -1, 0))
        return value

    @staticmethod
    def _collision_algorithm(b1,b1_rad, b2, b2_side):
        """
        _collision_algorithm

        * handles collision

        :b1: the first entity
        :b1_rad: the radius of the first entity
        :b2: the second entity
        :b2_side: the side of the second entity

        :return: bool if collision
        """
        try:
            x1, y1, z1 = b1
            x2, y2, z2 = b2
            r1 = b1_rad
            r2 = b2_side

            if abs(x1 - x2) < r1 + r2 or abs(y1-y2) < r1 + r2 or abs(z1-z2) < r1 + r2:
                return True
            return False
        except:
            return False

    def _collide(self, position):
        """
        collide

        * handles collision with the world

        :position: the position of the player
        """
        x, y, z = position
        x = x-int(x)
        y = y-int(y)
        z = z-int(z)

        if self._collision_algorithm((x,y,z),0.45,(0,0,-1),0.5) and self.vel[0] < 0 and self.block_exists["forward"]:
            self.vel[0] = 0
        elif self._collision_algorithm((x,y,z),0.45,(0,0,1),0.5) and self.vel[0] > 0 and self.block_exists["backward"]:
            self.vel[0] = 0
        elif self._collision_algorithm((x,y,z),0.45,(1,0,0),0.5) and self.vel[1] < 0 and self.block_exists["left"]:
            self.vel[1] = 0
        elif self._collision_algorithm((x,y,z),0.45,(-1,0,0),0.5) and self.vel[1] > 0 and self.block_exists["right"]:
            self.vel[1] = 0

    def update(self, dt, keys):
        """
        update

        * updates the player

        :dt: the delta time
        :keys: the keys pressed
        """
        sens = self.speed
        s = dt*10
        rotY = _to_radians(-self.rot[1])
        rotX = _to_radians(-self.rot[0])
        dx, dz = math.sin(rotY), math.cos(rotY)
        dy = math.sin(rotX)
        self.hit_test(position=self.pos, vector=(dx, dy, dz), max_distance=self.hit_range)
        
        if self.velocity_y > self.terminal_velocity:
            self.velocity_y = self.terminal_velocity
        if self.velocity_y < -self.terminal_velocity:
            self.velocity_y = -self.terminal_velocity

        if keys[key.W]:
            self.vel[0] += dx*sens
            self.vel[1] -= dz*sens
        if keys[key.S]:
            self.vel[0] -= dx*sens
            self.vel[1] += dz*sens
        if keys[key.A]:
            self.vel[0] -= dz*sens
            self.vel[1] -= dx*sens
        if keys[key.D]:
            self.vel[0] += dz*sens
            self.vel[1] += dx*sens
        if keys[key.SPACE] and not self.falling:
            self.velocity_y += 0.05
        if keys[key.LCTRL]:
            self.speed = 0.5
        else:
            self.speed = 0.3
        
        self.collide()

        if self.mouse_click and not self.pointing_at[0] is None and not self.pointing_at[1] is None:
            if self.parent.model.block_exists([self.pointing_at[0][0], self.pointing_at[0][1], self.pointing_at[0][2]]):
                self.parent.model.remove_block([self.pointing_at[0][0], self.pointing_at[0][1], self.pointing_at[0][2]])

        self.pos[1] += self.velocity_y
        self.pos[0] += self.vel[0]
        self.pos[2] += self.vel[1]

        self.vel[0] *= self.friction
        self.vel[1] *= self.friction