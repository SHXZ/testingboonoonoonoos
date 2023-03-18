#############################################################
## Reset All functions used to reset bone controllers positions
## to be used when posing or animating the character.
## Accessed from the picker "Reset" button
## and from the "Reset All" buttons from the N-key panel, 
## Rig Main Properties tab
#############################################################

import bpy


# FUNCTIONS ------------------------------------
def set_inverse_child(b, cns):			
    # direct inverse matrix method
    if cns.subtarget != "":
        if bpy.context.active_object.data.bones.get(cns.subtarget):           
            cns.inverse_matrix = bpy.context.active_object.pose.bones[cns.subtarget].matrix.inverted()	
    else:
        print("Child Of constraint could not be reset, bone does not exist:", cns.subtarget, cns.name)
        
             
def is_reset_bone(bone_name):    
    reset_bones_parent = ["c_foot_ik", "c_hand_ik"]
    
    for n in reset_bones_parent:
        if n in bone_name:
            return True 

def reset_all_controllers():
    # the function is run at startup, this allows to exit it
    try:
        bpy.context.active_object
    except:
        return
        
    #save display layers
    saved_layers = [layer_bool for layer_bool in bpy.context.active_object.data.layers]


    #display layer 8 for neck child of reset
    disp_layer = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,22,23,24,25,26,27,28,29,30,31]
    for idx in disp_layer:
        bpy.context.active_object.data.layers[idx] = True
        
    bones_data = bpy.context.active_object.data.bones


    # Reset Properties
    for bone in bpy.context.object.pose.bones:
        bone_parent = ""
        try:
            bone_parent = bone.parent.name
        except:
            pass
        
        if (bone.name[:2] == 'c_' or bone.name[:3] == "cc_") and bone_parent != "Picker": 
            bone.location = [0,0,0]
            bone.rotation_euler = [0,0,0]
            if bone.rotation_mode == 'QUATERNION':
                bone.rotation_quaternion = [1,0,0,0]
            bone.scale = [1.0,1.0,1.0]
        
        if len(bone.keys()) > 0:
            for key in bone.keys():
                if 'ik_fk_switch' in key:
                    if 'hand' in bone.name:
                        bone['ik_fk_switch'] = 1.0
                    else:
                        bone['ik_fk_switch'] = 0.0
                if 'stretch_length' in key:
                    bone['stretch_length'] = 1.0
                if 'auto_stretch' in key:
                    bone['auto_stretch'] = 1.0
                if 'pin' in key:
                    if 'leg' in key:
                        bone['leg_pin'] = 0.0
                    else:
                        bone['elbow_pin'] = 0.0
                if 'bend_all' in key:
                    bone['bend_all'] = 0.0
                if 'fingers_grasp' in key:
                    bone['fingers_grasp'] = 0.0
                if 'thigh_twist' in key:
                    bone['thigh_twist'] = 0.0
                if 'arm_twist' in key:
                    bone['arm_twist'] = 0.0
              
    #hide layers
    for i, layer_bool in enumerate(saved_layers):
        bpy.context.active_object.data.layers[i] = layer_bool

    bpy.ops.pose.select_all(action='DESELECT')
    
# necessary, since the picker execute scripts instead of calling functions 
reset_all_controllers()


