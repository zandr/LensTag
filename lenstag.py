#!/usr/bin/python

# lenstag.py
# Copyright 2010 Aleksandr Milewski <zandr@milewski.org>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
                                    

import os
from collections import defaultdict
import subprocess
import optparse
import ConfigParser

usage = "usage: %prog [options] lens.ini imagefile1 [imagefile2...]"

parser=optparse.OptionParser(usage=usage)
parser.add_option("-g", "--geotag", type="string", dest="tracklog", 
                  help="GeoTag using a track log file (i.e. GPX)",
                 )
parser.add_option("-w", "--wide-open", action="store_true", default=False,
                  dest="wide_open",
                  help="Set Fnumber tag assuming the lens was wide open",
                 )
parser.add_option("-e", "--exif-tool", type="string", dest="exiftool",
                  default="exiftool", 
                  help="Path to exiftool binary"
                 )
parser.add_option("-v", "--verbose", action="store_true", default=False,
                  help="Be verbose, passes -v to exiftool"
                 )

(options, args) = parser.parse_args()

print options.exiftool

def usage():
    parser.print_help()
    exit(2)

if len(args) < 2:
    print "You must specify a lens file and at least one image file."
    usage()

if "ini" not in args[0]:
    print args[0]
    print "The first argument must be a lens .ini file."
    usage()

cp = ConfigParser.SafeConfigParser()
cp.read(args.pop(0))

lensdata = dict(cp.items("Lens"))



# Try to guess lens type if it's missing
if 'type' not in lensdata:
    if 'fl' in lensdata: 
        lensdata['type'] = "Fixed"
    elif (lensdata['fl_short'] == lensdata['fl_long']):
        lensdata['type'] = "Fixed"
        lensdata['fl'] = lensdata['fl_short']
    else:
        lensdata['type'] = "Zoom"

# Populate min/max fields based on type, abort if type is unknown
if lensdata['type'] == "Fixed":
    lensdata['fl_short'] = lensdata['fl']
    lensdata['fl_long'] = lensdata['fl']
    lensdata['aperture_max_short'] = lensdata['aperture_max']
    lensdata['aperture_max_long'] = lensdata['aperture_max']
elif lensdata['type'] == "Zoom":
    lensdata['aperture_max'] = lensdata['aperture_max_short']
else:
    print 'Lens type must be "Fixed" or "Zoom"'
    usage()

# Set no_iris flag if we should populate FNumber
if 'no_iris' not in lensdata:
    if (lensdata['aperture_min'] == lensdata['aperture_max']):
        lensdata['no_iris'] = True
    else:
        lensdata['no_iris'] = False

# Conversely, fill in missing aperture_min if no_iris
if 'aperture_min' not in lensdata and lensdata['no_iris']:
    lensdata['aperture_min'] = lensdata['aperture_max']
    
def set_tags(lens, tags, extension):

    tags['LensModel']=lens['description']

    if (extension == ".ORF"):
        tags['MaxApertureValue'] = lens['aperture_max_short']
        tags['MaxApertureAtMinFocal'] = lens['aperture_max_short']
        tags['MaxApertureAtMaxFocal'] = lens['aperture_max_long']
        tags['MinFocalLength'] = lens['fl_short']
        tags['MaxFocalLength'] = lens['fl_long']
    else:
        tags['MaxAperture'] = lens['aperture_max_short']
        tags['MinAperture'] = lens['aperture_min']
        tags['LongFocal'] = lens['fl_long']
        tags['ShortFocal'] = lens['fl_short']

    if (extension == ".CR2"):
        tags['FocalType'] = lens['type']

    if lens['no_iris'] or options.wide_open:
        tags['FNumber'] = lens['aperture_max']
        if (extension == ".CR2"):
            tags['ApertureValue'] = lens['aperture_max']

    if lens['type'] == "Fixed":
        tags['FocalLength'] = lens['fl']

filetypes = defaultdict(list)

for file in args:
    basename, ext = os.path.splitext(file)
    ext = ext.upper()
    filetypes[ext].append(file)

for extension, files in filetypes.iteritems():
    exiftags = dict()

# GeoTag
    if options.tracklog:
        exiftags['geotag'] = options.tracklog

    set_tags(lensdata, exiftags, extension)
    arglist = list()
    for option, argument in exiftags.iteritems():
        arglist.append("-" + option + "=" + argument)
    if options.verbose: arglist.insert(0, "-v")
    arglist.insert(0, options.exiftool)
    arglist.extend(files)
    print "Calling exiftool on " + str(len(files)) + " " + extension + " file(s)..."
    result = subprocess.call(arglist)
