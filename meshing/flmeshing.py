from pybench import Benchmark, parser
from string import Template
import re
import os
import re
import subprocess
import pprint

class FLMeshing(Benchmark):
    warmups = 0
    repeats = 1

    def __init__(self, **kwargs):
        super(FLMeshing, self).__init__(**kwargs)
        args, _ = self.parser().parse_known_args()
        self.meta['dim'] = args.dim
        self.meta['sizes'] = args.size
        self.meta['nprocs'] = args.nprocs
        self.series = {'dim' : self.meta['dim']}
        self.params = [('dim', [self.meta['dim']]),
                       ('size', self.meta['sizes']),
                       ('nprocs', self.meta['nprocs']),
                       ('force', [args.force])]

        # Basic filehandling info for Fluidity projects
        self._meshdir = { 2 : 'void-2d', 3 : 'void-3d' }
        self._fname = Template('${dir}/${name}_${dim}d_${size}${end}')

    def parser(self, **kwargs):
        p = super(FLMeshing, self).parser(**kwargs)
        p.add_argument('--dim', type=int, default=2,
                       help='Dimension of test mesh (default 2D)')
        p.add_argument('-m', '--size', type=int, nargs='+',
                       help='Relative mesh sizes to use: lf = 1 / size')
        p.add_argument('-np', '--nprocs', type=int, nargs='+',
                       help='Number of procs to run on')
        p.add_argument('-f', '--force', action='store_true', dest='force', default=False,
                       help='Force remeshing before running benchmark')
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

        # Create .go file, with lf = 1 / size
        self.create_file_from_template(template, geofile, r"\$INSERT_LF\$", r"%.6f" % float(1./size))

        # Run Gmsh on the generated .geo file
        cmd = ['gmsh', '-%d' % (dim), '-o', meshfile, geofile]
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


if __name__ == '__main__':
    p = parser(description="Plot results for Fluidity meshing benchmark")
    p.add_argument('--dim', type=int, default=2,
                   help='Dimension of benchmark mesh (default=2)')
