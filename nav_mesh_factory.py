import bpy, bmesh
import os, sys, random
import numpy as np
import math

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append( dir )
    
import cube_clustering
import navmesh
import utils
import navmesh_utils

# this next part forces a reload in case you edit the source after you first start the blender session:
import importlib
importlib.reload(cube_clustering)
importlib.reload(navmesh)
importlib.reload(utils)
importlib.reload(navmesh_utils)


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
        
        print(f"Searching for entrances between rooms {self.interface_id}")
        if self.interface_id == "(156, 162)":
            print("==========================================\nDEBUG!")
        self.entrances = []
        
        nodes = self.nodes.copy()       # Will get modified, so make a copy!
        
        for n in nodes:
            print(n.index, n.room_id)
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
            self.entrances.append( navmesh.NavRoomEntrance( self.interface_id[0], self.interface_id[1], entrance_nodes ) )
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
    
def verts_to_nodes( verts, assigned_rooms, heights ):
    
    verts.ensure_lookup_table()
    
    nodes = []
    for i, v in enumerate( verts ):
        node = navmesh.NavNode(np.array(v.co), v.index, assigned_rooms[v.index],
                normal=np.array(v.normal), max_height=heights[i] )
        nodes.append( node )
    
    for i, v in enumerate( verts ):
        node = nodes[i]
        for n in utils.get_neighbor_verts( v ):
            if assigned_rooms[v.index] == assigned_rooms[n.index]:
                node.add_direct_neighbor( nodes[n.index] )
            else:
                node.add_next_level_neighbor( nodes[n.index] )
                
    return nodes

def create_navmesh( nodes, num_rooms ):
    
    nav_mesh = navmesh.NavMesh( nodes, num_rooms )
    
    # Create list of nodes for each "room":
    room_nodes = {}
    for room_id in range(num_rooms):
        room_nodes[room_id] = []
        
    # For each room, fill its list of nodes with those nodes that have been 
    # assigned to the room:
    for i,node in enumerate( nodes ):
        room_nodes[node.room_id].append( node )
        
    ##self.allverts = numpy.empty( (num_verts,4) )
    
    high_level_node_index = 0
    
    # Create the rooms from the nodes:   
    for room_id in range(num_rooms):
        
        # Create room for the vertices:
        room = navmesh.NavRoom( room_id=room_id, nodes=room_nodes[room_id] )
        nav_mesh.add_room( room )
        
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
            room_1 = nav_mesh.rooms[entrance.room_id_1]
            room_2 = nav_mesh.rooms[entrance.room_id_2]
            
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
            
            nav_mesh.add_entrance( entrance )
            
    return nav_mesh

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


def test_navmesh( nav_mesh ):
    import time
    
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
        for n in utils.get_neighbor_verts( v ):    
            if n.normal.length < 1e-10:
                continue
            ang = v.normal.angle( n.normal )
            if ang < math.pi*0.1:            
                for n2 in utils.get_neighbor_verts( n ):
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
    
def navmesh_from_object( obj ):
    obj = utils.duplicate_object( obj, "NavMesh_source" )
    add_skip_connections( obj )
    me = obj.data
    
    # Get a BMesh representation
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(me)   # fill it in from a Mesh
    
    cube_side_length = 10
    assigned_rooms = cube_clustering.estimate_rooms( bm, cube_side_length )
    
    assigned_rooms, num_rooms = cube_clustering.split_non_connected_rooms( bm, assigned_rooms )
    
    heights = navmesh_utils.calculate_max_node_heights( bm )
    #navmesh_utils.visualize_max_node_heights( bm, heights )
    
    heights = navmesh_utils.smooth_max_node_heights( bm, heights )
    navmesh_utils.visualize_max_node_heights( bm, heights, "MaxNodeHeights_Smooth" )
    
    nodes = verts_to_nodes( bm.verts, assigned_rooms, heights )
    
    
    nav_mesh = create_navmesh( nodes, num_rooms )
    create_high_level_mesh( nav_mesh )
    
    #cube_clustering.create_debug_meshes( bm, assigned_rooms, num_rooms )
    bm.free()
    
    
    #test_navmesh( nav_mesh )
    
    import pickle
    
    filename = os.path.join( os.path.dirname(bpy.data.filepath), "navmesh.pickle" )
    with open( filename, "wb" ) as f:
        pickle.dump( nav_mesh, f )
        print("Saved navmesh as:", filename)
        
    print("pickle version", pickle.format_version)
    with open( filename, "rb" ) as f:
        nav_mesh_2 = pickle.load( f )
        print(nav_mesh_2)

if __name__ == "__main__":
    
    obj = bpy.context.object
    navmesh_from_object( obj )
    
        