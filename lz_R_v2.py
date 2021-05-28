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
            self.table[literal] = collections.deque([index], maxlen=3000)


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
                match_length, offset = self.iterate(text, index, pos, best_match_length)
                if offset == match_length == 0:
                    break
                if match_length > best_match_length:
                    match_found = True
                    best_match_length = match_length
                    best_offset = offset
                    if best_match_length >= 65535:
                        break

        return match_found, best_match_length, best_offset

    def iterate(self, text, match_index, literal_index, best_length):
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
        self.it = 0
        blocks = bytearray()
        last_match = 0
        LZ4.LENGTH = len(text)
        while self.it < LZ4.LENGTH:
            literal = text[self.it:self.it + 4]
            match_found, match_length, offset = self.find_best(text, literal, self.it)
            if match_found: # match found
                if 10 < len(self.table.table):
                    for k in range(4):
                        literal_next = text[self.it+1:self.it+ 5]
                        match_found, match_length_next, offset_next = self.find_best(text, literal_next, self.it + 1)
                        # if match at next position is better take it instead of this
                        if match_length_next > match_length:
                            self.table.add(literal, self.it)
                            self.it += 1
                            match_length = match_length_next
                            offset = offset_next
                            literal = literal_next
                        else:
                            break
                # print('Match found with length', match_length, 'and offset', offset)
                LZ4.createBlock(blocks, text[last_match:self.it], self.it - last_match, match_length, offset)
                self.table.add(literal, self.it) # remove line to increase speed
                # remove for increased speed, but less compression
                for blockByte in range(self.it, match_length + self.it, 1):
                    self.table.add(text[blockByte:blockByte + 4], blockByte)
                self.it += match_length
                last_match = self.it
            else:
                self.table.add(literal, self.it)
                self.it += 1

        LZ4.createBlock(blocks, text[last_match:self.it], self.it - last_match, 0, 0, last_block=True)
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

    def readToken(self, code):
        self.literalLength = code[self.it] >> 4 # 4 highest bits
        self.matchLength = code[self.it] & 0x0F # 4 lowest bits

        self.it += 1

    def readLiteral(self, code):
        literal = code[self.it:self.it + self.literalLength]
        self.it += self.literalLength
        #print('Literal found:', literal)
        return literal

    def readLiteralLenght(self, code):
        self.literalLength = self.readLSIC(code, self.literalLength)
        #print('Literal length:', self.literalLength)


    def readMatchLength(self, code):
        self.matchLength = self.readLSIC(code, self.matchLength) + LZ4.MIN_MATCH_LENGTH
        #print('Match length:', self.matchLength)

    def readOffset(self, code):
        higher = code[self.it + 1]
        lower = code[self.it]
        #print('Offset hex:', code[self.it:self.it + 1])
        self.offset = (higher << 8) + lower
        self.it += 2
        #print('Offset:', self.offset)

    def readLSIC(self, code, initialLength):
        length = initialLength
        currentByte = initialLength
        # 15 == 4 bits
        if currentByte >= 15:
            currentByte = code[self.it]
            # 8 bits
            while currentByte >= 255:
                length += currentByte
                self.it += 1
                currentByte = code[self.it]

            length += currentByte
            self.it += 1 # next block

        return length

    def readMatch(self, text):
        #print('Text Length:', len(text))
        #print('Offset:', self.offset)
        initialLength = len(text)
        # begin representes where the match starts
        pos = initialLength - self.offset
        # match distance is the distance of begin to the end of text
        distance = initialLength - pos
        # preacollate
        text +=  b"0" * self.matchLength
        if distance < self.matchLength:
            for i in range(self.matchLength):
                text[initialLength + i] = text[pos + i]
        else:
            text[initialLength:] = text[pos:pos + self.matchLength]



    def decompress(self, code):
        self.it = 0
        text = bytearray()
        LZ4.LENGTH = len(code)
        while self.it < LZ4.LENGTH:
            self.readToken(code)
            #print('It:', self.it)
            self.readLiteralLenght(code)
            #print('It:', self.it)
            literal = self.readLiteral(code)
            #print('It:', self.it)
            text += literal
            if self.it < LZ4.LENGTH : # in case it is the last token
                self.readOffset(code)
                #print('It:', self.it)
                self.readMatchLength(code)
                #print('It:', self.it)
                # add
                self.readMatch(text)



        return text









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
        #print('Compressed correctly:', text == encoder.decompress(code))
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
