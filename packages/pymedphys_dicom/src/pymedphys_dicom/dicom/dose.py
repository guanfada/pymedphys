# Copyright (C) 2016-2019 Matthew Jennings and Simon Biggs

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version (the "AGPL-3.0+").

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License and the additional terms for more
# details.

# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# ADDITIONAL TERMS are also included as allowed by Section 7 of the GNU
# Affero General Public License. These additional terms are Sections 1, 5,
# 6, 7, 8, and 9 from the Apache License, Version 2.0 (the "Apache-2.0")
# where all references to the definition "License" are instead defined to
# mean the AGPL-3.0+.

# You should have received a copy of the Apache-2.0 along with this
# program. If not, see <http://www.apache.org/licenses/LICENSE-2.0>.
"""A DICOM RT Dose toolbox"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import path

from scipy.interpolate import RegularGridInterpolator

import pydicom
import pydicom.uid

from ..rtplan import (get_surface_entry_point_with_fallback,
                      require_gantries_be_zero)

from .structure import pull_structure
from .coords import xyz_axes_from_dataset

# pylint: disable=C0103


def zyx_and_dose_from_dataset(dataset):
    x, y, z = xyz_axes_from_dataset(dataset)
    coords = (z, y, x)
    dose = dose_from_dataset(dataset)

    return coords, dose


def dose_from_dataset(ds, set_transfer_syntax_uid=True):
    r"""Extract the dose grid from a DICOM RT Dose file.
    """

    if set_transfer_syntax_uid:
        ds.file_meta.TransferSyntaxUID = pydicom.uid.ImplicitVRLittleEndian

    dose = ds.pixel_array * ds.DoseGridScaling

    return dose


def dicom_dose_interpolate(interp_coords, dicom_dose_dataset: pydicom.Dataset):
    """Interpolates across a DICOM dose dataset.

    Parameters
    ----------
    interp_coords : tuple(z, y, x)
        A tuple of coordinates in DICOM order, z axis first, then y, then x
        where x, y, and z are DICOM axes.
    dose : pydicom.Dataset
        An RT DICOM Dose object
    """

    interp_z = np.array(interp_coords[0], copy=False)[:, None, None]
    interp_y = np.array(interp_coords[1], copy=False)[None, :, None]
    interp_x = np.array(interp_coords[2], copy=False)[None, None, :]

    coords, dicom_dose_dataset = zyx_and_dose_from_dataset(dicom_dose_dataset)
    interpolation = RegularGridInterpolator(coords, dicom_dose_dataset)

    try:
        result = interpolation((interp_z, interp_y, interp_x))
    except ValueError:
        print(f"coords: {coords}")
        raise

    return result


def depth_dose(depths, dose_dataset: pydicom.Dataset, plan_dataset: pydicom.Dataset):
    """Interpolates dose for defined depths within a DICOM dose dataset.

    Since the DICOM dose dataset is in CT coordinates the corresponding DICOM
    plan is also required in order to calculate the conversion between CT
    coordinate space and depth.

    Currently only Gantry 0 beams are supported, and depth is assumed to be
    purely in the y axis direction in DICOM coordinates.

    Parameters
    ----------
    depths : numpy.ndarray
        An array of depths to interpolate within the DICOM dose file. 0 is
        defined as the surface of the phantom using either the
        `SurfaceEntryPoint` parameter or a combination of `SourceAxisDistance`,
        `SourceToSurfaceDistance`, and `IsocentrePosition`.
    dose_dataset : pydicom.dataset.Dataset
        The RT DICOM dose dataset to be interpolated
    plan_dataset : pydicom.dataset.Dataset
        The RT DICOM plan used to extract surface parameters and verify gantry
        angle 0 beams are used.
    """
    require_gantries_be_zero(plan_dataset)
    depths = np.array(depths, copy=False)

    surface_entry_point = get_surface_entry_point_with_fallback(plan_dataset)
    depth_adjust = surface_entry_point.y

    y = depths + depth_adjust
    x, z = [surface_entry_point.x], [surface_entry_point.z]

    coords = (z, y, x)

    extracted_dose = np.squeeze(dicom_dose_interpolate(coords, dose_dataset))

    return extracted_dose


def profile(displacements, depth, direction, dose_dataset: pydicom.Dataset,
            plan_dataset: pydicom.Dataset):
    """Interpolates dose for cardinal angle horizontal profiles within a
    DICOM dose dataset.

    Since the DICOM dose dataset is in CT coordinates the corresponding
    DICOM plan is also required in order to calculate the conversion
    between CT coordinate space and depth and horizontal displacement.

    Currently only Gantry 0 beams are supported, and depth is assumed to be
    purely in the y axis direction in DICOM coordinates.

    Parameters
    ----------
    displacements : numpy.ndarray
        An array of displacements to interpolate within the DICOM dose
        file. 0 is defined in the DICOM z or x directions based either
        upon the `SurfaceEntryPoint` or the `IsocenterPosition`
        depending on what is available within the DICOM plan file.
    depth : float
        The depth at which to interpolate within the DICOM dose file. 0 is
        defined as the surface of the phantom using either the
        `SurfaceEntryPoint` parameter or a combination of `SourceAxisDistance`,
        `SourceToSurfaceDistance`, and `IsocentrePosition`.
    direction : str, one of ('inplane', 'inline', 'crossplane', 'crossline')
        Corresponds to the axis upon which to apply the displacements.
         - 'inplane' or 'inline' converts to DICOM z direction
         - 'crossplane' or 'crossline' converts to DICOM x direction
    dose_dataset : pydicom.dataset.Dataset
        The RT DICOM dose dataset to be interpolated
    plan_dataset : pydicom.dataset.Dataset
        The RT DICOM plan used to extract surface and isocentre
        parameters and verify gantry angle 0 beams are used.
    """

    require_gantries_be_zero(plan_dataset)
    displacements = np.array(displacements, copy=False)

    surface_entry_point = get_surface_entry_point_with_fallback(plan_dataset)
    depth_adjust = surface_entry_point.y
    y = [depth + depth_adjust]

    if direction in ('inplane', 'inline'):
        coords = (
            displacements + surface_entry_point.z,
            y, [surface_entry_point.x]
        )
    elif direction in ('crossplane', 'crossline'):
        coords = (
            [surface_entry_point.z], y,
            displacements + surface_entry_point.x
        )
    else:
        raise ValueError(
            "Expected direction to be equal to one of "
            "'inplane', 'inline', 'crossplane', or 'crossline'")

    extracted_dose = np.squeeze(dicom_dose_interpolate(coords, dose_dataset))

    return extracted_dose


def _get_indices(z_list, z_val):
    indices = np.array([item[0] for item in z_list])
    # This will error if more than one contour exists on a given slice
    desired_indices = np.where(indices == z_val)[0]
    # Multiple contour sets per slice not yet implemented

    return desired_indices


def get_dose_grid_structure_mask(structure_name, dcm_struct, dcm_dose):
    x_dose, y_dose, z_dose = xyz_axes_from_dataset(dcm_dose)

    xx_dose, yy_dose = np.meshgrid(x_dose, y_dose)
    points = np.swapaxes(np.vstack([xx_dose.ravel(), yy_dose.ravel()]), 0, 1)

    x_structure, y_structure, z_structure = pull_structure(
        structure_name, dcm_struct)
    structure_z_values = np.array([item[0] for item in z_structure])

    mask = np.zeros((len(y_dose), len(x_dose), len(z_dose)), dtype=bool)

    for z_val in structure_z_values:
        structure_indices = _get_indices(z_structure, z_val)

        for structure_index in structure_indices:
            dose_index = int(np.where(z_dose == z_val)[0])

            assert z_structure[structure_index][0] == z_dose[dose_index]

            structure_polygon = path.Path([
                (x_structure[structure_index][i],
                 y_structure[structure_index][i])
                for i in range(len(x_structure[structure_index]))
            ])
            mask[:, :, dose_index] = mask[:, :, dose_index] | (
                structure_polygon.contains_points(points).reshape(
                    len(y_dose), len(x_dose)))

    return mask


def find_dose_within_structure(structure_name, dcm_struct, dcm_dose):
    dose = dose_from_dataset(dcm_dose)
    mask = get_dose_grid_structure_mask(structure_name, dcm_struct, dcm_dose)

    return dose[mask]


def create_dvh(structure, dcm_struct, dcm_dose):
    structure_dose_values = find_dose_within_structure(structure, dcm_struct,
                                                       dcm_dose)
    hist = np.histogram(structure_dose_values, 100)
    freq = hist[0]
    bin_edge = hist[1]
    bin_mid = (bin_edge[1::] + bin_edge[:-1:]) / 2

    cumulative = np.cumsum(freq[::-1])
    cumulative = cumulative[::-1]
    bin_mid = np.append([0], bin_mid)

    cumulative = np.append(cumulative[0], cumulative)
    percent_cumulative = cumulative / cumulative[0] * 100

    plt.plot(bin_mid, percent_cumulative, label=structure)
    plt.title('DVH')
    plt.xlabel('Dose (Gy)')
    plt.ylabel('Relative Volume (%)')
