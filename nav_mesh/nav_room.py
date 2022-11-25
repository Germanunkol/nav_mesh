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


class NavRoom():
    
    def __init__( self, room_id, nodes ):
        
        self.room_id = room_id
        
        # List of all the verts within this room. 
        # Should all hold an ".index" member which indexes into the complete(!) mesh
        self.nodes = nodes
        
        # Links to connected neighbor rooms:
        self.connections = {}
        self.entrances = {}
        
        self.mean_point = None
        self.center_vert = None
        self.node = None
        
        self.max_height = max( [n.max_height for n in nodes] )
    
    def add_entrance( self, e ):
        # Get the room id of the connected room:
        other_room_id = e.get_other_room_id( self.room_id )
        
        if not other_room_id in self.entrances.keys():
            # Create a list to hold entrances between this room and other_room_id:
            self.entrances[other_room_id] = []
        self.entrances[other_room_id].append( e )
        
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
          
