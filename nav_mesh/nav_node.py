############################################################
# Copyright (C) 2022 Germanunkol
# License: MIT
############################################################

import numpy as np
import math

class SimpleNavNode():
    def __init__( self, pos, normal=None, max_height=0):
        self.pos = np.asarray(pos)
        self.normal = normal
        self.max_height = max_height
        self.blocked = False
    def get_pos_above( self, height, normal=None ):
        if normal:
            return self.pos + normal*height
        else:
            return self.pos + self.normal*height

class NavNode( SimpleNavNode ):
    
    # List of all nodes.
    # First dictionary holds all low-level nodes by index,
    # second dictionary holds all high-level nodes by index
    node_list = [{},{}]
    
    def __init__( self, pos, index, zone_id=None, level=0, normal=None, max_height=0):
        SimpleNavNode.__init__( self, pos, normal, max_height )

        # Neighbors of this node which are on the same "level"
        self.__direct_neighbors = set()
        
        # Neighbors of this node which are not in the same zone, i.e. links/entrances to another zone
        self.__next_level_neighbors = set()

        # Distances to each neighbor:
        self.__neighbor_dists = {}
        
        self.index = index
        self.zone_id = zone_id
        self.pos = pos
        self.normal = normal
        self.max_height = max_height
        
        self.parent_node_id = -1
        self.g = 0
        self.h = None
        
        # Only set when this is a high-level node representing an entrance between two zones:
        self.entrance = None
        
        self.level = level
        NavNode.node_list[self.level][index] = self
        
    def set_heuristic( self, heuristic ):
        self.h = heuristic
    
    def set_parent( self, parent_node, angle_penalty=0 ):
        if parent_node:
            self.g = parent_node.g + np.linalg.norm(parent_node.pos - self.pos) + angle_penalty
            self.parent_node_id = parent_node.index
        else:
            self.g = 0      # Distance from start node
            self.parent_node_id = -1

    def get_node_on_other_side( self, entrance ):
        # Return the node "opposite" of this node, i.e. the connected node which leads
        # through the given entrance.
        # Only call on low-level nodes which are part of an entrance!
        other_zone_id = entrance.get_other_zone_id( self.zone_id )
        closest_dist_squared = math.inf
        closest_node = None
        for n in self.next_level_neighbors:
            if n.zone_id == other_zone_id:
                #length_squared = ((n.pos - self.pos)**2).sum()
                squared = (n.pos - self.pos)**2
                length_squared = squared.sum()
                if length_squared < closest_dist_squared:
                    closest_dist_squared = length_squared
                    closest_node = n
                    
        return closest_node
        
    @property    
    def f( self ):
        #f = self.g + math.sqrt(self.h)       # Total cost
        f = self.g + self.h      # Total cost
        return f
    
    def __lt__( self, other ):
        return self.f < other.f
    
    def add_direct_neighbor( self, n ):
        assert self.index != n.index, "Error: Cannot add node with same index as neighbor!"
        self.__direct_neighbors.add( n.index )
        self.__neighbor_dists[n.index] = np.linalg.norm( self.pos - n.pos )
        
    @property
    def direct_neighbors( self ):
        for index in self.__direct_neighbors:
            yield NavNode.node_list[self.level][index]
    
    def add_next_level_neighbor( self, n ):
        assert self.index != n.index, "Error: Cannot add node with same index as neighbor!"
        self.__next_level_neighbors.add( n.index )
        self.__neighbor_dists[n.index] = np.linalg.norm( self.pos - n.pos )
        
    @property
    def next_level_neighbors( self ):
        for index in self.__next_level_neighbors:
            yield NavNode.node_list[self.level][index]
        
    @property
    def parent_node( self ):
        if self.parent_node_id in NavNode.node_list[self.level]:
            return NavNode.node_list[self.level][self.parent_node_id]
        return None

    def dist_to_neighbor( self, other ):
        return self.__neighbor_dists[other.index]

    def angle_penalty( self, other, max_ang = 0.5*math.pi, initial_dir = np.asarray((0,0,0)) ):
        """ If we have a parent, penalize tight angles in the path parent->self->other """

        # Determine the incoming direction. If we have a parent, use that direction.
        # Otherwise, use the given initial_dir.
        pn = self.parent_node
        if pn:
            from_parent = (self.pos - pn.pos)
        else:
            from_parent = initial_dir

        # The direction in which we are considering leaving this node:
        to_other = (other.pos - self.pos)

        # Let the angle between these determine the penalty: Small angles are penalized most:
        dist_from_parent = np.linalg.norm( from_parent )
        dist_to_other = np.linalg.norm( to_other )
        assert dist_from_parent > 0, initial_dir
        if dist_from_parent > 0 and dist_to_other > 0:
            dot = np.dot( from_parent, to_other )/(dist_from_parent*dist_to_other)
            dot = max( -1, min( dot, 1 ) )  # Only necessary for the occasional numerical imprecision
            ang = math.acos( dot )
            #if ang > max_ang:
            return 50*ang # Make it very expensive to use this steep ang (but not impossible)
        return 0    # Fallback
    
    def __str__( self ):
        
        direct_neighbors = [n for n in self.direct_neighbors]
        next_level_neighbors = [n for n in self.next_level_neighbors]
        return f"Node: {self.index}, zone ID: {self.zone_id}, ({self.pos}), (direct: {len(direct_neighbors)}, next-level: {len(next_level_neighbors)})"
    
    def __setstate__( self, state ):
        self.__dict__ = state

        self.blocked = False        # May not have been set by cave generator

#        p = state["pos"]
#        self.__dict__["pos"] = LVector3f( p[0], p[1], p[2] )
#        n = state["normal"]
#        if type(n) == np.ndarray:
#            self.__dict__["normal"] = LVector3f( n[0], n[1], n[2] )
        NavNode.node_list[self.level][self.index] = self
        #print("self.level", self.level, self.index,
        #        len(NavNode.node_list[self.level]), max(NavNode.node_list[self.level]))


