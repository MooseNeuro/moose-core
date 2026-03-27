'''<Reformats .swc data file format into .p file format.>
   <Output .p file can be processed through shape_shifter.py for morphological modifications>
    Copyright (C) <2019>  <Jonathan Reed>

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

#Usage:  python convert_swc_pfile.py --file filename.swc
#Output: filenameconvert.p

#George Mason University
#Jonathan Reed
#March 1, 2019

import argparse
import datetime

def swc_to_p(data_lines,parlist):
    newlines=[]
    #rearranges values for .p format
    for num,line in enumerate(data_lines):
        newline = line[:6]
        newline[0] = (str(line[0]) + '_' + str(line[1]))
        if num == 0: #soma line always first in .swc file, unique parent-type 'none'
            newline[1] = 'none'
        else:
            parent_index = parlist[0].index(line[6])  #parlist[0] refers to parent location of comp at line[6]
            parent_type = parlist[1][parent_index]
            for x in range(2,5):
                #convert to relative coordinates, see https://github.com/INCF/swc-specification
                newline[x] = round(float(data_lines[num][x]) - float(parlist[x][parent_index]),4) 
            newline[1] = str(line[6]) + '_' + str(parent_type)
        newline[5] = round(float(newline[5])*2,4) #.p file format takes diameter values instead of radius
        newlines.append(newline)
    return newlines

def read_data_comments(lines):
    #copies intended values for .pfile from .swcfile into list
    data_lines = []
    comment_lines=[]
    for line in lines:
        if line[0] !='*' and line[0] !='/' and line[0] != '\n' and line[0] != '\r' and line[0] != '#':
            copy_line = line.split()
            data_lines.append(copy_line)
        else:
            comment_lines.append(line) #may need to replace # with // depending on moose
    return data_lines,comment_lines

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    args = parser.parse_args()
    filename = args.file

    lines = open(filename, 'r').readlines()
    data_lines,comment_lines=read_data_comments(lines)
    comment_lines.append('# Original .swc file : '+filename + '\n')
    comment_lines.append('# Converted from .swc to .p file on : '+str(datetime.datetime.now()) + '\n')

    #list of parent values
    parlist = []
    for x in range(5):
        parlist.append(list(zip(*data_lines))[x])

    newlines=swc_to_p(data_lines,parlist)

    #write newlines to file
    out_name = filename.split('.swc')[0] + 'convert.p'
    outfile = open(out_name,'w')

    for line in comment_lines:
        outfile.write(line)
    outfile.write('\n*relative\n') #indicate that the p file contains delta x,y,z values relative to parent compartment

    for line in newlines:
        write_line = ' '.join([str(val) for val in line]) #converts from list of strings to single string
        outfile.write(write_line + '\n')
    outfile.close()

    print('Converted ' + str(len(data_lines)) + ' compartments from original file : ' + str(filename))
    print('Modified file created : ' + str(out_name))
