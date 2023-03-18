import bpy
from math import *
from mathutils import *

def mat3_to_vec_roll(mat, ret_vec=False):
    vec = mat.col[1]
    vecmat = vec_roll_to_mat3(mat.col[1], 0)
    vecmatinv = vecmat.inverted()
    rollmat = vecmatinv @ mat
    roll = atan2(rollmat[0][2], rollmat[2][2])
    if ret_vec:
        return vec, roll
    else:
        return roll


def vec_roll_to_mat3(vec, roll):
    epsi = 0.0000000001
    target = Vector((0, 0.1, 0))
    nor = vec.normalized()
    axis = target.cross(nor)
    if axis.dot(axis) > epsi:
        axis.normalize()
        theta = target.angle(nor)
        bMatrix = Matrix.Rotation(theta, 3, axis)
    else:
        updown = 1 if target.dot(nor) > 0 else -1
        bMatrix = Matrix.Scale(updown, 3)
        bMatrix[2][2] = 1.0

    rMatrix = Matrix.Rotation(roll, 3, nor)
    mat = rMatrix @ bMatrix
    return mat


def align_bone_x_axis(edit_bone, new_x_axis):
    new_x_axis = new_x_axis.cross(edit_bone.y_axis)
    new_x_axis.normalize()
    dot = max(-1.0, min(1.0, edit_bone.z_axis.dot(new_x_axis)))
    angle = acos(dot)
    edit_bone.roll += angle
    dot1 = edit_bone.z_axis.dot(new_x_axis)
    edit_bone.roll -= angle * 2.0
    dot2 = edit_bone.z_axis.dot(new_x_axis)
    if dot1 > dot2:
        edit_bone.roll += angle * 2.0


def align_bone_z_axis(edit_bone, new_z_axis):
    new_z_axis = -(new_z_axis.cross(edit_bone.y_axis))
    new_z_axis.normalize()
    dot = max(-1.0, min(1.0, edit_bone.x_axis.dot(new_z_axis)))
    angle = acos(dot)
    edit_bone.roll += angle
    dot1 = edit_bone.x_axis.dot(new_z_axis)
    edit_bone.roll -= angle * 2.0
    dot2 = edit_bone.x_axis.dot(new_z_axis)
    if dot1 > dot2:
        edit_bone.roll += angle * 2.0


def signed_angle(vector_u, vector_v, normal):
    normal = normal.normalized()
    a = vector_u.angle(vector_v)
    if vector_u.cross(vector_v).angle(normal) < 1:
        a = -a
    return a


def project_point_onto_plane(q, p, n):
    # q = point
    # p = point belonging to the plane
    # n = plane normal
    n = n.normalized()
    return q - ((q - p).dot(n)) * n


def get_pole_angle(base_bone, ik_bone, pole_location):
    pole_normal = (ik_bone.tail - base_bone.head).cross(pole_location - base_bone.head)
    projected_pole_axis = pole_normal.cross(base_bone.tail - base_bone.head)
    return signed_angle(base_bone.x_axis, projected_pole_axis, base_bone.tail - base_bone.head)


def smooth_interpolate(value):
    # value: float belonging to [0, 1]
    # return the smooth interpolated value using cosinus function
    return (cos((value*pi + pi )) + 1) /2


def get_point_projection_onto_line_factor(a, b, p):
    # return the factor of the projected point 'p' onto the line 'a,b'
    # if below a, factor[0] < 0
    # if above b, factor[1] < 0
    return ((p - a).dot(b - a), (p - b).dot(b - a))


def project_point_onto_line(a, b, p):
    # project the point p onto the line a,b
    ap = p - a
    ab = b - a
    result = a + ap.dot(ab) / ab.dot(ab) * ab
    return result


def project_vector_onto_vector(a, b):
    abdot = (a[0] * b[0]) + (a[1] * b[1]) + (a[2] * b[2])
    blensq = (b[0] ** 2) + (b[1] ** 2) + (b[2] ** 2)

    temp = abdot / blensq
    c = Vector((b[0] * temp, b[1] * temp, b[2] * temp))

    return c


def cross(a, b):
    c = Vector((a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]))
    return c


def get_line_plane_intersection(planeNormal, planePoint, rayDirection, rayPoint, epsilon=1e-6):
    ndotu = planeNormal.dot(rayDirection)
    if abs(ndotu) < epsilon:
        raise RuntimeError("no intersection or line is within plane")

    w = rayPoint - planePoint
    si = -planeNormal.dot(w) / ndotu
    Psi = w + si @ rayDirection + planePoint
    return Psi

    
def rotate_object(obj, angle, axis, origin):
    # rotate the object around the "axis" (vector 3) 
    # for the angle value (radians)
    # around the origin (vector 3)
    rot_mat = Matrix.Rotation(angle, 4, axis.normalized())
    loc, rot, scale = obj.matrix_world.decompose()
    loc = loc - origin
    obj_mat = Matrix.Translation(loc) @ rot.to_matrix().to_4x4()
    obj_mat_rotated = rot_mat @ obj_mat
    loc, rot, scale = obj_mat_rotated.decompose()
    loc = loc + origin
    obj.location = loc.copy()
    obj.rotation_euler = rot.to_euler()
    
    # fix numerical imprecisions
    for i in range(0,3):
        rot = obj.rotation_euler[i]
        obj.rotation_euler[i] = round(rot, 4)
        
        
def rotate_point(point_loc, angle, axis, origin):
    # rotate the point_loc (vector 3) around the "axis" (vector 3) 
    # for the angle value (radians)
    # around the origin (vector 3)
    rot_mat = Matrix.Rotation(angle, 4, axis.normalized())
    loc = point_loc.copy()
    loc = loc - origin
    point_mat = Matrix.Translation(loc).to_4x4()
    point_mat_rotated = rot_mat @ point_mat
    loc, rot, scale = point_mat_rotated.decompose()
    loc = loc + origin
    return loc