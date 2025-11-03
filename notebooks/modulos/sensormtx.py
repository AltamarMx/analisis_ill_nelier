import numpy as np
import pandas as pd

def sensormtx (x1,x2,y1,y2,nx,ny,z, filename="../modelo/matrices/workplane.pts"):
    gridx = np.linspace(x1,x2,nx)
    gridy = np.linspace(y1,y2,ny)
    parametros =[x1,y1,x2,y2,nx,ny]
    z = z
    f = open (filename,"wt")
    for j in gridy:
        for i in gridx:
            f.write("{} {} {} 0 0 1\n".format(i,j,z))
    f.close()
    return parametros
