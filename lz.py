import lz4.frame as frame
import sys



class LZ4:

    ENCODE_EXT = '.lz4'
    DECODE_EXT = '_decoded'

    def compress(self, text):
        return text

    def decompress(self, code):
        return code




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
