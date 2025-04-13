
from sklearn.mixture import GaussianMixture

import numpy as np
import random
import math
import bpy, bmesh
import os, sys
import time
from mathutils import Vector
import pickle

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)

import src.utils as utils

# this next part forces a reload in case you edit the source after you first start the blender session
import imp
imp.reload(utils)

def cube_clustering( verts, cube_side_length ):
    
    assigned_room_ids = [-1 for v in verts]
    
    room_ids = {}
    
    print("VERTS:", verts, len(verts))
    for vert_index,v in enumerate(verts):
        ix = math.floor(v.co.x/cube_side_length)
        iy = math.floor(v.co.y/cube_side_length)
        iz = math.floor(v.co.z/cube_side_length)
        print(v.co, ix, iy, iz)
        index = f"{ix}_{iy}_{iz}"
        if not index in room_ids:
            room_ids[index] = len(room_ids)
            
        assigned_room_ids[vert_index] = room_ids[index]

    return assigned_room_ids



def estimate_rooms( bm, cube_side_length=20 ):
    
    print("=======================")
    print("CALCULATING CLUSTERS")
        
    #print("points:", points)
    print(f"Running Cube-based clustering on {len(bm.verts)} points")
    print(f"Splitting mesh into 'rooms' of size {cube_side_length}")

    res = cube_clustering( bm.verts, cube_side_length=cube_side_length )
    
    print("Done.", res)
    print("=======================")
    
    return res

def split_non_connected_rooms( bm, assigned_rooms ):
    
    print( "Splitting non-connected verts into new rooms" )
    bm.verts.ensure_lookup_table()
    
    # Assign "-1" as a starting index:
    newly_assigned_rooms = [-1 for id in assigned_rooms]
    
    cur_new_room_id = 0
    
    while True:
        # Find an unassigned vertex:
        unassigned_vert_index = -1
        for i,id in enumerate(newly_assigned_rooms):
            if id == -1:
                unassigned_vert_index = i
                break
        # No more unassigned vertices found?
        if unassigned_vert_index == -1:
            break
        
        #print("Found new unassigned vert:", unassigned_vert_index)
        #print("Generating new room", cur_new_room_id)
        
        # If we do still have unassigned vertices, start with the first and
        # Find all connected(!) verts in the same room. Split these into a sepparate
        # room.
        front = [bm.verts[unassigned_vert_index]]
        visited = [False for i in range(len(bm.verts))]
        original_room_id = assigned_rooms[unassigned_vert_index]
        steps =  0
        while len( front ) > 0:
            steps += 1
                
            v = front.pop()
            visited[v.index] = True
            
            newly_assigned_rooms[v.index] = cur_new_room_id
            
            for n in utils.get_neighbor_verts( v ):
                #print( n in visited, n in front, original_room_id, assigned_rooms[n.index], n.index)
                if not visited[n.index] and original_room_id == assigned_rooms[n.index]:
                    front.append( n )
                    visited[n.index] = True
        
        cur_new_room_id += 1
    
    print( f"New number of rooms: {cur_new_room_id}" )
    return newly_assigned_rooms, cur_new_room_id
            
def create_debug_meshes( bm, assigned_rooms, num_rooms, overlap=False, assign_material_indices=False, move_origin=False, copy_smooth=True, copy_uvs=False ):
    # TODO: don't ignore 'overlap'!
    
    bm.verts.index_update()
    
    # Create a new mesh for each result:
    split_verts = [set() for i in range(num_rooms)]
    
    for i,v in enumerate(bm.verts):
        room_id = assigned_rooms[i]
        
        split_verts[room_id].add( v )
        # make sure the vertex's neighbors are added to the same cluster as well (even if they're in the neighboring cluster):
        #if overlap:
        for n in utils.get_verts_connected_via_face( v ):
            split_verts[room_id].add( n )
            
    
    objects = []
    origin = Vector( (0,0,0) )
    processed_faces = set()
    #verts_to_clusters_per_object = []
    for room_id in range(num_rooms):
        print(f"Creating cluster {room_id} of {num_rooms}")
        
        if move_origin and len(split_verts[room_id]) > 0:
            # Calculate mean center point to be used as new origin:
            origin = utils.mean_vert_position( split_verts[room_id] )
            

        #selection = bmesh.ops.region_extend( bm, geom=split_verts[cluster_id] )
        #print(selection)
        #print(f"Splitting off {len(split_verts[cluster_id])} verts")
        if overlap:
            processed_faces = set()   # Ignore which faces have been copied before
            
#        cluster_ids_b = [verts_to_clusters[v.index] for v in split_verts[room_id]]
#        vert_inds = [v.index for v in split_verts[room_id]]
#        print( "vert_inds before", min(vert_inds), max(vert_inds) )
        
        #print("cluster ids before copy:", cluster_ids)
        new_mesh, _, _, _ = utils.copy_to_new_mesh( split_verts[room_id], assign_material_indices=assign_material_indices, origin=origin, copy_smooth=copy_smooth, copy_uvs=copy_uvs, copy_vertex_colors=True, processed_faces=processed_faces, bm=bm )
        
