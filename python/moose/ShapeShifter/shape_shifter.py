'''<Modifies morphology files (.p) for comp. simulations from types below>
   <Condenses .p files of neuron traces to maintain specific lambda (ac or dc) and removes 0 length compartments.>
    Copyright (C) <2016>  <Saivardhan Mada>
    Copyright (C) <2017>  <Avrama Blackwell>
    Copyright (C) <2021>  <Jonathan Reed>
    Copyright (C) <2022>  <Estiphanos Wodajo>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.'''

#Usage: python shape_shifter.py --file 'filename.p' --type 'condense'
#Types:
#  '0'        remove compartments of size 0
#  'condense' combine compartments of similar radius (specify --rad_diff 0 to only combine identical radii),
#               electrotonic length not to exceed max_len* lambda.
#  'expand'   to change single, long compartment (e.g. a Neuron software segment) into multiple smaller compartments
#               electrotonic length of subdivided compartments do not exceed max_len* lambda
#  'radii'    to change the radius value depending on the distance to the end of the longest branch
# can specify alternative values to default rm [4], cm [0.01], ri [2.5] in SI units
# can specify frequency (--f) for ac lambda calculation, current default is 0.1 hz
# can specify maximum electrotonic length (--max_len) current default is 0.1, specify 0 to use dc lambda
# can specify maximum difference (rad_diff) in radii for combining adjacent compartments, default is 0.1 (=10%)
# change info or debug (below) to get additional information while running program


#Ideal Usage Scenario:
#run shape_shifter.py through type radii for more accurate diameters
#can currently accept either .swc or .p morphology files

#in Shape_Shifter Directory:
#requires file_extract.txt from morph_feature_extract to load feature values
#requires model.txt from morph_feature_analysis.py to load in OLS model

# Input:   python shape_shifter.py --file morph_file.swc --type radii --model model.txt
# Ouput:   morph_file_org.p
 
#run shape_shifter.py again through type condense to combine similar compartments together for future simulation
#can also pass additional parameters i.e. f (frequency) and radius difference from optional arguments above
# Input:   python shape_shifter.py --file filenameconvert.p --type condense --f 100 --rad_diff 0
# Ouput:   filenameconvertoutout.p

#TO DO:
# test remove_zeros and condense (--type 'condense') using additional p files
#  - validate voltage response with simulations 
# read (and use) rm, cm and ri from p file
# write rm, cm and ri to p file if (a) not already specified and (b) given as input parameters

#George Mason University
#Saivardhan Mada
#Jul 20th, 2016
#Avrama Blackwell
#Apr 28, 2017
#Jonathan Reed
#Mar 14, 2021

from __future__ import print_function, division
import sys
import os
import glob
import argparse
import collections
import numpy as np
from scipy.stats import pearsonr
from extract_dynamic import create_dict
import matplotlib.pyplot as plt
import datetime
import copy

