import numpy as np
from sortedcontainers import SortedList

import os, sys
import bpy
import math
import bisect # for inserting into sorted list

def heuristic( node, end_nodes ):
    min_val = np.inf
    for end in end_nodes:
        length_squared = ((end.pos - node.pos)**2).sum()
        min_val = min( length_squared, min_val )
    return math.sqrt( min_val )

def backtrack( final_node ):
    
    path = []
    
    cur_node = final_node
    while cur_node:
        # insert at beginning of path:
        path.insert( 0, cur_node )
        
        cur_node = cur_node.parent_node
        
    return path

def a_star( start_node, end_nodes, verbose=False ):
    
    if verbose:
        print( "Searching path. From:", start_node)
        print( "\tto:", [str(n) for n in end_nodes] )
    
    for n in end_nodes:
        assert n.room_id == start_node.room_id, "Cannot run A* for nodes from separete rooms. room_id must be the same for each node!"
    
    assert len( end_nodes ) > 0, "Cannot run A*, end nodes list is empty!"
    
    open_list = list()
    closed = set()
    
    start_node.set_parent( None )
    bisect.insort( open_list, start_node )
    
    while len(open_list) > 0:
        
        if verbose:
            print(f"Loop start. Open nodes: {len(open_list)}")
        #print( [str(n) for n in open] )
        
        # Get node with lowest f value. We assume open_list is sorted!
        cur_node = open_list.pop(0)
        if verbose:
            print("\tChoosing ", cur_node)
        
        # Move node to "closed" list:
        closed.add( cur_node.index )
        
        if cur_node in end_nodes:
            if verbose:
                print("\tTarget node found. Returning path.")
            return backtrack( cur_node )
        
        f_updated = False
        for neighbor_node in cur_node.direct_neighbors:
            if verbose:
                print("\t\tneighbor:", neighbor_node, neighbor_node.index, f"(closed {neighbor_node.index in closed})")
            if not neighbor_node.index in closed:
                
                # If this is not in the open list, create a new vert and add it to the open list:
                if not neighbor_node in open_list:
                    h = heuristic( neighbor_node, end_nodes )
                    neighbor_node.set_heuristic( h )
                    neighbor_node.set_parent( cur_node ) 
                    bisect.insort( open_list, neighbor_node )
                else:
                    # If node is already on the open list, potentially update:
                    new_g = cur_node.g + np.linalg.norm(neighbor_node.pos - cur_node.pos)
                    if neighbor_node.g > new_g:
                        # Remove node, change values, re-add node:

                        open_list.remove( neighbor_node )
                        
                        # WARNING: after this operation, "open" list may not be sorted any more. That's why we removed the node first.
                        neighbor_node.set_parent( cur_node )
                        
                        bisect.insort( open_list, neighbor_node )                        
                     
        
    # No path found:
    if verbose:
        print("\tNo path found.")
    return None

if __name__ == "__main__":
    
    import bpy, bmesh, random, time
    import navmesh
    
    ob = bpy.context.object
    me = ob.data
    
    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    bm.verts.ensure_lookup_table()
    nodes = navmesh.verts_to_nodes( bm.verts, assigned_rooms=[0 for v in bm.verts] )
    
    start_time = time.time()
    num_paths = 10
    for i in range(num_paths ):
        start_node = nodes[ random.randint(0,len(nodes)-1) ]
        end_nodes = [nodes[ random.randint(0,len(nodes)-1) ] for i in range(5)]
        
        path = a_star( start_node, end_nodes )
    print("Average time: ", (time.time() - start_time)/num_paths )
    
    path_to_mesh( path )
    
    bm.free()
