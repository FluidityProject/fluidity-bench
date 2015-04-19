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
        self.meta['timesteps'] = args.timesteps
        self.meta['reorder'] = args.reorder
        self.meta['ascii'] = args.ascii

        self.params = [('dim', [self.meta['dim']]),
                       ('size', self.meta['sizes']),
                       ('nprocs', self.meta['nprocs']),
                       ('timesteps', [self.meta['timesteps']]),
                       ('reorder', [self.meta['reorder']]),
                       ('ascii', [self.meta['ascii']])]

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
        p.add_argument('-np', '--nprocs', type=int, nargs='+',
                       help='Number of procs to run on')
        p.add_argument('-ts', '--timesteps', type=int, default=1,
                       help='Number of procs to run on')
        p.add_argument('-f', '--force', action='store_true', dest='force', default=False,
                       help='Force remeshing before running benchmark')
        p.add_argument('--archer', action='store_true', dest='archer', default=False,
                       help='Use aprun when running on Archer')
        p.add_argument('--ascii', action='store_true', dest='ascii', default=False,
                       help='Use meshes in ASCII Gmsh format')
        p.add_argument('--reorder', action='store_true', dest='reorder', default=False,
                       help='Apply RCM reordering to DMPlex-generated meshes')
        return p

    def filename(self, name='box', dim=2, size=5, end=''):
        return self._fname.substitute(dir=self._meshdir[dim], name=name, dim=dim, size=size, end=end)

    def create_file_from_template(self, template, newfile, replacements):
        with file(newfile, "w") as nf:
            with file(template, "r") as tf:
                fbuffer = tf.read()
                for key, value in replacements.iteritems():
                    fbuffer = re.sub(key, value, fbuffer)
                nf.write(fbuffer)

    def create_flml(self, dim, size, timesteps=1, reorder=False):
        template = self.filename(name='sim', dim=dim, size='template', end='.flml')
        flmlfile = self.filename(name='sim', dim=dim, size=size, end='.flml')
        if self.meta['ascii']:
            meshfile = self.filename(name='box', dim=dim, size=size, end='_ascii')
        else:
            meshfile = self.filename(name='box', dim=dim, size=size, end='')

        replacements = {r"\$MESHNAME\$": meshfile,
                        r"\$TIMESTEP\$": str(timesteps)}
        replacements[r"\$REORDERING\$"] = "<rcm_reordering/>" if reorder else "<no_reordering/>"
        self.create_file_from_template(template, flmlfile, replacements)

    def create_mesh(self, dim, size, force=False):
        template = self.filename(name='box', dim=dim, size='template', end='.geo')
        geofile = self.filename(name='box', dim=dim, size=size, end='.geo')
        logfile = self.filename(name='flmeshing', dim=dim, size='', end='.log')
        metafile = self.filename(name='flmeshing', dim=dim, size='', end='.meta')
        if self.meta['ascii']:
            meshfile = self.filename(name='box', dim=dim, size=size, end='_ascii.msh')
        else:
            meshfile = self.filename(name='box', dim=dim, size=size, end='.msh')
        re_gmsh_info = re.compile(r"Info\s+:\s+([0-9]+)\s+vertices\s+([0-9]+)\s+elements")

        if not force and os.path.exists(meshfile):
            return

        # Create .geo file, with lf = 1 / size
        replacements = {r"\$INSERT_LF\$": r"%.6f" % float(1./size)}
        self.create_file_from_template(template, geofile, replacements)

        # Run Gmsh on the generated .geo file
        cmd = ['gmsh', '-%d' % (dim), '-o', meshfile, geofile]
        if self.meta['ascii']:
            cmd = ['gmsh', '-%d' % (dim), '-o', meshfile, geofile]
        else:
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

def add_weak_line(ax, flm, args, region, label, color, linestyle='solid'):
    params = {'dim': args.dim, 'timesteps': args.timesteps,
              'reorder': args.reorder, 'ascii': args.ascii}
    groups = {'np': args.weak}
    regions = [region]
    style = {region: {'linestyle': linestyle, 'color': color}}
    labels = {(args.weak[0],): label}
    flm.subplot(ax, xaxis='size', kind='plot', xvals=args.size, xvalues=meshsizes,
                xlabel='Mesh Size', xticklabels=meshsizes,
                title='Fluidity Startup Cost', axis='tight',
                regions=regions, groups=groups, params=params,
                plotstyle=style, labels=labels)

