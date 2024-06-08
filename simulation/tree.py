import numpy as np

class QuadTreeNode(object):

    def __init__(self, center, length):
        self.max = 4   #max number of points in the node 
        self.points = np.zeros(self.max*3)   #on note pas les sous arrays sinon numba plante
        self.IDs = np.zeros(self.max).astype(int)
        self.npoints = 0
        self.center = center       #center of the node
        self.length = length       #length of the node 
        self.leaf= 1

        self.nw = None             #top left node
        self.ne = None             #top right node
        self.sw = None             #bottom left node
        self.se = None             #bottom right node

def add_point(node, point,i):
   
    xmin = node.center[0]-node.length/2
    xmax = node.center[0]+node.length/2
    ymin = node.center[1]-node.length/2
    ymax = node.center[1]+node.length/2

    if point[0] <= xmin or point[0]>xmax or point[1] <= ymin or point[1]>ymax:                #Check if point is outside node
        return False
    
    if node.leaf == 0 :
        return (add_point(node.nw,point,i) or add_point(node.sw,point,i) or add_point(node.ne,point,i) or add_point(node.se,point,i))

    if node.npoints < node.max:
        node.points[3*node.npoints:3*node.npoints+3] = point
        node.IDs[node.npoints] = i
        node.npoints += 1
        return True
    
    else :
        set_nodes(node)
        points_toremove,IDs = get_points(node)
        node.npoints = 0
        node.leaf = 0
        for i in range(len(points_toremove)) :
            p = points_toremove[i]
            ID = IDs[i]
            add_point(node,p,ID)
        add_point(node,point,i)
        
    return

def set_nodes(node):
    l = node.length / 2
    d = node.length / 4

    node.nw = QuadTreeNode(node.center + np.array((-d, d)), l)
    node.ne = QuadTreeNode(node.center + np.array((d, d)), l)
    node.sw = QuadTreeNode(node.center + np.array((-d, -d)), l)
    node.se = QuadTreeNode(node.center + np.array((d, -d)), l)

    return l

def get_points(node):
    if node.leaf == 0 : #not a leaf
        return -1 
    points = np.zeros((node.max,3))
    IDs = node.IDs[:node.npoints]
    points[0] = node.points[:3]
    points[1] = node.points[3:6]
    points[2] = node.points[6:9]
    points[3] = node.points[9:12]
    points = points[:node.npoints]
    return points,IDs

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

    return list

def particles_in_box(node,point,L):
    #return all particles coordinates in the box of size L around point 
    nodes = []
    nodes = nodes_in_square(node,point,L,nodes)
    #print(nodes,len(nodes))
    nparticles = 0
    particles = np.zeros((node.max*len(nodes),3))
    IDs = np.zeros(node.max*len(nodes))
    for i in range(len(nodes)):
        #print(particles)
        points,ids = get_points(nodes[i])
        particles[nparticles:nparticles+nodes[i].npoints,] = points
        IDs[nparticles:nparticles+nodes[i].npoints] = ids
        nparticles += nodes[i].npoints
    #print(particles)
    return particles[:nparticles],IDs[:nparticles]

def set_tree(points):
    xmin = np.min(points[:,0]) 
    xmax = np.max(points[:,0]) 
    ymin = np.min(points[:,1]) 
    ymax = np.max(points[:,1]) 
    center = np.array([xmax+xmin,ymax+ymin])/2
    length = np.max(np.array([xmax-xmin,ymax-ymin]))
    tree = QuadTreeNode(center,length)
    for i in range(len(points)):
        add_point(tree,points[i],i)
    return tree