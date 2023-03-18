import bpy
from .bone_pose import *
from mathutils import *
from math import *

def set_constraint_inverse_matrix(cns):
    # set the inverse matrix of Child Of constraint
    subtarget_pbone = get_pose_bone(cns.subtarget)
    if subtarget_pbone:
        cns.inverse_matrix = subtarget_pbone.bone.matrix_local.to_4x4().inverted()


def add_copy_transf(p_bone, tar=None, subtar="", h_t=0.0, no_scale=False):
    if tar == None:
        tar = bpy.context.active_object

    if no_scale:
        cns1 = p_bone.constraints.new("COPY_LOCATION")
        cns1.name = "Copy Location"
        cns1.target = tar
        cns1.subtarget = subtar
        cns1.head_tail = h_t

        cns2 = p_bone.constraints.new("COPY_ROTATION")
        cns2.name = "Copy Rotation"
        cns2.target = tar
        cns2.subtarget = subtar

        return cns1, cns2
    else:
        cns1 = p_bone.constraints.new("COPY_TRANSFORMS")
        cns1.name = "Copy Transforms"
        cns1.target = tar
        cns1.subtarget = subtar
        cns1.head_tail=h_t

        return cns1, None