class LaptimeParser(object):
    @classmethod
    def is_valid(cls, filename, data):
        return False

    @classmethod
    def parse_data(cls, data):
        raise NotImplemented("Parse needs to implement parse_data()")




from harrys_csv import HarrysCSVParser

parsers = [HarrysCSVParser]

def find_parser(filename, filedata):
    for parser in parsers:
        if parser.is_valid(filename, filedata):
            # Take the first parser that passes
            return parser
