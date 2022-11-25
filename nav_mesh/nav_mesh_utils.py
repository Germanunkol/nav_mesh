############################################################
# Copyright (C) 2022 Germanunkol
# License: MIT
############################################################

def mean_node_position( nodes ):
    
    mean_point = np.array((0.0,0.0,0.0))
    for n in nodes:
        mean_point += n.pos
    mean_point /= len(nodes)
    
    return mean_point
