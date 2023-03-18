import bpy, bmesh, math, re, operator, os, difflib, csv
from math import degrees, pi, radians, ceil, sqrt
from bpy.types import Panel, UIList
import mathutils
from mathutils import Vector, Euler, Matrix
from . import auto_rig
from .utils import *

#print ("\n Starting Auto-Rig Pro: Remap... \n")

##########################  CLASSES  ##########################

# BONES COLLECTION CLASS
class ARP_UL_items(UIList):

    @classmethod
    def poll(cls, context):
        return (context.scene.source_action != "" and context.scene.source_rig != "" and context.scene.target_rig != "")

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        split = layout.split(factor=1.0)
        split.prop(item, "source_bone", text="", emboss=False, translate=False)# icon='BONE_DATA')
        split = layout.split(factor=1.0)
        split.prop(item, "name", text="", emboss=False, translate=False)# icon='BONE_DATA')

    def invoke(self, context, event):
        pass


# OTHER CLASSES
class ARP_MT_remap_import(bpy.types.Menu):
    bl_label = "Import built-in presets list"
    
    addon_directory = os.path.dirname(os.path.abspath(__file__))
    fp = addon_directory + "/remap_presets/"
    
    def draw(self, _context):
        layout = self.layout
        layout.operator("arp.import_config_from_path", text="Mixamo FK").filepath = self.fp+"mixamo_fk.bmap"
        layout.operator("arp.import_config_from_path", text="Mixamo IK").filepath = self.fp+"mixamo_ik.bmap"
        layout.operator("arp.import_config_from_path", text="Mixamo Fbx IK").filepath = self.fp+"mixamo_fbx_ik.bmap"
        layout.operator("arp.import_config_from_path", text="Rokoko Legs IK").filepath = self.fp+"rokoko_legs_ik.bmap"
        layout.operator("arp.import_config_from_path", text="Rokoko Legs IK 2").filepath = self.fp+"rokoko_legs_ik_2.bmap"
        layout.operator("arp.import_config_from_path", text="Unity Fbx").filepath = self.fp+"unity_export.bmap"
        layout.operator("arp.import_config_from_path", text="Unreal Mannequin").filepath = self.fp+"unreal_mannequin_remap.bmap"
        
        
class ARP_OT_clear_tweaks(bpy.types.Operator):  
    """Clear interactive tweaks"""

    bl_idname = "arp.retarget_clear_tweaks"
    bl_label = "retarget_clear_tweaks"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.scene.source_rig != "":
            if get_object(context.scene.source_rig):
                return True

    def execute(self, context):        
        try:
            _clear_interactive_tweaks()

        finally:
            pass
        return {'FINISHED'}
        
        
class ARP_OT_synchro_select(bpy.types.Operator):    
    """Select in the bones list the active bone in the viewport"""

    bl_idname = "arp.retarget_synchro_select"
    bl_label = "synchro_select"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == "POSE"

    def execute(self, context):
        scn = context.scene
        try:
            if len(context.selected_pose_bones):
                selected_pbone = context.selected_pose_bones[0]
                for idx, bone_item in enumerate(scn.bones_map):
                    if bone_item.name == selected_pbone.name or bone_item.source_bone == selected_pbone.name:
                        scn.bones_map_index = idx

        finally:
            pass
        return {'FINISHED'}


class ARP_OT_freeze_armature(bpy.types.Operator):
    """Clear animation datas from the armature object and initialized its transforms. Preserve bones animation"""

    bl_idname = "arp.freeze_armature"
    bl_label = "freeze_armature"
    bl_options = {'UNDO'}

    arm : bpy.props.StringProperty(default="")

    @classmethod
    def poll(cls, context):
        if context.scene.source_rig != "":
            if get_object(context.scene.source_rig):
                return True


    def execute(self, context):
        if get_object(context.scene.source_rig) == None:
            message = "Source armature not found"
            print(message)
            self.report({'ERROR'}, message)
            return {'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _freeze_armature(self.arm)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_redefine_rest_pose(bpy.types.Operator):
    """If the source and target armatures have different rest poses, click this button to change the source armature rest pose, so that it looks like the target armature.\nNecessary for accurate retargetting.\nClick Apply to complete"""

    bl_idname = "arp.redefine_rest_pose"
    bl_label = "Use as rest pose:"
    bl_options = {'UNDO'}
    
    rest_pose: bpy.props.EnumProperty(items=(('REST', 'Rest Pose', 'Use the actual rest pose'), ('CURRENT', 'Current Pose', 'Use the current pose as rest pose')), default="REST", name="Use Rest Pose", description="Set the rest pose")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_action != "" and context.scene.source_rig != "" and context.scene.target_rig != "")
        
    def draw(self, context):
        layout = self.layout        
        layout.prop(self, 'rest_pose', expand=True)
        if self.rest_pose == "CURRENT":
            layout.label(text="Use the current pose as rest pose.")
        elif self.rest_pose == "REST":
            layout.label(text="Use the actual rest pose of this armature")
        layout.label(text="The pose will remain editable until the Apply button is clicked. To revert, click Cancel")
        
        
    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, width=450)

    def execute(self, context):

        if not sanity_check(self):
            return {'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            _redefine_rest_pose(self, context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_auto_scale(bpy.types.Operator):

    #tooltip
    """Automatic scale of the source armature to fit the target armature height\nMay not work if the rest position is incorrect, the height is calculated on this basis. Scale manually otherwise."""

    bl_idname = "arp.auto_scale"
    bl_label = "auto_scale"
    bl_options = {'UNDO'}


    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_action != "" and context.scene.source_rig != "" and context.scene.target_rig != "")

    def execute(self, context):

        #save current mode
        current_mode = context.mode
        active_obj_name = None
        try:
            active_obj_name = context.active_object.name
        except:
            pass

        if not sanity_check(self):
            return {'FINISHED'}

        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            #set to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            _auto_scale(self, context)

            #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
                set_active_object(active_obj_name)
                print(active_obj_name)
                bpy.ops.object.mode_set(mode=current_mode)

            except:
                pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_apply_offset(bpy.types.Operator):

    #tooltip
    """Add an offset"""

    bl_idname = "arp.apply_offset"
    bl_label = "apply_offset"
    bl_options = {'UNDO'}


    value : bpy.props.StringProperty(name="offset_value")

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            #save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
            #set to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            _apply_offset(self.value)

            #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
                set_active_object(active_obj.name)
                bpy.ops.object.mode_set(mode=current_mode)

            except:
                pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
        return {'FINISHED'}


class ARP_OT_cancel_redefine(bpy.types.Operator):
    #tooltip
    """Cancel the rest pose edition"""

    bl_idname = "arp.cancel_redefine"
    bl_label = "cancel_redefine"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _cancel_redefine()

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_copy_bone_rest(bpy.types.Operator):

    #tooltip
    """Copy the selected bones rotation from the corresponding bones in the target armature (the bones list must be assigned properly first)"""

    bl_idname = "arp.copy_bone_rest"
    bl_label = "copy_bone_rest"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _copy_bone_rest(self, context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_copy_raw_coordinates(bpy.types.Operator):

    #tooltip
    """Complete the rest pose edition (long animations may take a while to complete)"""

    bl_idname = "arp.copy_raw_coordinates"
    bl_label = "copy_raw_coordinates"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False
        try:
            _copy_raw_coordinates(self, context)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo
            
        return {'FINISHED'}
        

class ARP_OT_pick_object(bpy.types.Operator):

    #tooltip
    """Pick the selected object/bone"""

    bl_idname = "arp.pick_object"
    bl_label = "pick_object"
    bl_options = {'UNDO'}

    action : bpy.props.EnumProperty(
        items=(
                ('pick_source', 'pick_source', ''),
                ('pick_target', 'pick_target', ''),
                ('pick_bone', 'pick_bone', ''),
                ('pick_pole', 'pick_pole', '')
            )
        )

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            _pick_object(self.action)

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_export_config(bpy.types.Operator):
    """Export the current bones list and config to the file path"""
    
    bl_idname = "arp.export_config"
    bl_label = "Export Mapping"
    bl_options = {'UNDO'}
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default='bmap')
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None)
    
    def execute(self, context):
    
        _export_config(self)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = 'remap_preset.bmap'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class ARP_OT_import_config_from_path(bpy.types.Operator):
    """Import bones mapping and settings from file path"""
    bl_idname = "arp.import_config_from_path"
    bl_label = "Import Mapping from Path"
    
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default='bmap')
    
    @classmethod
    def poll(cls, context):
        return (context.active_object != None)
    
    def execute(self, context):
        scn = bpy.context.scene 
        
        _import_config(self)
       
        return {'FINISHED'}
        
        
class ARP_OT_import_config(bpy.types.Operator):
    """Import bones mapping and settings from file"""
    bl_idname = "arp.import_config"
    bl_label = "Import Mapping"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH", default='bmap')

    @classmethod
    def poll(cls, context):
        return (context.active_object != None)
    
    def execute(self, context):
        scn = bpy.context.scene 
        
        _import_config(self)
       
        return {'FINISHED'}

    def invoke(self, context, event):
        self.filepath = 'remap_preset.bmap'
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def check_retargetting_inputs(self):
    context = bpy.context

    def log_error_state():
        try:
            self.safety_check_error = True
        except:
            pass

    # check armature validity
    self.source_rig = get_object(context.scene.source_rig)
    if self.source_rig == None:
        log_error_state()
        self.report({'ERROR'}, 'The source armature cannot be found in the scene')
        return {'FINISHED'}

    self.target_rig = get_object(context.scene.target_rig)
    if self.target_rig == None:
        log_error_state()
        self.report({'ERROR'}, 'The target armature cannot be found in the scene')
        return {'FINISHED'}

    # check the source armature has animation
    if self.source_rig.animation_data.action == None:
        log_error_state()
        self.report({'ERROR'}, 'The source armature has no animation')
        return {'FINISHED'}

    self.frame_start, self.frame_end = self.source_rig.animation_data.action.frame_range

    #check if a Root bone has been assigned    
    if self.unbind == False:
        found_root = False
        for bone in context.scene.bones_map:
            if bone.set_as_root:
                found_root = True

        if not found_root:
            log_error_state()
            self.report({'ERROR'}, 'The root bone must be marked first: "Set as Root"')
            return {'FINISHED'}
    
    # check for invalid arp bones
    target_armature = get_object(context.scene.target_rig).data
    if target_armature.bones.get("c_traj") and target_armature.bones.get("c_pos"):
        print("The target armature is an Auto-Rig Pro armature")
        for b in context.scene.bones_map:
            if target_armature.bones.get(b.name):
                pbone = self.target_rig.pose.bones.get(b.name)
                if not b.name.startswith("c_") and not "cc" in pbone.keys() and not b.name.startswith("cc"):
                    self.invalid_arp_bones = True
                    print("found invalid bones")
                    break
                    
                    
def check_armature_init_transforms(self):
    if self.target_rig == None or self.source_rig == None:
        return
        
    current_selection_name = bpy.context.active_object.name if bpy.context.active_object else None
    
    for arm_obj in [self.target_rig, self.source_rig]:
        # is rotation initialized?        
        for axis in arm_obj.rotation_euler:
            if axis != 0.0:
                if arm_obj == self.source_rig:
                    self.source_rig_is_frozen = False
                elif arm_obj == self.target_rig:
                    self.target_rig_is_frozen = False
                    
        # is scale initialized?        
        for axis in arm_obj.scale:
            if axis != 1.0:
                # scale initialization can be avoided for the source rig
                #if arm_obj == self.source_rig:
                #    self.source_rig_is_frozen = False
                if arm_obj == self.target_rig:
                    self.target_rig_is_frozen = False        
        
        # is the armature object animated?    
        has_action = False
        if arm_obj.animation_data:
            if arm_obj.animation_data.action:
                has_action = True
                
        if has_action:
            for fcurve in arm_obj.animation_data.action.fcurves:
                if not "pose.bones" in fcurve.data_path:
                    if "location"in fcurve.data_path or "rotation" in fcurve.data_path or "scale" in fcurve.data_path:
                        if arm_obj == self.source_rig:
                            self.source_rig_is_frozen = False
                        elif arm_obj == self.target_rig:
                            self.target_rig_is_frozen = False   

        # is the origin normalized?
        if arm_obj == self.source_rig:
            # enter Edit Mode
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            set_active_object(self.source_rig.name)
            
            bpy.ops.object.mode_set(mode='EDIT')
            
            for ebone in self.source_rig.data.edit_bones:
                if (self.source_rig.matrix_world @ ebone.head)[2] < -0.01:
                    self.source_origin_not_normalized = True
                    break
            
    # restore selection
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(current_selection_name)
        

