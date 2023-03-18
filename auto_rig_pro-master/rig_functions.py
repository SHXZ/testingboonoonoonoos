import bpy, os
from mathutils import *
from math import *
from bpy.app.handlers import persistent
from . import auto_rig_datas
from . import reset_all_controllers
from operator import itemgetter
from bpy.types import (
    Operator,
    Menu,
    Panel,
    UIList,
    PropertyGroup,
)

#print ("\n Starting Auto-Rig Pro Functions... \n")

# Global vars
hands_ctrl = ["c_hand_ik", "c_hand_fk"]
sides = [".l", ".r"]
eye_aim_bones = ["c_eye_target.x", "c_eye"]
auto_eyelids_bones = ["c_eye", "c_eyelid_top", "c_eyelid_bot"]
fk_arm = ["c_arm_fk", "c_forearm_fk", "c_hand_fk", "arm_fk_pole"]
ik_arm = ["arm_ik", "forearm_ik", "c_hand_ik", "c_arms_pole", "c_arm_ik"]
fk_leg = ["c_thigh_fk", "c_leg_fk", "c_foot_fk", "c_toes_fk", "leg_fk_pole"]
ik_leg = ["thigh_ik", "leg_ik", "c_foot_ik", "c_leg_pole", "c_toes_ik", "c_foot_01", "c_foot_roll_cursor", "foot_snap_fk", "c_thigh_ik", "c_toes_pivot", "c_foot_ik_offset", "c_thigh_b"]
fingers_root = ["c_index1_base", "c_thumb1_base", "c_middle1_base", "c_ring1_base", "c_pinky1_base"]
fingers_start = ["c_thumb", "c_index", "c_middle", "c_ring", "c_pinky"]
fingers_type_list = ["thumb", "index", "middle", "ring", "pinky"]

# OPERATOR CLASSES ########################################################################################################### 
class ARP_OT_layers_add_defaults(Operator):
    """Add default Main and Secondary layer sets"""
    bl_idname = "arp.layers_add_defaults"
    bl_label = "Show All Layers Set"
    bl_options = {'UNDO'}   
  
    def execute(self, context):        
        try:           
            rig = bpy.context.active_object
    
            set1 = rig.layers_set.add()
            set1.name = 'Main'    
            lay1 = set1.layers.add()
            lay1.idx = 0
            
            set2 = rig.layers_set.add()
            set2.name = 'Secondary'    
            lay2 = set2.layers.add()
            lay2.idx = 1
    
            rig.layers_set_idx = len(rig.layers_set)-1
                    
        except:
            pass
        return {'FINISHED'}
        
        
class ARP_OT_layers_set_all_toggle(Operator):
    """Set all layers visibility.\nWhen hiding all, the first layer will remain displayed"""
    bl_idname = "arp.layers_set_all_toggle"
    bl_label = "Show All Layers Set"
    bl_options = {'UNDO'}   
  
    state: bpy.props.BoolProperty(default=True)
    
    def execute(self, context):        
        try:   
            rig = bpy.context.active_object           
            
            if self.state == False:
                rig.data.layers[0] = True
                
            for set in rig.layers_set:
                for lay in set.layers:
                    if self.state == False:
                        if lay.idx == 0:
                            continue
                    rig.data.layers[lay.idx] = self.state            
        except:
            pass
        return {'FINISHED'}
        

class ARP_MT_layers_set_menu(Menu):
    bl_label = "Layers Set Specials"

    def draw(self, _context):
        layout = self.layout
        layout.operator("arp.layers_set_all_toggle", text="Show All", icon='HIDE_OFF').state = True
        layout.operator("arp.layers_set_all_toggle", text="Hide All", icon='HIDE_ON').state = False
        layout.operator("arp.layers_add_defaults", text="Add Default Sets")
        

def set_layer_vis(self, state):
    rig = bpy.context.active_object
    
    for lay in self.layers:
        rig.data.layers[lay.idx] = state
    
    
def update_layer_set_on(self, context):  
    set_layer_vis(self, True)
    
    
def update_layer_set_off(self, context):  
    set_layer_vis(self, False)
    
    
def update_layer_set_exclusive(self, context):
    rig = bpy.context.active_object
    
    set_layer_vis(self, True)
    
    for lay_set in rig.layers_set:
        if lay_set != self:
            for lay in lay_set.layers:
                rig.data.layers[lay.idx] = False

    set_layer_vis(self, True)
    
    
class LayerIdx(PropertyGroup):
    idx: bpy.props.IntProperty(default=0, description="Layer index", override={'LIBRARY_OVERRIDABLE'})
    

class LayerSet(PropertyGroup):  
    name : bpy.props.StringProperty(default="", description="Limb Name", override={'LIBRARY_OVERRIDABLE'})
    layers: bpy.props.CollectionProperty(type=LayerIdx, description="Collection of layers index or this set", override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})
    show_toggle: bpy.props.BoolProperty(default=True, update=update_layer_set_on)
    hide_toggle: bpy.props.BoolProperty(default=True, update=update_layer_set_off)
    exclusive_toggle: bpy.props.BoolProperty(default=True, update=update_layer_set_exclusive)
    
    
class ARP_UL_layers_set_list(UIList):
    """
    @classmethod
    def poll(cls, context):
        return
    """
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "name", text="", emboss=False, translate=False)# icon='BONE_DATA')
        row.prop(item, "show_toggle", text="", icon='HIDE_OFF', emboss=False)
        row.prop(item, "hide_toggle", text="", icon='HIDE_ON', emboss=False)
        row.prop(item, "exclusive_toggle", text="", icon='LAYER_ACTIVE', emboss=False)
        
    def invoke(self, context, event):
        pass
        
        
class ARP_OT_layers_set_move(bpy.types.Operator):
    """Move entry"""
    bl_idname = "arp.layers_set_move"
    bl_label = "Move Layer Set"
    bl_options = {'UNDO'}   
  
    direction: bpy.props.StringProperty(default="UP")
    
    def execute(self, context):        
        try:   
            rig = bpy.context.active_object
            fac = -1
            if self.direction == 'DOWN':
                fac = 1
                
            target_idx = rig.layers_set_idx + fac
            if target_idx < 0:
                target_idx = len(rig.layers_set)-1
            if target_idx > len(rig.layers_set)-1:
                target_idx = 0
                
            #item = rig.layers_set[rig.layers_set_idx]
            rig.layers_set.move(rig.layers_set_idx, target_idx)
            rig.layers_set_idx = target_idx
            
        except:
            pass
        return {'FINISHED'}
  

class ARP_OT_layers_set_add(bpy.types.Operator):
    """Add a layer set"""
    bl_idname = "arp.layers_set_add"
    bl_label = "Add Layer Set"
    bl_options = {'UNDO'}
   
    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        rig_data = context.active_object.data
        
        layout.prop(rig_data, "layers", text="")


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:       
            _add_layer_set(self)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}

    def invoke(self, context, event):
        # Open dialog
        wm = context.window_manager
        return wm.invoke_props_dialog(self)
        
        
class ARP_OT_layers_set_remove(bpy.types.Operator):
    """Remove a layer set"""
    bl_idname = "arp.layers_set_remove"
    bl_label = "Remove Layer Set"
    bl_options = {'UNDO'}

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:       
            _remove_layer_set(self)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'} 
        

class ARP_OT_switch_snap_root_tip_all(Operator):
    """Switch and snap all fingers IK Root-Tip"""

    bl_idname = "arp.switch_snap_root_tip_all"
    bl_label = "switch_snap_root_tip_all"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    finger_root_name: bpy.props.StringProperty(name="", default="")
    state: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            for fing_type in fingers_start:
                finger_root_name = fing_type+"1_base"+self.side
                finger_root = get_pose_bone(finger_root_name)

                if self.state == "ROOT":
                    root_to_tip_finger(finger_root, self.side)
                elif self.state == "TIP":
                    tip_to_root_finger(finger_root, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_switch_all_fingers(Operator):
    """Set all fingers to IK or FK"""

    bl_idname = "arp.switch_all_fingers"
    bl_label = "switch_all_fingers"
    bl_options = {'UNDO'}

    state: bpy.props.StringProperty(default="")
    side: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        try:
            for fing_type in fingers_start:
                finger_root_name = fing_type+"1_base"+self.side
                finger_root = get_pose_bone(finger_root_name)

                if finger_root:
                    if "ik_fk_switch" in finger_root.keys():
                        if self.state == "IK":
                            ik_to_fk_finger(finger_root, self.side)

                        elif self.state == "FK":
                            fk_to_ik_finger(finger_root, self.side)

        finally:
            print("")

        return {'FINISHED'}


class ARP_OT_free_parent_ik_fingers(Operator):
    """Enable or disable the Child Of constraints of all fingers IK target"""

    bl_idname = "arp.free_lock_ik_fingers"
    bl_label = "free_lock_ik_fingers"
    bl_options = {'UNDO'}

    side: bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        try:
            for fing_type in fingers_start:
                ik_target_name = fing_type+"_ik"+self.side
                ik_target2_name = fing_type+"_ik2"+self.side
                ik_target_pb = get_pose_bone(ik_target_name)
                ik_target2_pb = get_pose_bone(ik_target2_name)

                for b in [ik_target_pb, ik_target2_pb]:
                    if b == None:
                        continue
                    if len(b.constraints) == 0:
                        continue

                    hand_cns = b.constraints.get("Child Of_hand")
                    if hand_cns:
                        if hand_cns.influence > 0.5:# set free
                            mat = b.matrix.copy()
                            hand_cns.influence = 0.0
                            b.matrix = mat

                        else:# parent
                            mat = b.matrix.copy()
                            bone_parent = get_pose_bone(hand_cns.subtarget)
                            hand_cns.influence = 1.0
                            b.matrix = bone_parent.matrix_channel.inverted() @ mat


        finally:
            print("")

        return {'FINISHED'}


class ARP_OT_toggle_layers(Operator):
    """Toggle controller layers visibility"""

    bl_idname = "arp.toggle_layers"
    bl_label = "toggle_layers"
    bl_options = {'UNDO'}

    layer_idx : bpy.props.IntProperty(name="Layer Index", default=0)

    @classmethod
    def poll(cls, context):
        if context.active_object != None:
            if context.active_object.type == "ARMATURE":
                return True

    def execute(self, context):
        try:
            arm = bpy.context.active_object
            arm.data.layers[self.layer_idx] = not arm.data.layers[self.layer_idx]
        finally:
            print("")
        return {'FINISHED'}


class ARP_OT_snap_head(Operator):
    """Switch the Head Lock and snap the head rotation"""

    bl_idname = "arp.snap_head"
    bl_label = "snap_head"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="Side", default="")

    @classmethod
    def poll(cls, context):
        if context.object != None:
            if is_object_arp(context.object):
                return True

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)
            _snap_head(self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_reset_script(Operator):
    """Reset character controllers to rest position"""

    bl_idname = "arp.reset_pose"
    bl_label = "reset_pose"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.object != None:
            if is_object_arp(context.object):
                return True

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            reset_all_controllers.reset_all_controllers()

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_set_picker_camera_func(Operator):

    """Display the bone picker of the selected character in this active view"""

    bl_idname = "id.set_picker_camera_func"
    bl_label = "set_picker_camera_func"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.object != None:
            if is_object_arp(context.object):
                return True

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _set_picker_camera(self)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_toggle_multi(Operator):
    """Toggle multi-limb visibility"""

    bl_idname = "id.toggle_multi"
    bl_label = "toggle_multi"
    bl_options = {'UNDO'}

    limb : bpy.props.StringProperty(name="Limb")
    id : bpy.props.StringProperty(name="Id")
    key : bpy.props.StringProperty(name="key")
    """
    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')
    """

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _toggle_multi(self.limb, self.id, self.key)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_snap_pin(Operator):
    """Switch and snap the pinning bone"""

    bl_idname = "pose.arp_snap_pin"
    bl_label = "Arp Switch and Snap Pin"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    type : bpy.props.StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            if is_selected(fk_arm, bname) or is_selected(ik_arm, bname):
                self.type = "arm"
            elif is_selected(fk_leg, bname) or is_selected(ik_leg, bname):
                self.type = "leg"

            _switch_snap_pin(self.side, self.type)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_arp_snap_pole(Operator):
    """Switch and snap the IK pole parent"""

    bl_idname = "pose.arp_snap_pole"
    bl_label = "Arp Snap FK arm to IK"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    bone_type : bpy.props.StringProperty(name="arm or leg")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            if is_selected(fk_arm, bname) or is_selected(ik_arm, bname):
                self.bone_type = "arms"
            elif is_selected(fk_leg, bname) or is_selected(ik_leg, bname):
                self.bone_type = "leg"

            _arp_snap_pole(context.active_object, self.side, self.bone_type)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_arm_bake_fk_to_ik(Operator):
    """Snaps and bake an FK to an IK arm over a specified frame range"""

    bl_idname = "pose.arp_bake_arm_fk_to_ik"
    bl_label = "Snap an FK to IK arm over a specified frame range"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    frame_start : bpy.props.IntProperty(name="Frame start", default=0)
    frame_end : bpy.props.IntProperty(name="Frame end", default=10)

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')


    def draw(self, context):
        layout = self.layout
        row = layout.column().row(align=True)
        row.prop(self, 'frame_start', text='Frame Start')
        row.prop(self, 'frame_end', text='Frame End')
        layout.separator()


    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        # set auto key to True
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = True
        # save current frame
        cur_frame = scn.frame_current

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            bake_fk_to_ik_arm(self)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)

        return {'FINISHED'}


