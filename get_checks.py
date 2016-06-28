import os
import re
import yaml
from yaml.representer import SafeRepresenter
from Ska.Shell import bash
from Ska.File import chdir

# If content in these fields is present in the input yaml, it should be preserved
SAVE_FIELDS = ['title', 'aca_cl_id', 'notes', 'hopper', 'ignore', 'type', 'severity', 'byhand', 'missing']


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

# Add helper code to be able to print certain fields (context) as literal blocks

class literal_str(str): pass

def change_style(style, representer):
    def new_representer(dumper, data):
        scalar = representer(dumper, data)
        scalar.style = style
        return scalar
    return new_representer

represent_literal_str = change_style('|', SafeRepresenter.represent_str)
yaml.add_representer(literal_str, represent_literal_str)


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
    context_lines = [line.strip().replace("\t", "    ") for line in ftext[min_line:max_line]]
    context_lines.insert(abs(context_range[0]), "# XXXXXXXXXXXXX MARKED WARNING XXXXXXXXXXXXX")
    context_lines.insert(abs(context_range[0]) + 2, "# XXXXXXXXXXXXX MARKED WARNING XXXXXXXXXXXXX")
    context = literal_str("\n".join(context_lines))
    return {'filename': fname,
            'line_number': idx + 1,
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
        check['github_url'] = "{url}{sha}/{filename}#L{line_number}".format(
            url=url, filename=check['filename'], sha=sha, line_number=check['line_number'])


def copy_manual_fields(c, pc):
    """
    Copy the manually-entered fields from a previous file into new output.
    """
    for field in SAVE_FIELDS:
        if field in pc.keys():
            c[field] = pc[field]
            pc['copied'] = 1


def assign_ids(checks):
    prev_ids = [int(c['id']) for c in checks if 'id' in c]
    prev_max = 0
    if len(prev_ids):
        prev_max = 1 + max(prev_ids)
    no_id_checks = [c for c in checks if 'id' not in c]
    for idx, c in enumerate(no_id_checks):
        c['id'] = prev_max + idx
        print("Assigning new id {} to check {}".format(c['id'], c['text']))

def preserve_manual_content(checks, previous_checks):
    """
    For each new check, see if it was in a previous version of the output
    and call the routine to copy over manual content.
    """
    for c in checks:
        for pc in previous_checks:
            if (pc['text'] == c['text']):
                pc['has_match'] = 1
                if 'id' not in c:
                    c['id'] = pc['id']
                    copy_manual_fields(c, pc)
                else:
                    print("Conflict on id {}".format(c['id']))


def confirm_no_lost_checks(checks, previous_checks):
    """
    Check that no warnings/checks went missing.
    """
    for pc in previous_checks:
        if 'has_match' not in pc:
            # if this is a by-hand/manual addition, re-add it
            if pc['byhand']:
                checks.extend(pc)
            else:
                print("test {} is now missing".format(pc['text']))
                pc['missing'] = 1
                checks.extend(pc)


def main(opt):
    scversion = get_dir_version(opt.scdir)
    with chdir(opt.scdir):
        checks = get_sc()
    add_github_urls(checks, scversion)
    if os.path.exists(opt.infile):
        previous_checks = yaml.load(open(opt.infile).read())
        assign_ids(previous_checks)
        preserve_manual_content(checks, previous_checks)
        confirm_no_lost_checks(checks, previous_checks)
    assign_ids(checks)
    open(opt.outfile, 'w').write(yaml.dump(checks))


if __name__ == '__main__':
    opt = get_options()
    main(opt)
