# ######################################################################
# Copyright (c) 2014, Brookhaven Science Associates, Brookhaven        #
# National Laboratory. All rights reserved.                            #
#                                                                      #
# Redistribution and use in source and binary forms, with or without   #
# modification, are permitted provided that the following conditions   #
# are met:                                                             #
#                                                                      #
# * Redistributions of source code must retain the above copyright     #
#   notice, this list of conditions and the following disclaimer.      #
#                                                                      #
# * Redistributions in binary form must reproduce the above copyright  #
#   notice this list of conditions and the following disclaimer in     #
#   the documentation and/or other materials provided with the         #
#   distribution.                                                      #
#                                                                      #
# * Neither the name of the Brookhaven Science Associates, Brookhaven  #
#   National Laboratory nor the names of its contributors may be used  #
#   to endorse or promote products derived from this software without  #
#   specific prior written permission.                                 #
#                                                                      #
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS  #
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT    #
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS    #
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE       #
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,           #
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES   #
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR   #
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)   #
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,  #
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OTHERWISE) ARISING   #
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE   #
# POSSIBILITY OF SUCH DAMAGE.                                          #
########################################################################
"""
This module is for Differential Phase Contrast (DPC) imaging based on
Fourier shift fitting
"""


from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import logging
import numpy as np
from scipy.optimize import minimize


def image_reduction(im, roi=None, bad_pixels=None):
    """
    Sum the image data along one dimension.
    
    Parameters
    ----------
    im : 2-D numpy array
        Input image.

    roi : 4-element 1-D numpy darray, optional (default None)
        [r, c, row, col], r and c are row and column number of the upper left 
        corner of the ROI. row and col are number of rows and columns from r 
        and c.

    bad_pixels : list, optional (default None)
        List of (row, column) tuples marking bad pixels.
        [(1, 5), (2, 6)] --> 2 bad pixels --> (1, 5) and (2, 6)

    Returns
    -------
    xline : 1-D numpy array
        The sum of the image data along x direction.

    yline : 1-D numpy array
        The sum of the image data along y direction.

    """

    im = im.copy()
    
    if bad_pixels is not None:
        for row, column in bad_pixels:
            im[row, column] = 0

    if roi is not None:
        r, c, row, col = roi
        im = im[r : r + row, c : c + col]

    xline = np.sum(im, axis=0)
    yline = np.sum(im, axis=1)

    return xline, yline


