'''<Reformats .p data file format into .swc file format.>
   <Output .swc file>
    Copyright (C) <2019>  <Zhi Cheng Wu>

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

# Usage:
# Output: filenameconvert.p

# George Mason University
# Jonathan Reed and Zhi Cheng Wu
# March 1, 2019
# Rewritten by Subhasis Ray, 2025-04-17

import argparse
import datetime
from convert_swc_pfile import read_data_comments

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--file")
    args = parser.parse_args()
    filename = args.file

    lines = open(filename, 'r').readlines()

    data_lines, comment_lines = read_data_comments(lines)

    comment_lines.append('# Original .p file : ' + filename + '\n')
    comment_lines.append(
        '# Modified to .swc file on : ' + str(datetime.datetime.now()) + '\n'
    )

    all_new_lines = []
    # rearranges values for .p format
    # Columns in the .p format are
    #     compartment_name parent_name x y z diameter
    # whereas swc format has
    #    node_id structure_type x y z radius parent_id
    #
    proto_fields = ('comp', 'parent', 'x', 'y', 'z', 'dia')
    swc_fields = ('comp', 'stype', 'x', 'y', 'z', 'rad', 'parent')
    proto_list = [dict(zip(proto_fields, line)) for line in data_lines]
    swc_list = []
    swc_dict = {}
    root = None
    for pdict in proto_list:
        name, stype = pdict['comp'].split('_')
        sdict = {
            'comp': name,
            'stype': stype,
            'rad': float(pdict['dia']) / 2.0,
            'children': [],
        }
        swc_dict[name] = sdict
        swc_list.append(sdict)
        if pdict['parent'] == 'none':
            sdict['parent'] = '-1'
        else:
            sdict['parent'] = pdict['parent'].split('_')[0]
        sdict['x'] = float(pdict['x'])
        sdict['y'] = float(pdict['y'])
        sdict['z'] = float(pdict['z'])
        sdict['children'] = []

    # Now construct the tree to convert the relative x,y,z to absolute
    for name, sdict in swc_dict.items():
        parent = sdict['parent']
        if parent == '-1':
            root = name
        else:
            swc_dict[parent]['children'].append(name)

    assert root is not None, 'Could not find root element'

    stack = [root]
    visited = set()
    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)
        parent = swc_dict[node]['parent']
        if parent != '-1':
            for dim in ('x', 'y', 'z'):
                swc_dict[node][dim] = round(
                    swc_dict[node][dim] + swc_dict[parent][dim], 4
                )
        stack.extend(swc_dict[node]['children'])

    out_name = filename.split('.p')[0] + '.swc'
    outfile = open(out_name, 'w')
    for line in comment_lines:
        outfile.write(f'# {line}')
    for sdict in swc_list:
        write_line = ' '.join(
            [str(sdict[key]) for key in swc_fields]
        )  # converts from list of strings to single string
        outfile.write(write_line + '\n')
    outfile.close()

    print(
        'Converted '
        + str(len(data_lines))
        + ' compartments from original file : '
        + str(filename)
    )
    print('Modified file created : ' + str(out_name))
