############################################################
# Copyright (C) 2022 Germanunkol
# License: GPL v 3
# 
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This file is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
############################################################


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


def get_neighbor_verts( v ):

    neighbors = [ e.other_vert( v ) for e in v.link_edges]
    return neighbors
 
def duplicate_object( orig_obj, new_name ):
    new_obj = orig_obj.copy()
    new_obj.data = orig_obj.data.copy()
    new_obj.name = new_name
    
    bpy.context.collection.objects.link(new_obj)
    return new_obj


