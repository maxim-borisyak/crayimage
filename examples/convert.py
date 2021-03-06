#!/usr/bin/env python

import sys, os
from glob import glob
import array
import ROOT as r
import numpy as np

if __name__ == "__main__":
    input_dir = sys.argv[1]

    samples = {}
    for idx,f in enumerate(glob(os.path.join(input_dir, "*.dat"))):
        particle_name = os.path.basename(f)[:-len('.dat')]

        datfile = np.loadtxt(f)

        # make a file to save the histogram to
        outfile_name = os.path.join(os.path.dirname(f), '%s.root'%particle_name)
        print "Saving to", outfile_name
        f_out = r.TFile(outfile_name, 'RECREATE')
        # ROOT is picky and wants python array.array for TH1F constructor
        binsx = array.array('d', datfile[:,0])
        h = r.TH1F("particleEnergy", particle_name, len(binsx)-1, binsx)
        for xbin,rate in datfile:
            h.Fill(xbin,rate)

        # save the reference histogram
        h.Write()
        f_out.Close()
