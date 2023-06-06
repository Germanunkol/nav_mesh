from panda3d.core import LineSegs, LVector3f

def to_panda_vector( vec ):
    return LVector3f( vec[0], vec[1], vec[2] )

def display_debug_info( debug_info, all_nodes ):

    l = LineSegs()
    l.set_thickness(2)

    node = debug_info["end_nodes"][0]
    zone_id = node.zone_id
    l.set_color( (1, 1, 1, 1) )
    l.set_thickness( 4 )
    for n in all_nodes:
        if n.zone_id == zone_id:
            l.move_to( to_panda_vector(n.pos) + LVector3f.up()*0.1 )
            l.draw_to( to_panda_vector(n.pos) )

    l.set_color( (0.5, 0.5, 0.5, 1) )
    closed_nodes = [all_nodes[i] for i in debug_info["closed"]]
    for n in closed_nodes:
        l.set_thickness( 4 )
        l.move_to( to_panda_vector(n.pos) + LVector3f.up()*0.1 )
        l.draw_to( to_panda_vector(n.pos) )
        l.set_thickness( 2 )
        if n.parent_node_id >= 0:
            parent_node = all_nodes[n.parent_node_id]
            l.draw_to( to_panda_vector(parent_node.pos) )

    l.set_color( (0.5, 0.5, 1, 1) )
    for n in debug_info["open_list"]:
        l.set_thickness( 4 )
        l.move_to( to_panda_vector(n.pos) + LVector3f.up()*0.1 )
        l.draw_to( to_panda_vector(n.pos) )
        l.set_thickness( 2 )
        if n.parent_node_id >= 0:
            parent_node = all_nodes[n.parent_node_id]
            l.draw_to( to_panda_vector(parent_node.pos) )


    l.set_color( (1, 0.25, 0.25, 1) )
    for n in debug_info["end_nodes"]:
        print("END NODE")
        l.set_thickness( 7 )
        l.move_to( to_panda_vector(n.pos) + LVector3f.up()*0.2 )
        l.draw_to( to_panda_vector(n.pos) )
        l.set_thickness( 2 )
        if n.parent_node_id >= 0:
            parent_node = all_nodes[n.parent_node_id]
            l.draw_to( to_panda_vector(parent_node.pos) )

    geom = l.create()
    node = render.attach_new_node( geom )
    return node
