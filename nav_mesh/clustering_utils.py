import bpy
from mathutils import Vector


import src.utils as utils

# this next part forces a reload in case you edit the source after you first start the blender session
import imp
imp.reload(utils)


def create_debug_meshes( bm, assigned_rooms, num_rooms, overlap=False, assign_material_indices=False, move_origin=False, copy_smooth=True, copy_uvs=False ):
    # TODO: don't ignore 'overlap'!
    
    bm.verts.index_update()
    
    # Create a new mesh for each result:
    split_verts = [set() for i in range(num_rooms)]
    
    for i,v in enumerate(bm.verts):
        room_id = assigned_rooms[i]
        
        split_verts[room_id].add( v )
        # make sure the vertex's neighbors are added to the same cluster as well (even if they're in the neighboring cluster):
        if overlap:
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
