import re
from pathlib import Path

# target figure size
# for scaling, as figure was created for 16:10
width = 14
height = 7
output_file = "world"
reading_file = open(str(Path(__file__).parent.parent) + "/simulation/results/world_vis.tex", "r")

dim_x = None
dim_y = None

# POSTPROCESSING
odd = True
new_file_content = ""
for line in reading_file:
    stripped_line = line.strip()

    new_line = stripped_line

    # logic for replacing goes here
    if(stripped_line.__contains__("xmin")):
        numbers = re.findall('-?\d+\.?\d*', stripped_line)
        dim_x = int(numbers[1]) - int(numbers[0])

    elif(stripped_line.__contains__("ymin")):
        numbers = re.findall('-?\d+\.?\d*', stripped_line)
        dim_y = int(numbers[1]) - int(numbers[0])
        
    elif(stripped_line.__contains__("ellipse")):
        split_line = stripped_line.split("ellipse ")
        numbers = re.findall('-?\d+\.?\d*', split_line[-1])
        el_x = float(numbers[0])
        el_y = dim_y/dim_x * width/height * el_x
        new_line = split_line[0] + ( "ellipse (%.2f and %.2f);" % (el_x, el_y) )

    elif(stripped_line.__contains__("<->")):
        if(odd):
            new_line = stripped_line.replace("<->", "stealth-stealth").replace("--", "to [out=-20,in=-160]")
        else:
            new_line = stripped_line.replace("<->", "stealth-stealth").replace("--", "to [out=20,in=160]")

        odd = not odd

    elif(stripped_line.__contains__("_")):
        new_line = stripped_line.replace("_", "")

    new_file_content += new_line +"\n"

reading_file.close()

writing_file = open(str(Path(__file__).parent) + "/figures/%s.tex" % output_file, "w")
writing_file.write(new_file_content)
writing_file.close()