class ARP_OT_arm_fk_to_ik(Operator):
    """Snaps an FK arm to an IK arm"""

    bl_idname = "pose.arp_arm_fk_to_ik_"
    bl_label = "Arp Snap FK arm to IK"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            fk_to_ik_arm(context.active_object, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_arm_bake_ik_to_fk(Operator):
    """Snaps and bake an IK to an FK arm over a specified frame range"""

    bl_idname = "pose.arp_bake_arm_ik_to_fk"
    bl_label = "Snap an IK to FK arm over a specified frame range"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    frame_start : bpy.props.IntProperty(name="Frame start", default=0)
    frame_end : bpy.props.IntProperty(name="Frame end", default=10)

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def draw(self, context):
        layout = self.layout
        row = layout.column().row(align=True)
        row.prop(self, 'frame_start', text='Frame Start')
        row.prop(self, 'frame_end', text='Frame End')
        layout.separator()

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = scn.tool_settings.use_keyframe_insert_auto
        # set auto key to True
        scn.tool_settings.use_keyframe_insert_auto = True
        # save current frame
        cur_frame = scn.frame_current

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            bake_ik_to_fk_arm(self)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)

        return {'FINISHED'}


class ARP_OT_arm_ik_to_fk(Operator):
    """Snaps an IK arm to an FK arm"""

    bl_idname = "pose.arp_arm_ik_to_fk_"
    bl_label = "Arp Snap IK arm to FK"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            ik_to_fk_arm(context.active_object, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_switch_snap_root_tip(Operator):
    """Switch and snap fingers IK Root-Tip"""

    bl_idname = "arp.switch_snap_root_tip"
    bl_label = "switch_snap_root_tip"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    finger_root_name: bpy.props.StringProperty(name="", default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            finger_type = None
            for type in fingers_type_list:
                if type in bname:
                    finger_type = type
                    break

            self.finger_root_name = "c_"+finger_type+"1_base"+self.side
            root_finger = get_pose_bone(self.finger_root_name)

            if root_finger['ik_tip'] < 0.5:
                tip_to_root_finger(root_finger, self.side)
            else:
                root_to_tip_finger(root_finger, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_switch_snap(Operator):
    """Switch and snap the IK-FK"""

    bl_idname = "pose.arp_switch_snap"
    bl_label = "Arp Switch and Snap IK FK"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    type : bpy.props.StringProperty(name="type", default="")
    finger_root_name: bpy.props.StringProperty(name="", default="")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            if is_selected(fk_leg, bname) or is_selected(ik_leg, bname):
                self.type = "LEG"
            elif is_selected(fk_arm, bname) or is_selected(ik_arm, bname):
                self.type = "ARM"
            elif is_selected(fingers_start, bname, startswith=True):
                self.type = "FINGER"

                finger_type = None
                for type in fingers_type_list:
                    if type in bname:
                        finger_type = type
                        break

                self.finger_root_name = "c_"+finger_type+"1_base"+self.side

            if self.type == "ARM":
                hand_ik = get_pose_bone(ik_arm[2] + self.side)
                if hand_ik['ik_fk_switch'] < 0.5:
                    fk_to_ik_arm(context.active_object, self.side)
                else:
                    ik_to_fk_arm(context.active_object, self.side)

            elif self.type == "LEG":
                foot_ik = get_pose_bone(ik_leg[2] + self.side)
                if foot_ik['ik_fk_switch'] < 0.5:
                    fk_to_ik_leg(context.active_object, self.side)
                else:
                    ik_to_fk_leg(context.active_object, self.side)

            elif self.type == "FINGER":
                root_finger = get_pose_bone(self.finger_root_name)
                if root_finger['ik_fk_switch'] < 0.5:
                    fk_to_ik_finger(root_finger, self.side)
                else:
                    ik_to_fk_finger(root_finger, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_leg_bake_fk_to_ik(Operator):
    """Snaps and bake an FK leg to an IK leg over a specified frame range"""

    bl_idname = "pose.arp_bake_leg_fk_to_ik"
    bl_label = "Snap an FK to IK leg over a specified frame range"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    frame_start : bpy.props.IntProperty(name="Frame start", default=0)
    frame_end : bpy.props.IntProperty(name="Frame end", default=10)
    temp_frame_start = 0
    temp_frame_end = 1

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')


    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(self, 'frame_start', text='Frame Start')
        row.prop(self, 'frame_end', text='Frame End')

        layout.separator()


    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)


    def set_range():
        ARP_OT_leg_bake_fk_to_ik.frame_start = ARP_OT_leg_bake_fk_to_ik.temp_frame_start
        ARP_OT_leg_bake_fk_to_ik.frame_end = ARP_OT_leg_bake_fk_to_ik.temp_frame_end


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = scn.tool_settings.use_keyframe_insert_auto
        # set auto key to True
        scn.tool_settings.use_keyframe_insert_auto = True
        # save current frame
        cur_frame = scn.frame_current
        
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            bake_fk_to_ik_leg(self)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)

        return {'FINISHED'}


class ARP_OT_leg_fk_to_ik(Operator):
    """Snaps an FK leg to an IK leg"""

    bl_idname = "pose.arp_leg_fk_to_ik_"
    bl_label = "Arp Snap FK leg to IK"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            fk_to_ik_leg(context.active_object, self.side)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_leg_bake_ik_to_fk(Operator):
    """Snaps and bake an IK leg to an FK leg over a specified frame range"""

    bl_idname = "pose.arp_bake_leg_ik_to_fk"
    bl_label = "Snap an IK to FK leg over a specified frame range"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")
    frame_start : bpy.props.IntProperty(name="Frame start", default=0)
    frame_end : bpy.props.IntProperty(name="Frame end", default=10)

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def draw(self, context):
        layout = self.layout
        row = layout.column().row(align=True)
        row.prop(self, 'frame_start', text='Frame Start')
        row.prop(self, 'frame_end', text='Frame End')
        layout.separator()

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=400)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        scn = context.scene
        
        # save current autokey state
        auto_key_state = bpy.context.scene.tool_settings.use_keyframe_insert_auto
        # set auto key to True
        bpy.context.scene.tool_settings.use_keyframe_insert_auto = True
        # save current frame
        cur_frame = scn.frame_current

        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            bake_ik_to_fk_leg(self)
            
        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            # restore autokey state
            scn.tool_settings.use_keyframe_insert_auto = auto_key_state
            # restore frame
            scn.frame_set(cur_frame)

        return {'FINISHED'}


class ARP_OT_leg_ik_to_fk(Operator):
    """Snaps an IK leg to an FK leg"""

    bl_idname = "pose.arp_leg_ik_to_fk_"
    bl_label = "Arp Snap IK leg to FK"
    bl_options = {'UNDO'}

    side : bpy.props.StringProperty(name="bone side")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.mode == 'POSE')

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            bname = get_selected_pbone_name()
            self.side = get_bone_side(bname)

            ik_to_fk_leg(context.active_object, self.side)
        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}



###FUNCTIONS ##############################################
def set_active_object(object_name):
     bpy.context.view_layer.objects.active = bpy.data.objects[object_name]
     bpy.data.objects[object_name].select_set(state=1)

def is_object_arp(object):
    if object.type == 'ARMATURE':
        if object.pose.bones.get('c_pos') != None:
            return True

def get_selected_pbone_name():
    try:
        return bpy.context.active_pose_bone.name
    except (AttributeError, TypeError):
        return

def get_bone_side(bone_name):
    side = ""
    if not "_dupli_" in bone_name:
        side = bone_name[-2:]
    else:
        side = bone_name[-12:]
    return side


