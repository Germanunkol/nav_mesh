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
try:
    from . import debug_utils
except:
    pass
from .exceptions import PathUnreachableError

# Remove to disable panda3d dependency:

class NavMesh():
    
    def __init__( self, nodes, num_zones ):
        
        num_nodes = len(nodes)
        self.nodes = nodes
        self.zones = {}
        self.entrances = []

        self.debug_display_node = None
        self.debug_display_active = False

        #self.init_kd_tree()
    def destroy( self ):
        if self.debug_display_node:
            self.debug_display_node.remove_node()

    def init_kd_tree( self ):
        nodes_tensor = np.empty( (len(self.nodes),3) )
        for i,n in enumerate(self.nodes):
            nodes_tensor[i,:] = n.pos

        self.kd_tree = KDTree( nodes_tensor )

    def find_closest_node( self, pos ):

        dist, index = self.kd_tree.query( (pos.x, pos.y, pos.z) )
        return self.nodes[index]
    
    def add_zone( self, zone ):
        self.zones[zone.zone_id] = zone
        
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
        for high_level_path, low_level_path in finder:
            if full_high_level_path is None:
                full_high_level_path = high_level_path
            full_low_level_path += low_level_path

        return full_high_level_path, full_low_level_path

    def find_path_sections( self, start_node, end_node, end_pos=None, avoid=[], min_height=0,
            initial_dir = np.asarray((0,0,0)) ):
        return PathSectionFinder( self, start_node, end_node, end_pos, avoid, min_height,
                initial_dir )

    def find_path_to_next_entrance( self, start_node, prev_high_level_path,
            initial_dir = np.asarray((0,0,0)), final_target_node = None, min_height = 0,
            debug_display_active = False ):
        
        # Find the next entrance along the high level path:
        next_entrance = self.find_next_entrance( prev_high_level_path )

        if self.debug_display_node:
            self.debug_display_node.remove_node()

        if next_entrance:

            # "Jump through" the entrance:
            #prev_end_node = prev_low_level_path[-1]
            #next_start_node = prev_end_node.get_node_on_other_side( next_entrance )

            #print("Next entrance:", next_entrance)l
           
            # Find path to the entrance:
            # 1. Choose the nodes which are part of the current zone and part of the entrance
            # to the next zone:
            entrance_nodes = [n for n in next_entrance.nodes \
                    if n.zone_id == start_node.zone_id]
            # 2. Find the path to one of those:
            if not debug_display_active:
                low_level_path = a_star.a_star( start_node, entrance_nodes, initial_dir=initial_dir,
                        final_target_node = final_target_node, min_height=min_height )
            else:
                low_level_path, node_debug_info = a_star.a_star( start_node, entrance_nodes, initial_dir=initial_dir,
                        final_target_node = final_target_node, min_height=min_height,
                        return_debug_info = True )
                if self.debug_display_active:
                    self.debug_display_node = debug_utils.display_debug_info( node_debug_info,
                            self.nodes )
            
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
        for k, r in self.zones.items():
            n = r.node
            nav_node.NavNode.node_list[n.level][n.index] = n

        self.debug_display_node = None

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

    def __init__( self, nav_mesh, start_node, end_node, end_pos=None, avoid=[], min_height=0,
            initial_dir = np.asarray((0,0,0)) ):
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
        self.initial_dir = initial_dir

        self.debug_display_active = False
        self.debug_display_node = None
    
        # TODO!!
        self.avoid = avoid
        self.min_height = min_height

        self.last_section_found = False

        # need to cross at least one entrance to another sector?
        if self.start_node.zone_id != self.end_node.zone_id: 
            start_high_level_node = self.nav_mesh.zones[self.start_node.zone_id].node
            end_high_level_node = self.nav_mesh.zones[self.end_node.zone_id].node
            
            high_level_path = a_star.a_star( start_high_level_node, [end_high_level_node] )
                    #min_height = self.min_height )
            
            if not high_level_path:
                self.last_section_found = True
       
            self.high_level_path = high_level_path
            self.cur_start_node = self.start_node
         
        else:   # start and end in same sector
            self.high_level_path = []        # TODO: Maybe return zone node instead?
            self.cur_start_node = self.start_node

    def destroy( self ):
        if self.debug_display_node:
            self.debug_display_node.remove_node()

    def __next__( self ):

        # End iteration:
        if self.last_section_found:
            raise StopIteration()

        if self.debug_display_node:
            self.debug_display_node.remove_node()

        if self.cur_start_node.zone_id == self.end_node.zone_id:
            # This means that there is no further
            # entrance on the path and we've reached the last zone:
            if not self.debug_display_active:
                low_level_path = a_star.a_star( self.cur_start_node, [self.end_node],
                        initial_dir = self.initial_dir, min_height = self.min_height )
            else:
                low_level_path, node_debug_info = a_star.a_star( self.cur_start_node,
                        [self.end_node],
                        initial_dir = self.initial_dir, min_height = self.min_height,
                        return_debug_info = True )
                if self.debug_display_active:
                    self.debug_display_node = debug_utils.display_debug_info( node_debug_info,
                            self.nav_mesh.nodes )

            self.last_section_found = True   # Stop iteration after this

            # If an end position is given, we don't want to end at the last node,
            # but rather on the last position:
            if self.end_pos:
                if len(low_level_path) > 0:
                    normal = low_level_path[-1].normal
                else:
                    normal = LVector3f(0,0,1)
                # Create a (temporary) node at the target position which we can add
                # to the path:
                tmp_end_node = nav_node.SimpleNavNode( self.end_pos, normal=normal )
             
                if len(low_level_path) > 1:
                    # If the distance to the last path node would be beyond the target position,
                    # remove this last node:
                    dist_last_segment = np.linalg.norm(low_level_path[-2].pos - low_level_path[-1].pos)
                    dist_to_end = np.linalg.norm(tmp_end_node.pos - low_level_path[-1].pos)
                    if dist_to_end < dist_last_segment:
                        del low_level_path[-1]


                low_level_path.append( tmp_end_node )
                

            return [], low_level_path

        high_level_path, low_level_path, next_entrance = \
                self.nav_mesh.find_path_to_next_entrance(
                    self.cur_start_node, self.high_level_path, self.initial_dir,
                    final_target_node = self.end_node, min_height = self.min_height,
                    debug_display_active = self.debug_display_active )

        if low_level_path:
            # "Jump through" next entrance:
            prev_end_node = low_level_path[-1]
            exit_pos = prev_end_node.pos
            self.cur_start_node = prev_end_node.get_node_on_other_side( next_entrance )
            self.high_level_path = high_level_path
            entry_pos = self.cur_start_node.pos

            self.initial_dir = entry_pos - exit_pos

            return high_level_path, low_level_path
        else:
            raise PathUnreachableError("Unexpected end of path")

    def __iter__( self ):
        return self


    def set_debug_display( self, active=True ):
        self.debug_display_active = active
        if not active:
            if self.debug_display_node:
                self.debug_display_node.remove_node()

