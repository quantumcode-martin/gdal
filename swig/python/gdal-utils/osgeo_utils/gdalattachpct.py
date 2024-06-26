#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ******************************************************************************
#  $Id$
#
#  Project:  GDAL
#  Purpose:  Simple command line program for copying the color table of a
#            raster into another raster.
#  Author:   Frank Warmerdam, warmerda@home.com
#
# ******************************************************************************
#  Copyright (c) 2000, Frank Warmerdam
#  Copyright (c) 2020-2021, Idan Miara <idan@miara.com>
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
# ******************************************************************************

import sys
from typing import Optional

from osgeo import gdal
from osgeo_utils.auxiliary.base import PathLikeOrStr
from osgeo_utils.auxiliary.color_table import ColorTableLike, get_color_table
from osgeo_utils.auxiliary.util import GetOutputDriverFor, open_ds


def Usage(isError=True):
    f = sys.stderr if isError else sys.stdout
    print("Usage: gdalattachpct.py [--help] [--help-general]", file=f)
    print("                        <pctfile> <infile> <outfile>", file=f)
    return 2 if isError else 0


def main(argv=sys.argv):
    pct_filename = None
    src_filename = None
    dst_filename = None
    driver_name = None

    argv = gdal.GeneralCmdLineProcessor(argv)
    if argv is None:
        return 0

    # Parse command line arguments.
    i = 1
    while i < len(argv):
        arg = argv[i]

        if arg == "--help":
            return Usage(isError=False)

        elif arg == "-of" or arg == "-f":
            i = i + 1
            driver_name = argv[i]

        elif pct_filename is None:
            pct_filename = argv[i]

        elif src_filename is None:
            src_filename = argv[i]

        elif dst_filename is None:
            dst_filename = argv[i]

        else:
            return Usage()

        i = i + 1

    if len(argv) < 3:
        return Usage()

    _ds, err = doit(
        src_filename=src_filename,
        pct_filename=pct_filename,
        dst_filename=dst_filename,
        driver_name=driver_name,
    )
    return err


def doit(
    src_filename,
    pct_filename: Optional[ColorTableLike],
    dst_filename: Optional[PathLikeOrStr] = None,
    driver_name: Optional[str] = None,
):

    # =============================================================================
    # Get the PCT.
    # =============================================================================

    ct = get_color_table(pct_filename)
    if pct_filename is not None and ct is None:
        print("No color table on file ", pct_filename)
        return None, 1

    # Figure out destination driver
    if not driver_name:
        driver_name = GetOutputDriverFor(dst_filename)

    dst_driver = gdal.GetDriverByName(driver_name)
    if dst_driver is None:
        print(f'"{driver_name}" driver not registered.')
        return None, 1

    src_ds = open_ds(src_filename)
    if src_ds is None:
        print(f"Cannot open {src_filename}")
        return None, 1

    if driver_name.upper() == "VRT":
        # For VRT, create the VRT first from the source dataset, so it
        # correctly refers to it
        out_ds = dst_driver.CreateCopy(dst_filename or "", src_ds)
        if out_ds is None:
            print(f"Cannot create {dst_filename}")
            return None, 1

        # And now assign the color table to the VRT
        out_ds.GetRasterBand(1).SetRasterColorTable(ct)
        out_ds.GetRasterBand(1).SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    else:
        # Create a MEM clone of the source file.
        mem_ds = gdal.GetDriverByName("MEM").CreateCopy("mem", src_ds)

        # Assign the color table in memory.
        mem_ds.GetRasterBand(1).SetRasterColorTable(ct)
        mem_ds.GetRasterBand(1).SetRasterColorInterpretation(gdal.GCI_PaletteIndex)

        # Write the dataset to the output file.
        if driver_name.upper() == "MEM":
            out_ds = mem_ds
        else:
            out_ds = dst_driver.CreateCopy(dst_filename or "", mem_ds)

        mem_ds = None

    src_ds = None

    return out_ds, 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