def append_from_arp(nodes=None, type=None):
    context = bpy.context
    scene = context.scene

    addon_directory = os.path.dirname(os.path.abspath(__file__))
    filepath = addon_directory + "/armature_presets/" + "master.blend"

    if type == "object":
        # Clean the cs_ materials names (avoid .001, .002...)
        for mat in bpy.data.materials:
            if mat.name[:3] == "cs_":
                if mat.name[-3:].isdigit() and bpy.data.materials.get(mat.name[:-4]) == None:
                    mat.name = mat.name[:-4]

        # make a list of current custom shapes objects in the scene for removal later
        cs_objects = [obj.name for obj in bpy.data.objects if obj.name[:3] == "cs_"]

        # Load the objects data in the file
        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            data_to.objects = [name for name in data_from.objects if name in nodes]

        # Add the objects in the scene
        for obj in data_to.objects:
            if obj:
                # Link
                bpy.context.scene.collection.objects.link(obj)

                # Apply existing scene material if exists
                if len(obj.material_slots) > 0:
                    mat_name = obj.material_slots[0].name
                    found_mat = None

                    for mat in bpy.data.materials:
                        if mat.name == mat_name[:-4]:  # substract .001, .002...
                            found_mat = mat.name
                            break

                    # Assign existing material if already in file and delete the imported one
                    if found_mat:
                        obj.material_slots[0].material = bpy.data.materials[found_mat]
                        bpy.data.materials.remove(bpy.data.materials[mat_name], do_unlink=True)

                # If we append a custom shape
                if "cs_" in obj.name or "c_sphere" in obj.name:
                    cs_grp = bpy.data.objects.get("cs_grp")
                    if cs_grp:
                        # parent the custom shape
                        obj.parent = cs_grp

                        # assign to new collection
                        assigned_collections = []
                        for collec in cs_grp.users_collection:
                            collec.objects.link(obj)
                            assigned_collections.append(collec)

                        if len(assigned_collections) > 0:
                            # remove previous collections
                            for i in obj.users_collection:
                                if not i in assigned_collections:
                                    i.objects.unlink(obj)
                            # and the scene collection
                            try:
                                bpy.context.scene.collection.objects.unlink(obj)
                            except:
                                pass

                # If we append other objects,
                # find added/useless custom shapes and delete them
                else:
                    for obj in bpy.data.objects:
                        if obj.name[:3] == "cs_":
                            if not obj.name in cs_objects:
                                bpy.data.objects.remove(obj, do_unlink=True)

                    if 'obj' in locals():
                        del obj

    if type == "text":
        # Load the objects data in the file
        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            data_to.texts = [name for name in data_from.texts if name in nodes]
        print("Loading text file:", data_to.texts)
        bpy.context.evaluated_depsgraph_get().update()

    if type == "font":
        # Load the data in the file
        with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
            data_to.fonts = [name for name in data_from.fonts if name in nodes]
        print("Loading font file:", data_to.fonts)
        bpy.context.evaluated_depsgraph_get().update()


def tip_to_root_finger(root_finger, side):
    scn = bpy.context.scene

    finger_type = None
    rig = bpy.context.active_object

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break

    ik_target_name = ""
    ik_tip = root_finger["ik_tip"]
    ik_target_name = "c_"+finger_type+"_ik"+side
    ik_target2_name = "c_"+finger_type+"_ik2"+side
    ik_target = get_pose_bone(ik_target_name)
    ik_target2 = get_pose_bone(ik_target2_name)

    if ik_target == None or ik_target2 == None:
        print("Finger IK target not found:", ik_target_name)
        return

    ik_pole_name = "c_"+finger_type+"_pole"+side
    ik_pole = get_pose_bone(ik_pole_name)
    if ik_pole == None:
        print("Finger IK pole not found:", ik_pole_name)
        return

    # Snap IK target
        # constraint support
    constraint, bparent_name, parent_type, valid_constraint = get_active_child_of_cns(ik_target)
    finger3_ik = get_pose_bone("c_"+finger_type+"3_ik"+side)

    if constraint and valid_constraint:
        if parent_type == "bone":
            bone_parent = get_pose_bone(bparent_name)
            ik_target.matrix = bone_parent.matrix_channel.inverted() @ finger3_ik.matrix
            update_transform()
            # set head to tail position
            tail_mat = bone_parent.matrix_channel.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
            ik_target.matrix = tail_mat @ ik_target.matrix

        if parent_type == "object":
            obj = bpy.data.objects.get(bparent_name)
            ik_target.matrix = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ finger3_ik.matrix
            update_transform()
            # set head to tail position
            tail_mat = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
            ik_target.matrix = tail_mat @ ik_target.matrix
    else:
        ik_target.matrix = finger3_ik.matrix
        update_transform()
        # set head to tail position
        tail_mat = Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
        ik_target.matrix = tail_mat @ ik_target.matrix

    update_transform()

    # Snap phalanges
    ik_fingers = ["c_"+finger_type+"1_ik"+side, "c_"+finger_type+"2_ik"+side, "c_"+finger_type+"3_ik"+side]

        # store current matrices
    fingers_mat = []
    for i, bname in enumerate(ik_fingers):
        b_ik = get_pose_bone(bname)
        fingers_mat.append(b_ik.matrix.copy())

    # Switch prop
    root_finger["ik_tip"] = 1

    for iter in range(0,4):
        for i, bname in enumerate(ik_fingers):
            b_ik = get_pose_bone(bname)
            loc, scale = b_ik.location.copy(), b_ik.scale.copy()
            b_ik.matrix = fingers_mat[i]
            # restore loc and scale, only rotation for better results
            b_ik.location = loc
            b_ik.scale = scale
        # update hack
        update_transform()

    # udpate hack
    update_transform()

    #insert key if autokey enable
    if scn.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_tip"]')

        for bname in ik_fingers+[ik_target.name, ik_target2.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            pb.keyframe_insert(data_path="scale")


def root_to_tip_finger(root_finger, side):
    scn = bpy.context.scene
    finger_type = None
    rig = bpy.context.active_object

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break

    ik_target_name = ""
    ik_tip = root_finger["ik_tip"]
    ik_target_name = "c_"+finger_type+"_ik"+side
    ik_target2_name = "c_"+finger_type+"_ik2"+side
    ik_target = get_pose_bone(ik_target_name)
    ik_target2 = get_pose_bone(ik_target2_name)

    if ik_target == None or ik_target2 == None:
        print("Finger IK target not found:", ik_target_name)
        return

    ik_pole_name = "c_"+finger_type+"_pole"+side
    ik_pole = get_pose_bone(ik_pole_name)
    if ik_pole == None:
        print("Finger IK pole not found:", ik_pole_name)
        return

    # Snap IK target
        # constraint support
    constraint, bparent_name, parent_type, valid_constraint = get_active_child_of_cns(ik_target)

    finger3_ik = get_pose_bone("c_"+finger_type+"3_ik"+side)
    if constraint and valid_constraint:
        if parent_type == "bone":
            bone_parent = get_pose_bone(bparent_name)
            ik_target2.matrix = bone_parent.matrix_channel.inverted() @ finger3_ik.matrix
            update_transform()

        elif parent_type == "object":
            obj = bpy.data.objects.get(bparent_name)
            ik_target2.matrix = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ finger3_ik.matrix
            update_transform()

    else:
        ik_target2.matrix = finger3_ik.matrix
        update_transform()

    update_transform()

    # Snap phalanges
    ik_fingers = ["c_"+finger_type+"1_ik"+side, "c_"+finger_type+"2_ik"+side]

        # store current matrices
    fingers_mat = []
    for i, bname in enumerate(ik_fingers):
        b_ik = get_pose_bone(bname)
        fingers_mat.append(b_ik.matrix.copy())

    # Switch prop
    root_finger["ik_tip"] = 0

    for iter in range(0,4):
        for i, bname in enumerate(ik_fingers):
            b_ik = get_pose_bone(bname)
            loc, scale = b_ik.location.copy(), b_ik.scale.copy()
            b_ik.matrix = fingers_mat[i]
            # restore loc and scale, only rotation for better results
            b_ik.location = loc
            b_ik.scale = scale
        # update hack
        update_transform()


    #insert key if autokey enable
    if scn.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_tip"]')

        for bname in ik_fingers+[ik_target.name, ik_target2.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            pb.keyframe_insert(data_path="scale")


def _switch_snap_pin(side, type):
    if type == "leg":
        c_leg_stretch = get_pose_bone("c_stretch_leg"+side)
        if c_leg_stretch == None:
            print("No 'c_stretch_leg' bone found")
            return

        c_leg_pin = get_pose_bone("c_stretch_leg_pin"+side)
        if c_leg_pin == None:
            print("No 'c_leg_stretch_pin' bone found")
            return

        if c_leg_stretch["leg_pin"] == 0.0:
            c_leg_pin.matrix = c_leg_stretch.matrix
            c_leg_stretch["leg_pin"] = 1.0
        else:
            c_leg_stretch["leg_pin"] = 0.0
            c_leg_stretch.matrix = c_leg_pin.matrix

    if type == "arm":
        c_arm_stretch = get_pose_bone("c_stretch_arm"+side)
        if c_arm_stretch == None:
            print("No 'c_stretch_arm' bone found")
            return

        c_arm_pin = get_pose_bone("c_stretch_arm_pin"+side)
        if c_arm_pin == None:
            print("No 'c_stretch_arm_pin' bone found")
            return

        if c_arm_stretch["elbow_pin"] == 0.0:
            c_arm_pin.matrix = c_arm_stretch.matrix
            c_arm_stretch["elbow_pin"] = 1.0
        else:
            c_arm_stretch["elbow_pin"] = 0.0
            c_arm_stretch.matrix =  c_arm_pin.matrix


def _set_picker_camera(self):
    # go to object mode
    bpy.ops.object.mode_set(mode='OBJECT')

    #save current scene camera
    current_cam = bpy.context.scene.camera

    rig = bpy.data.objects[bpy.context.active_object.name]
    bpy.ops.object.select_all(action='DESELECT')
    cam_ui = None
    rig_ui = None
    ui_mesh = None
    char_name_text = None

    for child in rig.children:
        if child.type == 'CAMERA' and 'cam_ui' in child.name:
            cam_ui = child
        if child.type == 'EMPTY' and 'rig_ui' in child.name:
            rig_ui = child
            for _child in rig_ui.children:
                if _child.type == 'MESH' and 'mesh' in _child.name:
                    ui_mesh = _child

    # if the picker is not there, escape
    if rig_ui == None and rig.proxy == None:
        self.report({'INFO'}, 'No picker found, click "Add Picker" to add one.')
        return

    # ui cam not found, add one
    active_obj_name = bpy.context.active_object.name
    if not cam_ui:
        bpy.ops.object.camera_add(align="VIEW", enter_editmode=False, location=(0, 0, 0), rotation=(0, 0, 0))
        # set cam data
        bpy.context.active_object.name = "cam_ui"
        cam_ui = bpy.data.objects["cam_ui"]
        cam_ui.data.type = "ORTHO"
        cam_ui.data.display_size = 0.1
        cam_ui.data.show_limits = False
        cam_ui.data.show_passepartout = False
        cam_ui.parent = bpy.data.objects[active_obj_name]

        # set collections
        for col in bpy.data.objects[active_obj_name].users_collection:
            try:
                col.objects.link(cam_ui)
            except:
                pass

    set_active_object(active_obj_name)

    if cam_ui:
        # lock the camera transforms
        #cam_ui.lock_location[0]=cam_ui.lock_location[1]=cam_ui.lock_location[2]=cam_ui.lock_rotation[0]=cam_ui.lock_rotation[1]=cam_ui.lock_rotation[2] = True
        cam_ui.select_set(state=1)
        bpy.context.view_layer.objects.active = cam_ui
        bpy.ops.view3d.object_as_camera()

        # set viewport display options
        #bpy.context.space_data.lock_camera_and_layers = False
        bpy.context.space_data.overlay.show_relationship_lines = False
        bpy.context.space_data.overlay.show_text = False
        bpy.context.space_data.overlay.show_cursor = False
        current_area = bpy.context.area
        space_view3d = [i for i in current_area.spaces if i.type == "VIEW_3D"]
        space_view3d[0].shading.type = 'SOLID'
        space_view3d[0].shading.show_object_outline = False
        space_view3d[0].shading.show_specular_highlight = False
        space_view3d[0].show_gizmo_navigate = False
        space_view3d[0].use_local_camera = True
        bpy.context.space_data.lock_camera = False#unlock camera to view

        rig_ui_scale = 1.0

        if rig_ui:
            rig_ui_scale = rig_ui.scale[0]

        units_scale = bpy.context.scene.unit_settings.scale_length
        fac_ortho = 1.8# * (1/units_scale)

        # Position the camera height to the backplate height
        if ui_mesh:
            vert_pos = [v.co for v in ui_mesh.data.vertices]
            vert_pos = sorted(vert_pos, reverse=False, key=itemgetter(2))
            max1 = ui_mesh.matrix_world @ vert_pos[0]
            max2 = ui_mesh.matrix_world @ vert_pos[len(vert_pos)-1]
            picker_size = (max1-max2).magnitude
            picker_center = (max1 + max2)/2

            # set the camera matrix
            cam_ui.matrix_world = Matrix.Translation(picker_center)
            cam_height = cam_ui.location[2]
            cam_ui.matrix_world = rig.matrix_world @ Matrix.Translation((0, -40, picker_center[2]))
            cam_ui.scale = (1.0,1.0,1.0)
            cam_ui.rotation_euler = (radians(90), 0, 0)

            # set the camera clipping and ortho scale
            bpy.context.evaluated_depsgraph_get().update()
            dist = (cam_ui.matrix_world.to_translation() - picker_center).length
            cam_ui.data.clip_start = dist*0.9
            cam_ui.data.clip_end = dist*1.1
            cam_ui.data.ortho_scale = fac_ortho * picker_size

        #restore the scene camera
        bpy.context.scene.camera = current_cam

    else:
        self.report({'ERROR'}, 'No picker camera found for this rig')

    #back to pose mode
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(state=1)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='POSE')

    # enable the picker addon
    try:
        bpy.context.scene.Proxy_Picker.active = True
    except:
        pass


def project_point_onto_plane(q, p, n):
    n = n.normalized()
    return q - ((q - p).dot(n)) * n


def get_ik_pole_pos(b1, b2, dist):
    plane_normal = (b1.head - b2.tail)
    midpoint = (b1.head + b2.tail) * 0.5
    prepole_dir = b2.head - midpoint
    pole_pos = b2.head + prepole_dir.normalized()
    pole_pos = project_point_onto_plane(pole_pos, b2.head, plane_normal)
    pole_pos = b2.head + ((pole_pos - b2.head).normalized() * (b2.head - b1.head).magnitude * dist)
    return pole_pos


def get_pose_matrix_in_other_space(mat, pose_bone):
    rest = pose_bone.bone.matrix_local.copy()
    rest_inv = rest.inverted()

    if pose_bone.parent and pose_bone.bone.use_inherit_rotation:
        par_mat = pose_bone.parent.matrix.copy()
        par_inv = par_mat.inverted()
        par_rest = pose_bone.parent.bone.matrix_local.copy()

    else:
        par_mat = Matrix()
        par_inv = Matrix()
        par_rest = Matrix()

    smat = rest_inv @ (par_rest @ (par_inv @ mat))


    return smat


def _snap_head(side):
    c_head = get_pose_bone("c_head"+side)
    head_scale_fix = get_pose_bone("head_scale_fix" + side)

    # get the bone parent (constrained) of head_scale_fix
    head_scale_fix_parent = None
    for cns in head_scale_fix.constraints:
        if cns.type == "CHILD_OF" and cns.influence == 1.0:
            head_scale_fix_parent = get_pose_bone(cns.subtarget)

    c_head_loc = c_head.location.copy()

    # matrices evaluations
    c_head_mat = c_head.matrix.copy()
    head_scale_fix_mat = head_scale_fix_parent.matrix_channel.inverted() @ head_scale_fix.matrix_channel

    # switch the prop
    c_head["head_free"] = 0 if c_head["head_free"] == 1 else 1

    # apply the matrices
    # two time because of a dependency lag
    for i in range(0,2):
        update_transform()
        c_head.matrix = head_scale_fix_mat.inverted() @ c_head_mat
        # the location if offset, preserve it
        c_head.location = c_head_loc

    #insert keyframe if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        c_head.keyframe_insert(data_path='["head_free"]')


def set_pos(pose_bone, mat):
    if pose_bone.bone.use_local_location == True:
        pose_bone.location = mat.to_translation()
    else:
        loc = mat.to_translation()

        rest = pose_bone.bone.matrix_local.copy()
        if pose_bone.bone.parent:
            par_rest = pose_bone.bone.parent.matrix_local.copy()
        else:
            par_rest = Matrix()

        q = (par_rest.inverted() @ rest).to_quaternion()
        pose_bone.location = q @ loc


def set_pose_rotation(pose_bone, mat):
    q = mat.to_quaternion()

    if pose_bone.rotation_mode == 'QUATERNION':
        pose_bone.rotation_quaternion = q
    elif pose_bone.rotation_mode == 'AXIS_ANGLE':
        pose_bone.rotation_axis_angle[0] = q.angle
        pose_bone.rotation_axis_angle[1] = q.axis[0]
        pose_bone.rotation_axis_angle[2] = q.axis[1]
        pose_bone.rotation_axis_angle[3] = q.axis[2]
    else:
        pose_bone.rotation_euler = q.to_euler(pose_bone.rotation_mode)



def snap_pos(pose_bone, target_bone):
    # Snap a bone to another bone. Supports child of constraints and parent.
    """
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pos(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')
    """

    # if the pose_bone has direct parent
    if pose_bone.parent:
        # apply double time because of dependecy lag
        pose_bone.matrix = target_bone.matrix
        #update hack
        update_transform()
        # second apply
        pose_bone.matrix = target_bone.matrix
    else:
        # is there a child of constraint attached?
        child_of_cns = None
        if len(pose_bone.constraints) > 0:
            all_child_of_cns = [i for i in pose_bone.constraints if i.type == "CHILD_OF" and i.influence == 1.0 and i.mute == False and i.target]
            if len(all_child_of_cns) > 0:
                child_of_cns = all_child_of_cns[0]# in case of multiple child of constraints enabled, use only the first for now

        if child_of_cns != None:
            if child_of_cns.subtarget != "" and get_pose_bone(child_of_cns.subtarget):
                # apply double time because of dependecy lag
                pose_bone.matrix = get_pose_bone(child_of_cns.subtarget).matrix_channel.inverted() @ target_bone.matrix
                update_transform()
                pose_bone.matrix = get_pose_bone(child_of_cns.subtarget).matrix_channel.inverted() @ target_bone.matrix
            else:
                pose_bone.matrix = target_bone.matrix

        else:
            pose_bone.matrix = target_bone.matrix

def update_transform():
    bpy.ops.transform.rotate(value=0, orient_axis='Z', orient_type='VIEW', orient_matrix=((0.0, 0.0, 0), (0, 0.0, 0.0), (0.0, 0.0, 0.0)), orient_matrix_type='VIEW', mirror=False)

def snap_pos_matrix(pose_bone, target_bone_matrix):
    # Snap a bone to another bone. Supports child of constraints and parent.

    # if the pose_bone has direct parent
    if pose_bone.parent:       
        pose_bone.matrix = target_bone_matrix.copy()        
        update_transform()
    else:
        # is there a child of constraint attached?
        child_of_cns = None
        if len(pose_bone.constraints) > 0:
            all_child_of_cns = [i for i in pose_bone.constraints if i.type == "CHILD_OF" and i.influence == 1.0 and i.mute == False and i.target]
            if len(all_child_of_cns) > 0:
                child_of_cns = all_child_of_cns[0]# in case of multiple child of constraints enabled, use only the first for now

        if child_of_cns:
            if child_of_cns.subtarget != "" and get_pose_bone(child_of_cns.subtarget):              
                pose_bone.matrix = get_pose_bone(child_of_cns.subtarget).matrix_channel.inverted() @ target_bone_matrix                
                update_transform()
            else:
                pose_bone.matrix = target_bone_matrix.copy()
        else:
            pose_bone.matrix = target_bone_matrix.copy()


def snap_rot(pose_bone, target_bone):
    mat = get_pose_matrix_in_other_space(target_bone.matrix, pose_bone)
    set_pose_rotation(pose_bone, mat)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='POSE')