debug=0   #default is 0
info=0    #default is 1
#Globals for compartment values stored in list structure
CHILD = 0; PARENT = 1; X = 2; Y = 3; Z = 4; DIA = 5; COMPLEN = 6; END_DIS = 7
class morph:
        
        def __init__(self,input_file):
                self.linelist,self.comments = self.read_file(input_file)
                self.soma_count()
                self.remove_zeros()
               
        def read_file(self,input_file):                 #read either .swc or .p morphology file and convert to .p if needed for morph-changes
                data_lines = [];comment_lines=[]
                lines = open(input_file, 'r').readlines()
                for line in lines:                      #avoid comment lines
                    if line[0] !='*' and line[0] !='/' and line[0] != '\n' and line[0] != '\r' and line[0] != '#':
                        copy_line = line.split()
                        for x in range(2,6):            #change certain values to floats for calculations
                                copy_line[x] = float(copy_line[x])
                        data_lines.append(copy_line)
                    else:
                        if line[0] == '#':
                                comment_lines.append('//' + line[1:-1])
                        else:
                                comment_lines.append(line)
                        
                        
                _,extension = os.path.splitext(input_file)

                if extension == '.p': #default file format for morph-changes
                         return data_lines,comment_lines
                        
                elif extension == '.swc': #change to .p file format, same coordinates as .swc file
                        comment_lines.append('# Converted from .swc to .p on '+str(datetime.datetime.now()) + '\n')
                        from convert_swc_pfile import swc_to_p
                        parlist = []
                        for x in range(5):
                                parlist.append(list(zip(*data_lines))[x]) #list of parent values
                        newlines=swc_to_p(data_lines,parlist)
                        
                        return newlines,comment_lines

        def soma_count(self):                            #count number of soma nodes, usually 3-pt or 1-pt
                soma_start = self.linelist[0]            #by default, the first soma node should connect to all other nodes
                self.soma_node_list = []
                self.soma_nodes = 0   
                self.other_node_list = []                  
                for line in self.linelist:               #check for all soma nodes with _1 ending
                        if '_1' in line[0]:
                            self.soma_nodes = self.soma_nodes + 1
                            self.soma_node_list.append(line)
                        else:
                             self.other_node_list.append(line)
                if self.soma_nodes == 1:
                        print('***1-pt soma detected***')
                
                if self.soma_nodes == 3:
                        print('***3-pt soma detected***') #default 1_1 at coordinates 0,0,0 --> merge to single 1-pt soma
                        comp1 = self.linelist[1]; comp2 = self.linelist[2]
                        check_if_parent = []
                        for num,comp in enumerate(self.linelist):   #remove extra soma nodes which do not connect to others (only visuallizes width)
                                if comp[PARENT] == comp1[CHILD] or comp[PARENT] == comp2[CHILD]:
                                        check_if_parent.append('true')
                        print(len(check_if_parent))
                        if len(check_if_parent) == 0 and soma_start[DIA] == comp1[DIA] == comp2[DIA] and soma_start[CHILD] == comp1[PARENT] == comp2[PARENT]:
                                #print('TRUE')
                                for val in range(X,DIA):
                                        soma_start[val] = comp1[val] - comp2[val]
                                del self.linelist[2]
                                del self.linelist[1]
                        else:
                                ('***Multiple soma node connections; possibly check morphology file***') #usually extra 3-pt soma nodes exact diameter equal to soma
                elif self.soma_nodes == 2 or self.soma_nodes > 3:
                    print('***More than 3-pt soma; possibly check morphology file***') #some morphology files contain multiple soma nodes
                
        def remove_zeros(self): 
                newlines=[]; parent_dict = {}
                #Calculate compartment length from XYZ values
                for line in self.linelist:
                        complen = np.sqrt((line[X])**2 + (line[Y])**2 + (line[Z])**2)
                        line.append(complen) 
                        
                #Remove Zeroes and Replace oldparent id with newparent id
                for line in self.linelist:
                        #removes any compartments with 0 distance or diameter OTHER THAN soma
                        if((line[DIA] == 0  or line[COMPLEN] == 0) and line[PARENT] != 'none'):
                                #relabel remaining children to previous parent (or compartment that is deleted)
                                # if                        4,3 0 0 0 <--- compartment needs to be removed since size 0
                                # then                      5,4 x y z <--- original (CHILD) compartment needs PARENT change to existing compartment
                                # should be changed to      5,3 x y z <--- new parent connection to remaining children  
                                parent_dict[line[CHILD]] = line[PARENT]
                                print ("######## Zero size comp removal: orig num lines=", line[CHILD], ", new num lines=", line[PARENT])
                        else:
                                newlines.append(line)
                                
                #Call to change parent if removing 0_compartments
                if parent_dict: #checks if parent_dict has any items, THEN does recursion
                        print('Zero point compartments removed; remaining comparments require parent-update for reconnection')
                        print(parent_dict)
                        parent_len = len(parent_dict.items())
                        if parent_len < 100: #arbitrary number; 100 zero-point compartments
                                for num, line in enumerate(self.linelist):
                                        if line[PARENT] != 'none':
                                                counter = 0 
                                                line = self.replace_par(parent_dict, counter, line)
                                print(len(newlines))
                                self.linelist = newlines
                        else:
                                print('Many zero-point compartments --> check morphology file')

        #replace parent values of compartments whose original parents were zero-point compartments and removed 
        def replace_par(self,parent_dict, counter, line):
                print('Original line', line)
                if line[PARENT] in parent_dict:
                        print('Line child', line[CHILD], 'Line parent', line[PARENT])
                        counter = counter + 1
                        line[PARENT] = parent_dict[line[PARENT]]
                        self.replace_par(parent_dict, counter, line)
                else:
                        if counter>0:
                                print('fixed line', counter ,line)
                        return line

