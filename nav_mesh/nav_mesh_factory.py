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
import os, sys, random
import numpy as np
import math
import time

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append( dir )
    
from . import cube_clustering
from . import nav_mesh
from . import nav_node
from . import nav_room
from . import nav_room_entrance
from . import nav_mesh_factory_utils

# Re-load all modules. This is only necessary when running the scripts from within blender,
# where modules already loaded from a previous run need to be re-loaded in case the scripts
# changed since the last run. The 'import' statements above aren't sufficient for this,
# because python/blender caches the modules.
import importlib
importlib.reload(cube_clustering)
importlib.reload(nav_mesh)
importlib.reload(nav_node)
importlib.reload(nav_room)
importlib.reload(nav_room_entrance)
importlib.reload(nav_mesh_factory_utils)


class NavRoomInterface():
    # Helper class that represents the connection between two rooms.
    # Note: This connection may be made up of multiple, separate actual entrances!
    # For a class representing a single entrance, check out NavRoomEntrance
    
    def __init__( self, room_id_1, room_id_2 ):
        assert room_id_1 != room_id_2
        
        self.interface_id = NavRoomInterface.unique_interface_id( room_id_1, room_id_2 )
        
        self.node_connections = {}
        self.nodes = set()
        
        self.entrances = []
        
        #self.mean_point = None
        #self.center_vert = None
        
    def add_connection( self, node_room_1, node_room_2 ):
        
        assert (node_room_1.room_id in self.interface_id and node_room_2.room_id in self.interface_id), "Cannot add nodes to interface, room_id's must match those of the interface!"
        
        self.node_connections[node_room_1.index] = node_room_2.index
        self.node_connections[node_room_2.index] = node_room_1.index
        
        self.nodes.add( node_room_1 )
        self.nodes.add( node_room_2 )
    
    def calculate_entrances( self ):
        
        #print(f"Searching for entrances between rooms {self.interface_id}")
        #if self.interface_id == "(156, 162)":
            #print("==========================================\nDEBUG!")
        self.entrances = []
        
        nodes = self.nodes.copy()       # Will get modified, so make a copy!
        
        #for n in nodes:
            #print(n.index, n.room_id)
            #print( "\tsame level", [neigh.index for neigh in n.direct_neighbors])
            #print( "\tnext level", [neigh.index for neigh in n.next_level_neighbors])

        while len(nodes) > 0:
            
            # Start with any vertex:
            node = nodes.pop()
            front = [node]
            entrance_nodes = []
            
            #print("start node:", node.index)
            
            # Find other vertices belonging to the same entrance:
            while len( front ) > 0:
                
                node = front.pop()
                entrance_nodes.append( node )
                
                to_remove = set()         # New neighbors which are to be added to the front
                for neighbor in node.direct_neighbors:
                    #print("direct neighbor:", neighbor.index)
                    if neighbor in nodes:
                        #print("\tin")
                        front.append( neighbor )
                        to_remove.add( neighbor )
                for neighbor in node.next_level_neighbors:
                    #print("next_level neighbor:", neighbor.index)
                    if neighbor in nodes:
                        #print("\tin")
                        front.append( neighbor )
                        to_remove.add( neighbor )
                
                for n in to_remove:
                    nodes.remove( n )
                
            #print(f"\tFound entrance, num verts: {len(entrance_nodes)}")
            #print("\t", [n.index for n in entrance_nodes])
            self.entrances.append( nav_room_entrance.NavRoomEntrance( self.interface_id[0], self.interface_id[1], entrance_nodes ) )
            if len( entrance_nodes ) == 1 and len(self.nodes) == 3:
                dsa = adre
        
    @staticmethod
    def unique_interface_id( room_id_1, room_id_2 ):
        if room_id_1 < room_id_2:
            return (room_id_1, room_id_2)
        else:
            return (room_id_2, room_id_1)
        
