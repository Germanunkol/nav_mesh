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
import random
import numpy as np
from scipy.spatial import KDTree
from . import nav_node

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

def path_to_mesh( nodes ):
    # Create a path-mesh given a list of nodes. Nodes must be in order!

    print(f"Turning path to mesh: {len(nodes)} nodes")
        
    # Get a new object and mesh:
    name = f"path: {nodes[0].index} -> {nodes[-1].index}"
    me = bpy.data.meshes.new(name)  # add a new mesh
    obj = bpy.data.objects.new(name, me)  # add a new object using the mesh
    col = bpy.context.scene.collection
    col.objects.link(obj)

    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    for node in nodes:
        bm.verts.new( node.pos )
    
    bm.verts.ensure_lookup_table()
    for i in range(len(bm.verts)-1):
        bm.edges.new( (bm.verts[i], bm.verts[i+1]) )
    
    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(me)
    bm.free()  # free and prevent further access

    
def verts_to_nodes( verts, assigned_rooms, heights ):
    
    verts.ensure_lookup_table()
    
    nodes = []
    for i, v in enumerate( verts ):
        node = nav_node.NavNode(np.array(v.co), v.index, assigned_rooms[v.index],
                normal=np.array(v.normal), max_height=heights[i] )
        nodes.append( node )
    
    for i, v in enumerate( verts ):
        node = nodes[i]
        for n in get_neighbor_verts( v ):
            if assigned_rooms[v.index] == assigned_rooms[n.index]:
                node.add_direct_neighbor( nodes[n.index] )
            else:
                node.add_next_level_neighbor( nodes[n.index] )
                
    return nodes

def test_nav_mesh( mesh ):
    
    start_room = random.choice( mesh.rooms )
    end_room = random.choice( mesh.rooms )
    start_node = random.choice( start_room.nodes )
    end_node = random.choice( end_room.nodes )

    high_level_path, low_level_path = mesh.find_full_path( start_node, end_node )

    path_to_mesh( high_level_path )
    path_to_mesh( low_level_path )
