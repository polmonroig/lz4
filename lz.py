import sys

class LZ4:

    ENCODE_EXT = '.lz4'

    MIN_MATCH_LENGTH = 4

    MINIMUM_LENGTH = 4
    GOOD_ENOUGH_SIZE = 64
    MAX_OFFSET = 65535 # 2 BYTES = 65535

    LENGTH = 0

    def __init__(self):
        self.literalLength = 0
        self.matchLength = 0
        self.offset = 0
        self.it = 0
        self.table = {}


    def compress(self, text):
        text_length = len(text)
        iterator = 0
        blocks = bytearray()
        last_match = 0
        table = {}

        while iterator < text_length:
            # get next literal
            literal_end = iterator + 8
            literal = text[iterator:literal_end]
            # if literal in table
            if literal in table:
                # get match
                match_start = table[literal]
                # calculate the offset
                offset = iterator - match_start
                # continue if offset is within range
                if offset <= 65535:
                    match_index = match_start + 8
                    # get longest match length
                    while literal_end < text_length and text[match_index] == text[literal_end]:
                        match_index += 1
                        literal_end += 1

                    length = match_index - match_start
                    LZ4.createBlock(blocks, text[last_match:iterator], iterator - last_match, length, offset)
                    iterator += length
                    last_match = iterator
                # skip match
                else:
                    table[literal] = iterator
                    iterator += 1
            # skip match
            else:
                table[literal] = iterator
                iterator += 1


        LZ4.createBlock(blocks, text[last_match:iterator], iterator - last_match, 0, 0, last_block=True)
        return blocks

    @staticmethod
    def writeVariableLength(length):
        blocks = bytearray()
        count = length // 255 # how many 255 we have
        blocks += b"\xff" * count
        # add last block
        blocks.append(int(length % 255)) # append final byte

        return blocks

    @staticmethod
    def createBlock(blocks, literal, literal_length, match_length, offset, last_block=False):
        # literal = bytes(literal, 'utf-8')
        #literal_length = len(literal)
        # codify token
        token = 0
        match_length -= 4
        if match_length < 15:
            token += match_length
        else:
            token += 15
        if last_block:
            token = 0
        if literal_length < 15:
            token += literal_length << 4
        else:
            token += 15 << 4

        blocks.append(token)
        if literal_length >= 15:
            blocks += LZ4.writeVariableLength(literal_length - 15)
        blocks += literal
        if not last_block:
            blocks.append(offset & 0x00FF)
            blocks.append(offset >> 8)
        if match_length >= 15:
            blocks += LZ4.writeVariableLength(match_length - 15)

    # DECOMPRESSION

    @staticmethod
    def readVariableLength(iterator, code):
        length = 15
        s = 255
        while s == 255:
            s = code[iterator]
            iterator += 1
            length += s

        return length, iterator



    def decompress(self, code):
        iterator = 0
        out = bytearray()
        LZ4.LENGTH = len(code)
        while iterator != LZ4.LENGTH:
            # first read token
            token = code[iterator]
            # increment iterator
            iterator += 1
            # read literal length
            length = token >> 4
            # read literals
            if length == 15:
                length, iterator = LZ4.readVariableLength(iterator, code)
            out += code[iterator:iterator + length]
            iterator += length
            # after literal always check if we are in the last block

            if iterator == LZ4.LENGTH:
                break
            # read offset
            offset = code[iterator] + (code[iterator + 1] << 8)
            iterator += 2
            # read match length
            length = token & 0x0F
            # read matches
            if length == 15:
                length, iterator = LZ4.readVariableLength(iterator, code)
            # always add 4 to length (MINMATCH)
            length += 4
            # read match
            initialLength = len(out)
            # begin representes where the match starts
            pos = initialLength - offset
            # match distance is the distance of begin to the end of text
            distance = initialLength - pos
            # preacollate
            out +=  b"0" * length
            if distance < length:
                for i in range(length):
                    out[initialLength + i] = out[pos + i]
            else:
                out[initialLength:] = out[pos:pos + length]


        return out






def main():
    # create instance on encoder
    encoder = LZ4()
    # if we don't have enough argumemts return
    if len(sys.argv) < 3:
        print('Not enough arguments provided')
    # if we want to compress we read the specific file
    elif sys.argv[1] == '-c':
        file = sys.argv[2]
        fd = open(file, 'rb')
        print('Compressing file', file)
        # read file and encode
        text = fd.read()
        code = encoder.compress(text)
        print('Ratio:', len(text) / len(code))
        # create new file
        with open(file + LZ4.ENCODE_EXT, 'wb') as out:
            out.write(code)
        fd.close()
    # if we want to decompress we read the specific file
    elif sys.argv[1] == '-d':
        file = sys.argv[2]
        fd = open(file, 'rb')
        print('Decompressing file', file)
        text = encoder.decompress(fd.read())
        # create new file
        with open(".".join(file.split('.')[:-1]), 'wb') as out:
            out.write(text)
        fd.close()
    # if the command specified is unknown skip
    else:
        print('Unknown command', sys.argv[1])






if __name__ == "__main__":
    main()
    #cProfile.run('main()')
