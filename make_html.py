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

check_data = yaml.safe_load(open(opt.infile).read())
checks = check_data['checks']
for check in checks:
    check['basename'] = ""
    if 'filename' in check:
        check['basename'] = os.path.basename(check['filename'])

headercols = ['id', 'title', 'file',
              'type', 'severity', 'aca_cl_id']

displaycols = ['id', 'title', 'file',
              'type', 'severity', 'aca_cl_id',
              'note', 'orvdot']

details = jinja_env.get_template('details.html')
detailpage = "details.html"
page = details.render(table=checks,
                      displaycols=displaycols)
f = open(os.path.join(opt.outdir, detailpage), 'w')
f.write(page)
f.close()

toc = jinja_env.get_template('toc.html')
page = toc.render(
    starcheck_commit=check_data['info']['starcheck_commit'],
    tags=check_data['info']['tags'],
    table=checks,
    headercols=headercols,
    detailpage=detailpage)
f = open(os.path.join(opt.outdir, "index.html"), 'w')
f.write(page)
f.close()
