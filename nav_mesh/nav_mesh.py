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
from . import loader
from . import nav_node

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

        full_low_level_path = []
        full_high_level_path = None
        
        finder = PathSectionFinder( self, start_node, end_node )
        #print(finder)
        for high_level_path, low_level_path in finder:
            if full_high_level_path is None:
                full_high_level_path = high_level_path
            full_low_level_path += low_level_path

        return full_high_level_path, full_low_level_path

    def find_path_sections( self, start_node, end_node, end_pos=None, avoid=[], max_height=0 ):
        return PathSectionFinder( self, start_node, end_node, end_pos, avoid, max_height )

    def find_path_to_next_entrance( self, start_node, prev_high_level_path ):
        
        # Find the next entrance along the high level path:
        next_entrance = self.find_next_entrance( prev_high_level_path )

        if next_entrance:

            # "Jump through" the entrance:
            #prev_end_node = prev_low_level_path[-1]
            #next_start_node = prev_end_node.get_node_on_other_side( next_entrance )

            #print("Next entrance:", next_entrance)l
           
            # Find path to the entrance:
            # 1. Choose the nodes which are part of the current room and part of the entrance
            # to the next room:
            entrance_nodes = [n for n in next_entrance.nodes \
                    if n.room_id == start_node.room_id]
            # 2. Find the path to one of those:
            low_level_path = a_star.a_star( start_node, entrance_nodes )
            
            #a_star.path_to_mesh( low_level_path )
            #print("Found detail level path:", len(low_level_path) )
            
            
            # Find next path:
            new_high_level_path = self.get_subpath( prev_high_level_path, next_entrance.node )
            #print("Truncated high level path:", len(cur_high_level_path) )
            
            return new_high_level_path, low_level_path, next_entrance
        else:
            return None, None, None
 

    def find_random_path( self ):
        start_node = self.nodes[ random.randint(0,len(self.nodes)-1) ]
        end_node = self.nodes[ random.randint(0,len(self.nodes)-1) ]
        path = self.find_full_path( start_node, end_node )
        return path

    def __setstate__( self, state ):
        self.__dict__ = state
        self.init_kd_tree()

        ####################################
        # Warning: For some reason, the nodes adding themselves to the NavNode.node_list
        # no longer works. I suspoect this is due to the renamed_load function, which
        # does some magic to the imports. Somehow, the nodes add themselves, but after
        # being imported, only the high-level nodes (node.level == 1) are present, the
        # other list is somehow empty. I don't know why, but it may be that somehow the
        # NavNode module is imported twice under different names, and then these different
        # modules are used? Doesn't explain why there is a state during loading where both
        # lists seem to be filled correctly, though.
        # Anyways, adding them here again manually solves the issue:
        for n in self.nodes:
            nav_node.NavNode.node_list[n.level][n.index] = n
        for k, r in self.rooms.items():
            n = r.node
            nav_node.NavNode.node_list[n.level][n.index] = n

    def save_to_file( self, filename = "nav_mesh.pickle" ):
        with open( filename, "wb" ) as f:
            pickle.dump( self, f )
            print("Saved nav_mesh as:", filename)
       
    @staticmethod
    def load_from_file( filename ):

        print("Attempting to load NavMesh from file:", filename)
        with open( filename, "rb" ) as f:
            #nav_mesh = pickle.load( f )
            nav_mesh = loader.renamed_load( f, "lib.nav_mesh", "lib.pathfinding" )
            print( "\tNavMesh loaded." )
        return nav_mesh

class PathSectionFinder:

    def __init__( self, nav_mesh, start_node, end_node, end_pos=None, avoid=[], max_height=0 ):
        """ Find a (sub-part of a) path. If start_node and end_node are in the same sector, find
        the full detail-level path. If they are not, find the full high-level path and the detail-
        level path for the first sector.

        If end_pos is given, it is appended to the final low-level-path.

        The 'avoid' parameter is an (optional) list of nodes which should be considered blocked"""

        self.high_level_path = None
        self.start_node = start_node
        self.end_node = end_node
        self.nav_mesh = nav_mesh
        self.end_pos = end_pos  # Optional, could be None!

        # TODO!!
        self.avoid = avoid
        self.max_height = max_height

        self.last_section_found = False

        # need to cross at least one entrance to another sector?
        if self.start_node.room_id != self.end_node.room_id: 
            start_high_level_node = self.nav_mesh.rooms[self.start_node.room_id].node
            end_high_level_node = self.nav_mesh.rooms[self.end_node.room_id].node
            
            high_level_path = a_star.a_star( start_high_level_node, [end_high_level_node] )
            
            if not high_level_path:
                self.last_section_found = True
       
            self.high_level_path = high_level_path
            self.cur_start_node = self.start_node
         
        else:   # start and end in same sector
            self.high_level_path = []        # TODO: Maybe return room node instead?
            self.cur_start_node = self.start_node

    def __next__( self ):

        # End iteration:
        if self.last_section_found:
            raise StopIteration()

        if self.cur_start_node.room_id == self.end_node.room_id:
            # This means that there is no further
            # entrance on the path and we've reached the last room:
            low_level_path = a_star.a_star( self.cur_start_node, [self.end_node] )
            self.last_section_found = True   # Stop iteration after this

            if self.end_pos:
                # If an end position is given, we don't want to end at the last node,
                # but rather on the last position:
                if len(low_level_path) > 0:
                    normal = low_level_path[-1].normal
                else:
                    normal = LVector3f(0,0,1)
                temp_end_node = nav_node.SimpleNavNode( self.end_pos, normal=normal )
                low_level_path.append( temp_end_node )
                
            return [], low_level_path

        high_level_path, low_level_path, next_entrance = \
                self.nav_mesh.find_path_to_next_entrance(
                    self.cur_start_node, self.high_level_path )

        if low_level_path:
            # "Jump through" next entrance:
            prev_end_node = low_level_path[-1]
            self.cur_start_node = prev_end_node.get_node_on_other_side( next_entrance )
            self.high_level_path = high_level_path

            return high_level_path, low_level_path
        else:
            raise Exception("Unexpected end of path")

    def __iter__( self ):
        return self


