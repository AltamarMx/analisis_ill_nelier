# %load ../../../Daylight-master/modulos/illumination.py
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
get_ipython().magic('matplotlib inline')
from ipywidgets import widgets,interact_manual,interact
import math
import matplotlib.gridspec as gridspec
# plt.rc('text',usetex=True)
# plt.rc('font', family ="serif")

class daylight:
    """
    Class to read ILL files from a Radiance Simulation, calculate and render UDIs, illuminance maps and others.

    Use:
    a = ill.daylight(arg1)

    Parameters
    ----------
    arg1 : path of the ILL file to load into a DataFrame.
    arg1 = 'data/CEEA.ill'
    Returns
    nx: number of elements in the x direction of the grid
    ny: number of elements in the y direction of the grid
    Lx: Lenght in the x direction of the grid
    Ly: Lenght in the y direction of the grid
    dx: Size of the grid in the x direction
    dy: Size of the grid in the y direction
    -------
    The class contains the following methods:
    
    udi()
        Calculate the UDI [https://patternguide.advancedbuildings.net/using-this-guide/analysis-methods/useful-daylight-illuminance]
        defining the following parameters:
        E_LL:  Lower limit illumination level [lx]
        E_UL:  Upper limit illumination level [lx]
        t_min: Start hour of day to evaluate the UDI [h]
        t_http://localhost:8891/edit/modulos/illumination.py#max: End hout of day to evaluate the UDI [h]
        dC:    Number of color leves for the UDI [-]
        Once executed, prints the frequency of visual comfort (FVC).
        
    map()
        Plot the illuminance map for the space for a specific day, time and renders using a maximum value of the illuminance:
        day:  day to plot the illuminance map [-]
        hour: Time of day (0,24) to plot the illuminance map [h]
        Lmax: Maximum value to render illuminance map [lx]
    
    x()
        Plot the illuminance along the x direction at a specific value of y:
        day:  day to plot the illuminance along the x direction [-]
        hour: Time of day (0,24) to plot the illuminance along the x direction [h]
        jj:   Number of element (0,Ly) to plot the illuminance along the x direcion [-]
        
    
    y()
        Plot the illuminance along the y direction at a specific value of x:
        day:  day to plot the illuminance along the x direction [-]
        hour: Time of day (0,24) to plot the illuminance along the y direction [h]
        ii:   Number of element (0,Lx) to plot the illuminance along the y direcion [-]

    """

    def __init__(self,archivo, sensores = 0):
        # pd.set_option('precision',25)
        if sensores == 0:
            print('Datos obtenidos con OpenStudio')
            parameters = pd.read_csv(archivo,sep=' ',nrows=1,skiprows=(0,1,2),header=None)
            self.xmin   = parameters[0]
            self.ymin   = parameters[1]
            self.xmax   = parameters[3]
            self.ymax   = parameters[7]
            self.deltax = parameters[9]
            self.deltay = parameters[10]
            self.nx     = int(((self.xmax - self.xmin) / self.deltax ).round())
            self.ny     = int(((self.ymax - self.ymin) / self.deltay).round())
            ill = pd.read_csv(archivo,sep=',',skiprows=(0,1,2,3),header=None)
            dias, _ = ill.shape
            self.dias = int(dias/24)
            self.renglones, self.cols = ill.shape
            self.columnas = np.arange(6,self.cols)
            ill_tmp  = ill[self.columnas]
            self.ill_data = ill_tmp
        
            print("days: {}".format(self.dias))  
            print("nx: {}".format(self.nx))
            print("ny: {}".format(self.ny))
            print("Lx: {:.2f} [m]".format(self.xmax[0]-self.xmin[0]))
            print("Ly: {:.2f} [m]".format(self.ymax[0]-self.ymin[0]))
            print("dx: {:.2f} [m]".format(self.deltax[0]))
            print("dy: {:.2f} [m]".format(self.deltay[0]))
            
        else:  
            self.xmin = sensores[0]
            self.ymin = sensores[1]
            self.xmax = sensores[2]
            self.ymax = sensores[3]
            self.nx   = sensores[4]
            self.ny   = sensores[5]
            self.deltay = (self.xmax-self.xmin)/self.nx
            self.deltax = (self.ymax-self.ymin)/self.ny
            ill = pd.read_csv(archivo, sep=' ', skiprows=range(0,10), skipinitialspace=True, header=None).transpose()
            dias, _ = ill.shape
            self.dias = int(dias/24)
            self.renglones, self.cols = ill.shape
            self.columnas = self.cols
            self.ill_data = ill
            print("Datos obtenidos con Radiance")
            print("days: {}".format(self.dias))  
            print("nx: {}".format(self.nx))
            print("ny: {}".format(self.ny))


    def UDI(self,E_LL,E_UL,t_min,t_max,dC,filename='UDI.pdf'):
        dC =  dC + 1
        result = pd.DataFrame()
        for d in range(0,self.dias):
            min = (d+1)*24-(24-t_min)
            max = (d+1)*24-(24-t_max)
            result = result.append(self.ill_data.iloc[min-1:max-1])
        renglones, cols = result.shape
        UDI_sub = np.zeros(self.columnas)
        UDI_u   = np.zeros(self.columnas)
        UDI_sob = np.zeros(self.columnas)

        for i in range(renglones):
            f = result.iloc[i] < E_LL
            UDI_sub[f] = (UDI_sub[f] + 1)
            f = (result.iloc[i] >= E_LL) & (result.iloc[i] <= E_UL)
            UDI_u[f] =( UDI_u[f] + 1)
            f = result.iloc[i] > E_UL
            UDI_sob[f] = (UDI_sob[f] + 1)

        UDI_sub = (UDI_sub /((t_max-t_min)*self.dias)*100).reshape(self.ny,self.nx)
        UDI_u   = (UDI_u   /((t_max-t_min)*self.dias)*100).reshape(self.ny,self.nx)
        UDI_sob = (UDI_sob /((t_max-t_min)*self.dias)*100).reshape(self.ny,self.nx)
        UDI_tot = np.concatenate((UDI_sub,UDI_u,UDI_sob))
    #GRAFICADO DE LOS UDISself.
        plt.figure(figsize=(5.5,8))
        #plt.rc('text',usetex=True)
        #plt.rc('font', family ="serif")
        gs = gridspec.GridSpec(3,2,width_ratios=[5.5,0.25])
        levels = np.linspace(0,100,dC)
        
        x = np.linspace(self.xmin,self.xmax,self.nx)
        y = np.linspace(self.ymin,self.ymax,self.ny)
        plt.set_cmap('gnuplot')
        
        ax4 = plt.subplot(gs[:,1])
        ax1 = plt.subplot(gs[0,0])
        ax2 = plt.subplot(gs[1,0])
        ax3 = plt.subplot(gs[2,0])
        
        ax1.title.set_text(r'$UDI_{und}$')
        z_contourR = ax1.contourf(x,y,UDI_sub,levels=levels)
        ax1.set_xticks([])
        
        ax2.title.set_text(r'$UDI_u$')
        z_contourI = ax2.contourf(x,y,UDI_u,levels=levels)
        ax2.set_xticks([])
        ax2.set_ylabel(r'$y$ $[m]$')
        ax3.title.set_text(r'$UDI_{over}$')
        z_contourJ = ax3.contourf(x,y,UDI_sob,levels=levels)
        
        ax4.title.set_text(r'\%')        
        cbarR = plt.colorbar(z_contourR,ticks=np.linspace(0,100,11), cax=ax4)
        plt.tight_layout()
        plt.xlabel(r'$x$ $[m]$')
        
        plt.savefig(filename)
        plt.show() 
        print("FVC = {:.2f}%".format(np.average(UDI_u)) )
        #return UDI_tot
        
    def MAP(self,day,hour,Lmax,div=22):
        
        position = (day-1)*24+(hour-1)
        mapa = self.ill_data.iloc[position].values.reshape(self.ny,self.nx)
        fig = plt.figure(figsize=(10,8))
        levels = np.linspace(0,Lmax,div)
        x = np.linspace(self.xmin,self.xmax,self.nx)
        y = np.linspace(self.ymin,self.ymax,self.ny)
        ax1 = fig.add_subplot(111,aspect=self.nx/self.ny)    
        plt.xlabel('$x$ $[m]$')
        plt.ylabel('$y$ $[m]$')
        plt.title('Illuminance $[lx]$')
        plt.set_cmap('gnuplot')
        
        z_contourR = ax1.contourf(x,y,mapa,levels=levels)
        cbarR = plt.colorbar(z_contourR,ticks=np.linspace(0,Lmax,6))
        plt.show()
    
    
    def MAPDF(self,day,hour,Lmax,Lext):
        
        position = (day-1)*24+(hour-1)
        #        position = (day)*24-(24-hour)
        #         position = (dia-1)*24-(24-hora-1)
        mapa = (self.ill_data.iloc[position].values.reshape(self.ny,self.nx))/Lext*100
        fig = plt.figure(figsize=(10,8))
        levels = np.linspace(0,Lmax,50)
        x = np.linspace(self.xmin,self.xmax,self.nx)
        y = np.linspace(self.ymin,self.ymax,self.ny)
        ax1 = fig.add_subplot(111,aspect=self.nx/self.ny)
        plt.xlabel('$x$ $[m]$')
        plt.ylabel('$y$ $[m]$')
        plt.title('Illuminance $[lx]$')
        #plt.set_cmap('gist_heat')
        plt.set_cmap('gnuplot')
        #plt.axes().set_aspect(1.0)
        
        z_contourR = ax1.contourf(x,y,mapa,levels=levels)
        cbarR = plt.colorbar(z_contourR,ticks=np.linspace(0,Lmax,6))
        plt.show()
    
    def Y(self,day,hour,ii):
        position = (day)*24-(24-hour)
        mapa = self.ill_data.iloc[position].values.reshape(self.ny,self.nx)
        y = np.linspace(self.ymin,self.ymax,self.ny)
        x = np.linspace(self.xmin,self.xmax,self.nx)
        fig = plt.figure(figsize=(10,3))
        ax1 = fig.add_subplot(111)    
        plt.xlabel('$y$ $[m]$')
        plt.ylabel('Illuminance $[lx]$')
        plt.ticklabel_format(axis='y', style='plain')
        y_plot = ax1.plot(y   ,mapa[:,ii])
        y_plot = ax1.scatter(y,mapa[:,ii])
        return mapa[:,ii]
        plt.show()
        print("x ={:.2f} [m]".format(x[ii]))
        print('#y\tIl')
        print('#[m]\t[lx]')
        for i in range(len(y)):
            print("{:.2f}\t{:.2f}".format(y[i],mapa[i,ii])) 
#         print(mapa[:,ii])
#         print(y)
        
    def X(self,day,hour,jj):
        position = (day)*24-(24-hour)
        mapa = self.ill_data.iloc[position].values.reshape(self.ny,self.nx)
        ymax = self.ymax - self.ymin + jj*self.deltay + self.deltay/2.
        y = np.linspace(self.ymin,self.ymax,self.ny)
        x = np.linspace(self.xmin,self.xmax,self.nx)
        fig = plt.figure(figsize=(10,3))
        ax1 = fig.add_subplot(111)    
        plt.xlabel('$x$ $[m]$')
        plt.ylabel('Illuminance $[lx]$')
        x_plot = ax1.plot(x,mapa[jj,:])
        x_plot = ax1.scatter(x,mapa[jj,:])
        plt.ticklabel_format(axis='y', style='plain')
        plt.show()
        print("y ={:.2f} [m]".format(y[jj]))
        print('#x\tIl')
        print('#[m]\t[lx]')
        for i in range(len(x)):
            print("{:.2f}\t{:.2f}".format(x[i],mapa[jj,i])) 
        print(x)