import bpy
from .version import *


def apply_modifier(mod_name):
    bl_version = blender_version._float
    if bl_version >= 290:
        bpy.ops.object.modifier_apply(modifier=mod_name)
    else:
        bpy.ops.object.modifier_apply(apply_as="DATA", modifier=mod_name)