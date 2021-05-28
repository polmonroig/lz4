import collections
import sys
import cProfile
import itertools
import timeit

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

    def find_best(self, text, literal):
        if literal in self.table:
            match_index = self.table[literal]
            literal_index = self.it
            offset = literal_index - match_index
            if offset > 65535:
                return False, 0, 0
            k = match_index + 8
            j = literal_index + 8
            # search buffer
            while j < LZ4.LENGTH and text[j] == text[k]:
                j += 1
                k += 1
            # adding k - match_length instead of match_length += 1 improves
            # speed by a little
            return True, k - match_index, offset

        return False, 0, 0



    def compress(self, text):
        self.it = 0
        blocks = bytearray()
        last_match = 0
        LZ4.LENGTH = len(text)
        while self.it < LZ4.LENGTH:
            literal = text[self.it:self.it + 8]
            match_found, match_length, offset = self.find_best(text, literal)

            if match_found: # match found

                # print('Match found with length', match_length, 'and offset', offset)
                LZ4.createBlock(blocks, text[last_match:self.it], self.it - last_match, match_length, offset)
                #self.table.add(literal, self.it) # remove line to increase speed
                # remove for increased speed, but less compression
                #for blockByte in range(self.it, match_length + self.it, 1):
                #    self.table.add(text[blockByte:blockByte + LZ4.MINIMUM_LENGTH], blockByte)

                self.it += match_length
                last_match = self.it
            else:
                self.table[literal] = self.it
                self.it += 1

        LZ4.createBlock(blocks, text[last_match:self.it], self.it - last_match, 0, 0, last_block=True)
        return blocks

    @staticmethod
    def writeLSIC(length):
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
            blocks += LZ4.writeLSIC(literal_length - 15)
        blocks += literal
        if not last_block:
            blocks.append(offset & 0x00FF)
            blocks.append(offset >> 8)
        if match_length >= 15:
            blocks += LZ4.writeLSIC(match_length - 15)

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
            if True:
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
        print('============================================')
        print('Compressing file', file)
        # read file and encode
        text = fd.read()
        start1 = timeit.default_timer()
        code = encoder.compress(text)
        end1 = timeit.default_timer()
        print('Compression time', end1 - start1)
        print('Ratio:', len(text) / len(code))
        print('Transmission time', len(code) / 1000000)
        start2 = timeit.default_timer()
        decoded = encoder.decompress(code)
        end2 = timeit.default_timer()
        print('Decompression time', end2 - start2)
        print('Total time', (end2 - start2) + (end1 - start1) + (len(code) / 1000000))
        print('Compressed correctly:', text == decoded)
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
