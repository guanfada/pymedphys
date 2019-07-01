# Copyright (C) 2019 South Western Sydney Local Health District,
# University of New South Wales

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

# This work is derived from:
# https://github.com/AndrewWAlexander/Pinnacle-tar-DICOM
# which is released under the following license:

# Copyright (c) [2017] [Colleen Henschel, Andrew Alexander]

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sys
import os
import logging

from .pinn_yaml import pinn_to_dict
from .pinnacle_plan import PinnaclePlan
from .pinnacle_image import PinnacleImage
from .rtstruct import convert_struct
from .rtplan import convert_plan
from .rtdose import convert_dose
from .image import convert_image


# This class holds all information relating to the Pinnacle Dataset
# Can be used to export various elements of the dataset, Images,
# RTSTRUCT, RTPLAN or RTDOSE.
class Pinnacle:

    def __init__(self, path, logger=None):

        self._logger = logger  # Logger to use for all logging

        self._path = path # Path to the root directory of the dataset
                         # (containing the Patient file)

        self._patient_info = None  # The patient data read from
        self._plans = None  # Pinnacle plans for this path
        self._images = None  # Images found in image.info

        if not self._logger:
            self._logger = logging.getLogger(__name__)
            self._logger.setLevel(logging.DEBUG)

            if len(self._logger.handlers) == 0:
                ch = logging.StreamHandler(sys.stdout)
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s')
                ch.setFormatter(formatter)
                ch.setLevel(logging.DEBUG)

                self._logger.addHandler(ch)

    @property
    def logger(self):
        return self._logger

    @property
    def patient_info(self):

        if not self._patient_info:
            path_patient = os.path.join(self._path, "Patient")
            self.logger.debug(
                'Reading patient data from: {0}'.format(path_patient))
            self._patient_info = pinn_to_dict(path_patient)

            # Set the full patient name
            self._patient_info['FullName'] = "{0}^{1}^{2}^".format(
                self._patient_info['LastName'],
                self._patient_info['FirstName'],
                self._patient_info['MiddleName'])

            # gets birthday string with numbers and dashes
            dobstr = self._patient_info['DateOfBirth']
            if '-' in dobstr:
                dob_list = dobstr.split('-')
            elif '/' in dobstr:
                dob_list = dobstr.split('/')
            else:
                dob_list = dobstr.split(' ')

            dob = ""
            for num in dob_list:
                if len(num) == 1:
                    num = '0' + num
                dob = dob + num

            self._patient_info['DOB'] = dob

        return self._patient_info

    @property
    def plans(self):

        # Read patient info to populate patients plns
        if not self._plans:

            self._plans = []
            for plan in self.patient_info['PlanList']:
                path_plan = os.path.join(
                    self._path, "Plan_"+str(plan['PlanID']))
                self._plans.append(PinnaclePlan(self, path_plan, plan))

        return self._plans

    @property
    def images(self):

        # Read patient info to populate patients images
        if not self._images:
            self._images = []
            for image in self.patient_info['ImageSetList']:
                pi = PinnacleImage(self, self._path, image)
                self._images.append(pi)

        return self._images

    def export_struct(self, plan, export_path="."):

        # Export Structures for plan
        convert_struct(plan, export_path)

    def export_dose(self, plan, export_path="."):

        # Export dose for plan
        convert_dose(plan, export_path)

    def export_plan(self, plan, export_path="."):

        # Export rtplan for plan
        convert_plan(plan, export_path)

    def export_image(self, image=None, series_uid="", export_path="."):

        for im in self.images:
            im_info = im.image_info[0]
            im_suid = im_info['SeriesUID']
            if len(series_uid) > 0 and im_suid == series_uid:
                convert_image(im, export_path)
                break

        if image:
            convert_image(image, export_path)

    def print_images(self):

        for i in self.images:
            image_header = i.image_header
            self.logger.info('{0}: {1} {2}'.format(
                image_header['modality'],
                image_header['series_UID'],
                image_header['SeriesDateTime']))

    def print_plan_names(self):

        for p in self.plans:
            self.logger.info(p.plan_info['PlanName'])

    def print_trial_names(self):

        for p in self.plans:
            self.logger.info('### ' + p.plan_info['PlanName'] + ' ###')
            for t in p.trials:
                self.logger.info('- '+t['Name'])

    def print_trial_names_in_plan(self, p):

        self.logger.info('### ' + p.plan_info['PlanName'] + ' ###')
        self.logger.info(p.path)
        for t in p.trials:
            self.logger.info('- '+t['Name'])
