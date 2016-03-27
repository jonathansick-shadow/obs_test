#!/usr/bin/env python2
from __future__ import absolute_import, division, print_function
#
# LSST Data Management System
# Copyright 2008, 2009, 2010, 2011, 2012, 2013 LSST Corporation.
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
import glob
import os
import re
import shutil
import sqlite3
import sys

import lsst.daf.base as dafBase
import lsst.afw.image as afwImage
import lsst.skypix as skypix

DefaultOutputRegistry = "registry.sqlite3"


def process(dirList, inputRegistry=None, outputRegistry="registry.sqlite3"):
    print("process(dirList=%s)" % (dirList,))
    if os.path.exists(outputRegistry):
        sys.stderr.write("Output registry %r exists; will not overwrite.\n" % (outputRegistry,))
        sys.exit(1)
    if inputRegistry is not None:
        if not os.path.exists(inputRegistry):
            sys.stderr.write("Input registry %r does not exist.\n" % (inputRegistry,))
            sys.exit(1)
        shutil.copy(inputRegistry, outputRegistry)

    conn = sqlite3.connect(outputRegistry)

    done = {}
    if inputRegistry is None:
        # Create tables in new output registry.
        cmd = """CREATE TABLE raw (id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit INT, filter TEXT, taiObs TEXT, expTime DOUBLE)"""
        conn.execute(cmd)
        cmd = "CREATE TABLE raw_skyTile (id INTEGER, skyTile INTEGER)"
        conn.execute(cmd)
        conn.execute("""CREATE TABLE raw_visit (visit INT, filter TEXT,
            taiObs TEXT, expTime DOUBLE, UNIQUE(visit))""")
        conn.commit()
    else:
        cmd = """SELECT visit || '_f' || filter || FROM raw"""
        for row in conn.execute(cmd):
            done[row[0]] = True

    qsp = skypix.createQuadSpherePixelization()

    try:
        for dirPath in dirList:
            rawDir = os.path.join(dirPath, "raw")
            if not os.path.exists(rawDir):
                sys.stderr.write("Could not find raw data dir %r\n" % (rawDir,))
            processRawDir(rawDir, conn, done, qsp)
    finally:
        print("Cleaning up...")
        conn.execute("DELETE FROM raw_visit")
        conn.commit()
        conn.execute("""INSERT INTO raw_visit
                SELECT DISTINCT visit, filter, taiObs, expTime FROM raw""")
        conn.commit()
        conn.execute("""CREATE UNIQUE INDEX uq_raw ON raw
                (visit)""")
        conn.execute("CREATE INDEX ix_skyTile_id ON raw_skyTile (id)")
        conn.execute("CREATE INDEX ix_skyTile_tile ON raw_skyTile (skyTile)")
        conn.close()
    print("wrote registry file %r" % (outputRegistry,))


def processRawDir(rawDir, conn, done, qsp):
    print(rawDir, "... started")
    nProcessed = 0
    nSkipped = 0
    nUnrecognized = 0
    for fitsPath in glob.glob(os.path.join(rawDir, "*.fits*")):
        m = re.search(r'raw_v(\d*)_f(.+)\.fits', fitsPath)
        if not m:
            sys.stderr.write("Warning: Unrecognized file: %r\n" % (fitsPath,))
            nUnrecognized += 1
            continue

        visit, filterName = m.groups()
        key = "%s_f%s" % (visit, filterName)
        if done.has_key(key):
            nSkipped += 1
            continue

        md = afwImage.readMetadata(fitsPath)
        expTime = md.get("EXPTIME")
        mjdObs = md.get("MJD-OBS")
        taiObs = dafBase.DateTime(mjdObs, dafBase.DateTime.MJD,
                                  dafBase.DateTime.TAI).toString()[:-1]
        conn.execute("""INSERT INTO raw VALUES
            (NULL, ?, ?, ?, ?)""",
                     (visit, filterName, taiObs, expTime))

        for row in conn.execute("SELECT last_insert_rowid()"):
            id = row[0]
            break

        wcs = afwImage.makeWcs(md)
        poly = skypix.imageToPolygon(wcs,
                                     md.get("NAXIS1"), md.get("NAXIS2"),
                                     padRad=0.000075)  # about 15 arcsec
        pix = qsp.intersect(poly)
        for skyTileId in pix:
            conn.execute("INSERT INTO raw_skyTile VALUES(?, ?)",
                         (id, skyTileId))

        conn.commit()

        nProcessed += 1

    print("%s... %d processed, %d skipped, %d unrecognized" %
          (rawDir, nProcessed, nSkipped, nUnrecognized))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Make a registry file for a data repository")
    parser.add_argument("dir", nargs="+", help="one or more directories of data, e.g. data/input")
    parser.add_argument("-i", "--input", help="input registry")
    parser.add_argument("-o", "--output", default=DefaultOutputRegistry,
                        help="output registry (default=%s)" % (DefaultOutputRegistry,))
    args = parser.parse_args()
    process(args.dir, args.input, args.output)
