import numpy as np
from sortedcontainers import SortedList

import os, sys
import math
import bisect # for inserting into sorted list
import random

from .exceptions import PathUnreachableError

#    def __str__( self ):
#        if self.parent_node:
#            return f"{self.vert.index} (parent: {self.parent_node.vert.index}) (g: {self.g}, h: {self.h}, f: {self.f})"
#        else:
#            return f"{self.vert.index} (parent: none) (g: {self.g}, h: {self.h}, f: {self.f})"
    
def eucledian( node, end_nodes ):
    min_val = np.inf
    for end in end_nodes:
        #length_squared = ((end.pos - node.pos)**2).sum()
        squared = (end.pos - node.pos)**2
        length_squared = squared[0] + squared[1] + squared[2]
        min_val = min( length_squared, min_val )
    return math.sqrt( min_val )

def manhatten( node, end_nodes ):
    min_val = np.inf
    for end in end_nodes:
        #length_squared = ((end.pos - node.pos)**2).sum()
        d = abs(end.pos[0]-node.pos[0]) + abs(end.pos[1]-node.pos[1]) + abs(end.pos[2]-node.pos[2])
        min_val = min( d, min_val )
    return min_val

def backtrack( final_node ):
    
    path = []
   
    cur_node = final_node
    while cur_node:
        # insert at beginning of path:
        path.insert( 0, cur_node )
        
        cur_node = cur_node.parent_node
        
    return path

def a_star( start_node, end_nodes, verbose=False, max_end_nodes=2, avoid=[], min_height=0,
        initial_dir = None, final_target_node=None, return_debug_info=False ):
    """
    - start_node: a single node at which to start searching
    - end_nodes: multiple nodes, the path will end at one of these.
    - avoid: nodes which should be considered "blocked"
    - min_height: only nodes are allowed to be traversed which have a max_height higher than the
        min_height given here. (TODO)
    """
    #if len( end_nodes ) > max_end_nodes:
        #print( f"reducing end nodes from {len(end_nodes)} to {max_end_nodes}")
    assert len( end_nodes ) > 0, "Cannot run A*, end nodes list is empty!"

    valid_end_nodes = [n for n in end_nodes if n.max_height >= min_height]
    if len(valid_end_nodes) < 0:
        raise PathUnreachableError( "All end nodes are too low!" )
    #end_nodes = random.sample(valid_end_nodes, max_end_nodes)      # TODO: Reenable?
    #end_nodes = valid_end_nodes[0:max_end_nodes]
    end_nodes = valid_end_nodes     # Use all valid end nodes. This seems to be the most stable

    #assert start_node.max_height > max_height, "The given start node for the path search has a max_height which is lower than the given max_height!"

    use_angular_penalty = (initial_dir is not None)
    
    if verbose:
        print( "Searching path. From:", start_node)
        print( "\tto:", [str(n) for n in end_nodes] )
    
    for n in end_nodes:
        assert n.zone_id == start_node.zone_id, "Cannot run A* for nodes from separete Zones. Zone_id must be the same for each node!"

    
    
    open_list = list()
    closed = set()
    # Add all the nodes to avoid to the "closed" list:
    for n in avoid:
        closed.add( n.index )
    
    start_node.set_parent( None )
    bisect.insort( open_list, start_node )

    # If given, steer towards the final target node. Otherwise, steer towards any of the end nodes:
    if final_target_node:
        target_nodes_for_heuristic = [final_target_node]
    else:
        target_nodes_for_heuristic = end_nodes
    
    iterations = 0
    while len(open_list) > 0:
        iterations += 1
        
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
            if not return_debug_info:
                return backtrack( cur_node )
            else:
                debug_info = {
                        "closed": closed,
                        "open_list": open_list,
                        "end_nodes": end_nodes
                        }
                return backtrack( cur_node ), debug_info
            

        parent = cur_node.parent_node
        if use_angular_penalty:
            if parent:
                vec_from_parent = cur_node.pos - parent.pos
                dir_from_parent = vec_from_parent/np.linalg.norm( vec_from_parent )
            else:
                dir_from_parent = initial_dir

        angle_penalty = 0
        
        f_updated = False
        for neighbor_node in cur_node.direct_neighbors:
            if verbose:
                print("\t\tneighbor:", neighbor_node, neighbor_node.index, f"(closed {neighbor_node.index in closed})")
            #if neighbor_node.blocked:
            #    continue
            if neighbor_node.max_height < min_height:
                continue
            if not neighbor_node.index in closed:
                
                # If this is not in the open list, create a new vert and add it to the open list:
                if not neighbor_node in open_list:
                    h = eucledian( neighbor_node, target_nodes_for_heuristic )
                    #h = eucledian( neighbor_node, end_nodes )
                    neighbor_node.set_heuristic( h )
                   
                    if use_angular_penalty:
                        angle_penalty = cur_node.angle_penalty(
                                neighbor_node, initial_dir=dir_from_parent )

                    #angle_penalty = 0   # DEBUG!
                    neighbor_node.set_parent( cur_node, angle_penalty ) 
                    bisect.insort( open_list, neighbor_node )
                else:
                    # If node is already on the open list, potentially update:
                    #new_g = cur_node.g + np.linalg.norm(neighbor_node.pos - cur_node.pos)
                    if use_angular_penalty:
                        angle_penalty = cur_node.angle_penalty(
                                neighbor_node, initial_dir=dir_from_parent )
                    #angle_penalty = 0   # DEBUG!
                    new_g = cur_node.g + \
                            cur_node.dist_to_neighbor( neighbor_node ) + \
                            angle_penalty
                    if neighbor_node.g > new_g:
                        # Remove node, change values, re-add node:
                        open_list.remove( neighbor_node )
                        # WARNING: after the following operation, "open" list may not be sorted
                        # any more!
                        # That's why we removed the node first and then re-add it.
                        neighbor_node.set_parent( cur_node, angle_penalty=angle_penalty )
                        bisect.insort( open_list, neighbor_node )                        

    print("NO END NODE FOUND! iterations:", iterations)
    # No path found:
    if verbose:
        print("\tNo path found.")
    #return None
    raise PathUnreachableError("Could not find path to target")

def path_to_mesh( nodes ):
    
    import bmesh
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
    
    for node in nodes:
        bm.verts.new( node.pos )
    
    bm.verts.ensure_lookup_table()
    for i in range(len(bm.verts)-1):
        bm.edges.new( (bm.verts[i], bm.verts[i+1]) )
    
    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(me)
    bm.free()  # free and prevent further access

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