#        cluster_ids_a = [new_verts_to_clusters[v.index] for v in new_mesh.verts]
#        vert_inds = [v.index for v in new_mesh.verts]
#        print( "vert_inds after", min(vert_inds), max(vert_inds) )
        
        #print("cluster ids after copy:", cluster_ids_a)
#        assert cluster_ids_b == cluster_ids_a
        
#        verts = [v for v in new_mesh.verts]
#        while len(verts) > 0:
#            v = verts.pop()
#            selected = utils.select_connected( [v] )
#            cluster_ids = [new_verts_to_clusters[sv.index] for sv in selected if isinstance( sv, bmesh.types.BMVert )]
#            print( min(cluster_ids), max(cluster_ids))
#            assert min(cluster_ids) == max(cluster_ids)
        
        name = f"cluster_{i}"
        me_cluster = bpy.data.meshes.new(name)  # add a new mesh
        obj_cluster = bpy.data.objects.new(name, me_cluster)  # add a new object using the mesh
        col = bpy.context.scene.collection
        col.objects.link(obj_cluster)
        
        obj_cluster.location = origin

        # Finish up, write the bmesh back to the mesh
        new_mesh.to_mesh(me_cluster)
        new_mesh.free()  # free and prevent further access
        
#        test_mesh = bmesh.new()
#        test_mesh.from_mesh( me_cluster )
#        verts = [v for v in test_mesh.verts]
#        while len(verts) > 0:
#            v = verts.pop()
#            selected = utils.select_connected( [v] )
#            cluster_ids = [new_verts_to_clusters[sv.index] for sv in selected if isinstance( sv, bmesh.types.BMVert )]
#            print("test mesh")
#            print( min(cluster_ids), max(cluster_ids))
#            assert min(cluster_ids) == max(cluster_ids)
        
        objects.append( obj_cluster )
        #verts_to_clusters_per_object.append( new_verts_to_clusters )
    return objects#, verts_to_clusters_per_object


def create_hierarchy( obj, cube_side_length=10, overlap=False, assign_material_indices=False, edge_split=False, copy_uvs=True ):#, verts_to_clusters=None ):
    
    print("Split meshes:", obj.name)
    # Get the active mesh
    me = obj.data

    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMeshs
    bm.from_mesh(me)   # fill it in from a Mesh
    
    assigned_rooms = estimate_rooms( bm, cube_side_length=cube_side_length )
    print("assigned rooms:", len(assigned_rooms), len(bm.verts), len(bm.faces))
    objects = create_debug_meshes( bm, assigned_rooms,
            num_rooms=max(assigned_rooms)+1, overlap=overlap,
            assign_material_indices=assign_material_indices,
            move_origin=True, copy_smooth=True, copy_uvs=copy_uvs )
    
    bm.free()

     # add a new empty object to serve as a parent for all the new collision meshes:
    group_object = bpy.data.objects.new( f"{obj.name}_sections", None )
    bpy.context.scene.collection.objects.link( group_object )
    
    for ob in objects:
        ob.name = f"{obj.name}_section"
        ob.data.name = ob.name
        print("Moving object to group:", ob.name)
        
        for m in obj.data.materials:
            ob.data.materials.append( m )
            
        t = time.time()
        
        # Loop through all collections the obj is linked to
        for coll in ob.users_collection:
            # Unlink the object
            coll.objects.unlink(ob)

        # Link each object to the target group
        bpy.context.scene.collection.objects.link( ob )
        ob.parent = group_object
        
        # Workaround for materials not getting updated correctly: Switching to edit mode and back:
#        bpy.context.view_layer.objects.active = ob
#        bpy.ops.object.mode_set(mode='EDIT')
#        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.context.view_layer.update()
    
    if edge_split:
        for o in objects:    
            modifier = o.modifiers.new(name="EdgeSplit", type='EDGE_SPLIT')
            modifier.split_angle = 1.2
            
#    if verts_to_clusters:
#        # Reindex by name so that we can find the verts-to-cluster assignment by object name:
#        verts_to_clusters_per_object_by_name = {}
#        for verts_to_clusters, ob in zip( verts_to_clusters_per_object, objects ):
#            verts_to_clusters_per_object_by_name[ob.name] = verts_to_clusters
#        
#        filename = os.path.join( os.path.dirname(bpy.data.filepath), "verts_to_clusters_per_object.pickle" )
#        with open( filename, "wb" ) as f:
#            pickle.dump( verts_to_clusters_per_object_by_name, f )
#            print("Saved verts_to_clusters_per_object as:", filename)
            
        # Vertex IDs will only be perserved upon export if the meshes have:
        # - smooth shading
        # - no UV maps:
        
#        for ob in objects:
#            uv_layers = ob.data.uv_layers
#            while len(uv_layers) > 0:
#                uv_layers.remove(uv_layers[0])
                
        
    return objects

if __name__ == "__main__":
    
    obj = bpy.context.object
    
#    verts_to_clusters = None
#    if obj.name == "CaveSystem_rocks":
#        filename = os.path.join( os.path.dirname(bpy.data.filepath), "verts_to_clusters.pickle" )
#        with open( filename, "rb" ) as f:
#            verts_to_clusters = pickle.load( f )
    
    objs = create_hierarchy( obj, assign_material_indices=True )
    
