import os
import yaml
import shutil
import jinja2


def get_options():
    import argparse
    parser = argparse.ArgumentParser(
        description="Get starcheck checks")
    parser.set_defaults()
    parser.add_argument("--infile",
                        default="checks.yaml",
                        help="file of checks (output from previous run of tool)")
    parser.add_argument("--outdir",
                        default="report_html")
    args = parser.parse_args()
    return args

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'))
jinja_env.line_comment_prefix = '##'
jinja_env.line_statement_prefix = '#'


opt = get_options()
if not os.path.exists(opt.outdir):
    os.makedirs(opt.outdir)
shutil.copy("prism_ocadia.css", opt.outdir)
shutil.copy("prism.js", opt.outdir)
shutil.copy("sorttable.js", opt.outdir)

checks = yaml.load(open(opt.infile).read())['checks']

displaycols = ['id', 'link', 'filename', 'line_number',
               'title', 'github_link',
               'ignore', 'missing', 'text', 'notes',
               'aca_cl_id', 'type', 'byhand', 'severity', 'hopper']

single_check = jinja_env.get_template('single_check.html')
for c in checks:
    page = single_check.render(context=c['context'],
                               displaycols=displaycols,
                               check=c)
    report_filename = "{:05d}_check.html".format(c['id'])
    c['report_page'] = report_filename
    f = open(os.path.join(opt.outdir, report_filename), 'w')
    f.write(page)
    f.close()
    c['filename'] = os.path.basename(c['filename'])

toc = jinja_env.get_template('toc.html')
page = toc.render(table=checks,
           displaycols=displaycols)
f = open(os.path.join(opt.outdir, "index.html"), 'w')
f.write(page)
f.close()
