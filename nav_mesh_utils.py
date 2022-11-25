import bpy, bmesh
import mathutils
import numpy as np
from scipy.spatial import KDTree

def smooth_max_node_heights( bm, heights ):
    positions = np.empty( (len(bm.verts),3) )
    for i,v in enumerate(bm.verts):
        positions[i,:] = (v.co.x, v.co.y, v.co.z)
    
    tree = KDTree( positions )

    smooth_heights = []
    for i, v in enumerate( bm.verts ):
        indices = tree.query_ball_point( v.co, r=3 )
        new_height = min( [heights[j] for j in indices] )
        smooth_heights.append( new_height )
    
    return smooth_heights

def mean_node_position( nodes ):
    
    mean_point = np.array((0.0,0.0,0.0))
    for n in nodes:
        mean_point += n.pos
    mean_point /= len(nodes)
    
    return mean_point

def calculate_max_node_heights( bm ):
    
    heights = []
    
    tree = mathutils.bvhtree.BVHTree.FromBMesh( bm )
    
    for v in bm.verts:
        direction = v.normal.normalized()
        _, _, _, dist = tree.ray_cast( v.co + direction*1e-3, direction )
        if not dist:    # If no hit was found, assume this node is not passable
            dist = 0
        heights.append( dist )
        
    return heights

def visualize_max_node_heights( bm, heights, name="MaxNodeHeights" ):
    
    me = bpy.data.meshes.new(name)  # add a new mesh
    obj = bpy.data.objects.new(name, me)  # add a new object using the mesh
    col = bpy.context.scene.collection
    col.objects.link(obj)
    
    bm_new = bmesh.new()
    
    for i, v in enumerate( bm.verts ):
        v1 = bm_new.verts.new( v.co )
        v2 = bm_new.verts.new( v.co + v.normal.normalized()*heights[i]*0.5 )
        bm_new.edges.new( (v1, v2) )
    
    # Finish up, write the bmesh back to the mesh
    bm_new.to_mesh(me)
    bm_new.free()  # free and prevent further access