def soma_condense(m,lambda_factor,soma):
        Lines = m.soma_node_list

        if(soma == "no_change"):
                print("**no changes to soma**")
                return

        # creates one point soma for multi-point somas done w/cross-sectional tracing
        if (soma == "cylinder"):
                soma1 = Lines[0]
                len_soma1=calc_electrotonic_len(soma1,lambda_factor)
                length1 = np.sqrt(soma1[X]**2 + soma1[Y]**2 + soma1[Z]**2)
                surface_tot_1 = np.pi * soma1[DIA] * length1
                Ltot = len_soma1
                surface_tot = surface_tot_1
                for soma2 in Lines[1:]:
                    len_soma2=calc_electrotonic_len(soma2,lambda_factor)
                    length2 = np.sqrt(soma2[X]**2 + soma2[Y]**2 + soma2[Z]**2)
                    surface_tot_2 = np.pi * soma2[DIA] * length2
                    surface_tot += surface_tot_2
                    Ltot += len_soma2
                x,y,z,diameter=calc_newcomp(Lines,surface_tot,Ltot,lambda_factor)  
                newcomp = ['1_1', 'None', x, y, z, diameter]   

       # creates one point soma for multi-point somas done w/countour tracing
        if(soma == "contour"):
                soma1 = Lines[0]
                
                
                x_max = soma1[X]; y_max = soma1[Y]; z_max = soma1[Z]; dia = []; x_min = 0; y_min = 0; z_min=0
                dia.append(soma1[DIA])
                soma2_x = soma1[X] ; soma2_y = soma1[Y]; soma2_z = soma1[Z]
                for soma2 in Lines[1:]:
                        # converts from relative to absolute coordinates
                        soma2_x = soma2_x + soma2[X] ; soma2_y = soma2_y + soma2[Y] ; soma2_z = soma2_z + soma2[Z]
                        x_max = max(soma2_x,x_max); x_min = min(soma2_x,x_min)
                        y_max = max(soma2_y,y_max); y_min = min(soma2_y,y_min) 
                        z_max = max(soma2_z,z_max); z_min = min(soma2_z,z_min)
                        dia.append(soma2[DIA])
                print('soma2_x: ', soma2_x,'soma2_y: ', soma2_y, 'soma2_z: ', soma2_z)
                print('x_max: ', x_max,'y_max: ', y_max, 'z_max: ', z_max)
                diameter = np.around(np.mean(dia),4)
                leng = np.sqrt((x_max-x_min)**2 + (y_max-y_min)**2 + (z_max-z_min)**2)                     
                Ltot = leng/lambda_factor
                surface_tot = leng * np.pi * diameter
                x = x_max - x_min; y = y_max - y_min; z = z_max - z_min
                x,y,z = comp_angle(x,y,z,leng)
                newcomp = ['1_1', 'None', str(x), str(y), str(z), diameter]

        #adds the dendrites to the list to be written into the file
        temp = []
        m.linelist = newcomp
        temp.append(newcomp)
        temp.extend(m.other_node_list)
        m.linelist = temp

