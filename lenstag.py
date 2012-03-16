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
if 't' not in lensdata:
    if 'fl' in lensdata: 
        lensdata['t'] = "Fixed"
    elif (lensdata['fls'] == lensdata['fll']):
        lensdata['t'] = "Fixed"
        lensdata['fl'] = lensdata['fls']
    else:
        lensdata['t'] = "Zoom"

# Populate min/max fields based on type, abort if type is unknown
if lensdata['t'] == "Fixed":
    lensdata['fls'] = lensdata['fl']
    lensdata['fll'] = lensdata['fl']
    lensdata['amxs'] = lensdata['amx']
    lensdata['amxl'] = lensdata['amx']
elif lensdata['t'] == "Zoom":
    lensdata['amx'] = lensdata['amxs']
else:
    print 'Lens type must be "Fixed" or "Zoom"'
    usage()

# Set no_iris flag if we should populate FNumber
if 'ni' not in lensdata:
    if (lensdata['amn'] == lensdata['amx']):
        lensdata['ni'] = True
    else:
        lensdata['ni'] = False

# Conversely, fill in missing amn if no_iris
if 'amn' not in lensdata and lensdata['ni']:
    lensdata['amn'] = lensdata['amx']
    
def set_tags(lens, tags, extension):

    tags['LensModel']=lens['d']

    if (extension == ".ORF"):
        tags['MaxApertureValue'] = lens['amxs']
        tags['MaxApertureAtMinFocal'] = lens['amxs']
        tags['MaxApertureAtMaxFocal'] = lens['amxl']
        tags['MinFocalLength'] = lens['fls']
        tags['MaxFocalLength'] = lens['fll']
    else:
        tags['MaxAperture'] = lens['amxs']
        tags['MinAperture'] = lens['amn']
        tags['LongFocal'] = lens['fll']
        tags['ShortFocal'] = lens['fls']

    if (extension == ".CR2"):
        tags['FocalType'] = lens['type']

    if lens['no_iris'] or options.wide_open:
        tags['FNumber'] = lens['amx']
        if (extension == ".CR2"):
            tags['ApertureValue'] = lens['amx']

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
