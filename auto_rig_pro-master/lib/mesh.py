import bpy, bmesh
from .objects import *

def overwrite_vgroup(obj, vgroup, new_vgname):
    new_vgrp = obj.vertex_groups.get(new_vgname)                    
    if new_vgrp:
        obj.vertex_groups.remove(new_vgrp)
    vgroup.name = new_vgname


def create_mesh_data(mesh_name, verts, edges, faces):
    # create an new mesh data given verts, edges and faces data
    new_mesh = bpy.data.meshes.new(name=mesh_name)
    new_mesh.from_pydata(verts, edges, faces)
    return new_mesh


def create_object_mesh(obj_name, verts, edges, faces):
    shape_mesh = create_mesh_data(obj_name, verts, edges, faces)
    # create object
    shape = bpy.data.objects.new(obj_name, shape_mesh)
    return shape


def transfer_shape_keys_deformed(source_obj, target_obj):
    if source_obj == None or target_obj == None:
        return

    # disable all non-armature modifiers to solve issues when baking the mesh
    disabled_mod = {}
    for obj in [source_obj, target_obj]:
        for mod in obj.modifiers:
            if mod.type != "ARMATURE" and mod.show_viewport:           
                mod.show_viewport = False
                if not obj.name in disabled_mod:
                    disabled_mod[obj.name] = {}
                disabled_mod[obj.name][mod.name] = mod.name

    if source_obj.data.shape_keys == None:
        return

    source_shape_keys = source_obj.data.shape_keys.key_blocks

    basis_index = 0
    # get the Basis shape key index
    for sk_index, sk in enumerate(source_shape_keys):
        if "Basis" in source_shape_keys[sk_index].name:
            basis_index = sk_index
            # pin the Basis key
            source_obj.active_shape_key_index = basis_index
            source_obj.show_only_shape_key = True
            bpy.context.evaluated_depsgraph_get().update()
            break

            # store the vert coords in basis shape keys
    mesh_baked = bmesh.new()
    mesh_baked.from_object(source_obj, bpy.context.evaluated_depsgraph_get(), deform=True, face_normals=False)
    mesh_baked.verts.ensure_lookup_table()
    base_verts_coords = [i.co for i in mesh_baked.verts]
 
    if 'mesh_baked' in locals():
        del mesh_baked

    # store the vert coords in basis shape keys
    for sk_index, sk in enumerate(source_shape_keys):
        if sk_index == basis_index:
            continue

        source_obj.active_shape_key_index = sk_index
        bpy.context.evaluated_depsgraph_get().update()

        # get the verts moved in shape key
        mesh_baked1 = bmesh.new()
        mesh_baked1.from_object(source_obj, bpy.context.evaluated_depsgraph_get(), deform=True, face_normals=False)
        mesh_baked1.verts.ensure_lookup_table()
        deformed_verts_coords = [i.co for i in mesh_baked1.verts]
       
        deformed_verts_index_list = []

        for vert_index, vert in enumerate(mesh_baked1.verts):
            if vert.co != base_verts_coords[vert_index]:
                deformed_verts_index_list.append(vert_index)
            
        # transfer the shape key
        bpy.ops.object.shape_key_transfer()

        target_sk = target_obj.data.shape_keys.key_blocks[sk_index]       
        target_sk.value = sk.value

        # correct the deformed vert coordinates
        for deformed_vert_index in deformed_verts_index_list:
            # print("set vertex", deformed_vert_index, "from", target_sk.data[deformed_vert_index].co, "TO", mesh_baked1.verts[deformed_vert_index].co)
            target_sk.data[deformed_vert_index].co = mesh_baked1.verts[deformed_vert_index].co

    source_obj.show_only_shape_key = False
    target_obj.show_only_shape_key = False

    # copy drivers
    anim_data = source_obj.data.shape_keys.animation_data

    if anim_data and anim_data.drivers:
        obj_anim_data = target_obj.data.shape_keys.animation_data_create()

        for fcurve in anim_data.drivers:
            new_fc = obj_anim_data.drivers.from_existing(src_driver=fcurve)
            new_fc.driver.is_valid = True

            for dvar in new_fc.driver.variables:
                for dtar in dvar.targets:
                    if dtar.id == source_obj:
                        dtar.id = target_obj

    # restore disabled modifiers  
    for objname in disabled_mod:
        ob = get_object(objname)
        for modname in disabled_mod[objname]:         
            ob.modifiers[modname].show_viewport = True