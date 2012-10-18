#!/bin/python

import os, sys
import fnmatch, re
import glob, time
import binascii, hashlib
from os.path import join, getsize

def hashfile(fname, blocksize=65536):
    hasher = hashlib.md5()
    afile = open(fname, 'r')
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    afile.close()
    return hasher.digest()
#end def hashfile

def AddFileProp(fprops, root, file):
    if len(fprops) == 0:  # first file, initialize dict
        fprops['count'] = 1
        fprops['props'] = {}
        file_size = -1    # ignore file size for the first file
    else:
        fprops['count'] += 1
        file_size = getsize(join(root, file))    # use file size as the key of dict
        
    props = fprops['props']
    if file_size == -1:
        props['fake_size'] = {}
        props['fake_size']['md5_dummy'] = [root]
        return

    # get file info while found different file with same name
    if fprops['count'] == 2:
        tmp_prop = props['fake_size']
        #fname = join(base_dir + tmp_prop['md5_dummy'][0], file)    # use file size as the key of dict
        fname = join(tmp_prop['md5_dummy'][0], file)    # use file size as the key of dict
        if os.path.exists(fname):  # if the first file removed, use the current file path to instead the old file path
            tmp_prop['md5_dummy'][0] = root
            return

        f_size = getsize(fname)    # use file size as the key of dict
        props[f_size] = {}   # set the real file size for the first file
        md5 = hashfile(fname)
        props[f_size][md5] = tmp_prop['md5_dummy']
        del props['fake_size']
        
        props[file_size] = {} # prepare for current file
    elif not props.has_key(file_size):
        props[file_size] = {} # prepare for current file
    else:
        pass
        
    md5 = hashfile(join(root, file))
    tmp_prop = props[file_size]
    if not tmp_prop.has_key(md5):
        tmp_prop[md5] = [root]
    else:
        tmp_prop[md5].append(root)
#end def AddFileProp

def Usage(prog):
    print "Usage: \n\t%s <dir[,dir[,dir[,...]]] [options]" % prog
    print "\t    options:"
    print "\t\t--file | -f <pattern>: pattern of wildcard file name"
    print "\t\t--regex | -r <pattern>: match file name with pattern by regular expression"
    print "\t\t--exclude-dir <pattern>: exclude dirs's name with pattern by regular expression"
#end def Usage

def main(argc, argv):
    if argc <= 1:
        Usage(argv[0])
        sys.exit(1)

    search_path = []
    wildcard_fname = None
    regex_fname = None
    exclude_dir = None

    print "\nfind duplicate file in"
    opt = 0
    for val in argv[1:]:
        if opt == 1:
            wildcard_fname = val
            opt = 0
        elif opt == 2:
            regex_fname = val
            opt = 0
        elif opt == 3:
            exclude_dir = val
            opt = 0
        elif opt == 0:
            if val == '--file' or val == '-f':
                opt = 1
                continue
            elif val == '--regex' or val == '-r':
                opt = 2
                continue
            elif val == '--exclude-dir':
                opt = 3
                continue
            else:
                search_path.extend(glob.glob(val))
            #endif val
        #endif opt
    #end for

    #for idx, val in enumerate(search_path):
    #for val in search_path:
    #    search_path[idx] = os.path.normpath(val)
    #    val = search_path[idx]
    #    if not os.path.isdir(val):
    #        print "   *** error:", val, "is not a directory"
    #        sys.exit(1)
    #    print "  ", val
    #print

    '''
    full_props: { file_name,    # file_name as key
                  file_count, 
                  file_props: { file_size,  # file_size as key
                                props_for_a_file: { md5,    # md5 signature as key 
                                                    path: []
                                                  }
                              }
                }

    '''

    file_list = {}

    count_dir = 0
    count_file = 0

    reobj_fname = None
    if regex_fname != None:
        reobj_fname = re.compile(regex_fname)

    reobj_exdir = None
    if exclude_dir != None:
        reobj_exdir = re.compile(exclude_dir)
        
    t_start = time.clock()

    for base_dir in search_path:
        if not os.path.isdir(base_dir):
            print base_dir, "is not a directory, ignored"
            continue
        for root, dirs, files in os.walk(base_dir):
            count_dir = count_dir + 1
            if reobj_exdir != None and reobj_exdir.search(root) != None:   # root is in exclude dirs pattern
                continue
            for afile in files:
                count_file = count_file + 1
                if wildcard_fname != None and not fnmatch.fnmatch(afile, wildcard_fname): # file is not in wildcard pattern
                    continue
                if reobj_fname != None and reobj_fname.match(afile) == None: # file is not in regex pattern
                    continue
                if not file_list.has_key(afile):
                    file_list[afile] = {}
                AddFileProp(file_list[afile], root, afile)
            #end for in files
        # end for in os.walk
    #end for in search path list

    t_end = time.clock()

    mylist = file_list
    count_same = 0
    count_dup = 0
    for file_name in mylist:
        count_same += 1
        full_props = mylist[file_name]
        count_of_file = full_props['count']
        file_props = full_props['props']
        # skip if only one file for a name or every file size are different, it's means no dupplicate files
        if count_of_file > 1 and count_of_file != len(file_props):
            output_filename = False
            for file_size in file_props:   # get file size for every file with same name
                props_for_a_file = file_props[file_size]
                output_filesize = False
                for md5 in props_for_a_file:    # get md5 signature for every file with same size
                    if len(props_for_a_file[md5]) > 1: # skip if only one file with a md5
                        count_dup += 1
                        if not output_filename:
                            print file_name, ":"
                            output_filename = True
                        if not output_filesize:
                            print "   size: %d:" % file_size
                            output_filesize = True
                            
                        print "      md5:", binascii.b2a_hex(md5)
                        for path in props_for_a_file[md5]:
                            print "          %s" % path
                            # TODO:
                            #   print latest modified date
                            #   print metadata
                        #end for in path dict
                    #end if for length of md5 dict
                #end for in md5 dict
            #end for in file size
            if output_filename:
                print
        #end if for count of file
    #end for in file name dict

    print "\nfind end, using time: %f" % (t_end - t_start)
    print "search in %d dirs, found %d file(s) with same name in %d files, and %d file(s) duplicate\n" % (count_dir, count_same, count_file, count_dup)
#end def main

main(len(sys.argv), sys.argv)
