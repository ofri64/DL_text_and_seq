import re
from collections import OrderedDict

PADD = "PADD"
UNK = "UNK"
BEGIN = "<>"
END = "</>"
START_LINE = "-DOCSTART-"


class BaseMapper(object):
    """
    Class for mapping discrete tokens in a training set
    to indices and back
    """

    def __init__(self, min_frequency: int = 0, split_char="\t"):
        self.min_frequency = min_frequency
        self.split_char = split_char
        self.token_to_idx = {}
        self.idx_to_token = {}
        self.label_to_idx = {}
        self.idx_to_label = {}

    def serialize(self) -> dict:
        return {
            "min_frequency": self.min_frequency,
            "token_to_idx": self.token_to_idx,
            "label_to_idx": self.label_to_idx,
            "idx_to_token": self.idx_to_token,
            "idx_to_label": self.idx_to_label
        }

    @classmethod
    def deserialize(cls, serialized_mapper: dict):
        mapper = cls()

        mapper.min_frequency = serialized_mapper["min_frequency"]
        mapper.token_to_idx = serialized_mapper["token_to_idx"]
        mapper.label_to_idx = serialized_mapper["label_to_idx"]
        mapper.idx_to_token = serialized_mapper["idx_to_token"]
        mapper.idx_to_label = serialized_mapper["idx_to_label"]

        return mapper

    def get_tokens_dim(self) -> int:
        return len(self.token_to_idx)

    def get_labels_dim(self) -> int:
        return len(self.label_to_idx)

    def create_mapping(self, filepath: str) -> None:
        raise NotImplementedError("A concrete mapper class needs to implement create_mapping method ")

    def get_token_idx(self, raw_token: str) -> int:
        raise NotImplementedError("A concrete mapper class needs to implement get_token_idx method ")

    def get_label_idx(self, raw_label: str) -> int:
        raise NotImplementedError("A concrete mapper class needs to implement get_label_idx method ")


class TokenMapper(BaseMapper):
    """
    Class for mapping discrete tokens in a training set
    to indices and back
    """
    def __init__(self, min_frequency: int = 0, split_char="\t"):
        super().__init__(min_frequency, split_char)

    @classmethod
    def deserialize(cls, serialized_mapper: dict):
        return BaseMapper.deserialize(serialized_mapper)

    def _init_mappings(self) -> None:
        self.token_to_idx[UNK] = 0
        self.idx_to_token[0] = UNK

    def _remove_non_frequent(self, words_frequencies) -> dict:
        # remove word below min_frequency
        words = OrderedDict()
        for word, frequency in words_frequencies.items():
            if frequency >= self.min_frequency:
                words[word] = 0

        return words

    def create_mapping(self, filepath: str) -> None:
        words_frequencies = OrderedDict()
        labels = OrderedDict()

        with open(filepath, "r", encoding="utf8") as f:
            for line in f:

                # skip start of document
                if line.startswith(START_LINE):
                    continue
                # skip empty line (end of sentence_
                if line == "\n":
                    continue

                else:
                    line_tokens = line[:-1].split(self.split_char)  # remove end of line
                    word = line_tokens[0]
                    label = line_tokens[1]

                    words_frequencies[word] = words_frequencies.get(word, 0) + 1
                    labels[label] = 0

        # remove word below min_frequency
        words = self._remove_non_frequent(words_frequencies)

        # init mappings with padding and unknown indices
        self._init_mappings()

        # start index will be different if index 0 marked already as padding
        word_start_index = len(self.token_to_idx)
        label_start_index = len(self.label_to_idx)

        # transform token to indices
        for index, word in enumerate(words.keys(), word_start_index):
            self.token_to_idx[word] = index
            self.idx_to_token[index] = word

        for index, label in enumerate(labels.keys(), label_start_index):
            self.label_to_idx[label] = index
            self.idx_to_label[index] = label

    def get_token_idx(self, raw_token: str) -> int:
        # usual case - word appears in mapping dictionary (seen in train)
        if raw_token in self.token_to_idx:
            return self.token_to_idx[raw_token]

        # if word doesn't appear - assign the index of unknown
        return self.token_to_idx[UNK]

    def get_label_idx(self, raw_label: str) -> int:
        return self.label_to_idx[raw_label]


class TokenMapperUnkCategory(TokenMapper):
    def __init__(self, min_frequency: int = 0, split_char="\t"):
        super().__init__(min_frequency, split_char=split_char)
        self.unk_categories = {
            'twoDigitNum': lambda w: len(w) == 2 and w.isdigit() and w[0] != '0',
            'fourDigitNum': lambda w: len(w) == 4 and w.isdigit() and w[0] != '0',
            'containsDigitAndAlpha': lambda w: bool(re.search('\d', w)) and bool(re.search('[a-zA-Z_]', w)),
            'containsDigitAndDash': lambda w: self._contains_digit_and_char(w, '-'),
            'containsDigitAndSlash': lambda w: self._contains_digit_and_char(w, '/'),
            'containsDigitAndComma': lambda w: self._contains_digit_and_char(w, ','),
            'containsDigitAndPeriod': lambda w: self._contains_digit_and_char(w, '.'),
            'otherNum': lambda w: w.isdigit(),
            'allCaps': lambda w: w.isupper(),
            'capPeriod': lambda w: len(w) == 2 and w[1] == '.' and w[0].isupper(),
            'initCap': lambda w: len(w) > 1 and w[0].isupper(),
            'lowerCase': lambda w: w.islower(),
            'punkMark': lambda w: w in (",", ".", ";", "?", "!", ":", ";", "-", '&'),
            'containsNonAlphaNumeric': lambda w: bool(re.search('\W', w)),
            '%PerCent%': lambda w: len(w) > 1 and w[0] == '%' and w[1:].isdigit()
        }

    @staticmethod
    def _contains_digit_and_char(word, ch) -> bool:
        return bool(re.search('\d', word)) and ch in word

    def _init_mappings(self) -> None:

        # init mappings with BEGIN and END symbols
        self.token_to_idx[BEGIN] = 0
        self.idx_to_token[0] = BEGIN
        self.token_to_idx[END] = 1
        self.idx_to_token[1] = END

        # continue with initiating unknown mappings
        self._init_unknown_mappings()

    def _init_unknown_mappings(self) -> None:
        current_index = len(self.token_to_idx)
        for category in self.unk_categories.keys():
            self.token_to_idx[category] = current_index
            self.idx_to_token[current_index] = category
            current_index += 1

        # add UNK as final fallback
        self.token_to_idx[UNK] = current_index
        self.idx_to_token[current_index] = UNK
        current_index += 1

    def get_token_idx(self, raw_token: str) -> int:
        # usual case - word appears in mapping dictionary (seen in train)
        if raw_token in self.token_to_idx:
            return self.token_to_idx[raw_token]

        # if the word doesn't appear - try to find a "smart" unknown pattern
        unknown_categories: dict = self.unk_categories
        for category, cond_func in unknown_categories.items():
            if cond_func(raw_token):
                return self.token_to_idx[category]

        # cannot find a smart unknown pattern - return index of general unknown
        return self.token_to_idx[UNK]
