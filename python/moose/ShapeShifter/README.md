Description
============
shape_shifter is a morphology converter which takes in neuron morphology files (.swc or Genesis .p) and simplifies dendritic morphology for more efficient use in model simulation. shape_shiter can combine sets of compartments with the same (or similar) radius and with combined length less than specified value of electrotonic length, caculated using either AC or DC methods. Previous trials of this program has resulted in reduction of the orginal file by almost 90%, and greatly increases processing speed in simulation with identical original (non-reduced) response. shape_shifter also can be used to transform a simple morphology with extremely long compartments into smaller compartments with same topology (connectivity).

**input files**

shape_shifter will accept .swc or .p morphology files for morphology conversion. Morphology files (.swc) can be attained from the NeuroMorpho repository through http://neuromorpho.org/ 

NOTE: shape_shifter has only been tested on swc morphologies with 3 point somata and .p files with one point somata

**shape_shifter usage**

 Input:
 ``` 
 python3 shape_shifter.py --file 'filename.swc' --type 'condense'
 ```
 Output:
 filename_condensed.p
 
type can be:
  - '0'        remove compartments of size 0; automatically completed if other types specified
  - 'condense' combine compartments of similar radius (specify --rad_diff 0 to only combine identical radii),
               electrotonic length not to exceed max_len* lambda.
  - 'expand'   to change single, long compartment (e.g. a Neuron software segment) into multiple smaller compartments
               electrotonic length of subdivided compartments do not exceed max_len* lambda
  - 'radii'    to change compartment width based on feature equations in OLS model (model.txt) from morph_feature_analysis

+ optional arguments:

  - can specify alternative values to default RM (--rm 4), CM (--cm 0.01), RI (--ri 2.5) for calculating lambda, units are SI
  - can specify frequency (--f) for ac lambda calculation, default is 0.1 hz, specify 0 to use dc lambda
  - can specify maximum electrotonic length (--max_len), default is 0.1
  - can specify criteria maximum difference (--rad_diff) in radii for combining adjacent compartments, default is 0.1 (=10%)
  - can specify model.txt (--model) to pass in feature equations for use in type radii (see Ideal Usage Scenario)
  
change info or debug parameter to get more or less information while running program

Utility Files
============

* convert_swc_pfile.py

   - will convert from swc format to .p format for use with the GENESIS and MOOSE simulation software
   - new name for each point/node:  node number + '_'+ node type
   - converts from absolute to relative coordinates (https://github.com/INCF/swc-specification)

   - Input:
   ``` 
   python3 convert_swc_pfile.py --file 'filename.swc'
   ```
   - Output:
   filenameconvert.p


* convert_to_swc.py

   - will convert from .p format to .swc format 
   - removes node type from node name (only works if p file generated from convert_swc_pfile.py)
   - converts from relative to absolute coordinates (https://github.com/INCF/swc-specification)


   - Input:
   ``` 
   python3 convert_to_swc.py --file 'filename.p'
   ```
   - Output:
   filenameconvert.swc


Calculating new diameter for neuron reconstructions
============
NeuroMorpho morphology files often inaccurate compartment (node) diameters.
To calculate diameter from morphology feature values:

A. run morph_feature_extract.py to calculate feature values from .swc morphology files

+ requires Python 2 for btmorph (https://btmorph.readthedocs.io/) to calculate feature values

  - Input:
  ```
  python2 morph_feature_extract.py --path /path/to/folder_with_swc_files 
  ```
  - Output:
  - filename_extract.txt

B. run morph_feature_analysis.py to compare features and create model equations

+ change binary variables to True generate sets of graphs: df_corr, parameter_plots, corr_matrices, final_predictions, xcorr, rall_test
+ change hist_features from [] to list of features to generate histograms
 
  - Input:
  ```
  python3 morph_feature_analysis.py --path /path/to/folder_with_swc_extract_files --seed integer --train_test npy_file
  ```
  - --seed specifies the random seed to split the files into training and testing sets, to allow reproducibility
  - --train_test allows you to specify the npy file with dictionary of training and testing files to reproduce the results in Reed and Blackwell 2021
  
  - Output:
  - multiple feature and correlation plots (.png), archive_model.txt
  
C. run shape_shifter.py through type radii to predict new radius for selected morphology 

+ .swc morphology file(s) and _extract.txt file(s) need to be in same directory
+ by default, will print multiple versions of morphology file with original diameter (org), predicted diameter (pred), predicted diameter including original inital diameters (pred_i)
+ archive_model.txt is the output file from morph_feature_analysis.py

 - Input:   
 ``` 
 python shape_shifter.py --file morphology_file.swc --type radii --model archive_model.txt
 ```
 - Ouput:
 - morphology_file_org.p, morphology_file_pred.p, morphology_file_pred_i.p
 
D. Optionally, run shape_shifter.py again through type condense to combine similar compartments together for future simulation

+ can also pass additional parameters i.e. f (frequency) and radius difference from optional arguments above
+ can run shape_shifter.py to reduce number of compartments for any .p file, independent of diameter predictions
 
 - Input:   
 ``` 
 python shape_shifter.py --file any_morphology_file.p --type condense --f 100 --rad_diff 0 
 ```
 - Ouput:
 - morphology_file_condensed.p

By default, shape_shifter will change 3-pt soma to 1-pt soma in morphology, unless greater than 3 soma nodes are present. shape_shifter will only alter dendritic compartments in morphology and maintain original size, shape, length, and diameter of soma nodes (unless 3-pt soma).


CVAPP - Description
============

If wanting to visualize morphology or change soma compartments manually, cvapp is provided in this repository. We strongly recommend that the 1st three soma lines in the cvapp output file be combined into a single coma compartment by hand prior to running shape_shifter, because cvapp output of neuromorpho files typically has 3 soma compartments, with the first, parent compartment (which cannot be eliminated by shape_shifter) having zero size. In addition, you may need to remove blank lines from the .p file to avoid error messages.

**CVAPP usage**

in Unix:
  ```
  java -classpath cvapp.jar: $CLASSPATH cvapp
  ```
  
on Windows:
  ```
  java -classpath cvapp.jar; $CLASSPATH cvapp
  ```
1. click on "file", then "open" in the dropdown, and then navigate to your swc file
2. click on "file", then "save as Genesis - flat", create filename
3. click on "file", then "quit" to exit cvapp
4. edit the output .p file as follows:
- add *cartesian, *asymmetrical, and all the resistance, voltage and capacitance values
- edit the lines specifying the soma. If the 1st compartment has 0,0,0 as coordinates, this will create a compartment of length 0 and volume 0 (not good. The next two compartments are likely specifying the left and right edges (or top and bottom edges) of the soma.  Change these three lines by
  - changing the 1st soma comp x, y, z to be equal the sum of the x, y, z values of the 2nd and 3d soma comps
  - delete the 2nd and 3d soma comps
5. run shape_shifter
