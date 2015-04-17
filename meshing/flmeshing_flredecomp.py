from flmeshing import FLMeshing
import re

flrd_regexes = {'flredecomp' : re.compile(r"\/flredecomp\s+::\s+([0-9\.]+)"),
                'flredecomp::gmsh_read' : re.compile(r"I\/O\s+::\s+Gmsh\s+::\s+([0-9\.]+)"),
                'flredecomp::state' : re.compile(r"\/flredecomp\s+::\s+Populate State\s+::\s+([0-9\.]+)"),
                'flredecomp::zoltan' : re.compile(r"\/flredecomp\s+::\s+zoltan\_drive\s+::\s+([0-9\.]+)"),
                'flredecomp::checkpoint' : re.compile(r"\/flredecomp\s+::\s+checkpoint\_simulation\s+::\s+([0-9\.]+)"),
                }

fluidity_regexes = {'fluidity' : re.compile(r"\/fluidity\s+::\s+([0-9\.]+)"),
                    'fluidity::gmsh_read' : re.compile(r"I\/O\s+::\s+Gmsh\s+::\s+([0-9\.]+)"),
                    'fluidity::state' : re.compile(r"I\/O\s+::\s+Populate\_State\s+::\s+([0-9\.]+)"),
                    'fluidity::pressure::assembly' : re.compile(r"\/material_phase\[0\]\/scalar\_field::Pressure::assembly\s+::\s+([0-9\.]+)"),
                    'fluidity::pressure::solve' : re.compile(r"\/material_phase\[0\]\/scalar\_field::Pressure::solve\s+::\s+([0-9\.]+)"),
                    'fluidity::velocity::assembly' : re.compile(r"\/material_phase\[0\]\/vector\_field::Velocity::assembly\s+::\s+([0-9\.]+)"),
                    'fluidity::velocity::solve' : re.compile(r"\/material_phase\[0\]\/vector\_field::Velocity::solve\s+::\s+([0-9\.]+)"),
                    }

class FLRedecompMeshing(FLMeshing):
    benchmark = 'flredecomp'
    description = 'Fluidity flredecomp benchmark'

    method = 'flredecomp'
    profileregions = flrd_regexes.keys() + fluidity_regexes.keys()

    def __init__(self, **kwargs):
        super(FLRedecompMeshing, self).__init__(**kwargs)
        args, _ = self.parser().parse_known_args()
        self._force = args.force

    def flredecomp(self, dim=2, size=5, nprocs=2, timesteps=1, reorder=False, ascii=False):
        self.create_mesh(dim, size, self._force)
        self.create_flml(dim, size, timesteps=timesteps, reorder=reorder)

        # First run flredecomp
        infile = self.filename(name='sim', dim=dim, size=size, end='')
        outfile = self.filename(name='sim', dim=dim, size=size, end='_flrd')
        args = ['-i 1', '-o %d' % nprocs, '-l', '-v', '-p', infile, outfile]
        self.run_application(nprocs, 'flredecomp', args, logfile='flredecomp.log-0', regexes=flrd_regexes)

        # Then run Fluidity to benchmark initial setup
        flmlfile = self.filename(name='sim', dim=dim, size=size, end='_flrd.flml')
        args = ['-l', '-p', flmlfile]
        self.run_application(nprocs, 'fluidity', args, logfile='fluidity.log-0', regexes=fluidity_regexes)


if __name__ == '__main__':
    # Benchmark
    b = FLRedecompMeshing()
    b.main()
