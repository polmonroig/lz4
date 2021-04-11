from lz4 import LZ4
import sys





def main():
    # create instance on encoder
    encoder = LZ4()
    # if we don't have enough argumemts return
    if len(sys.argv) < 3:
        print('Not enough arguments provided')
    # if we want to compress we read the specific file
    elif sys.argv[1] == '-c':
        file = sys.argv[2]
        fd = open(file, 'r')
        print('Compressing file', file)
        code = encoder.encode(fd.read())
        fd.close()
    # if we want to decompress we read the specific file
    elif sys.argv[1] == '-d':
        file = sys.argv[2]
        fd = open(file, 'r')
        print('Decompressing file', file)
        text = encoder.decode(fd.read())
        fd.close()
    # if the command specified is unknown skip
    else:
        print('Unknown command', sys.argv[1])







if __name__ == '__main__':
    main()
