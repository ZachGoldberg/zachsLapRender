class LaptimeParser(object):
    @classmethod
    def is_valid(cls, filename):
        return False

    @classmethod
    def parse_data(cls, datafile):
        raise NotImplemented("Parse needs to implement parse_data()")




from harrys_csv import HarrysCSVParser

parsers = [HarrysCSVParser]

def find_parser(filename):
    for parser in parsers:
        if parser.is_valid(filename):
            # Take the first parser that passes
            return parser
