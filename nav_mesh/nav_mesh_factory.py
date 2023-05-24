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
    
#from . import cube_clustering
from . import size_clustering
from . import clustering_utils
from . import nav_mesh
from . import nav_node
from . import nav_zone
from . import nav_zone_entrance
from . import nav_mesh_factory_utils

# Re-load all modules. This is only necessary when running the scripts from within blender,
# where modules already loaded from a previous run need to be re-loaded in case the scripts
# changed since the last run. The 'import' statements above aren't sufficient for this,
# because python/blender caches the modules.
import importlib
importlib.reload(size_clustering)
importlib.reload(clustering_utils)
importlib.reload(nav_mesh)
importlib.reload(nav_node)
importlib.reload(nav_zone)
importlib.reload(nav_zone_entrance)
importlib.reload(nav_mesh_factory_utils)


class NavZoneInterface():
    # Helper class that represents the connection between two zones.
    # Note: This connection may be made up of multiple, separate actual entrances!
    # For a class representing a single entrance, check out NavZoneEntrance
    
    def __init__( self, zone_id_1, zone_id_2 ):
        assert zone_id_1 != zone_id_2
        
        self.interface_id = NavZoneInterface.unique_interface_id( zone_id_1, zone_id_2 )
        
        self.node_connections = {}
        self.nodes = set()
        
        self.entrances = []
        
        #self.mean_point = None
        #self.center_vert = None
        
    def add_connection( self, node_zone_1, node_zone_2 ):
        
        assert (node_zone_1.zone_id in self.interface_id and node_zone_2.zone_id in self.interface_id), "Cannot add nodes to interface, zone_id's must match those of the interface!"
        
        self.node_connections[node_zone_1.index] = node_zone_2.index
        self.node_connections[node_zone_2.index] = node_zone_1.index
        
        self.nodes.add( node_zone_1 )
        self.nodes.add( node_zone_2 )
    
    def calculate_entrances( self ):
        
        print(f"Searching for entrances between zones {self.interface_id}")
        if self.interface_id == "(156, 162)":
            print("==========================================\nDEBUG!")
        self.entrances = []
        
        nodes = self.nodes.copy()       # Will get modified, so make a copy!
        
        for n in nodes:
            print(n.index, n.zone_id)
            print( "\tsame level", [neigh.index for neigh in n.direct_neighbors])
            print( "\tnext level", [neigh.index for neigh in n.next_level_neighbors])

        while len(nodes) > 0:
            
            # Start with any vertex:
            node = nodes.pop()
            front = [node]
            entrance_nodes = []
            
            print("start node:", node.index)
            
            # Find other vertices belonging to the same entrance:
            while len( front ) > 0:
                
                node = front.pop()
                entrance_nodes.append( node )
                
                to_remove = set()         # New neighbors which are to be added to the front
                for neighbor in node.direct_neighbors:
                    print("direct neighbor:", neighbor.index)
                    if neighbor in nodes:
                        print("\tin")
                        front.append( neighbor )
                        to_remove.add( neighbor )
                for neighbor in node.next_level_neighbors:
                    print("next_level neighbor:", neighbor.index)
                    if neighbor in nodes:
                        print("\tin")
                        front.append( neighbor )
                        to_remove.add( neighbor )
                
                for n in to_remove:
                    nodes.remove( n )
                
            print(f"\tFound entrance, num verts: {len(entrance_nodes)}")
            print("\t", [n.index for n in entrance_nodes])
            self.entrances.append( nav_zone_entrance.NavZoneEntrance( self.interface_id[0], self.interface_id[1], entrance_nodes ) )
            if len( entrance_nodes ) == 1 and len(self.nodes) == 3:
                dsa = adre
        
    @staticmethod
    def unique_interface_id( zone_id_1, zone_id_2 ):
        if zone_id_1 < zone_id_2:
            return (zone_id_1, zone_id_2)
        else:
            return (zone_id_2, zone_id_1)
        
