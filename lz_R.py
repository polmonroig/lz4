import collections
import sys
import cProfile


class LinkedHashTable:

    MAX_TABLE_SIZE = 8000000
    QUEUE_SIZE = 5000

    def __init__(self):
        self.table = {}

    def find(self, literal):
        if literal in self.table:
            return self.table[literal]
        return None

    def add(self, literal, index):
        if literal in self.table:
            # important, it is faster to append left, this way we don't have to
            # iterate matche in reverse order. It has a O(1) time complexity
            self.table[literal].appendleft(index)
        else:
            self.table[literal] = collections.deque([index], maxlen=20000)


class LZ4:

    ENCODE_EXT = '.lz4'

    MIN_MATCH_LENGTH = 4

    MINIMUM_LENGTH = 4
    GOOD_ENOUGH_SIZE = 1024
    MAX_OFFSET = 65535 # 2 BYTES = 65535

    def __init__(self):
        self.literalLength = 0
        self.matchLength = 0
        self.offset = 0
        self.it = 0
        self.table = LinkedHashTable()


    def find_best(self, text, literal, pos):
        match_indices = self.table.find(literal)
        best_match_length = 3
        best_offset = -1
        match_found = False
        if match_indices is not None:
            for index in match_indices:
                match_length, offset = LZ4.iterate(text, index, pos, best_match_length)
                if offset == match_length == 0:
                    break
                if match_length > best_match_length:
                    match_found = True
                    best_match_length = match_length
                    best_offset = offset
                    if best_match_length >= 65535:
                        break

        return match_found, best_match_length, best_offset

    @staticmethod
    def iterate(text, match_index, literal_index, best_length):
        match_length = 4
        offset = literal_index - match_index
        if offset > 65535 :
            return 0, 0
        left_index = match_index + best_length
        right_index = literal_index + best_length
        if right_index < LZ4.LENGTH and text[left_index]  != text[right_index]:# this is a worse candidate
            return -1, -1
        k = match_index + 4
        j = literal_index + 4
        # search buffer

        while j < LZ4.LENGTH and text[j] == text[k]:
            j += 1
            k += 1
        # adding k - match_length instead of match_length += 1 improves
        # speed by a little
        return k - match_index, offset


    def compress(self, text):
        iterator = 0
        blocks = bytearray()
        last_match = 0
        LZ4.LENGTH = len(text)
        while iterator < LZ4.LENGTH:
            literal = text[iterator:iterator + 4]
            match_found, match_length, offset = self.find_best(text, literal, iterator)
            if match_found: # match found
                for k in range(5):
                    literal_next = text[iterator+1:iterator+ 5]
                    match_found, match_length_next, offset_next = self.find_best(text, literal_next, iterator + 1)
                    # if match at next position is better take it instead of this
                    if match_length_next > match_length:
                        self.table.add(literal, iterator)
                        iterator += 1
                        match_length = match_length_next
                        offset = offset_next
                        literal = literal_next
                    else:
                        break
                # print('Match found with length', match_length, 'and offset', offset)
                LZ4.createBlock(blocks, text[last_match:iterator], iterator - last_match, match_length, offset)
                self.table.add(literal, iterator) # remove line to increase speed
                # remove for increased speed, but less compression
                for blockByte in range(iterator, match_length + iterator, 1):
                    self.table.add(text[blockByte:blockByte + 4], blockByte)
                iterator += match_length
                last_match = iterator
            else:
                self.table.add(literal, iterator)
                iterator += 1

        LZ4.createBlock(blocks, text[last_match:iterator], iterator - last_match, 0, 0, last_block=True)
        return blocks

    @staticmethod
    def writeLSIC(length):
        blocks = bytearray()
        count = int(length / 255) # how many 255 we have
        blocks += b"\xff" * count
        # add last block
        blocks.append(int(length % 255)) # append final byte

        return blocks

    @staticmethod
    def createBlock(blocks, literal, literal_length, match_length, offset, last_block=False):
        # literal = bytes(literal, 'utf-8')

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
            blocks += offset.to_bytes(2, 'little')
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