class ARP_OT_bind_only(bpy.types.Operator):
    """Retarget, binding only without baking for quick preview"""

    bl_idname = "arp.retarget_bind_only"
    bl_label = "retarget_bind_only"
    bl_options = {'UNDO'}

    target_rig = None
    source_rig = None
    source_rig_is_frozen = True
    target_rig_is_frozen = True
    invalid_arp_bones = None
    bind_only = True

    unbind : bpy.props.BoolProperty(default=False)
    safety_check_error = False

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_rig != "" and context.scene.target_rig != "")

    def draw(self, context):
        layout = self.layout
        
        if not self.source_rig_is_frozen or not self.target_rig_is_frozen:
            if not self.source_rig_is_frozen:
                layout.label(icon="INFO", text="Source armature transforms will be initialized first: Rotation (0,0,0), Scale (1,1,1)")
            if not self.target_rig_is_frozen:
                layout.label(icon="INFO", text="Target armature transforms will be initialized first: Rotation (0,0,0), Scale (1,1,1)")
                
        if self.invalid_arp_bones:
            layout.separator()
            layout.label(text='Warning!', icon='INFO')
            layout.label(text='The target armature is an Auto-Rig Pro armature, while some bones')
            layout.label(text='in the list are not controller (no "c_" prefix").')
            layout.label(text='Retargetting to non-controller bones can potentially break the rig. Continue?')

        layout.separator()


    def invoke(self, context, event):
        wm = context.window_manager
        check_retargetting_inputs(self)
        check_armature_init_transforms(self)
        if self.invalid_arp_bones or not self.source_rig_is_frozen or not self.target_rig_is_frozen:
            return wm.invoke_props_dialog(self, width=450)
        else:
            if self.safety_check_error:
                return {'FINISHED'}

            return self.execute(context)


    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            #save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
            #save to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            #execute            
            if not self.source_rig_is_frozen:
                _freeze_armature("source")
            if not self.target_rig_is_frozen:
                _freeze_armature("target")
            
            _retarget(self)

            #restore current mode
            try:
                set_active_object(active_obj.name)
            except:
                pass
                #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'

            try:
                bpy.ops.object.mode_set(mode=current_mode)
            except:
                pass


        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


class ARP_OT_retarget(bpy.types.Operator):
    """Retarget the source armature action to the target armature"""

    bl_idname = "arp.retarget"
    bl_label = "Retarget"
    bl_options = {'UNDO'}

    frame_start : bpy.props.IntProperty(default=0, name="Frame Start", description="Bake from this frame")
    frame_end : bpy.props.IntProperty(default=10, name = "Frame End", description="Bake to this frame")
    target_rig = None
    source_rig = None
    source_rig_is_frozen = True
    target_rig_is_frozen = True
    source_origin_not_normalized = False
    force_source_freeze : bpy.props.BoolProperty(default=False, description="Freeze the source armature", name="Freeze Source Armature")

    safety_check_error = False
    invalid_arp_bones = None
    bind_only = False
    unbind : bpy.props.BoolProperty(default=False)

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_rig != "" and context.scene.target_rig != "")

        
    def draw(self, context):
        layout = self.layout
        
        if not self.source_rig_is_frozen or not self.target_rig_is_frozen:
            if not self.source_rig_is_frozen:
                layout.label(icon="INFO", text="Source armature transforms will be initialized first (rotation 0,0,0, scale 1,1,1)")
            if not self.target_rig_is_frozen:
                layout.label(icon="INFO", text="Target armature transforms will be initialized first (rotation 0,0,0, scale 1,1,1)")  
        
        elif self.source_origin_not_normalized:
            layout.label(icon="INFO", text="Source armature origin seems incorrect, freeze it?")
            layout.label(text="(If not sure, first try without freezing. Then if the output animation is offset, enable it)")
            layout.prop(self, "force_source_freeze")
            layout.separator()
        
        row = layout.column().row()
        row.prop(self, 'frame_start')
        row.prop(self, 'frame_end')

        if self.invalid_arp_bones:
            layout.separator()
            layout.label(text='Warning!', icon='INFO')
            layout.label(text='The target armature is an Auto-Rig Pro armature, while some bones')
            layout.label(text='in the list are not controller (no "c_" prefix").')
            layout.label(text='Retargetting to non-controller bones can potentially break the rig. Continue?')

        layout.separator()
        

    def invoke(self, context, event):
        wm = context.window_manager
        self.force_source_freeze = False
        check_retargetting_inputs(self)
        check_armature_init_transforms(self)
        
        if self.safety_check_error:
            return {'FINISHED'}
                
        return wm.invoke_props_dialog(self, width=450)
        

    def execute(self, context):
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:           
            # save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
                
            # save to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            # execute            
            if not self.source_rig_is_frozen or self.force_source_freeze:
                _freeze_armature("source")
            if not self.target_rig_is_frozen:
                _freeze_armature("target")
            
            _retarget(self)

            # restore current mode
            try:
                set_active_object(active_obj.name)
            except:
                pass
                #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'

            try:
                bpy.ops.object.mode_set(mode=current_mode)
            except:
                pass


        finally:            
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}

        
class ARP_OT_build_bones_list(bpy.types.Operator):

    #tooltip
    """Build the source and target bones list, and try to match their names with Auto-Rig Pro or any other armature"""

    bl_idname = "arp.build_bones_list"
    bl_label = "build_bones_list"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object != None and context.scene.source_action != "" and context.scene.source_rig != "" and context.scene.target_rig != "")

    def execute(self, context):
        scn = context.scene
        
        if not sanity_check(self):
            return {'FINISHED'}
        
        if bpy.data.actions.get(scn.source_action) == None:
            self.report({"ERROR"}, "Source action '"+scn.source_action+"' cannot be found, set again the Source Armature object to fix it") 
            return {'FINISHED'}
            
        use_global_undo = context.preferences.edit.use_global_undo
        context.preferences.edit.use_global_undo = False

        try:
            #save current mode
            current_mode = context.mode
            active_obj = None
            try:
                active_obj = context.active_object
            except:
                pass
            #save to object mode
            bpy.ops.object.mode_set(mode='OBJECT')

            #execute function
            _build_bones_list()

            #restore current mode
            try:
                bpy.ops.object.select_all(action='DESELECT')
                set_active_object(active_obj.name)
            except:
                pass
                #restore saved mode
            if current_mode == 'EDIT_ARMATURE':
                current_mode = 'EDIT'

            try:
                bpy.ops.object.mode_set(mode=current_mode)
            except:
                pass

        finally:
            context.preferences.edit.use_global_undo = use_global_undo

        return {'FINISHED'}


############ FUNCTIONS ##############################################################
def sanity_check(self):
    # check if both source and target armature are in the scene
    try:
        set_active_object(bpy.context.scene.source_rig)
        set_active_object(bpy.context.scene.target_rig)
        return True

    except:
        print("Armature not found")
        self.report({'ERROR'}, "Armature not found")
        return False

#Global utilities---------------------------------------------------------
def add_empty(location_empty = (0,0,0), name_string="name_string"):
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, location=(location_empty), rotation=(0, 0, -0))


    bpy.context.object.name = name_string

#Main funcs-------------------------------------------------------------
def _copy_bone_rest(self,context):
    scene = context.scene
    current_frame = bpy.context.scene.frame_current#save current frame
    target_rig = get_object(scene.target_rig)
    source_rig = get_object(scene.source_rig)
    target_bone_name = None

    for bone in context.selected_pose_bones:
        #get the target bone
        for b in scene.bones_map:
            if b.source_bone == bone.name:
                target_bone_name =b.name
                print("Target bone name", target_bone_name)

        if target_bone_name == None:
            continue

        if target_bone_name == "" or target_rig.pose.bones.get(target_bone_name) == None:
            continue

        target_bone = target_rig.pose.bones[target_bone_name]
        vec = (target_bone.tail - target_bone.head)

        #refresh
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)#debug

        empty_loc = (source_rig.matrix_world @ bone.head) + target_rig.matrix_world @ (vec*10000)

        add_empty(location_empty=empty_loc, name_string=bone.name+"_empty_track")

        set_active_object(source_rig.name)
        bpy.ops.object.mode_set(mode='POSE')

        new_cns = bone.constraints.new('DAMPED_TRACK')
        new_cns.name = 'damped_track'
        new_cns.target = get_object(bone.name + "_empty_track")

        #refresh
        bpy.context.scene.frame_set(bpy.context.scene.frame_current)

        # store the bone transforms
        bone_mat = bone.matrix.copy()

        #clear constraints
        cns = bone.constraints.get('damped_track')
        if cns:
            bone.constraints.remove(cns)

        # restore the transforms
        bone.matrix = bone_mat

    #clear empties helpers
    for object in bpy.data.objects:
        if 'empty_track' in object.name:
            bpy.data.objects.remove(object, do_unlink=True)


def _pick_object(action):
    obj = bpy.context.object
    scene = bpy.context.scene

    if action == "pick_source":
        scene.source_rig = obj.name
    if action == "pick_target":
        scene.target_rig = obj.name
    if action == 'pick_bone':
        try:
            pose_bones = obj.pose.bones
            scene.bones_map[scene.bones_map_index].name = bpy.context.active_pose_bone.name
        except:
            print("can't pick bone")

    if action == 'pick_pole':
        try:
            pose_bones = obj.pose.bones
            scene.bones_map[scene.bones_map_index].ik_pole = bpy.context.active_pose_bone.name
        except:
            print("can't pick bone")
            
     
