
import csv
import pickle
import argparse

from no_accent_vietnamese import convert_no_accent


class DatabaseHelper:
    def __init__(self):
        pass

    def load_csv(self, csv_file_dir):
        self.prefixes = [
            "Thành phố", "Tỉnh",
            "Quận", "Huyện", "Thành phố", "Thị xã",
            "Phường", "Xã", "Thị trấn",
        ]
        self.short_prefixes = ["".join([word[0]
                                        for word in s.split()]).upper() for s in self.prefixes]
        self.lower_prefixes = [s.lower() for s in self.prefixes]
        self.parse_csv(csv_file_dir)
        self.add_location_name()

    def split_name(self, name_location):
        """
        Split string into 2 parts.

        Parameters:
        name_location (str): Raw string (exp: "Thành phố Hà Nội")

        Returns:
        tuple: 2 parts after split (exp: "thành phố", ["Hà Nội"])
        """

        words = name_location.split(" ")
        for i in range(len(words)):
            prefix = (" ".join(words[:i + 1])).lower()
            if prefix in self.lower_prefixes:
                suffix = " ".join(words[i + 1:])
                return self.lower_prefixes.index(prefix), [suffix]

        raise ValueError("Can't parse '{}'".format(name_location))

    @staticmethod
    def insert_to_list(lst, item):
        if not (item in lst):
            lst.append(item)
        return lst.index(item)

    def parse_csv(self, csv_file_dir):
        """
        Parse csv into Python objects.

        Parameters:
        csv_file_dir (str): Directory of csv file need parsing
        """

        """self.data_2
            Array of ([None, pos_1, pos_2], [match_str])
            pos_1: index of level_1 location in self.location_level[1]
            pos_2: ...
            match_str: full name of location: exp, match_str = "Vạn Ninh, Khánh Hòa"
        """
        self.data_2 = []
        """self.next_2
            Array of positions of data_3 that match with data_2
        """
        self.next_2 = []
        """self.data_3
            Array of ([None, pos_1, pos_2, pos_3], [match_str])
            pos_1: index of level_1 location in self.location_level[1]
            pos_2: ...
            pos_3: ...
            match_str: full name of location: exp, match_str = "Đại Lãnh, Vạn Ninh, Khánh Hòa"
        """
        self.data_3 = []
        """self.location_level 
            for each level, Array of (code, type_idx, [Array of possible names])
        """
        self.location_level = [[] for i in range(4)]

        with open(csv_file_dir, encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            next(reader, None)  # skip the header

            for row in reader:
                pos = [None for i in range(4)]
                pos[1] = self.insert_to_list(
                    self.location_level[1], (row[6], *self.split_name(row[7])))
                pos[2] = self.insert_to_list(
                    self.location_level[2], (row[4], *self.split_name(row[5])))
                pos[3] = self.insert_to_list(
                    self.location_level[3], (row[0], *self.split_name(row[1])))

                self.data_3.append((pos, []))
                if (pos[:3], []) not in self.data_2:
                    self.data_2.append((pos[:3], []))
                    self.next_2.append([])
                idx = self.data_2.index((pos[:3], []))
                self.next_2[idx].append(len(self.data_3) - 1)

    def add_location_name(self):
        for level in range(1, 4):
            for location in self.location_level[level]:
                location[2].append(self.prefixes[location[1]] + " " + location[2][0])
                location[2].append(self.short_prefixes[location[1]] + " " + location[2][0])
                """ Thành phố, Quận: Hồ Chí Minh -> HCM """
                if self.short_prefixes[location[1]] in ["TP", "Q"]:
                    location[2].append(
                        "".join([word[0] for word in location[2][0].split()]).upper())
                """ Phường: 2 -> P 02 """
                if self.short_prefixes[location[1]] == "P" and len(location[2][0]) == 1 \
                        and location[2][0].isdigit():
                    location[2].append("P 0" + location[2][0])

        for pos, lst in self.data_2:
            _, pos_1, pos_2 = pos
            for name_1 in self.location_level[1][pos_1][2]:
                for name_2 in self.location_level[2][pos_2][2]:
                    lst.append(convert_no_accent("".join([name_2, name_1])).replace(" ", ""))
        for pos, lst in self.data_3:
            _, pos_1, pos_2, pos_3 = pos
            for name_1 in self.location_level[1][pos_1][2]:
                for name_2 in self.location_level[2][pos_2][2]:
                    for name_3 in self.location_level[3][pos_3][2]:
                        lst.append(convert_no_accent("".join([name_3, name_2, name_1])).
                                   replace(" ", ""))

    def save_pickle(self, pickle_file_dir):
        with open(pickle_file_dir, "wb") as f:
            pickle.dump(self, f)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--database_dir', type=str, default="databases/gso_gov_vn_191022.csv",
                            help="CSV file directory")
    arg_parser.add_argument('--pickle_dir', type=str, default="databases/gso_gov_vn_191022.pkl",
                            help="Pickle file directory")
    args = arg_parser.parse_args()

    database_helper = DatabaseHelper()
    database_helper.load_csv(args.database_dir)
    database_helper.save_pickle(args.pickle_dir)

    # print(database_helper.data)
    # print(database_helper.location_level)