def set_inverse_child(b):
    pbone = bpy.context.active_object.pose.bones[b]
    context_copy = bpy.context.copy()
    context_copy["constraint"] = pbone.constraints["Child Of"]
    bpy.context.active_object.data.bones.active = pbone.bone
    bpy.ops.constraint.childof_set_inverse(context_copy, constraint="Child Of", owner='BONE')


def bake_fk_to_ik_arm(self):
    for f in range(self.frame_start, self.frame_end +1):
        bpy.context.scene.frame_set(f)
        print("baking frame", f)

        fk_to_ik_arm(bpy.context.active_object, self.side)


def fk_to_ik_arm(obj, side):

    arm_fk  = obj.pose.bones[fk_arm[0] + side]
    forearm_fk  = obj.pose.bones[fk_arm[1] + side]
    hand_fk  = obj.pose.bones[fk_arm[2] + side]

    arm_ik = obj.pose.bones[ik_arm[0] + side]
    forearm_ik = obj.pose.bones[ik_arm[1] + side]
    hand_ik = obj.pose.bones[ik_arm[2] + side]
    pole = obj.pose.bones[ik_arm[3] + side]

    # Stretch
    if hand_ik['auto_stretch'] == 0.0:
        hand_fk['stretch_length'] = hand_ik['stretch_length']
    else:
        diff = (arm_ik.length+forearm_ik.length) / (arm_fk.length+forearm_fk.length)
        hand_fk['stretch_length'] *= diff

    #Snap rot
    snap_rot(arm_fk, arm_ik)
    snap_rot(forearm_fk, forearm_ik)
    snap_rot(hand_fk, hand_ik)

    #Snap scale
    hand_fk.scale =hand_ik.scale

    #rot debug
    forearm_fk.rotation_euler[0]=0
    forearm_fk.rotation_euler[1]=0

    #switch
    hand_ik['ik_fk_switch'] = 1.0

    #udpate view   
    bpy.context.view_layer.update()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        #fk chain
        hand_ik.keyframe_insert(data_path='["ik_fk_switch"]')
        hand_fk.keyframe_insert(data_path='["stretch_length"]')
        hand_fk.keyframe_insert(data_path="scale")
        hand_fk.keyframe_insert(data_path="rotation_euler")
        arm_fk.keyframe_insert(data_path="rotation_euler")
        forearm_fk.keyframe_insert(data_path="rotation_euler")

        #ik chain
        hand_ik.keyframe_insert(data_path='["stretch_length"]')
        hand_ik.keyframe_insert(data_path='["auto_stretch"]')
        hand_ik.keyframe_insert(data_path="location")
        hand_ik.keyframe_insert(data_path="rotation_euler")
        hand_ik.keyframe_insert(data_path="scale")
        pole.keyframe_insert(data_path="location")

    # change FK to IK hand selection, if selected
    if hand_ik.bone.select:
        hand_fk.bone.select = True
        hand_ik.bone.select = False