def _freeze_armature(arm_type):
    print("Freeze armature:", arm_type)
    context = bpy.context
    scn = context.scene
    saved_frame = scn.frame_current
    scn.frame_set(context.scene.frame_current)# update hack, not sure it's necessary there

    # Disable auto-keying
    scn.tool_settings.use_keyframe_insert_auto = False

    arm_name = ""
    if arm_type == "source":
        arm_name = scn.source_rig
    elif arm_type == "target":
        arm_name = scn.target_rig
    
    armature = get_object(arm_name)
    
    set_active_object(armature.name)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(armature.name)
   
    base_arm_name = armature.name
    
    # the target armature is not supposed to be animated
    if arm_type == "target":
        if armature.animation_data:
            if armature.animation_data.action:
                armature.animation_data.action = None
                
        # if it's an ARP armature as target: init rot and scale, reset_stretches() et set_inverse()
        is_arp_armature = False
        if armature.data.bones.get("c_traj") and armature.data.bones.get("c_pos"):
            is_arp_armature = True
            
        if is_arp_armature:
            auto_rig.init_arp_scale(armature.name)
            auto_rig._reset_stretches()
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            bpy.ops.object.mode_set(mode='POSE')
            auto_rig._set_inverse()
            bpy.ops.object.mode_set(mode='OBJECT')
            return
                
    # get the current action name
    base_action_name = None   
    if armature.animation_data:
        if armature.animation_data.action:
            base_action_name = armature.animation_data.action.name
        else:
            print("Armature", armature.name, "has no action")
    else:
        print("Armature", armature.name, "has no action")

    # Unparent skinned meshes
    skinned_meshes = []
    parented_meshes = []

        # meshes parented to bones support (no skinning): store meshes
    meshes_parented_to_bones = {}
    for obj in bpy.data.objects:
        if (obj.type != 'MESH' and obj.type != "EMPTY") or is_object_hidden(obj):
            continue
        # obj parented to bone
        if obj.parent:
            if obj.parent == armature and obj.parent_type == "BONE":
                if obj.parent_bone != "":
                    meshes_parented_to_bones[obj.name] = obj.parent_bone

        # skinned meshes
    if len(armature.children):
        for obj in armature.children:
            if obj.type == "MESH":
                obj_mat = obj.matrix_world.copy()
                obj.parent = None
                bpy.context.evaluated_depsgraph_get().update()
                obj.matrix_world = obj_mat
                parented_meshes.append(obj.name)

                for mod in obj.modifiers:
                    if mod.type == "ARMATURE":
                        if mod.object == bpy.context.active_object:
                            skinned_meshes.append(obj.name)


    # Freeze 
    # temporarily zero out location
    saved_loc = armature.location.copy()   
    armature.location = [0,0,0]
   
    # duplicate
    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, 0, 0), "remove_on_cancel":False, "release_confirm":False, "use_accurate":False})
    
    duplicate_armature = bpy.data.objects.get(bpy.context.active_object.name)
    if base_action_name:
        duplicate_armature.animation_data.action.name = base_action_name + "_TEMP_COPY"

    # Constrain to the first armature
    bpy.ops.object.mode_set(mode='POSE')

    for pbone in duplicate_armature.pose.bones:
        cns = pbone.constraints.new('COPY_TRANSFORMS')
        cns.target = get_object(base_arm_name)
        cns.subtarget = pbone.name
        cns.name = "arp_remap_temp"
        
        # add scale constraint to fix scale of armature object leading to incorrect bone scaling
        cns_scale = pbone.constraints.new('COPY_SCALE')
        cns_scale.target = get_object(base_arm_name)
        cns_scale.subtarget = pbone.name
        cns_scale.name = "arp_remap_temp"
        cns_scale.target_space = "POSE"
        cns_scale.owner_space = "WORLD"

    # Set frame 0  
    scn.frame_set(0)

    # Remove keyframes on object level
    if base_action_name:
        fcurves = duplicate_armature.animation_data.action.fcurves

        for fc_index, fc in enumerate(fcurves):
            if not fc.data_path.startswith("pose.bones"):
                if "rotation" in fc.data_path or "location" in fc.data_path or "scale" in fc.data_path:
                    duplicate_armature.animation_data.action.fcurves.remove(fc)
                
    # Store bones X axis
    bpy.ops.object.mode_set(mode='EDIT')
    
    bones_x_axes = {}
    for eb in duplicate_armature.data.edit_bones:
        bones_x_axes[eb.name] = duplicate_armature.matrix_world @ eb.x_axis
       
    # Apply transforms    
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)    
    
    # Ensure bones roll is preserved, applying scale may break it
    bpy.ops.object.mode_set(mode='EDIT')
    
    for eb_name in bones_x_axes:
        saved_x_axis = bones_x_axes[eb_name]  
        align_bone_x_axis(get_edit_bone(eb_name), saved_x_axis)
        
    # Normalize the edit bones rest position (source armature only)
    if arm_type == "source":
        # centered
        # height above the origin
        bound_low = 100000000
        bound_up = -100000000
        bound_right = -10000000000
        bound_left = 1000000000000
        bound_front = 100000000000
        bound_back = -100000000000
        bones_data = {}
        
            # get boundaries  
        for ebone in duplicate_armature.data.edit_bones:
            bones_data[ebone.name] = {"roll": ebone.roll}
            if ebone.head[0] > bound_right:
                bound_right = ebone.head[0]
            if ebone.head[0] < bound_left:
                bound_left = ebone.head[0]
            if ebone.head[1] > bound_back:
                bound_back = ebone.head[1]
            if ebone.head[1] < bound_front:
                bound_front = ebone.head[1]
            if ebone.head[2] < bound_low:
                bound_low = ebone.head[2]
            if ebone.head[2] > bound_up:
                bound_up = ebone.head[2]
                
        center_x = (bound_right + bound_left) / 2
        center_y = (bound_front + bound_back) / 2
        #bound_low -= (bound_up-bound_low)/20# add 5% offset from the ground
        
        print("left", bound_left, "right", bound_right, "front", bound_front, "back", bound_back)
        for ebone in duplicate_armature.data.edit_bones:
            if ebone.use_connect:
                ebone.tail += -Vector((center_x, center_y, bound_low))
            else:
                ebone.head += -Vector((center_x, center_y, bound_low))
                ebone.tail += -Vector((center_x, center_y, bound_low))
            ebone.roll = bones_data[ebone.name]["roll"]# make sure to preserve roll
        
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Bake
    if base_action_name:
        frame_range = duplicate_armature.animation_data.action.frame_range
        bake_anim(frame_start=frame_range[0], frame_end=frame_range[1], only_selected=False, bake_bones=True, bake_object=False)

    # Delete constraints
    for pbone in duplicate_armature.pose.bones:
        for cns in pbone.constraints:
            if cns.name.startswith("arp_remap_temp"):
                pbone.constraints.remove(cns)

    # Delete old armature
    bpy.data.objects.remove(get_object(base_arm_name), do_unlink=True)
    
    duplicate_armature.name = base_arm_name

    # Delete old actions    
    if base_action_name:
        bpy.data.actions.remove(bpy.data.actions.get(base_action_name), do_unlink=True)
        try:
            bpy.data.actions.remove(bpy.data.actions.get(base_action_name + "_TEMP_COPY"), do_unlink=True)
        except:
            pass

    # Rename new action
    if base_action_name:
        duplicate_armature.animation_data.action.name = base_action_name

    # restore frame
    scn.frame_set(saved_frame)    
    
    # restore loc       
    duplicate_armature.location = saved_loc
    
    # Assign back armature modifiers
    for obj_name in skinned_meshes:
        obj = get_object(obj_name)
        for mod in obj.modifiers:
            mod.object = duplicate_armature
    
    # restore parented meshes
    for obj_name in parented_meshes:
        obj = get_object(obj_name)
        obj_mat = obj.matrix_world.copy()
        obj.parent = duplicate_armature
        bpy.context.evaluated_depsgraph_get().update()
        obj.matrix_world = obj_mat

    # meshes object parented to bones support (no skinning): set new bones parent
    bpy.ops.object.mode_set(mode='POSE')
    
    for obj_name in meshes_parented_to_bones:
        obj = get_object(obj_name)
        mat = obj.matrix_world.copy()
        obj.parent = duplicate_armature
        obj.parent_type = "BONE"
        original_parent_name = meshes_parented_to_bones[obj_name]
        obj.parent_bone = original_parent_name
        # bone parent use_relative option must be enabled now
        duplicate_armature.data.bones.get(original_parent_name).use_relative_parent = True
        obj.matrix_world = mat

   
    print("Armature is frozen.")
    

def _auto_scale(self, context):
    scene = context.scene
    source_rig = get_object(scene.source_rig)
    target_rig = get_object(scene.target_rig)
    #switch to rest pose
    source_rig.data.pose_position = 'REST'
    target_rig.data.pose_position = 'REST'
    #update hack
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)

    def get_armature_dim(arm_obj):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(arm_obj.name)
        bpy.ops.object.mode_set(mode='POSE')

        is_arp = False

        # Auto-Rig Pro armature case, exclude the picker bones if any
        if bpy.context.active_object.data.bones.get("Picker"):
            is_arp = True

        # get the source armature dimension
        highest = 0.0
        lowest = 100000000
        for bone in arm_obj.pose.bones:
            if is_arp:
                if bone.head[2] < 0:
                    continue

            z_head = (arm_obj.matrix_world @ bone.head)[2]
            z_tail = (arm_obj.matrix_world @ bone.tail)[2]

            if z_head > highest:
                highest = z_head
            if z_tail > highest:
                highest = z_tail
            if z_head < lowest:
                lowest = z_head
            if z_tail < lowest:
                lowest = z_tail


        dim = highest - lowest
        return dim


    source_dim = get_armature_dim(source_rig)
    print("source dim", source_dim)
    target_dim = get_armature_dim(target_rig)
    print("target dim", target_dim)

    fac = target_dim / source_dim

    get_object(scene.source_rig).scale *= fac * 0.87

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    #switch to pose position
    source_rig.data.pose_position = 'POSE'
    target_rig.data.pose_position = 'POSE'


def _clear_interactive_tweaks():
    print("Clearing interactive tweaks...")
    context = bpy.context
    scn = context.scene    
    target_rig = get_object(scn.target_rig)
    if target_rig == None:
        return
        
    action = None
    if target_rig.animation_data:
        action = target_rig.animation_data.action            
    if action == None:
        return

    fcurves = action.fcurves
    
    for bone_item in scn.bones_map:
        bone_name = bone_item.name
        # clear rot add
        fac = bone_item.rot_add
        if fac != Vector((0,0,0)):
            for idx, add_value in enumerate(fac):
                f = fcurves.find('pose.bones["'+bone_name+'"].rotation_euler', index=idx)
                if f:
                    for key in f.keyframe_points:
                        key.co[1] -= add_value
                        key.handle_left[1] -= add_value
                        key.handle_right[1] -= add_value
                        
        bone_item.rot_add = Vector((0,0,0))                    
                        
        # clear loc add
        fac = bone_item.loc_add
        if fac != Vector((0,0,0)):
            for idx, add_value in enumerate(fac):
                f = fcurves.find('pose.bones["'+bone_name+'"].location', index=idx)
                if f:
                    for key in f.keyframe_points:
                        key.co[1] -= add_value
                        key.handle_left[1] -= add_value
                        key.handle_right[1] -= add_value
    
        bone_item.loc_add = Vector((0,0,0))          
    
    # clear loc mult
        fac = bone_item.loc_mult
        if fac != 0.0:           
            for idx in range(0, 3):
                f = fcurves.find('pose.bones["'+bone_name+'"].location', index=idx)
                if f:
                    for key in f.keyframe_points:
                        key.co[1] *= 1/fac
                        key.handle_left[1] *= 1/fac
                        key.handle_right[1] *= 1/fac
                        
        bone_item.loc_mult = 1.0  
    
    print("Interactive tweaks cleared.")
    
    
def _apply_offset(value, post_baking=False):
    context = bpy.context
    scene = context.scene
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scene.target_rig)

    action = None
    if context.active_object.animation_data:
        action = context.active_object.animation_data.action         
    if action == None:
        return

    fcurves = action.fcurves
    selected_bone_item = scene.bones_map[scene.bones_map_index]

    # Apply  offset
    saved_loc_mult = False
    saved_loc_add = False
    saved_rot_add = False
    
    if "rot" in value:
        fac = scene.additive_rot
        if "-" in value:
            fac = -scene.additive_rot
        if post_baking:# after baking, use the saved value
            fac = selected_bone_item.rot_add# Vector x, y, z: (0.5, 0.1, 1.2)
    
    if "loc" in value and not "loc_mult" in value:
        fac = scene.additive_loc
        if "-" in value:
            fac = -scene.additive_loc
        if post_baking:
            fac = selected_bone_item.loc_add
            
    if "loc_mult" in value:
        fac = scene.loc_mult
        if post_baking:
            fac = selected_bone_item.loc_mult
    
    for f in fcurves:
        bone_name = (f.data_path.split('"')[1])
        # Rotation
        if "rot" in value and not post_baking:# after baking, rather use direct fcurves access for convenience
            if 'rotation' in f.data_path:
                try:
                    if bone_name == scene.bones_map[scene.bones_map_index].name:                       
                        if (f.array_index == 0 and "x" in value) or (f.array_index == 1 and "y" in value) or (f.array_index == 2 and "z" in value):      
                            for key in f.keyframe_points:
                                key.co[1] += fac
                                key.handle_left[1] += fac
                                key.handle_right[1] += fac
                                    
                        # save it in bones_map data
                        if not saved_rot_add:
                            if "x" in value:
                                add_vec = Vector((fac, 0, 0))
                            elif "y" in value:
                                add_vec = Vector((0, fac, 0))
                            elif "z" in value:
                                add_vec = Vector((0, 0, fac))
                            selected_bone_item.rot_add += add_vec
                            saved_rot_add = True
                except:
                    pass

        # Location
        if "loc" in value and not "loc_mult" in value and not post_baking:# after baking, rather use direct fcurves access for convenience
            if 'location' in f.data_path: #location curves only
                try:
                    if bone_name == scene.bones_map[scene.bones_map_index].name:
                        if (f.array_index == 0 and "x" in value) or (f.array_index == 1 and "y" in value) or (f.array_index == 2 and "z" in value):                     
                            for key in f.keyframe_points:
                                key.co[1] += fac
                                key.handle_left[1] += fac
                                key.handle_right[1] += fac  

                        # save it in bones_map data
                        if not saved_loc_add:
                            if "x" in value:
                                add_vec = Vector((fac, 0, 0))
                            elif "y" in value:
                                add_vec = Vector((0, fac, 0))
                            elif "z" in value:
                                add_vec = Vector((0, 0, fac))
                            selected_bone_item.loc_add += add_vec
                            saved_loc_add = True                           
                except:
                    pass

        # Loc Multiply
        if "loc_mult" in value:
            if 'location' in f.data_path:
                try:
                    if bone_name == selected_bone_item.name: 
                        if f.array_index == 0 or f.array_index == 1 or f.array_index == 2:
                            for key in f.keyframe_points:
                                key.co[1] *= fac

                        # save it in bones_map data
                        if not post_baking and not saved_loc_mult:
                            selected_bone_item.loc_mult *= scene.loc_mult
                            saved_loc_mult = True
                except:
                    pass
    
    if post_baking:# set fcurves for additive location and rotation post-baking here
        if value == "rot_add":
            for idx, add_value in enumerate(fac):
                f = fcurves.find('pose.bones["'+selected_bone_item.name+'"].rotation_euler', index=idx)
                if f:
                    for key in f.keyframe_points:
                        key.co[1] += add_value
                        key.handle_left[1] += add_value
                        key.handle_right[1] += add_value
        
        elif value == "loc_add":
            for idx, add_value in enumerate(fac):
                f = fcurves.find('pose.bones["'+selected_bone_item.name+'"].location', index=idx)
                if f:
                    for key in f.keyframe_points:
                        key.co[1] += add_value
                        key.handle_left[1] += add_value
                        key.handle_right[1] += add_value
    
    #update hack
    bpy.ops.object.mode_set(mode='OBJECT')
    #current_frame = bpy.context.scene.frame_current#save current frame
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)

    
def _cancel_redefine():
    scn = bpy.context.scene
    source_rig = get_object(scn.source_rig)
    source_rig_copy =  get_object(scn.source_rig + "_copy")
    
    source_rig.data.pose_position = 'POSE'
    source_rig.animation_data.action = source_rig_copy.animation_data.action
    
    bpy.data.objects.remove(source_rig_copy, do_unlink=True)
    
    target_rig = get_object(scn.target_rig)
    target_rig.data.pose_position = 'POSE'
    
    # update hack
    scn.frame_set(scn.frame_current)
    

