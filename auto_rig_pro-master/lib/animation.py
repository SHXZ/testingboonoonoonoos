import bpy, sys
from .maths_geo import *
from .bone_pose import *
from .version import *
from .sys_print import *


def clear_fcurve(fcurve):
    found = True
    while found:
        try:
            fcurve.keyframe_points.remove(fcurve.keyframe_points[0])
        except:
            found = False


def get_keyf_data(key):
    # return keyframe point data
    return [key.co[0], key.co[1], key.handle_left[0], key.handle_left[1], key.handle_right[0], key.handle_right[1],
            key.handle_left_type, key.handle_right_type, key.easing]


def set_keyf_data(key, data):
    # set keyframe point from data (list)
    key.co[0] = data[0]
    key.co[1] = data[1]
    key.handle_left[0] = data[2]
    key.handle_left[1] = data[3]
    key.handle_right[0] = data[4]
    key.handle_right[1] = data[5]
    key.handle_left_type = data[6]
    key.handle_right_type = data[7]
    key.easing = data[8]
    

def bake_anim(frame_start=0, frame_end=10, only_selected=False, bake_bones=True, bake_object=False, shape_keys=False, _self=None, action_export_name=None, new_action=True):  
    scn = bpy.context.scene
    obj_data = []
    bones_data = []
    armature = bpy.data.objects.get(bpy.context.active_object.name)

    def get_bones_matrix():
        matrices_dict = {}
        for pbone in armature.pose.bones:
            if only_selected and not pbone.bone.select:
                continue
            matrices_dict[pbone.name] = armature.convert_space(pose_bone=pbone, matrix=pbone.matrix, from_space="POSE", to_space="LOCAL")
        return matrices_dict

    def get_obj_matrix():
        parent = armature.parent
        matrix = armature.matrix_world
        if parent:
            return parent.matrix_world.inverted_safe() @ matrix
        else:
            return matrix.copy()

    # make list of meshes with valid shape keys
    sk_objects = []
    if shape_keys and _self and action_export_name:# bake shape keys value for animation export
        for ob_name in _self.char_objects:
            ob = bpy.data.objects.get(ob_name+"_arpexport")
            if ob.type != "MESH":
                continue
            if ob.data.shape_keys == None:
                continue
            if len(ob.data.shape_keys.key_blocks) <= 1:
                continue
            sk_objects.append(ob)

    # store matrices
    current_frame = scn.frame_current
    for f in range(int(frame_start), int(frame_end+1)):
        scn.frame_set(f)
        bpy.context.view_layer.update()
        """
        # trigger the update two times to fix instability with IK Splines curves as proxy
        bpy.context.evaluated_depsgraph_get().update()
        scn.frame_set(f)
        bpy.context.view_layer.update()
        """
        # bones data
        if bake_bones:
            bones_data.append((f, get_bones_matrix()))

        # objects data
        if bake_object:
            obj_data.append((f, get_obj_matrix()))

        # shape keys data (for animation export only)
        for ob in sk_objects:
            for i, sk in enumerate(ob.data.shape_keys.key_blocks):
                if (sk.name == "Basis" or sk.name == "00_Basis") and i == 0:
                    continue
                #print(sk.name, float(f-int(frame_range[0])), sk.value)
                frame_in_action = float(f-int(frame_start))
                dict_entry = action_export_name+'|'+'BMesh#'+ob.data.name+'|Shape|BShape Key#'+sk.name+'|'+str(frame_in_action)
                #print(dict_entry, sk.value)
                _self.shape_keys_data[dict_entry] = sk.value

        print_progress_bar("Baking phase 1", f-frame_start, frame_end-frame_start)

    print("")

    # set new action
    action = None
    if new_action:
        action = bpy.data.actions.new("Action")
        anim_data = armature.animation_data_create()
        anim_data.action = action
    else:
        action = armature.animation_data.action

    def store_keyframe(bone_name, prop_type, fc_array_index, frame, value):
        fc_data_path = 'pose.bones["' + bone_name + '"].' + prop_type
        fc_key = (fc_data_path, fc_array_index)
        if not keyframes.get(fc_key):
            keyframes[fc_key] = []
        keyframes[fc_key].extend((frame, value))


    # set transforms and store keyframes
    if bake_bones:
        bone_count = 0
        total_bone_count = len(armature.pose.bones)      
        
        for pbone in armature.pose.bones:
            bone_count += 1
            print_progress_bar("Baking phase 2", bone_count, total_bone_count)

            if only_selected and not pbone.bone.select:
                continue

            euler_prev = None
            quat_prev = None
            keyframes = {}

            for (f, matrix) in bones_data:
                pbone.matrix_basis = matrix[pbone.name].copy()

                for arr_idx, value in enumerate(pbone.location):
                    store_keyframe(pbone.name, "location", arr_idx, f, value)

                rotation_mode = pbone.rotation_mode
                if rotation_mode == 'QUATERNION':
                    if quat_prev is not None:
                        quat = pbone.rotation_quaternion.copy()
                        if blender_version._float >= 282:# previous versions don't know this function
                            quat.make_compatible(quat_prev)
                        pbone.rotation_quaternion = quat
                        quat_prev = quat
                        del quat
                    else:
                        quat_prev = pbone.rotation_quaternion.copy()

                    for arr_idx, value in enumerate(pbone.rotation_quaternion):
                        store_keyframe(pbone.name, "rotation_quaternion", arr_idx, f, value)

                elif rotation_mode == 'AXIS_ANGLE':
                    for arr_idx, value in enumerate(pbone.rotation_axis_angle):
                        store_keyframe(pbone.name, "rotation_axis_angle", arr_idx, f, value)

                else:  # euler, XYZ, ZXY etc
                    if euler_prev is not None:
                        euler = pbone.rotation_euler.copy()
                        euler.make_compatible(euler_prev)
                        pbone.rotation_euler = euler
                        euler_prev = euler
                        del euler
                    else:
                        euler_prev = pbone.rotation_euler.copy()

                    for arr_idx, value in enumerate(pbone.rotation_euler):
                        store_keyframe(pbone.name, "rotation_euler", arr_idx, f, value)

                for arr_idx, value in enumerate(pbone.scale):
                    store_keyframe(pbone.name, "scale", arr_idx, f, value)

            # Add keyframes
            fi = 0
            for fc_key, key_values in keyframes.items():
                data_path, index = fc_key
                fcurve = action.fcurves.find(data_path=data_path, index=index)
                if new_action == False and fcurve:# for now always remove existing keyframes if overwriting current action, must be driven by constraints only
                    action.fcurves.remove(fcurve)
                    fcurve = action.fcurves.new(data_path, index=index, action_group=pbone.name)
                if fcurve == None:
                    fcurve = action.fcurves.new(data_path, index=index, action_group=pbone.name)

                num_keys = len(key_values) // 2
                fcurve.keyframe_points.add(num_keys)
                fcurve.keyframe_points.foreach_set('co', key_values)
                if blender_version._float >= 290:# internal error when doing so with Blender 2.83, only for Blender 2.90 and higher
                    linear_enum_value = bpy.types.Keyframe.bl_rna.properties['interpolation'].enum_items['LINEAR'].value
                    fcurve.keyframe_points.foreach_set('interpolation', (linear_enum_value,) * num_keys)
                else:
                    for kf in fcurve.keyframe_points:
                        kf.interpolation = 'LINEAR'


    if bake_object:
        euler_prev = None
        quat_prev = None

        for (f, matrix) in obj_data:
            name = "Action Bake"
            armature.matrix_basis = matrix

            armature.keyframe_insert("location", index=-1, frame=f, group=name)

            rotation_mode = armature.rotation_mode
            if rotation_mode == 'QUATERNION':
                if quat_prev is not None:
                    quat = armature.rotation_quaternion.copy()
                    if blender_version._float >= 282:# previous versions don't know this function
                        quat.make_compatible(quat_prev)
                    armature.rotation_quaternion = quat
                    quat_prev = quat
                    del quat
                else:
                    quat_prev = armature.rotation_quaternion.copy()
                armature.keyframe_insert("rotation_quaternion", index=-1, frame=f, group=name)
            elif rotation_mode == 'AXIS_ANGLE':
                armature.keyframe_insert("rotation_axis_angle", index=-1, frame=f, group=name)
            else:  # euler, XYZ, ZXY etc
                if euler_prev is not None:
                    euler = armature.rotation_euler.copy()
                    euler.make_compatible(euler_prev)
                    armature.rotation_euler = euler
                    euler_prev = euler
                    del euler
                else:
                    euler_prev = armature.rotation_euler.copy()
                armature.keyframe_insert("rotation_euler", index=-1, frame=f, group=name)

            armature.keyframe_insert("scale", index=-1, frame=f, group=name)


    # restore current frame
    scn.frame_set(current_frame)
    
    print("\n")