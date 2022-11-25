############################################################
# Copyright (C) 2022 Germanunkol
# License: MIT
############################################################

import os, sys, math
import time
import numpy as np
import pickle
import random
from scipy.spatial import KDTree

from . import a_star

class NavMesh():
    
    def __init__( self, nodes, num_rooms ):
        
        num_nodes = len(nodes)
        self.nodes = nodes
        self.rooms = {}
        self.entrances = []
        
        #self.init_kd_tree()

    def init_kd_tree( self ):
        nodes_tensor = np.empty( (len(self.nodes),3) )
        for i,n in enumerate(self.nodes):
            nodes_tensor[i,:] = n.pos

        self.kd_tree = KDTree( nodes_tensor )

    def find_closest_node( self, pos ):

        dist, index = self.kd_tree.query( (pos.x, pos.y, pos.z) )
        return self.nodes[index]
    
    def add_room( self, room ):
        self.rooms[room.room_id] = room
        
    def add_entrance( self, entrance ):
        self.entrances.append( entrance )
    
    def find_next_entrance( self, high_level_path ):
        # Find and retrun first entrance in high_level_path:
        for node in high_level_path:
            if node.entrance:
                return node.entrance
        return None
    
    def get_subpath( self, full_path, node ):
        # Get the subpath of full_path which starts after "node"
        subpath = []
        node_found = False
        for n in full_path:
            if node_found:
                subpath.append( n )
            if n == node:
                node_found = True
        return subpath
        
    def find_full_path( self, start_node, end_node ):
        start_high_level_node = self.rooms[start_node.room_id].node
        end_high_level_node = self.rooms[end_node.room_id].node
        
        #print("Searching for path from, to:", start_high_level_node, end_high_level_node )
        high_level_path = a_star.a_star( start_high_level_node, [end_high_level_node] )
    
        #print("Found high level path:", len(high_level_path) )
        
        #a_star.path_to_mesh( high_level_path )

        full_low_level_path = []
        
        cur_start_node = start_node
        cur_high_level_path = high_level_path.copy()
        next_entrance = self.find_next_entrance( high_level_path )
        while next_entrance:
            #print("Next entrance:", next_entrance)
            
            entrance_nodes = [n for n in next_entrance.nodes if n.room_id == cur_start_node.room_id]
            low_level_path = a_star.a_star( cur_start_node, entrance_nodes )
            
            #a_star.path_to_mesh( low_level_path )
            #print("Found detail level path:", len(low_level_path) )
            
            # "Jump through" the entrance:
            cur_end_node = low_level_path[-1]
            cur_start_node = cur_end_node.get_node_on_other_side( next_entrance )
            #print( "Jump through:", cur_end_node, "->", cur_start_node )
            
            # Find next path:
            cur_high_level_path = self.get_subpath( cur_high_level_path, next_entrance.node )
            #print("Truncated high level path:", len(cur_high_level_path) )
            
            next_entrance = self.find_next_entrance( cur_high_level_path )
            
            full_low_level_path += low_level_path
        
        #print("Getting final path:")
        low_level_path = a_star.a_star( cur_start_node, [end_node] )
        #a_star.path_to_mesh( low_level_path )
        #print("Found detail level path:", len(low_level_path) )

        return high_level_path, full_low_level_path

    def find_partial_path( self, start_node, end_node, avoid=[], max_height=0 ):
        """ Find a (sub-part of a) path. If start_node and end_node are in the same sector, find
        the full detail-level path. If they are not, find the full high-level path and the detail-
        level path for the first sector.
        The 'avoid' parameter is an (optional) list of nodes which should be considered blocked"""

        # need to cross at least one entrance to another sector?
        if start_node.room_id != end_node.room_id: 
            start_high_level_node = self.rooms[start_node.room_id].node
            end_high_level_node = self.rooms[end_node.room_id].node
            
            #print("Searching for path from, to:", start_high_level_node, end_high_level_node )
            t = time.time()
            import cProfile, pstats
            profiler = cProfile.Profile()
            profiler.enable()
            high_level_path = a_star.a_star( start_high_level_node, [end_high_level_node] )
            profiler.disable()
            stats = pstats.Stats(profiler).sort_stats('ncalls')
            stats.print_stats()
            print("\thigh_level_path:", time.time()-t)
            t = time.time()

            print("high_level_path", high_level_path)

            if not high_level_path:
                return None, None
        
            #print("Found high level path:", len(high_level_path) )
            
            #a_star.path_to_mesh( high_level_path )

            cur_start_node = start_node
            cur_high_level_path = high_level_path.copy()
            next_entrance = self.find_next_entrance( high_level_path )
            print("\tnext entrance:", time.time()-t)
            t = time.time()
            #print("Next entrance:", next_entrance)
                
            entrance_nodes = [n for n in next_entrance.nodes if n.room_id == cur_start_node.room_id]
            print("\tlist:", time.time()-t)
            t = time.time()
            low_level_path = a_star.a_star( cur_start_node, entrance_nodes, avoid=avoid,
                    max_height=max_height )
            print("\tlow_level_path:", time.time()-t)
            t = time.time()

        else:   # start and end in same sector
            high_level_path = []        # TODO: Maybe return room node instead?
            t = time.time()
            low_level_path = a_star.a_star( start_node, [end_node], avoid=avoid,
                    max_height=max_height )
            print("\tlow_level_path:", time.time()-t)
        #print("Found detail level path:", len(low_level_path) )

        return high_level_path, low_level_path
    
    def __setstate__( self, state ):
        self.__dict__ = state
        self.init_kd_tree()
       
    @staticmethod
    def load_from_file( filename ):

        print("Attempting to load NavMesh from file:", filename)
        with open( filename, "rb" ) as f:
            nav_mesh = pickle.load( f )
            print( "\tNavMesh loaded." )
        return nav_mesh

    def find_random_path( self ):
        start_node = self.nodes[ random.randint(0,len(self.nodes)-1) ]
        end_node = self.nodes[ random.randint(0,len(self.nodes)-1) ]
        path = self.find_full_path( start_node, end_node )
        return path

if __name__ == "__main__":
    
    filename = "nav_mesh.pickle"    # TODO: add path?
    with open( filename, "rb" ) as f:
        nav_mesh = pickle.load( f )
        
    import time, random
    
    start_time = time.time()
    num_runs = 1
    
    import nav_mesh_factory
    nav_mesh_factory.create_high_level_mesh( nav_mesh )
    
    for i in range(num_runs):
        # Test A* path finding:
        start_node = nav_mesh.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
        end_node = nav_mesh.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
    
        nav_mesh.find_full_path( start_node, end_node )
        
    print("Average time: ", (time.time() - start_time)/num_runs )