def _redefine_rest_pose(self,context):
    scn = context.scene
    source_rig = get_object(scn.source_rig)
    
    # make sure auto keyframe is disabled
    scn.tool_settings.use_keyframe_insert_auto = False

    # ensure the source armature selection
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scn.source_rig)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # if current pose is used, save bone transforms
    current_pose_mat = {}
    if self.rest_pose == 'CURRENT':
        bpy.ops.object.mode_set(mode='POSE')
        for pbone in source_rig.pose.bones:
            current_pose_mat[pbone.name] = pbone.matrix
        
        bpy.ops.object.mode_set(mode='OBJECT')
            
    #set the target in rest pose for correct transform copy
    get_object(scn.target_rig).data.pose_position = 'REST'
    
    bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, -1000, -10000), "constraint_axis":(False, True, False), "mirror":False, "snap":False, "remove_on_cancel":False, "release_confirm":False})    
   
    armature_copy = bpy.data.objects.get(bpy.context.active_object.name)
    
    # rename
    armature_copy.name = scn.source_rig + "_copy"
    armature_copy.animation_data.action.name = scn.source_action + "_COPY"
    
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scn.source_rig)
    
    # reset transforms
    bpy.ops.object.mode_set(mode='POSE')
    bpy.context.active_object.animation_data.action = None
    
    
    for pbone in source_rig.pose.bones:
        if self.rest_pose == 'REST':
            pbone.location = [0,0,0]
            pbone.rotation_euler = [0,0,0]
            pbone.rotation_quaternion = [1,0,0,0]
            pbone.scale = [1,1,1]     
            
        elif self.rest_pose == 'CURRENT':
            pbone.matrix = current_pose_mat[pbone.name]
    
    bpy.ops.pose.select_all(action='DESELECT')

    
def _apply_pose_as_rest(rig):
    # 1.Apply armature modifiers of meshes
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    shape_keys_objects = []
    skinned_objects_dict = {}
            
    for obj in bpy.data.objects:
        if len(obj.modifiers) == 0 or obj.type != "MESH" or is_object_hidden(obj):
            continue
        for modindex, mod in enumerate(obj.modifiers):
            if mod.type != "ARMATURE":
                continue
            if mod.object != rig or mod.object == None:
                continue

            # save the armature modifiers to restore them later
            if obj.name not in skinned_objects_dict:
                skinned_objects_dict[obj.name] = {}
            if mod.object:  # safety check
                skinned_objects_dict[obj.name][mod.name] = [mod.object.name, mod.use_deform_preserve_volume,
                                                            mod.use_multi_modifier, modindex]

            # objects with shape keys are handled separately, since modifiers can't be applied here
            if obj.data.shape_keys:
                if not obj in shape_keys_objects:                  
                    shape_keys_objects.append(obj)
                continue

            # apply modifier         
            set_active_object(obj.name)
            if mod.show_viewport:
                apply_modifier(mod.name)               
   
    # handle objects with shape keys
    for obj_sk in shape_keys_objects:    
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        # duplicate the mesh
        print("duplicate...")
        set_active_object(obj_sk.name)
        current_objs_name = [obj.name for obj in bpy.data.objects]
        duplicate_object()
        dupli_mesh = None

        for obj in bpy.data.objects:
            if obj.name not in current_objs_name:
                dupli_mesh = obj
                break

        # delete shape keys on the original mesh
        print("remove shape keys data...")
        set_active_object(obj_sk.name)
        for i in reversed(range(len(obj_sk.data.shape_keys.key_blocks))):
            print("remove sk", obj_sk.data.shape_keys.key_blocks[i])
            obj_sk.active_shape_key_index = i
            bpy.ops.object.shape_key_remove()

        # apply modifiers
        for mod in obj_sk.modifiers:
            if mod.type != "ARMATURE":
                continue
            if mod.use_multi_modifier:  # do not apply if "multi modifier" is enabled, incorrect result... skip for now
                obj_sk.modifiers.remove(mod)
                continue
            if mod.object == rig:
                print(obj_sk.name + " applied " + mod.name)
                set_active_object(obj_sk.name)
                apply_modifier(mod.name)

        # transfer shape keys
        print("transfer shape keys data...")
        transfer_shape_keys_deformed(dupli_mesh, obj_sk)

        # delete duplicate
        if dupli_mesh:
            bpy.data.objects.remove(dupli_mesh, do_unlink=True)

    # Restore modifiers
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    for obj_name in skinned_objects_dict:
        set_active_object(obj_name)
        _obj = bpy.data.objects[obj_name]
        for mod_name in skinned_objects_dict[obj_name]:
            print("set mod", mod_name)
            new_mod = _obj.modifiers.new(type="ARMATURE", name=mod_name)
            arm_name = skinned_objects_dict[obj_name][mod_name][0]
            preserve_bool = skinned_objects_dict[obj_name][mod_name][1]
            use_multi = skinned_objects_dict[obj_name][mod_name][2]
            new_mod.object = bpy.data.objects[arm_name]
            new_mod.use_deform_preserve_volume = preserve_bool
            new_mod.use_multi_modifier = use_multi

        def get_current_mod_index(mod_name):
            mod_dict = {}
            for i, mod in enumerate(bpy.context.active_object.modifiers):
                mod_dict[mod.name] = i
            return mod_dict[mod_name]

        # re-order the modifiers stack
        for mod_name in skinned_objects_dict[obj_name]:
            target_index = skinned_objects_dict[obj_name][mod_name][3]
            current_index = get_current_mod_index(mod_name)
            move_delta = current_index - target_index
            if move_delta == 0:
                continue
            for i in range(0, abs(move_delta)):
                if move_delta < 0:
                    bpy.ops.object.modifier_move_down(modifier=mod_name)
                else:
                    bpy.ops.object.modifier_move_up(modifier=mod_name)

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(rig.name)
    bpy.ops.object.mode_set(mode='POSE')   
    bpy.ops.pose.armature_apply(selected=False)
    
                    
def _copy_raw_coordinates(self, context):
    scn = bpy.context.scene
    get_object(scn.target_rig).data.pose_position = 'POSE'
    source_rig = get_object(scn.source_rig)
    source_rig_copy =  get_object(scn.source_rig + "_copy")
    _action = source_rig_copy.animation_data.action
    action_name = _action.name
    fcurves = bpy.data.actions[action_name].fcurves
    frame_range = _action.frame_range
    current_frame = scn.frame_current#save current frame        

    # Ensure the source armature selection
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scn.source_rig)
    bpy.ops.object.mode_set(mode='POSE')

    # Apply as rest pose    
    _apply_pose_as_rest(source_rig)
 
    # setup constraints
    source_rig_copy.location = source_rig.location

    print("add constraints...")
    for bone in source_rig.pose.bones:
        cns = bone.constraints.new('COPY_TRANSFORMS')
        cns.name = 'arp_redefine'
        cns.target = source_rig_copy
        cns.subtarget = bone.name

    # Bake
    print("bake...")   
    bake_anim(frame_start=frame_range[0], frame_end=frame_range[1], only_selected=False, bake_bones=True, bake_object=False)

    # delete constraints
    print("delete constraints...")
    for bone in source_rig.pose.bones:
        if len(bone.constraints) > 0:
            for cns in bone.constraints:
                if cns.name == 'arp_redefine':
                    bone.constraints.remove(cns)                    

    # remove base action
    base_action = bpy.data.actions.get(scn.source_action)
    if base_action:
        bpy.data.actions.remove(base_action)
    
    # remove copied action
    copy_action = bpy.data.actions.get(scn.source_action+"_COPY")
    if copy_action:
        bpy.data.actions.remove(copy_action)
    
    # rename new action
    source_rig.animation_data.action.name = scn.source_action
    
    # restore current frame   
    scn.frame_set(current_frame)

    bpy.data.objects.remove(source_rig_copy, do_unlink=True)
    print("Redefining done.")


def node_names_items(self, context):
    # make a list of the names
    items = []

    if context is None:
        return items

    i = 1
    names_string = context.scene.source_nodes_name_string
    if names_string != "":
        for name in names_string.split("+"):
            items.append((name, name, name, i))
            i += 1
    else:
        items.append(("None", "None", "None"))

    return items


def node_axis_items(self, context):
    items=[]
    items.append(('XYZ', 'XYZ', 'Default axis order', 1))
    items.append(('ZYX', 'ZYX', 'Typical', 2))
    items.append(('XZY', 'XZY', 'Less used', 3))

    return items


