import os
import re
import yaml
from Ska.Shell import bash
from Ska.File import chdir

# If content in these fields is present in the input yaml, it should be preserved
SAVE_FIELDS = ['title', 'aca_cl_id', 'notes', 'hopper', 'exclude']


def get_options():
    import argparse
    parser = argparse.ArgumentParser(
        description="Get starcheck checks")
    parser.set_defaults()
    parser.add_argument("scdir",
                        help="starcheck git repo directory")
    parser.add_argument("--infile",
                        default="checks.yaml",
                        help="file of checks (output from previous run of tool)")
    parser.add_argument("--outfile",
                        default="checks.yaml")
    args = parser.parse_args()
    return args


def get_dir_version(dirname):
    """
    Get git revision of the supplied repo dir
    Print a warning if the try looks dirty.
    """
    with chdir(dirname):
        changes = int(bash("git diff-index --quiet HEAD ; echo $?")[0])
        if changes != 0:
            print "Warning: {} has changes and git version may not map to code".format(dirname)
        return bash("git rev-parse HEAD")[0]


def get_single_warn(fname, ftext, idx, context_range=[-15, 10]):
    """
    Extra the context and text of a warning

    :param fname: file name with code and warning lines
    :param ftext: the text lines of that file
    :param idx: line index of a warning
    :param context_range: lines back and forward of idx to fetch for context
    :return: dictionary of the warning
    """
    warn_text = []
    for fline in ftext[idx:]:
        warn_text.append(fline.strip())
        if re.search(";", fline):
            break
    min_line = max(idx + context_range[0], 0)
    max_line = min(idx + context_range[1], len(ftext) - 1)
    context_lines = [line.strip() for line in ftext[min_line:max_line]]
    context_lines.insert(abs(context_range[0]), "# XXXXXXXXXXXXX MARKED WARNING XXXXXXXXXXXXX")
    context_lines.insert(abs(context_range[0]) + 2, "# XXXXXXXXXXXXX MARKED WARNING XXXXXXXXXXXXX")
    context = "\n".join(context_lines)
    return {'filename': fname,
            'line_number': idx,
            'text': warn_text,
            'context': context}


def get_sc():
    """
    For a list of source files, get all the indexes of lines that match
    standard warning patterns, and fetch the context about and warning that starts
    with the matching line.
    """
    perl_files = ['src/starcheck.pl',
                  'src/lib/Ska/Starcheck/Obsid.pm',
                  'src/lib/Ska/Starcheck/FigureOfMerit.pm',
                  'src/lib/Ska/Parse_CM_File.pm']
    checks = []
    for f in perl_files:
        text = open(f).readlines()
        for idx, line in enumerate(text):
            if re.match("^\s*#", line):
                continue
            if (re.search('[^\$]warning\s*\(', line)
                or re.search("\$warn\s*=", line)
                or re.search("push @\S*warn", line)
                or re.search("push @\{\$error\}", line)
                ):
                   checks.append(get_single_warn(f, text, idx))
    return checks


def add_github_urls(checks, sha):
    """
    Given the array of warnings/checks, determine the github URL and add to the
    per-warning dict.
    """
    url = "https://github.com/sot/starcheck/blob/"
    for check in checks:
        check['github_url'] = "{url}{sha}/{filename}#L{idx}".format(
            url=url, filename=check['filename'], sha=sha, idx=check['line_number'] + 1)


def copy_manual_fields(c, pc):
    """
    Copy the manually-entered fields from a previous file into new output.
    """
    for field in SAVE_FIELDS:
        if field in pc.keys():
            c[field] = pc[field]
            pc['copied'] = 1


def preserve_manual_content(checks, previous_checks):
    """
    For each new check, see if it was in a previous version of the output
    and call the routine to copy over manual content.
    """
    for c in checks:
        for pc in previous_checks:
            if pc['text'] == c['text']:
                pc['has_match'] = 1
                copy_manual_fields(c, pc)


def confirm_no_lost_checks(checks, previous_checks):
    """
    Check that no warnings/checks went missing.
    """
    for pc in previous_checks:
        if 'has_match' not in pc:
            raise ValueError("test {} is now missing".format(pc['text']))


def main(opt):
    scversion = get_dir_version(opt.scdir)
    with chdir(opt.scdir):
        checks = get_sc()
    add_github_urls(checks, scversion)
    if os.path.exists(opt.infile):
        previous_checks = yaml.load(open(opt.infile).read())
        preserve_manual_content(checks, previous_checks)
        confirm_no_lost_checks(checks, previous_checks)
    open(opt.outfile, 'w').write(yaml.dump(checks, default_style="|"))


if __name__ == '__main__':
    opt = get_options()
    main(opt)