def calc_lambda (type1, RM, RI, CM, F):
        tm = RM * CM #time constant
	#Lambda when working with diameter of cables.  Use 2.0 if working with radius
        dc_factor = np.sqrt(RM/(RI*4.0))*1000 #1000 is for unit conversion to microns 
        partial_ac= 2.0*np.pi*F*tm 
        ac_factor = dc_factor * np.sqrt(2.0/(1.0+np.sqrt(1.0+partial_ac**2.0)))
        return ac_factor 

def calc_electrotonic_len(line,factor):
        lamb = factor * np.sqrt(float(line[DIA])) #calculates ac or dc lambda from compartment radius
        if debug:
                print('    calc_len comp %s lambda=%.1f len=%.3f L=%.5f' % (line[CHILD], lamb, line[COMPLEN], line[COMPLEN]/lamb))
        return line[COMPLEN]/lamb

def write_file(output, line):
        write_line = [str(val) for val in line[CHILD:COMPLEN]]
        write_line = ' '.join(write_line) #converts from list of strings to single string
        output.write(write_line + '\n')   #writes every node as new line

def comp_angle(x,y,z,l):
        theta = np.arctan2(y,x) 
        phi = np.arccos(z/np.sqrt(x*x+y*y+z*z)) if (x>0 or y>0 or z>0) else 0
        
        if debug:
                print ('theta %.4f phi %.4f ' %(theta,phi))
        x = np.round(l*np.cos(theta)*np.sin(phi),3)
        y = np.round(l*np.sin(theta)*np.sin(phi),3)
        z = np.round(l*np.cos(phi),3)
        return x,y,z
        
def calc_newcomp(condense,surface_tot,Ltot,lamb_factor):
        #Equations from Hendrickson J Comput Neurosci 2011
        #surface_tot=pi*diam*len
        #Ltot=len*sqrt((4*Ra)/(Rm*diam))
        #solve simultaneously for diameter and length
        diameter=(surface_tot/(Ltot*np.pi*lamb_factor))**(2/3.)
        l=surface_tot/(np.pi*diameter)
        if debug:
                print('TSA: dia %.5f, l=%.2f tsa=%.1f Ltot=%.5f' % (diameter, l, np.pi*diameter*l,l/(lamb_factor*np.sqrt(diameter))))
        x = 0.0; y = 0.0; z = 0.0
        #total distance in x, y and z.  
        for comp in condense:
                x += comp[X]
                y += comp[Y]
                z += comp[Z]
        if debug:
                print ('xtot %.3f ytot %.3f ztot %.3f'%(x, y, z))
        x,y,z = comp_angle(x,y,z,l)
        return str(x),str(y),str(z),str(np.round(diameter,3))

def subdivide_comp(line,segs):  #only for type expand --> non-working version
        lineset = []
        print ("subdivide", line[CHILD], "x,y,z,len", line[X], line[Y], line[Z], line[COMPLEN], "into", segs, "segments")
        newline=copy.copy(line) #1. initialize newline to be the same as original line
        for j in [X,Y,Z]: #2. change the x,y,z coordinates to be original values / number of segments
                newline[j]=np.round(line[j]/segs,5) 
        seg_length = segs*np.sqrt((newline[X])**2 + (newline[Y])**2 + (newline[Z])**2) #3. calculate segment length of the new line
        for i in range(segs):
                lineset.append(copy.copy(newline))
                if i > 0: #update the parent of each new line, and add a number to the name of the segment
                        lineset[i][PARENT] = lineset[i-1][CHILD]
                        if '_' in lineset[i][CHILD]: #naming convention for swc files - unlikely to subdivide
                                lineset[i][CHILD]=lineset[i][CHILD].split()[0]+chr(i+97)+lineset[i][CHILD].split()[1]
                        elif '[' in lineset[i][CHILD]: #array - need to re-order segments
                                lineset[i][CHILD] = lineset[i][CHILD] + str(i)  #FIXME
                        else:
                                lineset[i][CHILD] = lineset[i][CHILD] + chr(i+64) #captial letter
                #save new parent_dict to connect subsequent compartment to new segmented one either here or in type = 'expand'
        if info:
                for i in range(segs):
                        print ("new seg", i, lineset[i])
                print ("total length", seg_length, "single seg", seg_length/segs,'old seg len', np.sqrt((line[X])**2 + (line[Y])**2 + (line[Z])**2) )
        return lineset