#    @staticmethod
#    def get( zone_id_1, zone_id_2 ):
#        interface_id = NavZoneInterface.unique_interface_id( zone_id_1, zone_id_2 )
#        if interface_id in NavZoneInterface.all_interfaces:
#            return NavZoneInterface.all_interfaces[interface_id]
#        else:
#            return NavZoneInterface( zone_id_1, zone_id_2 )
def create_nav_mesh( nodes, num_zones, zone_heights ):
    
    nav = nav_mesh.NavMesh( nodes, num_zones )
    
    # Create list of nodes for each "zone":
    zone_nodes = {}
    for zone_id in range(num_zones):
        zone_nodes[zone_id] = []
        
    # For each zone, fill its list of nodes with those nodes that have been 
    # assigned to the zone:
    for i,node in enumerate( nodes ):
        zone_nodes[node.zone_id].append( node )
        
    ##self.allverts = numpy.empty( (num_verts,4) )
    
    high_level_node_index = 0
    
    # Create the zones from the nodes:   
    for zone_id in range(num_zones):
        
        # Create zone for the vertices:
        zone = nav_zone.NavZone( zone_id=zone_id, nodes=zone_nodes[zone_id], height=zone_heights[zone_id] )
        nav.add_zone( zone )
        
        zone.create_center_node( index=high_level_node_index )
        high_level_node_index += 1
    
    # List of interfaces between zones. All touching "zones" make up exactly one interface
    interfaces = {}
    
    # Find all vertices which are at the border between zones:
    for node in nodes:
        for next_level_neighbor in node.next_level_neighbors:
            unique_interface_id = NavZoneInterface.unique_interface_id( node.zone_id, next_level_neighbor.zone_id )
            if not unique_interface_id in interfaces:
                interface = NavZoneInterface( node.zone_id, next_level_neighbor.zone_id )
                interfaces[unique_interface_id] = interface
            
            interface = interfaces[unique_interface_id]
                
            # Create a connection between the vertices:
            interface.add_connection( node, next_level_neighbor )
    
    for interface_id,interface in interfaces.items():
        interface.calculate_entrances()
        # Add a pointer to this entrance to all the zones it connects:
        for entrance in interface.entrances:
            zone_1 = nav.zones[entrance.zone_id_1]
            zone_2 = nav.zones[entrance.zone_id_2]
            
            zone_1.add_entrance( entrance )
            zone_2.add_entrance( entrance )
            # Create a node at the center of this entrance
            entrance.create_center_node( index=high_level_node_index )
            high_level_node_index += 1
            
            # Connect the zone nodes to the new entrance node:
            zone_1.node.add_direct_neighbor( entrance.node )
            zone_2.node.add_direct_neighbor( entrance.node )
            entrance.node.add_direct_neighbor( zone_1.node )
            entrance.node.add_direct_neighbor( zone_2.node )
            
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
    for i,zone in nav_mesh.zones.items():
        node_list.append( zone.node )
    for entrance in nav_mesh.entrances:
        node_list.append( entrance.node )
    node_list_sorted = sorted( node_list, key=lambda x: x.index )  # sort by index
    print( "number of zones:", len(nav_mesh.zones))
    print( "number of entrances:", len(nav_mesh.entrances))
    
    for node in node_list_sorted:
        bm.verts.new( node.pos )
    
    bm.verts.ensure_lookup_table()
    for i,zone in nav_mesh.zones.items():
        for i,entrances in zone.entrances.items():
            for e in entrances:
                bm.edges.new( (bm.verts[zone.node.index], bm.verts[e.node.index]) )

#        for zone_id, r in self.zones.items():
#            r.create_center_vert( bm )
#            for other_zone_id, entrances in r.entrances.items():
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
    
def verts_to_nodes( verts, assigned_zone_ids, heights ):
    
    verts.ensure_lookup_table()
    
    nodes = []
    for i, v in enumerate( verts ):
        node = nav_node.NavNode(np.array(v.co), v.index, assigned_zone_ids[v.index],
                normal=np.array(v.normal), max_height=heights[i] )
        nodes.append( node )
    
    for i, v in enumerate( verts ):
        node = nodes[i]
        for n in nav_mesh_factory_utils.get_neighbor_verts( v ):
            if assigned_zone_ids[v.index] == assigned_zone_ids[n.index]:
                node.add_direct_neighbor( nodes[n.index] )
            else:
                node.add_next_level_neighbor( nodes[n.index] )
                
    return nodes


    
def nav_mesh_from_object( obj ):
    obj = nav_mesh_factory_utils.duplicate_object( obj, "NavMesh_source" )
    add_skip_connections( obj )
    me = obj.data
    
    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    
    heights = nav_mesh_factory_utils.calculate_max_node_heights( bm )
    nav_mesh_factory_utils.visualize_max_node_heights( bm, heights )
    
    #heights = nav_mesh_factory_utils.smooth_max_node_heights( bm, heights )
    #nav_mesh_factory_utils.visualize_max_node_heights( bm, heights, "MaxNodeHeights_Smooth" )
    
    assigned_zone_ids, zone_heights = size_clustering.split_zones_by_height( bm, heights )
    num_zones = len(zone_heights)
    
    #assigned_zones, num_zones = cube_clustering.split_non_connected_zones( bm, assigned_zones )
    
    nodes = verts_to_nodes( bm.verts, assigned_zone_ids, heights )
    
    nav_mesh = create_nav_mesh( nodes, num_zones, zone_heights )
    create_high_level_mesh( nav_mesh )
    
    #debug_objs = clustering_utils.create_debug_meshes( bm, assigned_zone_ids, num_zones )
    bm.free()    
    
    #test_nav_mesh( nav_mesh )
    
    import pickle
    
    filename = os.path.join( os.path.dirname(bpy.data.filepath), "nav_mesh.pickle" )
    with open( filename, "wb" ) as f:
        pickle.dump( nav_mesh, f )
        print("Saved nav_mesh as:", filename)
        
    print("pickle version", pickle.format_version)
    with open( filename, "rb" ) as f:
        nav_mesh_2 = pickle.load( f )
        print(nav_mesh_2)

    return nav_mesh

if __name__ == "__main__":
    
    obj = bpy.context.object
    nav_mesh = nav_mesh_from_object( obj )
    
    num_runs = 1

    for i in range(num_runs):
        # Test A* path finding:
        start_node = nav_mesh.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
        end_node = nav_mesh.nodes[ random.randint(0,len(nav_mesh.nodes)-1) ]
    
        high_level_path, low_level_path = nav_mesh.find_full_path( start_node, end_node )
    
        path_to_mesh( high_level_path )
        path_to_mesh( low_level_path )
        
