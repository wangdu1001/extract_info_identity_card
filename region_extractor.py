import json
import cv2 
import numpy as np
from pyvi import ViUtils
from pathlib import Path 
from difflib import SequenceMatcher
from address_extractor import *

def transfer_box(box):
    '''
    input: box has 4 points 
    output: box has 4 coordinates tl=(x1, y1), br=(x2, y2)
    input: box = [tl, tr, br, bl]
    return: [x1, y1, x2, y2]
    '''
    box_new = []
    box = np.array(box)
    top_left, bottom_right = np.amin(box, axis=0), np.amax(box, axis=0)
    box_new = [top_left[0], top_left[1], bottom_right[0], bottom_right[1]]
    return box_new

def compute_inter_area(boxA, boxB):
    boxA = transfer_box(boxA)
    boxB = transfer_box(boxB)
    tl_interbox = np.maximum(boxA[:2], boxB[:2])
    br_interbox = np.minimum(boxA[2:], boxB[2:])
    intersection = np.maximum(0.0, br_interbox - tl_interbox)
    interArea = intersection[0] * intersection[1]
    return interArea

def computer_box_area(box):
    box = transfer_box(box)
    area = (box[3] - box[1]) * (box[2] - box[0])
    return area

class DectectField(object):
	def __init__(self):
		self.RATIO_THRES = 0.7
		self.SIMILARITY_THRES = 0.4
		self.WIDTH_BOX_SCALE = 15
		self.HEIGHT_BOX_SCALE = 2
		self.IDENTIFY_FIELD = ['SỐ', 'Họ tên', 'Sinh ngày', 'Nguyên quán', 'Nơi ĐKHK thường trú']

	def get_json_data(self, json_path):
		with open(json_path, 'r', encoding = 'utf8') as read_json:
			data = json.load(read_json)
		return data

	def compute_similarity_sentence(self, dst, src):
		dst, src = dst.lower(), src.lower()
		dst, src = str(ViUtils.remove_accents(dst.strip())), str(ViUtils.remove_accents(src.strip()))
		seq_match = SequenceMatcher(None, src, dst)
		match = seq_match.find_longest_match(0, len(src), 0, len(dst))
		return 0 if match.size == 0 else match.size / len(src)

	def detect_field(self, field, json_path):
		json_data = self.get_json_data(json_path) 
		sorted_list_field = sorted(json_data['text_lines'], 
				key = lambda x : 1 - self.compute_similarity_sentence(x['text'], field))
		txt_field = sorted_list_field[0]['text']
		coor_field = [[pts['x'], pts['y']] for pts in sorted_list_field[0]['coordinates']]

		return txt_field, coor_field

	def get_values_of_field(self, field, json_path):
		json_data = self.get_json_data(json_path)
		txt_field, coor_field = self.detect_field(field, json_path)
		result = dict()
		result['top'] = txt_field
		result['bottom'] = ''
		if self.compute_similarity_sentence(txt_field, field) < self.SIMILARITY_THRES:
			result['top'], result['bottom'] = '', ''
			return result
		textline = [tl for tl in json_data['text_lines'] if tl['text'] != txt_field]
		width = max(coor_field[1][0], coor_field[2][0]) - min(coor_field[0][0], coor_field[3][0])
		height = max(coor_field[2][1], coor_field[3][1]) - min(coor_field[0][1], coor_field[1][1])

		top_box_x = np.max(coor_field, axis=0)[0]
		top_box_y = np.min(coor_field, axis=0)[1] - height * 0.8
		top_box_w = width * self.WIDTH_BOX_SCALE
		top_box_h = height * self.HEIGHT_BOX_SCALE

		top_box = [[top_box_x, top_box_y], #x,y
		           [top_box_x + top_box_w, top_box_y], #x+w, y 
		           [top_box_x + top_box_w, top_box_y + top_box_h], #x+w, y+h 
		           [top_box_x, top_box_y + top_box_h]] #x, y+h

		bot_box_x = np.min(coor_field, axis=0)[0]
		bot_box_y = np.max(coor_field, axis=0)[1] - height * 0.25
		bot_box_w = width * self.WIDTH_BOX_SCALE
		bot_box_h = height * self.HEIGHT_BOX_SCALE
		bot_box = [[bot_box_x, bot_box_y], 
		           [bot_box_x + bot_box_w, bot_box_y], 
		           [bot_box_x + bot_box_w, bot_box_y + bot_box_h], 
		           [bot_box_x, bot_box_y + bot_box_h]]

		max_inter_area_top = 0.
		max_inter_area_bot = 0.
		for tl in textline:
			txt_box = [[pts['x'], pts['y']] for pts in tl['coordinates']]

			inter_area_top = compute_inter_area(txt_box, top_box)
			inter_ratio_top = inter_area_top / computer_box_area(txt_box)
			if(inter_ratio_top > self.RATIO_THRES and inter_area_top > max_inter_area_top):
				result['top'] = tl['text']
				max_inter_area_top = inter_area_top

			inter_area_bot = compute_inter_area(txt_box, bot_box)
			inter_ratio_bot = inter_area_bot / computer_box_area(txt_box)
			if(inter_ratio_bot > self.RATIO_THRES and inter_area_bot > max_inter_area_bot):
				result['bottom'] = tl['text']
				max_inter_area_bot = inter_area_bot

		return result

	def extract_info_card(self, json_path):
		dict_info = dict()
		dict_card_field = self.IDENTIFY_FIELD
		for field in dict_card_field:
			result = self.get_values_of_field(field, json_path)
			if(field == self.IDENTIFY_FIELD[0] or field == self.IDENTIFY_FIELD[2]):
				result['bottom'] = ''
			dict_info[str(field)] = str(result['top']) + ' ' + str(result['bottom'])
		return dict_info

if __name__ == '__main__':
	pickle_dir = 'databases/gso_gov_vn_191022.pkl'
	json_dir = 'jsons/'

	field_extractor = DectectField()
	address_extractor = AddressExtractor(pickle_dir)
	print("[INFO] Database loading completed!")


	list_json_path = list(Path(json_dir).glob('*.json'))

	for json_path in list_json_path:
		info_extract = field_extractor.extract_info_card(json_path)
		print('before : ')
		print(info_extract)

		info_extract['Nguyên quán'] = edit_sentence(str(info_extract['Nguyên quán']), address_extractor)
		info_extract['Nơi ĐKHK thường trú'] = edit_sentence(str(info_extract['Nơi ĐKHK thường trú']), address_extractor)

		print('after: ')
		print(info_extract)
		print('____________________________________________________________________________________________________________________________________________________________________')