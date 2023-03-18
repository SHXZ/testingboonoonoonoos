import bpy
from .objects import *

def get_selected_pose_bones():
    return bpy.context.selected_pose_bones


def get_pose_bone(name):
    return bpy.context.active_object.pose.bones.get(name)


def set_bone_custom_shape(pbone, cs_name):
    cs = get_object(cs_name)
    if cs == None:
        append_cs(cs_name)
        cs = get_object(cs_name)

    pbone.custom_shape = cs


def set_bone_color_group(obj, pb, grp_name):
    grp_color_body_mid = (0.0, 1.0, 0.0)
    grp_color_body_left = (1.0, 0.0, 0.0)
    grp_color_body_right = (0.0, 0.0, 1.0)

    grp = obj.pose.bone_groups.get(grp_name)
    if grp == None:
        grp = obj.pose.bone_groups.new(name=grp_name)
        grp.color_set = 'CUSTOM'

        grp_color = None
        if grp_name == "body_mid":
            grp_color = grp_color_body_mid
        elif grp_name == "body_left":
            grp_color = grp_color_body_left
        elif grp_name == "body_right":
            grp_color = grp_color_body_right

        # set normal color
        grp.colors.normal = grp_color
        # set select color/active color
        for col_idx in range(0,3):
            grp.colors.select[col_idx] = grp_color[col_idx] + 0.2
            grp.colors.active[col_idx] = grp_color[col_idx] + 0.4

    pb.bone_group = grp