def to_condense(condense,surface_tot,Ltot,lambda_factor,rad_diff,delta_rad,line,comp2,outfile):
        if len(condense):
                #cannot add any additional compartments.  Condense the set
                x,y,z,diameter=calc_newcomp(condense,surface_tot,Ltot,lambda_factor)
                if info:
                        print ('#######condense', condense, 'stop before', comp2[CHILD])
                        print ('new: x y z',x,y,z, diameter )
                newcomp = [condense[-1][CHILD], condense[0][PARENT], x, y, z, diameter]
                write_file(outfile, newcomp)
                condense = []  #reinitializing to condense next set of compartments
                Ltot = 0
                surface_tot = 0
        else:
                #cannot condense this comp and nothing in condense set.  Just print out line
                write_file(outfile, line)
                if info:
                        print ('not condensing',len(condense),Ltot, line[CHILD], "rad", rad_diff,delta_rad)
        return condense, Ltot, surface_tot

def branch_comp(linelist):
        parents = [line[PARENT] for line in linelist] #create a list of just parents
        parent_count = collections.Counter(parents)   #create dictionary giving number of times each parent occurs
        branch_points = [line[CHILD] for line in linelist if parent_count[line[CHILD]]>1] #set of parents that appear more than once
        #print('branch points', branch_points)
        return branch_points, parents
'''
def end_comp(linelist, parents):
        unique_parents=set(parents) #set() eliminates duplicate parents
        children=[line[CHILD] for line in linelist] #create a list of children
        end_points=list(set(children)-unique_parents)
        print(end_points)
        return end_points
'''
def calc_enddis(dis_to_end, par_comp, line, ending = 0):
        if ending == 0:                                     #if endpoint
                dis_to_end = dis_to_end + line[COMPLEN]/2
        else:                                               #all other comps. except soma
                dis_to_end = dis_to_end + line[COMPLEN]/2 + par_comp
                par_comp = line[COMPLEN]/2
        end_dis = dis_to_end
        return dis_to_end, par_comp, end_dis

def write_comments(fileptr,m):
        relative=False
        for line in m.comments:
                if line.startswith('*relative'):
                        relative=True
                fileptr.write(line)
        if not relative:
                fileptr.write('*relative' + '\n')

