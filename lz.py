import sys





def main():

    if len(sys.argv) < 3:
        print('Not enough arguments provided')
    elif sys.argv[1] == '-c':
        file = sys.argv[2]
        fd = open(file, 'r')
        print('Compressing file', file)
        fd.close()
    elif sys.argv[1] == '-d':
        file = sys.argv[2]
        fd = open(file, 'r')
        print('Decompressing file', file)
        fd.close()
    else:
        print('Unknown command', sys.argv[1])







if __name__ == '__main__':
    main()
