import copy
import math
import os
import sys
import uuid
import warnings
import re

import numpy

import pydicom
from pydicom.sequence import Sequence
from pydicom.dataset import Dataset


class DICOMDirectory:
    def __init__(self, directory=None):
        self._directory = directory

    @property
    def directory(self):
        return self._directory

    @directory.setter
    def directory(self, directory):
        self._directory = directory

    def __iter__(self):
        if self._directory is None:
            self.filenames = []
        else:
            self.filenames = os.listdir(self._directory)
        return self

    def next(self):
        while self.filenames:
            filename = self.filenames.pop(0)
            path = os.path.join(self._directory, filename)
            try:
                dataset = pydicom.dcmread(path)
            except pydicom.errors.InvalidDicomError:
                warnings.warn('%s is not a valid DICOM file' % filename)
                continue
            if not hasattr(dataset, 'SOPInstanceUID'):
                warnings.warn('%s is not a valid DICOM file' % filename)
                continue
            return path, dataset
        raise StopIteration


class DICOMSplitter:
    def __init__(self, pixel_array=None, axis=0, n=2):
        self._pixel_array = pixel_array
        self._axis = axis
        self._n = n

    @property
    def pixel_array(self):
        return self._pixel_array

    @pixel_array.setter
    def pixel_array(self, pixel_array):
        self._pixel_array = pixel_array

    @property
    def axis(self):
        return self._axis

    @axis.setter
    def axis(self, axis):
        self._axis = axis

    @property
    def n(self):
        return self._n

    @n.setter
    def n(self, n):
        self._n = n

    def __iter__(self):
        self.index = 0
        if self._pixel_array is not None:
            size = self._pixel_array.shape[self._axis]
            self.size = int(math.floor(size/self._n))
        return self

    def next(self):
        if self.index == self._n:
            raise StopIteration

        index = self.index

        if self._pixel_array is None:
            self.index += 1
            return index, None, None

        start = numpy.zeros(self._pixel_array.ndim, numpy.int16)
        remainder = self._pixel_array.shape[self._axis] % self._n
        offset = max(0, index + 1 + remainder - self._n)
        if offset:
            warnings.warn('image axis %d not divisible by %d'
                          ', split %d offset 1 pixel from previous split'
                          % (self._axis, self._n, index + 1))
        start[self._axis] = index * self.size + offset
        stop = numpy.zeros(self._pixel_array.ndim, numpy.int16)
        stop[self._axis] = start[self._axis] + self.size
        indices = numpy.arange(start[self._axis], stop[self._axis])
        self.index += 1
        return index, start, numpy.take(self._pixel_array, indices, self._axis)


def x667_uuid():
    return '2.25.%d' % uuid.uuid4()


def parse_patient(patient, delimiter='_'):
    root = str(patient).split(delimiter)[0]
    ids = str(patient).split(delimiter)[1:]
    trailing = ''
    if ids[-1] in map(str, range(1, 10)):
        warnings.warn('patient %s ends with %s, removing...' % (patient,
                                                                ids[-1]))
        trailing = delimiter + ids.pop()
    return [delimiter.join((root, re.sub("[^0-9]", "", id_))) for id_ in ids], trailing

def affine(dataset):
    S = numpy.array(dataset.ImagePositionPatient, numpy.float64)
    F = numpy.array([dataset.ImageOrientationPatient[3:],
                     dataset.ImageOrientationPatient[:3]], numpy.float64).T
    delta_r, delta_c = map(float, dataset.PixelSpacing)
    return numpy.array([[F[0, 0]*delta_r, F[0, 1]*delta_c, 0, S[0]],
                        [F[1, 0]*delta_r, F[1, 1]*delta_c, 0, S[1]],
                        [F[2, 0]*delta_r, F[2, 1]*delta_c, 0, S[2]],
                        [0, 0, 0, 1]])


def directory_name(directory, i):
    return os.path.join(directory.rstrip(os.sep), i)


def make_output_paths(directory, n, output_paths=None):
    if output_paths is None:
        output_paths = [directory_name(directory, i) for i in range(n)]
    for output_path in output_paths:
        try:
            os.mkdir(output_path)
        except:
            pass
    return output_paths


def make_output_path(directory, i, output_path=None):
    if output_path is None:
        output_path = directory_name(directory, i)
    try:
        os.mkdir(output_path)
    except:
        pass
    return output_path


