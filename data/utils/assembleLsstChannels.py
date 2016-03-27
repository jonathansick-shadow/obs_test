#!/usr/bin/env python2
from __future__ import absolute_import, division, print_function
#
# LSST Data Management System
# Copyright 2014 LSST Corporation.
#
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
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
# You should have received a copy of the LSST License Statement and
# the GNU General Public License along with this program.  If not,
# see <http://www.lsstcorp.org/LegalNotices/>.
#
"""Assemble a set of LSSTSim channel images into one obs_test image
"""
import argparse
import glob
import os.path
import re

import numpy

import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage

OutFileName = "image.fits"
SizeY = 1000  # number of pixels per amplifier in X direction (Y uses all pixels)

KeysToCopy = (
    "EPOCH",
    "OBSID",
    "TAI",
    "MJD-OBS",
    "EXPTIME",
    "DARKTIME",
    "AIRMASS",
)


def openChannelImage(dirPath, x, y):
    """Open an LSSTSim channel image
    """
    globStr = os.path.join(dirPath, "imsim_*_R22_S00_C%d%d*" % (y, x))
    inImagePathList = glob.glob(globStr)
    if len(inImagePathList) != 1:
        raise RuntimeError("Found %s instead of 1 file" % (inImagePathList,))
    inImagePath = inImagePathList[0]
    inImageFileName = os.path.basename(inImagePath)
    # calib images (which are float) have names such as imsim_2_R22_S00_C00.fits
    # raw images (which are unsigned int) have names such as imsim_890104911_R22_S00_C00_E000....
    if re.match(r"imsim_\d\d\d\d\d", inImageFileName):
        print("loading %s as raw unsigned integer data" % (inImageFileName,))
        exposureClass = afwImage.ExposureU
    else:
        print("loading %s as float data" % (inImageFileName,))
        exposureClass = afwImage.ExposureF
    return exposureClass(inImagePath)


def assembleImage(dirPath):
    """Make one image by combining half of amplifiers C00, C01, C10, C11 of lsstSim data
    """
    inExposure = openChannelImage(dirPath, 0, 0)
    fullInDim = inExposure.getDimensions()
    yStart = fullInDim[1] - SizeY
    if yStart < 0:
        raise RuntimeError("channel image unexpectedly small")
    subDim = afwGeom.Extent2I(fullInDim[0], SizeY)  # dimensions of the portion of a channel that we use
    inSubBBox = afwGeom.Box2I(afwGeom.Point2I(0, yStart), subDim)
    outBBox = afwGeom.Box2I(afwGeom.Point2I(0, 0), subDim * 2)
    outExposure = inExposure.Factory(outBBox)

    # copy WCS, filter and other metadata
    if inExposure.hasWcs():
        outExposure.setWcs(inExposure.getWcs())
    outExposure.setFilter(inExposure.getFilter())
    inMetadata = inExposure.getMetadata()
    outMetadata = outExposure.getMetadata()
    for key in KeysToCopy:
        if inMetadata.exists(key):
            outMetadata.set(key, inMetadata.get(key))
    outExposure.setMetadata(outMetadata)
    outMI = outExposure.getMaskedImage()

    for x in (0, 1):
        for y in (0, 1):
            inExposure = openChannelImage(dirPath, x, y)
            inView = inExposure.Factory(inExposure, inSubBBox)
            inMIView = inView.getMaskedImage()

            # flip image about x axis for the y = 1 channels
            if y == 1:
                inArrList = inMIView.getArrays()
                for arr in inArrList:
                    if numpy.any(arr != 0):
                        arr[:, :] = numpy.flipud(arr)

            xStart = x * subDim[0]
            yStart = y * subDim[1]
            outSubBBox = afwGeom.Box2I(afwGeom.Point2I(xStart, yStart), subDim)
            outMIView = outMI.Factory(outMI, outSubBBox)
            outMIView[:] = inMIView

    outExposure.writeFits(OutFileName)
    print("wrote assembled data as %r" % (OutFileName,))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Assemble a set of LSSTSim channel images into one obs_test image.

Output is written to the current directory as file %r, which is OVERWRITTEN if it exists.
""" % (OutFileName,),
    )
    parser.add_argument("dir", default=".", nargs="?", help="directory containing LSSTSim channel images " +
                        "(at least for channels 0,0, 0,1, 1,0 and 1,1); defaults to the current working directory.")
    args = parser.parse_args()

    assembleImage(args.dir)
