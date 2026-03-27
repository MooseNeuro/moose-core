'''<Extracts data values from .txt .p .swc files>
    Copyright (C) <2020>  <Zhi Cheng Wu>

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

#Usage:  python extract_dynamic.py or import 
#        Have the data file being extracted within the same cwd, change file name in main class
#        Data file's first line of string must be the header of the data values of the columns separated by spaces
#        Data extracted are all changed to floats, only extract numerical values of data (no units, etc)
#        
#        Use as function through "from extract_dynamic import create_dict" in beginning line of main python code
#        create_dict function returns a dictionary so a variable has to be assigned when called: temp = create_dict('*.txt')
#        You can then manipulate the dictionary using the keys from the header of the data
#        Can work with *.swc, *.p, *.txt
#George Mason University
#Zhi Cheng Wu
#Feb. 27, 2020
#simplified by Avrama Blackwell
#April 15, 2021

import re

def create_dict(pythonfile):
    newFile = open(pythonfile,'r')
    content = newFile.readlines() #content now list of lines
    report = 0
    header = []
    for linenum,row in enumerate(content):
        if row[0] == '*' and row[1] == 'C':
        #naming system of dict dynamic
            header = row.split('; ')
            header[0] = 'CHILD'
            final_dict={cat:[] for cat in header}
            startline=linenum+1
            print(pythonfile,'linenumber that begins data',startline)
            break
    if len(header)==0:
        print("!!!!!! Possible error in data set format. No header row beginning *CHILD")        
    for kk,line in enumerate(content[startline:]):
        row = re.findall(r"[-+]?\d*\.\d+|\d+", line) #could also use line.split()
        if len(row)!=len(header):
            print("!!!!!! Possible error in data set format.  Too many or too few numbers in the row\n",row)            
            report += 1
        else:
            for count,categories in enumerate(header):
                final_dict[categories].append(float(row[count]))
    if report:
        print("!!!!!!!!!!!! Possible error in data set format.", report,'lines are wrong length')
    return final_dict
def main():
    temp = create_dict('Adol-20100419cell1.CNG_extract.txt')
    print(temp)
if __name__ == "__main__":
    main()
        