def condenser(m, type1, max_len, lambda_factor, h):
        #num_comps=0
        ######## type = '0' removes 0 length compartments, this is done in the class, so just write file
        filename,_ = os.path.splitext(h.file)
        if(type1 == "0"):
                removed = open(filename + '_removed.p','w')
                m.comments.append('// Modified by removing zero size segments on '+str(datetime.datetime.now()) + '\n')
                write_comments(removed,m)
                for line in m.linelist:
                        write_file(removed,line)
                removed.close()
                print('Removed Zero point Compartments : Created ' + filename + '_removed.p')

        if(type1 == "condense_soma"): #not really needed.  Determine if soma has been condensed, and add comment
                file = open(filename + '_somacondensed.p','w')
                file.write('*relative' + '\n')
                for line in m.linelist:
                        write_file(file,line)
                file.close()
                print('Condensed multi-point soma to a one-point soma : Created ' + filename + '_somacondensed.p')

        ####### type = "expand" takes long compartments and subdivides into multiple "segments"  --> in progress non-working version
        if (type1 == "expand"):
                #Expands linelist to include new created segments
                
                new_par = {} #holds all compartments whose parent needs to change with included segments
                newlinelist = [];added_lines=[]
                for num,line in enumerate(m.linelist):
                        L_comp = calc_electrotonic_len(line,lambda_factor)
                        print ("max_len", max_len, "L", L_comp, 'of', line[CHILD])
                        if L_comp > max_len and line[CHILD] != 'soma' and line[CHILD] != '1_1':
                                print('Adding segments to: ', line[CHILD])
                                segs=int(np.ceil(L_comp/max_len))
                                newlines=subdivide_comp(line,segs)
                                for ii,seg in enumerate(newlines):
                                        newlinelist.append(seg)
                                        if ii>0:
                                                added_lines.append(seg)
                                                print('Segment added: ', seg[CHILD])
                                new_par[m.linelist[num][CHILD]] = newlines[-1][CHILD]
                        else:
                                newlinelist.append(line)
                        if info:
                                print ("OK", line)

                ##### Replaces parent-child of any compartment whose parent was expanded
                print('new parent dictionary',len(new_par),new_par)
                print(len(newlinelist), newlinelist)
                
                for line in newlinelist:                #change parent-child here
                        if line[PARENT] in new_par.keys():
                                if line not in added_lines:
                                        line[PARENT]=new_par[line[PARENT]]

                ####### write to file
                expanded = open(filename + '_expanded.p','w')
                m.comments.append('//Modified by expanding line segments into multiple segments on '+str(datetime.datetime.now()) + '\n')
                m.comments.append('// Used parameters: lambda_factor='+str(lambda_factor)+'\n')
                write_comments(expanded,m)
                for line in newlinelist:
                        write_file(expanded,line)
                expanded.close()
        
        ######## type = condense condenses branches with similar radius and combined electronic length < 0.1 lambda
        if (type1 == "condense"):    #if rad_diff = 0, only condenses branches with same radius
                branch_points, parents = branch_comp(m.linelist)
                #cvapp converts .swc to .p file format AND from absolute to relative coordinates
                #print(m.linelist)
                #print('Original Compartments : ' + len(m.linelist[0]))
                condensed = open(filename + '_condensed.p','w')
                m.comments.append('// Modified by removing zero segs and condensing short segments on '+str(datetime.datetime.now()) + '\n')
                m.comments.append('// Used parameters: lambda_factor='+str(lambda_factor)+',rad_diff='+str(h.rad_diff)+'\n')
                m.comments.append('*set_global RA '+str(h.ri)+'\n')
                m.comments.append('*set_global RM '+str(h.rm)+'\n')
                m.comments.append('*set_global CM '+str(h.cm)+'\n')
                write_comments(condensed,m)

                Ltot = 0; surface_tot = 0; condense = [] #list to hold compartments to be condensed
                for num,line in enumerate(m.linelist):
                        comp1 = line
                        if debug:
                                print ('**** begin', line[CHILD])
                        if num <= (len(m.linelist)-2):
                                comp2 = m.linelist[num+1]
                                len_comp1=calc_electrotonic_len(comp1,lambda_factor)
                                len_comp2=calc_electrotonic_len(comp2,lambda_factor)
                        if len(condense): #assumes condense has values
                                delta_rad=abs((condense[0][DIA] - comp2[DIA])/condense[0][DIA])
                                tot_len=len_comp2+Ltot
                        else:
                                delta_rad=abs((comp1[DIA] - comp2[DIA])/comp1[DIA])
                                tot_len=len_comp1 + len_comp2
                        #rad_diff default is 0.1, max_len default is 0.1, see parameters at bottom
                        if info:
                                print ('comp1', comp1[CHILD], comp1[PARENT], 'comp2', comp2[CHILD], comp2[PARENT])
                        if(delta_rad <= h.rad_diff and comp2[PARENT]==comp1[CHILD] and tot_len < max_len and comp1[CHILD] not in branch_points):
                                print('***comps to be condensed: ', comp1[CHILD],comp2[CHILD], '***')  #branch point list has to be created before this point
                                if info:
                                        print('delta_rad <= rad_diff for :', 'comp1', comp1, 'comp2', comp2)
                                length1 = np.sqrt(comp1[X]**2 + comp1[Y]**2 + comp1[Z]**2)
                                length2 = np.sqrt(comp2[X]**2 + comp2[Y]**2 + comp2[Z]**2)
                                #if the radii are almost the same and comp2 is attached to comp1
                                #if this is last line of file, comp2=comp1, thus comp2[1] != comp1[0], skip down to condensing or writing file
                                if len(condense) == 0:
                                        #if this is 1st compartment of a set, add it
                                        condense.append(comp1)
                                        Ltot = len_comp1
                                        surface_tot = np.pi * comp1[DIA] * length1
                                #always add the 2nd compartment to set of comartments to be condensed
                                condense.append(comp2)
                                Ltot=Ltot+len_comp2
                                surface_tot=surface_tot+(np.pi * comp2[DIA] * length2)    
                        else:
                                condense, Ltot, surface_tot = to_condense(condense,surface_tot,Ltot,lambda_factor,h.rad_diff,delta_rad,line,comp2,condensed)
                                
                #temp_name = m.filename.split('.swc')[0] + '_condense.swc'
                #print('Created : ' + m.filename  )#+ ' with ' + len(m.linelist) + ' Condensed Compartments')
                #print(len(m.outfile))
                #print ("finished,", len(m.linelist), "output compartments")
                condensed.close()
                print('Condensed Compartments : Created ' + filename + '_condensed.p')

        if (type1 =="radii"):
                read_model = open(h.model,'r').readlines() #read model file and organize by node-type
                models = {}                                #save as dictionary for feature name (key) and coefficient (value)
                for line in read_model:
                        line = line.split()
                        if line[0] == 'Apical' or line[0] == 'Basal':
                                comp = line[0]
                                if not line[0] in models.keys():
                                        models[comp] = {}
                        elif line[0] == 'Initial' or line[0] == 'BP_Child' or line[0] == 'Continuing':
                                connect = line[0]
                                if not line[0] in models[comp].keys():
                                        models[comp][connect] = {}
                        elif len(line) == 2: 
                                models[comp][connect][line[0]] = float(line[1])

                feature_file = filename + '_extract.txt'
                features = create_dict(feature_file)
                for feature in features.keys():                    #remove trailing '\n' from final feature name
                        if '\n' in feature:
                                new_key = feature.strip('\n')
                                features[new_key] = features.pop(feature)

                soma_count = 0
                newrads = {}; newrads_i = {}
                pdict = {0:'Initial',1:'BP_Child',2:'Continuing'}  #original data (#'s) to dictionary organization (terms)
                cdict = {3:'Basal', 4:'Apical'}
                
                for num,line in enumerate(m.linelist):
                        #print(line[CHILD])
                        newrad = 0; newrad_i = 0
                        if '_1' in line[CHILD]:
                                soma_count = soma_count + 1
                                print(line[CHILD])
                        else:
                                new_num = num - soma_count   #features do not have soma extended values
                                ctype = cdict[features['TYPE'][new_num]]; pcon = pdict[features['PAR_CONNECT'][new_num]]
                                for feature in models[ctype][pcon]:
                                        if feature == 'PARENT_DIA':              
                                                if pcon == 'Initial':
                                                        newrad = newrad + models[ctype][pcon][feature] * (features['PARENT_RAD'][new_num]*2)
                                                        newrad_i = features['RADIUS'][new_num]*2
                                                else:
                                                        newrad = newrad + models[ctype][pcon][feature] * newrads[line[PARENT]]
                                                        newrad_i = newrad_i + models[ctype][pcon][feature] * newrads_i[line[PARENT]]
                                        elif feature=='const':
                                                newrad=newrad+models[ctype][pcon][feature]
                                                if pcon != 'Initial':
                                                     newrad_i=newrad_i+models[ctype][pcon][feature]   
                                        else:                              
                                                newrad = newrad + models[ctype][pcon][feature] * features[feature][new_num]
                                                if pcon=='Initial':
                                                        newrad_i=features['RADIUS'][new_num]*2
                                                if not '_1' in line[PARENT]:
                                                        newrad_i = newrad_i + models[ctype][pcon][feature] * features[feature][new_num]
                                newrads[line[CHILD]] = newrad
                                newrads_i[line[CHILD]] = newrad_i
                
                org_file = open(filename + '_org.p','w')
                pred_file = open(filename + '_pred.p','w')
                pred_i_file = open(filename + '_pred_i.p','w')
                zdia1_file = open(filename + '_zdia1.p','w')
                zdia2_file = open(filename + '_zdia2.p','w')
                
                for fname in [org_file,pred_file,pred_i_file,zdia1_file,zdia2_file]:
                        m.comments.append('// Modified by predicting radius on '+str(datetime.datetime.now()) + '\n')
                        m.comments.append('//radii predicted using '+h.model + '\n')
                        write_comments(fname,m)
                        #fname.write('*relative' + '\n')

                for num,line in enumerate(m.linelist):
                        if num >= soma_count:             
                                write_file(org_file,line)
                                pred_line = line
                                pred_line[DIA] = newrads[line[CHILD]]
                                write_file(pred_file,pred_line)
                                pred_i_line = line
                                pred_i_line[DIA] = newrads_i[line[CHILD]]
                                write_file(pred_i_file,pred_i_line)
                                zdia1_line = line
                                zdia1_line[DIA] = 1.0
                                write_file(zdia1_file,zdia1_line)
                                zdia2_line = line
                                zdia2_line[DIA] = 2.0
                                write_file(zdia2_file,zdia2_line)
                        else:
                                for fname in [org_file,pred_file,pred_i_file,zdia1_file,zdia2_file]:
                                        write_file(fname,line)   
                org_file.close()
                pred_file.close()
                pred_i_file.close()
                zdia1_file.close()
                zdia2_file.close()
                
 