#    @staticmethod
#    def get( room_id_1, room_id_2 ):
#        interface_id = NavRoomInterface.unique_interface_id( room_id_1, room_id_2 )
#        if interface_id in NavRoomInterface.all_interfaces:
#            return NavRoomInterface.all_interfaces[interface_id]
#        else:
#            return NavRoomInterface( room_id_1, room_id_2 )
def create_nav_mesh( nodes, num_rooms ):
    
    nav = nav_mesh.NavMesh( nodes, num_rooms )
    
    # Create list of nodes for each "room":
    room_nodes = {}
    for room_id in range(num_rooms):
        room_nodes[room_id] = []
        
    # For each room, fill its list of nodes with those nodes that have been 
    # assigned to the room:
    for i,node in enumerate( nodes ):
        room_nodes[node.room_id].append( node )
       
    #for room_id in range(num_rooms):
    #    print(f"found {len(room_nodes[room_id])} nodes for room {room_id}")
        
    ##self.allverts = numpy.empty( (num_verts,4) )
    
    high_level_node_index = 0
    
    # Create the rooms from the nodes:   
    for room_id in range(num_rooms):
        
        # Create room for the vertices:
        room = nav_room.NavRoom( room_id=room_id, nodes=room_nodes[room_id] )
        nav.add_room( room )
        
        room.create_center_node( index=high_level_node_index )
        high_level_node_index += 1
    
    # List of interfaces between rooms. All touching "rooms" make up exactly one interface
    interfaces = {}
    
    # Find all vertices which are at the border between rooms:
    for node in nodes:
        for next_level_neighbor in node.next_level_neighbors:
            unique_interface_id = NavRoomInterface.unique_interface_id( node.room_id, next_level_neighbor.room_id )
            if not unique_interface_id in interfaces:
                interface = NavRoomInterface( node.room_id, next_level_neighbor.room_id )
                interfaces[unique_interface_id] = interface
            
            interface = interfaces[unique_interface_id]
                
            # Create a connection between the vertices:
            interface.add_connection( node, next_level_neighbor )
    
    for interface_id,interface in interfaces.items():
        interface.calculate_entrances()
        # Add a pointer to this entrance to all the rooms it connects:
        for entrance in interface.entrances:
            room_1 = nav.rooms[entrance.room_id_1]
            room_2 = nav.rooms[entrance.room_id_2]
            
            room_1.add_entrance( entrance )
            room_2.add_entrance( entrance )
            # Create a node at the center of this entrance
            entrance.create_center_node( index=high_level_node_index )
            high_level_node_index += 1
            
            # Connect the room nodes to the new entrance node:
            room_1.node.add_direct_neighbor( entrance.node )
            room_2.node.add_direct_neighbor( entrance.node )
            entrance.node.add_direct_neighbor( room_1.node )
            entrance.node.add_direct_neighbor( room_2.node )
            
            nav.add_entrance( entrance )
            
    return nav

def create_high_level_mesh( nav_mesh ):
    
    # Get a new object and mesh:
    name = "nav_mesh_level1"
    me = bpy.data.meshes.new(name)  # add a new mesh
    obj = bpy.data.objects.new(name, me)  # add a new object using the mesh
    col = bpy.context.scene.collection
    col.objects.link(obj)

    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    
    # Get all the nodes, sort them by index:
    node_list = []
    for i,room in nav_mesh.rooms.items():
        node_list.append( room.node )
    for entrance in nav_mesh.entrances:
        node_list.append( entrance.node )
    node_list_sorted = sorted( node_list, key=lambda x: x.index )  # sort by index
    print( "number of rooms:", len(nav_mesh.rooms))
    print( "number of entrances:", len(nav_mesh.entrances))
    print( "room nodes:" )
    for n in node_list:
        print("\t", n)
    
    for node in node_list_sorted:
        bm.verts.new( node.pos )
    
    bm.verts.ensure_lookup_table()
    for i,room in nav_mesh.rooms.items():
        for i,entrances in room.entrances.items():
            for e in entrances:
                bm.edges.new( (bm.verts[room.node.index], bm.verts[e.node.index]) )

