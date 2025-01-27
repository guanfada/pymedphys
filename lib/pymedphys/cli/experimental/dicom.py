# Copyright (C) 2020 Simon Biggs

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Experimental command line DICOM tools.

Provides an extra argument `--pseudo` to the `dicom anonymise` CLI.
If you wish to utilise standard anonymisation, please instead use `pymedphys dicom anonymise`
as opposed to `pymedphys experimental dicom anonymise`."""

from pymedphys.cli import dicom

from pymedphys._experimental.pseudonymisation import anonymise_with_pseudo_cli


def dicom_cli(subparsers):
    dicom_parser, dicom_subparsers = dicom.set_up_dicom_cli(subparsers)
    anonymise(dicom_subparsers)

    return dicom_parser


def anonymise(dicom_subparsers):
    parser = dicom.anonymise(dicom_subparsers)

    parser.add_argument(
        "--pseudo",
        action="store_true",
        help=(
            "Use this flag to activate the use of pseudonymisation of the "
            "identifying elements in the DICOM files, "
            "as opposed to replacing them with 'dummy' values. "
            "The pseudonymised values are SHA3_256 hashed if text or UIDs, shifted if dates, and jittered if an age. "
            "UIDs retain consistency so that entire sets of data will retain their referential integrity. "
            "Patient Identifiers stay consistent but are not reversible, and are unlikely to collide with other patient identifiers"
        ),
    )

    parser.set_defaults(func=anonymise_with_pseudo_cli)
