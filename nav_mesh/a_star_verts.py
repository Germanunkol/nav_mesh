import numpy as np
from sortedcontainers import SortedList

import os, sys
import bpy
import math
import bisect # for inserting into sorted list

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)
  
import src.utils as utils
# this next part forces a reload in case you edit the source after you first start the blender session
import importlib
importlib.reload(utils)

class Node():
    
    def __init__( self, vert, heuristic, parent_node=None ):
        self.vert = vert
        self.parent_node = parent_node
        
        # Calc g, the distance from the start node:
        if parent_node:
            self.g = parent_node.g + (parent_node.vert.co - vert.co).length
        else:
            self.g = 0      # Distance from start node
        self.h = heuristic       # Heuristic (estimated dist to goal)
        
    @property
    def f( self ):
        #f = self.g + math.sqrt(self.h)       # Total cost
        f = self.g + self.h      # Total cost
        return f
    
    def __lt__( self, other ):
        return self.f < other.f
    
#    def __str__( self ):
#        if self.parent_node:
#            return f"{self.vert.index} (parent: {self.parent_node.vert.index}) (g: {self.g}, h: {self.h}, f: {self.f})"
#        else:
#            return f"{self.vert.index} (parent: none) (g: {self.g}, h: {self.h}, f: {self.f})"
    
def heuristic( vert, end_verts ):
    min_val = np.inf
    for end in end_verts:
        min_val = min( (end.co - vert.co).length_squared, min_val )
    return math.sqrt( min_val )

def backtrack( final_node ):
    
    path = []
    
    cur_node = final_node
    while cur_node:
        
        path.insert(0, cur_node.vert)
        
        cur_node = cur_node.parent_node
        
    return path

def a_star( start_vert, end_verts ):
    
    open_list = list()
    closed = set()
    
    start_node = Node( start_vert, heuristic( start_vert, end_verts ) )
    bisect.insort( open_list, start_node )
    
    i = 0
    while len(open_list) > 0:
        
        #print(f"Loop start. Open nodes: {len(open)}")
        #print( [str(n) for n in open] )
        
        # Get node with lowest f value. We assume open_list is sorted!
        cur_node = open_list.pop(0)
        #print("\tChoosing ", cur_node)
        
        # Move node to "closed" list:
        closed.add( cur_node.vert.index )
        
        if cur_node.vert in end_verts:
            return backtrack( cur_node )
        
        f_updated = False
        for neighbor_vert in utils.get_neighbor_verts( cur_node.vert ):
            #print("\t\tneighbor:", neighbor_vert, neighbor_vert.index, f"(closed {neighbor_vert.index in closed})")
            if not neighbor_vert.index in closed:
                
                # Search the open list for a node 
                node_from_open = next((n for n in open_list if n.vert.index == neighbor_vert.index), None)
                # If this is not in the open list, create a new vert and add it to the open list:
                if not node_from_open:
                    h = heuristic( neighbor_vert, end_verts )
                    new_node = Node( neighbor_vert, h, parent_node = cur_node )
                    bisect.insort( open_list, new_node )
                else:
                    # If node is already on the open list, potentially update:
                    new_g = cur_node.g + (neighbor_vert.co - cur_node.vert.co).length
                    if node_from_open.g > new_g:
                        # Remove node, change values, re-add node:

                        open_list.remove( node_from_open )
                        
                        node_from_open.g = new_g  # WARNING: after this operation, "open" list may not be sorted any more. That's why we removed the node first.
                        node_from_open.parent_node = cur_node
                        
                        bisect.insort( open_list, node_from_open)
#        if i == 2:
#            return
        i += 1
        #return  #DEBUG
                        
                     
        
    # No path found:
    return None

def path_to_mesh( verts ):
    # Create a path-mesh given a list of verts. Verts must be in order!
        
    # Get a new object and mesh:
    name = "path: {verts[0].index} -> {verts[-1].index}"
    me = bpy.data.meshes.new(name)  # add a new mesh
    obj = bpy.data.objects.new(name, me)  # add a new object using the mesh
    col = bpy.context.scene.collection
    col.objects.link(obj)

    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    for v in verts:
        bm.verts.new( v.co )
    
    bm.verts.ensure_lookup_table()
    for i in range(len(bm.verts)-1):
        bm.edges.new( (bm.verts[i], bm.verts[i+1]) )
    
    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(me)
    bm.free()  # free and prevent further access

if __name__ == "__main__":
    
    import bpy, bmesh, random, time
    
    ob = bpy.context.object
    me = ob.data
    
    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    bm.verts.ensure_lookup_table()
    
    start_time = time.time()
    num_paths = 10
    for i in range(num_paths ):
        start_vert = bm.verts[ random.randint(0,len(bm.verts)-1) ]
        end_vert = bm.verts[ random.randint(0,len(bm.verts)-1) ]
        
        path = a_star( start_vert, [end_vert] )
    print("Average time: ", (time.time() - start_time)/num_paths )
    
    path_to_mesh( path )
    
    bm.free()
