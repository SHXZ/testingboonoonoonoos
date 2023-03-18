import bpy

def update_all_tab_names(self, context):
    try:
        from . import auto_rig, auto_rig_ge, auto_rig_smart, auto_rig_remap, rig_functions
        auto_rig.update_arp_tab()
        auto_rig_ge.update_arp_tab()
        auto_rig_smart.update_arp_tab()
        auto_rig_remap.update_arp_tab()
        rig_functions.update_arp_tab()
    except:
        pass

class ARP_MT_arp_addon_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    arp_tab_name : bpy.props.StringProperty(name="Interface Tab", description="Name of the tab to display the interface in", default="ARP", update=update_all_tab_names)
    arp_tools_tab_name : bpy.props.StringProperty(name="Tools Interface Tab", description="Name of the tab to display the tools (IK-FK snap...) interface in", default="Tool", update=update_all_tab_names)
    custom_limb_path: bpy.props.StringProperty(name="Custom Limbs Path", subtype='FILE_PATH', default="C:\\Custom Limbs/")
    
    def draw(self, context):
        col = self.layout.column(align=True)
        col.prop(self, "arp_tab_name", text="Interface Tab")
        col.prop(self, "arp_tools_tab_name", text="Tools Interface Tab")        
        col.prop(self, "custom_limb_path")
        col.prop(context.scene, "arp_debug_mode")
        col.prop(context.scene, "arp_experimental_mode")

def register():
    from bpy.utils import register_class

    try:
        register_class(ARP_MT_arp_addon_preferences)
    except:
        pass
    bpy.types.Scene.arp_debug_mode = bpy.props.BoolProperty(name="Debug Mode", default = False, description = "Run the addon in debug mode (should be enabled only for debugging purposes, not recommended for a normal usage)")
    bpy.types.Scene.arp_experimental_mode = bpy.props.BoolProperty(name="Experimental Mode", default = False, description = "Enable experimental, unstable tools. Warning, can lead to errors. Use it at your own risks.")
    
def unregister():
    from bpy.utils import unregister_class
    unregister_class(ARP_MT_arp_addon_preferences)

    del bpy.types.Scene.arp_debug_mode
    del bpy.types.Scene.arp_experimental_mode
