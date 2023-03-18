import bpy

def get_parent_collections(target):
    # return the list of all parent collections to the specified target collection
    # with a recursive function. A sub-function is used, string based, to ease the process

    def get_parent_collections_string(target_name):
        parent_collections = ""
        found = None

        for collec in bpy.data.collections:
            for child in collec.children:
                if child.name == target_name:
                    print("found", collec.name)
                    parent_collections += collec.name + ","
                    parent_collections += get_parent_collections_string(collec.name)

        return parent_collections


    string_result = get_parent_collections_string(target.name)
    to_list = [bpy.data.collections[i] for i in string_result[:-1].split(",") if i != ""]

    return to_list

    meshes_data = []

    for child in children:
        # store the mesh data for removal afterward
        if child.data:
            if not child.data.name in meshes_data:
                meshes_data.append(child.data.name)

        bpy.data.objects.remove(child, do_unlink=True, do_id_user=True, do_ui_user=True)

    for data_name in meshes_data:
        current_mesh = bpy.data.meshes.get(data_name)
        if current_mesh:
            bpy.data.meshes.remove(current_mesh, do_unlink=True, do_id_user=True, do_ui_user=True)


    bpy.data.objects.remove(passed_node, do_unlink = True)


def get_all_collections_list():
    def mt_traverse_tree(t):
        yield t
        for child in t.children:
            yield from mt_traverse_tree(child)

    colls = []
    coll = bpy.context.view_layer.layer_collection
    for c in mt_traverse_tree(coll):
        colls.append(c)
    return colls


def get_cs_collection():
    # returns the custom shape collection
    custom_shape_collection = None
    for col in bpy.data.collections:
        split_len = len(col.name.split('_'))
        if split_len > 0:
            if col.name.split('_')[split_len - 1] == "cs":
                custom_shape_collection = col
                break

    if custom_shape_collection == None:  # the collection haven't been found, the collection hierarchy isn't correct
        for collec in bpy.data.collections:  # look for any collection called cs_grp
            if collec.name.startswith("cs_grp"):
                custom_shape_collection = collec
                break

    return custom_shape_collection


def search_layer_collection(layerColl, collName):
    # Recursivly transverse layer_collection for a particular name
    found = None
    if (layerColl.name == collName):
        return layerColl
    for layer in layerColl.children:
        found = search_layer_collection(layer, collName)
        if found:
            return found