def bake_ik_to_fk_arm(self):
    for f in range(self.frame_start, self.frame_end +1):
        bpy.context.scene.frame_set(f)
        print("baking frame", f)

        ik_to_fk_arm(bpy.context.active_object, self.side)


def ik_to_fk_arm(obj, side):
    arm_fk  = obj.pose.bones[fk_arm[0] + side]
    forearm_fk  = obj.pose.bones[fk_arm[1] + side]
    hand_fk  = obj.pose.bones[fk_arm[2] + side]
    pole_fk = obj.pose.bones[fk_arm[3] + side]

    arm_ik = obj.pose.bones[ik_arm[0] + side]
    forearm_ik = obj.pose.bones[ik_arm[1] + side]
    hand_ik = obj.pose.bones[ik_arm[2] + side]
    pole  = obj.pose.bones[ik_arm[3] + side]

    # reset custom pole angle if any
    if obj.pose.bones.get("c_arm_ik" + side) != None:
        obj.pose.bones["c_arm_ik" + side].rotation_euler[1] = 0.0

    # Stretch
    hand_ik['stretch_length'] = hand_fk['stretch_length']

    # Snap
        # constraint support
    constraint = None
    bparent_name = ""
    parent_type = ""
    valid_constraint = True

    if len(hand_ik.constraints) > 0:
        for c in hand_ik.constraints:
            if not c.mute and c.influence > 0.5 and c.type == 'CHILD_OF':
                if c.target:
                    #if bone
                    if c.target.type == 'ARMATURE':
                        bparent_name = c.subtarget
                        parent_type = "bone"
                        constraint = c
                    #if object
                    else:
                        bparent_name = c.target.name
                        parent_type = "object"
                        constraint = c


    if constraint != None:
        if parent_type == "bone":
            if bparent_name == "":
                valid_constraint = False

    if constraint and valid_constraint:
        if parent_type == "bone":
            bone_parent = bpy.context.object.pose.bones[bparent_name]
            hand_ik.matrix = bone_parent.matrix_channel.inverted()@hand_fk.matrix
        if parent_type == "object":
            bone_parent = bpy.data.objects[bparent_name]
            obj_par = bpy.data.objects[bparent_name]
            hand_ik.matrix = constraint.inverse_matrix.inverted() @obj_par.matrix_world.inverted() @ hand_fk.matrix
    else:
        hand_ik.matrix = hand_fk.matrix

    # Pole target position
    pole_dist = 1.0
    foot_ref = get_data_bone("foot_ref"+side)
    if foot_ref:
        if "ik_pole_distance" in foot_ref.keys():
            pole_dist = foot_ref["ik_pole_distance"]

    pole_pos = get_ik_pole_pos(arm_fk, forearm_fk, pole_dist)
    pole_mat = Matrix.Translation(pole_pos)
    snap_pos_matrix(pole, pole_mat)

    #switch
    hand_ik['ik_fk_switch'] = 0.0

    #update view  
    bpy.context.view_layer.update()  

     #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        #ik chain
        hand_ik.keyframe_insert(data_path='["ik_fk_switch"]')
        hand_ik.keyframe_insert(data_path='["stretch_length"]')
        hand_ik.keyframe_insert(data_path='["auto_stretch"]')
        hand_ik.keyframe_insert(data_path="location")
        hand_ik.keyframe_insert(data_path="rotation_euler")
        hand_ik.keyframe_insert(data_path="scale")
        pole.keyframe_insert(data_path="location")

        #ik controller if any
        if obj.pose.bones.get("c_arm_ik" + side) != None:
            obj.pose.bones["c_arm_ik" + side].keyframe_insert(data_path="rotation_euler", index=1)

        #fk chain
        hand_fk.keyframe_insert(data_path='["stretch_length"]')
        hand_fk.keyframe_insert(data_path="location")
        hand_fk.keyframe_insert(data_path="rotation_euler")
        hand_fk.keyframe_insert(data_path="scale")
        arm_fk.keyframe_insert(data_path="rotation_euler")
        forearm_fk.keyframe_insert(data_path="rotation_euler")

    # change FK to IK hand selection, if selected
    if hand_fk.bone.select:
        hand_fk.bone.select = False
        hand_ik.bone.select = True


def bake_fk_to_ik_leg(self):
    for f in range(self.frame_start, self.frame_end +1):
        bpy.context.scene.frame_set(f)
        print("baking frame", f)

        fk_to_ik_leg(bpy.context.active_object, self.side)


def fk_to_ik_leg(obj, side):
    thigh_fk  = obj.pose.bones[fk_leg[0] + side]
    leg_fk  = obj.pose.bones[fk_leg[1] + side]
    foot_fk  = obj.pose.bones[fk_leg[2] + side]
    toes_fk = obj.pose.bones[fk_leg[3] + side]

    thigh_ik = obj.pose.bones[ik_leg[0] + side]
    leg_ik = obj.pose.bones[ik_leg[1] + side]
    foot_ik = obj.pose.bones[ik_leg[2] + side]
    pole = obj.pose.bones[ik_leg[3] + side]
    toes_ik = obj.pose.bones[ik_leg[4] + side]
    foot_01 = obj.pose.bones[ik_leg[5] + side]
    foot_roll = obj.pose.bones[ik_leg[6] + side]
    footi_rot = obj.pose.bones[ik_leg[7] + side]

    # save the c_thigh_b matrix if any
    c_thigh_b = get_pose_bone("c_thigh_b"+side)
    if c_thigh_b:
        c_thigh_b_matrix = c_thigh_b.matrix.copy()

    # Stretch
    if foot_ik['auto_stretch'] == 0.0:
        foot_fk['stretch_length'] = foot_ik['stretch_length']
    else:
        diff = (thigh_ik.length+leg_ik.length) / (thigh_fk.length+leg_fk.length)

        foot_fk['stretch_length'] *= diff

    # Thigh snap
    snap_rot(thigh_fk, thigh_ik)

    # Leg snap
    snap_rot(leg_fk, leg_ik)

    # foot_fk snap
    snap_rot(foot_fk, footi_rot)
        #scale
    foot_fk.scale =foot_ik.scale

    #Toes snap
    snap_rot(toes_fk, toes_ik)
        #scale
    toes_fk.scale =toes_ik.scale

    #rotation debug
    leg_fk.rotation_euler[0]=0
    leg_fk.rotation_euler[1]=0

     #switch
    foot_ik['ik_fk_switch'] = 1.0

    # udpate hack  
    bpy.context.view_layer.update()

    if c_thigh_b:
        c_thigh_b.matrix = c_thigh_b_matrix.copy()


    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        #fk chain
        foot_ik.keyframe_insert(data_path='["ik_fk_switch"]')
        foot_fk.keyframe_insert(data_path='["stretch_length"]')
        foot_fk.keyframe_insert(data_path="scale")
        foot_fk.keyframe_insert(data_path="rotation_euler")
        thigh_fk.keyframe_insert(data_path="rotation_euler")
        leg_fk.keyframe_insert(data_path="rotation_euler")
        toes_fk.keyframe_insert(data_path="rotation_euler")
        toes_fk.keyframe_insert(data_path="scale")

        #ik chain
        foot_ik.keyframe_insert(data_path='["stretch_length"]')
        foot_ik.keyframe_insert(data_path='["auto_stretch"]')
        foot_ik.keyframe_insert(data_path="location")
        foot_ik.keyframe_insert(data_path="rotation_euler")
        foot_ik.keyframe_insert(data_path="scale")
        foot_01.keyframe_insert(data_path="rotation_euler")
        foot_roll.keyframe_insert(data_path="location")
        toes_ik.keyframe_insert(data_path="rotation_euler")
        toes_ik.keyframe_insert(data_path="scale")
        pole.keyframe_insert(data_path="location")

        #ik angle controller if any
        if obj.pose.bones.get("c_thigh_ik" + side) != None:
            obj.pose.bones["c_thigh_ik" + side].keyframe_insert(data_path="rotation_euler", index=1)

    # change IK to FK foot selection, if selected
    if foot_ik.bone.select:
        foot_fk.bone.select = True
        foot_ik.bone.select = False


def bake_ik_to_fk_leg(self):
    for f in range(self.frame_start, self.frame_end +1):
        bpy.context.scene.frame_set(f)
        print("baking frame", f)

        ik_to_fk_leg(bpy.context.active_object, self.side)