def _build_bones_list():
    scene = bpy.context.scene
    #select the target rig
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scene.target_rig)

    target_pose_bones = get_object(scene.target_rig).pose.bones
    obj = bpy.context.active_object

    # Get source action bone names
    scene.source_nodes_name_string = ""
    fcurves = bpy.data.actions[scene.source_action].fcurves

    #clear the collection
    if len(scene.bones_map) > 0:
        i = len(scene.bones_map)
        while i >= 0:
            scene.bones_map.remove(i)
            i -= 1

    # create a string containing all the source bones names
    for f in fcurves:
        #bone_name = f.data_path.split('"')[1]
        string = f.data_path[12:]
        bone_name = string.partition('"')[0]
        # add bones names to the string list
        if f.array_index == 0 and 'rotation' in f.data_path:#avoid unwanted iterations
            scene.source_nodes_name_string += bone_name + "+"

    # create the collection items, one per source bone
    sources_nodes_list = [i for i in scene.source_nodes_name_string.split("+") if i != ""]
    sources_nodes_list.sort()# we want it in alphabetical order
    for i in sources_nodes_list:
        item = scene.bones_map.add()
        item.name = 'None'
        item.source_bone = i
        item.axis_order = 'XYZ'
        item.x_inv = False
        item.y_inv = False
        item.z_inv = False

    pose_bones_list = []
    is_arp_armature = False

    if target_pose_bones.get("c_traj") and target_pose_bones.get("c_pos"):
        is_arp_armature = True

    for b in target_pose_bones:
        if is_arp_armature:
            if b.name.startswith("c_") or "cc" in b.keys():# must be a bone controller or custom controller
                pose_bones_list.append(b.name)
        else:
            pose_bones_list.append(b.name)

    # guess linked bones, try to find Auto-Rig Pro bones match, if not lambda name match
    for item in scene.bones_map:
        found = False
        name_low = item.source_bone.lower()

        def get_side(str):
            if 'left' in str or " l " in str or "_l_" in str or "lft" in str or ".l" in str or "-l" in str:
                return ".l"
            elif 'right' in str or " r " in str or "_r_" in str or "rgt" in str or ".r" in str or "-r" in str:
                return ".r"
            return None

        # head
        if 'head' in name_low:
            if target_pose_bones.get("c_head.x"):
                item.name = 'c_head.x'
                found = True
        # neck
        if 'neck' in name_low:
            if target_pose_bones.get("c_neck.x"):
                item.name = 'c_neck.x'
                found = True
        # spine 01
        if 'abdomen' in name_low or 'spine' in name_low:
            if target_pose_bones.get("c_spine_01.x"):
                item.name= 'c_spine_01.x'
                found = True
        # spine 02
        if 'chest' in name_low or 'spine2' in name_low:
            if target_pose_bones.get("c_spine_02.x"):
                item.name='c_spine_02.x'
                found = True
        # root master
        if 'hip' in name_low:
            if target_pose_bones.get("c_root_master.x"):
                item.name='c_root_master.x'
                item.set_as_root = True
                found = True

        if 'tospine' in name_low:
            if target_pose_bones.get("c_root_master.x"):
                item.name='None'
                item.set_as_root = True
                found = True

        if 'pelvis' in name_low:
            if target_pose_bones.get("c_root_master.x"):
                item.name='c_root_master.x'
                item.set_as_root = True                
                found = True

        # shoulder
        if 'collar' in name_low or "shoulder" in name_low or "clavicle" in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_shoulder"+side):
                    item.name='c_shoulder'+side
                    found = True

        # arm
            # special cases
        if 'rshldr' in name_low or ('right' in name_low and 'arm' in name_low and not 'fore' in name_low):
            if target_pose_bones.get("c_arm_fk.r"):
                item.name='c_arm_fk.r'
                found = True

        if 'lshldr' in name_low or ('left' in name_low and 'arm' in name_low and not 'fore' in name_low):
            if target_pose_bones.get("c_arm_fk.l"):
                item.name='c_arm_fk.l'
                found = True

            # more common
        if "upperarm" in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_arm_fk"+side):
                    item.name='c_arm_fk'+side
                    found = True

        # forearms
            # special cases
        if 'rforearm' in name_low or ('right' in name_low and 'forearm' in name_low):
            if target_pose_bones.get("c_forearm_fk.r"):
                item.name='c_forearm_fk.r'
                found = True

        if 'lforearm' in name_low or ('left' in name_low and 'forearm' in name_low):
            if target_pose_bones.get("c_forearm_fk.l"):
                item.name='c_forearm_fk.l'
                found = True

        # more common
        if "forearm" in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_forearm_fk"+side):
                    item.name='c_forearm_fk'+side
                    found = True

        # hand
        if 'hand' in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_hand_fk"+side):
                    item.name='c_hand_fk'+side
                    found = True

        # thigh
        if 'lthigh' in name_low:
            if target_pose_bones.get("c_thigh_fk.l"):
                item.name='c_thigh_fk.l'
                found = True

        if 'rthigh' in name_low:
            if target_pose_bones.get("c_thigh_fk.r"):
                item.name='c_thigh_fk.r'
                found = True

        if 'upleg' in name_low or 'thigh' in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_thigh_fk"+side):
                    item.name='c_thigh_fk'+side
                    found = True

        # calf
        if 'lshin' in name_low:
            if target_pose_bones.get("c_leg_fk.l"):
                item.name='c_leg_fk.l'
                found = True

        if 'rshin' in name_low:
            if target_pose_bones.get("c_leg_fk.r"):
                item.name='c_leg_fk.r'
                found = True

        if ('leg' in name_low and not "upleg" in name_low) or 'shin' in name_low or "calf" in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_leg_fk"+side):
                    item.name='c_leg_fk'+side
                    found = True

        # foot
        if 'foot' in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_foot_fk"+side):
                    item.name='c_foot_fk'+side
                    found = True

        # toes
        if 'toe' in name_low:
            side = get_side(name_low)
            if side:
                if target_pose_bones.get("c_toes_fk"+side):
                    item.name='c_toes_fk'+side
                    found = True


        finger_list = ['thumb', 'index', 'middle', 'ring', 'pinky']
        for fing in finger_list:
            for side in ['l', 'r']:
                for fing_idx in ['1', '2', '3']:
                    full_side = ""
                    if side == 'l':
                        full_side = 'left'
                    if side == 'r':
                        full_side = 'right'

                    # look for lThumb1 or LeftThumb1 or Thumb1_l or Thumb1_left or LeftHandThumb1
                    item_name = item.source_bone.lower()
                    if (fing+fing_idx+'_'+side) in item_name or (side+fing+fing_idx) in item_name or (full_side in item_name and fing+fing_idx in item_name):
                        if target_pose_bones.get('c_'+fing+fing_idx+'.'+side):
                            item.name = 'c_'+fing+fing_idx+'.'+side
                            found = True

        if found == False:
            try:
                #print(item.source_bone,">", difflib.get_close_matches(item.source_bone, pose_bones_list)[0])
                item.name = difflib.get_close_matches(item.source_bone, pose_bones_list)[0]
                #print("adding", item.name)
            except:
                #print(item.source_bone,">None")
                pass

    scene.bones_map_index = 0


