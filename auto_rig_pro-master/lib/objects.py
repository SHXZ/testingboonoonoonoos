import bpy, os
from .bone_edit import *
from .context import *

def set_active_object(object_name):
    bpy.context.view_layer.objects.active = get_object(object_name)
    get_object(object_name).select_set(state=1)


def get_object(name, view_layer_change=False):
    ob = bpy.data.objects.get(name)
    if ob:
        if view_layer_change:
            found = False
            for v_o in bpy.context.view_layer.objects:
                if v_o == ob:
                    found = True
            if not found:# object not in view layer, add to the base collection
                bpy.context.collection.objects.link(ob)

    return ob


def delete_object(obj):
    bpy.data.objects.remove(obj, do_unlink=True)


def set_active_object(object_name):
     bpy.context.view_layer.objects.active = bpy.data.objects[object_name]
     bpy.data.objects[object_name].select_set(state=True)


def hide_object(obj_to_set):
    try:# object may not be in current view layer
        obj_to_set.hide_set(True)
        obj_to_set.hide_viewport = True
    except:
        pass


def hide_object_visual(obj_to_set):
    obj_to_set.hide_set(True)


def is_object_hidden(obj_to_get):
    try:
        if obj_to_get.hide_get() == False and obj_to_get.hide_viewport == False:
            return False
        else:
            return True
    except:# the object must be in another view layer, it can't be accessed
        return True


def unhide_object(obj_to_set):
    # we can only operate on the object if it's in the active view layer...
    try:
        obj_to_set.hide_set(False)
        obj_to_set.hide_viewport = False
    except:
        print("Could not reveal object:", obj_to_set.name)


def duplicate_object():
    try:
        bpy.ops.object.duplicate(linked=False, mode='TRANSLATION')
    except:
        bpy.ops.object.duplicate('TRANSLATION', False)


def delete_children(passed_node, type):
    if passed_node:
        if type == "OBJECT":
            parent_obj = passed_node
            children = []

            for obj in bpy.data.objects:
                if obj.parent:
                    if obj.parent == parent_obj:
                        children.append(obj)
                        for _obj in children:
                            for obj_1 in bpy.data.objects:
                                if obj_1.parent:
                                    if obj_1.parent == _obj:
                                        children.append(obj_1)

            meshes_data = []

            for child in children:
                # store the mesh data for removal afterward
                try:
                    if child.data:
                        if not child.data.name in meshes_data:
                            meshes_data.append(child.data.name)
                except:
                    continue

                bpy.data.objects.remove(child, do_unlink=True, do_id_user=True, do_ui_user=True)

            for data_name in meshes_data:
                current_mesh = bpy.data.meshes.get(data_name)
                if current_mesh:
                    bpy.data.meshes.remove(current_mesh, do_unlink=True, do_id_user=True, do_ui_user=True)

            bpy.data.objects.remove(passed_node, do_unlink=True)

        elif type == "EDIT_BONE":
            current_mode = bpy.context.mode

            bpy.ops.object.mode_set(mode='EDIT')

            if bpy.context.active_object.data.edit_bones.get(passed_node.name):

                # Save displayed layers
                _layers = [bpy.context.active_object.data.layers[i] for i in range(0, 32)]

                # Display all layers
                for i in range(0, 32):
                    bpy.context.active_object.data.layers[i] = True

                bpy.ops.armature.select_all(action='DESELECT')
                bpy.context.evaluated_depsgraph_get().update()
                bpy.context.active_object.data.edit_bones.active = get_edit_bone(passed_node.name)
                bpy.ops.armature.select_similar(type='CHILDREN')
                bpy.ops.armature.delete()

                for i in range(0, 32):
                    bpy.context.active_object.data.layers[i] = _layers[i]

            # restore saved mode
            restore_current_mode(current_mode)


def parent_objects(_obj_list, target):
    for obj in _obj_list:
        if obj.type == "MESH":
            #print("parenting", obj.name)
            obj_mat = obj.matrix_world.copy()
            obj.parent = target
            obj.matrix_world = obj_mat