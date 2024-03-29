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
        #if not os.path.exists(fname):  # if the first file removed, use the current file path to instead the old file path
        if not os.access(fname, os.R_OK): # check accessibility for the file, if not, use the current file path to instead the old file path
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
    print "\t\t--exclude-file | -x <pattern>: exclude file which name is matched by pattern of wildcard"
    print "\t\t--exclude-regex | -X <pattern>: exclude file name with pattern by regular expression"
    print "\tthe priority of exclude is higher then match pattern"
#end def Usage

def ParseArgs(argv, options):
    opt_name = None
    option_names = options['option_names']
    for val in argv[1:]:
        if opt_name == None:
            if val == '--file' or val == '-f':
                opt_name = option_names[0]    # 'wildcard_file'
            elif val == '--regex' or val == '-r':
                opt_name = option_names[1]    # 'regex_file'
            elif val == '--exclude-dir':
                opt_name = option_names[2]    # 'exclude_dir'
            elif val == '--exclude-file' or val == '-x':
                opt_name = option_names[3]    # 'exclude_file'
            elif val == '--exclude-regex' or val == '-X':
                opt_name = option_names[4]    # 'exclude_regex'
            else:
                options['search_path'].extend(glob.glob(val))
            #endif val
        elif opt_name in option_names:
            options[opt_name] = val
            opt_name = None
        else:
            Usage(argv[0])
            sys.exit(1)
        #endif opt_name
    #end for

    if options['regex_file'] != None:
        options['regex_file'] = re.compile(options['regex_file'])

    if options['exclude_dir'] != None:
        options['exclude_dir'] = re.compile(options['exclude_dir'])

    if options['exclude_regex'] != None:
        options['exclude_regex'] = re.compile(options['exclude_regex'])
#end def ParseArgs

def OutputResult(mylist):
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
                        #endif print file name
                        
                        if not output_filesize:
                            print "   size: %d:" % file_size
                            output_filesize = True
                        #endif print file size
                        
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
            #end if for output blank line
        #end if for count of file
    #end for file in file_list
    return (count_same, count_dup)
#end def OutputResult

def MatchedFilesPattern(afile, options):
    if options['exclude_file'] and fnmatch.fnmatch(afile, options['exclude_file']):
        return False
    if options['exclude_regex'] and options['exclude_regex'].search(afile):
        return False

    # no wildcard_file and regex_file, assume all files
    if (options['wildcard_file'] == None and options['regex_file'] == None):
        return True

    if (options['wildcard_file'] != None and fnmatch.fnmatch(afile, options['wildcard_file'])):
        return True
    if (options['regex_file'] != None and options['regex_file'].search(afile) != None):
        return True
    return False
#end def MatchedFilesPattern

def FindDup(options, file_list):
    count_dir = 0
    count_file = 0
    for base_dir in options['search_path']:
        if not os.path.isdir(base_dir):
            print base_dir, "is not a directory, ignored"
            continue
        #endif isdir
        
        for root, dirs, files in os.walk(base_dir):
            count_dir = count_dir + 1
            if options['exclude_dir'] != None and options['exclude_dir'].search(root) != None:   # found directory root in exclude dirs pattern
                continue
            for afile in files:
                count_file = count_file + 1
                # file does not in wildcard pattern and regex pattern
                if not MatchedFilesPattern(afile, options):
                    continue
                if not os.access(join(root, afile), os.R_OK): # if the file cannot be access, skip it
                    continue
                if not file_list.has_key(afile):
                    file_list[afile] = {}
                AddFileProp(file_list[afile], root, afile)
            #end for afile in files
        # end for in os.walk
    #end for in search path list
    return (count_dir, count_file)
#end def FindDup
    
def main(argc, argv):
    if argc <= 1:
        Usage(argv[0])
        sys.exit(1)

    options = {}
    options['search_path'] = []
    options['option_names'] = ('wildcard_file', 'regex_file', 'exclude_dir', 'exclude_file', 'exclude_regex')
    for name in options['option_names']:
        options[name] = None

    ParseArgs(argv, options)
    
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

    print "\nfind duplicate file in:\n", options['search_path'], "\n"

    t_start = time.clock()
    (count_dir, count_file) = FindDup(options, file_list)
    t_end = time.clock()

    (count_same, count_dup) = OutputResult(file_list)

    print "\nfind end, using time: %f" % (t_end - t_start)
    print "search in %d dirs, found %d file(s) with same name in %d files, and %d file(s) duplicate\n" % (count_dir, count_same, count_file, count_dup)
#end def main

main(len(sys.argv), sys.argv)
