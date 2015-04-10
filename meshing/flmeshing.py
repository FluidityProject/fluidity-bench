from pybench import Benchmark, parser
from string import Template
import re
import os
import re
import subprocess
import pprint

class FLMeshing(Benchmark):
    warmups = 0
    repeats = 3

    def __init__(self, **kwargs):
        super(FLMeshing, self).__init__(**kwargs)
        args, _ = self.parser().parse_known_args()
        self.meta['dim'] = args.dim
        self.meta['sizes'] = args.size
        self.meta['nprocs'] = args.nprocs
        self.series = {'dim': self.meta['dim'],
                       'nprocs': self.meta['nprocs']}
        self.params = [('size', self.meta['sizes'])]

        # Basic filehandling info for Fluidity projects
        self._meshdir = { 2 : 'void-2d', 3 : 'void-3d' }
        self._fname = Template('${dir}/${name}_${dim}d_${size}${end}')
        self._archer = args.archer

    def parser(self, **kwargs):
        p = super(FLMeshing, self).parser(**kwargs)
        p.add_argument('--dim', type=int, default=2,
                       help='Dimension of test mesh (default 2D)')
        p.add_argument('-m', '--size', type=int, nargs='+',
                       help='Relative mesh sizes to use: lf = 1 / size')
        p.add_argument('-np', '--nprocs', type=int,
                       help='Number of procs to run on')
        p.add_argument('-f', '--force', action='store_true', dest='force', default=False,
                       help='Force remeshing before running benchmark')
        p.add_argument('-a', '--archer', action='store_true', dest='archer', default=False,
                       help='Use aprun when running on Archer')
        return p

    def filename(self, name='box', dim=2, size=5, end=''):
        return self._fname.substitute(dir=self._meshdir[dim], name=name, dim=dim, size=size, end=end)

    def create_file_from_template(self, template, newfile, key, value):
        with file(newfile, "w") as nf:
            with file(template, "r") as tf:
                nf.write(re.sub(key, value, tf.read()))

    def create_flml(self, dim, size):
        template = self.filename(name='sim', dim=dim, size='template', end='.flml')
        flmlfile = self.filename(name='sim', dim=dim, size=size, end='.flml')
        meshfile = self.filename(name='box', dim=dim, size=size, end='')

        self.create_file_from_template(template, flmlfile, r"\$MESHNAME\$", meshfile)

    def create_mesh(self, dim, size, force=False):
        template = self.filename(name='box', dim=dim, size='template', end='.geo')
        geofile = self.filename(name='box', dim=dim, size=size, end='.geo')
        meshfile = self.filename(name='box', dim=dim, size=size, end='.msh')
        logfile = self.filename(name='flmeshing', dim=dim, size='', end='.log')
        metafile = self.filename(name='flmeshing', dim=dim, size='', end='.meta')
        re_gmsh_info = re.compile(r"Info\s+:\s+([0-9]+)\s+vertices\s+([0-9]+)\s+elements")

        if not force and os.path.exists(meshfile):
            return

        # Create .geo file, with lf = 1 / size
        self.create_file_from_template(template, geofile, r"\$INSERT_LF\$", r"%.6f" % float(1./size))

        # Run Gmsh on the generated .geo file
        cmd = ['gmsh', '-bin', '-%d' % (dim), '-o', meshfile, geofile]
        print "FLMeshing: Generating meshfile %s from %s" % (meshfile, geofile)
        with file(logfile, "w") as log:
            try:
                subprocess.check_call(cmd, stderr=log, stdout=log)
            except subprocess.CalledProcessError as e:
                raise e

        # Read previous .meta entries
        if (os.path.exists(metafile)):
            with file(metafile, 'r') as mf:
                meta = eval(mf.read())
        else:
            meta = {'_header' : '{ size : [lf, vertices, elements] }' }

        # Read no. vertices/elements from Gmsh log and store in .meta file
        with file(logfile, 'r') as log:
            re_match = re_gmsh_info.search(log.read())
            meta[size] = [ 1. / size, re_match.group(1), re_match.group(2) ]
            with file(metafile, 'w') as mf:
                pprint.pprint(meta, mf)

    def run_application(self, nprocs, binary, args, logfile=None, regexes=None):
        if self._archer:
            pes_per_node = 24 if nprocs > 24 else nprocs
            cmd = ['aprun', '-n %d'%nprocs, '-N %d'%pes_per_node, '-d 1', '-j 1']
        else:
            cmd = ['mpiexec', '-n', '%d'%nprocs]

        cmd += [os.environ['FLUIDITY_DIR'] + "/bin/" + binary]
        cmd += args

        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            raise e

        # Parse log file and extract profiler timings via given regexes
        if (logfile is not None and regexes is not None):
            with file(logfile, "r") as lf:
                log = lf.read()
                for key, regex in regexes.iteritems():
                    try:
                        self.register_timing(key, float(regex.search(log).group(1)))
                    except AttributeError as e:
                        print "WARNING: Could not find match for regex:", regex.pattern

if __name__ == '__main__':
    p = parser(description="Plot results for Fluidity meshing benchmark")
    p.add_argument('--dim', type=int, default=2,
                   help='Dimension of benchmark mesh (default=2)')
    p.add_argument('-m', '--size', type=int, nargs='+',
                   help='mesh sizes to plot')
    args = p.parse_args()

    flm_plex = FLMeshing(resultsdir=args.resultsdir, plotdir=args.plotdir)
    flm_flrd = FLMeshing(resultsdir=args.resultsdir, plotdir=args.plotdir)

    # Get mesh sizes from .meta file
    metafile = flm_plex.filename(name='flmeshing', dim=args.dim, size='', end='.meta')
    with file(metafile, 'r') as mf:
        meshmeta = eval(mf.read())

    # Let's see what we want to compare...
    flrd_regions = ['flredecomp', 'flredecomp::gmsh_read', 'flredecomp::state', 'flredecomp::zoltan']
    fluidity_regions = ['fluidity', 'fluidity::gmsh_read' ,'fluidity::state']
    fldmplex_regions = ['fluidity', 'fluidity::state', 'dmplex', 'dmplex::create', 'dmplex::distribute']

    groups = []
    aggregate = {'flredecomp-total': ['flredecomp', 'fluidity::state']}

    if args.weak:
        meshsizes = [meshmeta[int(m)][2] for m in args.size]

        regions = ['flredecomp', 'fluidity::state']
        flm_flrd.combine_series([('dim', [args.dim]), ('nprocs', args.weak)],
                         filename='flredecomp')
        flm_flrd.plot(xaxis='size', wscale=0.7, format='pdf', kinds='plot',
               regions=regions, groups=groups,
               xlabel='Mesh size (cells)', xticklabels=meshsizes,
               figname='FLM-Flrd', legend={'loc': 'upper left'},
               title='Fluidity-flredecomp startup: dim=%(dim)d')

        regions = ['fluidity::state', 'dmplex']
        flm_plex.combine_series([('dim', [args.dim]), ('nprocs', args.weak)],
                         filename='fldmplex')
        flm_plex.plot(xaxis='size', wscale=0.7, format='pdf', kinds='plot',
               regions=regions, groups=groups,
               xlabel='Mesh size (cells)', xticklabels=meshsizes,
               figname='FLM-DMPlex', legend={'loc': 'upper left'},
               title='Fluidity-DMPlex startup: dim=%(dim)d')
