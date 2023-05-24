############################################################
# Copyright (C) 2022 Germanunkol
# License: MIT
############################################################

from . import nav_node
from . import nav_mesh_utils

# Re-load all modules. This is only necessary when running the scripts from within blender,
# where modules already loaded from a previous run need to be re-loaded in case the scripts
# changed since the last run. The 'import' statements above aren't sufficient for this,
# because python/blender caches the modules.
import importlib
importlib.reload(nav_node)
importlib.reload(nav_mesh_utils)



class NavZoneEntrance():
    # Represents a single entrance from one zone to another.
    # Note that there may be multiple (disconnected) entrances between the same
    # two zones. This class only represents one entrance, i.e. all the verts
    # in this entrance should be connected!
    
    all_entrances = {}
    
    def __init__( self, zone_id_1, zone_id_2, nodes ):
        self.zone_id_1 = zone_id_1
        self.zone_id_2 = zone_id_2
        
        self.nodes = nodes
        
        self.max_height = max( [n.max_height for n in nodes] )
        
        print("Building entrance:", [n.zone_id for n in nodes] )
        
        # Ensure all verts are connected:
        nodes_copy = nodes.copy()
        front = [nodes_copy.pop()]
        while len( front ) > 0:
            node = front.pop()
            for neighbor in node.direct_neighbors:
                if neighbor in nodes_copy:
                    nodes_copy.remove( neighbor )
                    front.append( neighbor )
            
            for neighbor in node.next_level_neighbors:
                if neighbor in nodes_copy:
                    nodes_copy.remove( neighbor )
                    front.append( neighbor )
        
        if len( nodes_copy ) > 0:
            raise ValueError("All verts in a NavZoneEntrance should be connected, but they aren't!")
        
        self.mean_point = None
        self.center_vert = None
        self.node = None
    
    def get_other_zone_id( self, zone_id ):
        if zone_id == self.zone_id_1:
            return self.zone_id_2
        elif zone_id == self.zone_id_2:
            return self.zone_id_1
        else:
            raise ValueError( f"Asking for 'other' zone id of entrance but given zone id {zone_id} is not in the entrance's zone ids ({self.zone_id_1} and {self.zone_id_2})!" )
        
    @property
    def center( self ):
        if not self.mean_point:
            self.mean_point = nav_mesh_utils.mean_node_position( self.nodes )
        return self.mean_point
        
    
    def create_center_vert( self, bm ):
        if not self.center_vert:
            self.center_vert = bm.verts.new( self.center )
            
    def create_center_node( self, index ):
        if not self.node:
            self.node = nav_node.NavNode( self.center, index, level=1, max_height=self.max_height )
            self.node.entrance = self
            
    def __str__( self ):
        nodes_zone_1 = 0
        nodes_zone_2 = 0
        for n in self.nodes:
            if n.zone_id == self.zone_id_1:
                nodes_zone_1 += 1
            if n.zone_id == self.zone_id_2:
                nodes_zone_2 += 1
            
        return f"Entrance: {self.zone_id_1} ({nodes_zone_1} nodes) -> {self.zone_id_2} ({nodes_zone_2} nodes), total nodes: {len(self.nodes)}"
