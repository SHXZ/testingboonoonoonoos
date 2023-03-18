import bpy

def create_custom_prop(bone=None, prop_name="", prop_val=1.0, prop_min=0.0, prop_max=1.0, prop_description="", soft_min=None, soft_max=None):
    if soft_min == None:
        soft_min = prop_min
    if soft_max == None:
        soft_max = prop_max

    if not "_RNA_UI" in bone.keys():
        bone["_RNA_UI"] = {}

    bone[prop_name] = prop_val
    bone["_RNA_UI"][prop_name] = {"use_soft_limits":True, "min": prop_min, "max": prop_max, "description": prop_description, "soft_min":soft_min, "soft_max":soft_max}
    bone.property_overridable_library_set('["'+prop_name+'"]', True)
