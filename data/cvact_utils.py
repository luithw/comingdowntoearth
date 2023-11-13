import io
import os
import torch.utils.data as data
import scipy.io as sio
import numpy as np
import pandas as pd
from PIL import Image
import traceback


class CVACT(data.Dataset):
    def __init__(self, root, all_data_list, use_polar=False, isTrain=False, transform_op=None):
        self.polar = use_polar
        self.train = isTrain
        self.transform_op = transform_op
        self.posDistThr = 25
        self.posDistSqThr = self.posDistThr * self.posDistThr
        self.root = root
        self.all_data_list = all_data_list

        #LOAD MAT FILE
        idx = 0
        self.all_list, self.all_list_idx = [], []
        self.all_data = sio.loadmat(self.all_data_list)

        self.bin_file_lookup = {}
        if "bin" in self.root:
            #     walk the directory and find the file "file_list.csv"
            for subdir, _, files in os.walk(self.root):
                for file in files:
                    if file == "file_list.csv":
                        self.bin_file_lookup[os.path.basename(subdir)] = pd.read_csv(os.path.join(subdir, file), index_col=0)
                        break

        for i in range(0, len(self.all_data['panoIds'])):
            grd_id_ori = self.root + '_' + self.all_data['panoIds'][i] + '/' + self.all_data['panoIds'][
                i] + '_zoom_2.jpg'
            grd_id_ori_sem = self.root + '_' + self.all_data['panoIds'][i] + '/' + self.all_data['panoIds'][
                i] + '_zoom_2_sem.jpg'
            grd_id_align_sem = self.root + '_' + self.all_data['panoIds'][i] + '/' + self.all_data['panoIds'][
                i] + '_zoom_2_aligned_sem.jpg'
            sat_id_sem = self.root + '_' + self.all_data['panoIds'][i] + '/' + self.all_data['panoIds'][
                i] + '_satView_sem.jpg'

            if "bin" in self.root:
                try:
                    grd_id_align = self.all_data['panoIds'][i] + '_grdView.jpg'
                    sat_id_ori = self.all_data['panoIds'][i] + '_satView_polish.jpg'
                    pano_lookup = self.bin_file_lookup['streetview_polish'].loc[grd_id_align]
                    if self.polar:
                        sat_lookup = self.bin_file_lookup['polarmap'].loc[sat_id_ori]
                    else:
                        sat_lookup = self.bin_file_lookup['satview_polish'].loc[sat_id_ori]
                except KeyError as err:
                    grd_id_align = "placeholder"
                    pano_lookup = "placeholder"
                    sat_lookup = "placeholder"
            else:
                grd_id_align = self.root + 'streetview_polish/' + self.all_data['panoIds'][i] + '_grdView.jpg'
                if self.polar:
                    sat_id_ori = self.root + 'polarmap/' + self.all_data['panoIds'][i] + '_satView_polish.jpg'
                else:
                    sat_id_ori = self.root + 'satview_polish/' + self.all_data['panoIds'][i] + '_satView_polish.jpg'
            self.all_list.append([grd_id_ori, grd_id_align, grd_id_ori_sem,
                                  grd_id_align_sem, sat_id_ori, sat_id_sem,
                                  self.all_data['utm'][i][0], self.all_data['utm'][i][1]])
            self.all_list_idx.append(idx)
            idx += 1
        self.all_data_size = len(self.all_list)

        #PARTITION IMAGES INTO CELL
        self.utms_all = np.zeros([2, self.all_data_size], dtype=np.float32)
        for i in range(0, self.all_data_size):
            self.utms_all[0, i] = self.all_list[i][6]
            self.utms_all[1, i] = self.all_list[i][7]
        if self.train:
            self.data_inds = self.all_data['trainSet']['trainInd'][0][0] - 1
        else:
            self.data_inds = self.all_data['valSet']['valInd'][0][0] - 1
        self.dataNum = len(self.data_inds)
        self.dataList = []
        self.dataIdList = []
        self.dataUTM = np.zeros([2, self.dataNum], dtype=np.float32)
        for k in range(self.dataNum):
            try:
                self.dataList.append(self.all_list[self.data_inds[k][0]])
                self.dataUTM[:, k] = self.utms_all[:, self.data_inds[k][0]]
                self.dataIdList.append(k)
            except IndexError as err:
                continue
        self.data_list_size = len(self.dataList)
        print('Load data from {}, total {}'.format(self.all_data_list, self.data_list_size))

    def load_im(self, file, resize=None):
        im = Image.open(file)
        im = im.convert("RGB")
        if resize is not None:
            im = im.resize(resize)
        # Convert to np
        im = np.array(im, dtype=np.float32)

        # im = cv2.imread(file)
        # im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        # if resize:
        #     im = cv2.resize(im, resize, interpolation=cv2.INTER_AREA)
        # im = np.array(im, dtype=np.float32)
        return im


    def __getitem__(self, index):
        if "bin" in self.root:
            pano_lookup = self.bin_file_lookup['streetview_polish'].loc[self.dataList[index][1]]
            pano_bin_filename = self.root + 'streetview_polish/%s.bin' % pano_lookup["bin_file"]
            with open(pano_bin_filename, 'rb') as f:
                f.seek(pano_lookup['offset'])
                pano_im = self.load_im(io.BytesIO(f.read(pano_lookup['size'])), resize=(616, 112))

            if self.polar:
                sat_name = 'polarmap'
                resize = (616, 112)
            else:
                sat_name = 'satview_polish'
                resize = None
            sat_lookup = self.bin_file_lookup[sat_name].loc[self.dataList[index][4]]
            sat_bin_filename = self.root + '%s/%s.bin' % (sat_name, sat_lookup["bin_file"])
            with open(sat_bin_filename, 'rb') as f:
                f.seek(sat_lookup['offset'])
                sate_im = self.load_im(io.BytesIO(f.read(sat_lookup['size'])), resize=resize)
        else:
            if self.polar:
                sate_im = self.load_im(self.dataList[index][4], resize=(616, 112))
            else:
                sate_im = self.load_im(self.dataList[index][4])
            pano_im = self.load_im(self.dataList[index][1], resize=(616, 112))
        utm = self.dataUTM[:, index]
        img_data = {'satellite': sate_im,
                     'street': pano_im}
        if self.transform_op:
            img_data = self.transform_op(img_data)
        return img_data, utm

    def __len__(self):
        return self.data_list_size
