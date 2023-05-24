import numpy as np
import random
import math
import bpy, bmesh
import os, sys
import time
from mathutils import Vector
import pickle

dir = os.path.dirname(bpy.data.filepath)
if not dir in sys.path:
    sys.path.append(dir)

import utils

# this next part forces a reload in case you edit the source after you first start the blender session
import imp
imp.reload(utils)

def split_zones_by_height( bm, heights, split_at = 0.5, max_radius = 10 ):
    
    open = set( bm.verts )
    
    visited = set()
    
    front = set()
    
    def level_for_height( h ):
        h = min( h, 10 )
        return int(h/split_at)
    
    def height_for_level( l ):
        return l*split_at
    
    #zone_ids = {}
    assigned_zone_ids = [-1 for v in bm.verts]
    zone_heights = []
    
    cur_zone_id = 0
    
    max_radius2 = max_radius**2
    
    while len(open) > 0:
        
        cur_start_vert = next(iter(open))  # Get first element without removing it
         
        front.add( cur_start_vert )
        cur_level = level_for_height( heights[cur_start_vert.index] )
        
        while len(front) > 0:
            
            v = front.pop()
            
            visited.add( v )
            open.remove( v )
            
            assigned_zone_ids[v.index] = cur_zone_id
            
            for n in utils.get_neighbor_verts( v ):
                if not n in visited and not n in front:
                    if level_for_height( heights[n.index] ) == cur_level:
                        dist2 = (n.co - cur_start_vert.co).length_squared
                        if dist2 < max_radius2:
                            front.add(n)
        
        # Remember the height for this zone:
        zone_heights.append( height_for_level( cur_level ) )
        
        # Carry on with a new zone:
        cur_zone_id += 1
        #if cur_zone_id > 5:
        #s    break
    
    # Debug:
    for v in open:
        assigned_zone_ids[v.index] = cur_zone_id
    
    print("assigned_zone_ids", len(assigned_zone_ids))
        
    return assigned_zone_ids, zone_heights