#        for room_id, r in self.rooms.items():
#            r.create_center_vert( bm )
#            for other_room_id, entrances in r.entrances.items():
#                for e in entrances:
#                    e.create_center_vert( bm )
#                    bm.edges.new( (r.center_vert, e.center_vert) )
#            
            

    # Finish up, write the bmesh back to the mesh
    bm.to_mesh(me)
    bm.free()  # free and prevent further access


def test_nav_mesh( nav_mesh ):
    start_time = time.time()
    num_runs = 1
    
    for i in range(num_runs):
        # Test A* path finding:
        start_node = nav_mesh.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
        end_node = nav_mesh.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
    
        nav_mesh.find_full_path( start_node, end_node )
        
    print("Average time: ", (time.time() - start_time)/num_runs )

def add_skip_connections( obj ):
    # Add connection to a neighbor's neighbors
    print("Adding skip connections")
    
    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(obj.data)   # fill it in from a Mesh
    
    offset_positions = {}
    for v in bm.verts:
        # Offset by 10 cm:
        o = v.co + v.normal*0.1
        
        # Store this offset position for later use
        offset_positions[v.index] = o
        
    num_edges = len( bm.edges )
    potential_connections = {}
        
    for v in bm.verts:
        pot_conn = set()
        if v.normal.length < 1e-10:
            continue
        for n in nav_mesh_factory_utils.get_neighbor_verts( v ):    
            if n.normal.length < 1e-10:
                continue
            ang = v.normal.angle( n.normal )
            if ang < math.pi*0.1:            
                for n2 in nav_mesh_factory_utils.get_neighbor_verts( n ):
                    if n2.normal.length < 1e-10:
                        continue
                    ang2 = v.normal.angle( n2.normal )
                    if ang2 < math.pi*0.1:
                        pot_conn.add( n2 )
        potential_connections[v] = pot_conn
                        
    for v, pot_conn in potential_connections.items():
        for p in pot_conn:
            try:
                bm.edges.new( (v, p) )
            except:
                pass
    print( "Added {len(bm.edges) - num_edges} new connections" )
    
    bm.to_mesh(obj.data)
    
def nav_mesh_from_object( obj ):
    obj = nav_mesh_factory_utils.duplicate_object( obj, "NavMesh_source" )
    add_skip_connections( obj )
    me = obj.data
    
    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    cube_side_length = 20
    assigned_rooms = cube_clustering.estimate_rooms( bm, cube_side_length )
    
    assigned_rooms, num_rooms = cube_clustering.split_non_connected_rooms( bm, assigned_rooms )
    
    heights = nav_mesh_factory_utils.calculate_max_node_heights( bm )
    #nav_mesh_factory_utils.visualize_max_node_heights( bm, heights )
    
    heights = nav_mesh_factory_utils.smooth_max_node_heights( bm, heights )
    nav_mesh_factory_utils.visualize_max_node_heights( bm, heights, "MaxNodeHeights_Smooth" )
    
    nodes = verts_to_nodes( bm.verts, assigned_rooms, heights )
    
    nav = create_nav_mesh( nodes, num_rooms )
   
    ######################################
    ## TODO: Check here!
    create_high_level_mesh( nav )
   
    #cube_clustering.create_debug_meshes( bm, assigned_rooms, num_rooms )

    bm.free()
    
    #test_nav_mesh( nav )
    
    filename = os.path.join( os.path.dirname(bpy.data.filepath), "nav_mesh.pickle" )
    nav.save_to_file( filename )
        
    #print("pickle version", pickle.format_version)
    #with open( filename, "rb" ) as f:
    #    nav_mesh_2 = pickle.load( f )
    #    print(nav_mesh_2)

    return nav

if __name__ == "__main__":
    import random
    
    obj = bpy.context.object
    nav = nav_mesh_from_object( obj )
    
    num_runs = 1

    for i in range(num_runs):
        # Test A* path finding:
        start_node = nav.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
        end_node = nav.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
    
        high_level_path, low_level_path = nav.find_full_path( start_node, end_node )
    
        nav_mesh_factory_utils.path_to_mesh( high_level_path )
        nav_mesh_factory_utils.path_to_mesh( low_level_path )
        