def ik_to_fk_leg(rig, side):
    thigh_fk = get_pose_bone(fk_leg[0] + side)
    leg_fk = get_pose_bone(fk_leg[1] + side)
    foot_fk = get_pose_bone(fk_leg[2] + side)
    toes_fk = get_pose_bone(fk_leg[3] + side)
    pole_fk = get_pose_bone(fk_leg[4] + side)

    thigh_ik = get_pose_bone(ik_leg[0] + side)
    leg_ik = get_pose_bone(ik_leg[1] + side)
    foot_ik = get_pose_bone(ik_leg[2] + side)
    pole_ik = get_pose_bone(ik_leg[3] + side)
    toes_ik = get_pose_bone(ik_leg[4] + side)
    foot_01 = get_pose_bone(ik_leg[5] + side)
    foot_roll = get_pose_bone(ik_leg[6] + side)
    toes_pivot = get_pose_bone("c_toes_pivot"+side)
    ik_offset = get_pose_bone("c_foot_ik_offset"+side)

    # Snap Stretch
    foot_ik['stretch_length'] = foot_fk['stretch_length']

    # reset IK foot_01, toes_pivot, ik_offset, foot_roll
    foot_01.rotation_euler = [0,0,0]
    
    if toes_pivot:
        toes_pivot.rotation_euler = toes_pivot.location = [0,0,0]
    if ik_offset:
        ik_offset.rotation_euler = ik_offset.location = [0,0,0]

    foot_roll.location[0] = 0.0
    foot_roll.location[2] = 0.0

    # reset custom pole angle if any
    if rig.pose.bones.get("c_thigh_ik" + side) != None:
        rig.pose.bones["c_thigh_ik" + side].rotation_euler[1] = 0.0
    
    # save the c_thigh_b matrix if any
    c_thigh_b = get_pose_bone("c_thigh_b"+side)
    if c_thigh_b:
        c_thigh_b_matrix = c_thigh_b.matrix.copy()

    # Snap Toes
    toes_ik.rotation_euler= toes_fk.rotation_euler
    toes_ik.scale = toes_fk.scale
    
    # Child Of constraint or parent cases
    constraint = None
    bparent_name = ""
    parent_type = ""
    valid_constraint = True

    if len(foot_ik.constraints) > 0:
        for c in foot_ik.constraints:
            if not c.mute and c.influence > 0.5 and c.type == 'CHILD_OF':
                if c.target:
                    #if bone
                    if c.target.type == 'ARMATURE':
                        bparent_name = c.subtarget
                        parent_type = "bone"
                        constraint = c
                    #if object
                    else:
                        bparent_name = c.target.name
                        parent_type = "object"
                        constraint = c


    if constraint != None:
        if parent_type == "bone":
            if bparent_name == "":
                valid_constraint = False

    # Snap Foot
    if constraint and valid_constraint:
        if parent_type == "bone":
            bone_parent = get_pose_bone(bparent_name)
            foot_ik.matrix = bone_parent.matrix_channel.inverted() @ foot_fk.matrix
        if parent_type == "object":
            rig = bpy.data.objects[bparent_name]
            foot_ik.matrix = constraint.inverse_matrix.inverted() @ rig.matrix_world.inverted() @ foot_fk.matrix

    else:
        foot_ik.matrix = foot_fk.matrix.copy()
    
    # udpate
    bpy.context.view_layer.update()    
    
    # Snap Pole
    pole_dist = 1.0
    foot_ref = get_data_bone("foot_ref"+side)
    if foot_ref:
        if "ik_pole_distance" in foot_ref.keys():
            pole_dist = foot_ref["ik_pole_distance"]

    pole_pos = get_ik_pole_pos(thigh_fk, leg_fk, pole_dist)
    pole_mat = Matrix.Translation(pole_pos)
    snap_pos_matrix(pole_ik, pole_mat)
    
    #if bpy.context.scene.frame_current == 1:
    #    print(br)
    
    # udpate hack
    update_transform()
    
     # Switch prop
    foot_ik['ik_fk_switch'] = 0.0

    # udpate hack
    update_transform()

     # Restore c_thigh_b matrix if any
    if c_thigh_b:
        c_thigh_b.matrix = c_thigh_b_matrix.copy()

    #update hack
    update_transform()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        #ik chain
        foot_ik.keyframe_insert(data_path='["ik_fk_switch"]')
        foot_ik.keyframe_insert(data_path='["stretch_length"]')        
        foot_ik.keyframe_insert(data_path='["auto_stretch"]')
        foot_ik.keyframe_insert(data_path="location")
        foot_ik.keyframe_insert(data_path="rotation_euler")
        foot_ik.keyframe_insert(data_path="scale")
        foot_01.keyframe_insert(data_path="rotation_euler")
        foot_roll.keyframe_insert(data_path="location")
        toes_ik.keyframe_insert(data_path="rotation_euler")
        toes_ik.keyframe_insert(data_path="scale")
        pole_ik.keyframe_insert(data_path="location")

        #ik controller if any
        if get_pose_bone("c_thigh_ik" + side):
            get_pose_bone("c_thigh_ik" + side).keyframe_insert(data_path="rotation_euler", index=1)

        #fk chain        
        foot_fk.keyframe_insert(data_path='["stretch_length"]')
        foot_fk.keyframe_insert(data_path="rotation_euler")
        foot_fk.keyframe_insert(data_path="scale")
        thigh_fk.keyframe_insert(data_path="rotation_euler")
        leg_fk.keyframe_insert(data_path="rotation_euler")
        toes_fk.keyframe_insert(data_path="rotation_euler")
        toes_fk.keyframe_insert(data_path="scale")
        
        
    # change IK to FK foot selection, if selected
    if foot_fk.bone.select:
        foot_fk.bone.select = False
        foot_ik.bone.select = True


def _arp_snap_pole(ob, side, bone_type):
    if get_pose_bone('c_' + bone_type + '_pole' + side) != None:
        pole = get_pose_bone('c_' + bone_type + '_pole' + side)


        if "pole_parent" in pole.keys():
            # save the pole matrix
            pole_mat = pole.matrix.copy()

            # switch the property
            if pole["pole_parent"] == 0:
                pole["pole_parent"] = 1
            else:
                pole["pole_parent"] = 0

            #update view
            update_transform()

            # are constraints there?
            cons = [None, None]
            for cns in pole.constraints:
                if cns.name == "Child Of_local":
                    cons[0] = cns
                if cns.name == "Child Of_global":
                    cons[1] = cns


            # if yes, set parent inverse
            if cons[0] != None and cons[1] != None:
                if pole["pole_parent"] == 0:
                    pole.matrix = get_pose_bone(cons[1].subtarget).matrix_channel.inverted() @ pole_mat
                    #pole.matrix = get_pose_bone(cons[1].subtarget).matrix.inverted()


                if pole["pole_parent"] == 1:
                    pole.matrix = get_pose_bone(cons[0].subtarget).matrix_channel.inverted() @ pole_mat

        else:
            print("No pole_parent poprerty found")

    else:
        print("No c_leg_pole found")


def get_active_child_of_cns(bone):
    constraint = None
    bparent_name = ""
    parent_type = ""
    valid_constraint = True

    if len(bone.constraints) > 0:
        for c in bone.constraints:
            if not c.mute and c.influence > 0.5 and c.type == 'CHILD_OF':
                if c.target:
                    if c.target.type == 'ARMATURE':# bone
                        bparent_name = c.subtarget
                        parent_type = "bone"
                        constraint = c
                    else:# object
                        bparent_name = c.target.name
                        parent_type = "object"
                        constraint = c

    if constraint:
        if parent_type == "bone":
            if bparent_name == "":
                valid_constraint = False

    return constraint, bparent_name, parent_type, valid_constraint