if __name__ == '__main__':
        #set default parameters
        rm = 4.00 #ohms-m^2 
        ri = 2.50 #ohms-m
        cm = 0.010 #F/m^2
        max_len = 0.1 #electrotonic length
        f = .1 #Hz
        rad_diff=0.1

        #set up argument parsers
        parser = argparse.ArgumentParser()
        parser.add_argument('--file')
        parser.add_argument('--type', choices={'0','condense','expand','radii','condense_soma'}, default='0') #just remove zero size compartments
        #parser.add_argument('--path', type = str) 
        parser.add_argument('--soma', choices={'no_change','cylinder','contour'}, default = 'no_change')
        parser.add_argument('--model')
        parser.add_argument('--save_as') #will need to reformat file if .swc output desired
        
        parser.add_argument('--rad_diff', default=rad_diff, type=float)
        parser.add_argument('--rm', default=rm, type=float)
        parser.add_argument('--ri', default=ri, type=float)
        parser.add_argument('--cm', default=cm, type=float)
        parser.add_argument('--f', default=f, type=float)
        parser.add_argument('--max_len', default=max_len, type=float)
        #ARGS='--file simple.p --type expand'
        try:
                args = ARGS.split() #in python: define space-separated ARGS string
                do_exit = False
        except NameError: #if you are not in python, read in filename and other parameters
                args = sys.argv[1:]
                do_exit = True
        h = parser.parse_args(args)
        newmorph=morph(h.file)
        
        #calculate lambda
        lambd_factor=calc_lambda(h.type, h.rm, h.ri, h.cm, h.f)
        #print('params', h, 'lambda', lambd_factor)
        
        #calls soma_condense if # of soma points is greater than 3
        if newmorph.soma_nodes > 3:
                soma_condense(newmorph,lambd_factor,h.soma)
        
        #Optionally, can condense multiple comps into one, expand large comp into multiple, or assign radii when there are none
        condenser(newmorph, h.type, h.max_len, lambd_factor, h)