def add_strong_line(ax, flm, args, region, label, color, linestyle='solid'):
    regions = [region]
    params = {'dim': args.dim, 'np': args.parallel, 'timesteps': args.timesteps,
              'reorder': args.reorder, 'ascii': args.ascii}
    groups = {'size': args.size}
    style = {region: {'linestyle': linestyle, 'color': color}}
    labels = {(args.size[0],): label}
    flm.subplot(ax, xaxis='np', kind='semilogx', xvals=args.parallel,
                xlabel='Number of Processes', xticklabels=args.parallel,
                title='Fluidity Startup Cost', axis='tight',
                regions=regions, groups=groups, params=params,
                plotstyle=style, labels=labels)


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    import numpy as np

    p = parser(description="Plot results for Fluidity meshing benchmark")
    p.add_argument('--dim', type=int, default=2,
                   help='Dimension of benchmark mesh (default=2)')
    p.add_argument('-m', '--size', type=int, nargs='+',
                   help='mesh sizes to plot')
    p.add_argument('-ts', '--timesteps', type=int, default=1,
                   help='Number of procs to run on')
    p.add_argument('--ascii', action='store_true', dest='ascii', default=False,
                   help='Use meshes in ASCII Gmsh format')
    p.add_argument('--reorder', action='store_true', dest='reorder', default=False,
                   help='Apply RCM reordering to DMPlex-generated meshes')
    args = p.parse_args()
    flm = FLMeshing(resultsdir=args.resultsdir, plotdir=args.plotdir)

    # Get mesh sizes from .meta file
    metafile = flm.filename(name='flmeshing', dim=args.dim, size='', end='.meta')
    with file(metafile, 'r') as mf:
        meshmeta = eval(mf.read())
    meshsizes = [int(meshmeta[int(m)][2]) for m in args.size]

    nprocs = args.weak if args.weak else args.parallel

    # Precompute colormap
    cmap = mpl.cm.get_cmap("Set1")
    numColors = 10
    colors = [cmap(i) for i in np.linspace(0, 0.9, numColors)]

    # Type and name of plot
    add_plot_line = add_weak_line if args.weak else add_strong_line
    fname = "Weak" if args.weak else "Strong"
    fname += "_ascii" if args.ascii else ""
    fname += "_plot" if args.weak else "_semilogx"
    fname += "_dim%d" % args.dim
    fname += "_np%d" % args.weak[0] if args.weak else "_m%d" % args.size[0]
    fname += ".pdf"

    if args.reorder:
        # Performance runs to highlight renumbering effects
        fig_pres, ax_pres = create_figure("PressureSolve.pdf")
        fig_vel, ax_vel = create_figure("VelocityAssembly.pdf")
        fig_run, ax_run = create_figure("FluidityRun.pdf")

        flm.load(filename='fldmplex')

        # Add reordered DMPlex results
        add_plot_line(ax_pres, flm, args, 'fluidity::pressure::solve',
                      'DMPlex RCM', color=colors[0], linestyle='dashed')
        add_plot_line(ax_vel, flm, args, 'fluidity::velocity::assembly',
                      'DMPlex RCM', color=colors[0], linestyle='dashed')
        add_plot_line(ax_run, flm, args, 'fluidity',
                      'DMPlex RCM', color=colors[0], linestyle='dashed')

        # Add native DMPlex results
        args.reorder = False
        add_plot_line(ax_pres, flm, args, 'fluidity::pressure::solve',
                      'DMPlex native', color=colors[0], linestyle='solid')
        add_plot_line(ax_vel, flm, args, 'fluidity::velocity::assembly',
                      'DMPlex native', color=colors[0], linestyle='solid')
        add_plot_line(ax_run, flm, args, 'fluidity',
                      'DMPlex native', color=colors[0], linestyle='solid')

        # Add native flredecomp results
        flm.load(filename='flredecomp')
        add_plot_line(ax_pres, flm, args, 'fluidity::pressure::solve',
                      'DMPlex native', color=colors[1], linestyle='solid')
        add_plot_line(ax_vel, flm, args, 'fluidity::velocity::assembly',
                      'DMPlex native', color=colors[1], linestyle='solid')
        add_plot_line(ax_run, flm, args, 'fluidity',
                      'DMPlex native', color=colors[1], linestyle='solid')

        save_fig(fig_pres, "PresSolve"+fname)
        save_fig(fig_vel, "VelAssembly"+fname)
        save_fig(fig_run, "Fluidity"+fname)

    else:
        # Startup runs to highlight DMPlex-I/O performance
        fig_start, ax_start = create_figure("FluidityStartup.pdf")
        fig_part, ax_part = create_figure("FluidityDistribute.pdf")
        fig_io, ax_io = create_figure("FluidityIO.pdf")

        # Flredecomp results
        flm.load(filename='flredecomp')
        aggregate = {'startup::total': ['flredecomp', 'fluidity::state']}
        flm.aggregate_timings(aggregate)

        add_plot_line(ax_start, flm, args, 'flredecomp', 'Preprocess',
                      color=colors[0], linestyle='dashed')
        add_plot_line(ax_start, flm, args, 'fluidity::state', 'Startup-Preproc',
                      color=colors[0], linestyle='dotted')
        add_plot_line(ax_start, flm, args, 'startup::total', 'Startup-Total',
                      color=colors[0], linestyle='solid')

        add_plot_line(ax_part, flm, args, 'flredecomp::zoltan', 'Fluidity-Zoltan',
                      color=colors[0])

        add_plot_line(ax_io, flm, args, 'flredecomp::gmsh_read', 'Fluidity-Gmsh',
                      color=colors[0])
        add_plot_line(ax_io, flm, args, 'fluidity::gmsh_read', 'Preproc-Gmsh',
                      color=colors[0], linestyle='dashed')

        # DMPlex results
        flm.load(filename='fldmplex')
        add_plot_line(ax_start, flm, args, 'fluidity::state', 'Startup-DMPlex',
                      color=colors[1])

        add_plot_line(ax_part, flm, args, 'dmplex::distribute', 'DMPlex-Distribute',
                      color=colors[1])
        add_plot_line(ax_io, flm, args, 'dmplex::create', 'DMPlex-Gmsh',
                      color=colors[1], linestyle='solid')

        if args.ascii:
            fname = "Weak_ascii_plot_dim%d_np%d.pdf" % (args.dim, args.weak[0])
        else:
            fname = "Weak_binary_plot_dim%d_np%d.pdf" % (args.dim, args.weak[0])
        save_fig(fig_start, "Startup"+fname)
        save_fig(fig_part, "Distribute"+fname)
        save_fig(fig_io, "Gmsh"+fname)
