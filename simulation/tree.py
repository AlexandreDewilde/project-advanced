import numpy as np
import numba
from numba import deferred_type, optional, float64, int64,typeof
from numba.experimental import jitclass
from numba.typed import List

node_type = deferred_type()
spec = (
    ("npoints", int64),
    ("points", float64[:,:] ),
    ("center", float64[:]),
    ("length", float64),
    ("nw", optional(node_type)),
    ("ne", optional(node_type)),
    ("sw", optional(node_type)),
    ("se", optional(node_type)),
    ("max",int64),
    ("IDs",int64[:]),
    ("leaf",int64),
)

@jitclass(spec)
class QuadTreeNode(object):

    def __init__(self, center, length):
        self.max = 4   #max number of points in the node 
        self.points = np.zeros((self.max,3))   #on note pas les sous arrays sinon numba plante
        self.IDs = np.zeros(self.max).astype(int64)
        self.npoints = 0
        self.center = center       #center of the node
        self.length = length       #length of the node 
        self.leaf= 1

        self.nw = None             #top left node
        self.ne = None             #top right node
        self.sw = None             #bottom left node
        self.se = None             #bottom right node

node_type.define(QuadTreeNode.class_type.instance_type)

@numba.jit()
def add_point(node, point,i):
    stack = List()
    stack.append((node,point,i))
    xmin = node.center[0]-node.length/2
    xmax = node.center[0]+node.length/2
    ymin = node.center[1]-node.length/2
    ymax = node.center[1]+node.length/2
    while len(stack):
        node = stack[0][0]
        point = stack[0][1]
        i = stack[0][2]
        stack.pop(0)
        if point[0] <= xmin or point[0]>xmax or point[1] <= ymin or point[1]>ymax:                #Check if point is outside node
            continue 
        
        if node.leaf == 0 :
            stack.append((node.nw,point,i))
            stack.append((node.sw,point,i))
            stack.append((node.se,point,i))
            stack.append((node.ne,point,i))
        
        elif node.npoints < node.max:
            node.points[node.npoints] = point
            node.IDs[node.npoints] = i
            node.npoints += 1
        else :
            set_nodes(node)
            points_toremove,IDs = get_points(node)
            node.leaf = 0
            for j in range(len(points_toremove)) :
                p = points_toremove[j]
                ID = IDs[j]
                stack.append((node,p,ID))
            stack.append((node,point,i))
    return

@numba.jit() #ok
def set_nodes(node): 
    l = node.length / 2
    d = node.length / 4

    node.nw = QuadTreeNode(node.center + np.array((-d, d)), l)
    node.ne = QuadTreeNode(node.center + np.array((d, d)), l)
    node.sw = QuadTreeNode(node.center + np.array((-d, -d)), l)
    node.se = QuadTreeNode(node.center + np.array((d, -d)), l)

    return l

@numba.jit() #ok
def get_points(node):
    points = node.points[:node.npoints]
    IDs = node.IDs[:node.npoints]
    return points,IDs

@numba.jit() #ok
def point_in_square(point,center,length):
    #Check if a point is in a square
    x = point[0]
    y = point[1]
    max_x = center[0]+length/2
    min_x = center[0]-length/2
    max_y = center[1]+length/2
    min_y = center[1]-length/2
    if min_x <= x <= max_x and min_y <= y <= max_y:
        return True
    else :
        return False

@numba.jit() #ok
def intersects(centerA,lengthA,centerB,lengthB):
    #Return true if rectangle A intersects rectangle B
    xminA = centerA[0] - lengthA/2
    xmaxA = centerA[0] + lengthA/2
    yminA = centerA[1] - lengthA/2
    ymaxA = centerA[1] + lengthA/2
    
    xminB = centerB[0] - lengthB/2
    xmaxB = centerB[0] + lengthB/2
    yminB = centerB[1] - lengthB/2
    ymaxB = centerB[1] + lengthB/2

    return not (xmaxA<xminB or xmaxB<xminA or ymaxA < yminB or ymaxB<yminA)

#@numba.jit()
def nodes_in_square(node,point,L,list):
    #return all the leaf nodes that touches the square of side L centered on point
    if intersects(node.center,node.length,point,L):
        if node.leaf == 1:
            list.append(node)
        else :
            list += nodes_in_square(node.nw,point,L,[])
            list += nodes_in_square(node.sw,point,L,[])
            list += nodes_in_square(node.ne,point,L,[])
            list += nodes_in_square(node.se,point,L,[])
    if len(list) == 0:
        return List()
    return list

#@numba.jit()
def particles_in_box(node,point,L):
    #return all particles coordinates in the box of size L around point 
    nodes = List()
    nodes.append(QuadTreeNode(np.array([0.0,0.0,0.0]),0.0))
    nodes = nodes_in_square(node,point,L,nodes)
    nparticles = 0
    particles = np.zeros((node.max*len(nodes),3))
    IDs = np.zeros(node.max*len(nodes))
    for i in range(1,len(nodes)):
        points,ids = get_points(nodes[i])
        particles[nparticles:nparticles+nodes[i].npoints,] = points
        IDs[nparticles:nparticles+nodes[i].npoints] = ids
        nparticles += nodes[i].npoints
    return particles[:nparticles],IDs[:nparticles]

#@numba.jit()
def set_tree(points):
    xmin = np.min(points[:,0]) - 1
    xmax = np.max(points[:,0]) + 1
    ymin = np.min(points[:,1]) - 1
    ymax = np.max(points[:,1]) + 1 
    center = np.array([xmax+xmin,ymax+ymin])/2
    length = np.max(np.array([xmax-xmin,ymax-ymin]))
    tree = QuadTreeNode(center,length)
    for i in range(len(points)):
        add_point(tree,points[i],i)
    return tree
