#######################################################
## Reset functions for internal usage (Match to Rig)
## resets all controllers transforms (pose mode)
#######################################################

import bpy

def reset_all():
    rig = bpy.context.active_object
    
    def set_inverse_child(cns):         
        # direct inverse matrix method
        if cns.subtarget != "":
            if rig.data.bones.get(cns.subtarget):
                cns.inverse_matrix = rig.pose.bones[cns.subtarget].matrix.inverted()  
        else:
            print("Child Of constraint could not be reset, bone does not exist:", cns.subtarget, cns.name)      
        
    # Reset transforms------------------------------
    bpy.ops.pose.select_all(action='SELECT')
    bpy.ops.pose.loc_clear()
    bpy.ops.pose.rot_clear()
    # "scale clear" leads to resetting bbones_easeout/in value, we need to preserve them
    bdict = {}
    for b in rig.pose.bones:
        bdict[b.name] = [b.bbone_easein, b.bbone_easeout]
        
    bpy.ops.pose.scale_clear()
    
    for bname in bdict:
        pbone = rig.pose.bones[bname]
        pbone.bbone_easein, pbone.bbone_easeout = bdict[bname]
    
    for bone in rig.pose.bones:       
        # Reset locked transforms       
        for i, rot in enumerate(bone.rotation_euler):
            if bone.lock_rotation[i]:                                
                bone.rotation_euler[i] = 0.0
        
        # Reset Properties
        if len(bone.keys()) > 0:
            for key in bone.keys():
                if 'ik_fk_switch' in key:
                    if 'hand' in bone.name:
                        bone['ik_fk_switch'] = 1.0
                    else:
                        bone['ik_fk_switch'] = 0.0
                if 'stretch_length' in key:
                    bone['stretch_length'] = 1.0
                # don't set auto-stretch to 1 for now, it's not compatible with Fbx export
                #if 'auto_stretch' in key:
                #    bone['auto_stretch'] = 1.0
                if 'pin' in key:
                    if 'leg' in key:
                        bone['leg_pin'] = 0.0
                    else:
                        bone['elbow_pin'] = 0.0
                if 'bend_all' in key:
                    bone['bend_all'] = 0.0
                    
        if len(bone.constraints) > 0:
            if bone.name.startswith('c_leg_pole') or bone.name.startswith('c_arms_pole') or 'hand' in bone.name or 'foot' in bone.name or 'head' in bone.name or bone.name.startswith("c_thumb") or bone.name.startswith("c_index") or bone.name.startswith("c_middle") or bone.name.startswith("c_ring") or bone.name.startswith("c_pinky"):
                for cns in bone.constraints:
                    if 'Child Of' in cns.name:
                        set_inverse_child(cns)
    
    bpy.ops.pose.select_all(action='DESELECT')