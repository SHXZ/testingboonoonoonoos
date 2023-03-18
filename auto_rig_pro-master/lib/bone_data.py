import bpy

def get_bone_base_name(bone_name):
    base_name = bone_name[:-2]# head.x > head
    if "_dupli_" in bone_name:
        base_name = bone_name[:-12]
    return base_name


def set_bone_layer(editbone, layer_idx, multi=False):
    editbone.layers[layer_idx] = True
    if multi:
        return
        
    for i, lay in enumerate(editbone.layers):
        if i != layer_idx:
            editbone.layers[i] = False


def get_bone_side(bone_name):
    side = ""
    if not "_dupli_" in bone_name:
        side = bone_name[-2:]
    else:
        side = bone_name[-12:]
    return side


def get_data_bone(bonename):
    return bpy.context.active_object.data.bones.get(bonename)


def duplicate(type=None):
    # runs the operator to duplicate the selected objects/bones
    if type == "EDIT_BONE":
        bpy.ops.armature.duplicate_move(ARMATURE_OT_duplicate={}, TRANSFORM_OT_translate={"value": (0.0, 0.0, 0.0), "constraint_axis": (False, False, False),"orient_type": 'LOCAL', "mirror": False, "use_proportional_edit": False, "snap": False, "remove_on_cancel": False, "release_confirm": False})
    elif type == "OBJECT":
        bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