def _retarget(self):
    print("\nRetargetting...")

    scene = bpy.context.scene
    context = bpy.context
    source_rig = get_object(scene.source_rig)
    target_rig = get_object(scene.target_rig)

    frame_range = [self.frame_start, self.frame_end]

    #make sure the target armature is visible
    armature_hidden = is_object_hidden(target_rig)
    unhide_object(target_rig)
    current_frame = bpy.context.scene.frame_current#save current frame

    # proxy?
    target_proxy_name = None  
    
    if get_object(scene.target_rig).proxy:
        target_proxy_name = get_object(scene.target_rig).proxy.name
        print("  The target armature is a proxy. Real name = ", target_proxy_name)
        
    overridden_armature = False
    
    if get_object(scene.target_rig).override_library:
        overridden_armature = True
        print("  Overridden armature")

    #select the target rig
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scene.target_rig)

    if target_proxy_name != None:
        if get_object(scene.target_rig + "_local") == None:
            bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
            bpy.context.active_object.name = scene.target_rig + "_local"
        else:
            set_active_object(scene.target_rig + "_local")
        
    if overridden_armature:
        if get_object(scene.target_rig + "_local") == None:
            bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
            bpy.context.active_object.name = scene.target_rig + "_local"
        else:
            set_active_object(scene.target_rig + "_local")

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    set_active_object(scene.target_rig)
    
    # unlink current action if any and reset pose
    bpy.ops.object.mode_set(mode='POSE')
    
    if target_rig.animation_data:
        if target_rig.animation_data.action:
            target_rig.animation_data.action = None
    
    try:
        bpy.ops.arp.reset_pose()
    except:
        pass

    # is it already bound?
    is_already_bound = False
    if len(target_rig.keys()) > 0:
        if "arp_retarget_bound" in target_rig.keys():
            if target_rig["arp_retarget_bound"] == True:
                is_already_bound = True

    if is_already_bound == False and self.unbind == False:
        print("  Binding...")

        bpy.ops.object.mode_set(mode='POSE')

        # set source armature at target armature position
        source_armature_init_pos = get_object(scene.source_rig).location.copy()
        get_object(scene.source_rig).location = get_object(scene.target_rig).location

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        local_armature_name = scene.target_rig + "_local"
        
        if target_proxy_name == None and overridden_armature == False:
            set_active_object(scene.target_rig)
        elif target_proxy_name:
            set_active_object(local_armature_name)
            proxy_armature = get_object(local_armature_name)
            proxy_armature.data = proxy_armature.data.copy()
        elif overridden_armature:
            set_active_object(local_armature_name)
            proxy_armature = get_object(local_armature_name)
            proxy_armature.data = proxy_armature.data.copy()
            bpy.ops.object.make_local(type='SELECT_OBJECT')            
            
        bpy.ops.object.mode_set(mode='EDIT')

        # create a transform dict of target bones
        bones_dict = {}

        for edit_bone in context.object.data.edit_bones:
            bones_dict[edit_bone.name] = source_rig.matrix_world.inverted() @ edit_bone.head.copy(), source_rig.matrix_world.inverted() @ edit_bone.tail.copy(), mat3_to_vec_roll(source_rig.matrix_world.inverted().to_3x3() @ edit_bone.matrix.to_3x3())#edit_bone.roll

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(scene.source_rig)
        bpy.ops.object.mode_set(mode='EDIT')

        print("  Creating Bones...")
        ik_chains = {}
        loc_helper_bones = []
        
        # create bones
        for bone_item in scene.bones_map:
            eb_source_bone = get_edit_bone(bone_item.source_bone)            
        
            if bone_item.name != "" and bone_item.name != "None" and eb_source_bone and bone_item.name in bones_dict:
                # create
                new_bone = source_rig.data.edit_bones.new(bone_item.name+"_REMAP")             
                new_bone.head, new_bone.tail, new_bone.roll = bones_dict[bone_item.name]
                new_bone.parent = eb_source_bone
                set_bone_layer(new_bone, 24)

                # optional: location
                if bone_item.location or bone_item.set_as_root:
                    new_bone_loc_name = bone_item.name+"_LOC"
                    new_bone_loc = source_rig.data.edit_bones.new(new_bone_loc_name)
                    new_bone_loc.head, new_bone_loc.tail, new_bone_loc.roll = new_bone.head.copy(), new_bone.tail.copy(), new_bone.roll
                    loc_helper_bones.append(new_bone_loc_name)
                    # position it at the source bone position
                    translate_vec = (eb_source_bone.head - new_bone.head)
                    new_bone_loc.head += translate_vec
                    new_bone_loc.tail += translate_vec
                    new_bone_loc.roll = new_bone.roll
                    # parent
                    if not bone_item.set_as_root:# root bone must be at root level
                        new_bone_loc.parent = eb_source_bone.parent

                    bpy.ops.object.mode_set(mode='POSE')

                    # add location constraint
                    new_bone_loc_pb = source_rig.pose.bones.get(new_bone_loc_name)
                    cns = new_bone_loc_pb.constraints.new('COPY_LOCATION')
                    cns.target = source_rig
                    cns.subtarget = bone_item.source_bone
                    cns.name += 'REMAP'

                    bpy.ops.object.mode_set(mode='EDIT')

                # optional: ik bones
                if bone_item.ik:
                    eb_source_bone = get_edit_bone(bone_item.source_bone)
                 
                    # add an IK helper bone to bake world coordinates to
                    new_bone_loc_name = bone_item.name+"_IKLOC"
                    new_bone_loc = source_rig.data.edit_bones.new(new_bone_loc_name)
                    new_bone_loc.head, new_bone_loc.tail, new_bone_loc.roll = eb_source_bone.head.copy(), eb_source_bone.head + Vector((0, -0.2, 0)), 0.0
                    set_bone_layer(new_bone_loc, 24)
                    loc_helper_bones.append(new_bone_loc_name)
                    
                    # constraint
                    bpy.ops.object.mode_set(mode='POSE')
                    helper_bone = get_pose_bone(new_bone_loc_name)
                    cns = helper_bone.constraints.new('COPY_LOCATION')
                    cns.target = context.active_object
                    cns.subtarget = bone_item.source_bone                   
                    cns.influence = 1.0
                    cns.name += 'REMAP'
                    
                    bpy.ops.object.mode_set(mode='EDIT')
                    
                    eb_source_bone = get_edit_bone(bone_item.source_bone)
                    
                    if bone_item.ik_pole != "":
                        bone_parent_1 = eb_source_bone.parent

                        # check for missing bones
                        if bone_parent_1 == None:
                            continue# the IK hierarchy is incorrect, the target IK bone has no parent, skip it

                        bone_parent_2 = bone_parent_1.parent

                        if bone_parent_2 == None:
                            continue# the IK hierarchy is incorrect, the IK chain is made of bone only instead of 2, skip it

                        bone_parent_1_name = bone_parent_1.name
                        bone_parent_2_name = bone_parent_2.name

                        #track bone
                        track_bone_name = bone_item.name+"_IK_REMAP"
                        track_bone = context.object.data.edit_bones.new(track_bone_name)
                        set_bone_layer(track_bone, 24)

                        #Check for ik chains straight alignment
                        if bone_parent_1.y_axis.angle(bone_parent_2.y_axis) == 0.0:
                            print("  Warning: Straight IK chain (" + bone_item.name + "), adding offset...")
                            #find foot direction if any
                            bone_vec = None
                            for ed_bone in context.active_object.data.edit_bones:
                                if 'foot' in ed_bone.name.lower():
                                    print("    found a foot bone as reference for offset")
                                    bone_vec = ed_bone.tail - ed_bone.head
                                    break
                            #else, get the current bone vector... not the good way to find the elbow direction :-(
                            if bone_vec == None:
                                bone_vec = get_edit_bone(bone_item.source_bone).tail - get_edit_bone(bone_item.source_bone).head

                            if 'hand' in bone_item.name.lower():
                                bone_vec *= -1

                            #offset the middle position
                            bone_parent_1.head += bone_vec/5
                            bone_parent_2.tail += bone_vec/5

                        #track_bone coords
                        track_bone.head = (bone_parent_1.tail + bone_parent_2.head)/2
                        track_bone.tail = bone_parent_1.head

                        ik_chains[bone_item.source_bone] = [bone_parent_1_name, bone_parent_2_name, bone_item.ik_pole]

                        # Fk pole
                        fk_pole_name = bone_item.name+"_FK_POLE_REMAP"
                        fk_pole = context.object.data.edit_bones.new(fk_pole_name)
                        set_bone_layer(fk_pole, 24)
                        #fk_pole.head = track_bone.tail + (track_bone.tail - track_bone.head)*60
                        fk_pole.head = track_bone.tail + (track_bone.tail-track_bone.head).normalized() * ((bone_parent_1.tail-bone_parent_1.head).magnitude + (bone_parent_2.tail-bone_parent_2.head).magnitude)
                        fk_pole.tail = fk_pole.head + (track_bone.tail - track_bone.head)*2
                        
                        if bone_item.ik_auto_pole:
                            # auto pole, just parent the FK pole to the foot/hand...
                            fk_pole.parent = get_edit_bone(bone_item.source_bone)
                        else:
                            # otherwise parent to the track bone to calculate the IK orientation
                            fk_pole.parent = track_bone
                        
                        
                        # Add constraints
                        bpy.ops.object.mode_set(mode='POSE')
                        p_track_bone = get_pose_bone(track_bone_name)

                        cns = p_track_bone.constraints.new('COPY_LOCATION')
                        cns.target = context.active_object
                        cns.subtarget = bone_parent_2_name
                        cns.name += 'REMAP'

                        cns = p_track_bone.constraints.new('COPY_LOCATION')
                        cns.target = context.active_object
                        cns.subtarget = bone_parent_1_name
                        cns.head_tail = 1.0
                        cns.influence = 0.5
                        cns.name += 'REMAP'

                        cns = p_track_bone.constraints.new('TRACK_TO')
                        cns.target = context.active_object
                        cns.subtarget = bone_parent_1_name
                        cns.influence = 1.0
                        cns.name += 'REMAP'
                        cns.track_axis = "TRACK_Y"
                        cns.up_axis = "UP_Z"
                       
                bpy.ops.object.mode_set(mode='EDIT')    
                
        bpy.ops.object.mode_set(mode='POSE')
        
        
        # Bake location helper bones transforms
        bpy.ops.pose.select_all(action='DESELECT')
            # select
        for pb_name in loc_helper_bones:
            pb = get_pose_bone(pb_name)
            context.object.data.bones.active = pb.bone

            # bake        
        print("  Bake location helpers...")
        bake_anim(frame_start=frame_range[0], frame_end=frame_range[1], only_selected=True, bake_bones=True, bake_object=False, new_action=False)
                                    
            # clear constraints
        for pb_name in loc_helper_bones:
            pb = get_pose_bone(pb_name)
            cns = pb.constraints[0]
            pb.constraints.remove(cns)
        
        # offset helper bones location fcurves
        action_name = source_rig.animation_data.action.name  
        fcurves = bpy.data.actions[action_name].fcurves 
        
        bpy.ops.object.mode_set(mode='EDIT')
        
        for pb_name in loc_helper_bones:
            pb = get_edit_bone(pb_name)
            
            # _LOC bones without parent must inherit the armature scale on animation level
            if pb_name.endswith("_LOC"):
                if pb.parent == None:
                    fc_loc_x = fcurves.find('pose.bones["'+pb_name+'"].location', index=0)
                    fc_loc_y = fcurves.find('pose.bones["'+pb_name+'"].location', index=1)
                    fc_loc_z = fcurves.find('pose.bones["'+pb_name+'"].location', index=2)                
                
                    for i, fc in enumerate([fc_loc_x, fc_loc_y, fc_loc_z]):
                        for key in fc.keyframe_points:                      
                            key.co[1] *= source_rig.scale[i]
                            key.handle_left[1] *= source_rig.scale[i]
                            key.handle_right[1] *= source_rig.scale[i]
            
            # IK
            if pb_name.endswith("_IKLOC"):
                target_name = pb_name.replace("_IKLOC", "")                
                src_name = scene.bones_map[target_name].name          
                remap_bone = get_edit_bone(target_name+"_REMAP")
                #print("OFFSET VEC", remap_bone.name, "-", pb.name)
                offset_vec = remap_bone.matrix.to_translation() - pb.matrix.to_translation()
                
                pb.head += offset_vec
                pb.tail += offset_vec                
              
        
        print("  IK Chains:", ik_chains)
        # store in a prop for access later
        target_rig["arp_retarget_ik_chains"] = ik_chains

        print("  Add constraints...")
        # Add constraints
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        set_active_object(scene.target_rig)
        
        # set IK-FK switch of ARP armature automatically if found
        bpy.ops.object.mode_set(mode='POSE')
        for bone_item in scene.bones_map:
            target_bone = get_pose_bone(bone_item.name)
            if target_bone:
                if target_bone.name.startswith("c_foot_ik") or target_bone.name.startswith("c_hand_ik"):
                    if "ik_fk_switch" in target_bone.keys():
                        target_bone["ik_fk_switch"] = 0.0
                elif target_bone.name.startswith("c_foot_fk") or target_bone.name.startswith("c_hand_fk"):
                    ik_pbone = get_pose_bone(target_bone.name.replace('fk', 'ik'))
                    if ik_pbone:
                        if "ik_fk_switch" in ik_pbone.keys():
                            ik_pbone["ik_fk_switch"] = 1.0
                            
        bpy.ops.object.mode_set(mode='OBJECT')

        # Add IK constraints if necessary
        for bone_item in scene.bones_map:
            if bone_item.ik_create_constraints:
                bpy.ops.object.mode_set(mode='EDIT')
                eb_target_bone = get_edit_bone(bone_item.name)
                bone_parent = eb_target_bone.parent

                if bone_parent == None:
                    continue# the foot has no parent, we can't setup an IK chain

                bone_parent_parent = bone_parent.parent

                if bone_parent_parent == None:
                    continue# the calf has no parent, we can't setup an IK chain

                parent_name = bone_parent.name

                # unparent the IK foot/hand
                eb_target_bone.parent = None

                # create ik constraints
                bpy.ops.object.mode_set(mode='POSE')
                second_ik_bone = get_pose_bone(parent_name)
                ik_cns = second_ik_bone.constraints.get("IK")
                if ik_cns == None:
                    ik_cns = second_ik_bone.constraints.new("IK")

                ik_cns.target = bpy.context.active_object
                ik_cns.subtarget = bone_item.name
                ik_cns.chain_count = 2

        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')


        for bone_item in scene.bones_map:
            if bone_item.name != "" and bone_item.name != "None" and context.object.pose.bones.get(bone_item.name):
                #select it for baking
                pose_bone = context.object.pose.bones[bone_item.name]
                context.object.data.bones.active = pose_bone.bone

                # Add constraints
                # main rotation
                cns = pose_bone.constraints.new('COPY_ROTATION')
                cns.target = source_rig
                cns.subtarget = bone_item.name + "_REMAP"
                cns.name += 'REMAP'

                # optional location
                if bone_item.location or bone_item.set_as_root:
                    cns_loc = pose_bone.constraints.new('COPY_LOCATION')
                    cns_loc.target = source_rig
                    cns_loc.subtarget = bone_item.name + "_LOC"
                    cns_loc.name += '_loc_REMAP'
                    cns_loc.owner_space = cns_loc.target_space = "LOCAL"

                # IK and Set as Root
                if bone_item.ik:
                    cns = pose_bone.constraints.new('COPY_LOCATION')
                    cns.target = source_rig
                   
                    if bone_item.ik:
                        cns.subtarget = bone_item.name + "_IKLOC"
                        
                    cns.name += 'REMAP'

                    if bone_item.ik_pole != "":
                        pole = context.object.pose.bones[bone_item.ik_pole]
                        cns = pole.constraints.new('COPY_LOCATION')
                        cns.target = source_rig
                        cns.subtarget = bone_item.name+"_FK_POLE_REMAP"
                        cns.name += 'REMAP'
                        context.object.data.bones.active = context.object.pose.bones[bone_item.ik_pole].bone

                        if "pole_parent" in pole.keys():
                            pole['pole_parent'] = 0

        bpy.ops.object.mode_set(mode='OBJECT')       
        #print(br)
        # save the bound state in a property
        target_rig["arp_retarget_bound"] = True

    else:
        if self.unbind == False:
            print("Already bound")
            self.report({'INFO'}, "Already bound")

    if self.bind_only == False:
        print("\n  Baking final [" + str(frame_range[0]) + "-" + str(frame_range[1]) + "]")
        
        #bake constraints      
        bake_anim(frame_start=frame_range[0], frame_end=frame_range[1], only_selected=True, bake_bones=True, bake_object=False)
        
        #Change action name
        get_object(scene.target_rig).animation_data.action.name = get_object(scene.source_rig).animation_data.action.name + '_remap'

        # Apply saved Interactive Tweaks:        
        print("  Apply interactive tweaks...")
        current_map_idx = scene.bones_map_index
        for idx in range(0, len(scene.bones_map)):
            scene.bones_map_index = idx
            bone_item = scene.bones_map[idx]
            
            # rot add
            if bone_item.rot_add != Vector((0.0, 0.0, 0.0)):
                _apply_offset("rot_add", post_baking=True)
            
            # loc add
            if bone_item.loc_add != Vector((0.0, 0.0, 0.0)):
                _apply_offset("loc_add", post_baking=True)
            
            # loc mult
            if bone_item.loc_mult != 1.0:
                _apply_offset("loc_mult", post_baking=True)
        
        # restore bones list index
        scene.bones_map_index = current_map_idx

    # is it already bound?
    is_already_bound = False
    if len(target_rig.keys()) > 0:
        if "arp_retarget_bound" in target_rig.keys():
            if target_rig["arp_retarget_bound"] == True:
                is_already_bound = True

    if is_already_bound:
        if (self.bind_only and self.unbind) or (self.bind_only == False):
            print("  Unbinding...")
            
            if len(target_rig.keys()) > 0:
                if "arp_retarget_ik_chains" in target_rig.keys():
                    ik_chains = target_rig["arp_retarget_ik_chains"]
                    found_ik_dict = True

            # Delete remap constraints
            for pose_bone in context.active_object.pose.bones:
                for cns in pose_bone.constraints:
                    if 'REMAP' in cns.name:
                        pose_bone.constraints.remove(cns)
            """
            # set IK-FK switch of ARP armature automatically if found
            for bone_item in scene.bones_map:
                target_bone = get_pose_bone(bone_item.name)
                if target_bone:
                    if target_bone.name.startswith("c_foot_ik") or target_bone.name.startswith("c_hand_ik"):
                        if "ik_fk_switch" in target_bone.keys():
                            target_bone["ik_fk_switch"] = 0.0
                    elif target_bone.name.startswith("c_foot_fk") or target_bone.name.startswith("c_hand_fk"):
                        ik_pbone = get_pose_bone(target_bone.name.replace('fk', 'ik'))
                        if ik_pbone:
                            if "ik_fk_switch" in ik_pbone.keys():
                                ik_pbone["ik_fk_switch"] = 1.0
            """
            try:# it has been already bound
                bpy.ops.pose.select_all(action='DESELECT')
            except:
                pass

            print("  Deleting bones...")
            # Delete helper bones
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            set_active_object(scene.source_rig)            
            bpy.ops.object.mode_set(mode='EDIT')
            
            removed_bones = []
            for ebone in source_rig.data.edit_bones:
                if '_REMAP' in ebone.name or ebone.name.endswith("_LOC") or ebone.name.endswith("_LOC.001") or ebone.name.endswith("_NOROT") or ebone.name.endswith("_IKLOC"):                    
                    removed_bones.append(ebone.name)
                    source_rig.data.edit_bones.remove(ebone)
                     
            print("  Delete helper bones keyframes...")
            action_name = source_rig.animation_data.action.name
            fcurves = bpy.data.actions[action_name].fcurves 
            print("  action name:", action_name)
            for fc in fcurves:
                dp = fc.data_path
                if not dp.startswith("pose.bones"):
                    continue
                bone_name = dp.split('"')[1] 
                #print("  bone name:", bone_name)
                if bone_name in removed_bones or bone_name.endswith("_NOROT"):
                    fcurves.remove(fc)
            
            bpy.ops.object.mode_set(mode='OBJECT')

            # Clean IK poles keyframes when chains are straight            
            print("  Clean IK pole keyframes...")
            if self.bind_only == False:               
                angle_tolerance = 5

                for keyframe in fcurves[0].keyframe_points:
                    cframe = keyframe.co[0]
                    if int(cframe) < self.frame_start or int(cframe) > self.frame_end:
                        continue
                    #check angle at each frames
                    #bpy.context.scene.frame_current = keyframe.co[0]
                    bpy.context.scene.frame_set(cframe)

                    for key, value in ik_chains.items():
                        bone1 = get_object(scene.source_rig).pose.bones[value[0]]
                        bone2 = get_object(scene.source_rig).pose.bones[value[1]]
                        chain_angle = bone1.y_axis.angle(bone2.y_axis)

                        if math.degrees(chain_angle) < angle_tolerance:
                            #remove keyframe, just interpolate
                            pole_bone = get_object(scene.target_rig).pose.bones[value[2]]
                            pole_bone.keyframe_delete(data_path="location")

            
            # restore source rig pos
            try:# for now does not work with "decoupled" retargetting
                get_object(scene.source_rig).location = source_armature_init_pos
            except:
                pass

            #update hack
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.scene.frame_set(bpy.context.scene.frame_current)

            # restore initial armature visibility
            get_object(scene.target_rig).hide_viewport = armature_hidden

            # delete proxy local copy if any            
            armature_local = get_object(scene.target_rig + "_local")
            if armature_local:
                bpy.data.objects.remove(armature_local, do_unlink=True)

            # save the binding state in a prop
            target_rig["arp_retarget_bound"] = False
            
            
            

    else:
        if self.unbind:
            print("Already unbound")
            self.report({'INFO'}, "Already unbound")

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    
    # hacky fix for proxy update issue
    act = target_rig.animation_data.action
    target_rig.animation_data.action = None
    target_rig.animation_data.action = act

    print("Retargetting done.\n")
    bpy.context.scene.frame_set(current_frame)

    