def _rss_factory(length):
    """
    A factory function for returning a residue function for use in dpc fitting.
    The main reason to do this is to generate a closure over beta so that
    linspace is only called once.

    Parameters
    ----------
    length : int
        The length of the data vector that the returned function can deal with.

    Returns
    -------
    function
        A function with signature f(v, xdata, ydata) which is suitable for use
        as a cost function for use with scipy.optimize.

    """

    beta = 1j * (np.linspace(-(length-1)//2, (length-1)//2, length))

    def _rss(v, arg1, arg2):
        """
        Internal function used by fit()
        Cost function to be minimized in nonlinear fitting

        Parameters
        ----------
        v : list
            Fit parameters.
            v[0], amplitude of the sample transmission function at one scanning 
            point;
            v[1], the phase gradient (along x or y direction) of the sample 
            transmission function.

        arg1 : 1-D numpy array
            Extra argument passed to the objective function. In DPC, it's the 
            sum of the reference image data along x or y direction.

        arg2 : 1-D numpy array
            Extra argument passed to the objective function. In DPC, it's the 
            sum of one captured diffraction pattern along x or y direction.

        Returns
        --------
        float
            Residue value.

        """

        diff = arg2 - arg1 * v[0] * np.exp(v[1] * beta)
        
        return np.sum((diff * np.conj(diff)).real)

    return _rss


def dpc_fit(rss, arg1, arg2, start_point, solver='Nelder-Mead', tol=1e-6, 
            max_iters=2000):
    """
    Nonlinear fitting for 2 points.

    Parameters
    ----------
    rss : callable
        Objective function to be minimized in DPC fitting.

    arg1 : 1-D numpy array
        Extra argument passed to the objective function. In DPC, it's the sum 
        of the reference image data along x or y direction.

    arg2 : 1-D numpy array
        Extra argument passed to the objective function. In DPC, it's the sum 
        of one captured diffraction pattern along x or y direction.

    start_point : 2-element list
        start_point[0], start-searching value for the amplitude of the sample 
        transmission function at one scanning point.
        start_point[1], start-searching value for the phase gradient (along x 
        or y direction) of the sample transmission function at one scanning 
        point.

    solver : string, optional (default 'Nelder-Mead')
        Type of solver, one of the following:
        * 'Nelder-Mead'
        * 'Powell'
        * 'CG'
        * 'BFGS'
        * 'Anneal'
        * 'L-BFGS-B'
        * 'TNC'
        * 'COBYLA'
        * 'SLSQP'
    
    tol : float, optional (default 1e-6)
        Termination criteria of nonlinear fitting.
    
    max_iters : integer, optional (default 2000)
        Maximum iterations of nonlinear fitting.
    
    Returns
    -------
    tuple 
        Fitting result: intensity attenuation and phase gradient.
    
    """
    
    return minimize(rss, start_point, args=(arg1, arg2), method=solver, 
                    tol=tol, options=dict(maxiter=max_iters)).x

# attributes
dpc_fit.solver = ['Nelder-Mead',
                  'Powell',
                  'CG',
                  'BFGS',
                  'Anneal',
                  'L-BFGS-B',
                  'TNC',
                  'COBYLA',
                  'SLSQP']


def recon(gx, gy, dx, dy, padding=0, w=0.5):
    """
    Reconstruct the final phase image.

    Parameters
    ----------
    gx : 2-D numpy array
        Phase gradient along x direction.

    gy : 2-D numpy array
        Phase gradient along y direction.

    dx : float
        Scanning step size in x direction (in micro-meter).
    
    dy : float
        Scanning step size in y direction (in micro-meter).
    
    padding : integer, optional (default 0)
        Pad a N-by-M array to be a (N*(2*padding+1))-by-(M*(2*padding+1)) array 
        with the image in the middle with a (N*padding, M*padding) thick edge 
        of zeros.
        padding = 0 --> v (the original image, size = (N, M))
                        0 0 0
        padding = 1 --> 0 v 0 (the padded image, size = (3 * N, 3 * M))
                        0 0 0
    
    w : float, valid in [0, 1], optional (default 0.5)
        Weighting parameter for the phase gradient along x and y direction when 
        constructing the final phase image. Default value = 0.5, which means 
        that gx and gy equally contribute to the final phase image.
    
    Returns
    -------
    phi : 2-D numpy array
        Final phase image.
    
    """
    
    if w < 0 or w > 1:
        raise ValueError('w should be within the range of [0, 1]!')
        
    pad = 2 * padding + 1
    gx = np.asarray(gx)
    rows, cols = gx.shape
    pad_row = rows * pad
    pad_col = cols * pad
        
    gx_padding = np.zeros((pad_row, pad_col), dtype='d')
    gy_padding = np.zeros((pad_row, pad_col), dtype='d')
    
    roi_slice = (slice(padding * rows, (padding + 1) * rows),
                 slice(padding * cols, (padding + 1) * cols))
    gx_padding[roi_slice] = gx
    gy_padding[roi_slice] = gy

    tx = np.fft.fftshift(np.fft.fft2(gx_padding))
    ty = np.fft.fftshift(np.fft.fft2(gy_padding))

    mid_col = pad_col // 2 + 1
    mid_row = pad_row // 2 + 1
    ax = (2 * np.pi * np.arange(1 - mid_col, pad_col - mid_col + 1) / 
         (pad_col * dx))
    ay = (2 * np.pi * np.arange(1 - mid_row, pad_row - mid_row + 1) / 
         (pad_row * dy))

    kappax, kappay = np.meshgrid(ax, ay)
    div_v = kappax ** 2 * (1 - w) + kappay ** 2 * w

    c = -1j * (kappax * tx * (1 - w) + kappay * ty * w) / div_v
    c = np.fft.ifftshift(np.where(div_v==0, 0, c))

    phi = np.fft.ifft2(c)[roi_slice].real

    return phi


def dpc_runner(ref, image_sequence, start_point, pixel_size, focus_to_det, 
               rows, cols, dx, dy, energy, padding=0, w=0.5, 
               solver='Nelder-Mead', roi=None, bad_pixels=None, invert=True,
               scale=True):
    """
    Controller function to run the whole Differential Phase Contrast (DPC) 
    imaging calculation.
    
    Parameters
    ----------
    ref : 2-D numpy array
        The reference image for a DPC calculation.

    image_sequence : iterable of 2D arrays
        Return diffraction patterns (2D Numpy arrays) when iterated over.
        
    start_point : 2-element list
        start_point[0], start-searching value for the amplitude of the sample 
        transmission function at one scanning point.
        start_point[1], start-searching value for the phase gradient (along x 
        or y direction) of the sample transmission function at one scanning 
        point.

    pixel_size : 2-element tuple
        Physical pixel (a rectangle) size of the detector in um.

    focus_to_det : float
        Focus to detector distance in um.

    rows : integer
        Number of scanned rows.

    cols : integer
        Number of scanned columns.

    dx : float
        Scanning step size in x direction (in micro-meter).

    dy : float
        Scanning step size in y direction (in micro-meter).

    energy : float
        Energy of the scanning x-ray in keV.
    
    padding : integer, optional (default 0)
        Pad a N-by-M array to be a (N*(2*padding+1))-by-(M*(2*padding+1)) array 
        with the image in the middle with a (N*padding, M*padding) thick edge 
        of zeros.
        padding = 0 --> v (the original image, size = (N, M))
                        0 0 0
        padding = 1 --> 0 v 0 (the padded image, size = (3 * N, 3 * M))
                        0 0 0

    w : float, valid in [0, 1], optional (default 0.5)
        Weighting parameter for the phase gradient along x and y direction when 
        constructing the final phase image. Default value = 0.5, which means 
        that gx and gy equally contribute to the final phase image.
        
    solver : string, optional (default 'Nelder-Mead')
        Type of solver, one of the following:
        * 'Nelder-Mead'
        * 'Powell'
        * 'CG'
        * 'BFGS'
        * 'Anneal'
        * 'L-BFGS-B'
        * 'TNC'
        * 'COBYLA'
        * 'SLSQP'

    roi : 4-element 1-D numpy darray, optional (default None)
        [r, c, row, col], r and c are row and column number of the upper left 
        corner of the ROI. row and col are number of rows and columns from r 
        and c.
    
    bad_pixels : list, optional (default None)
        List of (row, column) tuples marking bad pixels.
        [(1, 5), (2, 6)] --> 2 bad pixels --> (1, 5) and (2, 6)
    
    invert : bool, optional (default True)
        If Ture (default), invert the phase gradient along x direction before 
        reconstructing the final phase image.

    scale : bool, optional (default True)
        If True, scale gx and gy according to the experiment set up.
        If False, ignore pixel_size, focus_to_det, energy.
    
    Returns
    -------
    phi : 2-D numpy array
        The final reconstructed phase image.
    
    a : 2-D numpy array
        Amplitude of the sample transmission function.
    
    References
    ----------
    [1] Yan, H. et al. Quantitative x-ray phase imaging at the nanoscale by 
    multilayer Laue lenses. Sci. Rep. 3, 1307; DOI:10.1038/srep01307 (2013).
    
    """
    
    if w < 0 or w > 1:
        raise ValueError('w should be within the range of [0, 1]!')

    # Initialize ax, ay, gx, gy and phi
    ax = np.zeros((rows, cols), dtype='d')
    ay = np.zeros((rows, cols), dtype='d')
    gx = np.zeros((rows, cols), dtype='d')
    gy = np.zeros((rows, cols), dtype='d')
    phi = np.zeros((rows, cols), dtype='d')

    # Dimension reduction along x and y direction
    refx, refy = image_reduction(ref, roi, bad_pixels)

    # 1-D IFFT
    ref_fx = np.fft.fftshift(np.fft.ifft(refx))
    ref_fy = np.fft.fftshift(np.fft.ifft(refy))

    ffx = _rss_factory(len(ref_fx))
    ffy = _rss_factory(len(ref_fy))

    # Same calculation on each diffraction pattern
    for index, im in enumerate(image_sequence):
        i, j = np.unravel_index(index, (rows, cols))

        # Dimension reduction along x and y direction
        imx, imy = image_reduction(im, roi, bad_pixels)

        # 1-D IFFT
        fx = np.fft.fftshift(np.fft.ifft(imx))
        fy = np.fft.fftshift(np.fft.ifft(imy))

        # Nonlinear fitting
        _ax, _gx = dpc_fit(ffx, ref_fx, fx, start_point, solver)
        _ay, _gy = dpc_fit(ffy, ref_fy, fy, start_point, solver)

        # Store one-point intermediate results
        gx[i, j] = _gx
        gy[i, j] = _gy
        ax[i, j] = _ax
        ay[i, j] = _ay

    if scale:
        if pixel_size[0] != pixel_size[1]:
            raise ValueError('In DPC, detector pixels are squares!')
            
        lambda_ = 12.4e-4 / energy
        gx *= len(ref_fx) * pixel_size[0] / (lambda_ * focus_to_det)
        gy *= len(ref_fy) * pixel_size[0] / (lambda_ * focus_to_det)
        
    if invert:
        gx = -gx

    # Reconstruct the final phase image
    phi = recon(gx, gy, dx, dy, padding, w)

    return phi, (ax + ay) / 2

# attributes
dpc_runner.solver = ['Nelder-Mead',
                     'Powell',
                     'CG',
                     'BFGS',
                     'Anneal',
                     'L-BFGS-B',
                     'TNC',
                     'COBYLA',
                     'SLSQP']
