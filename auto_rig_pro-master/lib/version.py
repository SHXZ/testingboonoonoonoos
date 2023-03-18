import bpy

class ARP_blender_version:
    _string = bpy.app.version_string
    blender_v = bpy.app.version
    _float = blender_v[0]*100+blender_v[1]+blender_v[2]*0.01
    _char = bpy.app.version_char
    
blender_version = ARP_blender_version()


def check_id_root(action):
    bl_version = blender_version._float
    if bl_version >= 291:
        if getattr(action, "id_root", None) == "OBJECT":
            return True
        else:
            return False
    else:
        return True
        
        
def invert_angle_with_blender_versions(angle=None, bone=False, axis=None):
    # Deprecated!
    # Use rotate_edit_bone() and rotate_object() instead
    #
    # bpy.ops.transform.rotate has inverted angle value depending on the Blender version
    # this function is necessary to support these version specificities
    bl_version = blender_version._float

    #print("BL VERSION", bl_version)
    invert = False
    if bone == False:
        if (bl_version >= 283 and bl_version < 290) or (bl_version >= 291 and bl_version < 292):
            invert = True

    elif bone == True:
        # bone rotation support
        # the rotation direction is inverted in Blender 2.83 only for Z axis
        if axis == "Z":
            if bl_version >= 283 and bl_version < 290:
                invert = True
        # the rotation direction is inverted for all but Z axis in Blender 2.90 and higher
        if axis != "Z":
            if bl_version >= 290:
                invert = True

    if invert:
        angle = -angle

    return angle