def get_target_bone_name(src_name):
    scn = bpy.context.scene
    for item in scn.bones_map:
        if item.source_bone == src_name:         
            return item.name
            

def update_set_as_root(self, context):
    scene = context.scene
    if scene.arp_remap_allow_root_update:
        # set all other 'set_as_root' property False (only one possible)
        for i in range(0, len(scene.bones_map)):
            item = scene.bones_map[i]
            if item.set_as_root and i != scene.bones_map_index:
                item.set_as_root = False
            
            if i == scene.bones_map_index:
                item.ik = False
                item.location = False



class CustomProp(bpy.types.PropertyGroup):
    '''name = bpy.props.StringProperty() '''
    # Properties of each item
    # implicit "name" property = target bone
    source_bone : bpy.props.EnumProperty(items=node_names_items, name = "Source  List", description="Source Bone Name")
    axis_order : bpy.props.EnumProperty(items=node_axis_items, name = "Axis Orders Switch", description="Axes Order")
    x_inv : bpy.props.BoolProperty(name = "X Axis Inverted", default = False, description = 'Inverse the X axis')
    y_inv : bpy.props.BoolProperty(name = "Y Axis Inverted", default = False, description = 'Inverse the Y axis')
    z_inv : bpy.props.BoolProperty(name = "Z Axis Inverted", default = False, description = 'Inverse the Z axis')
    id : bpy.props.IntProperty()
    set_as_root : bpy.props.BoolProperty(name = "Set As Root", default = False, description = 'Set this bone as the root (hips) of the armature ', update=update_set_as_root)
    offset_rot_x : bpy.props.FloatProperty(name = "Offset X Rotation", default = 0.0, description = 'Offset X rotation value')
    offset_rot_y : bpy.props.FloatProperty(name = "Offset Y Rotation", default = 0.0, description = 'Offset Y rotation value')
    offset_rot_z : bpy.props.FloatProperty(name = "Offset Z Rotation", default = 0.0, description = 'Offset Z rotation value')

    ik : bpy.props.BoolProperty(name="IK", default = False, description="Use IK for this bone (precise hands, feet tracking)")
    ik_pole : bpy.props.StringProperty(default="", description="IK pole bone (optional)")
    ik_auto_pole : bpy.props.BoolProperty(name="Auto Pole", default = False, description = "The pole bone will inherit the target bone transforms, instead of trying to match the IK chain orientation.\nUseful for legs, knees poles.")
    ik_create_constraints: bpy.props.BoolProperty(name="Add IK Const.", default=False, description="Automatically creates IK constraints if the bone has none")
    location: bpy.props.BoolProperty(name="Location", description="Use relative location remapping", default=False)
    rot_add: bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_add: bpy.props.FloatVectorProperty(default=(0.0, 0.0, 0.0), subtype='TRANSLATION', size=3)
    loc_mult: bpy.props.FloatProperty(default=1.0)


def _export_config(self):
    scene=bpy.context.scene
    
    filepath = self.filepath
   
    #add extension
    if filepath[-5:] != ".bmap":
        filepath += ".bmap"
    
    file = open(filepath, "w", encoding="utf8", newline="\n")

    for item in scene.bones_map:
        file.write(item.name+'%'+str(item.location)+'%'+str(item.ik_auto_pole)+'%'+vec_to_string(item.rot_add)+'%'+vec_to_string(item.loc_add)+'%'+str(item.loc_mult)+"\n")#pack new properties in the first line. Not ideal but best to ensure compatibility with older files.
        file.write(item.source_bone+"\n")
        file.write(str(item.set_as_root)+"\n")
        file.write(str(item.ik)+"\n")
        file.write(item.ik_pole+"\n")

    # close file
    file.close()

    
def _import_config(self):
    context = bpy.context
    scene = context.scene
    bones_not_found = []
    
    target_arm = get_object(scene.target_rig)
    source_arm = get_object(scene.source_rig)
    
    # no armatures set, return
    if target_arm == None or source_arm == None:
        return
        
    filepath = self.filepath
    file = None
    try:
        file = open(filepath, 'rU')   
    except:
        self.report({"ERROR"}, "Filepath is invalid: "+ filepath)
        return
        
    file_lines = file.readlines()
    total_lines = len(file_lines)
    props_count = 5
    bone_counts = total_lines / props_count

    #clear the bone collection
    if len(scene.bones_map) > 0:
        i = len(scene.bones_map)
        while i >= 0:
            scene.bones_map.remove(i)
            i -= 1

    #import items
    line = 0
    error_load = False

    # is there a prefix?
    prefix = ""
    prefix = scene.source_nodes_name_string.split("+")[0].split(":")[0]
    if prefix != "":
        print("Found prefix:", prefix)
  
    preset_data = {}
    
    # read settings
    for i in range(0, int(bone_counts)):
        first_line = str(file_lines[line]).rstrip()
        first_line_list = first_line.split('%')
        target_bone_name = ""

        item_location = "False"
        item_ik_auto_pole = "False"
        item_rot_add = Vector((0.0, 0.0, 0.0))
        item_loc_add = Vector((0.0, 0.0, 0.0))
        item_loc_mult = 1.0
        
        if len(first_line_list) == 1:
            target_bone_name = first_line
        else:# new format, multiple properties in the first line
            target_bone_name = first_line_list[0]
            if len(first_line_list) >= 2:
                item_location = first_line_list[1]
            if len(first_line_list) >= 3:
                item_ik_auto_pole = first_line_list[2]
            if len(first_line_list) >= 4:
                item_rot_add = first_line_list[3].split(',')
                item_rot_add = str_list_to_fl_list(item_rot_add)
            if len(first_line_list) >= 5:
                item_loc_add = first_line_list[4].split(',')
                item_loc_add = str_list_to_fl_list(item_loc_add)
            if len(first_line_list) >= 6:
                item_loc_mult = first_line_list[5]

        item_target_bone = "None"
        if target_arm.data.bones.get(target_bone_name):
            item_target_bone = target_bone_name

        found_name = False

        next_line = str(file_lines[line+1]).rstrip()
        next_line_2 = str(file_lines[line+2]).rstrip()
        next_line_3 = str(file_lines[line+3]).rstrip()
        next_line_4 = str(file_lines[line+4]).rstrip()

        item_source_bone = ""
        item_set_as_root = string_to_bool(next_line_2)
        item_ik = next_line_3
        item_ik_pole = next_line_4

        for n in scene.source_nodes_name_string.split("+"):
            if scene.search_and_replace:
                replaced_line = next_line.replace(scene.name_search, scene.name_replace)
                if n == replaced_line:
                    item_source_bone = replaced_line
                    found_name = True
            else:
                if n == next_line:
                    item_source_bone = next_line
                    found_name = True
                # try to add the prefix and see if there's a match
                elif n == prefix + ":" + next_line:
                    item_source_bone = prefix + ":" + next_line
                    found_name = True
                    print("Found match without prefix:", n, ">", next_line)

        if not found_name:
            bones_not_found.append(next_line)
            error_load = True

        line += props_count

        if item_source_bone != "":
            preset_data[item_source_bone] = [item_target_bone, item_set_as_root, item_ik, item_ik_pole, item_location, item_ik_auto_pole, item_rot_add, item_loc_add, item_loc_mult]

    # close file
    file.close()

    scene.arp_remap_allow_root_update = False# disable it before assigning the set root value, otherwise it's interfering
    
    # set settings
    for key, value in sorted(preset_data.items()):       
        item = scene.bones_map.add()
        item.name = value[0]
        item.source_bone = key
        item.set_as_root = value[1]
        item.ik = string_to_bool(value[2])
        item.ik_pole = value[3]
        item.location = string_to_bool(value[4])
        item.ik_auto_pole = string_to_bool(value[5])
        item.rot_add = value[6]
        item.loc_add = value[7]
        item.loc_mult = float(value[8])     

    scene.arp_remap_allow_root_update = True

    if len(bones_not_found) > 0:
        self.report({'ERROR'}, "Imported, but some preset bones do not exist in the armature:")
        for i in bones_not_found:
            self.report({'ERROR'}, i)
            
    # end import_config()
          
          
def set_global_scale(context):
    scn = context.scene
    source_rig = get_object(scn.source_rig)
    target_rig = get_object(scn.target_rig)
    try:
        scn.global_scale = source_rig.scale[0] / target_rig.scale[0]
    except:
        pass


def update_source_rig(self, context):   
    scn = context.scene
    # set source action
    if scn.source_rig != "":
        arm_obj = get_object(scn.source_rig)
        scn.source_action = arm_obj.animation_data.action.name
    
    # set global scale
    if scn.source_rig != "" and scn.target_rig != "":
        set_global_scale(context)


def update_target_rig(self,context):
    scn = context.scene    
    # set global scale
    if scn.source_rig != "" and scn.target_rig != "":
        set_global_scale(context)

        
def entries_are_set():
    scn = bpy.context.scene
    if scn.source_action != "" and scn.source_rig != "" and scn.target_rig != "":
        return True
    else:
        return False

        
def update_in_place(self, context):
    scn = context.scene
    act_name = scn.source_action
    act = bpy.data.actions.get(act_name)
    rig_name = scn.source_rig
    rig = get_object(rig_name)

    if act:
        if scn.arp_retarget_in_place:
            # make sure to keep the base action in file
            act.use_fake_user = True

            # remove current
            act_in_place = bpy.data.actions.get(act_name+"_IN_PLACE")
            if act_in_place:
                bpy.data.actions.remove(act_in_place)
         
            act_in_place = act.copy()
            act_in_place.name = act.name+"_IN_PLACE"

            # assign action
            rig.animation_data.action = act_in_place
            # set location fcurves
            start, end = act_in_place.frame_range[0], act_in_place.frame_range[1]
            for fc in act_in_place.fcurves:
                if not "location" in fc.data_path or not "pose.bones" in fc.data_path:
                    continue
                first_keyf = fc.keyframe_points[0]
                start_value = first_keyf.co[1]
                last_keyf = fc.keyframe_points[len(fc.keyframe_points)-1]
                end_value = last_keyf.co[1]
                delta = end_value-start_value
                for idx in range(0, len(fc.keyframe_points)):
                    keyf = fc.keyframe_points[idx]
                    fac = delta/(len(fc.keyframe_points)-1)
                    fac = fac * idx
                    keyf.co[1] -= fac

        else:
            # set base action
            act_base = bpy.data.actions.get(act_name.replace("_IN_PLACE", ""))
            print("act_base", act_base)
            if act_base and "_IN_PLACE" in rig.animation_data.action.name:
                # remove in place action
                act_in_place = rig.animation_data.action
                if act_in_place:
                    bpy.data.actions.remove(act_in_place)
                print("set action")
                rig.animation_data.action = act_base
                
                
                    
                
    update_source_rig(self, context)

    
###########  UI PANEL  ###################

