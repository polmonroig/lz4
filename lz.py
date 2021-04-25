import lz4.frame as frame
import sys



class LZ4:

    ENCODE_EXT = '.lz4'
    DECODE_EXT = '_decoded'

    MIN_MATCH_LENGTH = 4

    def __init__(self):
        self.literalLength = 0
        self.matchLength = 0
        self.offset = 0
        self.it = 0

    def compress(self, text):

        return text

    def readToken(self, code):
        self.literalLength = code[self.it] >> 4 # 4 highest bits
        self.matchLength = (code[self.it] % 16)
        
        self.it += 1

    def readLiteral(self, code):
        literal = code[self.it:self.it + self.literalLength]
        self.it += self.literalLength
        # print('Literal found:', literal)
        return literal

    def readLiteralLenght(self, code):
        self.literalLength = self.readLSIC(code, self.literalLength)
        # print('Literal length:', self.literalLength)
        

    def readMatchLength(self, code):
        self.matchLength = self.readLSIC(code, self.matchLength) + LZ4.MIN_MATCH_LENGTH
        # print('Match length:', self.matchLength)

    def readOffset(self, code):
        higher = code[self.it + 1]
        lower = code[self.it]
        # print('Offset hex:', code[self.it:self.it + 1])
        self.offset = (higher << 8) + lower
        self.it += 2
        # print('Offset:', self.offset)

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
        # print('Text Length:', len(text))
        # print('Offset:', self.offset)
        pos = len(text) - self.offset
        for i in range(self.matchLength):
            text += text[pos + i].to_bytes(1, 'big') 
        

        return text


    def decompress(self, code):
        self.it = 0
        text = b""
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
                    text = self.readMatch(text)
                    #print('It:', self.it)
                # print(offsets[k], "==", self.offset)
                # print('Block:', code[it_old:self.it])
                # print('Text:', text)


        return text









def main():
    # create instance on encoder
    #encoder = LZ4()
    encoder = frame
    # if we don't have enough argumemts return
    if len(sys.argv) < 3:
        print('Not enough arguments provided')
    # if we want to compress we read the specific file
    elif sys.argv[1] == '-c':
        file = sys.argv[2]
        fd = open(file, 'rb')
        print('Compressing file', file)
        # read file and encode
        code = encoder.compress(fd.read())
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
        with open(file.split('.')[0] + LZ4.DECODE_EXT, 'wb') as out:
            out.write(text)
        fd.close()
    # if the command specified is unknown skip
    else:
        print('Unknown command', sys.argv[1])







if __name__ == '__main__':
    main()