def ik_to_fk_finger(root_finger, side):
    finger_type = None
    rig = bpy.context.active_object

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break

    ik_target_name = ""
    ik_tip = root_finger["ik_tip"]

    if ik_tip == 1:# ik1
        ik_target_name = "c_"+finger_type+"_ik"+side
    elif ik_tip == 0:# ik2
        ik_target_name = "c_"+finger_type+"_ik2"+side

    ik_target = get_pose_bone(ik_target_name)
    if ik_target == None:
        print("Finger IK target not found:", ik_target_name)
        return

    ik_pole_name = "c_"+finger_type+"_pole"+side
    ik_pole = get_pose_bone(ik_pole_name)
    if ik_pole == None:
        print("Finger IK pole not found:", ik_pole_name)
        return

    hand_b = get_data_bone("hand_ref"+side)

    fingers_ik_pole_distance = 1.0
    if "fingers_ik_pole_distance" in hand_b.keys():
        fingers_ik_pole_distance = hand_b["fingers_ik_pole_distance"]

    # Snap IK target
        # constraint support
    constraint, bparent_name, parent_type, valid_constraint = get_active_child_of_cns(ik_target)

    finger3_fk = get_pose_bone("c_"+finger_type+"3"+side)
    if constraint and valid_constraint:
        if parent_type == "bone":
            bone_parent = get_pose_bone(bparent_name)
            ik_target.matrix = bone_parent.matrix_channel.inverted() @ finger3_fk.matrix
            update_transform()
            if ik_tip == 1:
                # set head to tail position
                tail_mat = bone_parent.matrix_channel.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
                ik_target.matrix = tail_mat @ ik_target.matrix

        if parent_type == "object":
            obj = bpy.data.objects.get(bparent_name)
            ik_target.matrix = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ finger3_fk.matrix
            update_transform()
            if ik_tip == 1:
                # set head to tail position
                tail_mat = constraint.inverse_matrix.inverted() @ obj.matrix_world.inverted() @ Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
                ik_target.matrix = tail_mat @ ik_target.matrix
    else:
        ik_target.matrix = finger3_fk.matrix
        update_transform()
        if ik_tip == 1:
            # set head to tail position
            tail_mat = Matrix.Translation((ik_target.y_axis.normalized() * ik_target.length))
            ik_target.matrix = tail_mat @ ik_target.matrix

    update_transform()

    # Snap IK pole
    fk_fingers = ["c_"+finger_type+"1"+side, "c_"+finger_type+"2"+side, "c_"+finger_type+"3"+side]
    ik_fingers = ["c_"+finger_type+"1_ik"+side, "c_"+finger_type+"2_ik"+side, "c_"+finger_type+"3_ik"+side]

    if ik_tip == 0:# only the first two phalanges must be snapped if ik2, since the last is the IK target
        fk_fingers.pop()
        ik_fingers.pop()

    phal2 = get_pose_bone(fk_fingers[1])
        # constraint support
    pole_cns, bpar_name, par_type, valid_cns = get_active_child_of_cns(ik_pole)

    if pole_cns and valid_cns:
        bone_parent = get_pose_bone(bpar_name)
        ik_pole.matrix = bone_parent.matrix_channel.inverted() @ Matrix.Translation((phal2.z_axis.normalized() * phal2.length * 1.3 * fingers_ik_pole_distance)) @ phal2.matrix
    else:
        ik_pole.matrix = Matrix.Translation((phal2.z_axis.normalized() * phal2.length * 1.3 * fingers_ik_pole_distance)) @ phal2.matrix

    ik_pole.rotation_euler = [0,0,0]

    update_transform()

        # phalanges
    for iter in range(0,4):
        for i, bname in enumerate(ik_fingers):
            b_ik = get_pose_bone(bname)
            loc, scale = b_ik.location.copy(), b_ik.scale.copy()
            b_fk = get_pose_bone(fk_fingers[i])
            b_ik.matrix = b_fk.matrix
            # restore loc and scale, only rotation for better results
            b_ik.location = loc
            b_ik.scale = scale
            # update hack
            update_transform()

     # Switch prop
    root_finger['ik_fk_switch'] = 0.0

    # udpate hack
    update_transform()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_fk_switch"]')

        for bname in ik_fingers + fk_fingers + [ik_target.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            pb.keyframe_insert(data_path="scale")


def fk_to_ik_finger(root_finger, side):
    finger_type = None

    for i in fingers_type_list:
        if i in root_finger.name:
            finger_type = i
            break

    ik_target_name = "c_"+finger_type+"_ik"+side
    ik_target = get_pose_bone(ik_target_name)
    if ik_target == None:
        print("Finger IK target not found:", ik_target_name)
        return

    # snap
    fk_fingers = ["c_"+finger_type+"1"+side, "c_"+finger_type+"2"+side, "c_"+finger_type+"3"+side]
    ik_fingers = ["c_"+finger_type+"1_ik"+side, "c_"+finger_type+"2_ik"+side, "c_"+finger_type+"3_ik"+side]

    for i in range(0,2):
        for i, name in enumerate(fk_fingers):
            b_fk = get_pose_bone(name)
            b_ik = get_pose_bone(ik_fingers[i])
            b_fk.matrix = b_ik.matrix

            # udpate hack
            update_transform()

     #switch
    root_finger['ik_fk_switch'] = 1.0

    # udpate hack
    update_transform()

    #insert key if autokey enable
    if bpy.context.scene.tool_settings.use_keyframe_insert_auto:
        root_finger.keyframe_insert(data_path='["ik_fk_switch"]')

        for bname in ik_fingers + fk_fingers + [ik_target.name]:
            pb = get_pose_bone(bname)
            pb.keyframe_insert(data_path="location")
            if pb.rotation_mode != "QUATERNION":
                pb.keyframe_insert(data_path="rotation_euler")
            else:
                pb.keyframe_insert(data_path="rotation_quaternion")
            pb.keyframe_insert(data_path="scale")


def get_data_bone(name):
    return bpy.context.active_object.data.bones.get(name)

def get_pose_bone(name):
    return bpy.context.active_object.pose.bones.get(name)

def _toggle_multi(limb, id, key):
    bone_list = []

    if limb == 'arm':
        bone_list = auto_rig_datas.arm_displayed + auto_rig_datas.fingers_displayed
    if limb == 'leg':
        bone_list = auto_rig_datas.leg_displayed

    if get_pose_bone('c_pos')[key] == 1:
        get_pose_bone('c_pos')[key] = 0
    else:
        get_pose_bone('c_pos')[key] = 1

    for bone in bone_list:

        current_bone = get_data_bone(bone+'_dupli_'+id)
        if current_bone != None:
            arp_layer = current_bone['arp_layer']

            if get_pose_bone('c_pos')[key] == 0:
                current_bone.layers[22] = True
                current_bone.layers[arp_layer] = False
            else:#need to set an active first
                current_bone.layers[arp_layer] = True
                current_bone.layers[22] = False


def is_selected(names, selected_bone_name, startswith=False):
    bone_side = get_bone_side(selected_bone_name)
    if startswith == False:
        if type(names) == list:
            for name in names:
                if not "." in name[-2:]:
                    if name + bone_side == selected_bone_name:
                        return True
                else:
                    if name[-2:] == ".x":
                        if name[:-2] + bone_side == selected_bone_name:
                            return True
        elif names == selected_bone_name:
            return True
    else:#startswith
        if type(names) == list:
            for name in names:
                if selected_bone_name.startswith(name):
                    return True
        else:
            return selected_bone_name.startswith(names)
    return False


def is_selected_prop(pbone, prop_name):
    if pbone.bone.keys():
        if prop_name in pbone.bone.keys():
            return True


def _add_layer_set(self):
    rig = bpy.context.active_object
    
    new_set = rig.layers_set.add()
    new_set.name = 'LayerSet'
    
    for layidx, lay in enumerate(rig.data.layers):
        if lay:
            new_layer = new_set.layers.add()
            new_layer.idx = layidx
    
    rig.layers_set_idx = len(rig.layers_set)-1
    
        
def _remove_layer_set(self):
    rig = bpy.context.active_object
    
    rig.layers_set.remove(rig.layers_set_idx)
    if rig.layers_set_idx > len(rig.layers_set)-1:
        rig.layers_set_idx = len(rig.layers_set)-1
    
    
    
# Rig UI Panels ##################################################################################################################
class ARP_PT_rig_ui(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"
    bl_label = "Rig Main Properties"
    bl_idname = "ARP_PT_rig_ui"

    @classmethod
    def poll(self, context):
        if context.mode != 'POSE':
            return False
        else:
            if context.active_object.data.get("rig_id") != None:
                return True


    def draw(self, context):
        layout = self.layout
        scn = bpy.context.scene
        rig = context.active_object
        
        # Layers display
        row = layout.row()
        row.prop(scn, "expand_ui_layers", icon="TRIA_DOWN" if scn.expand_ui_layers else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Controllers Layers Set:")
        if scn.expand_ui_layers:
            row = layout.row(align=True)
            row.template_list("ARP_UL_layers_set_list", "", rig, "layers_set", rig, "layers_set_idx", rows=5)
            col = row.column(align=True)
            col.operator(ARP_OT_layers_set_add.bl_idname, text="", icon="ADD")
            col.operator(ARP_OT_layers_set_remove.bl_idname, text="", icon="REMOVE")
            col.separator()
            col.menu("ARP_MT_layers_set_menu", icon='DOWNARROW_HLT', text="")
            col.separator()
            col.operator(ARP_OT_layers_set_move.bl_idname, text="", icon="TRIA_UP").direction = 'UP'
            col.operator(ARP_OT_layers_set_move.bl_idname, text="", icon="TRIA_DOWN").direction = 'DOWN'
            """
            row = layout.row(align=True)
            row.operator(ARP_OT_toggle_layers.bl_idname, text="Main").layer_idx = 0
            row.operator(ARP_OT_toggle_layers.bl_idname, text="2").layer_idx = 1
            row.operator(ARP_OT_toggle_layers.bl_idname, text="3").layer_idx = 2
            row.operator(ARP_OT_toggle_layers.bl_idname, text="4").layer_idx = 3
            row.operator(ARP_OT_toggle_layers.bl_idname, text="5").layer_idx = 4
            layout.separator()
            """
            layout.separator()
            
        pose_bones = context.active_object.pose.bones
        try:
            active_bone = context.active_pose_bone
            selected_bone_name = active_bone.name
        except (AttributeError, TypeError):
            return

        # Get bone side
        bone_side = get_bone_side(selected_bone_name)

       # Leg
        if (is_selected(fk_leg, selected_bone_name) or is_selected(ik_leg, selected_bone_name)):
            
            c_foot_ik = pose_bones["c_foot_ik"+bone_side]
            c_foot_fk = pose_bones["c_foot_ik"+bone_side]
            
           # Stretch length property
            if is_selected(fk_leg, selected_bone_name):
                layout.prop(c_foot_fk, '["stretch_length"]', text="Stretch Length (FK)", slider=True)
                
            if is_selected(ik_leg, selected_bone_name):                
                layout.prop(c_foot_ik, '["stretch_length"]', text="Stretch Length (IK)", slider=True)                
                layout.prop(c_foot_ik, '["auto_stretch"]', text="Auto Stretch", slider=True)
                # 3 bones IK
                if "three_bones_ik" in c_foot_ik.keys():
                    layout.prop(c_foot_ik, '["three_bones_ik"]' , text="3 Bones IK", slider=True)
                    
                    
            # Twist tweak
            c_thighb = get_pose_bone("c_thigh_b"+bone_side)
            if "thigh_twist" in c_thighb.keys():# backward-compatibility
                layout.prop(c_thighb, '["thigh_twist"]', text="Thigh Twist", slider=True)
            
            # Fix_roll prop
            layout.prop(c_foot_ik, '["fix_roll"]', text="Fix Roll", slider=True)

            layout.separator()

            # IK-FK Switch
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator(ARP_OT_switch_snap.bl_idname, text="Snap IK-FK")

            row.prop(scn, "show_ik_fk_advanced", text="", icon="SETTINGS")
            col.prop(c_foot_ik, '["ik_fk_switch"]', text="IK-FK Switch", slider=True)

            if scn.show_ik_fk_advanced:
                col.operator("pose.arp_leg_fk_to_ik_", text="Snap FK > IK")
                col.operator("pose.arp_leg_ik_to_fk_", text="Snap IK > FK")
                col.operator("pose.arp_bake_leg_fk_to_ik", text="Bake FK > IK...")
                col.operator("pose.arp_bake_leg_ik_to_fk", text="Bake IK > FK...")


            if is_selected(ik_leg, selected_bone_name):
                if "pole_parent" in pose_bones["c_leg_pole" + bone_side].keys():
                    # IK Pole parent
                    col = layout.column(align=True)
                    op = col.operator("pose.arp_snap_pole", text = "Snap Pole Parent")
                    col.prop(pose_bones["c_leg_pole" + bone_side], '["pole_parent"]', text="Pole Parent", slider=True)

            # Pin Snap
            layout.separator()
            col = layout.column(align=True)
            p = col.operator("pose.arp_snap_pin", text="Snap Pinning")
            # Pinning
            col.prop(pose_bones["c_stretch_leg"+ bone_side], '["leg_pin"]', text="Knee Pinning", slider=True)


        # Arm
        if is_selected(fk_arm, selected_bone_name) or is_selected(ik_arm, selected_bone_name):

           # Stretch length property
            if is_selected(fk_arm, selected_bone_name):
                layout.prop(pose_bones["c_hand_fk" + bone_side], '["stretch_length"]', text="Stretch Length (FK)", slider=True)
            if is_selected(ik_arm, selected_bone_name):
                layout.prop(pose_bones["c_hand_ik" + bone_side], '["stretch_length"]', text="Stretch Length (IK)", slider=True)
                # Auto_stretch ik
                layout.prop(pose_bones["c_hand_ik" + bone_side], '["auto_stretch"]', text="Auto Stretch", slider=True)
                
            # Twist tweak
            c_shoulder = get_pose_bone("c_shoulder"+bone_side)
            if "arm_twist" in c_shoulder.keys():# backward-compatibility
                layout.prop(c_shoulder, '["arm_twist"]', text="Arm Twist", slider=True)

            layout.separator()            
            
            # IK-FK Switch
            col = layout.column(align=True)
            row = col.row(align=True)
            row.operator(ARP_OT_switch_snap.bl_idname, text="Snap IK-FK")

            row.prop(scn, "show_ik_fk_advanced", text="", icon="SETTINGS")
            col.prop(pose_bones["c_hand_ik" + bone_side], '["ik_fk_switch"]', text="IK-FK Switch", slider=True)

            if scn.show_ik_fk_advanced:
                col.operator("pose.arp_arm_fk_to_ik_", text="Snap FK > IK")
                col.operator("pose.arp_arm_ik_to_fk_", text="Snap IK > FK")
                col.operator("pose.arp_bake_arm_fk_to_ik", text="Bake FK > IK...")
                col.operator("pose.arp_bake_arm_ik_to_fk", text="Bake IK > FK...")


            if is_selected(ik_arm, selected_bone_name):
                # IK Pole parent
                if "pole_parent" in pose_bones["c_arms_pole" + bone_side].keys():
                    col = layout.column(align=True)
                    op = col.operator("pose.arp_snap_pole", text = "Snap Pole Parent")
                    col.prop(pose_bones["c_arms_pole" + bone_side], '["pole_parent"]', text="Pole Parent", slider=True)

            # Pin Snap
            layout.separator()
            col = layout.column(align=True)
            p = col.operator("pose.arp_snap_pin", text="Snap Pinning")
            # Pinning
            layout.prop(pose_bones["c_stretch_arm"+ bone_side], '["elbow_pin"]', text="Elbow Pinning", slider=True)

        # Eye Aim
        if is_selected(eye_aim_bones, selected_bone_name):
            layout.prop(pose_bones["c_eye_target" + bone_side[:-2] + '.x'], '["eye_target"]', text="Eye Target", slider=True)


        # Auto-eyelid
        for eyel in auto_eyelids_bones:
            if is_selected(eyel + bone_side, selected_bone_name):
                eyeb = pose_bones["c_eye" + bone_side]
                #retro compatibility, check if property exists
                if len(eyeb.keys()) > 0:
                    if "auto_eyelid" in eyeb.keys():
                        layout.separator()
                        layout.prop(pose_bones["c_eye" + bone_side], '["auto_eyelid"]', text="Auto-Eyelid", slider=True)


        # Fingers
        if is_selected(fingers_start, selected_bone_name, startswith=True):
            finger_type = None
            for type in fingers_type_list:
                if type in selected_bone_name:
                    finger_type = type
                    break

            layout.label(text=finger_type.title()+" "+bone_side+":")

            finger_root = get_pose_bone("c_"+finger_type+"1_base"+bone_side)

            # Fingers IK-FK switch
            if "ik_fk_switch" in finger_root.keys():
                col = layout.column(align=True)
                col.operator(ARP_OT_switch_snap.bl_idname, text="Snap IK-FK")
                col.prop(finger_root, '["ik_fk_switch"]', text="IK-FK", slider=True)
                row = col.row(align=True).split(factor=0.7, align=True)
                btn = row.operator(ARP_OT_switch_all_fingers.bl_idname, text="Snap All to IK")
                btn.state = "IK"
                btn.side = bone_side
                btn = row.operator(ARP_OT_switch_all_fingers.bl_idname, text="FK")
                btn.state = "FK"
                btn.side = bone_side

                col = layout.column(align=True)
                col.operator(ARP_OT_switch_snap_root_tip.bl_idname, text="Snap Root-Tip")
                col.prop(finger_root, '["ik_tip"]', text="IK Root-Tip", slider=True)
                row = col.row(align=True).split(factor=0.7, align=True)
                btn = row.operator(ARP_OT_switch_snap_root_tip_all.bl_idname, text="Snap All to Root")
                btn.state = "ROOT"
                btn.side = bone_side
                btn = row.operator(ARP_OT_switch_snap_root_tip_all.bl_idname, text="Tip")
                btn.state = "TIP"
                btn.side = bone_side

                col.separator()

                col.operator(ARP_OT_free_parent_ik_fingers.bl_idname, text="Toggle All IK Parents").side = bone_side

                layout.separator()

            # Fingers Bend
            layout.prop(finger_root, '["bend_all"]', text="Bend All Phalanges", slider=True)


        # Fingers Grasp
        if is_selected(hands_ctrl, selected_bone_name):
            if 'fingers_grasp' in pose_bones["c_hand_fk" + bone_side].keys():#if property exists, retro-compatibility check
                layout.label(text="Fingers:")
                layout.prop(pose_bones["c_hand_fk" + bone_side],  '["fingers_grasp"]', text = "Fingers Grasp", slider = False)


        # Pinning
        pin_arms = ["c_stretch_arm_pin", "c_stretch_arm_pin", "c_stretch_arm", "c_stretch_arm"]
        if is_selected(pin_arms, selected_bone_name):
            if (selected_bone_name[-2:] == ".l"):
                layout.label(text="Left Elbow Pinning")
                layout.prop(pose_bones["c_stretch_arm"+ bone_side], '["elbow_pin"]', text="Elbow pinning", slider=True)
            if (selected_bone_name[-2:] == ".r"):
                layout.label(text="Right Elbow Pinning")
                layout.prop(pose_bones["c_stretch_arm"+bone_side], '["elbow_pin"]', text="Elbow pinning", slider=True)

        pin_legs = ["c_stretch_leg_pin", "c_stretch_leg_pin", "c_stretch_leg", "c_stretch_leg"]


        if is_selected(pin_legs, selected_bone_name):
            if (selected_bone_name[-2:] == ".l"):
                layout.label(text="Left Knee Pinning")
                layout.prop(pose_bones["c_stretch_leg"+bone_side], '["leg_pin"]', text="Knee pinning", slider=True)
            if (selected_bone_name[-2:] == ".r"):
                layout.label(text="Right Knee Pinning")
                layout.prop(pose_bones["c_stretch_leg"+bone_side], '["leg_pin"]', text="Knee pinning", slider=True)


        # Head Lock
        if is_selected('c_head' + bone_side, selected_bone_name):
            head_pbone = pose_bones['c_head' + bone_side]
            if len(head_pbone.keys()) > 0:
                if 'head_free' in head_pbone.keys():#retro compatibility
                    col = layout.column(align=True)
                    op = col.operator(ARP_OT_snap_head.bl_idname, text="Snap Head Lock")
                    col.prop(context.active_pose_bone, '["head_free"]', text = 'Head Lock', slider = True)
            neck_pbone = pose_bones.get("c_neck"+bone_side)
            if len(neck_pbone.keys()) > 0:
                if "neck_global_twist" in neck_pbone.keys():
                    col = layout.column(align=True)
                    col.prop(neck_pbone, '["neck_global_twist"]', text = 'Neck Global Twist', slider = False)

        # Neck
        if selected_bone_name.startswith("c_neck") or selected_bone_name.startswith("c_subneck_"):
            if len(active_bone.keys()):
                if "neck_twist" in active_bone.keys():
                    col = layout.column(align=True)
                    neck_pbone = pose_bones.get("c_neck"+bone_side)
                    if len(neck_pbone.keys()) > 0:
                        if "neck_global_twist" in neck_pbone.keys():
                            col = layout.column(align=True)
                            col.prop(neck_pbone, '["neck_global_twist"]', text = 'Neck Global Twist', slider = False)

                    col.prop(active_bone, '["neck_twist"]', text = 'Neck Twist', slider = False)


        # Lips Retain
        if is_selected('c_jawbone' + bone_side, selected_bone_name):
            if len(pose_bones['c_jawbone' + bone_side].keys()) > 0:
                if 'lips_retain' in pose_bones['c_jawbone' + bone_side].keys():#retro compatibility
                    layout.prop(pose_bones["c_jawbone" + bone_side], '["lips_retain"]', text = 'Lips Retain', slider = True)
                    layout.prop(pose_bones["c_jawbone" + bone_side], '["lips_stretch"]', text = 'Lips Stretch', slider = True)

        # Spline IK
        if is_selected("c_spline_", selected_bone_name, startswith=True) or is_selected_prop(active_bone, "arp_spline"):
            layout.label(text="Spline IK")
            spline_name = selected_bone_name.split('_')[1]

            if len(active_bone.keys()):
                if "twist" in active_bone.keys():
                    layout.prop(active_bone, '["twist"]', text="Twist")

            spline_root = get_pose_bone("c_" + spline_name + "_root" + bone_side)

            if spline_root:
                str = "None"
                if spline_root["y_scale"] == 1:
                    str = "Fit Curve"
                elif spline_root["y_scale"] == 2:
                    str = "Bone Original"
                layout.label(text="Y Scale:")
                layout.prop(spline_root, '["y_scale"]', text = str)

                str = "None"
                if spline_root["stretch_mode"] == 1:
                    str = "Bone Original"
                elif spline_root["stretch_mode"] == 2:
                    str = "Inverse Scale"
                elif spline_root["stretch_mode"] == 3:
                    str = "Volume Preservation"
                layout.label(text="XZ Scale:")
                layout.prop(spline_root, '["stretch_mode"]', text = str)

                layout.prop(spline_root, '["volume_variation"]', text = 'Volume Variation')


        # Reset
        layout.separator()
        col = layout.column(align=True)
        col.operator(ARP_OT_reset_script.bl_idname, text="Reset All Pose")

        # Multi Limb display
        if is_selected('c_pos', selected_bone_name):
            layout.label(text='Multi-Limb Display:')
            #look for multi limbs

            if len(get_pose_bone('c_pos').keys()) > 0:
                for key in get_pose_bone('c_pos').keys():

                    if 'leg' in key or 'arm' in key:
                        row = layout.column(align=True)
                        b = row.operator('id.toggle_multi', text=key)
                        if 'leg' in key:
                            b.limb = 'leg'
                        if 'arm' in key:
                            b.limb = 'arm'
                        b.id = key[-5:]
                        b.key = key
                        row.prop(pose_bones['c_pos'], '["'+key+'"]', text=key)

            else:
                layout.label(text='No Multiple Limbs')

        # Set Picker Camera
        layout.separator()
        row = layout.row()
        row.prop(scn, "expand_ui_picker", icon="TRIA_DOWN" if scn.expand_ui_picker else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Picker Camera:")
        if scn.expand_ui_picker:
            col = layout.column(align=True)
            col.operator(ARP_OT_set_picker_camera_func.bl_idname, text="Set Picker Cam")#, icon = 'CAMERA_DATA')




###########  REGISTER  ##################
classes = (ARP_OT_snap_head, ARP_OT_set_picker_camera_func, ARP_OT_toggle_multi, ARP_OT_arp_snap_pole, ARP_OT_arm_bake_fk_to_ik, ARP_OT_arm_fk_to_ik, ARP_OT_arm_bake_ik_to_fk, ARP_OT_arm_ik_to_fk, ARP_OT_switch_snap, ARP_OT_leg_fk_to_ik, ARP_OT_leg_bake_fk_to_ik,  ARP_OT_leg_ik_to_fk, ARP_OT_leg_bake_ik_to_fk, ARP_PT_rig_ui, ARP_OT_snap_pin, ARP_OT_reset_script, ARP_OT_toggle_layers, ARP_OT_free_parent_ik_fingers, ARP_OT_switch_all_fingers, ARP_OT_switch_snap_root_tip, ARP_OT_switch_snap_root_tip_all, ARP_UL_layers_set_list, LayerIdx, LayerSet, ARP_OT_layers_set_add, ARP_OT_layers_set_remove, ARP_OT_layers_set_move, ARP_MT_layers_set_menu, ARP_OT_layers_set_all_toggle, ARP_OT_layers_add_defaults)

def update_arp_tab():
    try:
        bpy.utils.unregister_class(ARP_PT_rig_ui)
    except:
        pass
    ARP_PT_rig_ui.bl_category = bpy.context.preferences.addons[__package__].preferences.arp_tools_tab_name
    bpy.utils.register_class(ARP_PT_rig_ui)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    update_arp_tab()
    
    bpy.types.Object.layers_set = bpy.props.CollectionProperty(type=LayerSet, name="Layers Set", description="List of bones layers set", override={'LIBRARY_OVERRIDABLE', 'USE_INSERTION'})
    bpy.types.Object.layers_set_idx = bpy.props.IntProperty(name="List Index", description="Index of the layers set list", default=0, override={'LIBRARY_OVERRIDABLE'})
    bpy.types.Scene.show_ik_fk_advanced = bpy.props.BoolProperty(name="Show IK-FK operators", description="Show IK-FK manual operators", default=False)
    bpy.types.Scene.expand_ui_layers = bpy.props.BoolProperty(name="", description="Expand UI", default=False)
    bpy.types.Scene.expand_ui_picker = bpy.props.BoolProperty(name="", description="Expand UI", default=True)



def unregister():
    from bpy.utils import unregister_class

    for cls in classes:
        unregister_class(cls)

    del bpy.types.Object.layers_set
    del bpy.types.Object.layers_set_idx
    del bpy.types.Scene.show_ik_fk_advanced
    del bpy.types.Scene.expand_ui_layers
    del bpy.types.Scene.expand_ui_picker