class ARP_PT_auto_rig_remap_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ARP"
    bl_label = "Auto-Rig Pro: Remap"
    bl_idname = "ARP_PT_auto_rig_remap"
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context):
        layout = self.layout
        object = context.object
        scn = context.scene

        # Inputs
        row = layout.row()
        row.prop(scn, "arp_inputs_expand_ui", icon="TRIA_DOWN" if scn.arp_inputs_expand_ui else "TRIA_RIGHT", icon_only=True, emboss=False)
        row.label(text="Inputs:")
        if scn.arp_inputs_expand_ui:
            layout.label(text="Source Armature:")
            row = layout.row(align=True)
            row.prop_search(scn, "source_rig", bpy.data, "objects", text="")
            row.operator("arp.pick_object", text="", icon='EYEDROPPER').action = 'pick_source'
         
            layout.prop(scn, "arp_retarget_in_place", text="In Place")

            layout.label(text="Target Armature:")
            row = layout.row(align=True)
            row.prop_search(scn, "target_rig", bpy.data, "objects", text="")
            row.operator("arp.pick_object", text="", icon='EYEDROPPER').action = 'pick_target'
       
            row = layout.row(align=True)
            col = layout.column(align=True)
            col.operator("arp.auto_scale", text="Auto Scale")
            layout.separator()
            
            
        row = layout.row(align=True)
        if entries_are_set():#display only if entries are set
            row.enabled = True
        else:
            row.enabled = False

        col = layout.column(align=True)
        col.operator("arp.build_bones_list", text="Build Bones List")

        row = col.row(align=True)
        row.operator("arp.retarget", text="Re-Target", icon="PLAY")
        row.prop(scn, "arp_retarget_decoupled_expand_ui", icon_only=True, icon='SETTINGS')
        if scn.arp_retarget_decoupled_expand_ui:
            p = col.operator("arp.retarget_bind_only", text="Bind Only")
            p.unbind = False
            p = col.operator("arp.retarget_bind_only", text="Unbind Only")
            p.unbind = True

        if entries_are_set():#only if entries are set
            target_armature = get_object(scn.target_rig).data.name
            row = layout.row(align=True)
            split = row.split(factor=0.5)
            split.label(text="Source Bones:")
            split.label(text="Target Bones:")
            row = layout.row(align=True)
            row.template_list("ARP_UL_items", "", scn, "bones_map", scn, "bones_map_index", rows=2)

            layout.operator("arp.retarget_synchro_select", text="", icon="FILE_REFRESH")

            # Display bone item properties
            if len(scn.bones_map) > 0:
                # make a box UI
                box = layout.box()
                row = box.row(align=True)

                row.prop(scn.bones_map[scn.bones_map_index], "source_bone", text="")
                row.prop_search(scn.bones_map[scn.bones_map_index], "name", bpy.data.armatures[target_armature], "bones", text="")
                row.operator("arp.pick_object", text="", icon='EYEDROPPER').action = 'pick_bone'

                row = box.row(align=True)
                row.prop(scn.bones_map[scn.bones_map_index], "set_as_root", text="Set as Root")
   
                row=box.row(align=True)
                split = row.split(factor=0.2)

                if scn.bones_map[scn.bones_map_index].set_as_root:
                    split.enabled = False                
                else:
                    split.enabled = True

                split.prop(scn.bones_map[scn.bones_map_index],"ik", text="IK")
                split2 = split.split(factor=0.9, align=True)
                if scn.bones_map[scn.bones_map_index].ik:
                    split2.enabled = True
                else:
                    split2.enabled = False
                split2.prop_search(scn.bones_map[scn.bones_map_index], "ik_pole", bpy.data.armatures[target_armature], "bones", text="Pole")
                split2.operator("arp.pick_object", text="", icon='EYEDROPPER').action = 'pick_pole'
                row = box.row(align=True)
                row.enabled = False
                if scn.bones_map[scn.bones_map_index].ik:
                    row.enabled = True
                row.prop(scn.bones_map[scn.bones_map_index], "ik_auto_pole")
                row.prop(scn.bones_map[scn.bones_map_index], "ik_create_constraints")

                row = box.row(align=True)
                row.enabled = not scn.bones_map[scn.bones_map_index].ik
                row.prop(scn.bones_map[scn.bones_map_index], "location")
                if scn.bones_map[scn.bones_map_index].set_as_root:
                    row.enabled = False

                col1 = box.column(align=True)
                row = col1.row(align=True)
                row.prop(scn, "arp_remap_show_tweaks", icon="HIDE_OFF")
                row.operator('arp.retarget_clear_tweaks', text="", icon='PANEL_CLOSE')
                
                if scn.arp_remap_show_tweaks:
                    col = box.column(align=True)
                    col.prop(scn, "additive_rot", text="Additive Rotation")
                    row = col.row(align=True)
                    btn = row.operator("arp.apply_offset", text="+X")
                    btn.value = "rot_+x"
                    btn = row.operator("arp.apply_offset", text="-X")
                    btn.value = "rot_-x"
                    btn = row.operator("arp.apply_offset", text="+Y")
                    btn.value = "rot_+y"
                    btn = row.operator("arp.apply_offset", text="-Y")
                    btn.value = "rot_-y"
                    btn = row.operator("arp.apply_offset", text="+Z")
                    btn.value = "rot_+z"
                    btn = row.operator("arp.apply_offset", text="-Z")
                    btn.value = "rot_-z"

                    col = box.column(align=True)
                    col.prop(scn, "additive_loc", text="Additive Location")
                    row = col.row(align=True)
                    btn = row.operator("arp.apply_offset", text="+X")
                    btn.value = "loc_+x"
                    btn = row.operator("arp.apply_offset", text="-X")
                    btn.value = "loc_-x"
                    btn = row.operator("arp.apply_offset", text="+Y")
                    btn.value = "loc_+y"
                    btn = row.operator("arp.apply_offset", text="-Y")
                    btn.value = "loc_-y"
                    btn = row.operator("arp.apply_offset", text="+Z")
                    btn.value = "loc_+z"
                    btn = row.operator("arp.apply_offset", text="-Z")
                    btn.value = "loc_-z"
                    col = box.column(align=True)
                    col.prop(scn, "loc_mult", text="Location Multiplier")
                    row = col.row(align=True)
                    btn = row.operator("arp.apply_offset", text="Set")
                    btn.value = "loc_mult"

                row = layout.row()
                row.prop(scn, "arp_map_presets_expand_ui",
                icon="TRIA_DOWN" if scn.arp_map_presets_expand_ui else "TRIA_RIGHT", icon_only=True, emboss=False)
                row.label(text="Mapping Presets:")

                if scn.arp_map_presets_expand_ui:                  
                    row = layout.row(align=True)
                    row.operator("arp.import_config", text="Import")
                    row.menu('ARP_MT_remap_import', text="", icon='DOWNARROW_HLT')
                    row = row.row(align=False)
                    row.operator("arp.export_config", text="Export")                    
                    row = layout.row(align=True)
                    row.prop(scn, "search_and_replace", text="Replace Namespace:")
                    row = layout.row(align=True)
                    if scn.search_and_replace:
                        row.enabled = True
                    else:
                        row.enabled = False
                    row.prop(scn, "name_search", text="Search")
                    row.prop(scn, "name_replace", text="Replace")

        else:
            layout.label(text="Empty bone list")

        layout.separator()
        layout.alignment = 'CENTER'
        layout.label(text="Redefine Source Rest Pose:")
        button_state = 0

        if get_object(scn.source_rig + "_copy"):
            button_state = 1

        try:
            current_mode = bpy.context.mode
            if current_mode == 'POSE' and bpy.context.object.name == scn.source_rig + "_copy":
                button_state = 1
        except:
            pass

        if button_state == 0:
            layout.operator("arp.redefine_rest_pose", text="Redefine Rest Pose")
        if button_state == 1:
            layout.operator("arp.copy_bone_rest", text="Copy Selected Bones Rotation", icon='COPYDOWN')
            row = layout.row(align=True)
            row.operator("arp.cancel_redefine", text="Cancel")
            row.operator("arp.copy_raw_coordinates", text="Apply")


###########  REGISTER  ##################

classes = (ARP_OT_clear_tweaks, ARP_OT_synchro_select, ARP_UL_items, ARP_OT_freeze_armature, ARP_OT_redefine_rest_pose, ARP_OT_auto_scale, ARP_OT_apply_offset, ARP_OT_cancel_redefine, ARP_OT_copy_bone_rest, ARP_OT_copy_raw_coordinates, ARP_OT_pick_object, ARP_OT_export_config, ARP_OT_import_config, ARP_OT_retarget, ARP_OT_build_bones_list, CustomProp, ARP_PT_auto_rig_remap_panel, ARP_OT_bind_only, ARP_MT_remap_import, ARP_OT_import_config_from_path)

def update_arp_tab():
    try:
        bpy.utils.unregister_class(ARP_PT_auto_rig_remap_panel)
    except:
        pass
    ARP_PT_auto_rig_remap_panel.bl_category = bpy.context.preferences.addons[__package__].preferences.arp_tab_name
    bpy.utils.register_class(ARP_PT_auto_rig_remap_panel)

def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    update_arp_tab()

    bpy.types.Scene.target_rig = bpy.props.StringProperty(name = "Target Rig", default="", description="Destination armature to re-target the action", update=update_target_rig)
    bpy.types.Scene.source_rig = bpy.props.StringProperty(name = "Source Rig", default="", description="Source rig armature to take action from", update=update_source_rig)
    bpy.types.Scene.bones_map = bpy.props.CollectionProperty(type=CustomProp)
    bpy.types.Scene.bones_map_index = bpy.props.IntProperty()
    bpy.types.Scene.global_scale = bpy.props.FloatProperty(name="Global Scale", default=1.0, description="Global scale offset for the root location")
    bpy.types.Scene.source_nodes_name_string = bpy.props.StringProperty(name = "Source Names String", default="")
    bpy.types.Scene.source_action = bpy.props.StringProperty(name = "Source Action", default="", description="Source action data to load data from")
    bpy.types.Scene.arp_inherit_rot = bpy.props.BoolProperty(name="ARP Inherit Rotation", default=False, description="Auto-Rig Pro type armature only: if enabled, the bones hierarchy will be modified so that the arms and the head will inherit their parent bones rotation.")    
    bpy.types.Scene.additive_rot = bpy.props.FloatProperty(name="Additive Rotation", default=math.radians(10), unit="ROTATION")
    bpy.types.Scene.additive_loc = bpy.props.FloatProperty(name="Additive Location", default=0.1)
    bpy.types.Scene.loc_mult = bpy.props.FloatProperty(name="Root Scale", default=0.9)
    bpy.types.Scene.name_search = bpy.props.StringProperty(name="Name search", default="")
    bpy.types.Scene.name_replace = bpy.props.StringProperty(name="Replace", default="")
    bpy.types.Scene.search_and_replace = bpy.props.BoolProperty(name="search_and_replace", default=False)
    bpy.types.Scene.arp_remap_show_tweaks = bpy.props.BoolProperty(name="Interactive Tweaks", default=False, description="Show the interactive tweaks menu")
    bpy.types.Scene.arp_remap_allow_root_update = bpy.props.BoolProperty(name="", default=True, description="Allow update check of the Set as Root prop")
    bpy.types.Scene.arp_map_presets_expand_ui = bpy.props.BoolProperty(name="", default=True, description="Expand the mapping presets interface")
    bpy.types.Scene.arp_inputs_expand_ui = bpy.props.BoolProperty(name="", default=True, description="Expand the inputs interface")
    bpy.types.Scene.arp_retarget_decoupled_expand_ui = bpy.props.BoolProperty(name="", default=False, description="Expand the retargetting options interface")
    bpy.types.Scene.arp_retarget_in_place = bpy.props.BoolProperty(default=False, description="Tries to compensate root motion so that the pelvis stay in place. Only works with cyclic animation (walk, run...)", update=update_in_place)


def unregister():

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.target_rig
    del bpy.types.Scene.source_rig
    del bpy.types.Scene.bones_map
    del bpy.types.Scene.bones_map_index
    del bpy.types.Scene.global_scale
    del bpy.types.Scene.source_nodes_name_string
    del bpy.types.Scene.source_action
    del bpy.types.Scene.arp_inherit_rot 
    del bpy.types.Scene.additive_rot
    del bpy.types.Scene.additive_loc
    del bpy.types.Scene.loc_mult
    del bpy.types.Scene.name_search
    del bpy.types.Scene.name_replace
    del bpy.types.Scene.search_and_replace
    del bpy.types.Scene.arp_remap_show_tweaks
    del bpy.types.Scene.arp_remap_allow_root_update
    del bpy.types.Scene.arp_map_presets_expand_ui
    del bpy.types.Scene.arp_inputs_expand_ui
    del bpy.types.Scene.arp_retarget_decoupled_expand_ui
    del bpy.types.Scene.arp_retarget_in_place

