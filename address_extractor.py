import argparse
# import polyleven
import pickle
import json

from no_accent_vietnamese import convert_no_accent
from database_helper import DatabaseHelper
import editdistance as ed

class AddressExtractor:
    def __init__(self, pickle_file_dir):
        """
        Init AddressExtractor object.

        Parameters: pickle_file_dir (str): Directory of pickle file that
        stores location database
        """
        with open(pickle_file_dir, "rb") as file_object:
            self.database_helper = pickle.load(file_object)
        self.THRESHOLD_EDIT_RATIO = [None, None, 0.9, 0.8]

    def find_match_address(self, words, loc_data, loc_type):
        """
        Find match address of a list of words

        Parameters:
        words (list of str): list of words
        loc_data (tuple): data from database
        loc_type (int): list of level of address (2: (1, 2), 3: (1, 2, 3))

        Returns:
        tuple (min_value, idx):
            similarity_score (double): max value of similarity score
            idx (tuple x, y):
                x (int): start position of words sub array that nearly matches with one of addresses
                y (int): position of address in database
        """
        min_value = 1 - self.THRESHOLD_EDIT_RATIO[loc_type] + 1e-6
        idx = None
        for i in range(len(words)):
            s = convert_no_accent("".join(words[i:]))
            for j, (_, list_str) in enumerate(loc_data):
                for match_str in list_str:
                    length = max(len(s), len(match_str))
                    # ratio = polyleven.levenshtein(s, match_str, int(min_value * length)) / length
                    ratio = ed.eval(s,match_str)/length
                    if ratio <= int(min_value * length):
                        if ratio < min_value:
                            min_value = ratio
                            idx = (i, j)
        return 1 - min_value, idx

    def extract(self, address_string):
        """
        Extract location information with multiple level.

        Level 1: Province, City
        Level 2: District, Town, City
        Level 3: Ward, Commune, Town
        Level 4: Other (Hamlet, Village, Street)

        Parameters:
        address_string (str): Raw string from OCR

        Returns:
        dict: Has field "address" stores an array of location information dict
              ("level", "id", "type", "name")
        """
        if address_string[-1] == ".":
            address_string = address_string[:-1]
        address_string = address_string.replace(".", " ")
        address_string = address_string.replace(",", " ")
        address_string = address_string.replace("-", " ")
        address_string = address_string.replace("  ", " ")
        words = address_string.split()

        loc_data, loc_type = self.database_helper.data_2, 2
        similarity_score, idx = self.find_match_address(words, loc_data, loc_type)

        if similarity_score >= self.THRESHOLD_EDIT_RATIO[2]:
            _loc_data, _loc_type = [], 3
            for j in self.database_helper.next_2[idx[1]]:
                _loc_data.append(self.database_helper.data_3[j])
            _similarity_score, _idx = self.find_match_address(words, _loc_data, _loc_type)
            if _idx is not None:
                similarity_score, loc_data, loc_type, idx = _similarity_score, _loc_data, \
                                                            _loc_type, _idx
        else:
            loc_data, loc_type = self.database_helper.data_3, 3
            similarity_score, idx = self.find_match_address(words, loc_data, loc_type)

        # print(similarity_score)
        # if idx is not None:
        #     print(" ".join(words[idx[0]:]), loc_data[idx[1]])

        ans = []

        if idx is None:
            item = dict(level=4, name=(" ".join(words)))
            ans.append(item)
            return ans

        for i in range(1, loc_type + 1):
            pos_in_location_level = loc_data[idx[1]][0][i]
            item = dict(level=i,
                        id=self.database_helper.location_level[i][pos_in_location_level][0],
                        type=self.database_helper.prefixes[
                            self.database_helper.location_level[i][pos_in_location_level][1]
                        ], name=self.database_helper.location_level[i][pos_in_location_level][2][0])
            ans.append(item)
        if idx[0] != 0:
            item = dict(level=4, name=(" ".join(words[:idx[0]])))
            ans.append(item)
        return ans

def edit_sentence(sentence, address_extractor):
    st = ''
    list_sent = address_extractor.extract(str(sentence))[::-1]
    for s in list_sent[:-1]:
        st += s['name'] + ', '
    st += list_sent[-1]['name']
    return st
# if __name__ == '__main__':
#     # arg_parser = argparse.ArgumentParser()
#     # arg_parser.add_argument('--pickle_dir', type=str, default="databases/gso_gov_vn_191022.pkl",
#     #                         help="Pickle file directory")
#     # arg_parser.add_argument('--request_json_dir', type=str, default="databases/id_card_data.json",
#     #                         help="JSON file directory")
#     # args = arg_parser.parse_args()
#     s = 'Nơi ĐKHK thường trú:.51/22, Lê Đức Tho, P.6, Quận Gò Vấp TP H Chí Minh'
#     pickle_dir = 'databases/gso_gov_vn_191022.pkl'
#     # address_extractor = AddressExtractor(args.pickle_dir)
#     address_extractor = AddressExtractor(pickle_dir)
#     print("Database loading completed!")

#     # with open(args.request_json_dir, 'r', encoding='utf8') as f:
#     #     data = json.load(f)['data']

#     # result = []
#     # for id_card in data:
#     #     result.append(address_extractor.extract(id_card['residence_address']))
#     result = address_extractor.extract(s)
#     from pprint import pprint

#     pprint(result)
