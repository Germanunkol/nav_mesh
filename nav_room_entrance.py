
class NavRoomEntrance():
    # Represents a single entrance from one room to another.
    # Note that there may be multiple (disconnected) entrances between the same
    # two rooms. This class only represents one entrance, i.e. all the verts
    # in this entrance should be connected!
    
    all_entrances = {}
    
    def __init__( self, room_id_1, room_id_2, nodes ):
        self.room_id_1 = room_id_1
        self.room_id_2 = room_id_2
        
        self.nodes = nodes
        
        self.max_height = max( [n.max_height for n in nodes] )
        
        print("Building entrance:", [n.room_id for n in nodes] )
        
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
            raise ValueError("All verts in a NavRoomEntrance should be connected, but they aren't!")
        
        self.mean_point = None
        self.center_vert = None
        self.node = None
    
    def get_other_room_id( self, room_id ):
        if room_id == self.room_id_1:
            return self.room_id_2
        elif room_id == self.room_id_2:
            return self.room_id_1
        else:
            raise ValueError( f"Asking for 'other' room id of entrance but given room id {room_id} is not in the entrance's room ids ({self.room_id_1} and {self.room_id_2})!" )
        
    @property
    def center( self ):
        if not self.mean_point:
            self.mean_point = mean_node_position( self.nodes )
        return self.mean_point
        
    
    def create_center_vert( self, bm ):
        if not self.center_vert:
            self.center_vert = bm.verts.new( self.center )
            
    def create_center_node( self, index ):
        if not self.node:
            self.node = NavNode( self.center, index, level=1, max_height=self.max_height )
            self.node.entrance = self
            
    def __str__( self ):
        nodes_room_1 = 0
        nodes_room_2 = 0
        for n in self.nodes:
            if n.room_id == self.room_id_1:
                nodes_room_1 += 1
            if n.room_id == self.room_id_2:
                nodes_room_2 += 1
            
        return f"Entrance: {self.room_id_1} ({nodes_room_1} nodes) -> {self.room_id_2} ({nodes_room_2} nodes), total nodes: {len(self.nodes)}"
