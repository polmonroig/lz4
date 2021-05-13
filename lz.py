from tqdm import tqdm
import collections
import sys



class LinkedHashTable:

    MAX_TABLE_SIZE = 8000000

    def __init__(self):
        self.table = collections.OrderedDict()

    def find(self, literal):
        if literal in self.table:
            value = self.table[literal]
            self.table.move_to_end(literal)
            return value
        else:
            return None


    def add(self, literal, index):
        if literal in self.table:
            self.table[literal].append(index)
        else:
            self.table[literal] = [index]
        self.table.move_to_end(literal)
        if len(self.table) > LinkedHashTable.MAX_TABLE_SIZE:
            self.table.popitem(last = False)
            # print("full")

class LZ4:

    ENCODE_EXT = '.lz4'

    MIN_MATCH_LENGTH = 4

    MINIMUM_LENGTH = 4
    GOOD_ENOUGH_SIZE = 512
    MAX_OFFSET = 65535 # 2 BYTES = 65535

    def __init__(self):
        self.literalLength = 0
        self.matchLength = 0
        self.offset = 0
        self.it = 0
        self.table = LinkedHashTable()

    def find_best(self, text, literal):
        match_indices = self.table.find(literal)
        best_match_length = LZ4.MINIMUM_LENGTH - 1
        best_offset = -1
        match_found = False
        if match_indices is not None:
            for index in reversed(match_indices):
                match_length, offset = self.iterate(text, index, self.it, best_match_length)
                if offset == match_length == 0:
                    break 
                if match_length > best_match_length:
                    match_found = True
                    best_match_length = match_length
                    best_offset = offset
                #if best_match_length >= GOOD_ENOUGH_SIZE:
                #    break

        return match_found, best_match_length, best_offset

    def iterate(self, text, match_index, literal_index, best_length):
        match_length = LZ4.MINIMUM_LENGTH
        offset = literal_index - match_index
        if offset > LZ4.MAX_OFFSET:
            return 0, 0
        left_index = match_index + best_length 
        right_index = literal_index + best_length  
        if right_index < len(text) and text[left_index]  != text[right_index]:# this is a worse candidate 
            return -1, -1 
        k = match_index + LZ4.MINIMUM_LENGTH
        j = literal_index + LZ4.MINIMUM_LENGTH
        # search buffer
        while j < len(text) and text[j] == text[k]:
            j += 1
            k += 1
            match_length += 1

        return match_length, offset

    def compress(self, text):
        self.it = 0
        blocks = bytearray()
        last_match = 0
        with tqdm(total=len(text)) as pbar:
            while self.it < len(text):
                #print('=================================')
                #print('Search ', chr(text[i]))
                #print('Text:', text[i:])
                #print('Search buffer:', "".join([chr(i)for i in searchBuffer]))
                #print('Code:', blocks)
                literal = text[self.it:self.it + LZ4.MINIMUM_LENGTH]
                match_found, match_length, offset = self.find_best(text, literal)

                if match_found: # match found

                    # print('Match found with length', match_length, 'and offset', offset)
                    LZ4.createBlock(blocks, text[last_match:self.it], match_length, offset)
                    self.table.add(literal, self.it) # remove line to increase speed
                    # remove for increased speed, but less compression
                    self.it += match_length
                    pbar.update(match_length)
                    last_match = self.it
                else:
                    self.table.add(literal, self.it)
                    pbar.update(1)
                    self.it += 1

        LZ4.createBlock(blocks, text[last_match:self.it], 0, 0, last_block=True)
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
    def createBlock(blocks, literal, match_length, offset, last_block=False):
        # literal = bytes(literal, 'utf-8')
        literal_length = len(literal)
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
        pos = len(text) - self.offset
        for i in range(self.matchLength):
            text.append(text[pos + i])


    def decompress(self, code):
        self.it = 0
        text = bytearray()
        with tqdm(total=len(code)) as pbar:
            it_old = self.it
            while self.it < len(code):

                pbar.update(self.it - it_old)
                it_old = self.it
                self.readToken(code)
                #print('It:', self.it)
                self.readLiteralLenght(code)
                #print('It:', self.it)
                literal = self.readLiteral(code)
                #print('It:', self.it)
                text += literal
                if self.it < len(code): # in case it is the last token
                    self.readOffset(code)
                    #print('It:', self.it)
                    self.readMatchLength(code)
                    #print('It:', self.it)
                    # add
                    self.readMatch(text)
                    #print('It:', self.it)
                # print(offsets[k], "==", self.offset)
                #print('Block:', code[it_old:self.it])
                #print('Text:', text)


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







if __name__ == '__main__':
    main()