def derive_image_sequence(sop_class_uid, sop_instance_uid):
    source_image = Dataset()
    source_image.ReferencedSOPClassUID = sop_class_uid
    source_image.ReferencedSOPInstanceUID = sop_instance_uid

    purpose_of_reference = Dataset()
    purpose_of_reference.CodeValue = '113130'
    purpose_of_reference.CodingSchemeDesignator = 'DCM'
    purpose_of_reference.CodeMeaning = \
            'Predecessor containing group of imaging subjects'
    source_image.PurposeOfReferenceCodeSequence = \
            Sequence([purpose_of_reference])
    derivation_image = Dataset()
    derivation_image.SourceImageSequence = Sequence([source_image])
    derivation_code = Dataset()
    derivation_code.CodeValue = '113131'
    derivation_code.CodingSchemeDesignator = 'DCM'
    derivation_code.CodeMeaning = \
            'Extraction of individual subject from group'
    derivation_image.DerivationCodeSequence = Sequence([derivation_code])
    derivation_image_sequence = Sequence([derivation_image])

    return derivation_image_sequence


def get_patient(patient_name, patient_id, n, patient_names=None, patient_ids=None, order=None):
    name_trailing, id_trailing = '', ''
    if patient_names is None:
        patient_names, name_trailing = parse_patient(patient_name)
    if patient_ids is None:
        patient_ids, id_trailing = parse_patient(patient_id)
    if len(patient_names) != n:
        tmpName = 3 * ['blank']
        for i in range(len(order)):
            if int(order[i]) != 0:
                try:
                    tmpName[i] = patient_names.pop(0)
                except:
                    continue
        patient_names = tmpName
        warnings.warn('failed to parse PatientName %s, append a blank' % patient_name)
    if len(patient_ids) != n:
        tmpId = 3 * ['blank']
        for i in range(len(order)):
            if int(order[i]) != 0:
                try:
                    tmpId[i] = patient_ids.pop(0)
                except:
                    continue
        patient_ids = tmpId
        warnings.warn('failed to parse PatientID %s, append a blank' % patient_id)
    source_patient = Dataset()
    # FIXME: remove '_1'?
    source_patient.PatientName = patient_name
    source_patient.PatientID = patient_id

    return (patient_names, patient_ids), Sequence([source_patient]), (name_trailing, id_trailing)


def set_pixel_data(dataset, pixel_array):
    dataset.PixelData = pixel_array.tostring()
    dataset.Rows, dataset.Columns = pixel_array.shape

def checkDirectory(directory, output_dir=None):
    for root, subdirs, files in os.walk(directory):
        if len(files):
            if files.pop(0) != '.DS_Store':
                newRoot = os.path.join(output_dir, root.split('/')[-4])
                newRoot = os.path.join(newRoot, root.split('/')[-3])
                newRoot = os.path.join(newRoot, root.split('/')[-2])
                newRoot = os.path.join(newRoot, root.split('/')[-1])
                if not os.path.exists(newRoot):
                    os.makedirs(newRoot)
                yield root, newRoot
