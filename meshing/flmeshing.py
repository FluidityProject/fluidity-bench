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
        kwargs['rank'] = 0
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

    # Note: Aggregation for param lists is currently broken in pybench
    def aggregate_timings(self, aggregate):
        for target, regions in aggregate.items():
            for k, timing in self.result['timings'].iteritems():
                timing[target] = sum(timing[region] for region in regions)

def create_figure(name, figsize=(9, 6)):
    fig = plt.figure(name, figsize=figsize, dpi=300)
    ax = fig.add_subplot(111)
    return fig, ax


def save_fig(fig, fname):
    fpath = os.path.join(args.plotdir, fname)
    fig.savefig(os.path.join(args.plotdir, fname),
                orientation='landscape', format="pdf",
                transparent=True, bbox_inches='tight')


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import numpy as np

    p = parser(description="Plot results for Fluidity meshing benchmark")
    p.add_argument('--dim', type=int, default=2,
                   help='Dimension of benchmark mesh (default=2)')
    p.add_argument('-m', '--size', type=int, nargs='+',
                   help='mesh sizes to plot')
    args = p.parse_args()
    flm = FLMeshing(resultsdir=args.resultsdir, plotdir=args.plotdir)

    # Get mesh sizes from .meta file
    metafile = flm.filename(name='flmeshing', dim=args.dim, size='', end='.meta')
    with file(metafile, 'r') as mf:
        meshmeta = eval(mf.read())

    # Precompute colormap
    cmap = mpl.cm.get_cmap("Set1")
    numColors = 10
    colors = [cmap(i) for i in np.linspace(0, 0.9, numColors)]

    if args.weak:
        meshsizes = [meshmeta[int(m)][2] for m in args.size]
        def add_plot_line(ax, region, label, color=colors[0], linestyle='solid'):
            params = {'dim': args.dim}
            groups = {'np': args.weak}
            regions = [region]
            style = {region: {'linestyle': linestyle, 'color': color}}
            labels = {(args.weak[0],): label}
            flm.subplot(ax, xaxis='size', kind='plot', xvals=args.size,
                        xlabel='Mesh Size', xticklabels=meshsizes,
                        title='Fluidity Startup Cost', axis='tight',
                        regions=regions, groups=groups, params=params,
                        plotstyle=style, labels=labels)

        fig_start, ax_start = create_figure("FluidityStartup.pdf")
        fig_part, ax_part = create_figure("FluidityDistribute.pdf")
        fig_io, ax_io = create_figure("FluidityIO.pdf")

        # Flredecomp results
        flm.combine_series([('dim', [args.dim]), ('nprocs', args.weak)],
                           filename='flredecomp')
        aggregate = {'startup::total': ['flredecomp', 'fluidity::state']}
        flm.aggregate_timings(aggregate)

        add_plot_line(ax_start, 'flredecomp', 'Preprocess',
                      color=colors[0], linestyle='dashed')
        add_plot_line(ax_start, 'fluidity::state', 'Startup-Preproc',
                      color=colors[0], linestyle='dotted')
        add_plot_line(ax_start, 'startup::total', 'Startup-Total',
                      color=colors[0], linestyle='solid')

        add_plot_line(ax_part, 'flredecomp::zoltan', 'Fluidity-Zoltan',
                      color=colors[0])

        add_plot_line(ax_io, 'flredecomp::gmsh_read', 'Fluidity-Gmsh',
                      color=colors[0])
        add_plot_line(ax_io, 'fluidity::gmsh_read', 'Preproc-Gmsh',
                      color=colors[0], linestyle='dashed')

        # DMPlex results
        flm.combine_series([('dim', [args.dim]), ('nprocs', args.weak)],
                           filename='fldmplex')
        add_plot_line(ax_start, 'fluidity::state', 'Startup-DMPlex',
                      color=colors[1])

        add_plot_line(ax_part, 'dmplex::distribute', 'DMPlex-Distribute',
                      color=colors[1])
        add_plot_line(ax_io, 'dmplex::create', 'DMPlex-Gmsh',
                      color=colors[1], linestyle='solid')


        fname = "StartupWeak_plot_dim%d_np%d.pdf" % (args.dim, args.weak[0])
        save_fig(fig_start, fname)
        fname = "DistributeWeak_plot_dim%d_np%d.pdf" % (args.dim, args.weak[0])
        save_fig(fig_part, fname)
        fname = "GmshWeak_plot_dim%d_np%d.pdf" % (args.dim, args.weak[0])
        save_fig(fig_io, fname)
