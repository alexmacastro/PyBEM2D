#########################################################################
#       (C) 2017 Department of Petroleum Engineering,                   # 
#       Univeristy of Louisiana at Lafayette, Lafayette, US.            #
#                                                                       #
# This code is released under the terms of the BSD license, and thus    #
# free for commercial and research use. Feel free to use the code into  #
# your own project with a PROPER REFERENCE.                             #
#                                                                       #
# PYBEM2D Code                                                          #
# Author: Bin Wang                                                      # 
# Email: binwang.0213@gmail.com                                         # 
# Reference: Wang, B., Feng, Y., Berrone, S., et al. (2017) Iterative   #
# Coupling of Boundary Element Method with Domain Decomposition.        #
# doi:                                                                  #
#########################################################################

import numpy as np

#[BEM Element type]
from Lib.Tools.Geometry import *


###############################
#
#  General BEM 2D Element Class
#
###############################

class BEM_element(object):
    """Class object for a single boundary element"""
    def __init__(self, Pts_a=(0,0),Pts_c=(0,0),Pts_b=(0,0),Type="quad",bd_marker=0):
        """Creates a boundary element from A->B.
           The position fo A,B decide the element direction
        
        Boundary Element Type:

        Type        Independent-Node    Sharded-Node    Continuous?      a         c        b    
        Constant        Pts_c(1)              -              No          |--------|*|--------|
        Linear          Pts_a(1)           Pts_b(1)          Yes         |*|---------------|*|
        Quadrature      Pts_a,Pts_c(2)     Pts_b(1)          Yes         |*|------|*|------|*|

        [Discontinuous Element]
        Linear          Pts_a',Pts_b'(2)      -              No          |---|*|-------|*|---|
        Quadrature      Pts_a',Pts_c',Pts_b'(3)  -           No          |---|*|--|*|--|*|---|

        Arguments
        ---------
        xa, ya    -- Cartesian coordinates of the first end-point A.
        xb, yb    -- Cartesian coordinates of the second end-point B.
        xc, yc    -- Cartesian coordinates of the center point.
        length    -- length of this BE.
        nx,ny     -- unit normal vector (available for linear line element, curve element requires jacobian)
        tx,ty     -- unit tagential vector
        
        bd_Indicator   -- 1 for Neumann B.C and Robin ....0 for Dirchelet B.C
        bd_value  -- boundary value(up to 3)
        Type      -- boundary element method type
                     [Const] [Linear] [Quad]
        bd_marker -- Classify boundary as index for BC
        
        P         -- Pressure on boundary element node
        Q         -- flux(pressure derivate in normal direction), u=dp/dx v=dp/dy  Q=nx*dp/dx+ny*dp/dy
        
        Author:Bin Wang (binwang.0213@gmail.com)
        Date: July. 2017
        """
        
        #[Geometry]
        self.xa, self.ya = Pts_a[0], Pts_a[1]  #First node for a quadratic BE
        self.xb, self.yb = Pts_b[0], Pts_b[1]  #Third node for a quadratic BE
        self.xc,self.yc=0,0
        if (Type=="Const" or Type=="Linear"): 
            self.xc, self.yc=(self.xa+self.xb)/2, (self.ya+self.yb)/2
        if (Type=="Quad"):  
            self.xc, self.yc = Pts_c[0], Pts_c[1]  #Second node for a quadratic BE 
        self.length = calcDist(Pts_a,Pts_b)     # length of the element   
        
        self.nx=(self.yb-self.ya)/self.length   # Normal unit Vector of the element nx*i+ny*j
        self.ny=-(self.xb-self.xa)/self.length  # 
        self.tx=-self.ny #Tagential unit vector tx*i+ty*j
        self.ty=self.nx

        self.d1=0.8 #Node offset from Pts_c to Pts_a
        self.d2=0.8 #Node offset from Pts_c to Pts_b
        
        #[Properties]
        self.element_type=Type
        self.bd_marker=bd_marker
        self.Discontinuous=False #Discontinuous element for linear and quad element
        
        #[Boundary Conditions & Values]
        self.bd_Indicator=1                            # Neumann-1   Dirichlet-0
        self.Robin_alpha=0                             # Robin is a special of Neumann, bd_indicator still use 1

        if (self.element_type=="Const"):
            self.bd_value1=0                           # boundary condition value1
            self.P1=0                                  # pressue for this element (mid point)
            self.Q1=0                                  # flux for this element (mid point)
            self.u1,self.v1=0,0                        # piece-wise constant for each element (mid point)
        
        if (self.element_type=="Linear"):
            self.bd_value1=0                           # boundary condition value1
            self.bd_value2=0                           # boundary condition value2
            self.P1=0                                  # pressure on the first node
            self.P2=0
            self.Q1=0                                  # left flux on a linear node[Left]
            self.Q2=0                                  # right flux on a linear node[Right]
            self.q1,self.q2=0,0                        # flux on the first,second node
            self.u1,self.u2=0,0                        # pressure derivative on x direction (Node1,Node2)
            self.v1,self.v2=0,0                        # pressure derivate on y direction
        
        if (self.element_type=="Quad"):
            self.bd_value1=0                           # boundary condition value1
            self.bd_value2=0                           # boundary condition value2
            self.bd_value3=0                           # boundary condition value3
            self.P1=0                                  # pressure on the first node
            self.P2=0                                  # pressure on the second node
            self.P3=0                                  # pressure on the third node(shared with the 1st node of next element)
            self.Q1=0                                  # right flux on the first node
            self.Q2=0                                  # middle flux on middle node, left flux and right flux for a middle is the same
            self.Q3=0                                  # left flux on the third node
            self.u1,self.u2,self.u3=0,0,0              # pressure derivative on x direction (Node1,Node2,Node3)
            self.v1,self.v2,self.v3=0,0,0              # pressure derivate on y direction
            
            
    def set_BC(self,bd_Indicator,bd_value,mode=0):
        #set up boundary condition for a element
        #mode-0 constant value along a element
        #mode-1 assign (1,2,3) values for a element

        self.bd_Indicator=bd_Indicator
        if(bd_Indicator==2):#Robin boundary conditions
            self.bd_Indicator=1
            self.Robin_alpha=1

        if (self.element_type=="Const"):
            if(mode==0):
                self.bd_value1=bd_value
            elif(mode==1):
                self.bd_value1=bd_value[0]
        if (self.element_type=="Linear"):
            if(mode==0):
                self.bd_value1=bd_value                          
                self.bd_value2=bd_value
            elif(mode==1):
                self.bd_value1=bd_value[0]
                self.bd_value2=bd_value[1]
        if (self.element_type=="Quad"):
            if(mode==0):
                self.bd_value1=bd_value                         
                self.bd_value2=bd_value                           
                self.bd_value3=bd_value
            elif(mode==1):
                self.bd_value1=bd_value[0]                         
                self.bd_value2=bd_value[1]                           
                self.bd_value3=bd_value[2]

    def get_ShapeFunc(self,Pts):
        #Interpolate the solution on the 1D boundary element
        #order=0-constant,1-linear,2-quadratic
        #Pts-Query point Ele_Pts-Element node points
    
        phi=[] #weights of shape function
        Pts_a=(self.xa, self.ya)
        Pts_b=(self.xb, self.yb)
        
        local=-1+2*calcDist(Pts,Pts_a)/calcDist(Pts_a,Pts_b)
        
        if(self.element_type=="Linear"):#Two nodes
            phi.append(0.5*(1-local))
            phi.append(0.5*(1+local))
        if(self.element_type=="Quad"):#Three nodes
            phi.append(0.5*local*(local-1))
            phi.append((1-local)*(1+local))
            phi.append(0.5*local*(local+1))
        
        return phi
    
    def reset_Element(self):
        #set the intial condition and solution in default model
        #[Boundary Conditions & Values]
        self.bd_Indicator=1                           
        if (self.element_type=="Const"):
            self.bd_value1=0                           
            self.P1=0                                  
            self.Q1=0                                  
            self.u1,self.v1=0,0                        
        
        if (self.element_type=="Linear"):
            self.bd_value1=0                           
            self.bd_value2=0                           
            self.P1=0                                 
            self.P2=0
            self.Q1=0                                  
            self.Q2=0                                  
            self.q1,self.q2=0,0                        
            self.u1,self.u2=0,0                        
            self.v1,self.v2=0,0                        
        
        if (self.element_type=="Quad"):
            self.bd_value1=0                           
            self.bd_value2=0                           
            self.bd_value3=0                           
            self.P1=0                                  
            self.P2=0                                  
            self.P3=0                                  
            self.Q1=0                                  
            self.Q2=0                                 
            self.Q3=0                                  
            self.u1,self.u2,self.u3=0,0,0           
            self.v1,self.v2,self.v3=0,0,0        