def split_dicom_directory(directory, axis=0, n=3, keep_origin=False,
                          study_instance_uids=None, series_instance_uids=None,
                          series_descriptions=None, output_dir=None,
                          derivation_description=None, patient_names=None,
                          patient_ids=None, output_paths=None,
                          mangle_output_paths=False, order=None):
    # FIXME processing all subfolder with same split volumn
    # if series_instance_uids:
    #     n = len(series_instance_uids)
    # if n is None:
    #     raise ValueError
    # if series_descriptions and len(series_descriptions) != n:
    #     raise ValueError
    # if study_instance_uids and len(study_instance_uids) != n:
    #     raise ValueError
    # for directoryChecked, newRoot in checkDirectory(directory, output_dir):
    #     print(directoryChecked)
    #     for path, dataset in DICOMDirectory(directoryChecked):
    #         try:
    #             pixel_array = dataset.pixel_array
    #         except (TypeError, AttributeError):
    #             pixel_array = None
    #         dicom_splitter = DICOMSplitter(pixel_array, axis, n)
    #
    #         dataset.ImageType = ['DERIVED', 'PRIMARY', 'SPLIT']
    #
    #         dataset.DerivationDescription = derivation_description
    #
    #         dataset.DerivationImageSequence = derive_image_sequence(dataset.SOPClassUID, dataset.SOPInstanceUID)
    #
    #         parsed, dataset.SourcePatientGroupIdentificationSequence, trailing = get_patient(dataset.PatientName, dataset.PatientID, n, patient_names, patient_ids)
    #         parsed_patient_names, parsed_patient_ids = parsed
    #         name_trailing, id_trailing = trailing
    #
    #         if not study_instance_uids:
    #             study_instance_uids = [x667_uuid() for i in range(n)]
    #
    #         if not series_instance_uids:
    #             series_instance_uids = [x667_uuid() for i in range(n)]
    #
    #         for i, origin, pixel_array in dicom_splitter:
    #             split_dataset = copy.deepcopy(dataset)
    #
    #             if pixel_array is not None:
    #                 set_pixel_data(split_dataset, pixel_array)
    #
    #                 if not keep_origin:
    #                     affine_matrix = affine(dataset)
    #                     position = affine_matrix.dot(numpy.append(origin, [0, 1]))
    #                     # maximum 16 characters
    #                     split_dataset.ImagePositionPatient = [str(p)[:16] for p in position[:3]]
    #
    #             split_dataset.SOPInstanceUID = x667_uuid()
    #             split_dataset.file_meta.MediaStorageSOPInstanceUID = split_dataset.SOPInstanceUID
    #
    #             split_dataset.StudyInstanceUID = study_instance_uids[i]
    #
    #             split_dataset.SeriesInstanceUID = series_instance_uids[i]
    #             split_dataset.StorageMediaFileSetUID = series_instance_uids[i] + '.0'
    #
    #             if series_descriptions:
    #                 split_dataset.SeriesDescription = series_descriptions[i]
    #             else:
    #                 split_dataset.SeriesDescription += ' split'
    #
    #             split_dataset.PatientName = parsed_patient_names[i]
    #             split_dataset.PatientID = parsed_patient_ids[i]
    #
    #             split_dataset.SeriesNumber = (10 *  split_dataset.SeriesNumber) + i + 1
    #
    #             if output_paths:
    #                 output_path = output_paths[i]
    #             elif mangle_output_paths:
    #                 output_path = parsed_patient_ids[i] + id_trailing
    #             else:
    #                 output_path = None
    #             created_output_path = make_output_path(newRoot, i, output_path)
    #             filename = os.path.join(created_output_path, os.path.basename(path))
    #             split_dataset.save_as(filename)
    order = order.split(',')
    if n != len(order):
        raise Exception('[ERROR] # of split has to equal to length of order')
    if series_instance_uids:
        n = len(series_instance_uids)
    if n is None:
        raise ValueError
    if series_descriptions and len(series_descriptions) != n:
        raise ValueError
    if study_instance_uids and len(study_instance_uids) != n:
        raise ValueError
    for directoryChecked, newRoot in checkDirectory(directory, output_dir):
        for path, dataset in DICOMDirectory(directoryChecked):
            # print(newRoot)
            try:
                pixel_array = dataset.pixel_array
            except (TypeError, AttributeError):
                pixel_array = None
            dicom_splitter = DICOMSplitter(pixel_array, axis, n)

            dataset.ImageType = ['DERIVED', 'PRIMARY', 'SPLIT']

            dataset.DerivationDescription = derivation_description

            dataset.DerivationImageSequence = derive_image_sequence(dataset.SOPClassUID, dataset.SOPInstanceUID)

            parsed, dataset.SourcePatientGroupIdentificationSequence, trailing = get_patient(dataset.PatientName, dataset.PatientID, n, patient_names, patient_ids, order)
            parsed_patient_names, parsed_patient_ids = parsed
            # print(parsed_patient_names, parsed_patient_ids)
            name_trailing, id_trailing = trailing
            if not study_instance_uids:
                study_instance_uids = [x667_uuid() for i in range(n)]

            if not series_instance_uids:
                series_instance_uids = [x667_uuid() for i in range(n)]

            for i, origin, pixel_array in dicom_splitter:
                if parsed_patient_names[i] != 'blank':
                    split_dataset = copy.deepcopy(dataset)

                    if pixel_array is not None:
                        set_pixel_data(split_dataset, pixel_array)

                        if not keep_origin:
                            affine_matrix = affine(dataset)
                            position = affine_matrix.dot(numpy.append(origin, [0, 1]))
                            # maximum 16 characters
                            split_dataset.ImagePositionPatient = [str(p)[:16] for p in position[:3]]

                    split_dataset.SOPInstanceUID = x667_uuid()
                    split_dataset.file_meta.MediaStorageSOPInstanceUID = split_dataset.SOPInstanceUID

                    split_dataset.StudyInstanceUID = study_instance_uids[i]

                    split_dataset.SeriesInstanceUID = series_instance_uids[i]
                    split_dataset.StorageMediaFileSetUID = series_instance_uids[i] + '.0'

                    if series_descriptions:
                        split_dataset.SeriesDescription = series_descriptions[i]
                    else:
                        if split_dataset.Modality == 'PT':
                            split_dataset.SeriesDescription = parsed_patient_ids[i] + ' split'
                        elif split_dataset.Modality == 'CT':
                            split_dataset.SeriesDescription = parsed_patient_ids[i] + ' split'
                        else:
                            split_dataset.SeriesDescription += ' split'

                    split_dataset.PatientName = parsed_patient_names[i]
                    split_dataset.PatientID = parsed_patient_ids[i]

                    split_dataset.SeriesNumber = (10 *  split_dataset.SeriesNumber) + i + 1

                    if output_paths:
                        output_path = output_paths, output_paths[i]
                    elif mangle_output_paths:
                        output_path = parsed_patient_ids[i] + id_trailing
                    else:
                        output_path = None
                    created_output_path = make_output_path(newRoot, parsed_patient_names[i], output_path)
                    filename = os.path.join(created_output_path, os.path.basename(path))
                    split_dataset.save_as(filename)

