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
import argparse

import pyfits

import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.meas.algorithms as measAlg
from lsst.ip.isr import maskPixelsFromDefectList

MaskFileName = "defectsMask.fits"


def getBBoxList(path, detectorName):
    """Get a list of defects as a list of bounding boxes
    """
    with pyfits.open(path) as hduList:
        for hdu in hduList[1:]:
            if hdu.header["name"] != detectorName:
                print("skipping hdu with name=%r" % (hdu.header["name"],))
                continue

            bboxList = []
            for data in hdu.data:
                bbox = afwGeom.Box2I(
                    afwGeom.Point2I(int(data['x0']), int(data['y0'])),
                    afwGeom.Extent2I(int(data['width']), int(data['height'])),
                )
                bboxList.append(bbox)
            return bboxList
        raise RuntimeError("Data not found for detector %r" % (detectorName,))


def writeDefectsFile(bboxList, path):
    maskBBox = afwGeom.Box2I(afwGeom.Point2I(0, 0), afwGeom.Extent2I(1, 1))
    for box in bboxList:
        maskBBox.include(box)

    defectsMaskedImage = afwImage.MaskedImageF(maskBBox)
    defectList = measAlg.DefectListT()
    for bbox in bboxList:
        nd = measAlg.Defect(bbox)
        defectList.append(nd)
    maskPixelsFromDefectList(defectsMaskedImage, defectList, maskName='BAD')
    defectsMaskedImage.getMask().writeFits(MaskFileName)
    print("wrote %s with bbox %s" % (MaskFileName, maskBBox,))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Make a mask image from a fits table of defects (for any camera).
To use this command you must setup meas_algorithms, ip_isr and pyfits.

WARNING: the output file may be smaller than the detector data region, because the upper and right
edges extend only as far as there are defects.

Output is written to the current directory as file %r, which is OVERWRITTEN if it exists.
""" % (MaskFileName,)
    )
    parser.add_argument("defects", help="path to defects file")
    parser.add_argument("detector", help="detector name")
    args = parser.parse_args()

    bboxList = getBBoxList(args.defects, args.detector)
    print("found %d defects" % (len(bboxList),))
    writeDefectsFile(bboxList, args.detector)