import argparse

# parser = argparse.ArgumentParser()
# parser.add_argument('DICOM_DIRECTORY', nargs='*')
# parser.add_argument('-a', '--axis', type=int, default=1,
#                     help='axis (0 for rows, 1 for columns)'
#                          ', default columns')
# parser.add_argument('-o', '--keep_origin', action='store_true',
#                     help='origin position from offset from original'
#                          ' volume, default no')
# parser.add_argument('-s', '--study_instance_uids', nargs='*',
#                     help='set the study instance UIDs')
# parser.add_argument('-S', '--unique_study_instance_uids',
#                     action='store_true',
#                     help='shared the study instance UID in all series')
# parser.add_argument('-d', '--series_descriptions', nargs='*',
#                     help='set the series descriptions')
# parser.add_argument('-v', '--derivation_description',
#                     default='Original volume split into equal subvolumes for each patient',
#                     help='set the derivation description')
# parser.add_argument('-p', '--patient_names', nargs='*',
#                     help='patient names')
# parser.add_argument('-i', '--patient_ids', nargs='*', help='patient ids')
# parser.add_argument('-O', '--output_paths', nargs='*', help='output path names')
# parser.add_argument('-Outdir', '--output_dir', help='save in new output directory')
# parser.add_argument('-X', '--mangle_output_paths', action='store_true',
#                     help='set output path to split patient ID plus'
#                          'trailing characters')
# parser.add_argument('-order', '--order', help='order of patient placed in scanner', default='1,1,1')

# group = parser.add_mutually_exclusive_group(required=True)
# group.add_argument('-n', type=int, help='split into N volumes')
# group.add_argument('-u', '--series_instance_uids', nargs='*', default=[],
#                    help='split volume for each series instance UID')

# kwargs = vars(parser.parse_args())
# # directories = kwargs.pop('DICOM_DIRECTORY')
# print n_of_split 
# print order 
# print subfolders 
# print topFolder

Outdir = outPath
topFolder = topFolder
subfolders = subfolders
axis = axis
# shared = not kwargs.pop('unique_study_instance_uids')
# if shared and not kwargs.get('study_instance_uids'):
#     n = len(kwargs.get('series_instance_uids')) or kwargs.get('n')
#     kwargs['study_instance_uids'] = [x667_uuid() for i in range(n)]
# subfolders = [subfolders for subfolders in os.listdir(topFolder)]

# if modality == 'MRI':
for index in range(len(subfolders)):
    directory = os.path.join(topFolder, subfolders[index])
    print directory
    kwargs = {"axis": int(axis[index]), "n": int(n_of_split[index]), "order": order[index], "output_dir": Outdir}

    split_dicom_directory(directory, **kwargs)
# elif modality == 'PTCT':
#     for index in range(len(subfolders)):
#         directory = os.path.join(topFolder, subfolders[index])
#         kwargs = {"axis": int(axis[index]), "n": int(n_of_split[index]), "order": order[index], "output_dir": Outdir, "modality": modality}

#         split_dicom_directory(directory, **kwargs)
# print(len(kwargs['order'].split(',')))

# for directory in directories:
#     split_dicom_directory(directory, **kwargs)

splitedVolumn = Outdir
